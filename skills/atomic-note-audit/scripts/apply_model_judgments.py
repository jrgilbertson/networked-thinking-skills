from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from finding_codes import FINDING_MESSAGES, FINDING_RECOMMENDATION_MODES
from model_contract import validate_model_judgment
from schema_validation import (
    DIMENSION_KEYS,
    PRIORITY_COUNT_KEYS,
    ROW_STATUS_COUNT_KEYS,
    ValidationError,
    validate_audit_row,
    validate_audit_run_pair,
    validate_run_manifest,
)
from scoring import bucket_for_score, canonicalize_findings, compute_clean, compute_final_score


DETERMINISTIC_RETAINED_CODES = frozenset(
    {
        "missing_frontmatter",
        "missing_parent",
        "malformed_anki",
        "duplicate_overlap",
    }
)


def apply_model_judgments(
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    judgments: list[dict[str, Any]],
    *,
    allow_missing: bool = False,
    outputs: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_run_manifest(manifest)
    for row in rows:
        validate_audit_row(row, default_scan=True)
    validate_audit_run_pair(rows, manifest)

    judgment_by_path = _judgment_map(judgments)
    row_paths = {str(row["note_path"]) for row in rows}
    extra_paths = sorted(set(judgment_by_path) - row_paths)
    if extra_paths:
        raise ValidationError(f"model judgment note_path has no audit row: {extra_paths[0]}")

    for row in rows:
        note_path = str(row["note_path"])
        judgment = judgment_by_path.get(note_path)
        if judgment is not None and judgment["prompt_version"] != row["prompt_version"]:
            raise ValidationError(
                f"model judgment prompt_version mismatch for {note_path}: "
                f"expected {row['prompt_version']}, got {judgment['prompt_version']}"
            )

    missing_paths = sorted(row_paths - set(judgment_by_path))
    if missing_paths and not allow_missing:
        raise ValidationError(
            f"missing model judgments for {len(missing_paths)} audit rows; first missing: {missing_paths[0]}"
        )

    merged_rows = [
        _merge_row(row, judgment_by_path.get(str(row["note_path"])))
        for row in rows
    ]
    merged_manifest = _merged_manifest(manifest, merged_rows, outputs or {})

    for row in merged_rows:
        validate_audit_row(row, default_scan=True)
    validate_audit_run_pair(merged_rows, merged_manifest)
    return sorted(merged_rows, key=lambda row: str(row["note_path"])), merged_manifest


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        rows = _read_jsonl(args.audit_jsonl)
        manifest = _read_json(args.manifest)
        judgments = _read_jsonl(args.model_judgments)
        merged_rows, merged_manifest = apply_model_judgments(
            rows,
            manifest,
            judgments,
            allow_missing=args.allow_missing,
            outputs=_manifest_outputs(args),
        )
        _write_jsonl(args.output_jsonl, merged_rows)
        _write_json(args.output_manifest, merged_manifest)
    except (ValidationError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"rows={len(merged_rows)} model_judgments={len(judgments)}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply model judgments to Atomic Note audit rows.")
    parser.add_argument("--audit-jsonl", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-judgments", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow partial model judgment coverage and mark unmatched rows as pending_model.",
    )
    return parser.parse_args(argv)


def _merge_row(row: dict[str, Any], judgment: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(row)
    if judgment is None:
        merged["pending_model"] = True
        score = merged["score"]
        merged["clean"] = (
            compute_clean(
                score,
                pending_model=True,
                fact_check_required=bool(merged["fact_check_required"]),
            )
            if score is not None
            else False
        )
        return merged

    validate_model_judgment(judgment)
    findings = _combined_findings(
        _retained_deterministic_findings(row.get("findings", [])),
        judgment.get("findings", []),
    )
    factual_risk = _has_factual_risk(findings) or bool(judgment["factual_risk"])
    if factual_risk and not _has_factual_risk(findings):
        findings = [
            *findings,
            {
                "code": "factual_risk",
                "message": FINDING_MESSAGES["factual_risk"],
            },
        ]
        findings = _canonical_findings(findings)

    fact_check_required = factual_risk or bool(judgment["fact_check_required"])
    score = compute_final_score(findings)

    merged.update(
        {
            "score": score,
            "priority": bucket_for_score(score),
            "clean": compute_clean(
                score,
                pending_model=False,
                fact_check_required=fact_check_required,
            ),
            "pending_model": False,
            "dimensions": _apply_dimension_adjustments(row["dimensions"], judgment["dimension_adjustments"]),
            "findings": findings,
            "recommendations": _recommendations_for_findings(findings),
            "model_judgment": deepcopy(judgment),
            "cache_status": "miss",
            "factual_risk": factual_risk,
            "fact_check_required": fact_check_required,
        }
    )
    if fact_check_required:
        merged["factual_risk_reason"] = (
            judgment.get("factual_risk_reason")
            or row.get("factual_risk_reason")
            or "Contains factual claims that need verification."
        )
    else:
        merged.pop("factual_risk_reason", None)
    return merged


def _combined_findings(
    base_findings: Iterable[dict[str, Any]],
    model_findings: Iterable[dict[str, Any]],
) -> list[dict[str, str]]:
    by_code: dict[str, dict[str, str]] = {}
    for finding in [*base_findings, *model_findings]:
        code = finding.get("code")
        message = finding.get("message")
        if not isinstance(code, str) or not isinstance(message, str):
            continue
        by_code.setdefault(code, {"code": code, "message": message})
    return _canonical_findings(by_code.values())


def _retained_deterministic_findings(findings: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    retained: list[dict[str, str]] = []
    for finding in findings:
        code = finding.get("code")
        message = finding.get("message")
        if (
            isinstance(code, str)
            and isinstance(message, str)
            and code in DETERMINISTIC_RETAINED_CODES
        ):
            retained.append({"code": code, "message": message})
    return retained


def _canonical_findings(findings: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    finding_list = list(findings)
    canonical_codes = canonicalize_findings(finding_list)
    return [finding for finding in finding_list if finding["code"] in canonical_codes]


def _recommendations_for_findings(findings: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "mode": FINDING_RECOMMENDATION_MODES[finding["code"]],
            "message": finding["message"],
        }
        for finding in findings
    ]


def _apply_dimension_adjustments(
    dimensions: dict[str, Any],
    adjustments: dict[str, Any],
) -> dict[str, int]:
    adjusted: dict[str, int] = {}
    for key in DIMENSION_KEYS:
        value = dimensions[key]
        adjustment = adjustments.get(key, 0)
        if type(value) is not int or type(adjustment) is not int:
            raise ValidationError(f"dimension {key} must be an integer")
        adjusted[key] = max(0, min(100, value + adjustment))
    return adjusted


def _has_factual_risk(findings: Iterable[dict[str, Any]]) -> bool:
    return any(finding.get("code") == "factual_risk" for finding in findings)


def _judgment_map(judgments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for index, judgment in enumerate(judgments, start=1):
        try:
            validate_model_judgment(judgment)
        except ValidationError as exc:
            raise ValidationError(f"model judgment line {index}: {exc}") from exc
        note_path = str(judgment["note_path"])
        if note_path in mapped:
            raise ValidationError(f"duplicate model judgment note_path: {note_path}")
        mapped[note_path] = judgment
    return mapped


def _merged_manifest(
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    outputs: dict[str, str],
) -> dict[str, Any]:
    merged = deepcopy(manifest)
    merged["row_status_counts"] = _count_row_statuses(rows)
    merged["priority_counts"] = _count_priorities(rows)
    merged["validation_status"] = "passed"
    merged["outputs"] = outputs
    merged["errors"] = []
    validate_run_manifest(merged)
    return merged


def _count_row_statuses(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in ROW_STATUS_COUNT_KEYS}
    for row in rows:
        counts[str(row["row_status"])] += 1
    return counts


def _count_priorities(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: 0 for key in PRIORITY_COUNT_KEYS}
    for row in rows:
        key = "no_change" if row["priority"] is None else str(row["priority"])
        counts[key] += 1
    return counts


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValidationError(f"{path}:{line_number}: line must be a JSON object")
            rows.append(value)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: JSON document must be an object")
    return value


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _manifest_outputs(args: argparse.Namespace) -> dict[str, str]:
    return {
        "audit_rows": str(args.output_jsonl),
        "model_judgments": str(args.model_judgments),
        "manifest": str(args.output_manifest),
    }


if __name__ == "__main__":
    raise SystemExit(main())
