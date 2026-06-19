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
filesystem writes. When working from this repo, prefer
`python3 -m shared.scripts.obsidian_cli` for app-context CLI commands.

## Required References

- `../../shared/references/doctrine.md`
- `../../shared/references/remediation-context.md`

## Workflow

1. Read the relevant source material or existing note.
2. Scan nearby notes and topics before writing: exact duplicates, overlapping aliases, parent structure notes, sibling notes, prerequisites, and connective gaps.
3. Draft one DAE note: Definition, Analogy, Example. For non-Anki notes, use
   explicit `## Definition`, `## Analogy`, and `## Example` headings.
4. Add useful aliases, links, and sources; follow the doctrine for numbered source sections, optional compact reference material, and agent-access dates.
5. Add Anki only when memorization is useful. For synced `Cloze` notes, preserve useful cloze ordinals and put the Analogy plus Example behind `Extra:`; the Example must be a separate paragraph beginning `For example,`.
6. For Anki-intended notes, create the file through Obsidian app-context APIs and follow the doctrine's first-sync ID verification after writing. For existing synced notes, reducing or renumbering cloze deletions or changing between `Basic` and `Cloze` requires the remediation-context delete-sync-recreate flow so stale Anki cards or fields are not retained.
7. Preview the note before writing when working in a user's vault.
8. Write through Obsidian-aware tooling when modifying vault files; never create atomic notes through direct filesystem path writes. Use quote-safe content transport for app-context writes.

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
