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

Verify the chosen binary against the running Obsidian app before relying on it:

```bash
type -a obsidian obsidian-cli
obsidian-cli help
obsidian-cli vault info=name
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
- Anki deletion path. If the approved delete target has an Obsidian-to-Anki ID,
  delete the Anki note before deleting the Obsidian file:
  1. Confirm Anki is open and AnkiConnect is reachable.
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
- Current backlinks from `obsidian-cli backlinks path="..." format=json`.
- Intended Obsidian CLI command. Deletes default to Obsidian's configured
  **Deleted files** behavior when the `permanent` flag is omitted. Check
  `trashOption` in the running app and report whether the vault will use system
  trash, Obsidian `.trash`, or permanent deletion:

```bash
obsidian-cli eval code='app.vault.getConfig("trashOption")'
```

```bash
obsidian-cli delete path="Atomic Notes/Example.md"
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
