# Audit review record

Read this before publishing an audit or processing selected item numbers.
Run commands from the skill root. Repository module commands below become
equivalent `scripts/*.py` commands in the self-contained installed copy.

## The report owns the record

Publish one `<YYYYMMDDHHMM> Atomic note audit.md` directly under the configured
`audit_output_folder`. Resolve the user's local time and capture it once. The
publisher's standalone fallback is the machine's local time. On refresh, select
the existing report path and retain its timestamp and location.

Use exactly one table with `#`, `Priority`, `Note`, `Recommendation`, and
`Action taken` columns, sorted P0 through P3. Item numbers belong to one audit;
reordering does not renumber them. Keep old rows and action history so retired
numbers remain reserved. Approved renames change the current note target while
preserving identity. New findings do not inherit earlier completion.

The Markdown file is the durable source of truth. Working JSON, drafts, raw
logs, and snapshots stay external by default and may be discarded. No persistent
configurable external review-state directory is required. The report must carry
the visible recommendations, dated outcomes, attribution, and verification
summaries needed to resume. A link to temporary evidence is optional; it cannot
replace that summary. Deleted raw audit evidence stays unavailable.

## Identification format

The report format is `1.0.0`. Hidden comments contain IDs and format information
only. They do not hold another copy of recommendations or outcomes. For example:

```markdown
<!-- atomic-note-audit:1.0.0 run=synthetic-run scope=selected%3Asynthetic -->
| # | Priority | Note | Recommendation | Action taken |
|---|---|---|---|---|
| 1 <!-- item:example-note --> | P2 | [Example](<Atomic%20Notes/Example.md>) | <!-- action:example -->Add a computed example. | <!-- outcome:pending-example action:example -->**Pending** |
```

Run and scope identities are URL-encoded. Item, action, and outcome IDs contain
letters, digits, underscores, or hyphens. Item numbers are positive; item and
outcome IDs are unique within the report, while action IDs are unique within an
item. Each action has an outcome, initially pending. Use `<br>` between entries
in one cell. Escape table pipes with `\|`, including inside code and math.
The [GFM table syntax](https://github.github.com/gfm/#tables-extension-)
defines pipe escaping before inline parsing; preserve existing backslashes.
Encoded Markdown destinations handle paths that cannot be represented reliably
as wikilinks. Verify the actual target in the app before claiming publication.

`audit_review_report.py` parses the report without the original audit manifest.
It preserves visible text and learner prose, and rejects duplicate/orphan IDs,
ambiguous cells, unsupported format, or wrong run/scope. Never infer a missing
association from row order or silently replace existing item numbers.

For an older selected report without markers, read its visible numbered table,
map each recommendation and recorded outcome explicitly, and add identification
comments without changing visible substance or numbers. Compare the before/after
visible content and link targets. Ask the learner about ambiguous mappings. Keep
unknown historical dates or proof explicitly unknown; a legacy completion claim
cannot close a newly flagged action. Do not migrate unselected old reports.

## Prepare a new report

Use matching validated model-led results and manifest:

```bash
python3 scripts/generate_report.py --jsonl "$EVIDENCE/results.jsonl" --manifest "$EVIDENCE/manifest.json" --output "$DRAFT"
python3 scripts/publish_audit_report.py --vault "$VAULT_NAME" --draft "$DRAFT" --timestamp 203001020304
```

Replace the synthetic timestamp with the captured user-local value. `DRAFT` is an
external file. The publisher reads app configuration through the app; an explicit
`--output-folder` must agree with an existing configured folder. Existing
destinations are preserved, including collisions within the same minute.

The generator writes filesystem drafts. Do not target an app-required live vault
with it. The publisher uses the verified official CLI and `ObsidianAdapter`, and
has no filesystem fallback for vault writes. Its temporary payload file avoids
command argument-size limits; the caller and desktop app need shared local file
access. Only the intended report and missing output folders can be created.

## Resume and record selected outcomes

Read the current report through app-context tooling first. A Python example for
exporting a fresh external snapshot from the repository or installed skill root:

```python
import os
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
from obsidian_adapter import ObsidianAdapter

text = ObsidianAdapter().read_note(os.environ["REPORT_PATH"], vault=os.environ["VAULT_NAME"])
Path(os.environ["REPORT_SNAPSHOT"]).write_text(text, encoding="utf-8")
```

Resolve the requested item and action IDs from that snapshot. Read the remediation
context before source/card operations; a report or recorder grants no new approval.
Held/declined decisions require neither a provider call nor an Anki lookup.

Prepare an external outcome JSON. A completion example, whose evidence must come
from actual approved work rather than copied placeholder assertions:

```json
{
  "run_id": "synthetic-run",
  "item": 1,
  "action_id": "example",
  "event_id": "verified-example-20300102",
  "status": "Completed",
  "timestamp": "2030-01-02T03:04:00+00:00",
  "description": "Added the computed example and checked its result.",
  "actor": "Learner-approved agent",
  "approval_ref": "Learner approved this example repair.",
  "verification": {
    "source": {"status": "passed", "detail": "Read back the exact approved text and checked the computation."},
    "links": {"status": "passed", "detail": "The note and parent targets resolve."},
    "anki": {"status": "not_applicable", "detail": "This action changes no card content or identifiers."}
  }
}
```

Statuses are `Pending`, `Held`, `Declined`, `Partial`, and `Completed`. Every new
entry needs a date/time with offset, description, actor, and stable event ID.
Completion requires approval, a passed source check, and explicit link/Anki checks
that passed or are justified as not applicable. Failed or unchecked integration
cannot become completion. Partial work needs verified progress and a nonempty
`remaining_checks` list. Held/declined entries need a decision/reason, not invented
verification. Verification details remain visible in `Action taken`.

After an approved verified rename, include `previous_path` and `rename_to` to
update the report link without changing its item identity. This records a rename;
it does not perform one. The links check must establish the new intended target.

```bash
python3 scripts/record_audit_outcome.py --report-snapshot "$REPORT_SNAPSHOT" --event "$EVENT_JSON" --draft "$DRAFT"
python3 scripts/publish_audit_report.py --vault "$VAULT_NAME" --draft "$DRAFT" --report-path "$REPORT_PATH" --expected-snapshot "$REPORT_SNAPSHOT"
```

The recorder changes only an external draft and calls no source/card mutation
tool or model. A repeated event ID with identical content is a no-op; reuse for
different content is refused. To regenerate against available original audit
artifacts, pass `--existing-report "$REPORT_SNAPSHOT"` to `generate_report.py`
with a model-led schema 2.0.0 manifest. Legacy deterministic generation rejects
this option rather than ignoring the selected report. Coverage summaries are
refreshed only when their complete generated lines remain recognizable; an
inline learner annotation requires reconciliation before regeneration.
Without those artifacts, selected-item recording still works from the report.

## Safe publication and recovery

Valid manual edits already present are authoritative input. The publisher checks
the expected text inside `app.vault.process`, so an edit after the read stops the
write. Preserve the current report and reconcile ambiguous content instead of
overwriting it from an older cache or draft. Keep recommendation and outcome
content visible when markers are damaged; never trust hidden text over it.

Only confirmed content readback and intended link resolution establish a durable
report update. A transport denial, timeout, malformed acknowledgement, or readback
mismatch is a failed or uncertain publication. Inspect the actual report before
retrying. A source/card change may already have happened even when its outcome is
absent from the report: inspect actual source/card state, then reconcile the
record. Do not blindly rerun that mutation or claim temporary JSON is durable.
