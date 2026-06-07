import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from shared.scripts.collect_model_judgments import (
    collect_model_judgments,
    parse_model_output,
    render_batch_prompt,
)
from shared.scripts.schema_validation import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"
AUDIT_JSONL = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"


def load_fixture_rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in AUDIT_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def judgment_for(note_path: str, *, findings: list[dict[str, object]] | None = None) -> dict[str, object]:
    factual_risk = any(finding.get("code") == "factual_risk" for finding in findings or [])
    return {
        "schema_version": "1.0.0",
        "note_path": note_path,
        "dimension_adjustments": {},
        "findings": findings or [],
        "factual_risk": factual_risk,
        "factual_risk_reason": "Synthetic factual risk reason." if factual_risk else None,
        "fact_check_required": factual_risk,
        "evidence": [],
    }


def jsonl_for(judgments: list[dict[str, object]]) -> str:
    return "\n".join(json.dumps(judgment, sort_keys=True) for judgment in judgments) + "\n"


class FakeRunner:
    def __init__(self, outputs: list[str]):
        self.outputs = outputs
        self.prompts: list[str] = []

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        if not self.outputs:
            raise AssertionError("fake runner has no output left")
        self.prompts.append(prompt)
        output_path.write_text(self.outputs.pop(0), encoding="utf-8")
        stdout_path.write_text("fake stdout", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")


class CollectModelJudgmentsTest(unittest.TestCase):
    def test_parse_model_output_accepts_jsonl_json_array_and_fence(self):
        rows = load_fixture_rows()
        judgments = [judgment_for(str(row["note_path"])) for row in rows[:2]]

        self.assertEqual(parse_model_output(jsonl_for(judgments)), judgments)
        self.assertEqual(parse_model_output(json.dumps(judgments)), judgments)
        self.assertEqual(parse_model_output(f"```jsonl\n{jsonl_for(judgments)}```"), judgments)

    def test_parse_model_output_rejects_non_object_line(self):
        with self.assertRaises(ValidationError):
            parse_model_output("[1]\n")

    def test_render_batch_prompt_contains_exact_note_paths_and_jsonl_instruction(self):
        rows = load_fixture_rows()[:2]

        prompt = render_batch_prompt(FIXTURE_VAULT, rows)

        self.assertIn("Return strict JSONL only", prompt)
        self.assertIn(str(rows[0]["note_path"]), prompt)
        self.assertIn(str(rows[1]["content_hash"]), prompt)
        self.assertIn("NOTE_CONTENT_START", prompt)

    def test_collect_model_judgments_writes_valid_output(self):
        rows = load_fixture_rows()[:3]
        judgments = [judgment_for(str(row["note_path"])) for row in rows]
        runner = FakeRunner([jsonl_for(judgments)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=3,
                    max_chars=100_000,
                    limit=3,
                    runner=runner,
                )

            self.assertEqual(count, 3)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 3)
            self.assertEqual(len(runner.prompts), 1)

    def test_collect_model_judgments_resumes_existing_output(self):
        rows = load_fixture_rows()[:3]
        completed = judgment_for(str(rows[0]["note_path"]))
        remaining = [judgment_for(str(row["note_path"])) for row in rows[1:]]
        runner = FakeRunner([jsonl_for(remaining)])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([completed]), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=3,
                    max_chars=100_000,
                    limit=3,
                    runner=runner,
                )

            self.assertEqual(count, 3)
            self.assertNotIn(str(rows[0]["note_path"]), runner.prompts[0])

    def test_collect_model_judgments_splits_and_retries_invalid_batch(self):
        rows = load_fixture_rows()[:2]
        bad_batch = jsonl_for(
            [
                judgment_for("Atomic Notes/Wrong.md"),
                judgment_for(str(rows[1]["note_path"])),
            ]
        )
        first = jsonl_for([judgment_for(str(rows[0]["note_path"]))])
        second = jsonl_for([judgment_for(str(rows[1]["note_path"]))])
        runner = FakeRunner([bad_batch, first, second])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            with redirect_stdout(io.StringIO()):
                count = collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=2,
                    max_chars=100_000,
                    limit=2,
                    runner=runner,
                )

            self.assertEqual(count, 2)
            self.assertEqual(len(runner.prompts), 3)

    def test_duplicate_existing_judgment_fails(self):
        rows = load_fixture_rows()[:1]
        duplicate = judgment_for(str(rows[0]["note_path"]))
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([duplicate, duplicate]), encoding="utf-8")

            with self.assertRaises(ValidationError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )

    def test_existing_judgment_outside_selected_rows_fails(self):
        rows = load_fixture_rows()[:2]
        outside_selected_rows = judgment_for(str(rows[1]["note_path"]))
        runner = FakeRunner([])

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output = tmp_path / "model-judgments.jsonl"
            output.write_text(jsonl_for([outside_selected_rows]), encoding="utf-8")

            with self.assertRaises(ValidationError):
                collect_model_judgments(
                    vault_root=FIXTURE_VAULT,
                    audit_jsonl=AUDIT_JSONL,
                    output_jsonl=output,
                    raw_dir=tmp_path / "raw",
                    max_notes=1,
                    max_chars=100_000,
                    limit=1,
                    runner=runner,
                )


if __name__ == "__main__":
    unittest.main()
