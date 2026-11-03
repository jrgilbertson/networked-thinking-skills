---
name: atomic-note-audit
description: Use when auditing or improving the quality of Networked Thinking atomic notes in an Obsidian vault.
---

# Atomic note audit

Audit every Markdown file in the configured Atomic Notes folder, report
vault-health KPIs, and create remediation queues. Audit first; apply repairs
only through the remediation workflow below. This skill supports batch audit
and remediation on its own. Install `atomic-note` alongside it for individual
note authoring.

## Required references

- `references/doctrine.md`: read before judging note quality. Defines DAE,
  naming, sourcing, learner purpose, and Anki requirements.
- `references/audit-rubric.md`: read before interpreting findings, scores,
  buckets, or clean-note KPIs.
- `references/model-judgment-prompt.md`: use verbatim for model judgments.
- `references/model-judgment-workflow.md`: read before preparing, collecting, or
  applying model judgments. Includes runner commands and provenance checks.
- `references/remediation-context.md`: read before planning any vault mutation.
  Defines approval, Obsidian tooling, rename, Anki, and held-decision workflows.
- `references/install-matrix.md`: read for supported installation surfaces and
  self-contained package requirements.

## Read-only audit

1. **Resolve scope.** Confirm the vault configuration and Atomic Notes folder.
   Write artifacts outside the vault unless the user requests them inside it.
   For in-vault artifacts, create one run folder under the configured audit
   output folder using `YYYYMMDDHHMM`, for example `202606061035 Model Judgment`.
2. **Scan every note.** Run `scripts/audit_notes.py` to produce the deterministic
   audit JSONL and run manifest. Use each script's `--help` for arguments.
3. **Validate the baseline.** Run `scripts/validate_jsonl.py` on the audit JSONL
   before using it for reports or model judgments.
4. **Review note quality.** Read the doctrine and rubric. Model judgment may send
   note content or excerpts to the active agent's model provider. Before
   exhaustive model judgment on private vault content, confirm that the user
   accepts this provider/tool trust boundary. In default mode,
   model-judge flagged or ambiguous notes and a sample of apparently clean
   notes. In exhaustive mode, model-judge every note. Follow
   `references/model-judgment-workflow.md` to collect, validate, and apply
   judgments to the deterministic rows before generating model-judgment reports.
5. **Generate review artifacts.** Run `scripts/generate_report.py` with the
   validated audit JSONL and matching manifest. When requested, generate an
   Obsidian Base with `scripts/generate_base.py`.
6. **Report the queues.** Summarize KPIs and P0-P3/no-change queues, including
   pending model judgments and fact checks when interpreting clean-note counts.
   Read-only audit ends with review artifacts and recommendations.

Deterministic scans run locally. Model judgment uses the active desktop or
terminal agent, such as Claude Desktop, Claude Code, Codex CLI, or Codex Desktop.
Use the agent's existing authentication; this skill does not collect API keys,
configure provider accounts, or send vault content through a repo-owned service.

## Remediation

1. **Plan before mutation.** Read `references/remediation-context.md`. Generate
   or consume an explicit remediation plan, or prepare an explicit per-note
   destructive dry run for a single user-directed operation. Audit findings
   alone do not authorize writes.
2. **Validate the dry run.** Run `scripts/remediate_notes.py --plan <plan.json>
   --manifest <manifest.json>`. Add `--destructive-allowed` to let `split`,
   `delete`, `rename`, or `move` pass validation without writing anything.
   Before approval, report each destructive target's path, Anki status,
   backlinks, intended Obsidian CLI command, link cleanup plan, and permanence.
   Before deletion, verify the running vault's `trashOption`; omitting the CLI
   `permanent` flag follows that setting.
3. **Resolve learner decisions.** Require approval before destructive
   operations. Stop for an Anki-specific decision when a note has Anki markers
   or Obsidian-to-Anki identifiers. For `anki_yagni`, ask whether the card is
   worth memorizing for this learner. Medical students, professors, and other
   specialized learners may need memorization the auditor does not. Hold the
   note for that decision rather than automatically keeping or removing Anki.
   During long-running goals, loops, or autonomous
   batches, maintain the remediation context's durable held-decision artifact
   for duplicate, YAGNI, split, delete, rehome, and factual-risk decisions.
   Chat history and checkpoint summaries are not sufficient.
4. **Apply approved operations through Obsidian.** Require official Obsidian
   skills and preflight, including a verified CLI binary. For decayed-LaTeX
   edits, follow **Repair script** below. Prefer
   `python3 scripts/obsidian_cli.py` for app-context commands; its resolver uses
   the registered `obsidian` command, rejects the macOS GUI executable, and
   checks the CLI fallback. If a sandbox prevents attachment to the running
   app, rerun in an approved unsandboxed context. Never substitute raw
   filesystem edits for app-context operations. When deleting a note with an
   Obsidian-to-Anki ID, follow the remediation context's `DELETE`, scan, verify,
   then delete sequence. Warn before scanning that plugin state files may
   change.
5. **Verify and report the result.** Follow the remediation context's path,
   link, content, and Anki verification for each operation. Preserve timestamped
   reports, Bases, JSONL files, and manifests as historical artifacts unless
   the user requests a correction. Keep mechanical wikilink changes that an
   approved Obsidian-aware rename makes inside those reports.

## Repair script

`scripts/remediate_notes.py` writes only when called with
`--execute --vault "<Vault Name>"`.
Use `--obsidian-binary` when the default `obsidian` resolves to the GUI app rather
than the CLI. Only `edit` is executable, and each operation must already carry
`approved: true` under the remediation context's approval gate. Decayed-LaTeX
repairs are non-destructive `edit` operations but still need the owner's
explicit approval before execution.

The script reports `operation_count=` and, on execution,
`dispatched_note_count=`. A halted batch also prints `dispatched_note=<path>`
for every note it sent a write for. Inspect the manifest's
`dispatched_note_paths` to identify notes that need inspection or rollback.
