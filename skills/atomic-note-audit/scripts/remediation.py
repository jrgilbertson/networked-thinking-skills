from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from markdown_parse import decayed_latex_commands


class RemediationError(Exception):
    pass


# Planning gate only. `validate_plan` requires approval for these operations
# and for no others, so `edit` and `relink` pass validation unapproved. Any
# path that writes to the vault must call `validate_executable_plan`, which
# requires approval for every operation it will execute.
DESTRUCTIVE_OPERATIONS = {"split", "delete", "rename", "move"}
SUPPORTED_OPERATIONS = {"edit", "split", "delete", "rename", "move", "relink"}
EXECUTABLE_OPERATIONS = {"edit"}
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
    """
    find, replace = operation["find"], operation["replace"]
    if find in replace:
        raise RemediationError(
            f"Operation {index} replacement contains the string it replaces, so it cannot repair"
        )
    carried = decayed_latex_commands(replace)
    if carried:
        raise RemediationError(
            f"Operation {index} replacement itself carries decayed command(s) {', '.join(carried)}"
        )


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

    introduced = set(decayed_latex_commands(after)) - set(decayed_latex_commands(before))
    if introduced:
        raise RemediationError(
            f"{note_path}: write introduced decayed command(s) {', '.join(sorted(introduced))}"
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
