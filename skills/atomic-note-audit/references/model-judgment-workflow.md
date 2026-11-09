# Model-led audit workflow

Model judgment is the default semantic review for all explicitly selected notes.
Start from an unscored inventory; no scored baseline is required.
Use the doctrine and generated model prompt before judging content.
Choose scope and resolve the provider-sharing boundary before exporting private notes.

## Current installed workflow

Run from the installed skill root.
The examples below use canonical repository module commands; generated installed references use the equivalent `scripts/*.py` commands.
Set `VAULT` to the authorized vault or an app-exported snapshot and `AUDIT_MODEL` to the configured model.
Set `EVIDENCE` and `RAW` to external working directories and `REPORT` to an external Markdown draft.
The learner-facing report is the durable review record; working directories may be discarded after publication.

```bash
python3 scripts/audit_inventory.py --vault "$VAULT" --run-id synthetic-example --evidence-dir "$EVIDENCE"
python3 scripts/collect_model_judgments.py --runner codex --model "$AUDIT_MODEL" --vault "$VAULT" --inventory-jsonl "$EVIDENCE/inventory.jsonl" --output-jsonl "$EVIDENCE/judgments.jsonl" --raw-dir "$RAW"
python3 scripts/apply_model_judgments.py --vault "$VAULT" --inventory-jsonl "$EVIDENCE/inventory.jsonl" --model-judgments "$EVIDENCE/judgments.jsonl" --output-jsonl "$EVIDENCE/results.jsonl" --output-manifest "$EVIDENCE/manifest.json"
python3 scripts/validate_jsonl.py "$EVIDENCE/results.jsonl"
python3 scripts/generate_report.py --jsonl "$EVIDENCE/results.jsonl" --manifest "$EVIDENCE/manifest.json" --output "$REPORT"
```

Use a unique run ID rather than the example ID for a real run.
Add repeatable `--note-path "Atomic Notes/Example.md"` arguments to inventory capture for an explicit subset.
Add `--check-anki` only for the read-only AnkiConnect check.
Without it, integration is not checked; an unavailable connection is also not checked.
Missing targets and duplicate source IDs remain distinct integrity failures.
Anki ID examples in code and frontmatter do not trigger live lookups.
Attachment file targets are checked; their fragments remain `not_checked` rather than being parsed as Markdown.

If evidence inside the vault was explicitly requested, inventory capture accepts `--allow-vault-evidence` and places its JSONL under one `Evidence/` directory.
Use the printed inventory path in subsequent commands.
Raw prompts and runner logs stay in the external `RAW` directory unless separately requested.

When the vault requires app-context access, do not run the filesystem capture command on the live vault.
Supply app-derived discovery, reads, parent targets and resolution to `inventory_vault`, and pass the app reader as `source_reader` to collection and `compose_inventory`.
The included `ObsidianAdapter.read_note` can provide that reader.
Alternatively export a complete path-preserving snapshot through the app and refresh it through the app before composition; scope and link-check conclusions must describe the captured snapshot.
Do not claim the private source is current when only an older snapshot was checked.

## Runner boundary

The generic runner accepts a configured local agent command:

```bash
python3 scripts/collect_model_judgments.py --runner command --command 'local-agent --write-final-response "{output_path}"' --model-identity configured-model --vault "$VAULT" --inventory-jsonl "$EVIDENCE/inventory.jsonl" --output-jsonl "$EVIDENCE/judgments.jsonl" --raw-dir "$RAW"
```

Replace the command and model identity with the active local runner configuration.
The collector sends the prompt on stdin and reads the response from stdout or `{output_path}`.
Quote path placeholders when paths can contain spaces; double literal braces in command templates.
Adapters own invocation and capture, while the shared collector owns batching, parsing, validation, output retries and provenance.
Malformed batch output can split into smaller retries; launch/nonzero invocation failures do not recursively split.

The model returns findings and evidence, not scores or trusted provenance.
The collector stamps captured source hash, prompt version, configured model identity, runner identity, run ID and cache key.
A configured identity is not a verified served-model receipt; use `unknown` for Auto or otherwise unidentifiable models.
Unknown identity permits same-run recovery and disables cross-run cache reuse.
Known identity and runner configuration must match before reuse.

`--limit` intentionally reviews only part of the selected scope.
Composition still includes every selected note and reports the rest as pending.
The collector writes a sibling `judgments.status.json`; composition reads it automatically to distinguish failed, unavailable and stale work.
After interruption, run composition and report generation to expose accepted results and incomplete coverage.
Refresh inventory when source content changes; compatible completed judgments can be reused while changed notes are reviewed again.
Never label unreviewed notes clean or use their score in a quality average.

## One plain Markdown report

Lead with recommendations and concise coverage, followed by one table. Use conceptual
groups with priority secondary, following the audit skill and audit review record;
the generator supplies initial priority order until groups are selected.
Its columns are `#`, `Priority`, `Note`, `Recommendation`, and `Action taken`.
Show each affected note once and retain every substantive action. Keep exact checks,
quality suggestions, unverified fact-checks, and Anki status distinguishable.
Unchanged notes are an aggregate count.

Read the package's `references/audit-review-record.md` before publication or later
selected-item processing. It owns the report's stable IDs, visible decision history,
minimal hidden identification markers, external draft commands, and guarded app write.
The report's Markdown is authoritative. A legacy manifest decision retains its original
provenance; missing dates or verification do not establish a new completion.
An optional Base remains a derived view and is not a second default report.

## Versions and historical compatibility

Current contracts are inventory 1.0.0, audit row/manifest 2.0.0, stored model judgment 3.0.0 and prompt 2.0.0.
The existing doctrine and loss table remain unchanged.
The historical deterministic engine, `--audit-jsonl` compatibility entry points and v1/v2 schemas remain available for old artifacts and callers.
They are outside the new default workflow and do not justify a new baseline report.
The `--inventory-jsonl` path rejects scored baseline input with an actionable diagnostic.
Do not rewrite or delete previous audits.
