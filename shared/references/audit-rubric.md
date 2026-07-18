# Atomic Note Audit Rubric

The scoring source of truth is `shared/scripts/finding_codes.py`. The
model-judgment prompt is generated from that source by
`python3 -m shared.scripts.model_prompt`.

Final score is a 1-100 remediation urgency score. A perfect vault has an
average score of 100. Compute each row score with a single loss budget:

```text
score = clamp(100 - total_loss, 1, 100)
```

Findings create loss once. Score alone determines the remediation bucket.
Finding-level priority labels are not part of the JSON contract.

Finding losses are defined by canonical code in `shared/scripts/finding_codes.py`.
Unknown finding codes fail validation.

Semantic de-duplication applies before scoring:

- If invalid DAE is present, weaker DAE component findings do not add extra
  loss.
- If invalid DAE is absent, DAE component findings are capped at 35 total.
- If multi-note is present, a generic not-atomic finding does not add extra
  loss.

Priority is assigned from the final score:

- P0: 1-49, critical remediation.
- P1: 50-69, high-impact remediation.
- P2: 70-84, meaningful improvement.
- P3: 85-99, polish.
- No changes: 100.

A clean note has score 100, no pending model-audit flag, and no pending
fact-check-required flag.

`anki_yagni` is a low-severity memorization-utility sanity check for synced
Anki notes. Use it when the card appears reference-only, low-stakes, or unlikely
to be worth recall practice for the intended learner. Do not use it merely
because the topic is advanced, specialized, medical, academic, or outside the
auditor's own work. When the learner explicitly wants to practice factual recall
or trivia, treat that goal as evidence of memorization utility; do not emit
`anki_yagni` solely because the card is recall-oriented or lacks an analytical
synthesis purpose. Pronunciation-only person cards and other reference-only
person details remain valid `anki_yagni` candidates when learner utility is
unclear. Remediation must stop for learner judgment before removing Anki from
the note.

DAE doctrine failures include missing DAE content and overlong Definitions. A
Definition longer than 50 rendered words receives `definition_too_long` so it can
be shortened without misclassifying the note as a multi-note or reference note.

`factual_risk` means a sentence contains a claim that should be checked before it
is relied on: empirical numbers, current or versioned claims, source-attributed
claims, legal/medical/financial/security claims with a check-worthy predicate,
causal claims, or named product configuration/classification/lifecycle claims.
Formal quantifiers in math, logic, acronym definitions, stable domain
definitions, and generic examples do not trigger factual-risk by themselves.
