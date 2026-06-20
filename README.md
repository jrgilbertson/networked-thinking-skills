# Networked Thinking Skills

Agent Skills and deterministic helper scripts for creating, auditing, and improving Networked Thinking atomic notes in Obsidian vaults.

Start with a read-only audit before running remediation workflows. Remediation workflows can edit, split, relink, or delete vault files and require Obsidian-aware tooling.

## Quickstart

- Install the official Obsidian skills before remediation so `obsidian-cli`, `obsidian-markdown`, and `obsidian-bases` are available.
- Install `atomic-note` and `atomic-note-audit` with `npx skills add`; see [docs/install.md](docs/install.md).
- Installed skills include their runtime references and helper scripts. Run helper commands from the installed skill root when a skill instructs you to do so.
- In sandboxed agents such as Codex CLI, rerun Obsidian app-context CLI commands in an approved unsandboxed context when the CLI cannot attach to the running app.
- Run audit workflows before remediation, then review the generated plan before allowing vault mutation.
