# Networked Thinking Skills

Agent Skills and deterministic helper scripts for creating, auditing, and improving Networked Thinking atomic notes in Obsidian vaults.

Start with a read-only audit before running remediation workflows. Remediation workflows can edit, split, relink, or delete vault files and require Obsidian-aware tooling.

## Quickstart

- Install the official Obsidian skills before remediation so `obsidian-cli`, `obsidian-markdown`, and `obsidian-bases` are available.
- Verify app-context CLI commands use the actual Obsidian CLI executable. The default for this repo is `obsidian-cli`.
- Install `atomic-note` and `atomic-note-audit` with a verified raw or `npx skills` command from [docs/install.md](docs/install.md).
- Run audit workflows before remediation, then review the generated plan before allowing vault mutation.
