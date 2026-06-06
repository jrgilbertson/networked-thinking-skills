# Atomic Note Audit

## Summary

- Run ID: fixture-run
- Total notes: 9
- Average score: 54.4 / 100
- Clean notes: 2 / 9 (22.2%)
- Priority counts: P0 3, P1 3, P2 1, P3 2
- Model judgment: not run; deterministic audit complete

## P0 Critical Remediation

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010103 Multi note bundle]] | 1 | no | missing_dae: Add complete Definition, Analogy, and Example sections.<br>missing_parent: Link this note from a structure note.<br>multi_note_file: Split bundled ideas into separate atomic notes.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example sections.<br>link-parent: Link this note from a structure note.<br>split-multi-note: Split bundled ideas into separate atomic notes.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |
| [[202601010104 Misfiled reference note]] | 7 | no | missing_dae: Add complete Definition, Analogy, and Example sections.<br>missing_parent: Link this note from a structure note.<br>misfiled_reference: Move source-material notes out of Atomic Notes or rewrite them as DAE notes.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example sections.<br>link-parent: Link this note from a structure note.<br>rehome-non-DAE: Move source-material notes out of Atomic Notes or rewrite them as DAE notes.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |
| [[202601010102 Weak DAE note]] | 27 | no | missing_dae: Add complete Definition, Analogy, and Example sections.<br>missing_parent: Link this note from a structure note.<br>weak_dae: Strengthen the DAE content with concrete, self-contained explanations. | improve-in-place: Add complete Definition, Analogy, and Example sections.<br>link-parent: Link this note from a structure note.<br>improve-in-place: Strengthen the DAE content with concrete, self-contained explanations. |

## P1 High-Impact Remediation

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010108 Malformed Anki note]] | 55 | no | missing_parent: Link this note from a structure note.<br>malformed_anki: Balance START and END markers for Anki card blocks. | link-parent: Link this note from a structure note.<br>improve-in-place: Balance START and END markers for Anki card blocks. |
| [[202601010106 Factual risk note]] | 57 | no | missing_parent: Link this note from a structure note.<br>factual_risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. | link-parent: Link this note from a structure note.<br>mark-factual-risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. |
| [[202601010105 Missing parent note]] | 63 | no | missing_parent: Link this note from a structure note. | link-parent: Link this note from a structure note. |

## P2 Meaningful Improvements

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010109 Duplicate candidate note]] | 80 | no | duplicate_overlap: Review this note against related notes for possible overlap. | duplicate-overlap-review: Review this note against related notes for possible overlap. |

## P3 Polish And Clean Notes

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010101 Clean DAE note]] | 100 | yes | none | none |
| [[202601010107 Optional Anki note]] | 100 | yes | none | none |

## Clean Notes

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010101 Clean DAE note]] | 100 | yes | none | none |
| [[202601010107 Optional Anki note]] | 100 | yes | none | none |

## Factual-Risk Notes

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010106 Factual risk note]] | 57 | no | missing_parent: Link this note from a structure note.<br>factual_risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. | link-parent: Link this note from a structure note.<br>mark-factual-risk: Mark empirical, current, attributed, or sensitive-domain claims for fact checking. |

## Duplicate Or Overlap Candidates

| Note | Score | Clean | Findings | Recommendations |
|---|---:|:---:|---|---|
| [[202601010109 Duplicate candidate note]] | 80 | no | duplicate_overlap: Review this note against related notes for possible overlap. | duplicate-overlap-review: Review this note against related notes for possible overlap. |

## Remediation Next Steps

- Resolve P0 critical remediation first: 3 notes.
- Work P1 high-impact remediation next: 3 notes.
- Review P2 improvements after blockers are clear: 1 note.
- Keep P3 polish and clean-note review as low-risk cleanup: 2 notes.
- Fact-check factual-risk notes before relying on them: 1 note.
- Review duplicate or overlap candidates before rewriting related notes: 1 note.
