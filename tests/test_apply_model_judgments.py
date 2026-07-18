import json
import io
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from shared.scripts.apply_model_judgments import _read_jsonl, apply_model_judgments, main
from shared.scripts.schema_validation import (
    ValidationError,
    validate_audit_row,
    validate_audit_run_pair,
    validate_run_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_JSONL = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"
MANIFEST_JSON = REPO_ROOT / "tests" / "golden" / "fixture-manifest.json"


def load_fixture_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in AUDIT_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_fixture_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))


def judgment_for(
    note_path: str,
    *,
    prompt_version: str = "1.0.1",
    findings: list[dict[str, object]] | None = None,
    dimension_adjustments: dict[str, int] | None = None,
    factual_risk: bool = False,
    factual_risk_reason: str | None = None,
    fact_check_required: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": "2.0.0",
        "prompt_version": prompt_version,
        "note_path": note_path,
        "dimension_adjustments": dimension_adjustments or {},
        "findings": findings or [],
        "factual_risk": factual_risk,
        "factual_risk_reason": factual_risk_reason,
        "fact_check_required": fact_check_required,
        "evidence": [
            {
                "excerpt": "Definition: A compact note has one idea.",
                "reason": "Synthetic evidence for contract validation.",
            }
        ],
    }


def judgments_for_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [judgment_for(str(row["note_path"])) for row in rows]


class ApplyModelJudgmentsTest(unittest.TestCase):
    def test_full_merge_recomputes_score_priority_clean_and_manifest_counts(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        judgments[0] = judgment_for(
            str(rows[0]["note_path"]),
            findings=[
                {
                    "code": "weak_analogy",
                    "message": "The analogy does not use a familiar concrete referent.",
                    "evidence": [
                        {
                            "excerpt": "Analogy: The idea maps to another idea.",
                            "reason": "The referent is abstract.",
                        }
                    ],
                }
            ],
            dimension_adjustments={"dae_quality": -10},
        )

        merged_rows, merged_manifest = apply_model_judgments(
            rows,
            manifest,
            judgments,
            outputs={
                "audit_rows": "model.jsonl",
                "model_judgments": "judgments.jsonl",
                "manifest": "model-manifest.json",
            },
        )

        changed = next(row for row in merged_rows if row["note_path"] == rows[0]["note_path"])
        self.assertEqual(changed["score"], 85)
        self.assertEqual(changed["priority"], "P3")
        self.assertFalse(changed["clean"])
        self.assertFalse(changed["pending_model"])
        self.assertEqual(changed["cache_status"], "miss")
        self.assertEqual(changed["dimensions"]["dae_quality"], 90)
        self.assertEqual(changed["model_judgment"]["findings"][0]["code"], "weak_analogy")
        self.assertEqual(merged_manifest["priority_counts"]["P3"], 7)
        self.assertEqual(merged_manifest["priority_counts"]["no_change"], 2)
        self.assertEqual(merged_manifest["validation_status"], "passed")

        for row in merged_rows:
            validate_audit_row(row, default_scan=True)
        validate_run_manifest(merged_manifest)
        validate_audit_run_pair(merged_rows, merged_manifest)

    def test_model_factual_risk_flag_adds_finding_and_loss(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        judgments[0] = judgment_for(
            str(rows[0]["note_path"]),
            factual_risk=True,
            factual_risk_reason="The note makes a factual claim that needs verification.",
            fact_check_required=True,
        )

        merged_rows, _ = apply_model_judgments(rows, manifest, judgments)

        changed = next(row for row in merged_rows if row["note_path"] == rows[0]["note_path"])
        self.assertEqual(changed["score"], 92)
        self.assertEqual(changed["priority"], "P3")
        self.assertFalse(changed["clean"])
        self.assertTrue(changed["factual_risk"])
        self.assertTrue(changed["fact_check_required"])
        self.assertIn(
            {"code": "factual_risk", "message": "Mark empirical, current, attributed, or sensitive-domain claims for fact checking."},
            changed["findings"],
        )

    def test_model_judgment_can_clear_deterministic_factual_risk(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        deterministic_factual_risk_row = rows[5]
        judgments[5] = judgment_for(str(deterministic_factual_risk_row["note_path"]))

        merged_rows, _ = apply_model_judgments(rows, manifest, judgments)

        changed = next(
            row
            for row in merged_rows
            if row["note_path"] == deterministic_factual_risk_row["note_path"]
        )
        self.assertFalse(changed["factual_risk"])
        self.assertFalse(changed["fact_check_required"])
        self.assertNotIn("factual_risk_reason", changed)
        self.assertNotIn("factual_risk", {finding["code"] for finding in changed["findings"]})

    def test_model_judgment_can_clear_deterministic_dae_false_positive(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        weak_dae_row = rows[1]
        judgments[1] = judgment_for(str(weak_dae_row["note_path"]))

        merged_rows, _ = apply_model_judgments(rows, manifest, judgments)

        changed = next(row for row in merged_rows if row["note_path"] == weak_dae_row["note_path"])
        self.assertEqual(changed["score"], 92)
        self.assertEqual(changed["findings"], [{"code": "missing_parent", "message": "Link this note from a structure note."}])

    def test_read_jsonl_wraps_malformed_json_as_validation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"ok": true}\n{"broken":\n', encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "bad.jsonl:2"):
                _read_jsonl(path)

    def test_invalid_dae_suppresses_component_model_findings(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        weak_dae_row = rows[1]
        judgments[1] = judgment_for(
            str(weak_dae_row["note_path"]),
            findings=[
                {
                    "code": "invalid_dae",
                    "message": "The note does not contain a valid DAE structure.",
                    "evidence": [
                        {
                            "excerpt": "This note only gestures at the idea.",
                            "reason": "The required DAE sections are not present.",
                        }
                    ],
                },
                {
                    "code": "weak_analogy",
                    "message": "The analogy is too abstract.",
                    "evidence": [
                        {
                            "excerpt": "Analogy: It is like a system.",
                            "reason": "The referent is vague.",
                        }
                    ],
                }
            ],
        )

        merged_rows, _ = apply_model_judgments(rows, manifest, judgments)

        changed = next(row for row in merged_rows if row["note_path"] == weak_dae_row["note_path"])
        self.assertEqual(changed["score"], 57)
        self.assertNotIn("weak_analogy", {finding["code"] for finding in changed["findings"]})

    def test_missing_judgment_fails_by_default(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)[:-1]

        with self.assertRaises(ValidationError):
            apply_model_judgments(rows, manifest, judgments)

    def test_allow_missing_marks_unmatched_rows_pending(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        rows[-1]["score"] = None
        judgments = [judgment_for(str(rows[0]["note_path"]))]

        merged_rows, merged_manifest = apply_model_judgments(
            rows,
            manifest,
            judgments,
            allow_missing=True,
        )

        reviewed = next(row for row in merged_rows if row["note_path"] == rows[0]["note_path"])
        pending = next(row for row in merged_rows if row["note_path"] == rows[-1]["note_path"])
        self.assertFalse(reviewed["pending_model"])
        self.assertTrue(pending["pending_model"])
        self.assertIsNone(pending["score"])
        self.assertFalse(pending["clean"])
        validate_audit_run_pair(merged_rows, merged_manifest)

    def test_duplicate_judgment_fails(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        judgments.append(deepcopy(judgments[0]))

        with self.assertRaises(ValidationError):
            apply_model_judgments(rows, manifest, judgments)

    def test_stale_prompt_version_fails(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        judgments[0]["prompt_version"] = "1.0.0"

        with self.assertRaisesRegex(ValidationError, "prompt_version mismatch"):
            apply_model_judgments(rows, manifest, judgments)

    def test_missing_prompt_version_fails(self):
        rows = load_fixture_rows()
        manifest = load_fixture_manifest()
        judgments = judgments_for_rows(rows)
        del judgments[0]["prompt_version"]

        with self.assertRaisesRegex(ValidationError, "missing required keys: prompt_version"):
            apply_model_judgments(rows, manifest, judgments)

    def test_cli_writes_valid_outputs(self):
        rows = load_fixture_rows()
        judgments = judgments_for_rows(rows)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            judgments_path = tmp_path / "model-judgments.jsonl"
            output_jsonl = tmp_path / "audit-model.jsonl"
            output_manifest = tmp_path / "manifest-model.json"
            judgments_path.write_text(
                "\n".join(json.dumps(judgment, sort_keys=True) for judgment in judgments) + "\n",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "--audit-jsonl",
                        str(AUDIT_JSONL),
                        "--manifest",
                        str(MANIFEST_JSON),
                        "--model-judgments",
                        str(judgments_path),
                        "--output-jsonl",
                        str(output_jsonl),
                        "--output-manifest",
                        str(output_manifest),
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue(output_jsonl.exists())
            self.assertTrue(output_manifest.exists())
            merged_rows = [
                json.loads(line)
                for line in output_jsonl.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            merged_manifest = json.loads(output_manifest.read_text(encoding="utf-8"))
            for row in merged_rows:
                validate_audit_row(row, default_scan=True)
            validate_run_manifest(merged_manifest)
            validate_audit_run_pair(merged_rows, merged_manifest)


if __name__ == "__main__":
    unittest.main()
