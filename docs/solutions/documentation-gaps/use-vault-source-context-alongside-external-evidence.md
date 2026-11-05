---
title: Use Vault Source Context Alongside External Evidence
date: 2026-11-05
module: networked-thinking atomic-note authoring and audit
problem_type: documentation_gap
tags: [atomic-notes, source-context, references, attribution, factual-review]
---

# Use Vault Source Context Alongside External Evidence

## Problem and correction

The authoring skill told agents to read source material, and the audit skill kept
fact-checks unverified until checked. Neither explicitly directed agents to the
books, articles, highlights, literature notes, and learner synthesis accumulated
in the vault. A linked reference could therefore be overlooked during a revision.

**Source Evidence for Authoring and Review** in the
[shared remediation context](../../../shared/references/remediation-context.md)
now owns this guidance. Both entrypoints load it before applicable source review
or improvement proposals. Relevant vault material and external evidence inform
the claim together; source location or publication date alone decides neither
authority nor reading order. Source checks remain separate from model quality
judgments and mutation approval.

Package 0.4.1 carries this workflow clarification. Doctrine, rubric, model prompt,
schemas, and report-format contracts are unchanged.

## Observed synthetic behavior

One authenticated `codex exec` run used the runner's default `gpt-6.1-sol` model
at low reasoning effort. The run supplied both revised entrypoints, the doctrine,
the shared remediation context, and six fictional source-review cases. The model
returned one response per case per skill: twelve responses total.

- [Saved inputs](../../../tests/fixtures/atomic-note-skill/vault-source-context.json)
- [Actual responses](../../../tests/fixtures/atomic-note-skill/vault-source-context-responses.json)

The evaluator manually checked each response against the supplied evidence:

| Case | Observed result for both skills |
| --- | --- |
| Linked book and highlight | Used the author's distinct-receiver definition and observation window; separated saved excerpts from learner interpretation. |
| No useful local evidence | Used the supplied fictional official manual with optional/version restrictions; claimed no live current-status check. |
| Historical and current disagreement | Resolved the claim by protocol version and retained historical attribution and learner commentary. |
| Missing citation and unrelated link | Kept the claim unverified and identified needed evidence without inventing a source. |
| Existing accepted quality judgment | Reported a source contradiction separately while preserving the recorded score, clean state, and cache key. |
| Required app access unavailable | Reported the inaccessible highlight and declined raw-filesystem substitution and numerical endorsement. |

## Reproduction and limits

The run used `codex exec --ignore-user-config --ephemeral
--skip-git-repo-check --sandbox read-only --color never -C /tmp`, with the prompt
on stdin and the final response saved through `--output-last-message`.
All source passages, names, and products in the cases are fictional.

The prompt required a read-only exercise: no tools, vault access, browsing,
mutations, or worker launches. It supplied the complete available excerpts and
asked each entrypoint for user-facing source-review responses and improvement
proposals, not self-grades. The audit exercise explicitly excluded new model
quality judgments and report publication. The response shape was
`{"responses":[{"skill":"...","case":"...","response":"..."}]}`.

This is one supplied-context observation, without repeated trials or a baseline
comparison. The responses are evidence for this instruction-following exercise,
not a deterministic golden assertion or proof of automatic reference loading,
source discovery, live external research, app integration, or end-to-end audits.
No private vault material was used and no Obsidian vault was created or opened.
Existing repository tests separately verify packaged references and generated
artifact parity; they do not prove agent compliance with prose.
