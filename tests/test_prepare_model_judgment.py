import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.model_prompt import render_model_judgment_prompt
from shared.scripts.prepare_model_judgment import (
    prepare_collector_input,
    render_model_judgment_request,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"
FIXTURE_AUDIT = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"
NOTE_PATH = (
    "Atomic Notes/202601010101 A clean atomic note explains one durable idea in plain language "
    "and keeps the claim small enough to test against examples.md"
)


class PrepareModelJudgmentTest(unittest.TestCase):
    def test_render_model_judgment_request_includes_prompt_and_note(self):
        request = render_model_judgment_request(FIXTURE_VAULT, NOTE_PATH)

        self.assertTrue(request.startswith(render_model_judgment_prompt().rstrip()))
        self.assertIn(f"Use this exact `note_path`: `{NOTE_PATH}`.", request)
        self.assertIn("Content SHA-256:", request)
        self.assertIn("NOTE_CONTENT_START", request)
        self.assertIn("A clean atomic note explains one durable idea", request)
        self.assertIn("NOTE_CONTENT_END", request)

    def test_render_model_judgment_request_rejects_path_traversal(self):
        with self.assertRaises(OSError):
            render_model_judgment_request(FIXTURE_VAULT, "../outside.md")

    def test_prepare_collector_input_selects_one_validated_audit_row(self):
        collector_input = prepare_collector_input(FIXTURE_AUDIT, NOTE_PATH)

        rows = [json.loads(line) for line in collector_input.splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["note_path"], NOTE_PATH)
        self.assertEqual(rows[0]["prompt_version"], "1.0.2")

    def test_cli_writes_output_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "requests" / "judgment.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.prepare_model_judgment",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--note-path",
                    NOTE_PATH,
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertTrue(output.exists())
            self.assertIn("NOTE_CONTENT_START", output.read_text(encoding="utf-8"))

    def test_cli_rejects_path_traversal_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "shared.scripts.prepare_model_judgment",
                "--vault",
                str(FIXTURE_VAULT),
                "--note-path",
                "../outside.md",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("note path must stay inside vault", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_cli_writes_single_note_collector_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "collector" / "example-audit.jsonl"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.prepare_model_judgment",
                    "--vault",
                    str(FIXTURE_VAULT),
                    "--note-path",
                    NOTE_PATH,
                    "--audit-jsonl",
                    str(FIXTURE_AUDIT),
                    "--collector-input",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(output))
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["note_path"] for row in rows], [NOTE_PATH])


if __name__ == "__main__":
    unittest.main()
