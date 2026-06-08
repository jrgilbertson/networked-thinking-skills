# Networked Thinking Atomic Note Doctrine

An atomic note captures one durable concept in DAE format: Definition, Analogy, and Example.

## Required Shape

- One concept per file.
- Timestamp-prefixed filename when the vault uses timestamp atomic notes.
- Frontmatter with `title` and `aliases`.
- Clear Definition, Analogy, and Example content.
- At least one useful connection to a structure note or related concept.
- Sources when the idea came from external material; write source sections as numbered lists.

## DAE Rules

- Definition: 10-50 rendered words. Rendered word counts use the visible text a
  reader sees, so `[[Target note|alias text]]` counts as `alias text`.
- Analogy: map the concept to a familiar concrete pattern. Preferred shape:
  `<concept> is like <familiar referent>: <shared relational structure>`.
- Example: concrete and specific. It starts with `For example,` and uses named
  tools, real numbers, real domains, or real situations.

## Anki

Anki cards are optional. A non-Anki atomic note still needs DAE. When Anki markers are present, `START` and `END` blocks must be balanced and scoped to the note's concept.

`Basic` cards can store the Definition, Analogy, and Example in the `Back:`
content. `Cloze` cards can store the Definition in the cloze body and keep the
Analogy and Example behind `Extra:` so Anki does not reveal them while testing
the cloze fields.

## Misfiled Notes

A non-DAE file in `Atomic Notes/` is not a valid alternate atomic-note class. Convert it or re-home it after review.
