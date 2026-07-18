from __future__ import annotations

import hashlib
import json
from typing import Any

from finding_codes import ALLOWED_FINDING_CODES
from schema_validation import DIMENSION_KEYS, ValidationError


MODEL_JUDGMENT_REQUIRED = {
    "schema_version",
    "prompt_version",
    "note_path",
    "dimension_adjustments",
    "findings",
    "factual_risk",
    "factual_risk_reason",
    "fact_check_required",
    "evidence",
}
MODEL_JUDGMENT_SCHEMA_VERSION = "2.0.0"
FINDING_REQUIRED = {"code", "message"}
FINDING_ALLOWED = FINDING_REQUIRED | {"evidence"}
EVIDENCE_KEYS = {"excerpt", "reason"}
MAX_EVIDENCE_EXCERPT_WORDS = 40


def build_cache_key(
    *,
    note_path: str,
    content_hash: str,
    doctrine_version: str,
    rubric_version: str,
    prompt_version: str,
    audit_mode: str,
) -> str:
    payload = {
        "audit_mode": audit_mode,
        "content_hash": content_hash,
        "doctrine_version": doctrine_version,
        "note_path": note_path,
        "prompt_version": prompt_version,
        "rubric_version": rubric_version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"model-judgment:v1:{digest}"


def validate_model_judgment(judgment: dict[str, Any]) -> None:
    if not isinstance(judgment, dict):
        raise ValidationError("model_judgment must be an object")

    _require_keys(judgment, MODEL_JUDGMENT_REQUIRED, "model_judgment")
    _reject_extra_keys(judgment, MODEL_JUDGMENT_REQUIRED, "model_judgment")
    if judgment["schema_version"] != MODEL_JUDGMENT_SCHEMA_VERSION:
        raise ValidationError(
            "model_judgment.schema_version must be "
            f"{MODEL_JUDGMENT_SCHEMA_VERSION}"
        )
    _validate_non_empty_string(judgment["prompt_version"], "model_judgment.prompt_version")
    _validate_non_empty_string(judgment["note_path"], "model_judgment.note_path")
    _validate_dimension_adjustments(judgment["dimension_adjustments"])
    _validate_findings(judgment["findings"])
    _validate_factual_risk(judgment)

    if not isinstance(judgment["fact_check_required"], bool):
        raise ValidationError("model_judgment.fact_check_required must be a boolean")

    _validate_evidence_array(judgment["evidence"], "model_judgment.evidence")


def _require_keys(data: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - set(data)
    if missing:
        raise ValidationError(f"{label} missing required keys: {', '.join(sorted(missing))}")


def _reject_extra_keys(data: dict[str, Any], allowed_keys: set[str] | tuple[str, ...], label: str) -> None:
    extra = set(data) - set(allowed_keys)
    if extra:
        raise ValidationError(f"{label} has unsupported keys: {', '.join(sorted(extra))}")


def _validate_non_empty_string(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} must be a non-empty string")


def _validate_dimension_adjustments(adjustments: Any) -> None:
    if not isinstance(adjustments, dict):
        raise ValidationError("model_judgment.dimension_adjustments must be an object")
    _reject_extra_keys(adjustments, DIMENSION_KEYS, "model_judgment.dimension_adjustments")
    for key, value in adjustments.items():
        if type(value) is not int or value < -100 or value > 100:
            raise ValidationError(
                f"model_judgment.dimension_adjustments.{key} must be an integer from -100 to 100"
            )


def _validate_findings(findings: Any) -> None:
    if not isinstance(findings, list):
        raise ValidationError("model_judgment.findings must be an array")
    for index, finding in enumerate(findings):
        label = f"model_judgment.findings[{index}]"
        if not isinstance(finding, dict):
            raise ValidationError(f"{label} must be an object")
        _require_keys(finding, FINDING_REQUIRED, label)
        _reject_extra_keys(finding, FINDING_ALLOWED, label)
        _validate_finding_code(finding["code"], f"{label}.code")
        _validate_non_empty_string(finding["message"], f"{label}.message")
        if "evidence" in finding:
            _validate_evidence_array(finding["evidence"], f"{label}.evidence")


def _validate_factual_risk(judgment: dict[str, Any]) -> None:
    if not isinstance(judgment["factual_risk"], bool):
        raise ValidationError("model_judgment.factual_risk must be a boolean")

    reason = judgment["factual_risk_reason"]
    if reason is not None:
        _validate_non_empty_string(reason, "model_judgment.factual_risk_reason")
    if judgment["factual_risk"] is True and reason is None:
        raise ValidationError("model_judgment.factual_risk_reason must explain factual_risk")


def _validate_finding_code(value: Any, label: str) -> None:
    _validate_non_empty_string(value, label)
    if value not in ALLOWED_FINDING_CODES:
        raise ValidationError(f"Invalid {label}: {value}")


def _validate_evidence_array(evidence: Any, label: str) -> None:
    if not isinstance(evidence, list):
        raise ValidationError(f"{label} must be an array")
    for index, item in enumerate(evidence):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise ValidationError(f"{item_label} must be an object")
        _require_keys(item, EVIDENCE_KEYS, item_label)
        _reject_extra_keys(item, EVIDENCE_KEYS, item_label)
        if not isinstance(item["excerpt"], str):
            raise ValidationError(f"{item_label}.excerpt must be a string")
        _validate_non_empty_string(item["reason"], f"{item_label}.reason")
        if len(item["excerpt"].split()) > MAX_EVIDENCE_EXCERPT_WORDS:
            raise ValidationError(f"{item_label}.excerpt must be {MAX_EVIDENCE_EXCERPT_WORDS} words or fewer")
