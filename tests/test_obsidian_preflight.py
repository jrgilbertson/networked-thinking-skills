import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shared.scripts.obsidian_adapter import (
    COMMAND_TIMEOUT_SECONDS,
    DEFAULT_OBSIDIAN_BINARY,
    TIMEOUT_RETURN_CODE,
    CommandResult,
    ObsidianAdapter,
    resolve_obsidian_binary,
)
from shared.scripts.preflight_obsidian import check_skill_paths, main


REQUIRED_SKILLS = ("obsidian-cli", "obsidian-markdown", "obsidian-bases")
REPO_ROOT = Path(__file__).resolve().parents[1]


def _create_required_skills(root: Path) -> None:
    for skill in REQUIRED_SKILLS:
        skill_dir = root / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")


class ObsidianPreflightTest(unittest.TestCase):
    def test_default_binary_uses_registered_obsidian_command(self):
        self.assertEqual(DEFAULT_OBSIDIAN_BINARY, "obsidian")

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

    def test_default_binary_falls_back_to_app_bundled_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = Path(tmp) / "obsidian-cli"
            cli.write_text("", encoding="utf-8")
            cli.chmod(0o755)

            with patch("shared.scripts.obsidian_adapter.shutil.which", return_value=None):
                with patch("shared.scripts.obsidian_adapter.MACOS_OBSIDIAN_CLI_PATH", cli):
                    resolved = resolve_obsidian_binary(DEFAULT_OBSIDIAN_BINARY)

        self.assertEqual(resolved, str(cli))

    def test_legacy_binary_name_falls_back_to_app_bundled_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            cli = Path(tmp) / "obsidian-cli"
            cli.write_text("", encoding="utf-8")
            cli.chmod(0o755)

            with patch("shared.scripts.obsidian_adapter.shutil.which", return_value=None):
                with patch("shared.scripts.obsidian_adapter.MACOS_OBSIDIAN_CLI_PATH", cli):
                    resolved = resolve_obsidian_binary("obsidian-cli")

        self.assertEqual(resolved, str(cli))

    def test_adapter_timeout_returns_failed_command_result(self):
        timeout = subprocess.TimeoutExpired(
            cmd=["/tmp/obsidian", "help"],
            timeout=COMMAND_TIMEOUT_SECONDS,
            output="partial output",
            stderr="partial error",
        )

        with patch("shared.scripts.obsidian_adapter.shutil.which", return_value="/tmp/obsidian"):
            with patch(
                "shared.scripts.obsidian_adapter.subprocess.run",
                side_effect=timeout,
            ) as run:
                result = ObsidianAdapter().help()

        self.assertFalse(result.ok)
        self.assertEqual(result.stdout, "partial output")
        self.assertIn("timed out", result.stderr)
        self.assertIn("partial error", result.stderr)
        self.assertEqual(result.returncode, TIMEOUT_RETURN_CODE)
        self.assertEqual(run.call_args.kwargs["timeout"], COMMAND_TIMEOUT_SECONDS)

    def test_resolver_uses_path_binary_when_local_shadow_is_not_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local_shadow = root / DEFAULT_OBSIDIAN_BINARY
            local_shadow.write_text("", encoding="utf-8")
            path_binary = root / "bin" / DEFAULT_OBSIDIAN_BINARY
            path_binary.parent.mkdir()
            path_binary.write_text("", encoding="utf-8")
            path_binary.chmod(0o755)
            previous_cwd = Path.cwd()

            try:
                os.chdir(root)
                with patch("shared.scripts.obsidian_adapter.shutil.which", return_value=str(path_binary)):
                    resolved = resolve_obsidian_binary(DEFAULT_OBSIDIAN_BINARY)
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(resolved, str(path_binary))

    def test_resolver_refuses_macos_gui_binary(self):
        gui_binary = "/Applications/Obsidian.app/Contents/MacOS/obsidian"

        with patch("shared.scripts.obsidian_adapter.shutil.which", return_value=gui_binary):
            with patch(
                "shared.scripts.obsidian_adapter.MACOS_OBSIDIAN_CLI_PATH",
                Path("/missing/obsidian-cli"),
            ):
                resolved = resolve_obsidian_binary("obsidian")

        self.assertIsNone(resolved)

    def test_resolver_refuses_symlink_to_macos_gui_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_binary = root / "Obsidian.app" / "Contents" / "MacOS" / "Obsidian"
            app_binary.parent.mkdir(parents=True)
            app_binary.write_text("", encoding="utf-8")
            shim = root / "bin" / "obsidian"
            shim.parent.mkdir()
            shim.symlink_to(app_binary)

            with patch("shared.scripts.obsidian_adapter.shutil.which", return_value=str(shim)):
                with patch(
                    "shared.scripts.obsidian_adapter.MACOS_OBSIDIAN_CLI_PATH",
                    root / "missing-obsidian-cli",
                ):
                    resolved = resolve_obsidian_binary("obsidian")

        self.assertIsNone(resolved)

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
