# Networked Thinking Skills

[![CI](https://github.com/jrgilbertson/networked-thinking-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/jrgilbertson/networked-thinking-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

Agent Skills and deterministic helper scripts for creating, auditing, and improving Networked Thinking atomic notes in Obsidian vaults.

## What this is

Networked Thinking is a practical system for turning saved articles, highlights, and notes into usable context for writing, decisions, and work. This repo ships the agent-side tooling for the system described in the forthcoming book by Jason Gilbertson and Terri Yeh. The `atomic-note` skill creates and improves single-concept notes in DAE format, and `atomic-note-audit` scores existing notes against the system's rubric with deterministic checks before any agent judgment. The [companion vault](https://github.com/jrgilbertson/networked-thinking) shows the full system these skills operate on. Learn more and join the waitlist at [networkedthinking.ai](https://networkedthinking.ai/).

## Quickstart

Install both skills into Claude Code:

```bash
npx skills add jrgilbertson/networked-thinking-skills --agent claude-code -g --skill '*' --copy -y
```

Swap `--agent codex` for Codex. Remediation workflows also require the official Obsidian skills (`obsidian-cli`, `obsidian-markdown`, `obsidian-bases`); install those first. [docs/install.md](docs/install.md) covers per-skill installs and sandboxed-agent caveats.

## Usage

In an agent session opened on your vault, run a read-only audit first, then create or improve notes:

```text
Use atomic-note-audit to audit the quality of my atomic notes.
Use atomic-note to turn this highlight into an atomic note.
```

Always run the audit before remediation and review the generated plan before allowing vault mutation. Remediation can edit, split, relink, or delete vault files. The deeper guides cover the [audit workflow](docs/audit-workflow.md), the [remediation runbook](docs/remediation.md), and the [scoring rubric](docs/rubric.md).

## Contributing

Issues and PRs are welcome. Read the [contributor guide](docs/contributor-guide.md) first; questions go to the [issue tracker](https://github.com/jrgilbertson/networked-thinking-skills/issues).

## License

MIT. See [LICENSE](LICENSE).
