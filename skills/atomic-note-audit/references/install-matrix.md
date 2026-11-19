# Install Matrix

## Self-contained skill installs

Published skill directories must include every runtime reference, schema, and
helper script they need under the skill root. Each installed skill is self-contained
under `<runtime-home>/skills/<skill>`.

## Audit report dependencies

The installed audit package includes its report parser, generator, outcome recorder,
and publisher. Python 3.11+ runs the helpers without third-party Python packages.
Semantic review uses the selected local runner and its existing authentication.
Live publication requires the running Obsidian app and a verified official CLI on
the same host, with access to the caller's temporary payload file. The app reads
that external payload, then writes the report only through vault APIs. AnkiConnect
is required only for requested Anki checks. None of these dependencies is a new
model service or a credential embedded in the package.
