---
title: Capitalize Analogy sentence starts, including wikilink aliases
date: 2026-09-04
category: conventions
module: networked-thinking atomic-note authoring
problem_type: convention
component: assistant
severity: medium
applies_when:
  - Authoring a Networked Thinking atomic note Analogy
  - Auditing DAE Analogy paragraphs for sentence case
  - Syncing Anki-backed notes whose Analogy starts with a wikilink
related_components:
  - tooling
  - documentation
tags:
  - atomic-notes
  - dae
  - analogy
  - wikilink
  - anki
  - sentence-case
---

# Capitalize Analogy sentence starts, including wikilink aliases

## Context

The Analogy paragraph is a sentence. Mid-sentence wikilink aliases are lowercase by convention (`[[Note|creatine]]`). When that alias is the first visible text, Obsidian-to-Anki renders only the alias, so the Anki card starts `creatine is like...`.

`weak_analogy` measures whether the mapping is concrete. Model judgment replaces it. Sentence case is a rendered-text rule, so it needs a deterministic finding that the apply step keeps.

## Guidance

Start the Analogy with a capital letter in the text a reader sees.

If the sentence starts with a wikilink, capitalize the visible alias and leave later aliases lowercase:

```markdown
[[202411271638 Creatine is a naturally occurring compound|Creatine]] is like a backup power generator for muscles.
```

Do not write:

```markdown
[[202411271638 Creatine is a naturally occurring compound|creatine]] is like a backup power generator for muscles.
```

Bare lowercase openers are the same defect (`a three-tier system is like...`). Analogies that open with inline math may keep the math token first (`$n$ is like...`).

Audit this with `analogy_sentence_case`, not `weak_analogy`. Keep it on the deterministic retain list so model judgment cannot drop it. Check every DAE location, including Anki `Back:` and Cloze `Extra:`, because a capitalized vault paragraph can still hide a lowercase card.

## Why This Matters

Anki shows the rendered alias, not the wikilink target. A lowercase alias at the start of the Analogy is a sentence-case error on the card even when the Obsidian source looks like a normal link.

## When to Apply

- Drafting or improving an Analogy
- Adding a leading wikilink on an Anki-backed note
- Changing finding codes or model-judgment retain behavior for DAE quality

## Examples

- Flag: `[[Note|creatine]] is like a backup power generator...`
- Flag: `a three-tier system is like a well-run restaurant...`
- Do not flag: `[[Note|Noise]] is like a blurry lens...`
- Do not flag: `$n$ is like the number of survey responses...`

## Related

- GitHub issue [jrgilbertson/networked-thinking-skills#51](https://github.com/jrgilbertson/networked-thinking-skills/issues/51)
- `docs/solutions/conventions/keep-atomic-note-naming-pairs-aligned-with-obsidian-aware-renames.md`
