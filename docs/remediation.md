# Remediation

Audit and remediation are separate phases. Audit recommendations do not mutate
notes. The source context is
[`shared/references/remediation-context.md`](../shared/references/remediation-context.md).

## Safety Gates

- Install the official Obsidian skills before mutation. Remediation requires
  `obsidian-cli`, `obsidian-markdown`, and `obsidian-bases` for vault-aware file
  edits, links, moves, and deletes.
- Use the actual Obsidian CLI binary for app-context commands. On current macOS
  installs this is often `obsidian-cli`, while `obsidian` may resolve to the GUI
  app binary and should not be used for CLI automation unless it is verified to
  print CLI help.
- Use a remediation plan with `plan_version`, `audit_run_id`, `mode`, and
  `operations`.
- Use dry-run manifests to validate a plan before execution:

```bash
python3 -m shared.scripts.remediate_notes --plan /path/to/remediation-plan.json --manifest /tmp/networked-thinking-remediation/dry-run-manifest.json
```

- Destructive operations are `split`, `delete`, `rename`, and `move`. They
  require explicit approval on each operation and the destructive approval gate.
  The task-level `--allow-destructive` wording maps to this gate; this branch's
  executable CLI flag is `--destructive-allowed`. This flag only permits
  destructive operations to pass plan validation and appear in the dry-run
  manifest; it does not apply changes to the vault:

```bash
python3 -m shared.scripts.remediate_notes --plan /path/to/remediation-plan.json --manifest /tmp/networked-thinking-remediation/destructive-dry-run-manifest.json --destructive-allowed
```

- Split operations must include `delete_original: true` and approved
  `proposed_outputs` with `note_path` and `content` for each child note.
- Duplicate and overlap findings are review candidates only. Do not auto-merge
  notes.
- In autonomous audit-review batches, hold likely duplicate, overlap, or
  Anki-YAGNI notes instead of forcing them to a clean score. Summarize each hold
  at the batch checkpoint with the candidate note, the nearby overlapping note
  or memorization concern, and the recommended user decision. Do not delete,
  merge, remove Anki markers, or rewrite the held note until the learner
  approves the specific outcome.

## Obsidian CLI Routing

Run preflight before any vault mutation:

```bash
python3 -m shared.scripts.preflight_obsidian --require-cli
```

The default binary is `obsidian-cli`. Override only when the target environment
uses a different executable for the official CLI:

```bash
python3 -m shared.scripts.preflight_obsidian --require-cli --obsidian-binary obsidian
```

Use the repo helper for app-context commands. It resolves the real CLI binary,
falls back to the app-bundled macOS `obsidian-cli`, and refuses the macOS GUI
binary when `obsidian` resolves to the wrong executable:

```bash
python3 -m shared.scripts.obsidian_cli vault="My Vault" eval code="app.vault.getFiles().length"
```

Verify the chosen binary against the running Obsidian app before relying on it:

```bash
type -a obsidian obsidian-cli
python3 -m shared.scripts.obsidian_cli help
python3 -m shared.scripts.obsidian_cli vault info=name
```

If `obsidian` resolves to the GUI app binary, use `obsidian-cli` or a verified
CLI shim instead. If `obsidian-cli` says it is unable to find Obsidian while the
app is running, check whether Obsidian owns the CLI socket:

```bash
lsof -U | grep .obsidian-cli.sock
```

When Obsidian owns `~/.obsidian-cli.sock` but the CLI still cannot attach from
Codex, rerun the Obsidian CLI command in an approved unsandboxed context. Do not
fall back to raw filesystem creates, moves, renames, deletes, Anki scans, or
link-sensitive edits.

Create atomic notes through Obsidian app-context APIs. Do not create notes with
direct filesystem path writes.

## Per-Note Destructive Dry Run

Before a destructive operation on one note, produce a human-readable dry-run
summary and get explicit approval. The dry run must include:

- Target `note_path`.
- Anki status. If the note contains `TARGET DECK`, `START`, `END`, `Basic`,
  `Cloze`, or Obsidian-to-Anki identifiers, stop and ask for an Anki-specific
  policy before deleting, splitting, or moving the note.
- Anki YAGNI status. If the audit or review raises `anki_yagni`, stop and ask
  whether the card is worth memorizing for the learner's current use case. Do
  not remove Anki markers, delete Anki cards, or keep the card by default. If
  the user chooses to remove only the Anki card while keeping the Obsidian note,
  use the `DELETE` marker and scan sequence, verify the old Anki note ID no
  longer resolves, then promptly remove the ID-less `TARGET DECK`/`START`/`END`
  card block so a later scan cannot recreate the card.
- Anki deletion path. If the approved delete target has an Obsidian-to-Anki ID,
  delete the Anki note before deleting the Obsidian file:
  1. Confirm Anki is open and AnkiConnect is reachable. Try
     `http://localhost:8765` if `http://127.0.0.1:8765` does not respond; some
     local AnkiConnect installs bind to one host name but not the other.
  2. Add a standalone `DELETE` line immediately above the existing ID line.
  3. Tell the user that the scan may update Obsidian-to-Anki plugin state files
     such as `.obsidian/plugins/obsidian-to-anki-plugin/data.json`.
  4. Run `Obsidian_to_Anki: Scan Vault` in the running Obsidian app.
  5. Verify the Anki note ID no longer resolves in Anki and the `DELETE`/ID
     block was removed from the Obsidian note.
  6. Delete the Obsidian note with Obsidian-aware tooling.

  Example marker block:

  ```markdown
  DELETE
  <!--ID: 1722884195648-->
  ```

  Delete the Obsidian note promptly after the successful scan. If an ID-less
  `START`/`END` card block remains in the vault and a later scan runs, the
  plugin can recreate the Anki card.
- Cloze replacement path. If an existing synced `Cloze` note reduces or
  renumbers cloze deletions, do not rely on a normal edit-and-scan. Removed
  cloze ordinals can leave stale Anki cards. Use the same `DELETE` marker and
  scan sequence to delete the old Anki note, but do not delete the Obsidian
  file. After the old ID no longer resolves and the Obsidian note is ID-less,
  force the plugin to rescan the ID-less file before recreating it. Either make
  a harmless app-context content normalization or use the plugin's file-hash
  cache clearing behavior; a plain second scan can skip the unchanged ID-less
  file. Run `Obsidian_to_Anki: Scan Vault` again to create a fresh ID. Verify
  the new Anki note exists and its card count equals the number of distinct
  current cloze ordinals.
- Stale-ID repair path. If AnkiConnect or `Obsidian_to_Anki: Scan Vault`
  shows that an Obsidian-to-Anki ID in the note no longer exists in Anki, do
  not add `DELETE`; there is no Anki note left to delete. If the note should
  remain Anki-backed, remove only the stale `<!--ID: ...-->` marker through
  Obsidian app-context tooling, run `Obsidian_to_Anki: Scan Vault`, and verify
  that the file receives a fresh ID. Then check the new Anki note's model,
  deck, card count, and representative field content. If the note's
  memorization value is uncertain, stop for the learner's judgment before
  recreating the card.
- Current backlinks from `obsidian-cli backlinks path="..." format=json`.
- Intended Obsidian CLI command. Deletes default to Obsidian's configured
  **Deleted files** behavior when the `permanent` flag is omitted. Check
  `trashOption` in the running app and report whether the vault will use system
  trash, Obsidian `.trash`, or permanent deletion:

```bash
python3 -m shared.scripts.obsidian_cli eval code='app.vault.getConfig("trashOption")'
```

```bash
python3 -m shared.scripts.obsidian_cli delete path="Atomic Notes/Example.md"
```

- Link cleanup plan for each backlink that should change. Use Obsidian-aware
  file editing for live knowledge-graph changes.
- Audit-output handling. Timestamped audit reports, Bases, JSONL files, and
  manifests are immutable historical artifacts by default. Do not edit old audit
  outputs during remediation unless the user explicitly asks for an audit
  artifact correction. One exception: when an approved Obsidian-aware rename
  updates wikilinks inside audit reports automatically, keep the automatic link
  maintenance. Do not manually reverse those mechanical Obsidian updates.
- Whether any operation is permanent. Permanent delete requires separate
  explicit approval and must use the CLI's `permanent` flag only after that
  approval.

Do not treat a dry-run manifest or summary as permission to mutate the vault.
Approval must happen after the user sees the expected effects.

## Modes

- `improve-in-place`: Edit one DAE note while preserving its path unless a
  rename is separately approved.
- `split-multi-note`: Propose child notes, rebuild aliases and links, then
  delete the original only after approval and Obsidian-aware preflight. Create
  Anki-intended child notes through Obsidian app-context APIs before the first
  Obsidian-to-Anki scan; do not use direct filesystem path writes.
- `rehome-non-DAE`: Recommend a better home for source material or non-DAE
  notes. Do not move automatically.
- `link-parent`: Add or propose a structure-note link so the atomic note has a
  parent context.
- `mark-factual-risk`: Mark broad or high-risk claims for fact checking before
  treating them as reliable.
- `duplicate-overlap-review`: Compare candidate notes against related notes and
  decide whether to keep, rewrite, split, or manually merge.

## Minimal Plan Shape

```json
{
  "plan_version": "1.0.0",
  "audit_run_id": "baseline-YYYYMMDD",
  "mode": "improve-in-place",
  "operations": [
    {
      "operation": "edit",
      "note_path": "Atomic Notes/Example.md",
      "priority": "P1"
    }
  ]
}
```

Use `operation`, not the legacy `operation_type` key.
