import textwrap
import unittest

from shared.scripts.verify_install_commands import find_command_blocks, validate_doc


def command_block(
    runtime="codex-raw",
    status="verified-local",
    source="local CLI evidence",
    last_verified="2026-06-06",
    execution="temp home smoke test",
    reason=None,
    command='echo "install"',
):
    reason_line = f"reason: {reason}\n" if reason is not None else ""
    return (
        "<!-- install-command\n"
        f"runtime: {runtime}\n"
        f"status: {status}\n"
        f"source: {source}\n"
        f"last_verified: {last_verified}\n"
        f"execution: {execution}\n"
        f"{reason_line}"
        "-->\n"
        "```bash\n"
        f"{command}\n"
        "```\n"
    )


class InstallCommandVerifierTest(unittest.TestCase):
    def test_find_command_blocks_extracts_metadata_and_command(self):
        text = "Before\n" + command_block(command="mkdir -p \"$HOME/.agents/skills\"\ncp -R skills/atomic-note \"$HOME/.agents/skills/\"")

        blocks = find_command_blocks(text)

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].metadata["runtime"], "codex-raw")
        self.assertEqual(blocks[0].metadata["status"], "verified-local")
        self.assertEqual(blocks[0].metadata["last_verified"], "2026-06-06")
        self.assertIn("mkdir -p", blocks[0].command)
        self.assertIn("cp -R", blocks[0].command)

    def test_validate_doc_success(self):
        text = command_block(runtime="codex-raw") + command_block(runtime="claude-raw")

        self.assertEqual(validate_doc(text), [])

    def test_validate_doc_rejects_missing_key(self):
        text = textwrap.dedent(
            """\
            <!-- install-command
            runtime: codex-raw
            status: verified-local
            source: local CLI evidence
            last_verified: 2026-06-06
            -->
            ```bash
            echo "install"
            ```
            """
        )

        errors = validate_doc(text)

        self.assertTrue(any("missing required metadata: execution" in error for error in errors))

    def test_validate_doc_rejects_invalid_status(self):
        text = command_block(status="verified")

        errors = validate_doc(text)

        self.assertTrue(any("invalid status: verified" in error for error in errors))

    def test_validate_doc_rejects_bad_date(self):
        text = command_block(last_verified="2026-99-99")

        errors = validate_doc(text)

        self.assertTrue(any("invalid last_verified date: 2026-99-99" in error for error in errors))

    def test_validate_doc_rejects_duplicate_runtime(self):
        text = command_block(runtime="codex-raw") + command_block(runtime="codex-raw")

        errors = validate_doc(text)

        self.assertTrue(any("duplicate runtime: codex-raw" in error for error in errors))

    def test_validate_doc_rejects_blocked_status_without_reason(self):
        text = command_block(status="blocked-with-reason")

        errors = validate_doc(text)

        self.assertTrue(any("requires a non-empty reason" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
