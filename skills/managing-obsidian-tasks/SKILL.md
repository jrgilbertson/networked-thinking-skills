---
name: managing-obsidian-tasks
description: Use when the user explicitly says task, todo, or personal Kanban, or asks to find, review, update, wait, block, complete, or cancel an existing Obsidian task. Requests phrased only as "track this for later" belong to the issue workflow. Do not use for work bound for GitHub, Linear, or a Codex conversation; calendar events or reminders; checklist edits inside other notes; or immediate implementation not requested as a task.
license: MIT
compatibility: Requires a running Obsidian desktop app with the official Obsidian CLI. Dashboard setup also requires the core Bases plugin.
---

# Managing Obsidian Tasks

Manage Obsidian tasks from capture to completion. Task notes are the source of
truth; dashboards only display their properties.

## Required References

- `references/task-contract.md`

Read `references/task-contract.md` before drafting, creating, changing,
transitioning, or validating a task. A search-only run may delay reading it
until task properties need interpretation.

Read the files under `assets/` only when setting up or repairing the task
system. They define the current task template, Base, and structure note.

## Obsidian CLI boundary

Use the official Obsidian CLI for every vault search, read, create, update,
rename, move, property change, and deletion. Run it through
`python3 scripts/obsidian_cli.py` when the bundled wrapper is usable; otherwise
invoke the official CLI binary directly. Always pass the intended vault and an
exact vault-relative path for mutations.

Preflight the CLI against the target vault before any write. When the app or
CLI is unavailable, keep the proposed content as a draft and stop before
mutation. Raw filesystem access is not a fallback for vault content.

## Workflow

### 1. Resolve the request and vault

Classify the request as setup, create, search, update, transition, or close.
If the request says only "capture this" and context does not identify the
destination, ask whether the user wants an Obsidian task or a tracker issue.
Resolve the target vault from the user's context or the CLI vault list; ask
when more than one plausible vault remains. Confirm that the CLI can read the
vault and inspect `Tasks/`, `Bases/Tasks.base`, `Structure Notes/Tasks.md`, and
`Templates/Task.md` as applicable.

Completion: one operation branch and one reachable target vault are known.

### 2. Inspect task context

Use the CLI to inspect all task metadata, then read the closest matches by
title, goal, project, people, and source. Read linked project or Person notes
when they would improve classification. For creation, compare prior
`human_energy` values and other repeated patterns before proposing metadata.
State that a check succeeded only when its CLI result was obtained. When vault
context is unavailable, label the draft provisional and stop before claiming
that duplicates, links, or historical patterns were verified.

Apply the duplicate rules from the task contract. Prefer improving an active
task that already owns the outcome; keep uncertain outcomes separate.

Completion: every plausible active duplicate is resolved and the relevant
historical context has informed the operation.

### 3. Follow the operation branch

#### Setup or repair

Compare the three assets with the target paths. Present the files that would be
created or replaced and wait for approval. Write approved content through the
CLI. Preserve user customizations unless they violate the task contract.

Completion: the template, Base, and structure note are readable through the
CLI, and every Base view queries without error.

#### Create

Draft from `assets/task-template.md`. Infer required values from the request,
comparable tasks, and linked context; use `unknown` only when evidence remains
insufficient. A required unknown keeps the proposed task in `triage`.

Present the proposed filename, complete metadata, and populated body. Wait for
explicit approval before writing every new task, including when the request
already says "create a task." Apply requested corrections to the preview and
ask again.

Set the proposed status to `todo` when every required value is resolved and the
task is ready to begin. Keep it in `triage` when any required value is
`unknown`.

After approval, use the CLI `create` operation without overwrite. Re-read the
exact path and query the All tasks Base view. Linter-owned properties remain
outside this skill's completion gate.

Completion: the approved note exists once, matches the preview, and appears in
the task Base.

#### Search or review

Query the narrowest relevant Base view, then inspect matching notes when the
answer needs body context. Return concise results with status, priority,
relevant dates, goal, and a link or vault-relative path for each task.

Completion: every task matching the stated filters is represented, or the
response states that none matched.

#### Update or transition

Resolve one exact task path. Read it immediately before mutation. Apply
property changes with CLI `property:set` or `property:remove`, and append Work
log entries with CLI `append`. For a body-section replacement, use CLI `eval`
with `app.vault.process(file, updater)` so the updater receives the current
content. Avoid whole-note replacement so concurrent context and history
survive.

Apply direct, unambiguous user updates without another confirmation. Follow the
execution-shape and status gates in the task contract for agent-initiated
transitions. Re-read the note after every mutation and query its applicable
Base view.

Completion: the requested state is visible in both the note and derived view,
with required conditional fields, sections, and Work log evidence present.

#### Close

Check every applicable Definition of done item and inspect Deliverables and
Result. Apply the closure and execution-shape gates from the task contract.

Set closure properties through the CLI, append the final Work log entry, then
verify the note appears in History and no longer appears in active views.

Completion: the closure contract passes and the derived views reflect the
closed state.

### 4. Report the result

State what changed or what was found. Link the affected task notes and name any
remaining `unknown`, waiting, blocked, or review condition. For a stopped
mutation, preserve the preview and state the specific CLI or vault condition
that must be restored.

Completion: the user can identify the affected task and its current state
without reopening the full note.
