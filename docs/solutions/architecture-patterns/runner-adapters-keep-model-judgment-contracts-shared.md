---
title: Runner Adapters Keep Model Judgment Collection Contracts Shared
date: 2026-07-06
category: docs/solutions/architecture-patterns
module: networked-thinking atomic-note audit
problem_type: architecture_pattern
component: tooling
severity: medium
applies_when:
  - "Adding model judgment runner support"
  - "Separating local agent invocation from shared audit collection"
  - "Syncing generated skill-local runtime scripts"
tags: [runner-adapters, model-judgment, artifact-sync, cli-contracts, raw-dir]
---

# Runner Adapters Keep Model Judgment Collection Contracts Shared

## Context

Model judgment collection used to look like a Codex-specific workflow even though
the durable audit contract is runner-independent: deterministic audit rows feed a
model prompt, model judgments are validated, and downstream apply/report/Base
tools consume the same JSONL.

Issue #1 required runner selection as the user-facing abstraction without making
Codex the conceptual default. The implementation needed to support a Codex
adapter and a generic command adapter while preserving batching, resumability,
validation, split-and-retry, raw logs, generated skill artifacts, and downstream
JSONL contracts.

## Guidance

Keep the collector contract above runner-specific code. The shared collector
should own audit-row loading, batch construction, prompt rendering, resumability,
model-output parsing, schema validation, append-only JSONL output, and
split-and-retry for model drift. A runner adapter should own only local command
mechanics: how the prompt is handed off, how the final response is captured, what
stdout/stderr logs are written, and which adapter-specific safety flags apply.

Use a narrow runner protocol instead of branching inside the collection loop:

```python
class AgentRunner(Protocol):
    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        pass
```

That shape lets tests inject fake runners and lets new adapters prove their
behavior without changing downstream contracts. The adapter factory belongs at
the CLI boundary, before `collect_model_judgments()` enters shared batching.

Separate invocation failures from model-output drift. Validation errors,
malformed JSONL, mismatched note paths, and incomplete model judgments remain
retryable because splitting the batch can recover useful model output. Local
runner launch failures, nonzero command exits, and invalid command templates
should surface as invocation failures without recursive batch splitting.

Keep adapter-specific options local to the selected adapter in both directions.
Codex flags such as model, sandbox, binary path, and user-config loading should
not be accepted on a generic command runner path, and command templates should
not be accepted on the Codex runner path. This prevents a runner-first CLI from
becoming a Codex-shaped command with a non-Codex escape hatch or silently
ignoring a local command the operator meant to run.

Be explicit about filesystem coordinates across process boundaries. The generic
command runner executes with the vault as its working directory so local agents
see the same note workspace they are judging. Any collector-managed paths passed
to the command, such as `{output_path}`, `{stdout_path}`, and `{stderr_path}`,
must therefore be absolute or otherwise independent of that changed working
directory.

When changing generated runtime scripts, edit the canonical `shared/` source
first and then sync the installable skill copy. The checked-in script under
`skills/atomic-note-audit/scripts/` is a generated skill artifact, not the edit
authority.

## Why This Matters

Runner adapters are a portability boundary, not a second audit pipeline. If
batching, validation, retries, or JSONL writing leak into adapters, every new
agent CLI becomes a parallel implementation with its own failure semantics.
Downstream tools would then need to care which runner produced the judgments,
which defeats the purpose of runner selection.

The filesystem boundary is easy to miss because tests often use absolute temp
paths. A relative `--raw-dir` combined with a runner process that changes `cwd`
can send `{output_path}` into the vault or make a command fail even though the
collector created the intended raw directory elsewhere. Resolving collector-owned
raw paths before invoking the runner keeps logs and final responses in the same
place the collector manages.

The generated artifact rule matters for user trust. The installable audit skill
must carry the same runtime behavior as the shared source, but direct edits to
the skill-local copy will either be overwritten by sync or leave the repo in an
artifact-drift state.

## When to Apply

- When adding a new model judgment runner or local agent CLI adapter.
- When changing prompt handoff, final-response capture, raw logs, or runner
  safety flags.
- When changing retry behavior around malformed model output or local command
  failures.
- When editing generated skill-local runtime scripts under `skills/`.

## Examples

Resolve collector-owned raw paths before the adapter receives them:

```python
def collect_model_judgments(..., raw_dir: Path, runner: AgentRunner) -> int:
    vault_root = vault_root.resolve()
    raw_dir = raw_dir.resolve()
    ...
```

Then let the command runner execute in the vault while still receiving stable
absolute response/log paths:

```python
result = subprocess.run(
    command,
    input=prompt,
    text=True,
    capture_output=True,
    timeout=self.timeout_seconds,
    cwd=self.vault_root,
)
```

Keep the command-runner contract small and documented. The prompt goes to stdin.
The final response is either stdout or the file path supplied as `{output_path}`.
If a command template needs literal braces, operators escape them as doubled
braces; if it includes path placeholders, docs should show those placeholders
quoted because raw directories may contain spaces.

Reject ambiguous adapter configuration before invocation. A supplied
`--command` without `--runner command` should fail at the CLI boundary instead
of falling back to the Codex compatibility path. Malformed templates should also
collapse into one invocation-failure contract: catch missing names, positional
placeholders, attribute placeholders, and format syntax errors before the runner
starts, then report an invalid command template without batch splitting.

Tests should cover both adapter dispatch and shared collector behavior:

```python
runner = CommandRunner(
    vault_root=FIXTURE_VAULT,
    command_template=command,
    timeout_seconds=10,
)

count = collect_model_judgments(
    vault_root=FIXTURE_VAULT,
    audit_jsonl=AUDIT_JSONL,
    output_jsonl=output,
    raw_dir=Path("relative-raw"),
    max_notes=1,
    max_chars=100_000,
    limit=1,
    runner=runner,
)
```

That kind of test catches the composition bug where relative raw paths behave
differently once the adapter process runs from the vault.

## Related

- GitHub issue #1: `https://github.com/jrgilbertson/networked-thinking-skills/issues/1`
- Plan: `docs/plans/2026-07-06-001-feat-runner-adapters-model-judgment-collection-plan.md`
- Existing convention: `docs/solutions/conventions/plain-prose-dae-contract-migration.md`
