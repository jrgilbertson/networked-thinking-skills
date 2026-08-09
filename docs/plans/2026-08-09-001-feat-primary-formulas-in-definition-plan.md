---
title: Primary Formulas in Definition - Plan
type: feat
date: 2026-08-09
topic: primary-formulas-in-definition
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
origin: https://github.com/jrgilbertson/networked-thinking-skills/issues/46
---

# Primary Formulas in Definition - Plan

## Goal Capsule

- **Objective:** Make atomic-note authoring put formulas that complete a concept in the Definition (with variable labels), instead of parking primary formulas only in `Reference:` where Anki Basic never shows them.
- **Product authority:** GitHub issue #46 and the Product Contract below.
- **Execution profile:** Shared doctrine wording, `atomic-note` skill workflow bullet, focused skill-contract tests, doctrine version bump, changelog note, and generated skill-artifact sync.
- **Stop conditions:** Stop if the work expands into bulk vault remediation, a new audit finding code, or dual process+formula Anki cards per concept.
- **Tail ownership:** The implementer owns syncing generated skill copies, updating contract tests, running pre-commit checks, and opening a PR against issue #46.

---

## Product Contract

### Summary

Update Networked Thinking atomic-note doctrine and the create/improve skill so agents include a formula in the Definition when omitting it would leave the concept incomplete at review, and require those formulas to label their variables.
Keep the filename rule prose-first and leave `Reference:` for alternate forms and non-tested extras, not as the default home of the primary formula.

### Problem Frame

Formulas are compact definitions, but current doctrine lists formulas under optional `Reference:` material “worth preserving but not worth testing.”
Agents over-apply that language and put the primary symbolic form after Anki `END`, so Basic cards never surface the equation during review.
Bare symbols without labels also force the learner to already know the notation, which undercuts the formula’s job of clarifying the Definition.

### Requirements

**Formula placement**

- R1. Prefer a formula in the Definition when omitting it makes the definition incomplete or forces the learner to invent symbols at review.
- R2. Prefer prose-first Definition text, with the primary formula as a later sentence or continuation in the same Definition paragraph (plain-prose) or same Definition section (legacy headed), not as the filename source sentence.
- R3. Keep `Reference:` for alternate forms, edge cases, long displays, and non-tested extras; do not treat it as the default home of the primary formula when the card needs that formula.
- R4. Doctrine must state the Anki implication: material only after `END` or only in post-Anki `Reference:` is Obsidian-only for Basic review and will not appear on the flashcard.

**Variable labels**

- R5. When a formula is included in the Definition because it completes the concept, label each variable the formula uses with a following “where …” clause or equivalent compact gloss so symbols are self-explanatory on the card.
- R6. Do not require labels on every incidental symbol in an Example calculation when the Definition already defined those symbols.

**Workflow and policy**

- R7. The `atomic-note` skill draft step must mention including formulas that complete the definition, with variable labels, in the Definition when appropriate.
- R8. Do not auto-create a second Anki note for every formula; Anki-YAGNI still applies. A separate Cloze is allowed only when symbol recall is the explicit goal.
- R9. Filename and short-title rules stay unchanged: the first reader-visible Definition sentence drives the filename; variable labels after the formula do not change the filename source.

**Contract maintenance**

- R10. Advance `doctrine_version` from `1.0.4` to `1.0.5`. Leave schema, rubric, prompt, and package versions unchanged.
- R11. Record the behavior change under `CHANGELOG.md` Unreleased.
- R12. Edit canonical doctrine under `shared/`, then sync generated skill-local copies.
- R13. Automated tests must assert the hybrid rule and variable-label requirement in shared doctrine and the skill workflow so the prior “formulas live in Reference” default cannot silently return.

### Acceptance Examples

- AE1. **Covers R1-R5, R9.** Given a concept whose primary relation is a formula (for example a neuron forward pass), when the skill drafts the Definition, then the first sentence is prose-safe for the filename, a later part of the same Definition paragraph includes the equation and a “where …” gloss for each variable the formula uses, and the primary formula is not only in post-`END` Reference.
- AE2. **Covers R3-R4.** Given alternate forms or long edge-case displays that are not the tested claim, when the skill adds supporting material, then those extras may live under `Reference:` while the primary formula remains in Definition when the card needs it.
- AE3. **Covers R6-R8.** Given an Example that reuses already-labeled symbols, when the skill writes the Example, then it does not restate every variable label, and it does not create a second Anki card solely because a formula exists.
- AE4. **Covers R7, R10-R13.** Given the merged skill package, when an agent reads doctrine and the skill workflow, then both state the hybrid rule and label requirement, audit results report doctrine version `1.0.5`, and focused tests fail if those instructions regress.

### Success Criteria

- Doctrine states the hybrid placement rule, variable-label rule, filename implication, and Anki visibility implication.
- Skill workflow mentions formulas that complete the definition, with variable labels, during Definition drafting.
- `Reference:` guidance no longer reads as “default all formulas here.”
- Doctrine version is `1.0.5`; unrelated contract versions are unchanged.
- Focused skill-contract tests and full pre-commit checks pass.
- Generated skill artifacts stay in sync with `shared/`.

### Scope Boundaries

- Bulk migration or remediation of existing vault notes is out of scope.
- New deterministic audit finding codes, rubric changes, or model-judgment prompt changes for formula placement are out of scope for this plan.
- Requiring dual process+formula cards for every concept is out of scope.
- Forcing labels on every incidental Example symbol when Definition already labeled them is out of scope.
- Companion-vault template or manuscript book changes are out of scope unless a later PR deliberately expands.

### Sources and Research

- GitHub issue #46: `https://github.com/jrgilbertson/networked-thinking-skills/issues/46`
- Current doctrine Reference language: `shared/references/doctrine.md` (Required Shape and Reference section)
- Current skill workflow: `skills/atomic-note/SKILL.md`
- Prior doctrine migration learning: `docs/solutions/conventions/plain-prose-dae-contract-migration.md`
- Naming-pair preservation (filename stays first Definition sentence): `docs/solutions/conventions/keep-atomic-note-naming-pairs-aligned-with-obsidian-aware-renames.md`
- Prior skill-contract test pattern: `tests/test_atomic_note_skill_examples.py`
- Display-math paragraphs are skipped by plain-prose paragraph extraction: `shared/scripts/markdown_parse.py` (`_is_display_math_paragraph`)

---

## Planning Contract

### Key Technical Decisions

- KTD1. **Authoring guidance only, no audit automation.** (session-settled: user-approved — chosen over adding audit findings: issue acceptance and confirmed scope stop at doctrine/skill text.) Update shared doctrine and the create/improve skill; do not add finding codes, rubric rows, or prompt checks for formula placement in this plan.
- KTD2. **Keep formula and labels inside the Definition paragraph block.** Prefer the primary formula and “where …” gloss as later sentences in the same Definition paragraph (or the same Definition section in legacy headed notes), not as a new intervening paragraph between Definition and Analogy. A lone `$$...$$` display-math paragraph is skipped by plain-prose DAE paragraph extraction and can leave component order ambiguous; if display math is needed, attach labels in prose that remains part of the Definition block and keep Analogy as the next non-math prose paragraph.
- KTD3. **Word-count discipline stays 10-50 rendered words for the Definition.** Formula symbols and the compact where-clause count as rendered words. Prefer a short prose opener plus a compact equation and short gloss; if the Definition would exceed 50 words, tighten wording rather than moving the primary formula solely to `Reference:`. U1’s worked example must itself stay within 50 rendered words so the doctrine budget is demonstrated, not only asserted. Math-aware word counting, a higher formula-bearing cap, and audit exceptions for temporary over-length formula notes are deferred follow-ups, not part of this plan.
- KTD4. **Doctrine version only (rulebook text, not audit semantics).** Behavior for agents changes, so bump `DOCTRINE_VERSION` `1.0.4` → `1.0.5` in the shared audit engine constant (and any mirrored generated copy after sync). Do not bump schema, rubric, or prompt versions because deterministic audit behavior is unchanged. Version `1.0.5` records the authoring-rulebook change; regression proof is phrase-lock tests, not new formula-placement findings.
- KTD5. **Prove the instruction with skill-contract assertions, not vault fixtures.** Follow `tests/test_atomic_note_skill_examples.py`: assert distinctive hybrid-rule and label phrases in `shared/references/doctrine.md` and `skills/atomic-note/SKILL.md`. Optionally add a tiny synthetic JSON fixture if it clarifies the worked example; do not commit private vault content.

### Assumptions

- Issue #46’s hybrid rule and worked neuron-forward-pass shape are the product intent; ce-pov already selected hybrid over “always append a formula.”
- `skills/atomic-note/SKILL.md` is hand-edited; only `references/doctrine.md` is generated from `shared/` for that skill.
- Syncing doctrine also refreshes `skills/atomic-note-audit/references/doctrine.md`, which is desired so both skills share one authoring contract even without new audit findings.

### Implementation Constraints

- Edit `shared/` sources first for generated artifacts, then run skill-artifact sync.
- Use synthetic reusable fixtures only; never commit real vault notes.
- Keep changes small and preserve deterministic goldens unless a doctrine-version field in goldens requires a mechanical refresh.

### Sequencing

1. Doctrine wording and example in `shared/references/doctrine.md`.
2. Skill workflow bullet in `skills/atomic-note/SKILL.md`.
3. Version constant, changelog, skill-contract tests.
4. Sync generated artifacts and run verification gates.

---

## Implementation Units

### U1. Doctrine hybrid formula rule and Reference rewrite

**Goal:** State when a formula belongs in Definition vs Reference, require variable labels on formulas that complete the concept, and include one short math example.

**Requirements:** R1-R6, R8-R9, R12

**Dependencies:** None

**Files:**
- Modify: `shared/references/doctrine.md`
- Generated after sync: `skills/atomic-note/references/doctrine.md`, `skills/atomic-note-audit/references/doctrine.md`

**Approach:**
1. Under DAE Rules (Definition bullet or a short adjacent rule), add the hybrid placement rule: include the formula in Definition when it completes the concept; prose-first opener; formula and variable gloss later in the same Definition paragraph (prefer inline math); label each variable the formula uses. State the anti-pattern: a blank-line-separated lone `$$...$$` paragraph between the opener and gloss is not Definition content for plain-prose DAE (display-math paragraphs are skipped by paragraph extraction).
2. Add a compact worked example (prose sentence + symbolic form + “where …” labels), synthetic and generic, written as one Definition paragraph with no blank lines around the equation, and verified to stay within 50 rendered words.
3. Rewrite Required Shape and Reference section language so formulas are not framed as default Reference-only material. Keep Reference for alternate forms, long displays, tables, commands, and non-tested extras.
4. State Anki Basic visibility: post-`END` / Reference-only primary formulas are invisible during Basic review.
5. Reaffirm filename uses the first reader-visible Definition sentence; labels do not change that source.
6. Note Anki-YAGNI: no automatic second card for every formula.

**Patterns to follow:** Existing DAE Rules density in `shared/references/doctrine.md`; naming-pair exactness language already in that file.

**Test scenarios:** Covered by U3 assertions once wording lands.

**Verification:** Doctrine text alone makes the hybrid rule, label rule, filename implication, and Anki implication unambiguous to a cold reader.

### U2. Skill workflow mentions primary formulas in Definition

**Goal:** Make the create/improve draft step surface the same placement and label rule without restating the full doctrine.

**Requirements:** R7, R9

**Dependencies:** U1

**Files:**
- Modify: `skills/atomic-note/SKILL.md`

**Approach:**
1. In Workflow step 3 (draft DAE), add a brief clause that when a formula completes the definition, include it in the Definition with variable labels, prose-first for the filename sentence.
2. Keep the step short; point agents to doctrine for the full hybrid rule rather than duplicating Reference policy.
3. Leave naming-pair and Anki steps unchanged except where a one-word cross-reference helps.

**Patterns to follow:** Existing recall-purpose and naming-pair workflow bullets in the same file.

**Test scenarios:** Covered by U3.

**Verification:** An agent reading only the workflow still learns to put formulas that complete the definition, with labels, in Definition when appropriate.

### U3. Version, changelog, contract tests, and artifact sync

**Goal:** Make the doctrine contract version and automated checks match the new authoring rule.

**Requirements:** R10-R13

**Dependencies:** U1, U2

**Files:**
- Modify: `shared/scripts/audit_engine.py` (`DOCTRINE_VERSION`)
- Modify: `tests/test_audit_engine.py` (`test_audit_versions_are_contract_specific` expects `1.0.5`)
- Modify: `CHANGELOG.md`
- Modify: `tests/test_atomic_note_skill_examples.py`
- Optional create: `tests/fixtures/atomic-note-skill/primary-formula-in-definition.json` only if it clarifies assertions
- Generated: skill-local doctrine and any synced script copies under `skills/atomic-note/` and `skills/atomic-note-audit/`

**Approach:**
1. Bump `DOCTRINE_VERSION` to `1.0.5`.
2. Update the contract-specific version assertion in `tests/test_audit_engine.py` from `1.0.4` to `1.0.5` (this is the live R10 check; pre-commit fails without it).
3. Add an Unreleased changelog entry describing the hybrid formula rule and label requirement; note that audit finding behavior is unchanged.
4. Add a focused test that shared doctrine and `skills/atomic-note/SKILL.md` contain distinctive hybrid-rule and variable-label language, and that prior default-only Reference framing for primary formulas is no longer the sole guidance.
5. Run `python3 -m shared.scripts.sync_skill_artifacts` so installable skill copies match shared doctrine and the version constant.
6. If golden audit outputs embed `doctrine_version`, refresh only those mechanical version strings.

**Execution note:** Prefer assertion-first on the skill and doctrine text so the regression is locked before polishing wording.

**Patterns to follow:** `tests/test_atomic_note_skill_examples.py` recall-purpose and naming-pair tests; prior plan version discipline from issue #28.

**Test scenarios:**
- Happy path: doctrine contains hybrid placement language (Definition when formula completes concept) and variable-label language (“where” or equivalent gloss requirement).
- Happy path: skill workflow text mentions formulas that complete the definition, with variable labels, in Definition.
- Regression: doctrine no longer presents formulas only as Reference “not worth testing” material without the Definition exception.
- Contract: audit engine doctrine version string is `1.0.5` while schema/rubric/prompt versions remain at their current values.
- Sync: `python3 -m shared.scripts.sync_skill_artifacts --check` reports clean after sync.

**Verification:** Focused unit tests pass; full pre-commit hook passes; generated skill doctrine matches `shared/references/doctrine.md`.

---

## Verification Contract

| Gate | Command / check | Applies to | Done signal |
| --- | --- | --- | --- |
| Focused skill contract | `env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_atomic_note_skill_examples` | U3 | New and existing assertions pass |
| Artifact sync | `python3 -m shared.scripts.sync_skill_artifacts --check` | U1, U3 | No out-of-sync generated copies |
| Full pre-commit | `lefthook run pre-commit --force --no-auto-install` | All units | Hook suite green |
| Manual doctrine read | Cold-read DAE Rules + Reference sections | U1-U2 | Hybrid rule, labels, filename, Anki visibility are explicit |

---

## Definition of Done

- Issue #46 acceptance checkboxes are met by the merged skill package.
- Shared doctrine and skill workflow encode the hybrid formula rule and variable-label requirement.
- `doctrine_version` is `1.0.5`; unrelated contract versions unchanged.
- Skill-contract tests lock the instruction; pre-commit and sync checks pass.
- No bulk vault edits, no new audit finding code, and no abandoned experimental wording left in the diff.
- PR links issue #46.

---

## Risks and Dependencies

| Risk | Mitigation |
| --- | --- |
| Formula + where-clause pushes Definition over 50 rendered words | KTD3: compact gloss; tighten prose; keep primary formula in Definition rather than demoting it to Reference-only |
| Display-math paragraph breaks plain-prose DAE component order | KTD2: keep formula/labels in the Definition block; avoid a lone intervening `$$` paragraph between Definition and Analogy |
| Agents still park formulas in Reference from habit | Skill workflow bullet (U2) plus doctrine demotion of “formulas default to Reference” language |
| Doctrine version bump without golden refresh fails checks | U3 checks goldens for embedded `doctrine_version` and refreshes only if required |

---

## System-Wide Impact

- **Authoring agents** using `atomic-note` will surface primary formulas on Basic cards more often.
- **Audit skill** receives the same doctrine text via sync but gains no new deterministic findings in this plan.
- **Existing vault notes** are unchanged until a human or separate remediation pass edits them.
