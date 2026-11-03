from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finding_codes import ALLOWED_FINDING_CODES, FINDING_RECOMMENDATION_MODES


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
    "config_snapshot",
    "doctrine_version",
    "rubric_version",
    "prompt_version",
}
AUDIT_ROW_ALLOWED = AUDIT_ROW_REQUIRED | {"created_time", "factual_risk_reason"}
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
PRIORITY_KEYS = ("P0", "P1", "P2", "P3")
PRIORITIES = {*PRIORITY_KEYS, None}
PRIORITY_COUNT_KEYS = (*PRIORITY_KEYS, "no_change")
CACHE_STATUSES = {"none", "miss", "hit", "partial"}
VALIDATION_STATUSES = {"passed", "failed", "not_run"}
OUTPUT_KEYS = {"audit_rows", "model_judgments", "remediation_plan", "manifest"}
DIMENSION_KEYS = (
    "structure",
    "atomicity",
    "dae_quality",
    "clarity",
    "connections",
    "metadata_card_safety",
)
RECOMMENDATION_MODES = set(FINDING_RECOMMENDATION_MODES.values())


@dataclass(frozen=True)
class ValidationResult:
    valid_rows: int


def _require_keys(row: dict[str, Any], keys: set[str]) -> None:
    missing = keys - set(row)
    if missing:
        raise ValidationError(f"Missing required keys: {', '.join(sorted(missing))}")


def _validate_audit_row_v1(row: dict[str, Any], *, default_scan: bool) -> None:
    if not isinstance(row, dict):
        raise ValidationError("row must be an object")
    _require_keys(row, AUDIT_ROW_REQUIRED)
    _reject_extra_keys(row, AUDIT_ROW_ALLOWED, "row")
    for key in (
        "schema_version",
        "run_id",
        "note_path",
        "content_hash",
        "modified_time",
        "doctrine_version",
        "rubric_version",
        "prompt_version",
    ):
        _validate_non_empty_string(row[key], key)
    if row["row_status"] not in ROW_STATUSES:
        raise ValidationError(f"Invalid row_status: {row['row_status']}")
    if default_scan and row["row_status"] == "skipped":
        raise ValidationError("Default Atomic Notes scans cannot skip rows")
    if row["priority"] not in PRIORITIES:
        raise ValidationError(f"Invalid priority: {row['priority']}")
    if row["cache_status"] not in CACHE_STATUSES:
        raise ValidationError(f"Invalid cache_status: {row['cache_status']}")
    score = row["score"]
    if score is not None and (type(score) is not int or score < 1 or score > 100):
        raise ValidationError("score must be an integer from 1 to 100 or null")
    if not isinstance(row["clean"], bool):
        raise ValidationError("clean must be a boolean")
    if not isinstance(row["pending_model"], bool):
        raise ValidationError("pending_model must be a boolean")
    _validate_dimensions(row["dimensions"])
    _validate_findings(row["findings"])
    _validate_recommendations(row["recommendations"])
    if row["model_judgment"] is not None:
        # Import lazily because model_contract reuses this module's shared
        # ValidationError and dimension names.
        from model_contract import validate_model_judgment

        model_judgment = row["model_judgment"]
        validate_model_judgment(model_judgment)
        for key in ("note_path", "prompt_version"):
            if model_judgment[key] != row[key]:
                raise ValidationError(
                    f"model_judgment.{key} mismatch: "
                    f"expected {row[key]!r}, got {model_judgment[key]!r}"
                )
    if not isinstance(row["factual_risk"], bool):
        raise ValidationError("factual_risk must be a boolean")
    if not isinstance(row["fact_check_required"], bool):
        raise ValidationError("fact_check_required must be a boolean")
    if not isinstance(row["config_snapshot"], dict):
        raise ValidationError("config_snapshot must be an object")
    note_link = row["note_link"]
    note_target = note_link[2:-2].split("|", 1)[0].strip() if isinstance(note_link, str) else ""
    if (
        not isinstance(note_link, str)
        or not note_link.startswith("[[")
        or not note_link.endswith("]]")
        or not note_target
    ):
        raise ValidationError("note_link must be an Obsidian wikilink")
    if "created_time" in row:
        _validate_non_empty_string(row["created_time"], "created_time")
    if "factual_risk_reason" in row:
        _validate_non_empty_string(row["factual_risk_reason"], "factual_risk_reason")


def _validate_run_manifest_v1(manifest: dict[str, Any]) -> None:
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
    if row_run_ids and row_run_ids != {expected_run_id}:
        raise ValidationError("manifest run_id does not match audit rows")

    if manifest["total_notes"] != len(rows):
        raise ValidationError("manifest total_notes does not match audit row count")

    row_status_counts = _count_row_field(rows, "row_status", ROW_STATUS_COUNT_KEYS)
    if manifest["row_status_counts"] != row_status_counts:
        raise ValidationError("manifest row_status_counts do not match audit rows")

    priority_counts = _count_priority_field(rows, model_led=manifest.get("schema_version") == "2.0.0")
    if manifest["priority_counts"] != priority_counts:
        raise ValidationError("manifest priority_counts do not match audit rows")
    paths = [row["note_path"] for row in rows]
    if len(paths) != len(set(paths)):
        raise ValidationError("duplicate audit row note_path")
    if manifest.get("schema_version") == "2.0.0":
        if any(row.get("schema_version") != "2.0.0" for row in rows):
            raise ValidationError("manifest and row contract versions differ")
        if manifest["model_coverage"] != {state: sum(r["review_status"] == state for r in rows) for state in MODEL_REVIEW_STATES}:
            raise ValidationError("manifest model_coverage does not match audit rows")
        if manifest["integrity_coverage"] != integrity_coverage(rows):
            raise ValidationError("manifest integrity_coverage does not match audit rows")


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


def _validate_non_empty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} must be a non-empty string")


def _validate_finding_code(value: Any, label: str) -> None:
    _validate_non_empty_string(value, label)
    if value not in ALLOWED_FINDING_CODES:
        raise ValidationError(f"Invalid {label}: {value}")


def _validate_dimensions(dimensions: Any) -> None:
    if not isinstance(dimensions, dict):
        raise ValidationError("dimensions must be an object")
    _require_keys(dimensions, set(DIMENSION_KEYS))
    _reject_extra_keys(dimensions, set(DIMENSION_KEYS), "dimensions")
    for key, value in dimensions.items():
        if not _is_score(value):
            raise ValidationError(f"dimensions.{key} must be an integer from 0 to 100")


def _validate_findings(findings: Any) -> None:
    if not isinstance(findings, list):
        raise ValidationError("findings must be an array")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValidationError(f"findings[{index}] must be an object")
        _require_keys(finding, {"code", "message"})
        _reject_extra_keys(finding, {"code", "message"}, f"findings[{index}]")
        _validate_finding_code(finding["code"], f"findings[{index}].code")
        _validate_non_empty_string(finding["message"], f"findings[{index}].message")


def _validate_recommendations(recommendations: Any) -> None:
    if not isinstance(recommendations, list):
        raise ValidationError("recommendations must be an array")
    for index, recommendation in enumerate(recommendations):
        if not isinstance(recommendation, dict):
            raise ValidationError(f"recommendations[{index}] must be an object")
        _require_keys(recommendation, {"mode", "message"})
        _reject_extra_keys(
            recommendation,
            {"mode", "message"},
            f"recommendations[{index}]",
        )
        if recommendation["mode"] not in RECOMMENDATION_MODES:
            raise ValidationError(f"Invalid recommendations[{index}].mode: {recommendation['mode']}")
        _validate_non_empty_string(recommendation["message"], f"recommendations[{index}].message")


def _is_score(value: Any) -> bool:
    return type(value) is int and 0 <= value <= 100


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


def _count_priority_field(rows: list[dict[str, Any]], *, model_led: bool = False) -> dict[str, int]:
    counts = {key: 0 for key in PRIORITY_COUNT_KEYS}
    if model_led:
        counts["unreviewed"] = 0
    for row in rows:
        value = row.get("priority")
        key = "no_change" if value is None else value
        if model_led and value is None and row.get("review_status") != "reviewed":
            key = "unreviewed"
        if key not in counts:
            raise ValidationError(f"audit row priority cannot be counted: {value}")
        counts[key] += 1
    return counts

MODEL_REVIEW_STATES = ("reviewed", "pending", "failed", "unavailable", "stale")
INVENTORY_REQUIRED = {
    "artifact_type", "schema_version", "run_id", "note_path", "note_link",
    "content", "content_hash", "modified_time", "doctrine_version",
    "rubric_version", "prompt_version", "audit_mode", "config_snapshot",
    "integrity_checks",
}


def _safe_note_path(value: Any) -> None:
    from pathlib import PurePosixPath
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValidationError("note_path must be a relative Markdown path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".md":
        raise ValidationError("note_path must stay inside vault and end in .md")


def _validate_integrity_checks(checks: Any) -> None:
    if not isinstance(checks, list):
        raise ValidationError("integrity_checks must be an array")
    keys = {"code", "source", "status", "message", "priority"}
    for check in checks:
        if not isinstance(check, dict):
            raise ValidationError("integrity check must be an object")
        _require_keys(check, keys)
        _reject_extra_keys(check, keys, "integrity check")
        for key in ("code", "source", "message"):
            _validate_non_empty_string(check[key], key)
        if check["status"] not in {"passed", "failed", "not_checked"}:
            raise ValidationError("invalid integrity check status")
        if check["priority"] not in PRIORITIES:
            raise ValidationError("invalid integrity priority")
        if (check["status"] == "failed") != (check["priority"] is not None):
            raise ValidationError("only failed integrity checks have an action priority")


def validate_inventory_row(row: dict[str, Any]) -> None:
    if not isinstance(row, dict) or row.get("artifact_type") != "audit_inventory":
        raise ValidationError("expected unscored inventory; run audit_inventory, not a baseline audit")
    _require_keys(row, INVENTORY_REQUIRED)
    _reject_extra_keys(row, INVENTORY_REQUIRED, "inventory")
    if row["schema_version"] != "1.0.0":
        raise ValidationError("unsupported inventory schema_version")
    for key in INVENTORY_REQUIRED - {"content", "config_snapshot", "integrity_checks"}:
        _validate_non_empty_string(row[key], key)
    _safe_note_path(row["note_path"])
    if not isinstance(row["content"], str) or not isinstance(row["config_snapshot"], dict):
        raise ValidationError("inventory requires content text and config_snapshot object")
    import hashlib
    if row["content_hash"] != hashlib.sha256(row["content"].encode("utf-8")).hexdigest():
        raise ValidationError("inventory content_hash does not match captured content")
    if not row["note_link"].startswith("[[") or not row["note_link"].endswith("]]"):
        raise ValidationError("inventory note_link must be an Obsidian wikilink")
    _validate_integrity_checks(row["integrity_checks"])


def validate_audit_row(row: dict[str, Any], *, default_scan: bool) -> None:
    version = row.get("schema_version") if isinstance(row, dict) else None
    if version in {None, "1.0.0"}:
        return _validate_audit_row_v1(row, default_scan=default_scan)
    if version != "2.0.0":
        raise ValidationError("unsupported audit row schema_version")
    _require_keys(row, AUDIT_ROW_REQUIRED | {"review_status", "integrity_checks"})
    _reject_extra_keys(row, AUDIT_ROW_ALLOWED | {"review_status", "integrity_checks"}, "row")
    _safe_note_path(row["note_path"])
    state = row["review_status"]
    if state not in MODEL_REVIEW_STATES:
        raise ValidationError("invalid review_status")
    _validate_integrity_checks(row["integrity_checks"])
    if state != "reviewed":
        if row["score"] is not None or row["dimensions"] is not None or row["clean"] is not False:
            raise ValidationError("unfinished review requires null quality values and clean=false")
        if row["pending_model"] is not True or row["model_judgment"] is not None or row["findings"]:
            raise ValidationError("unfinished review cannot claim a model result")
    else:
        if row["pending_model"] is not False or row["score"] is None or row["model_judgment"] is None:
            raise ValidationError("reviewed state requires validated model quality")
        if row["model_judgment"].get("schema_version") != "3.0.0":
            raise ValidationError("current rows require provenance-bound model judgment 3.0.0")
        if row["model_judgment"].get("content_hash") != row["content_hash"]:
            raise ValidationError("model judgment content_hash mismatch")
    legacy = {k: v for k, v in row.items() if k not in {"review_status", "integrity_checks"}}
    if state != "reviewed":
        legacy["dimensions"] = {key: 100 for key in DIMENSION_KEYS}
    _validate_audit_row_v1(legacy, default_scan=False)


def validate_run_manifest(manifest: dict[str, Any]) -> None:
    version = manifest.get("schema_version") if isinstance(manifest, dict) else None
    if version in {None, "1.0.0"}:
        return _validate_run_manifest_v1(manifest)
    if version != "2.0.0":
        raise ValidationError("unsupported manifest schema_version")
    extra = {"model_coverage", "integrity_coverage", "audit_mode", "decisions"}
    _require_keys(manifest, RUN_MANIFEST_REQUIRED | extra)
    _reject_extra_keys(manifest, RUN_MANIFEST_REQUIRED | extra, "manifest")
    legacy = {k: v for k, v in manifest.items() if k not in extra}
    legacy["priority_counts"] = {k: v for k, v in manifest["priority_counts"].items() if k != "unreviewed"}
    _validate_count_mapping(manifest["priority_counts"], required_keys=set(PRIORITY_COUNT_KEYS) | {"unreviewed"}, label="priority_counts")
    legacy["outputs"] = {k: v for k, v in manifest["outputs"].items() if k in OUTPUT_KEYS}
    _validate_run_manifest_v1(legacy)
    if set(manifest["outputs"]) - (OUTPUT_KEYS | {"inventory", "evidence", "collection_status"}):
        raise ValidationError("unsupported manifest output")
    if not all(isinstance(v, str) for v in manifest["outputs"].values()):
        raise ValidationError("manifest outputs must be strings")
    _validate_count_mapping(manifest["model_coverage"], required_keys=set(MODEL_REVIEW_STATES), label="model_coverage")
    if sum(manifest["model_coverage"].values()) != manifest["total_notes"]:
        raise ValidationError("model coverage does not reconcile to selected scope")
    _validate_non_empty_string(manifest["audit_mode"], "audit_mode")
    if not isinstance(manifest["integrity_coverage"], dict):
        raise ValidationError("integrity_coverage must be an object")
    for source, counts in manifest["integrity_coverage"].items():
        _validate_non_empty_string(source, "integrity source")
        _validate_count_mapping(counts, required_keys={"passed", "failed", "not_checked"}, label="integrity_coverage")
    if not isinstance(manifest["decisions"], list):
        raise ValidationError("decisions must be an array")
    for decision in manifest["decisions"]:
        if not isinstance(decision, dict) or set(decision) != {"note_path", "status", "message"}:
            raise ValidationError("decision requires note_path, status, message")
        _safe_note_path(decision["note_path"])
        if decision["status"] not in {"completed", "held"}:
            raise ValidationError("invalid recorded decision status")
        _validate_non_empty_string(decision["message"], "decision message")


def integrity_coverage(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    sources = {c["source"] for row in rows for c in row["integrity_checks"]}
    result = {}
    for source in sorted(sources):
        counts = {"passed": 0, "failed": 0, "not_checked": 0}
        for row in rows:
            checks = [c for c in row["integrity_checks"] if c["source"] == source]
            if checks:
                state = "failed" if any(c["status"] == "failed" for c in checks) else ("not_checked" if any(c["status"] == "not_checked" for c in checks) else "passed")
                counts[state] += 1
        result[source] = counts
    return result
