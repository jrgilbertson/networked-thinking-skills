# Audit Workflow

Use audit workflows before remediation. These commands read notes and write audit
artifacts; they do not mutate vault files.

## Synthetic Fixture Check

Run the fixture workflow first when validating a fresh checkout or changing audit
logic:

```bash
python3 -m shared.scripts.make_fixture_vault /tmp/networked-thinking-fixture-vault
python3 -m shared.scripts.audit_notes --vault /tmp/networked-thinking-fixture-vault --run-id fixture-run --jsonl /tmp/networked-thinking-audit/fixture-audit.jsonl --manifest /tmp/networked-thinking-audit/fixture-manifest.json --deterministic-fixture-output
python3 -m shared.scripts.validate_jsonl /tmp/networked-thinking-audit/fixture-audit.jsonl
python3 -m shared.scripts.generate_report --jsonl /tmp/networked-thinking-audit/fixture-audit.jsonl --manifest /tmp/networked-thinking-audit/fixture-manifest.json --output /tmp/networked-thinking-audit/fixture-report.md
python3 -m shared.scripts.generate_base --jsonl /tmp/networked-thinking-audit/fixture-audit.jsonl --output /tmp/networked-thinking-audit/fixture-audit.base
```

Expected command signals:

- `audit_notes` prints `rows=<count>`.
- `validate_jsonl` prints `valid_rows=<count>`.
- `generate_report` prints the Markdown report path.
- `generate_base` prints the Base file path.

## Real Vault Audit

Write outputs outside the vault unless the user explicitly wants generated files
inside the vault.

When writing audit artifacts inside an Obsidian vault, create one run folder
under the configured audit output folder using the vault timestamp style
`YYYYMMDDHHMM`, for example a folder named `202606061035 Model Judgment`. Do
not use dashed date folder names such as `2026-06-06 103558`.

Real-vault audit artifacts can expose private note paths, titles, links,
findings, and recommendations. Keep them outside this repo by default, do not
commit them, and do not paste or publish them without explicit approval.

```bash
python3 -m shared.scripts.audit_notes --vault /path/to/vault --run-id baseline-YYYYMMDDHHMM --jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json
python3 -m shared.scripts.validate_jsonl /tmp/networked-thinking-audit/baseline.jsonl
python3 -m shared.scripts.generate_report --jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --output /tmp/networked-thinking-audit/baseline-report.md
python3 -m shared.scripts.generate_base --jsonl /tmp/networked-thinking-audit/baseline.jsonl --output /tmp/networked-thinking-audit/baseline.base
```

## Deep Baseline Guidance

- Confirm the vault path and configured Atomic Notes and Structure Notes folders
  before running a full baseline.
- Treat the generated JSONL and manifest as the machine-readable audit record.
  Treat the Markdown report and Base file as review surfaces.
- Review the lowest-scoring P0 notes first, then P1. The score determines the
  remediation bucket.
- Sample no-change notes and P3 notes during the first baseline to catch false
  negatives before trusting the queue.
- Do not remediate directly from an audit row. Create or consume an explicit
  remediation plan, then follow [remediation.md](remediation.md).

## Model Judgment

Model judgment assumes the user is already running an authenticated desktop or
terminal agent in the vault, such as Claude Desktop, Claude Code, Codex CLI, or
Codex Desktop. The audit skill does not own provider authentication, API keys, or
a hosted inference service.

Deterministic scans run locally. Model judgment may send note content or
excerpts to the model provider used by the active agent. Confirm the user accepts
that provider/tool trust boundary before running exhaustive model judgment on
private vault content.

The deterministic audit remains the source input. A model-judgment pass should
emit strict JSON matching `shared/schemas/model-judgment.schema.json`; validate
those judgments before they affect scores, buckets, or reports. In default
mode, review flagged or ambiguous notes plus a sample of apparently clean notes.
In exhaustive mode, review every note.
