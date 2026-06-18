# Networked Thinking Atomic Note Doctrine

An atomic note captures one durable concept in DAE format: Definition, Analogy, and Example.

## Required Shape

- One concept per file.
- Timestamp-prefixed filename when the vault uses timestamp atomic notes.
- Frontmatter with `title` and `aliases`.
- Clear Definition, Analogy, and Example content.
- At least one useful connection to a structure note or related concept.
- Sources when the idea came from external material; write source sections as numbered lists.
- Agent-access source lines, such as `Codex 5.5 last accessed [[YYYY-MM-DD]]`,
  use the actual local date when the note is created or edited, not a copied
  example date from prior work.
- Optional compact reference material can appear after the Anki `END` block and
  before `Sources:` when the concept has formulas, lookup tables, commands, or
  other exact artifacts worth preserving but not worth testing directly.

## DAE Rules

- Definition: 10-50 rendered words. Rendered word counts use the visible text a
  reader sees, so `[[Target note|alias text]]` counts as `alias text`. When the
  concept has a common acronym or initialism that will be used in the note,
  introduce it on first use in the Definition's first sentence with the pattern
  `<full term> (<ACRONYM>)`, then use the acronym later.
- Analogy: map the concept to a familiar concrete pattern. Start with a clear
  `<concept> is like <familiar referent>` mapping, then explain the shared
  relational structure in natural prose. Do not default to colon or semicolon
  templates; use punctuation only when the sentence would read naturally outside
  the note format.
- Example: concrete and specific. It starts with `For example,` and uses named
  tools, real numbers, real domains, or real situations.

## Anki

Anki cards are optional. A non-Anki atomic note still needs DAE. When Anki markers are present, `START` and `END` blocks must be balanced and scoped to the note's concept.

`Basic` cards can store the Definition, Analogy, and Example in the `Back:`
content. `Cloze` cards can store the Definition in the cloze body and keep the
Analogy and Example behind `Extra:` so Anki does not reveal them while testing
the cloze fields.

New Anki-intended notes must be created through Obsidian app-context APIs, such
as the official CLI `create` command from a verified Obsidian CLI binary or
`app.vault.create(...)` from an app-context eval. Do not create them through
direct filesystem path writes; the Obsidian-to-Anki plugin may create cards
before Obsidian writes IDs back to files, making sync state ambiguous. New
Anki-intended notes do not include an Obsidian-to-Anki `<!--ID: ...-->` line
when first written. After writing a note with `TARGET DECK`, `START` and `END`,
and a `Basic` or `Cloze` card block, run `Obsidian_to_Anki: Scan Vault` in the
running Obsidian app and verify the file received an `<!--ID: ...-->` line.
Treat the note as written but not fully created in Anki until the ID is
present. Tell the user before scanning that plugin state files such as
`.obsidian/plugins/obsidian-to-anki-plugin/data.json` may change.

Reference material that should be available in Obsidian but not tested in Anki
belongs outside the Anki block, after `END` and before `Sources:`. Keep it
compact and exact. Typical uses are formulas, lookup tables, syntax snippets,
and commands that support the concept but would make a poor flashcard.

## Misfiled Notes

A non-DAE file in `Atomic Notes/` is not a valid alternate atomic-note class. Convert it or re-home it after review.
