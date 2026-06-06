# Atomic Note Audit Rubric

Final score is a 1-100 remediation urgency score. A perfect vault has an
average score of 100. Compute each row score with a single loss budget:

```text
score = clamp(100 - total_loss, 1, 100)
```

Findings create loss once. Finding priority labels may explain findings for
reviewers, but they do not feed the score. Score alone determines the
remediation bucket.

Finding losses:

- Multi-note file: 45
- Missing or invalid DAE: 35
- Misfiled reference: 35
- Not atomic: 25
- Definition too long: 20
- Weak definition: 18
- Malformed Anki: 18
- Weak DAE, analogy, or example: 15
- Unclear note: 15
- Title/body mismatch: 15
- Missing parent: 8
- Duplicate overlap: 8
- Factual risk: 8
- Unknown future finding code: 8

Semantic de-duplication applies before scoring:

- Deterministic and model factual-risk findings count once.
- Deterministic and model duplicate-overlap findings count once.
- Deterministic and model multi-note findings count once.
- Missing DAE and invalid DAE count as one invalid-DAE loss.
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

DAE doctrine failures include missing DAE content and overlong Definitions. A
Definition longer than 50 rendered words receives `definition_too_long` so it can
be shortened without misclassifying the note as a multi-note or reference note.

`factual_risk` means a sentence contains a claim that should be checked before it
is relied on: empirical numbers, current or versioned claims, source-attributed
claims, legal/medical/financial/security claims with a check-worthy predicate,
causal claims, or named product configuration/classification/lifecycle claims.
Formal quantifiers in math, logic, acronym definitions, stable domain
definitions, and generic examples do not trigger factual-risk by themselves.
