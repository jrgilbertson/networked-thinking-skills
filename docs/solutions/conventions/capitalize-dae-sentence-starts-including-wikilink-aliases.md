---
title: Capitalize DAE sentence starts, including wikilink aliases
date: 2026-09-04
last_updated: 2026-09-19
category: conventions
module: networked-thinking atomic-note authoring
problem_type: convention
component: assistant
severity: medium
applies_when:
  - Authoring a Networked Thinking atomic note Definition, Analogy, or Example
  - Auditing DAE paragraphs for sentence case
  - Syncing Anki-backed notes whose DAE section starts with a wikilink
  - Adding a paragraph collector that walks every DAE location
related_components:
  - tooling
  - documentation
tags:
  - atomic-notes
  - dae
  - definition
  - analogy
  - example
  - wikilink
  - anki
  - sentence-case
---

# Capitalize DAE sentence starts, including wikilink aliases

## Context

Each DAE section is a sentence. Mid-sentence wikilink aliases are lowercase by convention (`[[Note|creatine]]`). When that alias is the first visible text, Obsidian-to-Anki renders only the alias, so the Anki card starts `creatine is like...`.

The rule began as Analogy-only (issue #51) because that is where a vault scan found almost every case. Definition and Example are sentences too, so issue #55 made it one rule for all three sections, with one finding code.

`weak_analogy` and `weak_dae` measure content quality, and model judgment replaces them. Sentence case is a rendered-text rule, so it needs a deterministic finding that the apply step keeps.

## Guidance

Start the Definition, Analogy, and Example with a capital letter in the text a reader sees.

If the sentence starts with a wikilink, capitalize the visible alias and leave later aliases lowercase:

```markdown
[[202411271638 Creatine is a naturally occurring compound|Creatine]] is like a backup power generator for muscles.
```

Do not write:

```markdown
[[202411271638 Creatine is a naturally occurring compound|creatine]] is like a backup power generator for muscles.
```

Bare lowercase openers are the same defect (`a three-tier system is like...`, `for example, a lifter...`).

Four openers are exempt. A section that opens with closed inline math may keep the math token first (`$n$ is like...`). A section that opens with a closed inline code span keeps it as written (`` `range` is like...``, including a multi-backtick span such as ``` ``range`` ```), because code is case-sensitive and `Range` is not `range`. A mixed-case first word that is correctly lowercase-initial stays as written (`gRPC`, `pH`, `mRNA`, `iOS`); capitalizing it would misspell the term and break Definition-to-filename alignment. A first word with no letter to capitalize, such as a numeral or a URL (`404 is...`, `https://example.com is...`), is exempt for the reason given under detector pitfalls below. An all-lowercase first word such as `curl` gets no exemption.

Audit this with `dae_sentence_case`, not `weak_analogy` or `weak_dae`. Keep it on the deterministic retain list so model judgment cannot drop it. A note gets the finding once however many sections start lowercase. Check every DAE location, including Anki `Back:` and the Cloze body and `Extra:`, because a capitalized vault paragraph can still hide a lowercase card.

## Detector pitfalls: judge the first word of a real sentence

Judge only the first visible word. Scanning the whole paragraph for its first letter flags a numeral or URL opener (`404 is the status...`) on the `i` of `is`, and no edit can clear that finding. A first word with no letter to capitalize is not a sentence-case error.

Take the Definition from the first paragraph that is a prose sentence. A tag line, list, inline field (`up:: [[Parent]]`), image, table, or callout above the DAE is not the Definition, and treating it as one tells the author to capitalize a Definition that is already capitalized. Apply that same filter inside a headed `## Definition`, `## Analogy`, or `## Example` body: a heading tells you which section you are in, but not that the first paragraph under it is prose. Do not gate the finding on a fully detected DAE to avoid this: a replay against real notes showed that gate hides genuine lowercase Analogies in notes whose DAE is incomplete for an unrelated reason.

## Collector pitfall: headed notes

A collector that walks DAE locations must not treat the plain-prose region as a Definition source when the note uses `## Definition` / `## Analogy` / `## Example` headings. In a headed note the first plain-prose paragraph is the heading line itself, so the check would inspect `## Definition` and silently pass. Read headed notes from their section bodies.

## Why This Matters

Anki shows the rendered alias, not the wikilink target. A lowercase alias at the start of a section is a sentence-case error on the card even when the Obsidian source looks like a normal link.

## When to Apply

- Drafting or improving any DAE section
- Adding a leading wikilink on an Anki-backed note
- Changing finding codes or model-judgment retain behavior for DAE quality

## Examples

- Flag: `[[Note|creatine]] is like a backup power generator...`
- Flag: `a three-tier system is like a well-run restaurant...`
- Flag: `for example, a sprinter can use...`
- Flag: `{{c1::creatine}} helps muscles...`
- Flag: `curl is a command-line tool...`
- Do not flag: `[[Note|Noise]] is like a blurry lens...`
- Do not flag: `$n$ is like the number of survey responses...`
- Do not flag: `gRPC is a framework...`
- Do not flag: `` `range` is like a ticket dispenser...``
- Do not flag: `404 is the status a server returns...`
- Do not flag: a `#tag` line or `up:: [[Parent]]` field above a capitalized Definition

## Related

- GitHub issues [jrgilbertson/networked-thinking-skills#51](https://github.com/jrgilbertson/networked-thinking-skills/issues/51) and [#55](https://github.com/jrgilbertson/networked-thinking-skills/issues/55)
- `docs/solutions/conventions/keep-atomic-note-naming-pairs-aligned-with-obsidian-aware-renames.md`
