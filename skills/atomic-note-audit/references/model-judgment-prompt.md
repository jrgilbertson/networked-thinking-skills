# Atomic Note Model Judgment Prompt

You audit one Obsidian atomic note at a time. Return strict JSON only.
Do not include Markdown fences, prose outside JSON, scores, or remediation buckets.

## Scoring Contract

The scripts compute score and bucket after your JSON is validated:

```text
score = clamp(100 - total_loss, 1, 100)
```

Bucket bands:

- P0: score 1-49
- P1: score 50-69
- P2: score 70-84
- P3: score 85-99
- no_change: score 100

Finding codes are the scoring source. Use only the exact codes below.
Do not invent codes. Do not prefix codes with `model_`. Unknown codes fail validation.
Return the final findings for the note, not a diff against a deterministic scan.
Do not preserve an issue unless it truly applies to the note content you reviewed.

| code | loss | use when |
|---|---:|---|
| `missing_frontmatter` | 8 | Add YAML frontmatter with the note's metadata. |
| `invalid_dae` | 35 | Add complete Definition, Analogy, and Example content. |
| `definition_too_long` | 20 | Shorten the Definition to 10-50 rendered words. |
| `missing_parent` | 8 | Link this note from a structure note. |
| `malformed_anki` | 18 | Balance START and END markers for Anki card blocks. |
| `anki_yagni` | 5 | Confirm this Anki card is worth memorizing for the intended learner before keeping it. |
| `multi_note` | 45 | Split bundled ideas into separate atomic notes. |
| `misfiled_reference` | 35 | Move source-material notes out of Atomic Notes or rewrite them as DAE notes. |
| `weak_dae` | 15 | Strengthen the DAE content with concrete, self-contained explanations. |
| `not_atomic` | 25 | Rewrite the note around one durable concept. |
| `weak_definition` | 18 | Rewrite the Definition so it is complete, concise, and standalone. |
| `weak_analogy` | 15 | Replace the Analogy with a familiar concrete referent and shared relation. |
| `weak_example` | 15 | Replace the Example with a concrete case that starts with 'For example,'. |
| `unclear` | 15 | Rewrite unclear or misleading prose before relying on the note. |
| `title_body_mismatch` | 15 | Align the proposition-style filename stem and Definition at the same specificity; keep the display title and body compatible with that concept. |
| `duplicate_overlap` | 8 | Review this note against related notes for possible overlap. |
| `factual_risk` | 8 | Mark empirical, current, attributed, or sensitive-domain claims for fact checking. |

De-duplication rules used by scoring:

- If `invalid_dae` applies, do not also emit DAE component codes for the same DAE failure.
- If `invalid_dae` does not apply, DAE component losses are capped at 35.
- DAE component codes are: `definition_too_long`, `weak_analogy`, `weak_dae`, `weak_definition`, `weak_example`.
- If `multi_note` applies, do not also emit `not_atomic` for the same bundled-note problem.
- If factual risk applies, set `factual_risk` and `fact_check_required` to true and emit exactly one `factual_risk` finding.
- If `anki_yagni` applies, do not delete or remove Anki cards automatically; remediation must confirm with the learner because memorization value depends on the learner's domain.

For `title_body_mismatch`, first establish from the user template and nearby
atomic notes that the local convention uses a proposition-style timestamp
filename. A timestamp prefix alone is not enough. In mixed or unclear vaults,
follow the target folder, template, and note-type convention and do not infer a
filename mismatch without evidence. When the proposition rule applies, emit
`title_body_mismatch` if the filename stem expresses a broader, narrower, or
different concept than the first definition sentence in `Back:` for `Basic`,
the cloze-bearing definition sentence for `Cloze`, or the first visible
Definition sentence for non-Anki DAE. A concise display title may differ in
wording, but emit the finding if it contradicts or broadens that concept.

Examples:

- A note with no complete DAE structure should emit `invalid_dae`, not `weak_definition` or `weak_example` for the same missing structure.
- A note with weak Definition, Analogy, and Example content can emit component codes, but scoring caps those DAE component losses at 35.
- A note that bundles two separate concepts should emit `multi_note`, not both `multi_note` and `not_atomic` for that bundled-note problem.
- A note with check-worthy factual claims should emit one `factual_risk` finding and set both `factual_risk` and `fact_check_required` to true.
- A synced Anki card for a reference-only, low-stakes, or rarely recalled concept can emit `anki_yagni`, but do not use it merely because the topic is advanced, specialized, medical, academic, or outside your own work.
- A synced Anki card that only asks for a person's name pronunciation or other reference-only person detail can emit `anki_yagni` before rehoming or removing the card.

## Output JSON Shape

Return this object shape exactly:

```json
{
  "schema_version": "1.0.0",
  "note_path": "Atomic Notes/example.md",
  "dimension_adjustments": {},
  "findings": [
    {
      "code": "invalid_dae",
      "message": "Brief note-specific explanation.",
      "evidence": [
        {
          "excerpt": "40 words or fewer from the note",
          "reason": "Why this excerpt supports the finding."
        }
      ]
    }
  ],
  "factual_risk": false,
  "factual_risk_reason": null,
  "fact_check_required": false,
  "evidence": []
}
```

Use an empty `findings` array only when no allowed finding code applies.
Do not output a score. Do not output P0, P1, P2, P3, or no_change; the scripts derive that from the score.
