from __future__ import annotations

from typing import Iterable, Mapping


FINDING_LOSSES: dict[str, int] = {
    "multi_note": 45,
    "invalid_dae": 35,
    "misfiled_reference": 35,
    "not_atomic": 25,
    "definition_too_long": 20,
    "weak_definition": 18,
    "malformed_anki": 18,
    "weak_dae": 15,
    "weak_analogy": 15,
    "weak_example": 15,
    "unclear": 15,
    "title_body_mismatch": 15,
    "missing_parent": 8,
    "duplicate_overlap": 8,
    "factual_risk": 8,
}

CODE_ALIASES: dict[str, str] = {
    "multi_note_file": "multi_note",
    "model_multi_note": "multi_note",
    "missing_dae": "invalid_dae",
    "model_invalid_dae": "invalid_dae",
    "model_misfiled_reference": "misfiled_reference",
    "model_not_atomic": "not_atomic",
    "model_weak_definition": "weak_definition",
    "model_weak_analogy": "weak_analogy",
    "model_weak_example": "weak_example",
    "model_unclear": "unclear",
    "model_title_body_mismatch": "title_body_mismatch",
    "model_duplicate_overlap": "duplicate_overlap",
    "model_factual_risk": "factual_risk",
}

PRIORITY_ORDER: tuple[str, ...] = ("P0", "P1", "P2", "P3")
NO_CHANGE_BUCKET = "no_change"
BUCKET_ORDER: tuple[str, ...] = PRIORITY_ORDER + (NO_CHANGE_BUCKET,)
DEFAULT_FINDING_LOSS = 8
DAE_COMPONENT_CODES = {
    "definition_too_long",
    "weak_definition",
    "weak_dae",
    "weak_analogy",
    "weak_example",
}
DAE_COMPONENT_LOSS_CAP = 35


def canonicalize_findings(findings: Iterable[Mapping[str, object]]) -> set[str]:
    codes: set[str] = set()
    for finding in findings:
        raw_code = finding.get("code")
        if not isinstance(raw_code, str) or not raw_code:
            continue
        codes.add(CODE_ALIASES.get(raw_code, raw_code))

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
        FINDING_LOSSES.get(code, DEFAULT_FINDING_LOSS)
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
