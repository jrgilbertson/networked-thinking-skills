---
title: Keep atomic-note naming pairs aligned with Obsidian-aware renames
date: 2026-07-15
last_updated: 2026-07-18
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
into one. In a proposition-style timestamp convention, the filename identifies
the Definition's proposition, while its YAML `title` and H1 identify the concept
with a short name. Treating all four values as one literal string makes the
concept label unnecessarily long; treating a timestamp alone as evidence of a
proposition convention can override the learner's local naming practice.

The durable contract is therefore two alignment relationships. A
proposition-style filename stem expresses the same single concept and
specificity as the applicable Definition source, while YAML `title` and H1
share a compatible short concept name. The authoring workflow establishes the
local convention before checking either relationship.

This naming rule also creates a safety problem: changing the first Definition
sentence can require renaming a file that other notes link to. The solution must
preserve Obsidian's link-maintenance behavior and the learner's approval
boundary, not merely make the file contents internally consistent.

## Guidance

First inspect the user template and nearby atomic notes in the same folder and
of the same note type. A template instruction or a consistent set of nearby
filename/Definition pairs is evidence of a proposition-style convention; a
timestamp prefix by itself is not. In a mixed vault, scope the decision to the
target folder, template, and note type. Preserve the local pattern when those
signals conflict or remain unclear.

Then treat the two relationships as independent invariants:

1. **Filename and Definition proposition.** For `Basic`, use the first
   definition sentence in `Back:`. For `Cloze`, use the cloze-bearing definition
   sentence. For non-Anki DAE, use the first visible Definition sentence after
   the H1, or under `## Definition` in a legacy headed note. The filename stem
   may use different wording, but it must express the same single concept at the
   same specificity rather than a broader, narrower, or different proposition.
2. **YAML `title` and H1.** Use the same short concept name in both places. It
   may differ from the proposition, but it must not contradict or broaden it.

Validate a proposed proposition stem as a single filename component for the
target vault and platform before writing. If it contains an invalid filename
character, redraft the filename and Definition wording with the learner while
preserving the same concept and specificity. Do not silently delete or replace
the character.

When an existing comparison finds semantic filename drift, route it through the
rename workflow even if the requested content improvement leaves the Definition
unchanged. When an improvement would introduce drift, treat the content edit
and rename as one approved operation:

- Derive the new filename, validate it, and preview the content and filename
  changes together (`shared/references/remediation-context.md:57`).
- Obtain explicit rename approval before applying either change. If approval is
  denied, retain the original Definition or redraft it to remain aligned; never
  write the new proposition by itself and leave a stale filename
  (`shared/references/remediation-context.md:63`).
- If a stale-only rename is denied, leave the filename unchanged and report the
  remaining mismatch rather than silently treating the note as aligned.
- Confirm under Obsidian's **Files and links** settings that **Automatically
  update internal links** is enabled. Inspect it through available Obsidian app
  context; if the interface cannot expose it, have the learner inspect the
  setting and explicitly confirm its state. Stop when it is disabled
  (`shared/references/remediation-context.md:68`).
- Record representative links or backlinks before mutation, then perform the
  filename change only with the official Obsidian CLI `rename` or `move`
  command through the verified CLI resolver. Never rename the file through the
  raw filesystem (`shared/references/remediation-context.md:74`).
- After mutation, verify both naming pairs, the final path, and the same links
  or backlinks captured before the rename. If the operation partially fails,
  restore the prior state with Obsidian-aware tooling or report the exact
  recovery state rather than claiming success
  (`shared/references/remediation-context.md:76`).

Maintain generated artifacts and version metadata as part of the same contract
change. Canonical generated sources live under `shared/`. The doctrine and
remediation references synchronize into both installable skill directories,
while audit-only scripts synchronize into `atomic-note-audit`
(`shared/scripts/sync_skill_artifacts.py:25`).
Because these rules change both doctrine and model-judgment instructions,
advance `doctrine_version` and `prompt_version`. The finding code and loss stay
the same, so schema and rubric versions remain unchanged (`pyproject.toml:11`).

Use synthetic contract fixtures rather than private vault content. Cover
`Basic`, `Cloze`, non-Anki DAE, mixed conventions, a successful rename, a denied
rename, and an invalid-filename case. This is instruction-contract coverage,
not a deterministic semantic detector or an Obsidian integration test.

## Why This Matters

The distinction preserves both readability and addressability. A short YAML
title and H1 make the concept easy to scan, while a proposition filename makes
the note's claim visible in links and file navigation. Requiring all four fields
to match literally would discard that useful distinction; checking only one
relationship would allow metadata or filenames to drift.

The Obsidian-aware rename protocol protects the surrounding note network.
Official Obsidian CLI `rename` and `move` commands update internal links when
the vault setting is enabled. Raw filesystem renames are outside that documented
workflow and are forbidden by this project's mutation contract. Capturing links
before the mutation and checking the same links afterward verifies the intended
graph behavior instead of assuming it.

The approval rule prevents partial state. If a learner declines a required
rename, applying a Definition change that introduces drift would immediately
violate the filename contract. Coupling those changes means the note stays
aligned whether the proposal is accepted or rejected.

Shared-source synchronization and contract-specific versioning keep installed
skills and audit output explainable. Without synchronized generated copies, the
repository could document one rule while installed skills teach another.

## When to Apply

- When local evidence establishes a proposition-style timestamp convention.
- When improving a note changes, or may change, its Definition proposition.
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
