# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `managing-obsidian-tasks`, a portable Obsidian CLI workflow for durable task
  notes, review-before-create capture, lifecycle transitions, and derived Bases.
- Runner adapters for model judgments in the audit workflow.
- Self-contained npx install artifacts so `npx skills add` works without a repo clone.

### Changed

- Doctrine `1.0.7`, rubric `1.0.3`, and model prompt `1.0.5` require the
  Definition, Analogy, and Example to start with a capital letter, including a
  leading wikilink alias. `dae_sentence_case` is one deterministic finding for
  all three sections that survives model judgment. A section that opens with
  inline math may keep the math token first, and a mixed-case first word such as
  `gRPC` or `pH` is exempt. This replaces the Analogy-only rule and finding code
  from doctrine `1.0.6`, rubric `1.0.2`, and prompt `1.0.3`-`1.0.4`, which never
  shipped in a release. The prompt bump makes resume and apply reject stored
  judgments that carry the old code.
- Doctrine `1.0.5` puts formulas that complete a concept in the Definition with
  variable labels after a prose-first sentence; `Reference:` holds alternate
  forms and other Obsidian-only extras. Basic Front is a retrieval question for
  the central claim. Audit finding codes are unchanged.
- Install and skill docs recommend `atomic-note` + `atomic-note-audit` as a pair
  and state that skill-local doctrine/remediation copies are generated from
  `shared/`.
- Updated the repository banner from the shared Networked Thinking visual
  system, removing proof marks and the border so the title and knowledge graph
  remain prominent.
- Model-judgment storage schema `2.0.0` now requires collector-stamped prompt
  provenance; resume and apply reject missing or stale prompt versions.
- Doctrine names the optional `Reference:` section alongside numbered `Sources:`.
- Doctrine `1.0.4` and model prompt `1.0.2` make canonical atomic-note filenames
  copy the exact reader-visible Definition opening after the timestamp and
  without its final period, while YAML titles and H1s share a short concept name.
- Interactive authoring preserves explicitly declared non-standard user-vault
  filename schemes as compatibility exceptions, while model judgment without
  vault-level context evaluates the canonical Networked Thinking contract.
- Atomic-note doctrine now matches filenames to the Definition's first sentence
  and keeps YAML titles aligned with short H1 concept names.
- Structure-note and Anki guidance now treats learner-chosen factual recall and
  trivia as valid purposes alongside conceptual navigation.

### Fixed

- Plain-prose DAE sections accepted for non-Anki notes.
- Audit scoring excludes trailing `Reference:` and `Sources:` labels from DAE word counts and factual-risk checks.
- Improved Definition sentences now require an approved Obsidian CLI rename
  with automatic internal-link updates enabled and post-rename link checks.
- Structure Note updates now use complete, unaliased note filenames unless the
  learner explicitly requests a display alias.

## [0.1.0] - 2026-06-05

### Added

- Initial public package for Networked Thinking atomic-note skills.
- `atomic-note` skill for creating and improving atomic notes in DAE format.
- `atomic-note-audit` skill with deterministic scoring rules and schemas for auditing note quality.
