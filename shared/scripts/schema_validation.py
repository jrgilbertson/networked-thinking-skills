from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ValidationError(Exception):
    pass


AUDIT_ROW_REQUIRED = {
    "schema_version",
    "run_id",
    "row_status",
    "note_path",
    "note_link",
    "content_hash",
    "modified_time",
    "score",
    "priority",
    "clean",
    "pending_model",
    "dimensions",
    "findings",
    "recommendations",
    "model_judgment",
    "cache_status",
    "factual_risk",
    "fact_check_required",
    "doctrine_version",
    "rubric_version",
    "prompt_version",
}
RUN_MANIFEST_REQUIRED = {
    "schema_version",
    "run_id",
    "started_at",
    "ended_at",
    "config_snapshot",
    "total_notes",
    "row_status_counts",
    "priority_counts",
    "validation_status",
    "outputs",
    "errors",
}

ROW_STATUSES = {"complete", "reused_cache", "error", "skipped"}
ROW_STATUS_COUNT_KEYS = ("complete", "reused_cache", "error", "skipped")
PRIORITIES = {"P0", "P1", "P2", "P3", None}
PRIORITY_COUNT_KEYS = ("P0", "P1", "P2", "P3")
CACHE_STATUSES = {"none", "miss", "hit", "partial"}
VALIDATION_STATUSES = {"passed", "failed", "not_run"}
OUTPUT_KEYS = {"audit_rows", "model_judgments", "remediation_plan", "manifest"}


@dataclass(frozen=True)
class ValidationResult:
    valid_rows: int


def _require_keys(row: dict[str, Any], keys: set[str]) -> None:
    missing = keys - set(row)
    if missing:
        raise ValidationError(f"Missing required keys: {', '.join(sorted(missing))}")


def validate_audit_row(row: dict[str, Any], *, default_scan: bool) -> None:
    if not isinstance(row, dict):
        raise ValidationError("row must be an object")
    _require_keys(row, AUDIT_ROW_REQUIRED)
    if row["row_status"] not in ROW_STATUSES:
        raise ValidationError(f"Invalid row_status: {row['row_status']}")
    if default_scan and row["row_status"] == "skipped":
        raise ValidationError("Default Atomic Notes scans cannot skip rows")
    if row["priority"] not in PRIORITIES:
        raise ValidationError(f"Invalid priority: {row['priority']}")
    if row["cache_status"] not in CACHE_STATUSES:
        raise ValidationError(f"Invalid cache_status: {row['cache_status']}")
    score = row["score"]
    if score is not None and (type(score) is not int or score < 0 or score > 100):
        raise ValidationError("score must be an integer from 0 to 100 or null")
    if not isinstance(row["pending_model"], bool):
        raise ValidationError("pending_model must be a boolean")
    if row["model_judgment"] is not None and not isinstance(row["model_judgment"], dict):
        raise ValidationError("model_judgment must be null or an object")
    if not isinstance(row["factual_risk"], bool):
        raise ValidationError("factual_risk must be a boolean")
    note_link = row["note_link"]
    note_target = note_link[2:-2].split("|", 1)[0].strip() if isinstance(note_link, str) else ""
    if (
        not isinstance(note_link, str)
        or not note_link.startswith("[[")
        or not note_link.endswith("]]")
        or not note_target
    ):
        raise ValidationError("note_link must be an Obsidian wikilink")


def validate_run_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValidationError("manifest must be an object")
    _require_keys(manifest, RUN_MANIFEST_REQUIRED)
    _reject_extra_keys(manifest, RUN_MANIFEST_REQUIRED, "manifest")

    for key in ("schema_version", "run_id", "started_at", "ended_at"):
        if not isinstance(manifest[key], str) or not manifest[key]:
            raise ValidationError(f"{key} must be a non-empty string")

    if not isinstance(manifest["config_snapshot"], dict):
        raise ValidationError("config_snapshot must be an object")
    if not _is_non_negative_int(manifest["total_notes"]):
        raise ValidationError("total_notes must be a non-negative integer")

    _validate_count_mapping(
        manifest["row_status_counts"],
        required_keys=set(ROW_STATUS_COUNT_KEYS),
        label="row_status_counts",
    )
    _validate_count_mapping(
        manifest["priority_counts"],
        required_keys=set(PRIORITY_COUNT_KEYS),
        label="priority_counts",
    )

    if manifest["validation_status"] not in VALIDATION_STATUSES:
        raise ValidationError(f"Invalid validation_status: {manifest['validation_status']}")

    outputs = manifest["outputs"]
    if not isinstance(outputs, dict):
        raise ValidationError("outputs must be an object")
    _reject_extra_keys(outputs, OUTPUT_KEYS, "outputs")
    for key, value in outputs.items():
        if not isinstance(value, str):
            raise ValidationError(f"outputs.{key} must be a string")

    errors = manifest["errors"]
    if not isinstance(errors, list) or not all(isinstance(error, str) for error in errors):
        raise ValidationError("errors must be an array of strings")


def validate_audit_run_pair(rows: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    expected_run_id = manifest["run_id"]
    row_run_ids = {row.get("run_id") for row in rows}
    if row_run_ids != {expected_run_id}:
        raise ValidationError("manifest run_id does not match audit rows")

    if manifest["total_notes"] != len(rows):
        raise ValidationError("manifest total_notes does not match audit row count")

    row_status_counts = _count_row_field(rows, "row_status", ROW_STATUS_COUNT_KEYS)
    if manifest["row_status_counts"] != row_status_counts:
        raise ValidationError("manifest row_status_counts do not match audit rows")

    priority_counts = _count_row_field(rows, "priority", PRIORITY_COUNT_KEYS)
    if manifest["priority_counts"] != priority_counts:
        raise ValidationError("manifest priority_counts do not match audit rows")


def _reject_extra_keys(data: dict[str, Any], allowed_keys: set[str], label: str) -> None:
    extra = set(data) - allowed_keys
    if extra:
        raise ValidationError(f"{label} has unsupported keys: {', '.join(sorted(extra))}")


def _validate_count_mapping(data: Any, *, required_keys: set[str], label: str) -> None:
    if not isinstance(data, dict):
        raise ValidationError(f"{label} must be an object")
    _require_keys(data, required_keys)
    _reject_extra_keys(data, required_keys, label)
    for key, value in data.items():
        if not _is_non_negative_int(value):
            raise ValidationError(f"{label}.{key} must be a non-negative integer")


def _is_non_negative_int(value: Any) -> bool:
    return type(value) is int and value >= 0


def _count_row_field(
    rows: list[dict[str, Any]],
    field: str,
    keys: tuple[str, ...],
) -> dict[str, int]:
    counts = {key: 0 for key in keys}
    for row in rows:
        value = row.get(field)
        if value not in counts:
            raise ValidationError(f"audit row {field} cannot be counted: {value}")
        counts[value] += 1
    return counts
