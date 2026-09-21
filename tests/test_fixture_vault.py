import contextlib
import io
import json
import tempfile
from pathlib import Path
import unittest

from shared.scripts.make_fixture_vault import create_fixture_vault, main


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKED_IN_VAULT = REPO_ROOT / "tests" / "fixtures" / "tiny-vault"
GOLDEN_AUDIT = REPO_ROOT / "tests" / "golden" / "fixture-audit.jsonl"

TAB_DECAYED_NOTE = "Atomic Notes/202601010111 Tab decayed equation note.md"
NEWLINE_DECAYED_NOTE = "Atomic Notes/202601010112 Newline decayed equation note.md"
QUOTED_CONTROL_CHARACTER_NOTE = (
    "Atomic Notes/202601010113 A tab inside a fenced code block or a table cell is "
    "quoted data rather than a command that decayed into it.md"
)


def golden_rows_by_note_path() -> dict[str, dict[str, object]]:
    rows = [
        json.loads(line)
        for line in GOLDEN_AUDIT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {str(row["note_path"]): row for row in rows}


def relative_markdown_files(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.md"))
    }


class FixtureVaultTest(unittest.TestCase):
    def test_fixture_contains_expected_folders_and_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = create_fixture_vault(Path(tmp) / "tiny-vault")
            self.assertTrue((root / "Atomic Notes").is_dir())
            self.assertTrue((root / "Structure Notes").is_dir())
            notes = sorted((root / "Atomic Notes").glob("*.md"))
            self.assertGreaterEqual(len(notes), 9)
            names = {note.name for note in notes}
            self.assertIn(
                "202601010101 A clean atomic note explains one durable idea in plain language "
                "and keeps the claim small enough to test against examples.md",
                names,
            )
            self.assertIn("202601010103 Multi note bundle.md", names)
            self.assertIn(
                "202601010110 A source-backed atomic note keeps one durable idea in DAE form "
                "and adds optional trailing sections for connections and provenance.md",
                names,
            )

    def test_main_accepts_target_and_prints_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tiny-vault"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                return_code = main(target)

            self.assertEqual(return_code, 0)
            self.assertIn(str(target), stdout.getvalue())
            self.assertTrue((target / "Atomic Notes").is_dir())

    def test_checked_in_vault_matches_the_generator(self):
        """The goldens are audited from the checked-in copy, not from the generator.

        So a generator edit that never reaches `tests/fixtures/tiny-vault`
        leaves the committed goldens describing notes no longer in the source.
        """
        with tempfile.TemporaryDirectory() as tmp:
            generated = create_fixture_vault(Path(tmp) / "tiny-vault")

            self.assertEqual(
                relative_markdown_files(CHECKED_IN_VAULT),
                relative_markdown_files(generated),
            )

    def test_golden_reports_decayed_commands_only_where_they_stand_unquoted(self):
        rows = golden_rows_by_note_path()

        tab_findings = {
            finding["code"]: finding["message"]
            for finding in rows[TAB_DECAYED_NOTE]["findings"]
        }
        newline_findings = {
            finding["code"]: finding["message"]
            for finding in rows[NEWLINE_DECAYED_NOTE]["findings"]
        }
        quoted_codes = {
            finding["code"] for finding in rows[QUOTED_CONTROL_CHARACTER_NOTE]["findings"]
        }

        self.assertIn(r"\times", tab_findings["decayed_latex_command"])
        self.assertIn(r"\neq", newline_findings["decayed_latex_command"])
        self.assertNotIn("decayed_latex_command", quoted_codes)


if __name__ == "__main__":
    unittest.main()
