# Atomic Note Remediation Context

Audit and remediation are separate phases. Audit recommendations do not mutate notes.

## Obsidian-Aware Mutation

Use the official Obsidian skills and the actual Obsidian CLI binary for
link-sensitive file operations. Prefer `obsidian-cli` unless the environment
has verified that `obsidian` is the official CLI executable, not the GUI binary.
When working from this repo, prefer `python3 -m shared.scripts.obsidian_cli` so
agents use the shared resolver and attach-failure hint instead of hard-coded
local binary paths.
If the CLI cannot reach the running Obsidian app from an agent sandbox, stop and
ask for approved unsandboxed execution. The official CLI uses a local Unix
socket such as `~/.obsidian-cli.sock`; in Codex CLI, sandboxed commands can fail
with "unable to find Obsidian" even when Obsidian is running and owns that
socket. Do not work around that by using raw filesystem writes for app-context
creates, moves, renames, deletes, Anki scans, or link-sensitive edits.

Create atomic notes through Obsidian app-context APIs. Do not create notes with
direct filesystem path writes.

When invoking app-context create or modify operations from a shell, pass note
content through a quote-safe transport such as a serialized JSON/base64 payload
or a helper that escapes content before eval. Do not inline large Markdown in
shell quotes when content may contain apostrophes, backticks, shell
substitutions, or wikilinks.

## Improve In Place

Improve one DAE note while preserving the file path unless a rename is explicitly approved.

## Split Multi-Note Files

Create proposed child notes, rebuild aliases and links, then delete the original only after approval and Obsidian-aware preflight. When a child note is Anki-intended, create it through Obsidian app-context APIs, not direct filesystem path writes, before running the first Obsidian-to-Anki scan.

## Rehome Non-DAE Notes

Recommend a better home by default. Do not move the note automatically.

## Delete Notes

Delete only from an approved remediation plan or explicit per-note approval.
Before approval, report the target path, Anki status, backlinks, intended CLI
delete command, link cleanup plan, and whether deletion is permanent. Deleting
without the CLI `permanent` flag uses the vault's configured Obsidian
`trashOption`; check the running app and report whether that means system trash,
Obsidian `.trash`, or permanent deletion. Permanent delete requires a separate
explicit approval.

If a note contains `TARGET DECK`, `START`, `END`, `Basic`, `Cloze`, or
Obsidian-to-Anki identifiers, stop for an Anki-specific decision before deleting
or splitting it.

If an audit finding or review judgment raises `anki_yagni`, stop and ask whether
the card is worth memorizing for the learner's current use case. Do not remove
Anki markers, delete Anki cards, or keep the card by default. If the user chooses
to remove only the Anki card while keeping the Obsidian note, use the `DELETE`
marker and scan sequence, verify the old Anki note ID no longer resolves, then
promptly remove the ID-less `TARGET DECK`/`START`/`END` card block so a later
scan cannot recreate the card.

If the user approves deleting a note that has an Obsidian-to-Anki ID, do not
delete the Obsidian file first. Use this sequence exactly so the Anki note is
not orphaned:

1. Confirm Anki is open and AnkiConnect is reachable. Try
   `http://localhost:8765` if `http://127.0.0.1:8765` does not respond; some
   local AnkiConnect installs bind to one host name but not the other.
2. Add a standalone `DELETE` line immediately above the existing ID line, for
   example:

   ```markdown
   DELETE
   <!--ID: 1722884195648-->
   ```

3. Tell the user that the scan may update Obsidian-to-Anki plugin state files
   such as `.obsidian/plugins/obsidian-to-anki-plugin/data.json`.
4. Run `Obsidian_to_Anki: Scan Vault` in the running Obsidian app.
5. Verify the Anki note ID no longer resolves in Anki and the `DELETE`/ID block
   was removed from the Obsidian note.
6. Delete the Obsidian note with Obsidian-aware tooling.

Delete the Obsidian note promptly after the successful scan. If an ID-less
`START`/`END` card block remains in the vault and a later scan runs, the plugin
can recreate the Anki card.

For an existing synced `Cloze` note, reducing or renumbering cloze deletions is
also an Anki replacement operation. Do not rely on a normal scan after editing:
removed cloze ordinals can leave stale Anki cards. Add `DELETE` above the
existing ID, run `Obsidian_to_Anki: Scan Vault`, verify the old Anki note ID no
longer resolves and the note is ID-less, then force the plugin to rescan the
ID-less Obsidian note before recreating it. Either make a harmless app-context
content normalization or use the plugin's file-hash-cache clearing behavior; a
plain second scan can skip the unchanged ID-less file. Scan again to recreate
the Anki note. After recreation, verify the new ID is present and the number of
Anki cards equals the number of distinct current cloze ordinals. Do not delete
the Obsidian file for this cloze replacement case.

## Audit Outputs

Timestamped audit reports, Bases, JSONL files, and manifests are immutable
historical artifacts by default. Remediation cleans live knowledge-graph files,
not prior audit outputs, unless the user explicitly asks for an audit artifact
correction. If an approved Obsidian-aware rename automatically updates
wikilinks inside audit reports, keep those mechanical link-maintenance changes.
Do not manually reverse Obsidian's automatic rename updates.

## Duplicate And Overlap Review

Flag candidates only. Do not auto-merge.
