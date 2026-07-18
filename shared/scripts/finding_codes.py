from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FindingCodeSpec:
    loss: int
    message: str
    recommendation_mode: str


FINDING_CODE_SPECS: dict[str, FindingCodeSpec] = {
    "missing_frontmatter": FindingCodeSpec(
        loss=8,
        message="Add YAML frontmatter with the note's metadata.",
        recommendation_mode="improve-in-place",
    ),
    "invalid_dae": FindingCodeSpec(
        loss=35,
        message="Add complete Definition, Analogy, and Example content.",
        recommendation_mode="improve-in-place",
    ),
    "definition_too_long": FindingCodeSpec(
        loss=20,
        message="Shorten the Definition to 10-50 rendered words.",
        recommendation_mode="improve-in-place",
    ),
    "missing_parent": FindingCodeSpec(
        loss=8,
        message="Link this note from a structure note.",
        recommendation_mode="link-parent",
    ),
    "malformed_anki": FindingCodeSpec(
        loss=18,
        message="Balance START and END markers for Anki card blocks.",
        recommendation_mode="improve-in-place",
    ),
    "anki_yagni": FindingCodeSpec(
        loss=5,
        message="Confirm this Anki card is worth memorizing for the intended learner before keeping it.",
        recommendation_mode="confirm-anki-utility",
    ),
    "multi_note": FindingCodeSpec(
        loss=45,
        message="Split bundled ideas into separate atomic notes.",
        recommendation_mode="split-multi-note",
    ),
    "misfiled_reference": FindingCodeSpec(
        loss=35,
        message="Move source-material notes out of Atomic Notes or rewrite them as DAE notes.",
        recommendation_mode="rehome-non-DAE",
    ),
    "weak_dae": FindingCodeSpec(
        loss=15,
        message="Strengthen the DAE content with concrete, self-contained explanations.",
        recommendation_mode="improve-in-place",
    ),
    "not_atomic": FindingCodeSpec(
        loss=25,
        message="Rewrite the note around one durable concept.",
        recommendation_mode="improve-in-place",
    ),
    "weak_definition": FindingCodeSpec(
        loss=18,
        message="Rewrite the Definition so it is complete, concise, and standalone.",
        recommendation_mode="improve-in-place",
    ),
    "weak_analogy": FindingCodeSpec(
        loss=15,
        message="Replace the Analogy with a familiar concrete referent and shared relation.",
        recommendation_mode="improve-in-place",
    ),
    "weak_example": FindingCodeSpec(
        loss=15,
        message="Replace the Example with a concrete case that starts with 'For example,'.",
        recommendation_mode="improve-in-place",
    ),
    "unclear": FindingCodeSpec(
        loss=15,
        message="Rewrite unclear or misleading prose before relying on the note.",
        recommendation_mode="improve-in-place",
    ),
    "title_body_mismatch": FindingCodeSpec(
        loss=15,
        message=(
            "Align the proposition-style filename stem and Definition at the same "
            "specificity; keep the display title and body compatible with that concept."
        ),
        recommendation_mode="improve-in-place",
    ),
    "duplicate_overlap": FindingCodeSpec(
        loss=8,
        message="Review this note against related notes for possible overlap.",
        recommendation_mode="duplicate-overlap-review",
    ),
    "factual_risk": FindingCodeSpec(
        loss=8,
        message="Mark empirical, current, attributed, or sensitive-domain claims for fact checking.",
        recommendation_mode="mark-factual-risk",
    ),
}

ALLOWED_FINDING_CODES = tuple(FINDING_CODE_SPECS)
FINDING_LOSSES = {code: spec.loss for code, spec in FINDING_CODE_SPECS.items()}
FINDING_MESSAGES = {code: spec.message for code, spec in FINDING_CODE_SPECS.items()}
FINDING_RECOMMENDATION_MODES = {
    code: spec.recommendation_mode for code, spec in FINDING_CODE_SPECS.items()
}

DAE_COMPONENT_CODES = frozenset(
    {
        "definition_too_long",
        "weak_definition",
        "weak_dae",
        "weak_analogy",
        "weak_example",
    }
)
DAE_COMPONENT_LOSS_CAP = 35
