from __future__ import annotations

from typing import Iterable, Mapping


DIMENSION_WEIGHTS: dict[str, float] = {
    "structure": 0.15,
    "atomicity": 0.25,
    "dae_quality": 0.25,
    "clarity": 0.15,
    "connections": 0.10,
    "metadata_card_safety": 0.10,
}

PRIORITY_SEVERITY_PENALTIES: dict[str, int] = {
    "P0": 51,
    "P1": 31,
    "P2": 11,
    "P3": 3,
}

PRIORITY_ORDER: tuple[str, ...] = ("P0", "P1", "P2", "P3")
ADDITIONAL_FINDING_PENALTY = 2
MAX_ADDITIONAL_FINDING_PENALTY = 12


def compute_weighted_score(dimensions: Mapping[str, int | float]) -> int:
    missing = set(DIMENSION_WEIGHTS) - set(dimensions)
    if missing:
        raise ValueError(f"Missing dimensions: {', '.join(sorted(missing))}")

    total = 0.0
    for name, weight in DIMENSION_WEIGHTS.items():
        value = float(dimensions[name])
        if value < 0 or value > 100:
            raise ValueError(f"Dimension {name} must be between 0 and 100")
        total += value * weight
    return int(round(total))


def highest_priority(findings: Iterable[Mapping[str, object]]) -> str | None:
    priorities = {str(finding.get("priority")) for finding in findings}
    for priority in PRIORITY_ORDER:
        if priority in priorities:
            return priority
    return None


def compute_final_score(dimensions: Mapping[str, int | float], findings: list[Mapping[str, object]]) -> int:
    weighted = compute_weighted_score(dimensions)
    priority_penalty = _highest_priority_penalty(findings)
    additional_penalty = min(
        max(0, len(findings) - 1) * ADDITIONAL_FINDING_PENALTY,
        MAX_ADDITIONAL_FINDING_PENALTY,
    )
    return max(1, min(100, weighted - priority_penalty - additional_penalty))


def priority_for_score(score: int) -> str:
    if score < 50:
        return "P0"
    if score < 70:
        return "P1"
    if score < 90:
        return "P2"
    return "P3"


def compute_clean(
    score: int,
    findings: list[Mapping[str, object]],
    *,
    pending_model: bool,
    fact_check_required: bool,
) -> bool:
    if score < 90 or pending_model or fact_check_required:
        return False
    priority = highest_priority(findings)
    return priority in (None, "P3")


def _highest_priority_penalty(findings: Iterable[Mapping[str, object]]) -> int:
    priority = highest_priority(findings)
    if priority is None:
        return 0
    return PRIORITY_SEVERITY_PENALTIES[priority]
