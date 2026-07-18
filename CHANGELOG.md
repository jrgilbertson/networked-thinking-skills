# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Runner adapters for model judgments in the audit workflow.
- Self-contained npx install artifacts so `npx skills add` works without a repo clone.

### Changed

- Doctrine names the optional `Reference:` section alongside numbered `Sources:`.
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
