# Install

Run read-only audits before remediation. Remediation can edit, split, relink, or delete vault files, and it requires Obsidian-aware tooling.

This repo packages two skills:

- `skills/atomic-note`
- `skills/atomic-note-audit`

Each published skill directory is self-contained. `npx skills add` copies the selected skill directory, including skill-local references, schemas, and helper scripts. No separate `shared/` copy step is required.

## Prerequisite: Official Obsidian Skills

Install the official Obsidian skills before running remediation. Remediation hard-fails without `obsidian-cli`, `obsidian-markdown`, and `obsidian-bases`.

For app-context file operations, verify the actual Obsidian CLI executable. On
current macOS installs this is often `obsidian-cli`; `obsidian` may launch the
GUI binary instead of the CLI. See [remediation.md](remediation.md) for the
preflight command and destructive-operation runbook. In Codex CLI, Obsidian
CLI commands may also need approved unsandboxed execution because the CLI talks
to the running app through a local Unix socket. Installed skills include
`python3 scripts/obsidian_cli.py` as the preferred wrapper for app-context
commands; run it from the installed skill root.

### Codex

Source: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)

<!-- install-command
runtime: codex-official-obsidian-skills
status: verified-local
source: https://github.com/kepano/obsidian-skills
last_verified: 2026-06-06
execution: temp HOME install with npx skills
-->
```bash
npx skills add https://github.com/kepano/obsidian-skills --agent codex -g --copy -y
```

### Claude Code

Source: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills)

<!-- install-command
runtime: claude-official-obsidian-skills
status: verified-local
source: https://github.com/kepano/obsidian-skills
last_verified: 2026-06-06
execution: temp HOME install with npx skills
-->
```bash
npx skills add https://github.com/kepano/obsidian-skills --agent claude-code -g --copy -y
```

## Primary Raw Installs

Use these commands from a clone of this repo. Each copied skill directory includes its runtime references, schemas, and helper scripts.

### Codex Raw Skills

Codex user skills live under `$HOME/.agents/skills`. See the official Codex skills docs: <https://developers.openai.com/codex/skills>.

<!-- install-command
runtime: codex-raw-skills
status: verified-local
source: https://developers.openai.com/codex/skills
last_verified: 2026-06-20
execution: temp HOME raw copy with self-contained skill directories
-->
```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.agents/skills/"
```

### Claude Code Raw Skills

Claude Code personal skills live under `~/.claude/skills/<skill-name>/SKILL.md`. See the official Claude skills docs: <https://code.claude.com/docs/en/skills>.

<!-- install-command
runtime: claude-raw-skills
status: verified-local
source: https://code.claude.com/docs/en/skills
last_verified: 2026-06-20
execution: temp HOME raw copy with self-contained skill directories
-->
```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.claude/skills/"
```

## `npx skills` From This Clone

`npx skills` can copy selected self-contained skills from the cloned repo root.

### Codex

Source: [`skills` CLI docs](https://skills.sh/docs/cli)

<!-- install-command
runtime: codex-npx-local-clone
status: verified-local
source: https://skills.sh/docs/cli
last_verified: 2026-06-20
execution: clean temp HOME local repo root npx install with self-contained skill artifacts
-->
```bash
npx skills add . --agent codex -g --skill atomic-note --skill atomic-note-audit --copy -y
```

### Claude Code

Source: [`skills` CLI docs](https://skills.sh/docs/cli)

<!-- install-command
runtime: claude-npx-local-clone
status: verified-local
source: https://skills.sh/docs/cli
last_verified: 2026-06-20
execution: clean temp HOME local repo root npx install with self-contained skill artifacts
-->
```bash
npx skills add . --agent claude-code -g --skill atomic-note --skill atomic-note-audit --copy -y
```

## Public GitHub Installs

After these self-contained skill manifests are merged to `main`, these are the
public install forms users can run without cloning the repo first:

```bash
npx skills add jrgilbertson/networked-thinking-skills --list
```

```bash
npx skills add jrgilbertson/networked-thinking-skills --agent codex -g --skill '*' --copy -y
```

```bash
npx skills add jrgilbertson/networked-thinking-skills --agent codex -g --skill atomic-note --copy -y
```

```bash
npx skills add https://github.com/jrgilbertson/networked-thinking-skills --list
```

```bash
npx skills add https://github.com/jrgilbertson/networked-thinking-skills/tree/main/skills/atomic-note --list
```

## Plugin Marketplace Installs

This repo is not published to a Codex or Claude plugin marketplace yet. Use the raw copy commands above until a marketplace entry exists.

### Codex Plugin

Codex CLI exposes `codex plugin add`, not the stale `codex plugin install` form. Codex plugin distribution uses marketplaces. See <https://developers.openai.com/codex/plugins/build>.

<!-- install-command
runtime: codex-plugin-marketplace
status: blocked-with-reason
source: https://developers.openai.com/codex/plugins/build
last_verified: 2026-06-06
execution: local codex plugin add help checked; command not run because package is unpublished
reason: no published Codex marketplace entry exists for networked-thinking-skills
-->
```bash
codex plugin add networked-thinking-skills@<marketplace>
```

### Claude Plugin

Claude plugin installation is available, but this package is not published through a Claude plugin source yet. See <https://code.claude.com/docs/en/plugins-reference>.

<!-- install-command
runtime: claude-plugin-marketplace
status: blocked-with-reason
source: https://code.claude.com/docs/en/plugins-reference
last_verified: 2026-06-06
execution: local claude plugin install help checked; command not run because package is unpublished
reason: no published Claude plugin source exists for networked-thinking-skills
-->
```bash
claude plugin install <published-plugin-source>
```

## Hermes

Hermes local skills live under `~/.hermes/skills`, and Hermes can also load external skill directories through `skills.external_dirs` in `~/.hermes/config.yaml`. See <https://hermes-agent.nousresearch.com/docs/user-guide/features/skills>.

Use the `.agents`-compatible copy below, then point Hermes at that skill directory. The command only copies files; it does not verify the Hermes CLI.

<!-- install-command
runtime: hermes-agents-external-dir-copy
status: verified-local
source: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
last_verified: 2026-06-20
execution: local file copy of self-contained skill directories only; Hermes CLI not installed or run
-->
```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.agents/skills/"
```

Add this to `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
```

## OpenClaw

OpenClaw public docs show `openclaw skills install <slug>` for published skills. This repo is not published to a ClawHub/OpenClaw channel, and `openclaw`/`claw` was not installed locally. Use the raw/manual copy fallback for a compatible runtime instead.

<!-- install-command
runtime: openclaw-marketplace
status: blocked-with-reason
source: https://docs.openclaw.ai/cli/skills
last_verified: 2026-06-06
execution: OpenClaw CLI not installed locally; command not run because package is unpublished
reason: no published ClawHub or OpenClaw channel entry exists for networked-thinking-skills
-->
```bash
openclaw skills install networked-thinking-skills
```
