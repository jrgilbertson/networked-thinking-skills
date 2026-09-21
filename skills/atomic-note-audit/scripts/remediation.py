from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
import unicodedata

from markdown_parse import DECAYED_LATEX_SUFFIXES, decayed_latex_commands


class RemediationError(Exception):
    pass


# Planning gate only. `validate_plan` requires approval for these operations
# and for no others, so `edit` and `relink` pass validation unapproved. Any
# path that writes to the vault must call `validate_executable_plan`, which
# requires approval for every operation it will execute.
DESTRUCTIVE_OPERATIONS = {"split", "delete", "rename", "move"}
SUPPORTED_OPERATIONS = {"edit", "split", "delete", "rename", "move", "relink"}
EXECUTABLE_OPERATIONS = {"edit"}
# The on-disk byte sequence each decayed command leaves behind, so a write
# that hides one from the detector can be told from a write that repaired it.
DECAYED_FORMS = {command: character + suffix for character, suffix, command in DECAYED_LATEX_SUFFIXES}
REQUIRED_EDIT_KEYS = ("note_path", "find", "replace", "expected_occurrences")
REQUIRED_PLAN_KEYS = ("plan_version", "audit_run_id", "mode", "operations")


def validate_plan(plan: dict[str, Any], *, destructive_allowed: bool) -> None:
    if not isinstance(plan, dict):
        raise RemediationError("plan must be an object")
    for key in REQUIRED_PLAN_KEYS:
        if key not in plan:
            raise RemediationError(f"Missing plan key: {key}")

    operations = plan["operations"]
    if not isinstance(operations, list):
        raise RemediationError("operations must be a list")

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise RemediationError(f"Operation {index} must be an object")
        if "operation_type" in operation:
            raise RemediationError(f"Operation {index} uses unsupported operation_type")

        operation_name = operation.get("operation")
        if not isinstance(operation_name, str):
            raise RemediationError(f"Operation {index} must state operation")
        if operation_name not in SUPPORTED_OPERATIONS:
            raise RemediationError(f"Operation {index} has unsupported operation")
        if operation_name in DESTRUCTIVE_OPERATIONS:
            if not destructive_allowed:
                raise RemediationError(f"Operation {index} is destructive")
            if operation.get("approved") is not True:
                raise RemediationError(f"Operation {index} requires approval")
        if operation_name == "split":
            if operation.get("delete_original") is not True:
                raise RemediationError(f"Split operation {index} must state delete_original=true")
            _validate_split_outputs(operation, index)


def validate_executable_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Check every operation a batch would execute, before its first write.

    Operation type, approval, and whether a replacement could repair at all
    are static properties of the plan file, so a plan carrying one bad
    operation writes none of them. Occurrence counts are deliberately
    excluded: checking a count here would open a window between the check and
    the write, so `assert_expected_occurrences` re-checks it against the note
    itself immediately before each write.
    """
    if not isinstance(plan, dict):
        raise RemediationError("plan must be an object")
    # Read the operations once and check that same list everywhere, so the
    # operations validated here are the operations the caller executes.
    operations = plan.get("operations")

    # Name the real reason before `validate_plan` reports a less apt one. An
    # unexecutable operation would otherwise be refused with authoring advice,
    # such as telling the operator a split needs delete_original.
    _assert_executable_operation_names(operations)
    # This gate is strictly narrower than either mode of `validate_plan`, so
    # the permissive flag only keeps its approval rule from shadowing the
    # refusal below.
    validate_plan(plan, destructive_allowed=True)
    if not isinstance(operations, list):
        raise RemediationError("operations must be a list")

    for index, operation in enumerate(operations):
        if operation.get("approved") is not True:
            raise RemediationError(f"Operation {index} requires approval before execution")
        for key in REQUIRED_EDIT_KEYS:
            if key not in operation:
                raise RemediationError(f"Operation {index} requires {key}")
        for key in ("note_path", "find", "replace"):
            if not isinstance(operation[key], str) or not operation[key]:
                raise RemediationError(f"Operation {index} requires a non-empty {key}")
        expected = operation["expected_occurrences"]
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            raise RemediationError(f"Operation {index} requires a positive expected_occurrences")
        _assert_replacement_repairs(operation, index)
    return operations


def _assert_replacement_repairs(operation: dict[str, Any], index: int) -> None:
    """Refuse a replacement that cannot repair, or that carries corruption.

    Both are properties of the plan file, so they belong here rather than in
    the read-back: caught up front they cost nothing, while caught afterwards
    the note has already been written. The likeliest authoring slip produces
    `find == replace`, because `"\\times"` in JSON is a tab followed by
    `imes` and only `"\\\\times"` is the command.

    The two halves are a matched pair. `find` matches decayed LaTeX so it must
    carry a control character, and `replace` restores the literal backslash
    sequence so it must carry none. Requiring the first narrows this execute
    path to control-character repairs on purpose: it is the only vault-write
    capability here, so it should grow by deliberate decision rather than turn
    out to have been looser than it looked. An edit that is not this repair --
    a typo fix, say -- is refused, and widening the gate for one is a change
    to make knowingly. Requiring it also moves the refusal earlier: a `find`
    matching nothing would otherwise be caught only by the count gate, after
    the note was read.

    The rules ask about raw control characters rather than about decayed
    commands because `decayed_latex_commands` reads a note: it masks code
    spans, table rows and tab-indented lines. Those exemptions are right for a
    note and wrong for a bare fragment, where a leading tab or pipe means
    something else entirely once the fragment is spliced mid-line.

    The last rule subsumes the others and is the reason this gate can be
    called complete: a replacement must be its find string with the decay
    restored and nothing else. Enumerating what a replacement must not add
    does not close it, because the detector masks on backticks, table pipes,
    tilde fences, HTML comments and display-math delimiters, and a list like
    that is only ever as complete as the last defect found.
    """
    find, replace = operation["find"], operation["replace"]
    if find in replace:
        raise RemediationError(
            f"Operation {index} replacement contains the string it replaces, so it cannot repair"
        )
    if not any(unicodedata.category(character) == "Cc" for character in find):
        raise RemediationError(
            f"Operation {index} find carries no control character, "
            "so it does not match the corruption this execute path repairs"
        )
    carried = sorted({character for character in replace if _is_non_printing(character)})
    if carried:
        codepoints = ", ".join(f"U+{ord(character):04X}" for character in carried)
        raise RemediationError(
            f"Operation {index} replacement carries non-printing character(s) {codepoints}; "
            "a replacement may contain only visible text"
        )
    if _restored(find) != replace:
        raise RemediationError(
            f"Operation {index} replacement is not its find string with the decay restored; "
            "a repair may change nothing else"
        )


def _commands_repaired_by(before: str, find: str) -> dict[str, int]:
    """How many decayed occurrences this operation's spans actually repair.

    Counts rather than names, because one repair must not licence hiding a
    second occurrence of the same command. Counted over every span the find
    string covers in the note, which also gives the total directly rather than
    multiplying by the asserted occurrence count.

    Read against the note rather than the find string alone. The detector's
    guard asks whether the character following a decayed form is a letter, and
    for a form at the end of `find` that character lives in the note. A
    one-character slice off the end of `find` is `""`, which is not a letter,
    so every trailing form was credited as repaired whether the detector had
    counted it or not — widening the set of commands a write may excuse.
    """
    repaired: dict[str, int] = {}
    for span_start in _occurrences_of(before, find):
        span_end = span_start + len(find)
        for command, form in DECAYED_FORMS.items():
            for start in _occurrences_of(before, form):
                if start < span_start or start + len(form) > span_end:
                    continue
                following = before[start + len(form):start + len(form) + 1]
                if not following.isalpha():
                    repaired[command] = repaired.get(command, 0) + 1
    return repaired


def _visible_occurrences(text: str) -> dict[str, int]:
    """How many decayed occurrences the detector actually reports.

    Asks `decayed_latex_commands` rather than re-deriving its masking, so this
    cannot drift from the rules the audit applies. Each occurrence is tested
    by neutralising every other occurrence of the same command with a
    stand-in of identical length that keeps the leading control character, so
    the note's line structure and every mask stay exactly as they were and the
    only thing that changes is which occurrence is left to report.
    """
    counts: dict[str, int] = {}
    for command, form in DECAYED_FORMS.items():
        starts = _occurrences_of(text, form)
        if not starts:
            continue
        stand_in = form[0] + "Z" + form[2:]
        for kept in starts:
            probe = text
            for start in starts:
                if start != kept:
                    probe = probe[:start] + stand_in + probe[start + len(form):]
            if command in decayed_latex_commands(probe):
                counts[command] = counts.get(command, 0) + 1
    return counts


def _occurrences_of(text: str, form: str) -> list[int]:
    starts: list[int] = []
    start = text.find(form)
    while start != -1:
        starts.append(start)
        start = text.find(form, start + 1)
    return starts


def _restored(text: str) -> str:
    """Turn each decayed form in a string into the command it reconstructs to.

    The forward direction. Re-decaying the replacement and comparing it to the
    find string looks equivalent and is not: it rewrites commands that were
    already intact, so a find window holding one is refused although the
    repair is correct. `DECAYED_LATEX_SUFFIXES` is ordered longest suffix
    first, so no shorter form matches inside a longer one.
    """
    restored: list[str] = []
    index = 0
    while index < len(text):
        for character, suffix, command in DECAYED_LATEX_SUFFIXES:
            form = character + suffix
            if not text.startswith(form, index):
                continue
            following = text[index + len(form):index + len(form) + 1]
            if following.isalpha():
                continue
            restored.append(command)
            index += len(form)
            break
        else:
            restored.append(text[index])
            index += 1
    return "".join(restored)


def _is_non_printing(character: str) -> bool:
    """Control, format and line or paragraph separator characters.

    The range matters beyond the C0 block this repair removes, because
    `str.splitlines()` also breaks on U+0085, U+2028 and U+2029 while the
    app's own `split("\\n")` does not. A replacement carrying one of those
    moves the detector's line boundaries without moving the note's, which can
    push an unrepaired command into a line the detector skips.
    """
    return unicodedata.category(character) in {"Cc", "Cf", "Zl", "Zp"}


def _assert_executable_operation_names(operations: Any) -> None:
    if not isinstance(operations, list):
        return
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            continue
        operation_name = operation.get("operation")
        if isinstance(operation_name, str) and operation_name not in EXECUTABLE_OPERATIONS:
            raise RemediationError(
                f"Operation {index} cannot be executed: {operation_name} is not an executable operation"
            )


def assert_expected_occurrences(operation: dict[str, Any], content: str) -> None:
    """Refuse a write whose note no longer matches the count the plan asserted.

    Call this against the note's current content immediately before writing it,
    never in a pre-flight pass, so the note cannot change between the check and
    the write.
    """
    actual = content.count(operation["find"])
    expected = operation["expected_occurrences"]
    if actual != expected:
        raise RemediationError(
            f"{operation['note_path']}: plan asserts {expected} occurrence(s) "
            f"but the note contains {actual}"
        )


def assert_repair_landed(operation: dict[str, Any], before: str, after: str) -> None:
    """Refuse to continue a batch whose last write did not land cleanly.

    The note must be left with the corruption gone and nothing else touched,
    so all three questions are asked and none of them gates the others. The
    equality is necessary but never sufficient on its own: it proves only that
    the transport did what the plan said, and a plan can be wrong. Asking it
    first would make a `find == replace` plan look like a clean repair.
    """
    note_path = operation["note_path"]
    if operation["find"] in after:
        raise RemediationError(f"{note_path}: write did not land, the matched string is still present")

    # Every decayed occurrence the detector reported must still be reported
    # afterwards, except the ones this operation repaired. Counting rather
    # than naming is what makes that true: `\neq` is the only decay whose
    # restoration deletes a line break, so it merges the broken line into the
    # line above, and if that line is a table row or tab-indented the merged
    # line leaves the detector's view with any decay still on it. Naming
    # commands lets an operation that legitimately repairs one `\times`
    # licence hiding a second.
    #
    # The question is asked of what the detector reported, never of raw bytes,
    # and it is asked by running the detector rather than re-deriving its
    # rules. Decayed sequences it always ignored — masked, or failing its
    # guard that the character after the suffix is not a letter — were never
    # signal, so finding them afterwards proves nothing. `\to` is a tab and
    # one letter and `\neq` a newline and two, so those sequences occur in
    # ordinary prose and indented code; a byte test refuses correct repairs
    # over them.
    #
    # One case this cannot speak for: in a note whose fences or code spans are
    # unbalanced the detector reports nothing to begin with, so this check is
    # vacuous and only the equality below still holds. The guarantee there is
    # that the transport obeyed the plan, not that the note's corruption
    # semantics were verified.
    before_counts = _visible_occurrences(before)
    after_counts = _visible_occurrences(after)
    repaired = _commands_repaired_by(before, operation["find"])
    # A replacement carries no control character, so a write cannot put a
    # decayed form into a note that did not already hold one. A command that
    # gains visibility was therefore revealed, not introduced — the corruption
    # was on disk all along and the audit can now see it, which is the outcome
    # this work wants. Only bytes that were absent before count as introduced,
    # and that can only come from a transport that ignored the plan.
    present_before = {command for command, form in DECAYED_FORMS.items() if form in before}

    concealed: list[str] = []
    introduced: list[str] = []
    for command in sorted(set(before_counts) | set(after_counts)):
        expected = before_counts.get(command, 0) - repaired.get(command, 0)
        actual = after_counts.get(command, 0)
        if actual < expected:
            concealed.append(command)
        elif actual > expected and command not in present_before:
            introduced.append(command)

    if introduced:
        raise RemediationError(
            f"{note_path}: write introduced decayed command(s) {', '.join(introduced)}"
        )
    if concealed:
        raise RemediationError(
            f"{note_path}: write concealed decayed command(s) {', '.join(concealed)} "
            "from the audit rather than repairing them"
        )

    if after != before.replace(operation["find"], operation["replace"]):
        raise RemediationError(f"{note_path}: write changed more than the matched string")


def build_dry_run_manifest(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "audit_run_id": plan["audit_run_id"],
        "mode": plan["mode"],
        "operation_count": len(plan["operations"]),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operations": deepcopy(plan["operations"]),
        "executed": False,
    }


def _validate_split_outputs(operation: dict[str, Any], index: int) -> None:
    outputs = operation.get("proposed_outputs")
    if not isinstance(outputs, list) or not outputs:
        raise RemediationError(f"Split operation {index} requires proposed_outputs")
    for output_index, output in enumerate(outputs):
        if not isinstance(output, dict):
            raise RemediationError(f"Split operation {index} output {output_index} must be an object")
        for key in ("note_path", "content"):
            if not isinstance(output.get(key), str) or not output[key]:
                raise RemediationError(f"Split operation {index} output {output_index} requires {key}")
