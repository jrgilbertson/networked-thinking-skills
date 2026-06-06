---
name: atomic-note-audit
description: Use when auditing or improving the quality of Networked Thinking atomic notes in an Obsidian vault.
---

# Atomic Note Audit

Use this skill to audit every Markdown file in a configured Atomic Notes folder, produce vault-health KPIs, and create remediation queues.

## Required References

- `../../shared/references/doctrine.md`
- `../../shared/references/audit-rubric.md`
- `../../shared/references/remediation-context.md`
- `../../shared/references/install-matrix.md`

## Read-Only Audit

1. Resolve vault config.
2. Run `shared/scripts/audit_notes.py`.
3. Validate JSONL with `shared/scripts/validate_jsonl.py`.
4. Generate Markdown report with `shared/scripts/generate_report.py`.
5. Generate Obsidian Base with `shared/scripts/generate_base.py` when requested.
6. Summarize KPIs and P0-P3 queues.

When writing audit artifacts inside an Obsidian vault, create one run folder
under the configured audit output folder using the vault timestamp style
`YYYYMMDDHHMM`, for example `202606061035 Model Judgment`. Do not use dashed
date folder names such as `2026-06-06 103558`.

## Model Judgment

Use deterministic scan for every note. In default mode, model-judge flagged or
ambiguous notes and a sample of apparently clean notes. In exhaustive mode,
model-judge every note.

Model judgment is performed by the active desktop or terminal agent that the
user is already using in the vault, such as Claude Desktop, Claude Code, Codex
CLI, or Codex Desktop. Do not require this skill to collect API keys, configure
provider accounts, or send vault content through a repo-owned service. The
agent supplies judgments; the shared scripts define the schema, validation,
merge, and report surfaces.

Privacy boundary: deterministic scans run locally. Model judgment may send note
content or excerpts to the model provider used by the active agent. Confirm the
user accepts that provider/tool trust boundary before running exhaustive model
judgment on private vault content.

Model output must be strict JSON and validated before it affects scoring.

## Remediation

Do not mutate notes from audit findings alone. Generate or consume an explicit remediation plan. Require official Obsidian skills and preflight before vault mutations. Require approval before destructive operations.
