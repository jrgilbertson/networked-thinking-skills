# Networked Thinking Atomic Note Doctrine

An atomic note captures one durable concept in DAE format: Definition, Analogy, and Example.

## Required Shape

- One concept per file.
- Timestamp-prefixed filename whose stem copies the reader-visible applicable
  Definition source without its final period.
- Frontmatter with `title` and `aliases`.
- Clear Definition, Analogy, and Example content.
- At least one useful connection to a structure note or related concept.
- `Sources:` (plural label, numbered list) when the idea came from external material; provenance for later verification.
- Agent-access source lines, such as `Codex 5.5 last accessed [[YYYY-MM-DD]]`,
  use the actual local date when the note is created or edited, not a copied
  example date from prior work.
- Optional `Reference:` section (singular label, bulleted) after the DAE prose,
  or after the Anki `END` block when Anki is present, and before `Sources:`, for
  related atomic notes, figures, and compact Obsidian-only extras (alternate
  formula forms, long displays, lookup tables, commands, worked-example steps)
  that are not the claim tested on the card.

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
  `<full term> (<ACRONYM>)`, then use the acronym later. When a formula completes
  the concept, or the Definition cannot stand alone at review without one, put
  the formula in the Definition after a prose-first sentence. Keep formula and
  labels in the same Definition paragraph (plain-prose) or Definition section
  (legacy-headed). Prefer inline math; a lone blank-line `$$...$$` paragraph is
  not Definition prose for plain-prose DAE. Label each variable the formula uses
  with a "where …" clause or short gloss in that paragraph. Filename source is
  the first reader-visible Definition sentence for plain-prose and Basic DAE;
  leave equation and gloss off that sentence. For Cloze-only DAE, the naming
  table still uses the rendered cloze-bearing sentence. Stay inside 10-50
  rendered words by tightening prose; keep the primary formula in Definition
  rather than only in `Reference:`. Example, one paragraph, two sentences
  (filename uses only the first): Binomial standard deviation measures spread
  for a fixed number of independent trials. It is $\sqrt{np(1-p)}$, where $n$
  is the number of trials and $p$ is the probability of success. Prefer a
  Cloze on the same note when symbol recall is the goal (Anki-YAGNI); do not
  auto-create a second Anki note for every formula.
- Equations: write mathematics as LaTeX inside Markdown math delimiters. If a
  write or a sync corrupts an equation, restore the LaTeX command it decayed
  from. Replacing the equation with a plain-text description is not an
  acceptable response to a transport failure.
- Analogy: map the concept to a familiar concrete pattern. Start with a clear
  `<concept> is like <familiar referent>` mapping, then explain the shared
  relational structure in natural prose. The first visible letter of that
  sentence is capitalized. If the sentence starts with a wikilink, capitalize
  the visible alias (`[[Note|Creatine]] is like...`); keep mid-sentence aliases
  lowercase. Analogies that open with inline math may keep the math token first
  (`$n$ is like...`). Do not default to colon or semicolon templates; use
  punctuation only when the sentence would read naturally outside the note
  format.
- Example: concrete and specific. It starts with `For example,` and uses named
  tools, real numbers, real domains, or real situations. After the Definition
  has labeled the formula's variables, reuse those symbols in the Example
  without restating the full where-clause.
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
  applicable Definition source without its final period. The timestamp, `.md`
  extension, Markdown wrappers, and Anki cloze syntax are not part of that
  comparison. Compare cloze text as a reader sees it. All other visible words,
  capitalization, punctuation, and word order must match.
- The YAML `title` and H1 use the same short concept name. That short concept
  name does not need to repeat the full Definition sentence.

Choose the applicable Definition source by note shape. Visible DAE takes
precedence over optional Anki card text:

| Note shape | Applicable Definition source | Matching rule |
| --- | --- | --- |
| Plain-prose DAE, with or without Anki | First visible DAE sentence after the H1 | Exact reader-visible wording without the final period |
| Legacy headed DAE, with or without Anki | First sentence under `## Definition` | Exact reader-visible wording without the final period |
| Anki `Basic` with DAE stored only in `Back:` | First Definition sentence in `Back:` | Exact reader-visible wording without the final period |
| Anki `Cloze` with DAE stored only in the card body | Rendered cloze-bearing Definition sentence | Exact reader-visible wording without the final period |

Before writing the filename, confirm that its derived stem is valid as one
filename component in the target vault and platform. If it is not, redraft the
Definition source with the learner so the visible sentence and filename can
still match; never silently remove or substitute characters. Check both pairs
when creating or improving a note. Reconcile an existing or newly introduced
filename/Definition mismatch through the approved rename flow in the
remediation context.

When a learner or governing template explicitly declares that a pre-existing
user vault uses a different filename scheme, preserve it as a compatibility
exception unless the learner approves a migration. Do not describe it as
another Networked Thinking naming style or use nearby inconsistencies to weaken
the canonical rule. This exception applies only to workflows that receive that
declaration; model judgment without vault-level context evaluates the canonical
contract.

## Anki

Anki cards are optional. A non-Anki atomic note still needs DAE. Write non-Anki
atomic notes as plain prose after the H1: first a Definition paragraph, then an
Analogy paragraph, then an Example paragraph that starts with `For example,`.
Do not add `## Definition`, `## Analogy`, or `## Example` headings solely to
mark DAE in non-Anki notes. When Anki markers are present, `START` and `END`
blocks must be balanced and scoped to the note's concept.

`Basic` Front is a retrieval question for the note's central claim. YAML title,
H1, and Definition sentence identify the note; they are not the Front prompt.
Store Definition, Analogy, and Example on `Back:`, including any primary formula
and variable labels. When plain-prose DAE also appears before `START`, the
Anki payload is still only Front/Back inside the Basic block: put the primary
formula and labels on `Back:` (not only in the pre-`START` Definition), or the
formula will not show during review.

`Cloze` cards can store the Definition in the cloze body and keep the Analogy
and Example behind `Extra:` so Anki does not reveal them while testing the cloze
fields. Do not place an unclozed primary formula on the cloze question side if
it would reveal the deletion; cloze the formula tokens, rephrase, or put the
formula in `Extra:` when it would leak the answer.

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

Obsidian material that is not tested in Anki goes in `Reference:` after the DAE
prose, or after Anki `END` when Anki is present, and before `Sources:`. Write a
compact bulleted list. Typical uses: related atomic notes, figures, alternate
formula forms, long displays, edge-case displays, lookup tables, worked-example
calculations, syntax snippets, and commands. When a formula completes the
concept, put it in the Definition (with labels), not only in `Reference:`. On
Anki `Basic`, text only after `END`, only in post-Anki `Reference:`, or only in
pre-`START` prose while absent from `Back:`, is Obsidian-only and does not
appear during review.

## Misfiled Notes

A non-DAE file in `Atomic Notes/` is not a valid alternate atomic-note class. Convert it or re-home it after review.
