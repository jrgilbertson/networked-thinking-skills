# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Runner adapters for model judgments in the audit workflow.
- Self-contained npx install artifacts so `npx skills add` works without a repo clone.

### Changed

- Doctrine names the optional `Reference:` section alongside numbered `Sources:`.
- Proposition-style timestamp filenames now express the same concept and
  specificity as each note type's Definition source, while concise display
  titles remain compatible labels.
- Authoring and model-judgment guidance now detect naming conventions from
  local templates and nearby notes instead of treating timestamps alone as
  proposition evidence.

### Fixed

- Plain-prose DAE sections accepted for non-Anki notes.
- Audit scoring excludes trailing `Reference:` and `Sources:` labels from DAE word counts and factual-risk checks.
- Improved Definition sentences now require an approved Obsidian CLI rename
  with automatic internal-link updates enabled and post-rename link checks.

## [0.1.0] - 2026-06-05

### Added

- Initial public package for Networked Thinking atomic-note skills.
- `atomic-note` skill for creating and improving atomic notes in DAE format.
- `atomic-note-audit` skill with deterministic scoring rules and schemas for auditing note quality.
