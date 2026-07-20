# Trigger query test: managing-obsidian-tasks

Full-rigor tier: eight should-trigger and eight near-miss queries, three fresh
ephemeral judgments per query. Each judge saw only the skill name,
description, and one synthetic query.

Date: 2026-07-20 | Harness: Codex CLI ephemeral | Model: gpt-5.6-sol

## Final description

> Use when the user explicitly says task, todo, or personal Kanban, or asks to
> find, review, update, wait, block, complete, or cancel an existing Obsidian
> task. Requests phrased only as "track this for later" belong to the issue
> workflow. Do not use for work bound for GitHub, Linear, or a Codex
> conversation; calendar events or reminders; checklist edits inside other
> notes; or immediate implementation not requested as a task.

## Should-trigger queries

| Query | Run 1 | Run 2 | Run 3 | Result |
| --- | --- | --- | --- | --- |
| Create a todo to follow up with Morgan next Friday. | yes | yes | yes | Pass |
| Add a task to research this article against the Northstar codebase. | yes | yes | yes | Pass |
| Show me all of my blocked tasks. | yes | yes | yes | Pass |
| Mark the vendor response task as waiting for Morgan until next Monday. | yes | yes | yes | Pass |
| Change my dentist task to P1 and move its due date to August 3. | yes | yes | yes | Pass |
| Mark the passport renewal task done and link the confirmation note as its result. | yes | yes | yes | Pass |
| Cancel my gym membership task because I decided to keep the plan. | yes | yes | yes | Pass |
| Set up my personal Kanban task system in this Obsidian vault. | yes | yes | yes | Pass |

## Near-miss queries

| Query | Run 1 | Run 2 | Run 3 | Result |
| --- | --- | --- | --- | --- |
| File a Linear issue for the checkout bug. | no | no | no | Pass |
| Open a GitHub issue to upgrade the authentication library. | no | no | no | Pass |
| Track this for later: the checkout page needs clearer errors. | no | no | no | Pass after tuning |
| Remind me tomorrow at 9 AM to call the dentist. | no | no | no | Pass |
| Add a packing checklist to the trip planning note. | no | no | no | Pass |
| Implement the login fix now and run the tests. | no | no | no | Pass |
| Start a new Codex task to debug the signup flow. | no | no | no | Pass |
| Create a task in Linear for the invoice export work. | no | no | no | Pass |

## Tuning

The original description activated all three runs of "Track this for later."
An explicit exclusion still produced one yes and two unsure judgments. The
final description changed the positive gate to explicit task, todo, personal
Kanban, or existing Obsidian-task language and routed the bare deferral phrase
to the issue workflow. The affected near-miss then returned no in all three
runs. All positive queries were rerun against the final description and passed
three of three.
