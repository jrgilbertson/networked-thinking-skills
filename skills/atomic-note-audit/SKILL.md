---
name: atomic-note-audit
description: Use when auditing or improving the quality of Networked Thinking atomic notes in an Obsidian vault.
---

# Atomic Note Audit

Use this skill to audit every Markdown file in a configured Atomic Notes folder, produce vault-health KPIs, and create remediation queues.

## Required References

- `references/doctrine.md`
- `references/audit-rubric.md`
- `references/model-judgment-prompt.md`
- `references/remediation-context.md`
- `references/install-matrix.md`

## Read-Only Audit

1. Resolve vault config.
2. Run `scripts/audit_notes.py`.
3. Validate JSONL with `scripts/validate_jsonl.py`.
4. Generate Markdown report with `scripts/generate_report.py`.
5. Generate Obsidian Base with `scripts/generate_base.py` when requested.
6. Summarize KPIs and P0-P3/no-change queues.

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
agent supplies judgments; the skill-local scripts define the schema, validation,
merge, and report surfaces.

Privacy boundary: deterministic scans run locally. Model judgment may send note
content or excerpts to the model provider used by the active agent. Confirm the
user accepts that provider/tool trust boundary before running exhaustive model
judgment on private vault content.

Use `references/model-judgment-prompt.md` verbatim when asking an
LLM for model judgment. The prompt is generated from the scoring vocabulary
source of truth and must stay aligned with `scripts/finding_codes.py`.
Model output must be strict JSON and validated before it affects scoring.

To prepare one note for judgment without prompt drift, run:

```bash
python3 scripts/prepare_model_judgment.py --vault /path/to/vault --note-path "Atomic Notes/Example.md" --output /tmp/model-judgment-request.md
```

For Codex CLI exhaustive runs, use the validated batch collector:

```bash
python3 scripts/collect_model_judgments.py --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --output-jsonl /tmp/networked-thinking-audit/model-judgments.jsonl --raw-dir /tmp/networked-thinking-model-raw --model gpt-5.5
```

Keep `--raw-dir` outside the vault by default because it contains private note
content in prompts and logs. The collector resumes from an existing valid
`model-judgments.jsonl`, validates each response, and splits failed batches into
smaller retries.

Collect model responses as JSONL, one strict
`schemas/model-judgment.schema.json` object per line. Then apply them to
the deterministic audit rows before generating the model-judgment report or
Base:

```bash
python3 scripts/apply_model_judgments.py --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --model-judgments /tmp/networked-thinking-audit/model-judgments.jsonl --output-jsonl /tmp/networked-thinking-audit/model-applied.jsonl --output-manifest /tmp/networked-thinking-audit/model-applied-manifest.json
```

By default, the apply step hard-fails unless every audit row has exactly one
matching model judgment. Use `--allow-missing` only for a deliberate sampling
pass; unmatched rows stay `pending_model: true`.

For reviewed rows, model findings replace deterministic semantic findings. The
apply step keeps only deterministic audit checks a single-note model cannot
reliably infer: `missing_frontmatter`, `missing_parent`, `malformed_anki`, and
`duplicate_overlap`.
These checks depend on frontmatter presence, graph parentage, Anki marker
integrity, or cross-note context that deterministic validation can verify more
reliably than a single-note model judgment.

## Remediation

Do not mutate notes from audit findings alone. Generate or consume an explicit
remediation plan, or produce an explicit per-note destructive dry run for a
single user-directed operation. Load `references/remediation-context.md`
before planning any vault mutation.

Require official Obsidian skills and preflight before vault mutations. Use the
actual Obsidian CLI binary; `obsidian-cli` is the default because some systems
reserve `obsidian` for the GUI app binary. Require approval before destructive
operations. If a sandboxed agent cannot attach to the running Obsidian app,
rerun the Obsidian CLI step in an approved unsandboxed context instead of using
raw filesystem edits for app-context operations. When working from an installed
skill, prefer `python3 scripts/obsidian_cli.py` for app-context CLI commands.

For delete, split, move, or rename dry runs, report the target path, Anki
status, backlinks, intended Obsidian CLI command, link cleanup plan, and whether
the operation is permanent. Stop for an Anki-specific decision when a note has
Anki markers or Obsidian-to-Anki identifiers. When deleting a note with an
Obsidian-to-Anki ID, follow the exact `DELETE` marker, scan, verify, then delete
sequence in `references/remediation-context.md`, including warning
that the scan may update Obsidian-to-Anki plugin state files.

When a synced Anki card appears potentially not worth memorizing, treat it as
`anki_yagni`: flag it as a sanity check and stop for the learner's judgment. Do
not remove or keep Anki automatically; medical students, professors, and other
specialized learners may need memorization that a general-purpose auditor would
not.

For long-running goals, loops, or autonomous remediation batches, keep a durable
held-decision artifact as described in
`references/remediation-context.md`. Chat history and checkpoint
summaries are not sufficient state for duplicate, YAGNI, split, delete, rehome,
or factual-risk decisions.

Before delete, verify the running vault's `trashOption`. Deleting without the
CLI `permanent` flag follows that configured Obsidian behavior.

Treat timestamped audit reports, Bases, JSONL files, and manifests as immutable
historical artifacts by default. Remediation cleans live knowledge-graph files,
not prior audit outputs, unless the user explicitly asks for an audit artifact
correction. If an approved Obsidian-aware rename automatically updates
wikilinks inside audit reports, keep those mechanical link-maintenance changes
instead of manually reversing them.
