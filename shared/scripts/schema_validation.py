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

ROW_STATUSES = {"complete", "reused_cache", "error", "skipped"}
PRIORITIES = {"P0", "P1", "P2", "P3", None}
CACHE_STATUSES = {"none", "miss", "hit", "partial"}


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
