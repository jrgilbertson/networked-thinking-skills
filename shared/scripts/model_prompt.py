from __future__ import annotations

from shared.scripts.finding_codes import (
    ALLOWED_FINDING_CODES,
    DAE_COMPONENT_CODES,
    DAE_COMPONENT_LOSS_CAP,
    FINDING_CODE_SPECS,
)
from shared.scripts.scoring import NO_CHANGE_BUCKET


def render_model_judgment_prompt() -> str:
    lines = [
        "# Atomic Note Model Judgment Prompt",
        "",
        "You audit one Obsidian atomic note at a time. Return strict JSON only.",
        "Do not include Markdown fences, prose outside JSON, scores, or remediation buckets.",
        "",
        "## Scoring Contract",
        "",
        "The scripts compute score and bucket after your JSON is validated:",
        "",
        "```text",
        "score = clamp(100 - total_loss, 1, 100)",
        "```",
        "",
        "Bucket bands:",
        "",
        "- P0: score 1-49",
        "- P1: score 50-69",
        "- P2: score 70-84",
        "- P3: score 85-99",
        f"- {NO_CHANGE_BUCKET}: score 100",
        "",
        "Finding codes are the scoring source. Use only the exact codes below.",
        "Do not invent codes. Do not prefix codes with `model_`. Unknown codes fail validation.",
        "Return the final findings for the note, not a diff against a deterministic scan.",
        "Do not preserve an issue unless it truly applies to the note content you reviewed.",
        "",
        "| code | loss | use when |",
        "|---|---:|---|",
    ]
    lines.extend(
        f"| `{code}` | {FINDING_CODE_SPECS[code].loss} | {FINDING_CODE_SPECS[code].message} |"
        for code in ALLOWED_FINDING_CODES
    )
    lines.extend(
        [
            "",
            "De-duplication rules used by scoring:",
            "",
            "- If `invalid_dae` applies, do not also emit DAE component codes for the same DAE failure.",
            f"- If `invalid_dae` does not apply, DAE component losses are capped at {DAE_COMPONENT_LOSS_CAP}.",
            "- DAE component codes are: "
            + ", ".join(f"`{code}`" for code in sorted(DAE_COMPONENT_CODES))
            + ".",
            "- If `multi_note` applies, do not also emit `not_atomic` for the same bundled-note problem.",
            "- If factual risk applies, set `factual_risk` and `fact_check_required` to true and emit exactly one `factual_risk` finding.",
            "",
            "## Output JSON Shape",
            "",
            "Return this object shape exactly:",
            "",
            "```json",
            "{",
            '  "schema_version": "1.0.0",',
            '  "note_path": "Atomic Notes/example.md",',
            '  "dimension_adjustments": {},',
            '  "findings": [',
            "    {",
            '      "code": "invalid_dae",',
            '      "message": "Brief note-specific explanation.",',
            '      "evidence": [',
            "        {",
            '          "excerpt": "40 words or fewer from the note",',
            '          "reason": "Why this excerpt supports the finding."',
            "        }",
            "      ]",
            "    }",
            "  ],",
            '  "factual_risk": false,',
            '  "factual_risk_reason": null,',
            '  "fact_check_required": false,',
            '  "evidence": []',
            "}",
            "```",
            "",
            "Use an empty `findings` array only when no allowed finding code applies.",
            "Do not output a score. Do not output P0, P1, P2, P3, or no_change; the scripts derive that from the score.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    print(render_model_judgment_prompt(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
