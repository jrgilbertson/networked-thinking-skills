# Atomic Note Audit

## Summary

- Run ID: fixture-run
- Total notes: 13
- Average score: 76.7 / 100
- No-change notes: 4 / 13 (30.8%)
- Bucket counts: P0 2, P1 1, P2 4, P3 2, No changes 4
- Model judgment: not run; deterministic audit complete

## P0 Critical Remediation

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010103 Multi note bundle]] | 12 | no | invalid_dae: Add complete Definition, Analogy, and Example content.<br>missing_parent: Link this note from a structure note.<br>multi_note: Split bundled ideas into separate atomic notes.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example content.<br>link-parent: Link this note from a structure note.<br>split-multi-note: Split bundled ideas into separate atomic notes.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |
| [[202601010104 Misfiled reference note]] | 22 | no | invalid_dae: Add complete Definition, Analogy, and Example content.<br>missing_parent: Link this note from a structure note.<br>misfiled_reference: Move source-material notes out of Atomic Notes or rewrite them as DAE notes.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example content.<br>link-parent: Link this note from a structure note.<br>rehome-non-DAE: Move source-material notes out of Atomic Notes or rewrite them as DAE notes.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |

## P1 High-Impact Remediation

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010102 Weak DAE note]] | 57 | no | invalid_dae: Add complete Definition, Analogy, and Example content.<br>missing_parent: Link this note from a structure note.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example content.<br>link-parent: Link this note from a structure note.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |

## P2 Meaningful Improvements

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010108 Malformed Anki note]] | 74 | no | missing_parent: Link this note from a structure note.<br>malformed_anki: Balance START and END markers for Anki card blocks. | link-parent: Link this note from a structure note.<br>improve-in-place: Balance START and END markers for Anki card blocks. |
| [[202601010111 Tab decayed equation note]] | 82 | no | decayed_latex_command: Restore `\times`. A control character stands where the command should begin. Write the note so the transport cannot decode the escape again. | improve-in-place: Restore `\times`. A control character stands where the command should begin. Write the note so the transport cannot decode the escape again. |
| [[202601010112 Newline decayed equation note]] | 82 | no | decayed_latex_command: Restore `\neq`. A control character stands where the command should begin. Write the note so the transport cannot decode the escape again. | improve-in-place: Restore `\neq`. A control character stands where the command should begin. Write the note so the transport cannot decode the escape again. |
| [[202601010106 Factual risk note]] | 84 | no | missing_parent: Link this note from a structure note.<br>factual_risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. | link-parent: Link this note from a structure note.<br>mark-factual-risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. |

## P3 Polish

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010105 Missing parent note]] | 92 | no | missing_parent: Link this note from a structure note. | link-parent: Link this note from a structure note. |
| [[202601010109 Duplicate candidate note]] | 92 | no | duplicate_overlap: Review this note against related notes for possible overlap. | duplicate-overlap-review: Review this note against related notes for possible overlap. |

## No Changes

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010101 A clean atomic note explains one durable idea in plain language and keeps the claim small enough to test against examples]] | 100 | yes | none | none |
| [[202601010107 Optional Anki cards can reinforce an atomic note when the prompt tests the central claim instead of repeating the heading]] | 100 | yes | none | none |
| [[202601010110 A source-backed atomic note keeps one durable idea in DAE form and adds optional trailing sections for connections and provenance]] | 100 | yes | none | none |
| [[202601010113 A tab inside a fenced code block or a table cell is quoted data rather than a command that decayed into it]] | 100 | yes | none | none |

## Factual-Risk Notes

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010106 Factual risk note]] | 84 | no | missing_parent: Link this note from a structure note.<br>factual_risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. | link-parent: Link this note from a structure note.<br>mark-factual-risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. |

## Duplicate Or Overlap Candidates

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010109 Duplicate candidate note]] | 92 | no | duplicate_overlap: Review this note against related notes for possible overlap. | duplicate-overlap-review: Review this note against related notes for possible overlap. |

## Remediation Next Steps

- Resolve P0 critical remediation first: 2 notes.
- Work P1 high-impact remediation next: 1 note.
- Review P2 improvements after blockers are clear: 4 notes.
- Keep P3 polish as low-risk cleanup: 2 notes.
- Leave no-change notes alone unless a later audit finds new issues: 4 notes.
- Fact-check factual-risk notes before relying on them: 1 note.
- Review duplicate or overlap candidates before rewriting related notes: 1 note.
