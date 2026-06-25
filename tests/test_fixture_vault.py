import contextlib
import io
import tempfile
from pathlib import Path
import unittest

from shared.scripts.make_fixture_vault import create_fixture_vault, main


class FixtureVaultTest(unittest.TestCase):
    def test_fixture_contains_expected_folders_and_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = create_fixture_vault(Path(tmp) / "tiny-vault")
            self.assertTrue((root / "Atomic Notes").is_dir())
            self.assertTrue((root / "Structure Notes").is_dir())
            notes = sorted((root / "Atomic Notes").glob("*.md"))
            self.assertGreaterEqual(len(notes), 9)
            names = {note.name for note in notes}
            self.assertIn("202601010101 Clean DAE note.md", names)
            self.assertIn("202601010103 Multi note bundle.md", names)
            self.assertIn("202601010110 Reference and sources note.md", names)

    def test_main_accepts_target_and_prints_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tiny-vault"
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                return_code = main(target)

            self.assertEqual(return_code, 0)
            self.assertIn(str(target), stdout.getvalue())
            self.assertTrue((target / "Atomic Notes").is_dir())


if __name__ == "__main__":
    unittest.main()
