from pathlib import Path
import tempfile
import textwrap
import unittest

from shared.scripts.sync_skill_artifacts import (
    ARTIFACT_SPECS,
    ROOT,
    SkillArtifactSpec,
    find_stale_shared_references,
    render_markdown_text,
    render_script_text,
    sync_artifacts,
)


class SkillArtifactSyncTest(unittest.TestCase):
    def test_specs_include_required_runtime_files(self):
        self.assertEqual(
            ARTIFACT_SPECS["atomic-note"].references,
            ("doctrine.md", "remediation-context.md"),
        )
        self.assertEqual(
            ARTIFACT_SPECS["atomic-note"].scripts,
            ("obsidian_adapter.py", "obsidian_cli.py", "verify_anki_notes.py"),
        )
        audit = ARTIFACT_SPECS["atomic-note-audit"]
        self.assertIn("model-judgment.schema.json", audit.schemas)
        self.assertIn("audit_notes.py", audit.scripts)
        self.assertIn("obsidian_cli.py", audit.scripts)
        self.assertNotIn("make_fixture_vault.py", audit.scripts)
        self.assertNotIn("verify_install_commands.py", audit.scripts)

    def test_render_markdown_rewrites_shared_paths(self):
        source = textwrap.dedent(
            """\
            Load `../../shared/references/doctrine.md`.
            Run `python3 -m shared.scripts.audit_notes --help`.
            Validate `shared/schemas/model-judgment.schema.json`.
            See `shared/scripts/finding_codes.py`.
            """
        )

        rendered = render_markdown_text(source)

        self.assertIn("`references/doctrine.md`", rendered)
        self.assertIn("`python3 scripts/audit_notes.py --help`", rendered)
        self.assertIn("`schemas/model-judgment.schema.json`", rendered)
        self.assertIn("`scripts/finding_codes.py`", rendered)
        self.assertEqual(find_stale_shared_references(rendered), [])

    def test_render_script_rewrites_imports(self):
        source = textwrap.dedent(
            """\
            from shared.scripts.schema_validation import ValidationError
            from shared.scripts.scoring import compute_clean
            """
        )

        rendered = render_script_text(source)

        self.assertIn("from schema_validation import ValidationError", rendered)
        self.assertIn("from scoring import compute_clean", rendered)
        self.assertEqual(find_stale_shared_references(rendered), [])

    def test_find_stale_shared_references_reports_all_forms(self):
        text = " ".join(
            [
                "../../shared/references/doctrine.md",
                "../shared/references/doctrine.md",
                "shared/scripts/audit_notes.py",
                "shared.scripts.audit_notes",
                "from shared import scripts",
            ]
        )

        findings = find_stale_shared_references(text)

        self.assertEqual(
            findings,
            [
                "../../shared",
                "../shared",
                "shared/",
                "shared.scripts",
                "from shared",
            ],
        )

    def test_sync_check_reports_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "shared/references").mkdir(parents=True)
            (root / "shared/schemas").mkdir(parents=True)
            (root / "shared/scripts").mkdir(parents=True)
            (root / "skills/demo").mkdir(parents=True)
            (root / "skills/demo/SKILL.md").write_text(
                "---\nname: demo\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            (root / "shared/references/doctrine.md").write_text("doctrine\n", encoding="utf-8")
            spec = {
                "demo": SkillArtifactSpec(
                    name="demo",
                    references=("doctrine.md",),
                    schemas=(),
                    scripts=(),
                )
            }

            errors = sync_artifacts(root=root, specs=spec, check=True)

            self.assertEqual(
                errors,
                ["skills/demo/references/doctrine.md is missing or out of sync"],
            )
            self.assertFalse((root / "skills/demo/references/doctrine.md").exists())


if __name__ == "__main__":
    unittest.main()
