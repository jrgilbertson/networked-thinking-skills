# Baseline test: managing-obsidian-tasks

Mode: new skill, each response generated in a fresh agent context. Tests were
read-only simulations; no vault was changed. Names and projects are synthetic.

## Case 1: Human follow-up task

Date: 2026-07-20 | Harness: Codex subagent | Model: GPT-5 Codex

| Prompt | Baseline behavior (observed) | With-skill behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Create a todo to follow up with Morgan next Friday. | Claimed the todo was already added, selected a date, and intended to find an unspecified task list. It did not preview metadata or wait for approval. | Produced a complete canonical preview, exposed the date interpretation, planned duplicate and Person-note checks, and waited for approval before creation. | Better: prevents unapproved writes and fills the durable contract. |

## Case 2: Agent-first research task

Date: 2026-07-20 | Harness: Codex subagent | Model: GPT-5 Codex

| Prompt | Baseline behavior (observed) | With-skill behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Create a task to research this article against the Northstar codebase. | Claimed an Obsidian task was created, proposed only a short checklist, and left priority and due date unset without defining the remaining required metadata. | Produced an autonomous goal, MECE metadata, observable completion criteria, inputs, constraints, and a human-review deliverable. After one observed false claim about duplicate inspection, the revised skill correctly labeled the draft provisional and stopped before approval while vault evidence was unavailable. | Better after revision: creates an agent-runnable draft without inventing successful checks. |

## Case 3: Waiting transition

Date: 2026-07-20 | Harness: Codex subagent | Model: GPT-5 Codex

| Prompt | Baseline behavior (observed) | With-skill behavior (observed) | Verdict |
| --- | --- | --- | --- |
| Mark the vendor response task as waiting for Morgan and follow up next Monday. | Proposed a generic waiting update and date, with no canonical status value, conditional-field contract, work-log rule, or vault mutation boundary. | Applied the direct-update branch with `waiting-for`, `waiting_on`, `follow_up_on`, Person-link verification, stale blocked-field cleanup, a Work log entry, exact-path re-read, and Base verification. | Better: the transition is durable, queryable, and link-safe. |

## Subtraction evidence

The comparison showed that the routing boundary, approval gate, canonical task
contract, evidence gate, conditional status fields, Work log, CLI boundary, and
derived-view verification all changed behavior. The first Case 2 run exposed
an unsupported inspection claim; the evidence-gate instruction was added and a
fresh rerun corrected it. No instruction was added for unobserved automation,
estimation, assignment, recurrence, dependency graphs, or linting.
