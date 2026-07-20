# Obsidian Task Contract

Task notes are the source of truth. Bases and structure notes are derived views.
The current contract is always canonical; task notes do not carry a schema
version.

## Location and identity

- Store every task note in `Tasks/`.
- Name it `YYYYMMDDHHmm Descriptive task title.md`.
- Keep the timestamp prefix unchanged. Rename the descriptive portion through
  the Obsidian CLI when clarity improves.
- Use one task note for one independently meaningful outcome. Keep smaller
  steps in Definition of done or Work log.

The first H1 is the descriptive title without the timestamp. `title`,
`date_created`, and `date_modified` are required vault-managed properties when
Obsidian Linter is configured to create them. Preserve them and let normal
vault behavior maintain them. Their transient absence does not authorize
linting and does not block creation. Do not invoke linting or set them manually.

## Required properties

Every task has these agent-managed properties:

```yaml
status: todo
priority: P2
execution_shape: agent-first
task_type: investigate
human_energy: medium
source_type: user-request
goal: "Complete the comparison until actionable findings are recorded, respecting the stated constraints, using the linked article and codebase, producing a linked findings note for human review."
```

Use `unknown` only when the available request, comparable tasks, and linked
context do not support a value. Set a new task to `todo` when every required
value is resolved and it is ready to begin. If any required value is `unknown`,
keep it in `triage`.

### Status

- `triage`: required information is unresolved.
- `todo`: defined and ready, but not started.
- `in-progress`: work is actively happening.
- `waiting-for`: no current action is expected while a person or event is
  pending.
- `blocked`: work cannot proceed because a required input, decision,
  credential, or dependency is missing.
- `done`: completion criteria and closure evidence are satisfied.
- `cancelled`: deliberately closed without completion.

There is no archived status. Closed notes remain in `Tasks/` and appear in the
History Base view.

### Priority

- `P0`: immediate material consequence if it is not addressed.
- `P1`: important or time-sensitive work needing near-term attention.
- `P2`: ordinary committed work; use when no other priority is supported.
- `P3`: optional, someday, or without a near-term consequence.
- `unknown`: evidence is insufficient or conflicting.

Assign P0 or P1 only from explicit urgency or strong evidence. A routine task
request is P2.

### Execution shape

- `human`: a human completes the work; agents may prepare.
- `agent`: an agent can complete, verify, and close the task end to end.
- `agent-first`: an agent produces the work, then a human accepts or finishes
  it before closure.
- `unknown`: the completion path is unclear.

Agent-suitable work defaults to `agent-first`. Use `agent` only when autonomous
closure is clearly safe and verifiable. An agent-first task moves from
`in-progress` to `waiting-for` when its proposed output is ready.

### Task type

Classify the primary completion outcome, not every activity involved:

- `create`: a new or materially changed artifact, document, design, system, or
  code result exists.
- `investigate`: a question is answered through research, comparison,
  diagnosis, analysis, or recommendation.
- `decide`: a choice or commitment is made and recorded.
- `communicate`: an asynchronous message, draft, handoff, follow-up, or
  outreach is completed.
- `meet`: a synchronous meeting, conversation, appointment, or interview
  occurs.
- `administer`: a transactional, logistical, or clerical action is completed,
  such as buying, booking, filing, scheduling, or submitting.
- `maintain`: an existing asset, system, environment, or routine is repaired,
  cleaned, updated, or preserved.
- `practice`: a skill, capability, health behavior, or practice is performed.
- `consume`: material is read, watched, heard, played, or experienced without a
  synthesized answer as the outcome.
- `other`: the outcome is understood but exposes a taxonomy gap.
- `unknown`: the outcome is not clear enough to classify.

### Human energy

- `none`: no human action is expected; use with `execution_shape: agent`.
- `low`, `medium`, or `high`: the energy needed for human execution, review,
  acceptance, or finishing work.
- `unknown`: the human demand is not clear enough to classify.

For `agent-first`, classify the human portion, not the agent's work.

### Source type

- `user-request`: a direct request from the user.
- `meeting`: a synchronous interaction.
- `message`: email, text, chat, or another asynchronous message.
- `document`: an article, note, PDF, transcript, or similar source.
- `code`: a repository, test, incident, or code inspection.
- `observation`: something noticed in personal or work life.
- `agent-recommendation`: a proactive agent proposal.
- `import`: a task migrated from another system.
- `unknown`: origin is unresolved.

Put detailed provenance and links in the Source section.

### Goal

`goal` is one clear outcome and its only canonical location. For `agent` and
`agent-first`, write it as one natural sentence following this contract:

```text
Complete [objective] until [verifiable end state], respecting [constraints],
using [inputs/tools], producing [artifact/handoff].
```

For `human`, use a concise outcome-oriented sentence. Put explanation in
Context instead of repeating the goal.

## Optional properties

Omit optional properties until they have a value:

- `project`: one Obsidian wikilink to a project note.
- `people`: a list of relevant Person-note wikilinks. Link only verified notes;
  preserve an unresolved name in the body instead of creating a Person note.
- `due`: a real deadline or externally meaningful date.
- `not_before`: the earliest date a human or agent should begin.

Do not use tags in task notes.

## Conditional properties and sections

`waiting-for` requires:

```yaml
waiting_on: "[[Person]] or external event"
follow_up_on: "<actual chosen follow-up date, YYYY-MM-DD>"
```

Waiting means no current action is expected. Review it on or after
`follow_up_on`; choose the actual date when the task should next be reviewed.
The value above is a placeholder, not a date to copy. Do not treat waiting as
an invitation to ask repeatedly how to unblock it.

`blocked` requires:

```yaml
blocked_on: "Missing credential, decision, dependency, or required input"
blocked_since: "<actual transition date, YYYY-MM-DD>"
```

Set `blocked_since` to the actual date of the transition to `blocked`; the
value above is a placeholder, not a date to copy. A blocked task also requires
a nonempty `## Unblock condition` section.

`done` and `cancelled` require:

```yaml
date_closed: "<actual transition date, YYYY-MM-DD>"
```

Set `date_closed` to the actual date of the transition to `done` or
`cancelled`; the value above is a placeholder, not a date to copy.

Done also requires every applicable Definition of done item checked and a
nonempty Result or Deliverables section. Cancelled requires a nonempty
`## Cancellation reason` section.

Remove waiting-only or blocked-only properties and sections when the status no
longer uses them. Preserve their history in Work log.

## Required body

Use these sections in this order:

1. `## Context`: why the task exists and relevant current state. Use `No
   additional context.` only when the task is genuinely self-explanatory.
2. `## Definition of done`: observable checklist items.
3. `## Inputs`: files, links, notes, people, systems, or tools needed to begin.
   Use `- None required.` for a self-contained task.
4. `## Constraints`: boundaries, non-goals, and important instructions. Use
   `- None beyond the task goal and vault-wide agent instructions.` when no
   special constraint exists.
5. `## Source`: human-readable provenance behind `source_type`. A direct task
   may say `Direct user request.`
6. `## Deliverables`: links to outputs; empty while none exist.
7. `## Result`: completed outcome and important consequences; empty while
   unfinished.
8. `## Work log`: append-only progress, decisions, state changes, and failed
   attempts. Format entries as `- YYYY-MM-DD HH:mm — Actor: Meaningful update.`
   Skip routine tool activity.

Put conditional Unblock condition or Cancellation reason immediately before
Work log.

## Duplicate and history rules

Before drafting a new task, inspect all task metadata and read the closest
matches by goal, title, project, people, and source.

- Update an active task that already represents the same outcome.
- For a new occurrence of closed work, create a new timestamped note and link
  the previous task in Context.
- When similarity remains uncertain, keep the outcomes separate.
- Preserve prior Work log entries. Record corrections as new entries.

## Transition rules

- A direct, unambiguous user instruction may update a task without another
  confirmation.
- An agent working an authorized task may set `in-progress`, append Work log,
  and record Deliverables or Result as work proceeds.
- `agent-first` may move to `waiting-for` with the user as `waiting_on`; only
  the user can accept it into `done`.
- `agent` may move to `done` after verifying every completion criterion.
- An agent may recommend cancellation, but applies it only on the user's direct
  instruction.

Every mutation targets one exact vault-relative path. Read the note immediately
before changing it, use an Obsidian CLI app-context operation, then re-read it.
If the pre-write read differs from the version used to plan the change,
recompute the change from the newer content.
