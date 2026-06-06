# Install Matrix

Human instructions live in `docs/install.md`.

Exact install commands must be verified during implementation and tagged with command metadata in `docs/install.md`.

Supported surfaces:

- `npx skills`
- Claude Code
- Codex plugin
- Codex raw skills
- Hermes
- OpenClaw
- Manual Git clone or copy

## Raw Skill Installs

Codex raw skills, Claude Code raw skills, and manual copy installs must preserve the package layout expected by skill-relative reference paths:

- Copy `skills/<skill>` into `<runtime-home>/skills/<skill>`.
- Copy `shared/references` into `<runtime-home>/shared/references`.
