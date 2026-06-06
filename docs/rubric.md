# Rubric Companion

This is the human-readable companion for the audit rubric. The source of truth
is [`shared/references/audit-rubric.md`](../shared/references/audit-rubric.md).
Change that reference first when changing scoring doctrine.

## Score

Scores use a single loss budget from finding codes:

```text
score = clamp(100 - total_loss, 1, 100)
```

Finding priority labels can help explain a finding, but they do not feed the
score. The loss table and de-duplication rules live in the source rubric.

## Bucket

Bucket means remediation urgency and is derived from score:

- P0: Critical structural hazards.
- P1: High-impact doctrine failures.
- P2: Meaningful improvements.
- P3: Polish.
- No changes: Score 100.

A clean note scores 100, has no pending model audit flag, and has no pending
fact-check-required flag.

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

- Use bucket and score to decide work order.
- Use dimension scores as diagnostics for what kind of edit is needed.
- Use findings and recommendations to choose a remediation mode.
- Use the JSONL row and manifest as the durable audit record.
