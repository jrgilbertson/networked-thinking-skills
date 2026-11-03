# Contributor Guide

Keep changes small, verified, and synthetic. Never commit real vault notes or
private user material. Tests, examples, and golden outputs must use synthetic
fixtures only.

## Development Loop

- Run tests before and after behavior changes.
- Update docs when behavior, schemas, prompts, or install paths change.
- Keep generated fixture outputs deterministic when they are committed.
- Stage only intentional files. Ignore local caches such as `__pycache__`.
- `uv.lock` is ignored intentionally. Use the documented `lefthook`/`python3`
  checks as the repo validation contract; ad hoc `uv run` commands may create
  a local lockfile.

## Required Checks

```bash
lefthook run pre-commit --force --no-auto-install
```

Run any added doc-specific tests with the same change.

## Regression Checks

Start from an observed failure. Fix it at the appropriate layer, then choose
the cheapest reliable regression check. A skill change does not require a
behavioral eval by default. Tests and lint rules can check objective conditions;
hooks run or enforce checks.

Behavioral evals measure model-driven behavior and can use code assertions,
human review, or LLM judges. Use Promptfoo for repeatable model runs and reuse
deterministic helpers for grading. Add human judgment where code cannot reliably
grade the result, and validate any LLM judge against human labels before
trusting it. Preserve the actual inputs, outputs, and grading evidence so a
result can be inspected and reproduced. See
[Hamel's evals FAQ](https://hamel.dev/blog/posts/evals-faq/).

Evals and batch model runs require approval under AGENTS.md. Automated tests
mock model calls. The vault-audit judgment collector is runtime functionality,
separate from the behavioral eval harness.

## Versioning

Use SemVer for package and contract versions. Treat these as separate contracts:

- Package version: release and install compatibility.
- Schema version: JSON input and output shape.
- Doctrine version: Networked Thinking note rules.
- Rubric version: finding-code loss table, bucket bands, and clean-note rules.
- Prompt version: model-judgment instructions and expected response contract.

Do not reuse one version bump to imply all contracts changed. Bump only the
contract that changed, and document why.

## Privacy

- Do not add real Obsidian vault notes, names, highlights, meeting notes, or
  attachments.
- Do not paste private note content into tests, fixtures, issue examples, or
  docs.
- Private vault audits may inform calibration, but public tests, fixtures,
  docs, rubrics, prompts, thresholds, and examples must remain reusable and
  synthetic rather than personalized to one vault.
- Use `shared.scripts.make_fixture_vault` and `tests/fixtures/tiny-vault` for
  examples.
- Keep golden outputs under `tests/golden` synthetic and reproducible.
