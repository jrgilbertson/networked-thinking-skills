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

## Audit report dependencies

The installed audit package includes its report parser, generator, outcome recorder,
and publisher. Python 3.11+ runs the helpers without third-party Python packages.
Semantic review uses the selected local runner and its existing authentication.
Live publication requires the running Obsidian app and a verified official CLI on
the same host, with access to the caller's temporary payload file. The app reads
that external payload, then writes the report only through vault APIs. AnkiConnect
is required only for requested Anki checks. None of these dependencies is a new
model service or a credential embedded in the package.
