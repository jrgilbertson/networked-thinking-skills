---
title: Preserve Learner Purpose Across Structure-Note Hubs and Atomic Children
date: 2026-07-18
category: documentation-gaps
module: networked-thinking atomic-note authoring and audit
problem_type: documentation_gap
component: documentation
severity: medium
applies_when:
  - Authoring or revising a broad structure note for conceptual navigation, factual recall, trivia review, or a mix
  - Applying DAE and one-concept rules around a structure-note hub and its atomic children
  - Evaluating recall-oriented atomic notes without treating analytical synthesis as the only valid purpose
  - Using Anki-YAGNI when the learner has explicitly stated a memorization goal
  - Changing doctrine, rubric, or prompt semantics that require synchronized versions, fixtures, and generated artifacts
related_components:
  - assistant
  - testing_framework
tags: [atomic-notes, structure-notes, learner-purpose, factual-recall, trivia, anki-yagni, dae, doctrine]
---

# Preserve Learner Purpose Across Structure-Note Hubs and Atomic Children

## Context

Issue #22 exposed an ambiguity in atomic-note guidance: advice intended to favor
durable knowledge could be read as a mandate to privilege analytical synthesis
over factual recall. In practice, that could narrow a broad structure note such
as `Mythology` to comparison frameworks while demoting names, stories, and
trivia the learner explicitly wanted to remember. It also risked applying the
one-concept DAE constraint to the parent hub instead of to the Atomic Notes
linked beneath it.

The durable correction separates three decisions:

1. The learner chooses the collection's purpose: conceptual navigation,
   factual recall, trivia review, or a mix.
2. A Structure Note organizes that collection and may remain intentionally
   broad; it is not itself a DAE Atomic Note.
3. Each Atomic Note still meets the ordinary quality contract: one concept,
   Definition-Analogy-Example (DAE), useful connections, sourcing when
   appropriate, and factual-risk review for check-worthy claims.

The canonical doctrine states these boundaries directly
(`shared/references/doctrine.md:24`, `shared/references/doctrine.md:29`) and makes recall orientation neutral rather
than defective (`shared/references/doctrine.md:33`). The authoring workflow
carries the same distinction into nearby-topic scanning and note creation
(`skills/atomic-note/SKILL.md:27`, `skills/atomic-note/SKILL.md:83`).

## Guidance

Start with learner purpose, then apply the quality contract at the correct
level.

- Preserve the learner's conceptual, factual-recall, trivia, or mixed purpose.
  Do not silently reinterpret a broad topic as valuable only when it yields an
  analytical framework (`shared/references/doctrine.md:24`).
- Treat a Structure Note as a navigation hub. Its breadth is not evidence that
  it should be split or rewritten as one atomic concept; the one-concept and
  DAE rules belong to its Atomic Notes (`shared/references/doctrine.md:29`,
  `skills/atomic-note/SKILL.md:31`).
- Keep recall-oriented Atomic Notes fully atomic. Each covers one concept in
  DAE form, connects to the surrounding network, and sources factual claims
  when appropriate (`shared/references/doctrine.md:33`). Check empirical,
  causal, current, source-attributed, and other check-worthy claims through the
  existing `factual_risk` contract (`shared/references/audit-rubric.md:55`).
- Keep Anki optional and learner-specific. An explicit wish to practice a fact
  is positive evidence of memorization utility, but it neither requires a card
  nor justifies turning every available fact into one
  (`shared/references/doctrine.md:36`, `skills/atomic-note/SKILL.md:45`).
- Apply `anki_yagni` to unclear learner utility, not merely to recall-oriented
  content. Explicit factual-recall or trivia intent is not by itself a reason
  to emit the finding; learner judgment remains required before removing Anki
  (`shared/references/audit-rubric.md:39`). The model prompt repeats this
  constraint (`shared/references/model-judgment-prompt.md:63`).

When these semantics change, update the whole contract surface deliberately.
Issue #22 changes doctrine, rubric, and prompt behavior, so those three
contracts receive independent patch bumps while the schema remains unchanged
(`pyproject.toml:11`, `shared/scripts/audit_engine.py:23`). Canonical sources
remain under `shared/`; synchronize the checked-in installable copies rather
than hand-editing generated artifacts (`shared/scripts/sync_skill_artifacts.py:133`).

## Why This Matters

Learner intent is part of utility, not an exception to quality. If an auditor
assumes analytical synthesis is inherently more valuable than factual recall,
it can erase legitimate study goals, fragment useful navigation hubs, or remove
cards that serve an explicit practice purpose. Conversely, treating all
requested facts as automatically card-worthy would abandon the learner-specific
YAGNI safeguard.

The level distinction prevents both errors. Broad organization stays broad
where it helps navigation, while Atomic Notes retain the rigor that makes the
network trustworthy. This preserves factual recall without relaxing DAE,
connection, sourcing, or factual-risk requirements. It also preserves
analytical use: the fresh-context evaluation found the analytical hero's-journey
case unchanged while the mixed-purpose hub and explicit quiz-recall cases
improved (`tests/fixtures/atomic-note-skill/baseline-recall-friendly-structure-note.md:13`,
`tests/fixtures/atomic-note-skill/baseline-recall-friendly-structure-note.md:21`,
`tests/fixtures/atomic-note-skill/baseline-recall-friendly-structure-note.md:29`).

The contract is tested rather than merely stated. The synthetic fixture encodes
the intended hub scope, child atomicity, sourcing, Anki decision, and absence of
a recall-orientation penalty
(`tests/fixtures/atomic-note-skill/recall-friendly-structure-note.json:6`). The
contract test ties those properties to the canonical doctrine and installed
skill (`tests/test_atomic_note_skill_examples.py:47`).

## When to Apply

- When creating or revising a broad Structure Note for comparison, factual
  recall, trivia, or a mix.
- When a nearby-topic scan suggests narrowing or splitting a parent solely
  because the parent spans many concepts.
- When creating a recall-oriented Atomic Note whose DAE, connections, sourcing,
  and factual-risk checks must remain intact.
- When deciding whether to add or retain Anki for an explicitly requested fact
  or trivia item.
- When auditing `anki_yagni` and distinguishing explicit learner utility from
  content that merely appears low-stakes to the auditor.
- When changing doctrine that also affects audit decisions or model
  instructions; bump only the changed contracts, regenerate skill-local
  artifacts, and verify synchronization.
- When evaluating a skill-contract clarification; compare prior and revised
  behavior in fresh contexts and check trigger and near-miss boundaries
  separately (`tests/fixtures/atomic-note-skill/trigger-queries.md:3`,
  `tests/fixtures/atomic-note-skill/trigger-queries.md:8`,
  `tests/fixtures/atomic-note-skill/trigger-queries.md:23`).

## Examples

### Mixed-purpose Mythology hub

Before: “Because `Mythology` spans many figures, stories, motifs, and facts,
narrow it to reusable analytical frameworks or split it as though the hub were
one Atomic Note.”

After: Keep one broad `Mythology` navigation hub with sections for motif
comparison and learner-selected recall. Link each figure, story, or motif to a
one-concept DAE Atomic Note. Source factual claims when appropriate. Add Anki
only where the learner wants practice and the learner-specific YAGNI check
supports it.

### Explicit factual quiz recall

Before: “This is trivia or reference material, so an Anki card lacks analytical
value and should receive `anki_yagni`.”

After: Treat the learner's explicit quiz-practice request as evidence that
memorization is useful. Still create a sourced, connected, one-concept DAE note
and retain normal card-safety and YAGNI checks for concerns other than recall
orientation.

### Analytical use without trivia

If the learner asks for the invented Lantern-Bridge pattern as a reusable
analytical framework and does not want trivia study, create the analytical DAE
note, connect it to the appropriate parent, and omit Anki. Preserving recall as
a valid option does not impose recall on learners who did not choose it.

## Related

- [Issue #22](https://github.com/jrgilbertson/networked-thinking-skills/issues/22)
- [Contract migration and generated-artifact precedent](../conventions/plain-prose-dae-contract-migration.md)
- [Atomic-note naming and DAE invariant precedent](../conventions/keep-atomic-note-naming-pairs-aligned-with-obsidian-aware-renames.md)
- [Broader atomic-note quality regression coverage](https://github.com/jrgilbertson/networked-thinking-skills/issues/20)
