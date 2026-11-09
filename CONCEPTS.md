# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or catch-all.

## Networked Thinking Notes

### Atomic Note
An individual Networked Thinking note that captures one durable concept in a self-contained form while staying connected to the surrounding note network.

### DAE
The required explanatory shape for an Atomic Note: Definition, Analogy, and Example content that can be read by a person and checked by deterministic audit rules.

Each DAE section is a sentence whose first visible letter is capitalized, including a leading wikilink alias. Mid-sentence aliases stay lowercase. A section that opens with inline math or inline code may keep that token first, a mixed-case first word such as gRPC stays as written, and a first word with no letter to capitalize, such as a numeral or a URL, is exempt.

### Non-Anki Atomic Note
An Atomic Note whose DAE content lives directly in visible note prose rather than inside an Anki card block.

### Anki-Backed Atomic Note
An Atomic Note that also includes Obsidian-to-Anki card content while preserving the same DAE concept contract.

### Atomic Note Filename
The canonical Networked Thinking filename uses a timestamp followed by the reader-visible applicable Definition source without its final period. Plain-prose DAE takes precedence over optional Anki card text. YAML `title` and H1 separately use the same short concept name.

### Structure Note
A hub note that organizes Atomic Notes into a findable topic or review area for learner-chosen conceptual navigation, factual recall, trivia review, or a mix.

Its breadth is intentional; DAE and one-concept rules apply to linked Atomic Notes, not the Structure Note itself.

## Audit And Skill Contracts

### Doctrine
The project-specific contract for valid Atomic Note shape, authoring rules, Anki handling, reference material, and deterministic audit expectations.

### Deterministic Audit
The historical non-model review path that evaluates Atomic Notes from structural and textual rules. It remains available for historical compatibility; it is not a prerequisite for a new model-led audit.

### Decayed LaTeX Command
A LaTeX command that reached the vault as the control character its escape sequence decodes to, such as `\times` stored as a tab followed by `imes`. The Obsidian CLI decodes `\t` and `\n` in its `content=` argument, so commands whose names start with `t` or `n` are the ones at risk. Deterministic audit reports these as `decayed_latex_command` and names the command it reconstructs, which is also the repair.

### Model Judgment Runner
A local agent invocation path for model judgment collection that executes the shared audit prompt and returns validated model judgment objects while the shared collector validates results against the applicable versioned contracts.

### Runner Adapter
The runner-specific boundary that owns prompt handoff, agent command invocation, final response capture, raw logs, and safety flags while leaving batching, parsing, validation, and retry behavior to the shared collector.

### Generated Skill Artifact
A checked-in installable skill copy of a canonical shared reference or helper that must stay synchronized with its shared source.

### Model-Led Audit
A quality review whose semantic findings come from model judgment, with exact integrity evidence kept distinct and presented in the same learner-facing report.

### Audit Inventory
An unscored capture of the selected notes, source hashes and exact-check evidence used to establish what a review covers.

### Review Coverage
The count of selected notes in each model-review state: reviewed, pending, failed, unavailable or stale. Coverage describes the selected scope rather than implying a whole-vault conclusion.

### Exact Integrity Check
A reproducible check of actual source structure, characters, link targets or Anki state. Its outcome does not substitute for semantic quality review.

### Quality-Clean Note
A model-reviewed note with no quality loss or pending fact check. An independent integrity failure can still require action.

### Audit Review Record
The single Markdown audit report that owns stable run-local item IDs, visible recommendations, and dated per-action decisions and verified outcomes. Temporary working data can be rebuilt from it. Minimal hidden markers identify actions and format; they do not duplicate recommendations or outcomes.

### Action Outcome
A recorded disposition for one recommendation: Pending, Held, Declined, Partial, or Completed. Prior work remains dated history; newly flagged work needs its own verification. Completion describes verified work rather than approval or a model suggestion.

### Concept Review Group
A set of related audit items reviewed together because their meanings, boundaries, or examples inform one another. Relationship determines group size; repair priority orders items within the group, while stable item numbers retain identity.
