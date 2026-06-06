# Atomic Note Audit Rubric

Scores use six weighted dimensions:

- Structure: 15
- Atomicity: 25
- DAE Quality: 25
- Clarity: 15
- Connections: 10
- Metadata & Optional Card Safety: 10

Priority means remediation urgency:

- P0: critical structural hazards.
- P1: high-impact doctrine failure.
- P2: meaningful improvement.
- P3: polish.

A clean note has no P0-P2 findings, score at least 90, no pending model-audit flag, and no pending fact-check-required flag. P3 findings are allowed.

DAE doctrine failures include missing DAE content and overlong Definitions. A
Definition longer than 50 rendered words receives `definition_too_long` so it can
be shortened without misclassifying the note as a multi-note or reference note.

`factual_risk` means a sentence contains a claim that should be checked before it
is relied on: empirical numbers, current or versioned claims, source-attributed
claims, legal/medical/financial/security claims with a check-worthy predicate,
causal claims, or named product configuration/classification/lifecycle claims.
Formal quantifiers in math, logic, acronym definitions, stable domain
definitions, and generic examples do not trigger factual-risk by themselves.
