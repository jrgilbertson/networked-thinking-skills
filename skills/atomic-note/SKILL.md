---
name: atomic-note
description: Use when creating or improving a Networked Thinking atomic note in DAE format.
---

# Atomic note

Create or improve one Networked Thinking atomic note. Install `atomic-note-audit`
alongside this skill for vault-wide audits and batch repairs; this skill supports
authoring on its own.

## Required references

- `references/doctrine.md`: read before drafting. Defines DAE, naming, sourcing,
  learner purpose, and optional Anki cards.
- `references/remediation-context.md`: read before any vault mutation. Defines
  Obsidian tooling, content transport, approval, rename, and Anki replacement
  workflows.

## Workflow

1. **Read the source and doctrine.** Read the source material or existing note
   and `references/doctrine.md`. Identify the concept the note must explain and
   the learner's purpose: conceptual navigation, factual recall, trivia review,
   or a mix.
2. **Scan nearby topics.** Search exact duplicates, likely aliases, overlapping
   concepts, neighboring topic sections, backlinks, parent structure notes,
   siblings, and prerequisites. Decide whether to improve an existing note,
   create one, link an existing sibling or prerequisite, or create a missing
   connective note for a related concept without an atomic home. Preserve the
   learner's purpose in the parent structure note. A broad parent is a
   navigation hub, not itself a DAE atomic note; apply the one-concept and DAE
   rules to each atomic child instead of narrowing or splitting the hub because
   it spans a topic. A Mythology hub may support figure and motif comparisons
   alongside names, stories, and facts selected for trivia review.
3. **Draft the DAE and provenance.** Write Definition, Analogy, and Example
   paragraphs under the doctrine's DAE rules. For non-Anki notes, use plain
   prose after the H1 without `## Definition`, `## Analogy`, or `## Example`
   headings. Add useful aliases, connections, numbered `Sources:`, and actual
   agent-access dates. Use `Reference:` for optional Obsidian-only extras.
   Doctrine owns formula placement, variable labels, sentence-case exceptions,
   and Anki visibility. When a formula completes the definition, put it in the
   Definition after a prose-first sentence. Write equations as LaTeX.
4. **Check both naming pairs.** Follow the doctrine's **Naming Alignment**
   section to select the applicable Definition source for plain-prose, legacy
   headed, `Basic`, or `Cloze` notes. Match the timestamp-prefixed filename to
   that reader-visible source without its final period, and YAML `title` to the
   H1 short concept name. Validate the derived filename for the target vault and
   platform; redraft an invalid Definition source with the learner. Preserve a
   declared pre-existing filename scheme only under the doctrine's compatibility
   exception.
5. **Decide whether to add Anki.** Apply the learner-specific Anki-YAGNI check.
   Factual recall and trivia are valid goals when the learner wants practice;
   add cards only where memorization serves that goal. Read the doctrine's
   **Anki** section before drafting a `Basic` or `Cloze` block. For synced notes,
   preserve useful cloze ordinals. Reducing or renumbering deletions, or changing
   between `Basic` and `Cloze`, requires the remediation context's
   delete-sync-recreate flow.
6. **Preview and write through Obsidian.** Read
   `references/remediation-context.md` before any vault mutation. Load the
   official Obsidian Markdown and file-management skills when available, verify
   the actual Obsidian CLI binary, and preview the note and both naming pairs.
   For an existing filename/Definition mismatch or a proposed change that would
   introduce one, follow **Improve In Place**, including explicit approval,
   automatic-link-update preflight, and official CLI `rename` or `move`. If
   rename approval is denied, do not write a proposed Definition change that
   would introduce filename drift. For a pre-existing mismatch, leave the
   unchanged Definition and stale filename in place; report an unchanged
   pre-existing mismatch. Use Obsidian-aware tooling and quote-safe, escape-safe
   content transport for vault writes. Never create or rename atomic notes
   through raw filesystem writes. Prefer `python3 scripts/obsidian_cli.py` for
   app-context CLI commands. If a sandbox prevents attachment to the running
   app, request approved unsandboxed CLI execution.
7. **Read back and verify.** Verify DAE, both naming pairs, the final path, and
   links affected by a rename. If `content=` decoding corrupts a LaTeX command
   such as `\times` into a tab or newline followed by its remaining letters,
   restore it through the remediation context's safe transport. Read back the
   literal backslash sequence; a plain-text description does not repair the
   equation. For new Anki-intended notes, complete the doctrine's first-sync ID
   verification. After any sync-affecting edit, also verify model, deck, card
   count, and representative field content. Report any incomplete verification.

Update the relevant structure note so the new or improved note is findable.
For Structure Note entries, use the complete filename stem, including its
timestamp, as an unaliased wikilink: `[[full note filename]]`. Use
`[[full note filename|display alias]]` only when the learner explicitly requests
an alias. Links in ordinary prose may use display aliases for readability.
