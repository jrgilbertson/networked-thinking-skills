import base64
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from shared.scripts import remediate_notes
from shared.scripts.obsidian_adapter import (
    CommandResult,
    ObsidianAdapter,
    build_replace_in_note_code,
)
from shared.scripts.remediate_notes import execute_plan
from shared.scripts.remediation import (
    RemediationError,
    assert_repair_landed,
    build_dry_run_manifest,
    validate_executable_plan,
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


CORRUPTED_NOTE = "# Ratio\n\nThe product is $2\times2\times7$.\n"
CLEAN_NOTE = "# Ratio\n\nThe product is $2\\times2\\times7$.\n"
ATOB_PATTERN = re.compile(r'atob\("([A-Za-z0-9+/=]+)"\)')


def decode_like_obsidian_cli(argument: str) -> str:
    """Decode an argument the way the Obsidian CLI decodes ``content=``.

    The CLI expands ``\\t`` and ``\\n`` after shell parsing, which is the
    mechanism that corrupted the vault in the first place. The fake applies it
    to every argument rather than only to ``content=``, so a transport that
    survives here survives a decoder stricter than the real one.
    """
    return argument.replace("\\t", "\t").replace("\\n", "\n")


def payload_of(call: list[str]) -> dict:
    """Decode the payload out of a recorded call, as the app would."""
    code = decode_like_obsidian_cli(call[-1])
    return json.loads(base64.b64decode(ATOB_PATTERN.search(code).group(1)).decode("utf-8"))


class FakeObsidianApp(ObsidianAdapter):
    """Stands in for the running app, but runs the real transport payload.

    Only ``run`` is replaced, so every test exercises the production encoding
    and decoding. Notes are real files, so assertions can read real bytes.
    """

    def __init__(self, root: Path, sabotage=None) -> None:
        super().__init__()
        self.root = root
        self.sabotage = sabotage
        self.calls: list[list[str]] = []
        self.written: list[str] = []

    def run(self, args: list[str]) -> CommandResult:
        self.calls.append(list(args))
        decoded = [decode_like_obsidian_cli(argument) for argument in args]
        if decoded and decoded[0].startswith("vault="):
            decoded = decoded[1:]
        if len(decoded) != 2 or decoded[0] != "eval" or not decoded[1].startswith("code="):
            return CommandResult(ok=False, stdout="", stderr=f"unsupported call: {decoded}", returncode=2)

        match = ATOB_PATTERN.search(decoded[1])
        if match is None:
            return CommandResult(ok=False, stdout="", stderr="no base64 payload in eval code", returncode=2)
        payload = json.loads(base64.b64decode(match.group(1)).decode("utf-8"))

        path = self.root / payload["path"]
        if not path.is_file():
            return CommandResult(ok=False, stdout="", stderr=f"missing file: {payload['path']}", returncode=1)
        content = path.read_bytes().decode("utf-8")

        if payload["action"] == "read":
            encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
            return CommandResult(ok=True, stdout=f'=> "{encoded}"\n', stderr="", returncode=0)

        if payload["action"] == "replace":
            occurrences = content.count(payload["find"])
            if occurrences != payload["expected_occurrences"]:
                return CommandResult(ok=False, stdout="", stderr="occurrence count changed", returncode=1)
            updated = content.replace(payload["find"], payload["replace"])
            if self.sabotage is not None:
                updated = self.sabotage(payload["path"], updated)
            path.write_bytes(updated.encode("utf-8"))
            self.written.append(payload["path"])
            return CommandResult(ok=True, stdout=f"=> {occurrences}\n", stderr="", returncode=0)

        return CommandResult(ok=False, stdout="", stderr=f"unknown action: {payload['action']}", returncode=2)


def edit_operation(note_path: str, **overrides) -> dict:
    operation = {
        "operation": "edit",
        "note_path": note_path,
        "priority": "P1",
        "approved": True,
        "find": "\times",
        "replace": "\\times",
        "expected_occurrences": 2,
    }
    operation.update(overrides)
    return operation


def execute_plan_fixture(operations: list[dict], mode: str = "improve-in-place") -> dict:
    return {
        "plan_version": "1.0.0",
        "audit_run_id": "run-latex-1",
        "mode": mode,
        "operations": operations,
    }


class ExecutePathTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "Atomic Notes").mkdir(parents=True)

    def write_note(self, name: str, content: str = CORRUPTED_NOTE) -> str:
        note_path = f"Atomic Notes/{name}"
        (self.root / note_path).write_bytes(content.encode("utf-8"))
        return note_path

    def test_execute_refuses_edit_without_approval(self):
        note_path = self.write_note("Unapproved.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path, approved=False)])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("approval", str(raised.exception))
        self.assertEqual(adapter.calls, [])
        self.assertEqual((self.root / note_path).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_execute_refuses_occurrence_count_mismatch(self):
        note_path = self.write_note(
            "Single.md",
            "# Ratio\n\nThe product is $2\times7$.\n",
        )
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path, expected_occurrences=2)])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("occurrence", str(raised.exception))
        self.assertIn(note_path, str(raised.exception))
        self.assertEqual(adapter.written, [])
        self.assertIn(b"\times", (self.root / note_path).read_bytes())

    def test_execute_refuses_non_edit_operation_even_when_approved(self):
        note_path = self.write_note("Doomed.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [{"operation": "delete", "note_path": note_path, "approved": True}],
            mode="split-multi-note",
        )

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("delete", str(raised.exception))
        self.assertEqual(adapter.calls, [])
        self.assertTrue((self.root / note_path).is_file())

    def test_execute_applies_approved_edit_and_changes_only_the_match(self):
        note_path = self.write_note("Repairable.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path)])

        written = execute_plan(plan, adapter, vault="test-vault")

        self.assertEqual(written, [note_path])
        self.assertEqual((self.root / note_path).read_bytes(), CLEAN_NOTE.encode("utf-8"))

    def test_batch_writes_nothing_when_a_later_operation_is_unapproved(self):
        first = self.write_note("First.md")
        second = self.write_note("Second.md")
        third = self.write_note("Third.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [
                edit_operation(first),
                edit_operation(second, approved=False),
                edit_operation(third),
            ]
        )

        with self.assertRaises(RemediationError):
            execute_plan(plan, adapter, vault="test-vault")

        self.assertEqual(adapter.calls, [])
        for note_path in (first, second, third):
            self.assertEqual((self.root / note_path).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_replacement_backslash_reaches_disk_as_a_backslash(self):
        note_path = self.write_note("Backslash.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path)])

        execute_plan(plan, adapter, vault="test-vault")

        on_disk = (self.root / note_path).read_bytes()
        self.assertIn(b"\\times", on_disk)
        self.assertNotIn(b"\t", on_disk)

        write_calls = [call for call in adapter.calls if payload_of(call)["action"] == "replace"]
        self.assertEqual(len(write_calls), 1)
        # The argument the CLI would escape-decode carries no backslash at all,
        # so there is no `\t` left in it for the decoder to turn into a tab.
        self.assertNotIn("\\", "".join(write_calls[0]))
        self.assertEqual(payload_of(write_calls[0])["replace"], "\\times")

    def test_read_back_that_is_still_decayed_halts_the_batch(self):
        first = self.write_note("Good.md")
        second = self.write_note("Sabotaged.md")
        third = self.write_note("Untouched.md")

        def sabotage(path: str, updated: str) -> str:
            return CORRUPTED_NOTE if path == second else updated

        adapter = FakeObsidianApp(self.root, sabotage=sabotage)
        plan = execute_plan_fixture(
            [edit_operation(first), edit_operation(second), edit_operation(third)]
        )
        written: list[str] = []

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault", on_written=written.append)

        self.assertIn(second, str(raised.exception))
        self.assertEqual(written, [first, second])
        self.assertEqual((self.root / first).read_bytes(), CLEAN_NOTE.encode("utf-8"))
        self.assertEqual((self.root / third).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_replacement_equal_to_the_find_string_is_refused_before_any_write(self):
        """The likeliest authoring slip: `"\\times"` in JSON is a tab, not a command.

        A plan that forgets to double the backslash asks for a substitution
        that cannot change anything, and the note would be certified repaired
        while still corrupt.
        """
        note_path = self.write_note("NoOp.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path, replace="\times")])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("replacement", str(raised.exception))
        self.assertEqual(adapter.calls, [])
        self.assertEqual((self.root / note_path).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_replacement_containing_the_find_string_is_refused_before_any_write(self):
        note_path = self.write_note("Reintroduces.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture([edit_operation(note_path, replace="x\times")])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("replacement", str(raised.exception))
        self.assertEqual(adapter.calls, [])

    def test_replacement_carrying_a_control_character_is_refused_before_any_write(self):
        """A replacement may never carry the corruption this repair removes.

        The shapes below all read as clean to `decayed_latex_commands`, which
        masks code spans, table rows and tab-indented lines. That masking is
        right for a note and wrong for a bare fragment, whose leading tab or
        pipe means something else entirely once spliced mid-line. The gate
        therefore asks about raw control characters, not about commands.
        """
        cases = {
            "mid-string": ("\\times \theta", "U+0009"),
            "code-span-masked": ("`\theta`", "U+0009"),
            "leading-tab-masked": ("\theta", "U+0009"),
            "table-row-masked": ("|\theta", "U+0009"),
            "bare-carriage-return": ("\\times\r", "U+000D"),
            "injected-newline": ("\\times\nX", "U+000A"),
        }
        for label, (replace, codepoint) in cases.items():
            with self.subTest(case=label):
                note_path = self.write_note(f"Carrier-{label}.md")
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture([edit_operation(note_path, replace=replace)])

                with self.assertRaises(RemediationError) as raised:
                    execute_plan(plan, adapter, vault="test-vault")

                self.assertIn(codepoint, str(raised.exception))
                self.assertEqual(adapter.calls, [])
                self.assertEqual((self.root / note_path).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_replacement_carrying_a_line_breaking_or_invisible_character_is_refused(self):
        """Above U+007F sit the characters Python splits lines on.

        `decayed_latex_commands` reads the note with `str.splitlines()`, which
        breaks on U+0085, U+2028 and U+2029 where the app's `split("\\n")`
        does not. A replacement carrying one moves the detector's line
        boundaries and can push a decayed command into a skipped line.
        """
        for label, character in (
            ("line-separator", " "),
            ("paragraph-separator", " "),
            ("next-line", "\u0085"),
            ("c1-control", "\u0080"),
            ("zero-width-space", "​"),
            ("byte-order-mark", "﻿"),
        ):
            with self.subTest(case=label):
                note_path = self.write_note(f"Invisible-{label}.md")
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture(
                    [edit_operation(note_path, replace=f"\\times{character}")]
                )

                with self.assertRaises(RemediationError) as raised:
                    execute_plan(plan, adapter, vault="test-vault")

                self.assertIn("U+", str(raised.exception))
                self.assertEqual(adapter.calls, [])

    def test_replacement_that_is_not_the_exact_reconstruction_is_refused(self):
        """Close the masking vectors at the source, not at the read-back.

        A replacement must be its find string with the decay restored, and
        nothing else. Enumerating the characters that move a mask does not
        close this: backtick and table pipe were the first two, tilde fences,
        HTML comments and display-math delimiters are three more, and the next
        reader would have to guess whether the list is complete. Requiring the
        exact reconstruction has no list to be incomplete.

        The read-back check behind this one is set-based on command names, so
        it cannot see a write that masks one occurrence of a command while
        another occurrence of the same command stays visible. This rule can,
        because it never lets the note change in any other way.
        """
        cases = {
            "adds-a-backtick": ("\times", "\\times`"),
            "adds-a-table-pipe": ("\times", "|\\times"),
            "adds-a-backtick-fence": ("\times", "\\times```"),
            "adds-a-tilde-fence": ("\times", "~~~\\times"),
            "opens-an-html-comment": ("\times", "\\times<!--"),
            "toggles-display-math": ("\times", "$$\\times"),
            "removes-a-backtick": ("`\times", "\\times"),
            "adds-plain-text": ("\times", "\\times and more"),
        }
        for label, (find, replace) in cases.items():
            with self.subTest(case=label):
                note_path = self.write_note(f"Masking-{label}.md")
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture(
                    [edit_operation(note_path, find=find, replace=replace, expected_occurrences=1)]
                )

                with self.assertRaises(RemediationError) as raised:
                    execute_plan(plan, adapter, vault="test-vault")

                self.assertIn("decay restored", str(raised.exception))
                self.assertEqual(adapter.calls, [])

    def test_write_that_hides_one_occurrence_of_a_still_visible_command_is_refused(self):
        """The case the set-based concealment check structurally cannot see.

        Two `\\theta` occurrences, one visible and one already inside a code
        span. Adding a single backtick re-pairs every later backtick and flips
        which one is masked, so the command stays in `decayed_latex_commands`
        both before and after while a previously visible occurrence is hidden.
        """
        note = "# T\n\n$2\times7$ A \theta B `code` C \theta D\n"
        note_path = self.write_note("Flip.md", note)
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [edit_operation(note_path, replace="\\times`", expected_occurrences=1)]
        )

        with self.assertRaises(RemediationError):
            execute_plan(plan, adapter, vault="test-vault")

        self.assertEqual(adapter.calls, [])
        self.assertEqual((self.root / note_path).read_bytes(), note.encode("utf-8"))

    def test_correct_repair_is_not_refused_over_bytes_the_detector_never_counted(self):
        """Decayed bytes the detector always ignored were never signal.

        `\\to` is a tab and one letter, `\\neq` a newline and two, so the raw
        sequences turn up in ordinary prose and code. The detector skips them
        by its masking and by the guard that the character after the suffix
        must not be a letter. A check that reads raw bytes instead sees
        corruption everywhere and refuses correct repairs — and because the
        note is recorded before the write, it halts the batch after modifying
        it, accusing the tool of hiding what it just fixed.
        """
        cases = {
            "tab-indented-line-starting-o": (
                "# Map\n\nThe map $a\to b$ is total.\n\n\toutput = f(x)\n",
                "\to b$",
                "\\to b$",
                "# Map\n\nThe map $a\\to b$ is total.\n\n\toutput = f(x)\n",
            ),
            "prose-line-starting-eq": (
                "# Bound\n\nThe value is $a\neq b$ here.\n\nequation three is tight.\n",
                "\neq b$",
                "\\neq b$",
                "# Bound\n\nThe value is $a\\neq b$ here.\n\nequation three is tight.\n",
            ),
            "already-masked-table-row": (
                "# Sym\n\nIn prose $2\times7$ holds.\n\n| $2\times3$ | product |\n",
                "In prose $2\times7$",
                "In prose $2\\times7$",
                "# Sym\n\nIn prose $2\\times7$ holds.\n\n| $2\times3$ | product |\n",
            ),
        }
        for label, (note, find, replace, expected) in cases.items():
            with self.subTest(case=label):
                note_path = self.write_note(f"Legit-{label}.md", note)
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture(
                    [edit_operation(note_path, find=find, replace=replace, expected_occurrences=1)]
                )

                self.assertEqual(execute_plan(plan, adapter, vault="test-vault"), [note_path])
                self.assertEqual((self.root / note_path).read_bytes(), expected.encode("utf-8"))

    def test_write_that_conceals_another_decayed_command_is_refused(self):
        """The mirror of the `introduced` check, and the one it cannot see.

        A set difference only catches commands added. These replacements
        contain no control character and change exactly the bytes the plan
        asked for, yet each one hides a second decayed command from the audit
        by closing an inline-code span or starting a table row. Corruption the
        detector can no longer see is worse than corruption it reports.
        """
        cases = {
            "closes-a-code-span": (
                "# T\n\nvalue $2\times7$ and $x\theta y` end\n",
                "\times",
                "\\times`",
            ),
            "starts-a-table-row": (
                "# T\n\nvalue $2\times7$ and $x\theta y$\n",
                "value $2\times",
                "|value $2\\times",
            ),
        }
        for label, (note, find, replace) in cases.items():
            with self.subTest(case=label):
                note_path = self.write_note(f"Conceal-{label}.md", note)
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture(
                    [edit_operation(note_path, find=find, replace=replace, expected_occurrences=1)]
                )

                # The reconstruction rule stops both of these in pre-flight,
                # so no write is attempted at all.
                with self.assertRaises(RemediationError) as raised:
                    execute_plan(plan, adapter, vault="test-vault")
                self.assertIn("decay restored", str(raised.exception))
                self.assertEqual(adapter.calls, [])

                # The read-back stays as the backstop, for a concealment the
                # static rule does not anticipate.
                operation = {"note_path": note_path, "find": find, "replace": replace}
                with self.assertRaises(RemediationError) as raised:
                    assert_repair_landed(operation, note, note.replace(find, replace))
                self.assertIn("concealed", str(raised.exception))
                self.assertIn("\\theta", str(raised.exception))

    def test_warn_delivers_the_account_when_stderr_raises_a_non_os_error(self):
        note_path = self.write_note("Shim.md")
        plan_path = self.root / "plan.json"
        blocked_manifest = self.root / "blocked"
        blocked_manifest.mkdir()
        plan_path.write_text(json.dumps(execute_plan_fixture([edit_operation(note_path)])), encoding="utf-8")
        adapter = FakeObsidianApp(self.root)

        class ShimStream(io.StringIO):
            def write(self, *args, **kwargs):
                raise RuntimeError("logging shim")

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(ShimStream()):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    return_code = remediate_notes.main(
                        [
                            "--plan", str(plan_path),
                            "--manifest", str(blocked_manifest),
                            "--execute",
                            "--vault", "test-vault",
                        ]
                    )

        self.assertEqual(return_code, 1)
        self.assertIn(note_path, stdout.getvalue())

    def test_cli_names_the_real_reason_an_operation_cannot_execute(self):
        """An operator must not be told to authorise an unexecutable operation."""
        plan_path = self.root / "plan.json"
        manifest_path = self.root / "manifest.json"
        plan_path.write_text(
            json.dumps(
                execute_plan_fixture(
                    [{"operation": "delete", "note_path": "Atomic Notes/Gone.md"}],
                    mode="split-multi-note",
                )
            ),
            encoding="utf-8",
        )
        adapter = FakeObsidianApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                return_code = remediate_notes.main(
                    [
                        "--plan", str(plan_path),
                        "--manifest", str(manifest_path),
                        "--execute",
                        "--vault", "test-vault",
                    ]
                )

        self.assertEqual(return_code, 1)
        self.assertIn("not an executable operation", stderr.getvalue())
        self.assertEqual(adapter.calls, [])

    def test_find_without_a_control_character_is_refused_before_any_write(self):
        """This execute path is for control-character repairs only, by design.

        The refusal also moves earlier than the count gate would put it. A
        `find` that matches nothing is otherwise caught only after the note
        has been read, so requiring the corruption up front means an operation
        that is not this repair never reaches the adapter at all.
        """
        note_path = self.write_note("PlainEdit.md", "# T\n\nPOTATO here\n")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [edit_operation(note_path, find="POTATO", replace="CARROT", expected_occurrences=1)]
        )

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("control character", str(raised.exception))
        self.assertEqual(adapter.calls, [])
        self.assertEqual((self.root / note_path).read_bytes(), b"# T\n\nPOTATO here\n")

    def test_both_decay_shapes_pass_the_replacement_rule(self):
        for label, find, replace in (
            ("tab-borne", "\times", "\\times"),
            ("newline-borne", "\neq b$", "\\neq b$"),
        ):
            with self.subTest(case=label):
                note_path = self.write_note(f"Contract-{label}.md", f"# T\n\n$a{find}$\n")
                adapter = FakeObsidianApp(self.root)
                plan = execute_plan_fixture(
                    [edit_operation(note_path, find=find, replace=replace, expected_occurrences=1)]
                )

                self.assertEqual(execute_plan(plan, adapter, vault="test-vault"), [note_path])
                self.assertEqual(
                    (self.root / note_path).read_bytes(),
                    f"# T\n\n$a{replace}$\n".encode("utf-8"),
                )

    def test_manifest_documents_the_same_operations_that_were_executed(self):
        """A plan may not hand the gates one list and the manifest another."""

        class SplitBrain(dict):
            def __getitem__(self, key):
                if key == "operations":
                    return [edit_operation("Atomic Notes/Decoy.md", find="ZZZZ")]
                return super().__getitem__(key)

        note_path = self.write_note("Real.md")
        plan = SplitBrain(execute_plan_fixture([edit_operation(note_path)]))
        adapter = FakeObsidianApp(self.root)

        operations = validate_executable_plan(plan)
        execute_plan(plan, adapter, vault="test-vault")
        manifest = remediate_notes._manifest(
            plan, executed=True, dispatched=[note_path], operations=operations
        )

        self.assertEqual(manifest["operations"][0]["note_path"], note_path)
        self.assertEqual(manifest["operation_count"], 1)
        self.assertEqual((self.root / note_path).read_bytes(), CLEAN_NOTE.encode("utf-8"))

    def test_read_back_hazards_are_checked_even_when_the_transport_obeyed_the_plan(self):
        """The backstop behind the pre-flight refusals above.

        Equality with `before.replace(find, replace)` only proves the transport
        did what the plan said, so it cannot be the first question asked. These
        operations never reach a write in practice; the check stands for plan
        bugs not yet imagined.
        """
        note = "# T\n\nvalue $2\times7$\n"
        for replace, expected in (
            ("\times", "still present"),
            ("\\times \theta", "introduced decayed command"),
        ):
            with self.subTest(replace=replace):
                operation = edit_operation("Atomic Notes/T.md", replace=replace, expected_occurrences=1)
                after = note.replace(operation["find"], operation["replace"])

                with self.assertRaises(RemediationError) as raised:
                    assert_repair_landed(operation, note, after)

                self.assertIn(expected, str(raised.exception))

    def test_two_commands_in_one_note_take_one_operation_each(self):
        note_path = self.write_note("Both.md", "# T\n\n$2\times7$ and $a\neq b$\n")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [
                edit_operation(note_path, expected_occurrences=1),
                edit_operation(
                    note_path,
                    find="\neq b",
                    replace="\\neq b",
                    expected_occurrences=1,
                ),
            ]
        )

        written = execute_plan(plan, adapter, vault="test-vault")

        # The first repair leaves the second command still decayed, which must
        # not read as a failed write, and the note is named once.
        self.assertEqual(written, [note_path])
        self.assertEqual(
            (self.root / note_path).read_bytes(),
            b"# T\n\n$2\\times7$ and $a\\neq b$\n",
        )

    def test_a_wrapped_read_is_decoded_whole_rather_than_truncated(self):
        """Base64 wrapped at a multiple of four is still valid base64.

        Decoding only the final line would hand back a short note that every
        later gate would then compare against, so the whole output is joined.
        """
        long_note = "# Long\n\n" + ("filler line\n" * 40) + "value $2\times7$\n"
        note_path = self.write_note("Wrapped.md", long_note)

        class WrappingApp(FakeObsidianApp):
            def run(self, args: list[str]) -> CommandResult:
                result = super().run(args)
                if payload_of(args)["action"] != "read":
                    return result
                token = result.stdout.strip().removeprefix("=>").strip().strip('"')
                wrapped = "\n".join(token[i:i + 76] for i in range(0, len(token), 76))
                return CommandResult(ok=True, stdout=f"=> {wrapped}\n", stderr="", returncode=0)

        adapter = WrappingApp(self.root)
        self.assertEqual(adapter.read_note(note_path, vault="test-vault"), long_note)

        plan = execute_plan_fixture([edit_operation(note_path, expected_occurrences=1)])
        execute_plan(plan, adapter, vault="test-vault")

        self.assertEqual(
            (self.root / note_path).read_bytes(),
            long_note.replace("\times", "\\times").encode("utf-8"),
        )

    def test_a_write_interrupted_after_it_landed_is_still_reported(self):
        first = self.write_note("Committed.md")
        second = self.write_note("Never.md")

        class CrashAfterWriting(FakeObsidianApp):
            def run(self, args: list[str]) -> CommandResult:
                result = super().run(args)
                if payload_of(args)["action"] == "replace":
                    raise KeyboardInterrupt
                return result

        adapter = CrashAfterWriting(self.root)
        plan = execute_plan_fixture([edit_operation(first), edit_operation(second)])
        written: list[str] = []

        with self.assertRaises(KeyboardInterrupt):
            execute_plan(plan, adapter, vault="test-vault", on_written=written.append)

        # The note was mutated, so the rollback account must name it.
        self.assertEqual(adapter.written, [first])
        self.assertEqual(written, [first])

    def test_write_that_rewrites_the_whole_note_is_refused(self):
        note_path = self.write_note("Truncated.md")
        adapter = FakeObsidianApp(self.root, sabotage=lambda path, updated: "")
        plan = execute_plan_fixture([edit_operation(note_path)])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn(note_path, str(raised.exception))
        self.assertIn("more than the matched string", str(raised.exception))

    def test_write_that_drops_the_match_instead_of_replacing_it_is_refused(self):
        note_path = self.write_note("Dropped.md")
        adapter = FakeObsidianApp(
            self.root,
            sabotage=lambda path, updated: updated.replace("\\times", ""),
        )
        plan = execute_plan_fixture([edit_operation(note_path)])

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn(note_path, str(raised.exception))

    def test_a_landed_write_is_reported_even_when_its_verification_fails(self):
        note_path = self.write_note("Unverified.md")
        adapter = FakeObsidianApp(self.root, sabotage=lambda path, updated: "")
        plan = execute_plan_fixture([edit_operation(note_path)])
        written: list[str] = []

        with self.assertRaises(RemediationError):
            execute_plan(plan, adapter, vault="test-vault", on_written=written.append)

        # The vault changed, so the account of what changed must say so.
        self.assertEqual(written, [note_path])
        self.assertEqual(adapter.written, written)

    def test_split_under_execute_is_refused_as_unexecutable_not_as_bad_authoring(self):
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [{"operation": "split", "note_path": "Atomic Notes/Bundle.md", "approved": True}],
            mode="split-multi-note",
        )

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault")

        self.assertIn("not an executable operation", str(raised.exception))

    def test_cli_reports_written_notes_when_the_batch_is_interrupted(self):
        first = self.write_note("Before.md")
        second = self.write_note("After.md")
        plan_path = self.root / "plan.json"
        manifest_path = self.root / "manifest.json"
        plan_path.write_text(
            json.dumps(execute_plan_fixture([edit_operation(first), edit_operation(second)])),
            encoding="utf-8",
        )

        class InterruptingApp(FakeObsidianApp):
            def run(self, args: list[str]) -> CommandResult:
                if payload_of(args)["path"] == second:
                    raise KeyboardInterrupt
                return super().run(args)

        adapter = InterruptingApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaises(KeyboardInterrupt):
                    remediate_notes.main(
                        [
                            "--plan", str(plan_path),
                            "--manifest", str(manifest_path),
                            "--execute",
                            "--vault", "test-vault",
                        ]
                    )

        self.assertIn(f"dispatched_note={first}", stderr.getvalue())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["dispatched_note_paths"], [first])

    def test_cli_falls_back_to_stdout_when_stderr_itself_fails(self):
        note_path = self.write_note("Pipe.md")
        plan_path = self.root / "plan.json"
        blocked_manifest = self.root / "blocked"
        blocked_manifest.mkdir()
        plan_path.write_text(json.dumps(execute_plan_fixture([edit_operation(note_path)])), encoding="utf-8")
        adapter = FakeObsidianApp(self.root)

        class BrokenStream(io.StringIO):
            def write(self, *args, **kwargs):
                raise BrokenPipeError(32, "Broken pipe")

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(BrokenStream()):
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    return_code = remediate_notes.main(
                        [
                            "--plan", str(plan_path),
                            "--manifest", str(blocked_manifest),
                            "--execute",
                            "--vault", "test-vault",
                        ]
                    )

        # Neither the refusal nor the account may be lost to a broken stderr.
        self.assertEqual(return_code, 1)
        self.assertIn(note_path, stdout.getvalue())

    def test_cli_manifest_documents_the_operations_that_were_executed(self):
        note_path = self.write_note("Documented.md")
        plan_path = self.root / "plan.json"
        manifest_path = self.root / "manifest.json"
        plan_path.write_text(json.dumps(execute_plan_fixture([edit_operation(note_path)])), encoding="utf-8")
        adapter = FakeObsidianApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stdout(io.StringIO()):
                remediate_notes.main(
                    [
                        "--plan", str(plan_path),
                        "--manifest", str(manifest_path),
                        "--execute",
                        "--vault", "test-vault",
                    ]
                )

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Built from the list the gates validated, not re-read from the plan.
        self.assertEqual(manifest["operations"][0]["find"], "\times")
        self.assertEqual(manifest["dispatched_note_paths"], [note_path])

    def test_cli_reports_written_notes_when_the_manifest_cannot_be_saved(self):
        note_path = self.write_note("Stranded.md")
        plan_path = self.root / "plan.json"
        blocked_manifest = self.root / "blocked"
        blocked_manifest.mkdir()
        plan_path.write_text(json.dumps(execute_plan_fixture([edit_operation(note_path)])), encoding="utf-8")
        adapter = FakeObsidianApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                return_code = remediate_notes.main(
                    [
                        "--plan", str(plan_path),
                        "--manifest", str(blocked_manifest),
                        "--execute",
                        "--vault", "test-vault",
                    ]
                )

        self.assertEqual(return_code, 1)
        self.assertIn(note_path, stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_write_that_corrupts_another_command_halts_the_batch(self):
        first = self.write_note("Collateral.md", "# Ratio\n\n$2\times7$ and $\\text{x}$.\n")
        second = self.write_note("Later.md")

        def sabotage(path: str, updated: str) -> str:
            # What a whole-note `content=` rewrite would do to the note's
            # other commands while repairing the asserted one.
            return updated.replace("\\text", "\text")

        adapter = FakeObsidianApp(self.root, sabotage=sabotage)
        plan = execute_plan_fixture(
            [edit_operation(first, expected_occurrences=1), edit_operation(second)]
        )
        written: list[str] = []

        with self.assertRaises(RemediationError) as raised:
            execute_plan(plan, adapter, vault="test-vault", on_written=written.append)

        self.assertIn(first, str(raised.exception))
        self.assertIn("\\text", str(raised.exception))
        self.assertEqual(written, [first])
        self.assertEqual((self.root / second).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))

    def test_eval_argument_survives_a_real_process_boundary(self):
        """Prove the encoding, not the fake: run the real adapter over execve.

        `FakeObsidianApp` replaces `run`, so it cannot show what a real process
        receives. This sends the production argument through a real subprocess
        and reads back the bytes that arrived.
        """
        landed = self.root / "argv.bin"
        code = ObsidianAdapter(binary=sys.executable).run(
            [
                "-c",
                "import sys, pathlib; pathlib.Path(sys.argv[1]).write_bytes(sys.argv[2].encode())",
                str(landed),
                f"code={build_replace_in_note_code('Atomic Notes/A.md', find='\times', replace='\\times', expected_occurrences=2)}",
            ]
        )

        self.assertTrue(code.ok, code.stderr)
        arrived = landed.read_bytes()
        self.assertNotIn(b"\\", arrived)
        self.assertNotIn(b"\t", arrived)
        payload = json.loads(
            base64.b64decode(ATOB_PATTERN.search(arrived.decode("ascii")).group(1)).decode("utf-8")
        )
        self.assertEqual(payload["replace"], "\\times")
        self.assertEqual(payload["find"], "\times")

    def test_newline_borne_repair_rejoins_the_split_math(self):
        note_path = self.write_note("Bound.md", "# Bound\n\nThe value is $a\neq b$.\n")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [
                edit_operation(
                    note_path,
                    find="\neq b$",
                    replace="\\neq b$",
                    expected_occurrences=1,
                )
            ]
        )

        execute_plan(plan, adapter, vault="test-vault")

        self.assertEqual(
            (self.root / note_path).read_bytes(),
            b"# Bound\n\nThe value is $a\\neq b$.\n",
        )
        # A find string containing a real newline still travels as one argument.
        write_call = [call for call in adapter.calls if payload_of(call)["action"] == "replace"][0]
        self.assertNotIn("\n", "".join(write_call))

    def test_cli_execute_requires_a_vault(self):
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                remediate_notes.main(["--plan", "p.json", "--manifest", "m.json", "--execute"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--vault", stderr.getvalue())

    def test_cli_execute_records_written_notes_in_the_manifest(self):
        note_path = self.write_note("Cli.md")
        plan_path = self.root / "plan.json"
        manifest_path = self.root / "out" / "manifest.json"
        plan_path.write_text(json.dumps(execute_plan_fixture([edit_operation(note_path)])), encoding="utf-8")
        adapter = FakeObsidianApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                return_code = remediate_notes.main(
                    [
                        "--plan", str(plan_path),
                        "--manifest", str(manifest_path),
                        "--execute",
                        "--vault", "test-vault",
                    ]
                )

        self.assertEqual(return_code, 0)
        self.assertIn("dispatched_note_count=1", stdout.getvalue())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(manifest["executed"])
        self.assertEqual(manifest["dispatched_note_paths"], [note_path])
        self.assertEqual((self.root / note_path).read_bytes(), CLEAN_NOTE.encode("utf-8"))

    def test_cli_execute_refuses_unapproved_plan_without_traceback(self):
        note_path = self.write_note("CliUnapproved.md")
        plan_path = self.root / "plan.json"
        manifest_path = self.root / "manifest.json"
        plan_path.write_text(
            json.dumps(execute_plan_fixture([edit_operation(note_path, approved=False)])),
            encoding="utf-8",
        )
        adapter = FakeObsidianApp(self.root)

        with patch("shared.scripts.remediate_notes.ObsidianAdapter", lambda **kwargs: adapter):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                return_code = remediate_notes.main(
                    [
                        "--plan", str(plan_path),
                        "--manifest", str(manifest_path),
                        "--execute",
                        "--vault", "test-vault",
                    ]
                )

        self.assertEqual(return_code, 1)
        self.assertIn("requires approval", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertFalse(manifest_path.exists())
        self.assertEqual(adapter.calls, [])

    def test_count_mismatch_mid_batch_keeps_completed_writes(self):
        first = self.write_note("Ahead.md")
        second = self.write_note("Stale.md", "# Ratio\n\nThe product is $2\times7$.\n")
        third = self.write_note("Behind.md")
        adapter = FakeObsidianApp(self.root)
        plan = execute_plan_fixture(
            [edit_operation(first), edit_operation(second), edit_operation(third)]
        )
        written: list[str] = []

        with self.assertRaises(RemediationError):
            execute_plan(plan, adapter, vault="test-vault", on_written=written.append)

        self.assertEqual(written, [first])
        self.assertEqual((self.root / first).read_bytes(), CLEAN_NOTE.encode("utf-8"))
        self.assertEqual((self.root / third).read_bytes(), CORRUPTED_NOTE.encode("utf-8"))


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
