# Networked Thinking Atomic Note Doctrine

An atomic note captures one durable concept in DAE format: Definition, Analogy, and Example.

## Required Shape

- One concept per file.
- Timestamp-prefixed filename when the vault uses timestamp atomic notes.
- Frontmatter with `title` and `aliases`.
- Clear Definition, Analogy, and Example content.
- At least one useful connection to a structure note or related concept.
- `Sources:` (plural label, numbered list) when the idea came from external material; provenance for later verification.
- Agent-access source lines, such as `Codex 5.5 last accessed [[YYYY-MM-DD]]`,
  use the actual local date when the note is created or edited, not a copied
  example date from prior work.
- Optional `Reference:` section (singular label, bulleted) after the DAE prose,
  or after the Anki `END` block when Anki is present, and before `Sources:`,
  for links to related atomic notes, figures, and compact reference material
  (formulas, lookup tables, commands) worth preserving but not worth testing
  directly.

## Learner Purpose and Structure Notes

Structure notes may organize atomic notes for conceptual navigation, factual
recall, trivia review, or a learner-chosen mix. Preserve the learner's intended
scope instead of narrowing a broad topic to analytical synthesis or reusable
thinking tools. For example, a `Mythology` structure note can connect figures
and motifs for conceptual comparison while also collecting names, stories, and
other facts the learner wants to remember. The structure note is a navigation
hub, not itself a DAE atomic note; the one-concept and DAE rules apply to its
atomic children rather than to the breadth of the hub.

Recall-oriented children remain atomic notes: each covers one concept in DAE
form, connects to the surrounding network, and sources factual claims when
appropriate. Recall or trivia orientation is not by itself a quality defect.
Anki remains optional and learner-specific; an explicit desire to practice a
fact supports adding a card, while the Anki-YAGNI check still prevents turning
every available fact into one by default.

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
- Use stable wording in generic DAE prose. Avoid temporal or support-status
  words such as `currently`, `latest`, `now`, and `supported` unless the note is
  intentionally making a claim that should be marked for factual-risk review.
  In examples, prefer stable reporting verbs such as `reports` over `says`, and
  avoid human-generalization phrasing like `every ... suggests` unless the note
  is intentionally making an evidence claim. In analogies, avoid attribution
  phrases such as `according to`; explain the relationship directly. For generic
  math and proof concepts, prefer definitional wording such as `is a proof
  technique` over assertion wording such as `proves` unless the sentence is
  intentionally presenting a theorem result. For distribution patterns, prefer
  structural wording such as `follows a pattern that favors smaller digits`
  over comparative empirical wording such as `smaller digits appear more often
  than larger digits` unless the note is intentionally making a check-worthy
  empirical claim.

## Naming Alignment

Atomic notes use two separate matching pairs:

- The timestamp-prefixed filename uses the reader-visible wording of the
  Definition's first sentence without its final period. The timestamp, `.md`
  extension, and Markdown wrappers are not part of that comparison. All other
  visible words, capitalization, punctuation, and word order must match.
  Before writing, confirm that the resulting text is valid as one filename
  component in the target vault and platform. If it is not, redraft the first
  sentence with the learner so the sentence and filename can still match;
  never silently remove or substitute characters.
- The YAML `title` and H1 use the same short concept name. That short concept
  name does not need to repeat the full Definition sentence.

Check both pairs when creating a note and when improving an existing note. If
an improvement changes the Definition's first sentence, reconcile the filename
through the approved rename flow in the remediation context rather than leaving
the old filename in place.

## Anki

Anki cards are optional. A non-Anki atomic note still needs DAE. Write non-Anki
atomic notes as plain prose after the H1: first a Definition paragraph, then an
Analogy paragraph, then an Example paragraph that starts with `For example,`.
Do not add `## Definition`, `## Analogy`, or `## Example` headings solely to
mark DAE in non-Anki notes. When Anki markers are present, `START` and `END`
blocks must be balanced and scoped to the note's concept.

`Basic` cards can store the Definition, Analogy, and Example in the `Back:`
content. `Cloze` cards can store the Definition in the cloze body and keep the
Analogy and Example behind `Extra:` so Anki does not reveal them while testing
the cloze fields.

For `Cloze` cards, write the `Extra:` content as normal DAE prose. Put the
Analogy immediately after `Extra:` or in the first paragraph after it, then put
the Example in a separate paragraph that starts with `For example,`. Do not
combine the Analogy and Example into one `Extra:` paragraph; that makes the
card harder to scan and can fail deterministic DAE validation.

If a synced `Cloze` note's cloze ordinals are still useful, preserve the
existing ordinals and add or repair the DAE `Extra:` content instead of
replacing the Anki note. Treat the edit as a normal synced update when no cloze
ordinal is removed or renumbered.

When reducing or renumbering cloze deletions on an existing synced `Cloze`
note, do not treat the change as a normal edit. Obsidian-to-Anki can leave
stale cards for removed cloze ordinals. Use the remediation-context
delete-sync-recreate sequence: delete the old Anki note with a `DELETE` marker,
verify the old ID is gone, force the plugin to rescan the ID-less Obsidian note
by changing its content hash or clearing the plugin's file-hash cache, rescan to
create a fresh ID, then verify the Anki card count matches the current cloze
ordinals.

Do not change a synced note between `Basic` and `Cloze` by editing only the
Obsidian block type. Obsidian-to-Anki may leave the existing Anki note model and
field content unchanged even after a scan. If the Anki model should change, use
the same delete-sync-recreate replacement flow. If the model should stay the
same, rewrite the Obsidian block to match the existing Anki model before
scanning.

New Anki-intended notes must be created through Obsidian app-context APIs, such
as the official CLI `create` command from a verified Obsidian CLI binary or
`app.vault.create(...)` from an app-context eval. Do not create them through
direct filesystem path writes; the Obsidian-to-Anki plugin may create cards
before Obsidian writes IDs back to files, making sync state ambiguous. New
Anki-intended notes do not include an Obsidian-to-Anki `<!--ID: ...-->` line
when first written. After writing a note with `TARGET DECK`, `START` and `END`,
and a `Basic` or `Cloze` card block, run the Obsidian-to-Anki vault scan in the
running Obsidian app and verify the file received an `<!--ID: ...-->` line.
When scanning from an app-context agent, prefer awaiting the loaded plugin's
`scanVault()` method directly, because command-dispatch helpers such as
`app.commands.executeCommandById(...)` can return before existing Anki note
fields are updated.
Treat the note as written but not fully created in Anki until the ID is
present. Tell the user before scanning that plugin state files such as
`.obsidian/plugins/obsidian-to-anki-plugin/data.json` may change.

After any sync-affecting edit, verify more than the presence of an ID. Check the
Anki note model, deck, card count, and a representative field value so stale
Anki content is caught before continuing. For `Basic` cards, Obsidian-to-Anki
may render the Back field as DAE paragraphs without literal `Definition:` or
`Analogy:` labels in Anki. Verify the vault note for doctrine labels and verify
the Anki note for the rendered card shape: expected model, deck, one card,
non-empty Front and Back, and representative updated Back content such as the
Example paragraph. Prefer `python3 scripts/verify_anki_notes.py` with a
JSON spec for this check so deck/model/card-count verification stays consistent
across remediation batches.

If a scan reports that an Obsidian-to-Anki ID does not exist in Anki, treat the
ID as stale. Do not leave the stale ID in place. If the note should remain
Anki-backed, remove only the stale `<!--ID: ...-->` marker through Obsidian
app-context tooling, rescan, and verify a fresh ID, model, deck, card count, and
representative field value. If the note should not remain Anki-backed, stop for
the learner's decision before removing the card block or deleting the note.
Do not use a `DELETE` marker for this repair, because there is no existing Anki
note to delete.

Reference material that should be available in Obsidian but not tested in Anki
belongs in the `Reference:` section after the DAE prose, or outside the Anki
block after `END` when Anki is present, and before `Sources:`. Write it as a
bulleted list and keep it compact and exact.
Typical uses are links to related atomic notes, figures, formulas, lookup
tables, worked-example calculations, syntax snippets, and commands that support
the concept but would make a poor flashcard.

## Misfiled Notes

A non-DAE file in `Atomic Notes/` is not a valid alternate atomic-note class. Convert it or re-home it after review.
