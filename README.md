# Networked Thinking Skills

Agent skills and deterministic helper scripts for creating, auditing, and improving [Networked Thinking](https://sustaining-ai.com/networked-thinking) atomic notes in Obsidian vaults.

## What This Ships

Two self-contained skills:

### [`atomic-note`](skills/atomic-note/)

Create or improve a single atomic note in DAE (Define, Apply, Extend) format. Handles note creation, editing, link resolution, and vault-aware file operations through Obsidian CLI.

### [`atomic-note-audit`](skills/atomic-note-audit/)

Audit every Markdown file in a configured Atomic Notes folder. Produces vault-health KPIs, scores notes against a rubric, and generates prioritized remediation queues. Run this before any remediation work.

## Install

### Prerequisites

Install the official Obsidian skills first — remediation hard-fails without them:

- [Codex](https://github.com/kepano/obsidian-skills)
- [Claude Code](https://github.com/kepano/obsidian-skills)
- [OpenCode](https://github.com/kepano/obsidian-skills)

See [docs/install.md](docs/install.md) for detailed instructions.

### Install the Skills

```bash
npx skills add atomic-note
npx skills add atomic-note-audit
```

Each skill is self-contained — `npx skills add` copies references, schemas, and helper scripts. No separate `shared/` step needed.

## Usage

### Audit First

Always run a read-only audit before making changes:

1. Load `atomic-note-audit` in your agent
2. Point it at your vault's Atomic Notes folder
3. Review the generated health report and remediation plan

### Then Improve

1. Load `atomic-note` in your agent
2. Create new notes or improve existing ones
3. The skill handles DAE formatting, link resolution, and vault-aware file ops

### Sandboxed Agents

In Codex CLI or similar sandboxed environments, Obsidian CLI commands may need approved unsandboxed execution because the CLI talks to the running app through a local Unix socket. Each skill includes `python3 scripts/obsidian_cli.py` as the preferred wrapper.

## Docs

- [Install guide](docs/install.md)
- [Audit workflow](docs/audit-workflow.md)
- [Remediation runbook](docs/remediation.md)
- [Rubric and scoring](docs/rubric.md)
- [Contributor guide](docs/contributor-guide.md)

## Contributing

See [docs/contributor-guide.md](docs/contributor-guide.md). Keep changes small, verified, and synthetic — never commit real vault notes or private material.

## License

See [LICENSE](LICENSE).
