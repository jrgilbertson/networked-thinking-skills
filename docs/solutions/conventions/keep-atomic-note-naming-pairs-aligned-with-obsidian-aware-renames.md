---
title: Keep atomic-note naming pairs aligned with Obsidian-aware renames
date: 2026-07-15
category: conventions
module: networked-thinking atomic-note authoring
problem_type: convention
component: assistant
severity: medium
applies_when:
  - Creating a Networked Thinking atomic note
  - Improving an existing note's Definition first sentence
  - Reconciling an atomic-note filename with visible Definition wording
  - Renaming a linked note inside an Obsidian vault
related_components:
  - documentation
  - development_workflow
  - tooling
tags:
  - atomic-notes
  - filename-alignment
  - definition
  - yaml-title
  - obsidian-cli
  - link-preservation
  - rename-approval
---

# Keep atomic-note naming pairs aligned with Obsidian-aware renames

## Context

Atomic-note naming uses two independent relationships that are easy to collapse
into one. A note's timestamped filename identifies the Definition sentence,
while its YAML `title` and H1 identify the concept with a short name. Treating
all four values as one title either makes the concept label unnecessarily long
or allows the filename to become stale when the Definition is improved.

The durable contract is therefore two separate matching pairs. The doctrine
states that the filename uses the reader-visible wording of the Definition's
first sentence without its final period, while YAML `title` and H1 share a
short concept name that does not have to repeat that sentence
(`shared/references/doctrine.md:51`). The authoring workflow checks the same two
pairs before and after a write (`skills/atomic-note/SKILL.md:31`).

This naming rule also creates a safety problem: changing the first Definition
sentence can require renaming a file that other notes link to. The solution must
preserve Obsidian's link-maintenance behavior and the learner's approval
boundary, not merely make the file contents internally consistent.

## Guidance

Treat the two relationships as independent invariants:

1. **Filename and first Definition sentence.** Remove the leading vault
   timestamp, the `.md` extension, Markdown wrappers, and the Definition
   sentence's final period for comparison. Preserve every other reader-visible
   word, capitalization choice, punctuation mark, and word-order choice exactly
   (`shared/references/doctrine.md:53`).
2. **YAML `title` and H1.** Use the same short concept name in both places. It
   is intentionally allowed to differ from the full first Definition sentence
   (`shared/references/doctrine.md:63`).

Validate the derived Definition text as a single filename component for the
target vault and platform before writing. If the sentence contains an invalid
filename character, redraft the sentence with the learner so the sentence and
filename remain exact matches. Do not silently delete or replace the character
(`shared/references/doctrine.md:59`).

When an existing comparison finds a stale filename, route it through the rename
workflow even if the requested content improvement leaves the Definition's
first sentence unchanged. When an improvement changes that sentence, treat the
content edit and rename as one approved operation:

- Derive the new filename, validate it, and preview the content and filename
  changes together (`shared/references/remediation-context.md:43`).
- Obtain explicit rename approval before applying either change. If approval is
  denied, retain the original first sentence or redraft without changing it;
  never write the new sentence by itself and leave a stale filename
  (`shared/references/remediation-context.md:48`).
- If a stale-only rename is denied, leave the filename unchanged and report the
  remaining mismatch rather than silently treating the note as aligned.
- Confirm under Obsidian's **Files and links** settings that **Automatically
  update internal links** is enabled. Inspect it through available Obsidian app
  context; if the interface cannot expose it, have the learner inspect the
  setting and explicitly confirm its state. Stop when it is disabled
  (`shared/references/remediation-context.md:52`).
- Record representative links or backlinks before mutation, then perform the
  filename change only with the official Obsidian CLI `rename` or `move`
  command through the verified CLI resolver. Never rename the file through the
  raw filesystem (`shared/references/remediation-context.md:56`).
- After mutation, verify both naming pairs, the final path, and the same links
  or backlinks captured before the rename. If the operation partially fails,
  restore the prior state with Obsidian-aware tooling or report the exact
  recovery state rather than claiming success
  (`shared/references/remediation-context.md:60`).

Maintain generated artifacts and version metadata as part of the same contract
change. Canonical generated sources live under `shared/`. The doctrine and
remediation references synchronize into both installable skill directories,
while audit-only scripts synchronize into `atomic-note-audit`
(`shared/scripts/sync_skill_artifacts.py:25`).
Because these rules change doctrine rather than schemas, scoring rubrics, or
prompts, advance only `doctrine_version` (`pyproject.toml:11`).

Use synthetic contract fixtures rather than private vault content. Test a
successful-rename contract scenario, a denied rename, and an invalid-filename
case. This is instruction-contract coverage, not an Obsidian integration test.
Derive filename text from the actual path and compare it with the actual
Definition sentence so the fixture cannot pass by repeating the same expected
value on both sides (`tests/test_atomic_note_skill_examples.py:15`).

## Why This Matters

The distinction preserves both readability and addressability. A short YAML
title and H1 make the concept easy to scan, while a filename copied from the
Definition sentence makes the note's claim visible in links and file
navigation. Requiring all four fields to match would discard that useful
distinction; checking only one pair would allow metadata or filenames to drift.

The Obsidian-aware rename protocol protects the surrounding note network.
Official Obsidian CLI `rename` and `move` commands update internal links when
the vault setting is enabled. Raw filesystem renames are outside that documented
workflow and are forbidden by this project's mutation contract. Capturing links
before the mutation and checking the same links afterward verifies the intended
graph behavior instead of assuming it.

The approval rule prevents partial state. If a learner declines a rename,
applying the new sentence alone would immediately violate the filename
contract. Coupling the two changes means the note stays aligned whether the
proposal is accepted or rejected.

Shared-source synchronization and contract-specific versioning keep installed
skills and audit output explainable. Without synchronized generated copies, the
repository could document one rule while installed skills teach another.

## When to Apply

- When creating an atomic note with a timestamp-prefixed filename.
- When improving a note changes, or may change, the first Definition sentence.
- When an existing note already has a stale filename, even if the requested
  content improvement does not change the first Definition sentence.
- When checking YAML `title`, H1, filename, and Definition text for alignment.
- When a proposed Definition sentence may contain invalid filename characters.
- When doctrine or remediation guidance under `shared/` changes and generated
  installable skill artifacts must be regenerated.

This is the creation and improve-in-place contract for keeping one note aligned
safely. It is not a bulk vault-remediation algorithm or a deterministic semantic
detector.

## Examples

An aligned note can use a concise concept name without copying the full
Definition into the title:

```text
Path:       Atomic Notes/202607151230 Deliberate practice improves performance through focused repetition and timely feedback.md
YAML title: Deliberate Practice
H1:         Deliberate Practice
Definition: Deliberate practice improves performance through focused repetition and timely feedback.
```

If the learner rejects the corresponding rename, keep the prior aligned
sentence and path:

```text
Keep path:       Atomic Notes/202607151230 Focused repetition builds durable skill.md
Keep Definition: Focused repetition builds durable skill.
Reject proposed: Deliberate practice improves performance through focused repetition and timely feedback.
```

For invalid filename characters, do not make an invisible substitution:

```text
Draft sentence:     Deliberate practice uses feedback/error cycles to improve a specific skill.
Forbidden filename: Deliberate practice uses feedback-error cycles to improve a specific skill
Required action:    Redraft the first sentence with the learner.
```

## Related

- [Issue #28](https://github.com/jrgilbertson/networked-thinking-skills/issues/28)
- [Official Obsidian CLI documentation](https://obsidian.md/help/cli)
- [Doctrine contract migration and generated-artifact precedent](plain-prose-dae-contract-migration.md)
- [Broader deferred audit and regression work](https://github.com/jrgilbertson/networked-thinking-skills/issues/20)
- [Earlier proposition-style alignment framing](https://github.com/jrgilbertson/networked-thinking-skills/issues/9)
