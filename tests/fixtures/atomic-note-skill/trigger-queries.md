# Trigger query test: atomic-note

Full-rigor public-collection tier. Each query was judged three times in a fresh
Codex subagent context that received only the skill name and description.

Date: 2026-07-18 | Harness: Codex subagent | Model: GPT-5 session model

## Should-trigger queries

| Query | Run 1 | Run 2 | Run 3 | Result |
| --- | --- | --- | --- | --- |
| Turn this highlight into one Networked Thinking atomic note. | yes | yes | yes | pass |
| Improve the DAE explanation in this atomic note. | yes | yes | yes | pass |
| Make an atomic note for a mythology fact I want to remember. | yes | yes | yes | pass |
| Add an Anki card while improving this atomic note. | yes | yes | yes | pass |
| Connect this single atomic note to its parent structure note. | yes | yes | yes | pass |
| Rewrite this existing Networked Thinking note so one concept stands alone. | yes | yes | yes | pass |
| Create a DAE atomic note from this source quotation. | yes | yes | yes | pass |
| Fix the filename and Definition mismatch in this atomic note. | yes | yes | yes | pass |
| Make one atomic note about Ganymede for trivia practice. | yes | yes | yes | pass |
| Add an analogy and example to this incomplete atomic note. | yes | yes | yes | pass |

## Near-miss queries

| Query | Run 1 | Run 2 | Run 3 | Result |
| --- | --- | --- | --- | --- |
| Audit my whole vault for atomic-note quality. | no | no | no | pass |
| Create a generic meeting note. | no | no | no | pass |
| Design a Zettelkasten system from scratch. | no | no | no | pass |
| Fix the Python audit parser. | no | no | no | pass |
| Summarize this mythology article without creating a note. | no | no | no | pass |
| Create only a broad Mythology structure note, with no atomic note. | no | no | no | pass |
| Remediate this batch of 200 weak atomic notes. | no | no | no | pass |
| Create an Anki deck unrelated to Networked Thinking notes. | no | no | no | pass |
| Rewrite the repository README. | no | no | no | pass |
| Search my vault for duplicates but do not create or improve a note. | no | no | no | pass |

## Result

Pass. All 10 should-trigger queries activated in all three runs, and all 10
near-misses stayed inactive in all three runs. The existing description did not
need tuning.
