import json
import io
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from shared.scripts.finding_codes import ALLOWED_FINDING_CODES, FINDING_RECOMMENDATION_MODES
from shared.scripts.schema_validation import (
    ValidationError,
    validate_audit_row,
    validate_audit_run_pair,
    validate_run_manifest,
)
from shared.scripts.validate_jsonl import main, validate_jsonl_file


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROW_SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "audit-row.schema.json"
MODEL_JUDGMENT_SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "model-judgment.schema.json"
RUN_MANIFEST_SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "run-manifest.schema.json"

VALID_ROW = {
    "schema_version": "1.0.0",
    "run_id": "run-1",
    "row_status": "complete",
    "note_path": "Atomic Notes/202601010101 Example.md",
    "note_link": "[[202601010101 Example]]",
    "content_hash": "abc123",
    "modified_time": "2026-06-05T12:00:00Z",
    "score": 100,
    "priority": None,
    "clean": True,
    "pending_model": False,
    "dimensions": {
        "structure": 100,
        "atomicity": 100,
        "dae_quality": 95,
        "clarity": 95,
        "connections": 90,
        "metadata_card_safety": 100
    },
    "findings": [],
    "recommendations": [],
    "model_judgment": None,
    "cache_status": "none",
    "factual_risk": False,
    "fact_check_required": False,
    "config_snapshot": {},
    "doctrine_version": "1.0.0",
    "rubric_version": "1.0.0",
    "prompt_version": "1.0.0"
}

VALID_EMBEDDED_MODEL_JUDGMENT = {
    "schema_version": "2.0.0",
    "prompt_version": VALID_ROW["prompt_version"],
    "note_path": VALID_ROW["note_path"],
    "dimension_adjustments": {"clarity": -5},
    "findings": [
        {
            "code": "weak_definition",
            "message": "The definition needs a clearer boundary.",
            "evidence": [
                {
                    "excerpt": "Definition: An idea that links to other ideas.",
                    "reason": "The definition does not distinguish the idea from a general note.",
                }
            ],
        }
    ],
    "factual_risk": False,
    "factual_risk_reason": None,
    "fact_check_required": False,
    "evidence": [],
}

VALID_MANIFEST = {
    "schema_version": "1.0.0",
    "run_id": "run-1",
    "started_at": "2026-06-05T12:00:00Z",
    "ended_at": "2026-06-05T12:00:01Z",
    "config_snapshot": {},
    "total_notes": 1,
    "row_status_counts": {
        "complete": 1,
        "reused_cache": 0,
        "error": 0,
        "skipped": 0,
    },
    "priority_counts": {
        "P0": 0,
        "P1": 0,
        "P2": 0,
        "P3": 0,
        "no_change": 1,
    },
    "validation_status": "not_run",
    "outputs": {
        "audit_rows": "audit.jsonl",
        "manifest": "manifest.json",
    },
    "errors": [],
}


class SchemaValidationTest(unittest.TestCase):
    def test_valid_row_passes(self):
        validate_audit_row(dict(VALID_ROW), default_scan=True)

    def test_missing_required_key_fails(self):
        row = dict(VALID_ROW)
        del row["note_link"]
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_missing_model_judgment_fails(self):
        row = dict(VALID_ROW)
        del row["model_judgment"]
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_valid_embedded_model_judgment_passes(self):
        row = dict(VALID_ROW)
        row["model_judgment"] = VALID_EMBEDDED_MODEL_JUDGMENT

        validate_audit_row(row, default_scan=True)

    def test_embedded_model_judgment_note_path_must_match_row(self):
        row = dict(VALID_ROW)
        row["model_judgment"] = {
            **VALID_EMBEDDED_MODEL_JUDGMENT,
            "note_path": "Atomic Notes/202601010102 Other.md",
        }

        with self.assertRaisesRegex(ValidationError, r"model_judgment\.note_path mismatch"):
            validate_audit_row(row, default_scan=True)

    def test_embedded_model_judgment_prompt_version_must_match_row(self):
        row = dict(VALID_ROW)
        row["model_judgment"] = {
            **VALID_EMBEDDED_MODEL_JUDGMENT,
            "prompt_version": "1.0.2",
        }

        with self.assertRaisesRegex(ValidationError, r"model_judgment\.prompt_version mismatch"):
            validate_audit_row(row, default_scan=True)

    def test_old_embedded_model_judgment_fails(self):
        row = dict(VALID_ROW)
        row["model_judgment"] = {
            **VALID_EMBEDDED_MODEL_JUDGMENT,
            "schema_version": "1.0.0",
        }

        with self.assertRaisesRegex(
            ValidationError,
            r"model_judgment\.schema_version must be 2\.0\.0",
        ):
            validate_audit_row(row, default_scan=True)

    def test_malformed_embedded_model_judgment_fails(self):
        row = dict(VALID_ROW)
        row["model_judgment"] = {
            **VALID_EMBEDDED_MODEL_JUDGMENT,
            "fact_check_required": "false",
        }

        with self.assertRaisesRegex(
            ValidationError,
            "model_judgment.fact_check_required must be a boolean",
        ):
            validate_audit_row(row, default_scan=True)

    def test_extra_audit_row_key_fails(self):
        row = dict(VALID_ROW)
        row["extra"] = 1
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_created_time_none_fails(self):
        row = dict(VALID_ROW)
        row["created_time"] = None
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_factual_risk_reason_must_be_string_when_present(self):
        row = dict(VALID_ROW)
        row["factual_risk_reason"] = 123
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_skipped_default_scan_fails(self):
        row = dict(VALID_ROW)
        row["row_status"] = "skipped"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_score_bool_fails(self):
        row = dict(VALID_ROW)
        row["score"] = True
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_unclosed_note_link_fails(self):
        row = dict(VALID_ROW)
        row["note_link"] = "[[Unclosed"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_note_link_empty_alias_target_fails(self):
        row = dict(VALID_ROW)
        row["note_link"] = "[[|Alias]]"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_non_string_note_path_fails(self):
        row = dict(VALID_ROW)
        row["note_path"] = 123
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_string_factual_risk_fails(self):
        row = dict(VALID_ROW)
        row["factual_risk"] = "medium"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_string_pending_model_fails(self):
        row = dict(VALID_ROW)
        row["pending_model"] = "false"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_invalid_row_status_fails(self):
        row = dict(VALID_ROW)
        row["row_status"] = "pending"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_invalid_priority_fails(self):
        row = dict(VALID_ROW)
        row["priority"] = "P4"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_invalid_cache_status_fails(self):
        row = dict(VALID_ROW)
        row["cache_status"] = "warm"
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_recommendations_must_be_list_of_objects(self):
        row = dict(VALID_ROW)
        row["recommendations"] = {"mode": "improve-in-place", "message": "Tighten one alias."}
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_unknown_finding_code_fails(self):
        row = dict(VALID_ROW)
        row["findings"] = [{"code": "weak_connection", "message": "Not an allowed code."}]
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_out_of_range_score_fails(self):
        row = dict(VALID_ROW)
        row["score"] = 101
        with self.assertRaises(ValidationError):
            validate_audit_row(row, default_scan=True)

    def test_skipped_non_default_scan_passes(self):
        row = dict(VALID_ROW)
        row["row_status"] = "skipped"
        validate_audit_row(row, default_scan=False)

    def test_audit_row_schema_defines_factual_risk_as_boolean(self):
        schema = json.loads(AUDIT_ROW_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["factual_risk"], {"type": "boolean"})

    def test_audit_row_schema_allows_score_null(self):
        schema = json.loads(AUDIT_ROW_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertIn("integer", schema["properties"]["score"]["type"])
        self.assertIn("null", schema["properties"]["score"]["type"])
        self.assertEqual(schema["properties"]["score"]["minimum"], 1)

    def test_model_judgment_schema_defines_factual_risk_as_boolean(self):
        schema = json.loads(MODEL_JUDGMENT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["factual_risk"]["type"], "boolean")

    def test_schema_finding_code_enums_match_source_of_truth(self):
        audit_schema = json.loads(AUDIT_ROW_SCHEMA_PATH.read_text(encoding="utf-8"))
        model_schema = json.loads(MODEL_JUDGMENT_SCHEMA_PATH.read_text(encoding="utf-8"))
        expected = list(ALLOWED_FINDING_CODES)

        self.assertEqual(audit_schema["$defs"]["finding"]["properties"]["code"]["enum"], expected)
        self.assertEqual(model_schema["$defs"]["finding"]["properties"]["code"]["enum"], expected)

    def test_remediation_plan_schema_modes_match_finding_recommendations(self):
        schema = json.loads(
            (REPO_ROOT / "shared" / "schemas" / "remediation-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        expected = sorted(set(FINDING_RECOMMENDATION_MODES.values()))

        self.assertEqual(sorted(schema["properties"]["mode"]["enum"]), expected)

    def test_valid_run_manifest_passes(self):
        validate_run_manifest(dict(VALID_MANIFEST))

    def test_run_manifest_missing_required_key_fails(self):
        manifest = dict(VALID_MANIFEST)
        del manifest["priority_counts"]
        with self.assertRaises(ValidationError):
            validate_run_manifest(manifest)

    def test_run_manifest_priority_counts_require_all_priorities(self):
        manifest = dict(VALID_MANIFEST)
        manifest["priority_counts"] = {}
        with self.assertRaises(ValidationError):
            validate_run_manifest(manifest)

    def test_run_manifest_schema_requires_priority_counts_keys(self):
        schema = json.loads(RUN_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$defs"]["priority_counts"]["required"],
            ["P0", "P1", "P2", "P3", "no_change"],
        )

    def test_valid_audit_run_pair_passes(self):
        validate_audit_run_pair([dict(VALID_ROW)], dict(VALID_MANIFEST))

    def test_empty_audit_run_pair_passes_with_zero_counts(self):
        manifest = dict(VALID_MANIFEST)
        manifest["run_id"] = "empty-run"
        manifest["total_notes"] = 0
        manifest["row_status_counts"] = {
            "complete": 0,
            "reused_cache": 0,
            "error": 0,
            "skipped": 0,
        }
        manifest["priority_counts"] = {
            "P0": 0,
            "P1": 0,
            "P2": 0,
            "P3": 0,
            "no_change": 0,
        }

        validate_audit_run_pair([], manifest)

    def test_audit_run_pair_rejects_mismatched_run_id(self):
        row = dict(VALID_ROW)
        row["run_id"] = "other-run"
        with self.assertRaises(ValidationError):
            validate_audit_run_pair([row], dict(VALID_MANIFEST))

    def test_audit_run_pair_rejects_total_notes_mismatch(self):
        manifest = dict(VALID_MANIFEST)
        manifest["total_notes"] = 2
        with self.assertRaises(ValidationError):
            validate_audit_run_pair([dict(VALID_ROW)], manifest)

    def test_audit_run_pair_rejects_row_status_counts_mismatch(self):
        manifest = dict(VALID_MANIFEST)
        manifest["row_status_counts"] = {
            "complete": 0,
            "reused_cache": 1,
            "error": 0,
            "skipped": 0,
        }
        with self.assertRaises(ValidationError):
            validate_audit_run_pair([dict(VALID_ROW)], manifest)

    def test_audit_run_pair_rejects_priority_counts_mismatch(self):
        manifest = dict(VALID_MANIFEST)
        manifest["priority_counts"] = {
            "P0": 0,
            "P1": 1,
            "P2": 0,
            "P3": 0,
            "no_change": 0,
        }
        with self.assertRaises(ValidationError):
            validate_audit_run_pair([dict(VALID_ROW)], manifest)

    def test_jsonl_file_validation_counts_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            path.write_text(json.dumps(VALID_ROW) + "\n", encoding="utf-8")
            result = validate_jsonl_file(path, default_scan=True)
            self.assertEqual(result.valid_rows, 1)

    def test_jsonl_non_object_row_includes_line_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            path.write_text("1\n", encoding="utf-8")
            with self.assertRaises(ValidationError) as context:
                validate_jsonl_file(path, default_scan=True)
            self.assertIn(":1:", str(context.exception))

    def test_jsonl_malformed_line_includes_line_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaises(ValidationError) as context:
                validate_jsonl_file(path, default_scan=True)
            self.assertIn(":1:", str(context.exception))

    def test_jsonl_blank_lines_do_not_count_as_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            path.write_text("\n" + json.dumps(VALID_ROW) + "\n\n", encoding="utf-8")
            result = validate_jsonl_file(path, default_scan=True)
            self.assertEqual(result.valid_rows, 1)

    def test_cli_validation_error_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            path.write_text("1\n", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(sys, "argv", ["validate_jsonl", str(path)]):
                with patch("sys.stderr", stderr):
                    result = main()
            self.assertEqual(result, 1)
            self.assertIn(":1:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_module_missing_file_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.jsonl"
            result = subprocess.run(
                [sys.executable, "-m", "shared.scripts.validate_jsonl", str(path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.strip())
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_script_missing_file_returns_nonzero_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.jsonl"
            result = subprocess.run(
                [sys.executable, "shared/scripts/validate_jsonl.py", str(path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.strip())
            self.assertNotIn("Traceback", result.stderr)

    def test_cli_non_default_scan_accepts_skipped_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = dict(VALID_ROW)
            row["row_status"] = "skipped"
            path = Path(tmp) / "audit.jsonl"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "shared.scripts.validate_jsonl", str(path), "--non-default-scan"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "valid_rows=1")
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
