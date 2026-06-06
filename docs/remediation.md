# Remediation

Audit and remediation are separate phases. Audit recommendations do not mutate
notes. The source context is
[`shared/references/remediation-context.md`](../shared/references/remediation-context.md).

## Safety Gates

- Install the official Obsidian skills before mutation. Remediation requires
  `obsidian-cli`, `obsidian-markdown`, and `obsidian-bases` for vault-aware file
  edits, links, moves, and deletes.
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

## Modes

- `improve-in-place`: Edit one DAE note while preserving its path unless a
  rename is separately approved.
- `split-multi-note`: Propose child notes, rebuild aliases and links, then
  delete the original only after approval and Obsidian-aware preflight.
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
