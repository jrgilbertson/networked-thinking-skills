---
name: atomic-note-audit
description: Use when auditing or improving the quality of Networked Thinking atomic notes in an Obsidian vault.
---

# Atomic note audit

Review selected Atomic Notes with the model and exact integrity checks, then publish one recommendation-first plain Markdown report. Audit first; apply repairs
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

1. **Resolve scope and privacy first.** Name the vault and selected notes before reading or exporting them. Default to model review of every note in that scope; an intentional limit is partial coverage, not a whole-vault conclusion. Before model review of private content, confirm that the user accepts this provider/tool trust boundary. Reuse an existing confirmation for the same scope and destination. Use the active agent's existing authentication; do not collect API keys or add a model service.
2. **Capture unscored inventory and exact checks.** Use `scripts/audit_inventory.py`, not a semantic baseline. Preserve source paths, hashes, captured content and scope. Keep supporting evidence outside the vault by default. If in-vault evidence was explicitly requested, use one `Evidence/` directory under the run folder. Keep raw prompts and logs external unless separately requested. Follow vault instructions for every read: when Obsidian app access is required, use the official CLI and `ObsidianAdapter` to supply selected paths, source reads, parent targets and link resolution to `inventory_vault`; supply the same app reader to collection and composition. Never fall back to raw filesystem reads. An app-exported snapshot is also valid if it preserves paths and is refreshed through the app before final composition.
3. **Review meaning with the model.** Read the doctrine, rubric and `references/model-judgment-workflow.md`. Use the shared prompt and existing runner adapters. Validate each batch before accepting it. Resume only compatible source/prompt/model/runner results. Do not replace missing judgments with heuristic quality scores. Read-only Anki checks may use `notesInfo` and `cardsInfo`; never sync or change cards as part of the audit.
4. **Compose truthful results.** Recheck source hashes and compose validated model judgments with separately attributed integrity evidence. Pending, failed, unavailable and stale model reviews have null quality values and are never clean. Keep unresolved fact-checks explicit. Anki unavailable or not requested means not checked, not passed. After a collection interruption, still compose and report accepted work and unfinished coverage.
5. **Publish one report.** Generate `Audit.md` from the matching results and manifest. Use plain Markdown with the recommendation first, concise coverage, then P0-P3 priority buckets. Show each affected note once in the action queue with a usable note link, concrete change and short reason. Summarize unchanged notes as a count. Record completed fixes or held decisions only from evidence; a suggestion is not a completed fix. Link to supporting evidence. Do not rely on graphics or publish competing baseline/model reports. Generate a Base only if requested.
6. **Finish read-only.** Return the one report and its actual coverage. Audit findings do not authorize note or card changes. Preserve historical artifacts unless the user explicitly requests changes. For an in-vault report, use one run folder under the configured output folder with a `YYYYMMDDHHMM` name, such as `202606061035 Audit`.

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
