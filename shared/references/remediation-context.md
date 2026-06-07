# Atomic Note Remediation Context

Audit and remediation are separate phases. Audit recommendations do not mutate notes.

## Obsidian-Aware Mutation

Use the official Obsidian skills and the actual Obsidian CLI binary for
link-sensitive file operations. Prefer `obsidian-cli` unless the environment
has verified that `obsidian` is the official CLI executable, not the GUI binary.
If the CLI cannot reach the running Obsidian app from an agent sandbox, stop and
ask for approved unsandboxed execution.

## Improve In Place

Improve one DAE note while preserving the file path unless a rename is explicitly approved.

## Split Multi-Note Files

Create proposed child notes, rebuild aliases and links, then delete the original only after approval and Obsidian-aware preflight.

## Rehome Non-DAE Notes

Recommend a better home by default. Do not move the note automatically.

## Delete Notes

Delete only from an approved remediation plan or explicit per-note approval.
Before approval, report the target path, Anki status, backlinks, intended CLI
delete command, link cleanup plan, and whether deletion is permanent. Deleting
without the CLI `permanent` flag uses the vault's configured Obsidian
`trashOption`; check the running app and report whether that means system trash,
Obsidian `.trash`, or permanent deletion. Permanent delete requires a separate
explicit approval.

If a note contains `TARGET DECK`, `START`, `END`, `Basic`, `Cloze`, or
Obsidian-to-Anki identifiers, stop for an Anki-specific decision before deleting
or splitting it.

## Audit Outputs

Timestamped audit reports, Bases, JSONL files, and manifests are immutable
historical artifacts by default. Remediation cleans live knowledge-graph files,
not prior audit outputs, unless the user explicitly asks for an audit artifact
correction.

## Duplicate And Overlap Review

Flag candidates only. Do not auto-merge.
