import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.base_generation import render_base


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_JSONL = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"
GOLDEN_BASE = REPO_ROOT / "tests" / "golden" / "fixture-audit.base"


class BaseGenerationTest(unittest.TestCase):
    def test_render_base_includes_required_views_and_source_jsonl(self):
        base = render_base(str(AUDIT_JSONL))

        self.assertIn("source_jsonl", base)
        self.assertIn(str(AUDIT_JSONL), base)
        for view_name in [
            "All Audited Notes",
            "P0 Critical",
            "P1 High Impact",
            "P2 Improvements",
            "P3 Polish",
            "Clean Notes",
            "Factual Risk",
            "Multi-Note Split Candidates",
            "Missing Parent Candidates",
            "Duplicate Or Overlap Candidates",
        ]:
            self.assertIn(f'name: "{view_name}"', base)
        self.assertIn('file.path == "Atomic Notes/202601010103 Multi note bundle.md"', base)
        self.assertIn('file.path == "Atomic Notes/202601010105 Missing parent note.md"', base)
        self.assertIn('file.path == "Atomic Notes/202601010109 Duplicate candidate note.md"', base)

    def test_render_base_escapes_quoted_note_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            jsonl_path = Path(tmp) / "audit.jsonl"
            note_path = 'Atomic Notes/Quoted "Idea" note.md'
            jsonl_path.write_text(
                json.dumps(
                    {
                        "note_path": note_path,
                        "priority": "P3",
                        "clean": False,
                        "factual_risk": False,
                        "fact_check_required": False,
                        "findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            base = render_base(str(jsonl_path))

        self.assertIn(f"file.path == {json.dumps(note_path)}", base)
        self.assertNotIn('file.path == "Atomic Notes/Quoted "Idea" note.md"', base)

    def test_rendered_fixture_matches_golden_base(self):
        base = render_base("tests/golden/fixture-audit.jsonl")

        self.assertEqual(base, GOLDEN_BASE.read_text(encoding="utf-8"))

    def test_generate_base_writes_base_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "bases" / "audit.base"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_base",
                    "--jsonl",
                    str(AUDIT_JSONL),
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
            self.assertIn('name: "All Audited Notes"', output.read_text(encoding="utf-8"))

    def test_generate_base_rejects_invalid_jsonl_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid_jsonl = Path(tmp) / "invalid.jsonl"
            invalid_jsonl.write_text('{"note_path": "Atomic Notes/Invalid.md"}\n', encoding="utf-8")
            output = Path(tmp) / "audit.base"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.generate_base",
                    "--jsonl",
                    str(invalid_jsonl),
                    "--output",
                    str(output),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())
            self.assertIn(str(invalid_jsonl), result.stderr)

    def test_generate_base_supports_direct_script_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "direct-audit.base"
            script = REPO_ROOT / "shared" / "scripts" / "generate_base.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--jsonl",
                    str(AUDIT_JSONL),
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


if __name__ == "__main__":
    unittest.main()
