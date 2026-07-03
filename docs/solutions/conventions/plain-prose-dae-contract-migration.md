---
title: Plain-Prose DAE Contract Migrations Need Parser, Fixture, and Version Alignment
date: 2026-07-03
last_updated: 2026-07-03
category: docs/solutions/conventions
module: networked-thinking atomic-note audit
problem_type: convention
component: tooling
severity: medium
applies_when:
  - Changing deterministic atomic-note audit rules
  - Changing Networked Thinking atomic-note doctrine
  - Syncing generated skill artifacts from shared sources
tags: [atomic-notes, dae, doctrine, artifact-sync, contract-versions]
---

# Plain-Prose DAE Contract Migrations Need Parser, Fixture, and Version Alignment

## Context

The plain-prose DAE migration for non-Anki atomic notes looked like a documentation wording change, but it changed the deterministic audit contract. The accepted non-Anki shape moved from `## Definition` / `## Analogy` / `## Example` heading sections to three visible prose paragraphs after the H1, while Basic and Cloze Anki validation had to stay stable.

That meant doctrine, parser behavior, audit metadata, synthetic fixtures, generated skill-local copies, and deterministic goldens all had to move together. Leaving any one of those behind would either keep the old heading contract alive or make valid plain-prose notes fail audit.

## Guidance

Treat doctrine-shape changes as contract migrations, not isolated prose edits.

Start from the canonical shared source for generated runtime artifacts. Update shared doctrine and parser helpers first, then sync skill-local references and scripts from the shared files. The installable skill directories are checked in, but they are not the edit authority for generated copies.

Keep the deterministic parser contract narrow and explicit. For the plain-prose DAE migration, `has_dae_sections()` became a thin wrapper around `analyze_dae()`, and `analyze_dae()` evaluates accepted shapes rather than raw heading presence. Heading-only DAE can still be extracted by legacy helper tests, but it is no longer a valid non-Anki analysis candidate.

Use existing parser primitives before adding new semantics. The plain-prose candidate reuses the same rendered-word count, paragraph extraction, analogy detection, and `For example,` prefix check that Basic-card parsing already uses. Its body window starts after the H1, skips structural `TARGET DECK:` metadata, and stops before structural Anki `START` or plain trailing `Reference:` / `Sources:` labels, using structural markdown so code-block markers do not terminate the region.

Keep component selection paragraph-aware. A plain-prose note needs separate Definition, Analogy, and Example paragraphs in that order. The same `For example,` paragraph should not satisfy both the analogy detector and the example detector, even if it contains wording like `is like`.

Keep quality heuristics shape-aware. Headingless prose cannot reuse `## Definition` / `## Analogy` / `## Example` section word counts, so the DAE analysis should carry the selected component word counts forward. The audit can then preserve `weak_dae` findings for short plain-prose Analogy or Example paragraphs without changing Basic or Cloze card behavior.

Keep version bumps contract-specific. A doctrine-only behavior change should bump the doctrine contract version while leaving schema, rubric, and prompt versions unchanged. Tests should assert those fields separately so future migrations do not collapse them back into one version constant.

Move fixtures before regenerating goldens. Valid synthetic non-Anki notes and the fixture generator should use the new shape before audit JSONL, report, and Base outputs are refreshed. This keeps deterministic golden changes explainable: content hashes and doctrine versions change because the fixture contract changed, not because unrelated scoring logic moved.

Do not widen scope silently while tightening a contract. In this migration, the plan only required plain `Reference:` and `Sources:` trailing-label boundaries because heading-style reference sections had already been normalized out of the source data. Supporting `## Reference` / `## Sources` clamps would have been an unplanned parser contract expansion.

## Why This Matters

The atomic-note skills are both authoring guidance and executable audit tooling. If the guidance changes without the parser, agents author notes that the audit rejects. If the parser changes without fixtures and goldens, the repo loses deterministic proof that the new contract is intentional. If metadata versions are not split, downstream consumers cannot tell whether schema, doctrine, rubric, or prompt contracts actually changed.

The safer pattern is to make every contract edge visible in the diff: doctrine wording, authoring workflow, parser candidates, audit rows, synthetic examples, generated artifacts, and verification commands.

## When to Apply

- When changing what counts as valid DAE for non-Anki or Anki-backed notes.
- When changing deterministic audit behavior, finding specificity, or audit metadata.
- When editing generated skill-local references or runtime helper copies.
- When fixture note shape changes require golden-output regeneration.

## Examples

Before the migration, heading presence alone could make `has_dae_sections()` true:

```python
headings = {heading.casefold() for heading in extract_headings(markdown)}
if {"definition", "analogy", "example"}.issubset(headings):
    return True
```

After the migration, the public helper follows the accepted analysis contract:

```python
def has_dae_sections(markdown: str) -> bool:
    return analyze_dae(markdown).present
```

A complete implementation also needs audit-level tests, not just parser unit tests. Parser tests prove the shape decision; audit tests prove the user-facing finding behavior, such as valid plain-prose notes avoiding `invalid_dae`, overlong plain-prose definitions receiving `definition_too_long`, short component paragraphs receiving `weak_dae`, and optional Anki metadata not being mistaken for the visible Definition.

## Related

- GitHub issue #13: `https://github.com/jrgilbertson/networked-thinking-skills/issues/13`
- Plan: `docs/plans/2026-07-03-001-fix-plain-prose-dae-plan.md`
