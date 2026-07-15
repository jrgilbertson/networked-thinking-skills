---
name: atomic-note
description: Use when creating or improving a Networked Thinking atomic note in DAE format.
---

# Atomic Note

Use this skill to create or improve one Networked Thinking atomic note.

Before writing or editing an Obsidian vault file, load the official Obsidian
Markdown and file-management skills when available. For note creates, file
moves, renames, deletes, Anki syncs, and link-sensitive operations, require
Obsidian-aware tooling and verify the actual Obsidian CLI binary before
mutating the vault. If a sandboxed agent cannot attach to the running Obsidian
app, request approved unsandboxed CLI execution instead of falling back to raw
filesystem writes. When working from an installed skill, prefer
`python3 scripts/obsidian_cli.py` for app-context CLI commands.

## Required References

- `references/doctrine.md`
- `references/remediation-context.md`

## Workflow

1. Read the relevant source material or existing note.
2. Scan nearby notes and topics before writing: exact duplicates, overlapping aliases, parent structure notes, sibling notes, prerequisites, and connective gaps.
3. Draft one DAE note: Definition paragraph, Analogy paragraph, Example
   paragraph. For non-Anki notes, write the DAE as plain prose after the H1
   without `## Definition`, `## Analogy`, or `## Example` headings.
4. Apply the two naming pairs: the timestamp-prefixed filename uses the
   Definition's first sentence without its final period, while the YAML `title`
   and H1 use the same short concept name. Preserve all other reader-visible
   wording, capitalization, punctuation, and word order in the filename. If the
   Definition sentence is not valid as one filename component in the target
   vault and platform, redraft it with the learner instead of silently changing
   characters.
5. Add useful aliases and links; follow the doctrine for the optional `Reference:` section (bulleted links, figures, and compact reference material) and the numbered `Sources:` section (external provenance), plus agent-access dates.
6. Add Anki only when memorization is useful. For synced `Cloze` notes, preserve useful cloze ordinals and put the Analogy plus Example behind `Extra:`; the Example must be a separate paragraph beginning `For example,`.
7. For Anki-intended notes, create the file through Obsidian app-context APIs and follow the doctrine's first-sync ID verification after writing. For existing synced notes, reducing or renumbering cloze deletions or changing between `Basic` and `Cloze` requires the remediation-context delete-sync-recreate flow so stale Anki cards or fields are not retained.
8. Preview the note and both naming pairs before writing when working in a
   user's vault. If an improved Definition's first sentence changes, preview
   the corresponding filename and follow the remediation context's explicit
   approval, automatic-link-update preflight, and official CLI `rename` or
   `move` workflow. If approval is denied, do not write a first-sentence change
   that would leave the filename stale.
9. Write through Obsidian-aware tooling when modifying vault files; never create atomic notes or rename them through direct filesystem path writes. Use quote-safe content transport for app-context writes.
10. After writing, verify the final filename against the Definition's first
    sentence, the YAML `title` against the H1 short concept name, and any path or
    link changes caused by a rename.

## Quality Bar

The note should explain one concept clearly enough to stand alone while remaining connected to the surrounding knowledge network.

## Nearby-Topic Scan

Do not treat duplicate review as an exact-title search. Search likely aliases,
neighboring topic sections, backlinks, parent structure notes, and adjacent
concept families before creating or splitting a note.

Use the scan to decide whether to:

- improve an existing note instead of creating a duplicate;
- link to sibling or prerequisite notes already present;
- create a missing connective note when the current note is carrying a related
  concept that has no atomic home;
- update the relevant structure note so the new or improved note is findable.
