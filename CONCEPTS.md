# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or catch-all.

## Networked Thinking Notes

### Atomic Note
An individual Networked Thinking note that captures one durable concept in a self-contained form while staying connected to the surrounding note network.

### DAE
The required explanatory shape for an Atomic Note: Definition, Analogy, and Example content that can be read by a person and checked by deterministic audit rules.

### Non-Anki Atomic Note
An Atomic Note whose DAE content lives directly in visible note prose rather than inside an Anki card block.

### Anki-Backed Atomic Note
An Atomic Note that also includes Obsidian-to-Anki card content while preserving the same DAE concept contract.

### Proposition-Style Filename Convention
A locally established Atomic Note naming pattern in which a timestamp-prefixed filename stem expresses the Definition's single concept at the same specificity rather than serving only as a short topic label.

### Structure Note
A hub note that gives Atomic Notes a findable context by linking related concepts into a larger topic or review area.

## Audit And Skill Contracts

### Doctrine
The project-specific contract for valid Atomic Note shape, authoring rules, Anki handling, reference material, and deterministic audit expectations.

### Deterministic Audit
The non-model review path that evaluates Atomic Notes from structural and textual rules before any model judgment is involved.

### Model Judgment Runner
A local agent invocation path for model judgment collection that executes the shared audit prompt and returns validated model judgment objects without changing downstream JSONL contracts.

### Runner Adapter
The runner-specific boundary that owns prompt handoff, agent command invocation, final response capture, raw logs, and safety flags while leaving batching, parsing, validation, and retry behavior to the shared collector.

### Generated Skill Artifact
A checked-in installable skill copy of a canonical shared reference or helper that must stay synchronized with its shared source.
