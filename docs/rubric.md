# Rubric Companion

This is the human-readable companion for the audit rubric. The source of truth
is [`shared/references/audit-rubric.md`](../shared/references/audit-rubric.md).
Change that reference first when changing scoring doctrine.

## Weights

- Structure: 15
- Atomicity: 25
- DAE Quality: 25
- Clarity: 15
- Connections: 10
- Metadata & Optional Card Safety: 10

Scores are weighted from the six dimension scores. Priority then caps the final
score for urgent findings.

## Priority

Priority means remediation urgency, not a score band:

- P0: Critical structural hazards.
- P1: High-impact doctrine failures.
- P2: Meaningful improvements.
- P3: Polish.

A clean note has no P0-P2 findings, scores at least 90, has no pending model
audit flag, and has no pending fact-check-required flag. P3 findings can still
exist on a clean note.

An overlong Definition is a P1 DAE doctrine failure reported as
`definition_too_long`. This means the note should be shortened in place, not
automatically split or rehomed.

`factual_risk` is for sentence-level claims that need verification before
reliance: empirical numbers, current/versioned claims, source-attributed claims,
sensitive-domain claims with a check-worthy predicate, causal claims, or named
product configuration/classification/lifecycle claims. Formal math, logic,
acronym, stable definition quantifiers, and generic examples do not count by
themselves.

## How To Read Results

- Use priority to decide work order.
- Use dimension scores to decide what kind of edit is needed.
- Use findings and recommendations to choose a remediation mode.
- Use the JSONL row and manifest as the durable audit record.
