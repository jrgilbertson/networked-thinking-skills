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
2. Scan nearby notes and topics before writing: exact duplicates, overlapping
   aliases, parent structure notes, sibling notes, prerequisites, and connective
   gaps. Identify whether the learner wants conceptual navigation, factual
   recall, trivia review, or a mix, and preserve that purpose in the parent
   structure note. A broad parent is a navigation hub, not itself a DAE atomic
   note; apply the one-concept and DAE rules to each atomic child instead of
   narrowing or splitting the hub merely because it spans a topic.
3. Draft one DAE note: Definition paragraph, Analogy paragraph, Example
   paragraph. For non-Anki notes, write the DAE as plain prose after the H1
   without `## Definition`, `## Analogy`, or `## Example` headings.
4. Apply the two naming pairs. The timestamp-prefixed filename uses the
   reader-visible wording of the applicable Definition source without its final
   period. The timestamp, `.md` extension, Markdown wrappers, and Anki cloze
   syntax are excluded; compare cloze text as a reader sees it. All other visible
   words, capitalization, punctuation, and word order must match. Keep the YAML
   `title` and H1 aligned to the same short concept name; that name does not need
   to repeat the full Definition sentence. If the derived text is not valid as
   one filename component in the target vault and platform, redraft the
   Definition source with the learner instead of silently changing characters.
5. When a learner or governing template explicitly declares that a pre-existing
   user vault uses a different filename scheme, preserve it as a compatibility
   exception unless the learner approves a migration. Do not describe it as
   another Networked Thinking naming style or use nearby inconsistencies to
   weaken the canonical rule.
6. Add useful aliases and links; follow the doctrine for the optional `Reference:` section (bulleted links, figures, and compact reference material) and the numbered `Sources:` section (external provenance), plus agent-access dates.
7. Add Anki only when memorization serves the learner's stated goal. Factual
   recall and trivia are valid uses when the learner explicitly wants to
   practice them; still apply the learner-specific Anki-YAGNI check rather than
   adding every available fact. For synced `Cloze` notes, preserve useful cloze
   ordinals and put the Analogy plus Example behind `Extra:`; the Example must
   be a separate paragraph beginning `For example,`.
8. For Anki-intended notes, create the file through Obsidian app-context APIs and follow the doctrine's first-sync ID verification after writing. For existing synced notes, reducing or renumbering cloze deletions or changing between `Basic` and `Cloze` requires the remediation-context delete-sync-recreate flow so stale Anki cards or fields are not retained.
9. Preview the note and both naming pairs before writing in a user's vault. If
   an existing filename/Definition mismatch is detected or a proposed change to
   the applicable Definition source would introduce one, preview the
   corresponding filename and follow the remediation context's explicit approval,
   automatic-link-update preflight, and official CLI `rename` or `move`
   workflow. If approval is denied, do not write a Definition change that would
   introduce filename drift; report an unchanged pre-existing mismatch.
10. Write through Obsidian-aware tooling when modifying vault files; never create atomic notes or rename them through direct filesystem path writes. Use quote-safe content transport for app-context writes.
11. After writing, verify the filename against the applicable Definition source,
    the YAML `title` against the H1 short concept name, and any path or link
    changes caused by a rename.

Choose the applicable Definition source by note shape. Visible DAE takes
precedence over optional Anki card text:

| Note shape | Applicable Definition source | Matching rule |
| --- | --- | --- |
| Plain-prose DAE, with or without Anki | First visible DAE sentence after the H1 | Exact reader-visible wording without the final period |
| Legacy headed DAE, with or without Anki | First sentence under `## Definition` | Exact reader-visible wording without the final period |
| Anki `Basic` with DAE stored only in `Back:` | First Definition sentence in `Back:` | Exact reader-visible wording without the final period |
| Anki `Cloze` with DAE stored only in the card body | Rendered cloze-bearing Definition sentence | Exact reader-visible wording without the final period |

## Quality Bar

The note should explain one concept clearly enough to stand alone while
remaining connected to the surrounding knowledge network. Judge quality from
the learner's purpose and the DAE, connection, and sourcing requirements, not
from whether the purpose favors conceptual synthesis over factual recall.

## Nearby-Topic Scan

Do not treat duplicate review as an exact-title search. Search likely aliases,
neighboring topic sections, backlinks, parent structure notes, and adjacent
concept families before creating or splitting a note.

Use the scan to decide whether to:

- improve an existing note instead of creating a duplicate;
- link to sibling or prerequisite notes already present;
- create a missing connective note when the current note is carrying a related
  concept that has no atomic home;
- update the relevant structure note so the new or improved note is findable
  without narrowing a broad, learner-chosen topic to analytical use alone. For
  example, a Mythology structure note can support comparison of figures and
  motifs alongside names, stories, and other facts selected for trivia review.

Structure Note entries are index links, so whenever this skill adds one, use
the complete note filename stem, including its timestamp, as an unaliased
wikilink: `[[full note filename]]`. Do not shorten Structure Note entries to
`[[full note filename|display alias]]` unless the learner explicitly requests
an alias. This convention is specific to Structure Note entries; wikilinks in
ordinary prose may use display aliases when shorter text improves readability.
