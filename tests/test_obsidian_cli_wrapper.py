import contextlib
import io
import unittest
from unittest.mock import patch

from shared.scripts.obsidian_adapter import CommandResult
from shared.scripts import obsidian_cli


class ObsidianCliWrapperTest(unittest.TestCase):
    def test_wrapper_forwards_args_to_adapter(self):
        calls = []

        class FakeObsidianAdapter:
            def __init__(self, binary: str) -> None:
                calls.append(("binary", binary))

            def run(self, args: list[str]) -> CommandResult:
                calls.append(("args", args))
                return CommandResult(ok=True, stdout="=> 42\n", stderr="", returncode=0)

        stdout = io.StringIO()
        with patch("shared.scripts.obsidian_cli.ObsidianAdapter", FakeObsidianAdapter):
            with contextlib.redirect_stdout(stdout):
                return_code = obsidian_cli.main(["vault=jason-obsidian", "eval", "code=app.vault.getFiles().length"])

        self.assertEqual(return_code, 0)
        self.assertEqual(stdout.getvalue(), "=> 42\n")
        self.assertEqual(calls[0], ("binary", "obsidian-cli"))
        self.assertEqual(calls[1], ("args", ["vault=jason-obsidian", "eval", "code=app.vault.getFiles().length"]))

    def test_wrapper_supports_binary_override_and_separator(self):
        calls = []

        class FakeObsidianAdapter:
            def __init__(self, binary: str) -> None:
                calls.append(("binary", binary))

            def run(self, args: list[str]) -> CommandResult:
                calls.append(("args", args))
                return CommandResult(ok=True, stdout="", stderr="", returncode=0)

        with patch("shared.scripts.obsidian_cli.ObsidianAdapter", FakeObsidianAdapter):
            return_code = obsidian_cli.main(["--obsidian-binary", "/tmp/obsidian-cli", "--", "--copy", "help"])

        self.assertEqual(return_code, 0)
        self.assertEqual(calls[0], ("binary", "/tmp/obsidian-cli"))
        self.assertEqual(calls[1], ("args", ["--copy", "help"]))

    def test_wrapper_prints_sandbox_hint_on_attach_failure(self):
        class FakeObsidianAdapter:
            def __init__(self, binary: str) -> None:
                self.binary = binary

            def run(self, args: list[str]) -> CommandResult:
                return CommandResult(
                    ok=False,
                    stdout="",
                    stderr="The CLI is unable to find Obsidian. Please make sure Obsidian is running and try again.\n",
                    returncode=1,
                )

        stderr = io.StringIO()
        with patch("shared.scripts.obsidian_cli.ObsidianAdapter", FakeObsidianAdapter):
            with contextlib.redirect_stderr(stderr):
                return_code = obsidian_cli.main(["help"])

        self.assertEqual(return_code, 1)
        self.assertIn("approved unsandboxed context", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
