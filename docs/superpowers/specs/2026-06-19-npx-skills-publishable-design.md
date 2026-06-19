# Make Skills Publishable Through `npx skills add`

Date: 2026-06-19
Issue: https://github.com/jrgilbertson/networked-thinking-skills/issues/3

## Goal

Make `atomic-note` and `atomic-note-audit` installable from this public GitHub
repo with `npx skills add` so each installed skill directory works without a
separate clone, repo-level `shared/` folder, or post-install copy step.

Success means:

- `npx skills add . --list` finds both skills.
- A clean Codex install with `npx skills add . --skill '*' --agent codex -g --copy -y`
  copies working skill directories into a temporary home.
- Installed skills contain no unresolved `../../shared`, `../shared`, or
  repo-level `shared/` references, including dotted Python imports such as
  `shared.scripts`.
- Helper entrypoints referenced by installed skills run from the installed
  skill layout.
- The supported GitHub source forms work: `owner/repo`, full GitHub URL, and
  direct `tree/main/skills/<skill>` URL.
- Repo tests pass after replacing old shared-layout assertions.
- README and install docs show working public install examples for all skills
  and one named skill.

## Current State

The repo currently keeps runtime support files under top-level `shared/`.
`skills/atomic-note/SKILL.md` references `../../shared/references/doctrine.md`,
`../../shared/references/remediation-context.md`, and mentions
`python3 -m shared.scripts.obsidian_cli`.

`skills/atomic-note-audit/SKILL.md` references five shared reference files,
multiple `shared/scripts/*` entrypoints, and `shared/schemas/*` schema paths.
The Python helper code is a package-like graph under `shared/scripts`; entrypoint
modules import other `shared.scripts` modules. Copying only top-level entrypoint
files would break imports.

Current install docs still describe plain `npx skills add .` as broken unless a
user also copies `shared/references`. Current integrity tests assert the old
contract by requiring shared references and proving skill-only installs fail.

## External Guidance

Current Agent Skills guidance treats a skill as a portable directory containing
`SKILL.md` plus optional `scripts/`, `references/`, `assets/`, and other local
files. File references should be relative to the skill root. Script guidance
says bundled scripts should be referenced from `SKILL.md`, avoid interactive
prompts, provide concise `--help`, print helpful errors, prefer structured
output, and document runtime prerequisites.

The current `skills` CLI supports the issue's install forms: local paths,
`owner/repo`, full GitHub URLs, direct GitHub tree URLs, `--skill '*'`,
`--list`, `--copy`, and global installs. Its copy installer recursively copies
the selected skill directory. Files outside `skills/<skill>/` are therefore not
part of a copied installed skill.

`vercel-labs/agent-skills` follows the same public catalog shape: skill
directories under `skills/`, support files inside those directories, and an
optional `skills.sh.json` for grouping/display rather than runtime dependency
resolution.

## Chosen Approach

Keep `shared/` as the development source of truth and generate checked-in,
self-contained publish artifacts inside each skill directory.

Generated artifacts must be committed because `npx skills add` does not run a
repo build or sync step before copying skill files. The generator makes the
installed layout portable while preserving one canonical development surface for
references, schemas, and Python helper code.

Target layout:

```text
skills/atomic-note/
  SKILL.md
  references/
  scripts/

skills/atomic-note-audit/
  SKILL.md
  references/
  schemas/
  scripts/
```

`atomic-note` gets only the support files its installed instructions actually
use. Because the current skill instructs repo-local agents to prefer the
Obsidian helper wrapper, the installed artifact includes the complete import
graph needed for `scripts/obsidian_cli.py`, not just the entrypoint file.

`atomic-note-audit` gets the complete helper graph needed by its audit,
validation, report, Base generation, model judgment, Obsidian preflight, Anki
verification, and remediation instructions.

## Generated File Rules

The generator owns skill-local runtime copies. It must:

- Copy required reference files from `shared/references/` into each skill's
  `references/` directory.
- Copy required schemas from `shared/schemas/` into skill-local `schemas/`.
- Copy the complete required Python helper graph into skill-local `scripts/`.
- Rewrite installed skill instructions to use paths relative to the skill root,
  such as `references/doctrine.md`, `scripts/audit_notes.py`, and
  `schemas/model-judgment.schema.json`.
- Rewrite or adapt helper imports so installed scripts run from the skill root
  without requiring `shared.scripts`.
- Rewrite or reject generated instructions, reference files, and scripts that
  contain stale repo-level `shared/` paths or dotted `shared.scripts` imports.
- Fail validation when generated artifacts drift from the canonical `shared/`
  sources.

Generated artifacts are intentionally duplicated. The duplication is acceptable
only because `shared/` remains canonical and tests enforce synchronization.

## Runtime Instructions

Installed skills should tell agents to run helper scripts from the skill root,
for example:

```bash
python3 scripts/audit_notes.py --vault /path/to/vault --run-id baseline-YYYYMMDDHHMM --jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json
```

The installed instructions should not use `python3 -m shared.scripts.*`.

Skill frontmatter or body text should document real runtime prerequisites:
Python 3.11+, local filesystem access, and workflow-specific tools such as
Obsidian CLI, Codex CLI, or Anki/AnkiConnect when those paths are used. The docs
should state prerequisites without turning public install into a repo-clone or
post-install copy process.

## Docs And Metadata

Update README and `docs/install.md` so the primary public install path uses
current `npx skills add` examples. Mention `install` only as an alias if it is
mentioned at all.

Docs must include:

- install all skills from this repo;
- install one named skill;
- list skills without installing;
- supported GitHub source forms;
- expected runtime prerequisites for helper-backed workflows.

Update `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` only where
their skill paths or repository metadata are stale. Add `skills.sh.json` only if
it improves public grouping/display; it must not be used to solve runtime file
dependencies.

## Tests And Verification

Replace old shared-layout assertions with self-contained-install assertions.
The updated tests should prove:

- required skill references resolve from each skill directory;
- generated artifacts are synchronized with canonical `shared/` files;
- skill-local references and scripts contain no unresolved repo-level
  `shared/` paths or dotted `shared.scripts` imports;
- copied skill-only layouts satisfy references and runnable helper entrypoints;
- the old requirement to copy `shared/references` beside installed skills is
  removed from docs and tests.

Final verification should include:

```bash
npx skills add . --list
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" npx skills add . --skill '*' --agent codex -g --copy -y
find "$TMP_HOME" -maxdepth 5 -type f | sort
! rg '\.\./\.\./shared|\.\./shared|shared/' "$TMP_HOME/.codex/skills"
! rg 'shared\.scripts|from shared|import shared' "$TMP_HOME/.codex/skills"
```

Run installed helper smoke checks from the copied layout, including
`atomic-note`'s Obsidian helper wrapper and the audit entrypoints referenced by
`atomic-note-audit`. Smoke checks for wrappers around optional external tools
should separate packaging from machine prerequisites: use `--help` or a fake
binary for layout/import checks, then reserve real Obsidian, Codex, or
Anki/AnkiConnect execution for environments where those tools are intentionally
available.

Verify public GitHub forms:

```bash
npx skills add jrgilbertson/networked-thinking-skills --list
npx skills add https://github.com/jrgilbertson/networked-thinking-skills --list
npx skills add https://github.com/jrgilbertson/networked-thinking-skills/tree/main/skills/atomic-note --list
```

For public source forms that point at the implementation ref under test, also
run copied clean-home installs and the same no-stale-shared validation. Before
the implementation reaches `main`, use the supported ref syntax or branch tree
URL for this verification; after merge, repeat the issue's `main` forms.

Run the repo test suite after updating the packaging assertions.

## Rejected Approaches

Moving all canonical runtime files into skill directories would produce the
cleanest installed layout, but it is a larger code move and makes shared helper
ownership between `atomic-note` and `atomic-note-audit` harder. It is not
necessary for issue #3 because generated checked-in artifacts satisfy the
single-source constraint.

Keeping `shared/` as an external install requirement is rejected. It violates
the issue, the user's clarified requirement, and the current `skills` CLI copy
behavior.

Relying on `skills.sh.json`, plugin manifests, zip files, or package-level
metadata to provide runtime files is rejected. Those surfaces are useful for
catalog display or plugin packaging, not for making `npx skills add --copy`
install a self-contained skill directory.

## Implementation Boundary

This design does not change the semantic behavior of `atomic-note` or
`atomic-note-audit`. It changes packaging, paths, helper entrypoint invocation,
docs, and validation so installed skills behave like the repo-local workflows.
