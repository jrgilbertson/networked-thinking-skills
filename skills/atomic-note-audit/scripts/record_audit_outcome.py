"""Prepare a report-only outcome update from an external report snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from audit_review_report import (
    TOKEN, RETIRED_NOTE_PREFIX, ReviewError, ReviewOutcome, note_link, note_target, parse_report, render_report, table_safe,
)


STATUSES = {"Pending", "Held", "Declined", "Partial", "Completed"}


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{label} must be a nonempty string")
    return value.strip().replace("<!--", "&lt;!--").replace("-->", "--&gt;")


def prepare_outcome(report_text: str, event: dict[str, object]) -> str:
    if not isinstance(event, dict):
        raise ReviewError("Outcome input must be an object")
    run_id = _text(event.get("run_id"), "run_id")
    report = parse_report(report_text, run_id=run_id)
    number = event.get("item")
    if type(number) is not int:
        raise ReviewError("item must be an integer")
    item = next((i for i in report.items if i.number == number), None)
    if item is None:
        raise ReviewError("Unknown item number")
    action_id = event.get("action_id")
    if not isinstance(action_id, str) or action_id not in {a.id for a in item.actions}:
        raise ReviewError("Unknown action ID")
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or re.fullmatch(TOKEN, event_id) is None:
        raise ReviewError("event_id must contain only letters, numbers, underscores or hyphens")
    status = event.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        raise ReviewError("Unknown outcome status")
    timestamp = _text(event.get("timestamp"), "timestamp")
    try:
        parsed_time = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ReviewError("timestamp must be an ISO date and time with offset") from exc
    if parsed_time.utcoffset() is None:
        raise ReviewError("timestamp requires a timezone offset")
    description = _text(event.get("description"), "description")
    actor = _text(event.get("actor"), "actor")
    approval = event.get("approval_ref", "")
    if not isinstance(approval, str):
        raise ReviewError("approval_ref must be a string")
    verification = event.get("verification", {})
    if not isinstance(verification, dict) or set(verification) - {"source", "links", "anki"}:
        raise ReviewError("verification accepts source, links and anki checks")
    checks = []
    for name in ("source", "links", "anki"):
        if name not in verification:
            continue
        check = verification[name]
        if not isinstance(check, dict) or set(check) != {"status", "detail"}:
            raise ReviewError("Each verification check requires status and detail")
        if not isinstance(check["status"], str) or check["status"] not in {"passed", "failed", "not_applicable", "not_checked"}:
            raise ReviewError("Invalid verification check status")
        checks.append(f"{name} {check['status']} — {_text(check['detail'], 'verification detail')}")
    remaining = event.get("remaining_checks", [])
    if not isinstance(remaining, list) or any(not isinstance(v, str) or not v.strip() for v in remaining):
        raise ReviewError("remaining_checks must be an array of nonempty strings")
    if status == "Completed":
        if not approval.strip() or set(verification) != {"source", "links", "anki"}:
            raise ReviewError("Completion requires approval and source/link/Anki verification")
        if any(c["status"] not in {"passed", "not_applicable"} for c in verification.values()) or remaining:
            raise ReviewError("Unverified checks or remaining work cannot become completion")
        if verification["source"]["status"] != "passed":
            raise ReviewError("Completion requires a verified source result")
    if status == "Partial" and (not remaining or not any(c["status"] == "passed" for c in verification.values())):
        raise ReviewError("Partial work requires verified progress and remaining checks")
    text = f"**{status} — {timestamp}** {description}<br>Actor: {actor}."
    if approval.strip():
        text += f" Approval: {_text(approval, 'approval_ref')}."
    if checks:
        text += "<br>Verification: " + "; ".join(checks) + "."
    if remaining:
        text += "<br>Remaining: " + "; ".join(_text(v, "remaining check") for v in remaining)
    rename_to = event.get("rename_to")
    retire_target = event.get("retire_target", False)
    if type(retire_target) is not bool:
        raise ReviewError("retire_target must be a boolean")
    if retire_target:
        if status != "Completed" or rename_to is not None:
            raise ReviewError("Retirement requires a verified approved deletion, separate from a rename")
        previous = _text(event.get("previous_path"), "previous_path")
        if note_target(item.note) != previous:
            raise ReviewError("Retirement receipt does not match the report's note target")
        text += f"<br>Recorded retirement: {previous}."
    if rename_to is not None:
        if status != "Completed":
            raise ReviewError("A report target changes only after a verified approved rename")
        previous = _text(event.get("previous_path"), "previous_path")
        new_link = note_link(_text(rename_to, "rename_to"))
        if note_target(item.note) not in {previous, rename_to}:
            raise ReviewError("Rename receipt does not match the report's note target")
        text += f"<br>Recorded rename: {previous} → {rename_to}."
    text = table_safe(text)
    for owner in report.items:
        for old in owner.outcomes:
            if old.id == event_id:
                if owner.number != number or old.action_id != action_id or old.text != text:
                    raise ReviewError("Outcome ID was reused for different content")
                return report_text
    item.outcomes.append(ReviewOutcome(event_id, action_id, text))
    if rename_to is not None:
        item.note = new_link
    elif retire_target:
        item.note = RETIRED_NOTE_PREFIX + note_link(previous)
    return render_report(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare an outcome draft; publication through Obsidian is a separate step.")
    parser.add_argument("--report-snapshot", type=Path, required=True, help="Fresh external app-exported Markdown snapshot")
    parser.add_argument("--event", type=Path, required=True, help="Structured outcome JSON")
    parser.add_argument("--draft", type=Path, required=True, help="External Markdown draft, distinct from inputs")
    args = parser.parse_args(argv)
    try:
        if args.draft.resolve() in {args.report_snapshot.resolve(), args.event.resolve()}:
            raise ReviewError("Draft must not overwrite an input")
        text = args.report_snapshot.read_text(encoding="utf-8")
        event = json.loads(args.event.read_text(encoding="utf-8"))
        result = prepare_outcome(text, event)
        args.draft.parent.mkdir(parents=True, exist_ok=True)
        args.draft.write_text(result, encoding="utf-8")
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(str(args.draft))
    print("Prepared only; outcome is durable after verified report publication.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
