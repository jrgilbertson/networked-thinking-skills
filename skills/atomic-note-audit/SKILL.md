---
name: atomic-note-audit
description: Use when auditing or improving Networked Thinking atomic notes in an Obsidian vault, or resuming selected numbered recommendations from an audit report.
compatibility: Python 3.11+; an authenticated local model runner for semantic review; running Obsidian with its official CLI and shared local temporary-file access for live publication; AnkiConnect for requested Anki checks.
---

# Atomic note audit

Review selected Atomic Notes with model judgment and exact integrity checks.
Deliver one numbered Markdown report that also records later decisions and
verified work. This skill supports batch audit and remediation on its own;
`atomic-note` is a companion for individual note authoring.

## Required references

- [Doctrine](references/doctrine.md): read before judging note quality; owns DAE, naming, sourcing, learner purpose, and Anki requirements.
- [Audit rubric](references/audit-rubric.md): read before interpreting findings, scores, buckets, or clean-note KPIs.
- [Model judgment prompt](references/model-judgment-prompt.md): use verbatim for model judgments.
- [Model judgment workflow](references/model-judgment-workflow.md): read before capturing, collecting, or applying judgments; owns runner commands and provenance.
- [Audit review record](references/audit-review-record.md): read before publishing or resuming a report; owns format, identity, outcome input, recovery, and guarded publication.
- [Remediation context](references/remediation-context.md): read before planning a source-note or card mutation; owns approvals, Obsidian tooling, renames, Anki, and held decisions.
- [Install matrix](references/install-matrix.md): read for supported installation surfaces and self-contained package requirements.

## Read-only audit

1. **Resolve scope and privacy first.** Name the vault and selected notes before reading or exporting them. Default to model review of every note in that scope; an intentional limit is partial coverage, not a whole-vault conclusion. Before model review of private content, confirm that the user accepts this provider/tool trust boundary. Reuse an existing confirmation for the same scope and destination. Use the active agent's existing authentication; do not collect API keys or add a model service.
2. **Capture unscored inventory and exact checks.** Use `scripts/audit_inventory.py`. Preserve source paths, hashes, captured content and scope in external working files. Raw prompts and logs stay external unless separately requested. If in-vault evidence was explicitly requested, use one `Evidence/` directory under the configured audit output folder. Follow vault instructions for every read: when app access is required, use the official CLI and `ObsidianAdapter` for selected paths, source reads, parent targets and link resolution. Supply the same app reader to collection and composition. Never fall back to raw filesystem reads. A path-preserving app-exported snapshot refreshed before final composition is also valid.
3. **Review meaning with the model.** Read the doctrine, rubric and model judgment workflow. Use the shared prompt and existing runner adapters. Validate each batch and resume only compatible source/prompt/model/runner results. Missing judgments have no heuristic substitute. Read-only Anki checks may use `notesInfo` and `cardsInfo`; never sync or change cards during an audit.
4. **Compose truthful results.** Recheck source hashes and compose validated judgments with separately attributed integrity evidence. Pending, failed, unavailable and stale reviews have null quality values and are never clean. Keep fact-checks unverified until checked against sources. Anki unavailable or not requested means not checked. After an interruption, report accepted work and unfinished coverage.
5. **Publish one report.** Follow the audit review record reference. Use plain Markdown with the recommendation first, concise coverage, and one table sorted P0 through P3: `#`, `Priority`, `Note`, `Recommendation`, `Action taken`. Show each affected note once with all substantive actions. Keep unchanged notes as a count. Initialize actions as pending; suggestions are not completed fixes. Publish `<YYYYMMDDHHMM> Atomic note audit.md` directly in `audit_output_folder`, with no per-run report folder. Capture user-local time once. Generate a Base only if requested.
6. **Finish read-only.** Return the report and actual coverage. The Markdown report is the durable source of truth; temporary data may be discarded and recreated from it. Preserve historical reports and locations. Audit findings authorize no note/card changes and no migration or cleanup.

## Resume selected items

1. Read the selected report through the required Obsidian app interface and export a fresh external snapshot. Recover its item/action IDs, recommendations and visible outcomes under the audit review record reference. Temporary audit files are optional.
2. Resolve the requested decisions or operations. Record held/declined decisions without calling a provider or Anki. Source/card changes follow **Remediation** below and its existing approvals.
3. Verify actual results before recording new completion. Keep previous work dated and separate from new findings; partial work names what remains. Prepare and publish the report update with its expected current text, then verify readback and links. Only that verified write makes the new outcome durable.

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
   batches, use the selected audit report as the remediation context's durable
   held-decision artifact for duplicate, YAGNI, split, delete, rehome, and
   factual-risk decisions.
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
