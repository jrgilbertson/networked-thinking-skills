import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shared.scripts.obsidian_adapter import DEFAULT_OBSIDIAN_BINARY, CommandResult, ObsidianAdapter
from shared.scripts.preflight_obsidian import check_skill_paths, main


REQUIRED_SKILLS = ("obsidian-cli", "obsidian-markdown", "obsidian-bases")
REPO_ROOT = Path(__file__).resolve().parents[1]


def _create_required_skills(root: Path) -> None:
    for skill in REQUIRED_SKILLS:
        skill_dir = root / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")


class ObsidianPreflightTest(unittest.TestCase):
    def test_missing_skills_fail_and_include_obsidian_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = check_skill_paths(Path(tmp))

        self.assertFalse(result.ok)
        self.assertIn("obsidian-cli", result.missing)

    def test_present_required_skill_dirs_with_skill_md_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)

            result = check_skill_paths(skills_root)

        self.assertTrue(result.ok)
        self.assertEqual(result.missing, [])

    def test_cli_missing_skills_returns_2_and_prints_missing_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                return_code = main(["--skills-root", tmp])

        self.assertEqual(return_code, 2)
        self.assertIn("missing_skills=", stdout.getvalue())
        self.assertIn("obsidian-cli", stdout.getvalue())

    def test_cli_present_skills_without_require_cli_returns_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                return_code = main(["--skills-root", str(skills_root)])

        self.assertEqual(return_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "obsidian_preflight=ok")

    def test_adapter_available_uses_shutil_which(self):
        with patch("shared.scripts.obsidian_adapter.shutil.which", return_value="/bin/example"):
            adapter = ObsidianAdapter(binary="example")

            self.assertTrue(adapter.available())

    def test_require_cli_missing_binary_returns_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                return_code = main(
                    [
                        "--skills-root",
                        str(skills_root),
                        "--require-cli",
                        "--obsidian-binary",
                        str(skills_root / "missing-obsidian"),
                    ]
                )

        self.assertEqual(return_code, 3)
        self.assertEqual(stdout.getvalue().strip(), "obsidian_cli=missing")

    def test_require_cli_defaults_to_obsidian_cli_binary(self):
        binaries = []

        class FakeObsidianAdapter:
            def __init__(self, binary: str = DEFAULT_OBSIDIAN_BINARY) -> None:
                binaries.append(binary)

            def available(self) -> bool:
                return True

            def help(self) -> CommandResult:
                return CommandResult(ok=True, stdout="", stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            stdout = io.StringIO()

            with patch("shared.scripts.preflight_obsidian.ObsidianAdapter", FakeObsidianAdapter):
                with contextlib.redirect_stdout(stdout):
                    return_code = main(
                        [
                            "--skills-root",
                            str(skills_root),
                            "--require-cli",
                        ]
                    )

        self.assertEqual(return_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "obsidian_preflight=ok")
        self.assertEqual(binaries, [DEFAULT_OBSIDIAN_BINARY])

    def test_require_cli_launch_oserror_returns_4(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            stdout = io.StringIO()

            with patch("shared.scripts.obsidian_adapter.shutil.which", return_value="/tmp/obsidian"):
                with patch(
                    "shared.scripts.obsidian_adapter.subprocess.run",
                    side_effect=OSError("cannot execute"),
                ):
                    with contextlib.redirect_stdout(stdout):
                        return_code = main(
                            [
                                "--skills-root",
                                str(skills_root),
                                "--require-cli",
                                "--obsidian-binary",
                                "obsidian",
                            ]
                        )

        self.assertEqual(return_code, 4)
        self.assertIn("obsidian_cli=unavailable", stdout.getvalue())
        self.assertIn("approved unsandboxed context", stdout.getvalue())

    def test_require_cli_help_nonzero_returns_4(self):
        class FakeObsidianAdapter:
            def __init__(self, binary: str = "obsidian") -> None:
                self.binary = binary

            def available(self) -> bool:
                return True

            def help(self) -> CommandResult:
                return CommandResult(ok=False, stdout="", stderr="failed", returncode=1)

        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            stdout = io.StringIO()

            with patch("shared.scripts.preflight_obsidian.ObsidianAdapter", FakeObsidianAdapter):
                with contextlib.redirect_stdout(stdout):
                    return_code = main(
                        [
                            "--skills-root",
                            str(skills_root),
                            "--require-cli",
                            "--obsidian-binary",
                            "fake-obsidian",
                        ]
                    )

        self.assertEqual(return_code, 4)
        self.assertIn("obsidian_cli=unavailable", stdout.getvalue())
        self.assertIn("local CLI socket", stdout.getvalue())

    def test_preflight_supports_direct_script_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp)
            _create_required_skills(skills_root)
            script = REPO_ROOT / "shared" / "scripts" / "preflight_obsidian.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--skills-root",
                    str(skills_root),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "obsidian_preflight=ok")


if __name__ == "__main__":
    unittest.main()
