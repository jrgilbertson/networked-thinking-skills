# Networked Thinking Skills

[![CI](https://github.com/jrgilbertson/networked-thinking-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/jrgilbertson/networked-thinking-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

Agent Skills and deterministic helper scripts for creating, auditing, and improving Networked Thinking atomic notes in Obsidian vaults.

## Purpose

Networked Thinking is a book and practical system for turning saved articles, highlights, and notes into usable context for writing, decisions, and work. This repo ships the agent-side tooling for the system, from the forthcoming book by Jason Gilbertson and Terri Yeh. The [companion vault](https://github.com/jrgilbertson/networked-thinking) shows the full system these skills operate on. Learn more and join the waitlist at [networkedthinking.ai](https://networkedthinking.ai/).

## Skills

| Skill | What it does |
|---|---|
| `atomic-note` | Create or improve a single-concept note in DAE format. |
| `atomic-note-audit` | Score existing notes against the system's rubric, deterministic checks first, agent judgment second. |

More skills will land here as the book's workflows do; each installs independently.

## Quickstart

Install every skill globally, symlinked into all of your agent harnesses from one location:

```bash
npx skills add jrgilbertson/networked-thinking-skills -g --agent '*'
```

Or install a single skill:

```bash
npx skills add jrgilbertson/networked-thinking-skills -g --skill atomic-note
```

Remediation workflows also require the official Obsidian skills (`obsidian-cli`, `obsidian-markdown`, `obsidian-bases`); install those first. [docs/install.md](docs/install.md) covers per-agent installs, copied (non-symlink) installs, and sandboxed-agent caveats.

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
