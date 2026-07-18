# Baseline test: atomic-note recall-friendly structure guidance

Mode: revision. Each prior and revised evaluation ran in a separate Codex
subagent context. The revised mythology case received one fresh-context
follow-up after the parent-hub boundary was clarified.

## Case 1: Mixed-purpose mythology hub

Date: 2026-07-18 | Harness: Codex subagent | Model: GPT-5 session model

| Prompt | Prior-version behavior (observed) | Revised-version behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Create a broad Mythology structure note for comparing motifs and reviewing names, figures, and stories I want to remember. | Preserved motif comparison but could narrow the hub toward analysis, split its breadth as if it were one atomic note, or demote recall material to reference-only content. | Preserved one broad navigation hub with both comparison and recall sections. Applied DAE and one-concept rules to linked atomic children, not to the hub, and did not add Anki without a clearer practice request. | Better |

## Case 2: Explicit factual quiz recall

Date: 2026-07-18 | Harness: Codex subagent | Model: GPT-5 session model

| Prompt | Prior-version behavior (observed) | Revised-version behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Turn the invented Velunara myth-cycle fact that the moon-keeper Orivane carries seven silver keys into a DAE atomic note and Anki card because I explicitly want quiz recall. | Likely created the card, but the audit guidance could still second-guess it as low-stakes or reference-only trivia because explicit recall intent was not affirmative utility evidence. | Created one sourced, connected DAE note and treated the explicit quiz goal as memorization-utility evidence. Kept Anki-YAGNI available for other utility concerns and retained first-sync verification. | Better |

## Case 3: Explicit analytical use

Date: 2026-07-18 | Harness: Codex subagent | Model: GPT-5 session model

| Prompt | Prior-version behavior (observed) | Revised-version behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Create an atomic note about the hero's journey as a reusable analytical framework; I do not want trivia study. | Created a non-Anki DAE note for the analytical framework and linked it to a narrative or mythology parent. | Preserved the same analytical purpose, DAE shape, connection, and sourcing guidance without introducing recall or Anki. | Same |

## Result

The revision changes the two affected behaviors without weakening the analytical
case. The prior version favored analytical use asymmetrically; the revised
version preserves learner-chosen conceptual, factual-recall, trivia, or mixed
purposes while retaining DAE, sourcing, connection, factual-risk, and
learner-specific Anki-YAGNI gates.
