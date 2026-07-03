# AGENTS.md

This is the canonical project instruction file. Codex reads `AGENTS.md`
natively; Claude Code reads it through the `CLAUDE.md` import shim. Do not
duplicate these instructions in `CLAUDE.md`.

## Project Context

This repo packages agent skills and deterministic Python helpers for Networked
Thinking atomic notes in Obsidian vaults.

- Start with read-only audit workflows before remediation.
- Treat remediation as potentially destructive: it can edit, split, relink,
  move, or delete vault files.
- Use Obsidian-aware tooling for vault mutations. Do not fall back to raw
  filesystem writes for app-context operations.

## Source Of Truth

- `shared/` is the canonical development source for generated runtime
  references, schemas, and helper scripts.
- `skills/atomic-note` and `skills/atomic-note-audit` are checked-in,
  self-contained installable skill directories.
- When changing generated skill-local references, schemas, or scripts, edit the
  corresponding file under `shared/` first, then run:

```bash
python3 -m shared.scripts.sync_skill_artifacts
```

- Verify generated artifacts are in sync before finishing:

```bash
python3 -m shared.scripts.sync_skill_artifacts --check
```

## Privacy And Fixtures

- Never commit real Obsidian vault notes, names, highlights, meeting notes,
  attachments, or private user material.
- Tests, examples, docs, prompts, thresholds, and golden outputs must use
  synthetic reusable fixtures only.
- Use `shared.scripts.make_fixture_vault` and `tests/fixtures/tiny-vault` for
  examples.
- Keep golden outputs under `tests/golden` deterministic and reproducible.

## Development Checks

Run the pre-commit check before finishing a change:

```bash
lefthook run pre-commit --force --no-auto-install
```

The hook currently runs:

```bash
env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
python3 -m shared.scripts.validate_jsonl tests/golden/fixture-audit.jsonl
python3 -m shared.scripts.verify_install_commands docs/install.md
python3 -m shared.scripts.sync_skill_artifacts --check
```

For focused work, run the relevant command directly, then run the full
pre-commit check before handoff.

## Documentation And Contracts

- Update docs when behavior, schemas, prompts, install paths, or user workflows
  change.
- Use SemVer for package and contract versions.
- Treat package, schema, doctrine, rubric, and prompt versions as separate
  contracts; bump only the contract that actually changed and document why.

## Tooling Notes

- Prefer `rg`/`rg --files` for searching.
- Stage only intentional files. Ignore local caches such as `__pycache__`.
- `uv.lock` is ignored intentionally: repo validation uses the documented
  `python3`/`lefthook` commands, and `uv run` may create a local project
  lockfile when used ad hoc.
- Keep changes small and preserve deterministic outputs.

<!-- BEGIN COMPOUND CODEX TOOL MAP -->
## Compound Codex Tool Mapping (Claude Compatibility)

This section maps Claude Code plugin tool references to Codex behavior.
Only this block is managed automatically.

Tool mapping:
- Read: use shell reads (cat/sed) or rg
- Write: create files via shell redirection or apply_patch
- Edit/MultiEdit: use apply_patch
- Bash: use shell_command
- Grep: use rg (fallback: grep)
- Glob: use rg --files or find
- LS: use ls via shell_command
- WebFetch/WebSearch: use curl or Context7 for library docs
- AskUserQuestion/Question: present choices as a numbered list in chat and wait for a reply number. For multi-select (multiSelect: true), accept comma-separated numbers. Never skip or auto-configure — always wait for the user's response before proceeding.
- Task (subagent dispatch) / Subagent / Parallel: run sequentially in main thread; use multi_tool_use.parallel for tool calls
- TaskCreate/TaskUpdate/TaskList/TaskGet/TaskStop/TaskOutput (Claude Code task-tracking, current): use update_plan (Codex's task-tracking primitive)
- TodoWrite/TodoRead (Claude Code task-tracking, legacy — deprecated, replaced by Task* tools): use update_plan
- Skill: open the referenced SKILL.md and follow it
- ExitPlanMode: ignore
<!-- END COMPOUND CODEX TOOL MAP -->
