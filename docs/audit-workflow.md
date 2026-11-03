# Audit workflow

A new audit is model-led and produces one plain Markdown `Audit.md`.
The report leads with a recommendation, then coverage and P0-P3 action buckets.
It lists each affected note once with a usable link, action and short reason.
Unchanged notes are counted rather than listed.

## Read-only sequence

1. Select the vault and note scope; resolve the model provider-sharing boundary before exporting private content.
2. Capture unscored inventory and exact metadata, marker, literal, link and optional read-only Anki evidence.
3. Collect model judgments for every selected note using an existing authenticated runner.
4. Compose accepted judgments with exact evidence and explicit unfinished states.
5. Validate the matching JSONL/manifest and publish the single report.

The installed [model judgment workflow](../shared/references/model-judgment-workflow.md) gives commands, runner options, resume rules and snapshot handling.
A normal run needs no deterministic semantic scoring pass.
Use `--inventory-jsonl` for current collection/composition.
The historical `audit_notes` and `--audit-jsonl` interfaces remain compatibility tools.

## Evidence and coverage

Keep inventory, judgments, results, manifest and private raw logs outside the vault by default.
If the user explicitly requests in-vault evidence, put JSONL and the manifest in one `Evidence/` directory; keep raw prompts/logs external unless separately requested.
Publish only `Audit.md` into the requested run folder.
For in-vault runs, use `YYYYMMDDHHMM` folder names under the configured audit output folder.
Generate a Base only on request.

Quality comes from validated model review.
Pending, failed, unavailable and stale notes have null quality values and are never clean.
Report both numerator and denominator; a limited pass is not exhaustive.
Exact-check and Anki coverage are separate.
An unavailable or omitted Anki check means not checked.
Pending fact-checks remain unverified even after model review.
The audit does not apply fixes or authorize remediation.

Honor vault-specific app tooling for all reads and writes.
For app-required vaults, use the included adapter callbacks or an app-exported, path-preserving snapshot refreshed before composition.
Do not silently substitute filesystem reads for required app access.

## Synthetic development verification

No provider call or private vault is needed for regression tests:

```bash
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_model_led_*.py'
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_audit_inventory.py
lefthook run pre-commit --force --no-auto-install
```

The installed-skill test copies only the packaged skill into a temporary directory, creates a synthetic vault, runs a fake local runner, composes and validates current results, and publishes one report.
Coverage includes full and partial review, interrupted/failed collection, malformed batch splitting, stale sources, cache invalidation, held decisions, exact Anki/link failures and optional Base behavior.
See [the synthetic Markdown report](../tests/golden/fixture-model-led-report.md) for the expected layout.
Historical fixture outputs remain under `tests/golden/fixture-audit*` to prove old readers still work.

## Remediation

Follow [remediation.md](remediation.md) after reviewing the report.
A model recommendation is never proof that a fix was applied.
Preserve previous audits unless the user explicitly requests a change.
Do not migrate or clean them up as a side effect of adopting the current workflow.
