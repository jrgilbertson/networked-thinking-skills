# Contributor Guide

Keep changes small, verified, and synthetic. Never commit real vault notes or
private user material. Tests, examples, and golden outputs must use synthetic
fixtures only.

## Development Loop

- Run tests before and after behavior changes.
- Update docs when behavior, schemas, prompts, or install paths change.
- Keep generated fixture outputs deterministic when they are committed.
- Stage only intentional files. Ignore local caches such as `__pycache__`.

## Required Checks

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m shared.scripts.verify_install_commands docs/install.md
python3 -m shared.scripts.validate_jsonl tests/golden/fixture-audit.jsonl
```

Run any added doc-specific tests with the same change.

## Versioning

Use SemVer for package and contract versions. Treat these as separate contracts:

- Package version: release and install compatibility.
- Schema version: JSON input and output shape.
- Doctrine version: Networked Thinking note rules.
- Rubric version: scoring dimensions, weights, priorities, and clean-note rules.
- Prompt version: model-judgment instructions and expected response contract.

Do not reuse one version bump to imply all contracts changed. Bump only the
contract that changed, and document why.

## Privacy

- Do not add real Obsidian vault notes, names, highlights, meeting notes, or
  attachments.
- Do not paste private note content into tests, fixtures, issue examples, or
  docs.
- Use `shared.scripts.make_fixture_vault` and `tests/fixtures/tiny-vault` for
  examples.
- Keep golden outputs under `tests/golden` synthetic and reproducible.
