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

## Self-contained skill installs

Published skill directories must include every runtime reference, schema, and
helper script they need under the skill root.

Runtime installs copy `skills/<skill>` into `<runtime-home>/skills/<skill>`.
No separate `<runtime-home>/shared` copy step is required.
