import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

from shared.scripts.remediation import (
    RemediationError,
    build_dry_run_manifest,
    validate_plan,
)
from shared.scripts.split_note import propose_split


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "shared" / "schemas" / "remediation-plan.schema.json"

APPROVED_PLAN = {
    "plan_version": "1.0.0",
    "audit_run_id": "run-1",
    "mode": "split-multi-note",
    "operations": [
        {
            "note_path": "Atomic Notes/202601010103 Multi note bundle.md",
            "operation": "split",
            "priority": "P0",
            "approved": True,
            "delete_original": True,
            "proposed_outputs": [
                {
                    "note_path": "Atomic Notes/202601010110 First bundled idea.md",
                    "content": "# First bundled idea\n",
                }
            ],
        }
    ],
}


class RemediationTest(unittest.TestCase):
    def test_unapproved_destructive_plan_fails(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [dict(APPROVED_PLAN["operations"][0], approved=False)]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_destructive_plan_requires_destructive_flag(self):
        with self.assertRaises(RemediationError):
            validate_plan(APPROVED_PLAN, destructive_allowed=False)

    def test_split_requires_delete_original_true(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [dict(APPROVED_PLAN["operations"][0], delete_original=False)]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_malformed_operations_fail_without_crashing(self):
        plan = dict(APPROVED_PLAN, operations=["not an object"])

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_legacy_operation_type_delete_fails_closed(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [{"operation_type": "delete", "note_path": "Atomic Notes/Old.md"}]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=False)

    def test_missing_operation_fails_closed(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [{"note_path": "Atomic Notes/Missing.md"}]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_non_string_operation_fails_closed(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [{"operation": ["delete"], "note_path": "Atomic Notes/List.md"}]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_unknown_operation_fails_closed(self):
        plan = dict(APPROVED_PLAN)
        plan["operations"] = [{"operation": "archive", "note_path": "Atomic Notes/Unknown.md"}]

        with self.assertRaises(RemediationError):
            validate_plan(plan, destructive_allowed=True)

    def test_split_requires_proposed_outputs(self):
        for operation in (
            dict(APPROVED_PLAN["operations"][0], proposed_outputs=[]),
            {key: value for key, value in APPROVED_PLAN["operations"][0].items() if key != "proposed_outputs"},
        ):
            with self.subTest(operation=operation):
                plan = dict(APPROVED_PLAN)
                plan["operations"] = [operation]

                with self.assertRaises(RemediationError):
                    validate_plan(plan, destructive_allowed=True)

    def test_dry_run_manifest_records_operations(self):
        validate_plan(APPROVED_PLAN, destructive_allowed=True)
        manifest = build_dry_run_manifest(APPROVED_PLAN)

        self.assertEqual(manifest["schema_version"], "1.0.0")
        self.assertEqual(manifest["audit_run_id"], "run-1")
        self.assertEqual(manifest["operation_count"], 1)
        self.assertEqual(manifest["mode"], "split-multi-note")
        self.assertEqual(manifest["operations"], APPROVED_PLAN["operations"])
        self.assertIsNot(manifest["operations"], APPROVED_PLAN["operations"])
        self.assertFalse(manifest["executed"])

    def test_propose_split_detects_multiple_headings(self):
        markdown = "# First idea\n\nBody.\n\n# Second/idea\n\nBody.\n"
        proposal = propose_split("Atomic Notes/Bundle.md", markdown)

        self.assertEqual(proposal["source_note_path"], "Atomic Notes/Bundle.md")
        self.assertEqual(proposal["operation"], "split")
        self.assertEqual(proposal["delete_original"], True)
        self.assertEqual(
            proposal["proposed_outputs"],
            [
                {
                    "note_path": "Atomic Notes/First idea.md",
                    "content": "# First idea\n\nBody.\n",
                },
                {
                    "note_path": "Atomic Notes/Second-idea.md",
                    "content": "# Second/idea\n\nBody.\n",
                },
            ],
        )

    def test_propose_split_ignores_fenced_code_headings(self):
        markdown = """# Real idea

Body.

```markdown
# Not a note heading
```

More body.

# Second idea

Body.
"""
        proposal = propose_split("Atomic Notes/Bundle.md", markdown)

        self.assertEqual(len(proposal["proposed_outputs"]), 2)
        self.assertEqual(proposal["proposed_outputs"][0]["note_path"], "Atomic Notes/Real idea.md")
        self.assertIn("# Not a note heading", proposal["proposed_outputs"][0]["content"])
        self.assertEqual(proposal["proposed_outputs"][1]["note_path"], "Atomic Notes/Second idea.md")

    def test_propose_split_ignores_frontmatter_and_html_comment_headings(self):
        markdown = """---
# Not frontmatter heading
---

<!--
# Not comment heading
-->

# Real idea

Body.
"""
        proposal = propose_split("Atomic Notes/Bundle.md", markdown)

        self.assertEqual(
            proposal["proposed_outputs"],
            [
                {
                    "note_path": "Atomic Notes/Real idea.md",
                    "content": "# Real idea\n\nBody.\n",
                }
            ],
        )

    def test_propose_split_without_top_level_heading_does_not_delete_original(self):
        proposal = propose_split("Atomic Notes/Bundle.md", "## Nested only\n\nBody.\n")

        self.assertEqual(proposal["delete_original"], False)
        self.assertEqual(proposal["proposed_outputs"], [])

    def test_remediate_notes_cli_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = Path(tmp) / "plan.json"
            manifest_path = Path(tmp) / "out" / "manifest.json"
            plan_path.write_text(json.dumps(APPROVED_PLAN), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.remediate_notes",
                    "--plan",
                    str(plan_path),
                    "--manifest",
                    str(manifest_path),
                    "--destructive-allowed",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "operation_count=1")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["operation_count"], 1)
            self.assertFalse(manifest["executed"])

    def test_remediate_notes_cli_rejects_unapproved_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = dict(APPROVED_PLAN)
            plan["operations"] = [dict(APPROVED_PLAN["operations"][0], approved=False)]
            plan_path = Path(tmp) / "plan.json"
            manifest_path = Path(tmp) / "manifest.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.remediate_notes",
                    "--plan",
                    str(plan_path),
                    "--manifest",
                    str(manifest_path),
                    "--destructive-allowed",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(manifest_path.exists())
            self.assertIn("requires approval", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_remediate_notes_cli_rejects_non_string_operation_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = dict(APPROVED_PLAN)
            plan["operations"] = [{"operation": ["delete"], "note_path": "Atomic Notes/List.md"}]
            plan_path = Path(tmp) / "plan.json"
            manifest_path = Path(tmp) / "manifest.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "shared.scripts.remediate_notes",
                    "--plan",
                    str(plan_path),
                    "--manifest",
                    str(manifest_path),
                    "--destructive-allowed",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(manifest_path.exists())
            self.assertIn("must state operation", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_schema_uses_operation_not_operation_type_as_ssot(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["$id"], "https://networked-thinking.dev/schemas/remediation-plan.schema.json")
        self.assertNotIn("$defs", schema)
        self.assertNotIn("operation_type", json.dumps(schema))
        self.assertEqual(schema["properties"]["operations"]["items"], {"type": "object"})


if __name__ == "__main__":
    unittest.main()
