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

## Model-led audit contracts

Version 0.3.0 makes unscored inventory the default review input and publishes one recommendation-first Markdown report.
Package 0.4.0 adds report-only recovery, stable item/action identity, visible outcome history, and guarded direct-directory publication. The Markdown review format is 1.0.0; hidden data is limited to IDs and format information.
Current inventory is 1.0.0, result/manifest 2.0.0, stored judgment 3.0.0 and prompt 2.0.0.
Doctrine 1.0.8 and rubric 1.0.4 retain their existing note rules, finding losses and quality bands.
The historical engine keeps its original schema/prompt labels and compatibility entry points; do not relabel or rewrite stored audits.

Canonical runtime changes belong under `shared/`; update the sync manifest when adding files and regenerate the installable skill.
`test_model_led_install.py` executes the current CLI chain from a copied skill with no repository imports or real provider call.
`test_model_led_reporting.py` protects the plain Markdown hierarchy, links, coverage and small action queue against synthetic fixtures.
Use the generated `fixture-model-led-report.md` alongside historical fixtures, which continue to verify old readers.

## Portable audit package checks

Keep the skill entrypoint focused on the reusable job, with conditional details in
package-local references and no research appendix. Declare actual environment
dependencies, bundle required helpers, and preserve one owner for each rule.
Run `skills-ref validate skills/atomic-note-audit` from a trusted available install;
if unavailable, inspect frontmatter, name-directory match, local links, and declared
dependencies directly and report that limitation. Run copied helpers outside the
checkout against synthetic filesystem fixtures. Node runs the generated publisher
JavaScript against a simulated app; no app vault is created or opened by tests.
A simulated app pass is not an actual Obsidian-rendering check.
