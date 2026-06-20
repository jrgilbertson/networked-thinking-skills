from __future__ import annotations

from collections.abc import Iterable, Mapping

from finding_codes import (
    ALLOWED_FINDING_CODES,
    DAE_COMPONENT_CODES,
    DAE_COMPONENT_LOSS_CAP,
    FINDING_LOSSES,
)

PRIORITY_ORDER: tuple[str, ...] = ("P0", "P1", "P2", "P3")
NO_CHANGE_BUCKET = "no_change"
BUCKET_ORDER: tuple[str, ...] = PRIORITY_ORDER + (NO_CHANGE_BUCKET,)


def canonicalize_findings(findings: Iterable[Mapping[str, object]]) -> set[str]:
    codes: set[str] = set()
    for finding in findings:
        raw_code = finding.get("code")
        if not isinstance(raw_code, str) or not raw_code:
            continue
        if raw_code not in ALLOWED_FINDING_CODES:
            raise ValueError(f"Unknown finding code: {raw_code}")
        codes.add(raw_code)

    if "multi_note" in codes:
        codes.discard("not_atomic")
    if "invalid_dae" in codes:
        codes.difference_update(DAE_COMPONENT_CODES)
    return codes


def compute_loss(findings: Iterable[Mapping[str, object]]) -> int:
    codes = canonicalize_findings(findings)
    dae_component_loss = min(
        sum(FINDING_LOSSES[code] for code in codes if code in DAE_COMPONENT_CODES),
        DAE_COMPONENT_LOSS_CAP,
    )
    non_dae_loss = sum(
        FINDING_LOSSES[code]
        for code in codes
        if code not in DAE_COMPONENT_CODES
    )
    return non_dae_loss + dae_component_loss


def compute_final_score(findings: Iterable[Mapping[str, object]]) -> int:
    return max(1, min(100, 100 - compute_loss(findings)))


def bucket_for_score(score: int) -> str | None:
    if score < 50:
        return "P0"
    if score < 70:
        return "P1"
    if score < 85:
        return "P2"
    if score < 100:
        return "P3"
    return None


def compute_clean(
    score: int,
    *,
    pending_model: bool,
    fact_check_required: bool,
) -> bool:
    return score == 100 and not pending_model and not fact_check_required


priority_for_score = bucket_for_score
