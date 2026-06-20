# Rubric Companion

This is the human-readable companion for the audit rubric. The source of truth
for installed-skill users is `scripts/finding_codes.py`.

Maintainer note: in this repo, the canonical development source remains
[`shared/scripts/finding_codes.py`](../shared/scripts/finding_codes.py); change
that module first when changing scoring doctrine.

## Score

Scores use a single loss budget from finding codes:

```text
score = clamp(100 - total_loss, 1, 100)
```

Finding codes must come from the controlled vocabulary. Unknown codes fail
validation. The loss table and de-duplication rules live in the source module
and the generated model prompt.

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

`anki_yagni` is a low-severity sanity check for synced Anki notes that may not
be worth memorizing for the intended learner. It is not an automatic delete
recommendation. Remediation pauses for learner judgment because specialized
learners may need cards that look unnecessary outside their domain.

## How To Read Results

- Use bucket and score to decide work order.
- Use dimension scores as diagnostics for what kind of edit is needed.
- Use findings and recommendations to choose a remediation mode.
- Use the JSONL row and manifest as the durable audit record.
