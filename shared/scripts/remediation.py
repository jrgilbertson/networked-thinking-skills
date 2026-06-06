from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class RemediationError(Exception):
    pass


DESTRUCTIVE_OPERATIONS = {"split", "delete", "rename", "move"}
SUPPORTED_OPERATIONS = {"edit", "split", "delete", "rename", "move", "relink"}
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
