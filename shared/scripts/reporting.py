from __future__ import annotations

from typing import Iterable
from pathlib import Path
import re

from shared.scripts.finding_codes import FINDING_MESSAGES


PRIORITY_ORDER = ("P0", "P1", "P2", "P3")
NO_CHANGE_BUCKET = "no_change"
BUCKET_ORDER = PRIORITY_ORDER + (NO_CHANGE_BUCKET,)
PRIORITY_SECTION_TITLES = {
    "P0": "P0 Critical Remediation",
    "P1": "P1 High-Impact Remediation",
    "P2": "P2 Meaningful Improvements",
    "P3": "P3 Polish",
}
BUCKET_LABELS = {
    "P0": "P0",
    "P1": "P1",
    "P2": "P2",
    "P3": "P3",
    NO_CHANGE_BUCKET: "No changes",
}


def render_markdown_report(
    rows: Iterable[dict[str, object]],
    manifest: dict[str, object],
) -> str:
    if manifest.get("schema_version") == "2.0.0":
        return _render_model_led_report(list(rows), manifest)
    sorted_rows = sorted(list(rows), key=_row_sort_key)
    total_notes = _int_or_default(manifest.get("total_notes"), len(sorted_rows))
    no_change_notes = sum(1 for row in sorted_rows if _bucket_key(row) == NO_CHANGE_BUCKET)
    average_score = _average_score(sorted_rows)
    priority_counts = _priority_counts(sorted_rows, manifest)
    reviewed_models = sum(1 for row in sorted_rows if row.get("model_judgment") is not None)
    pending_models = sum(1 for row in sorted_rows if row.get("pending_model") is True)

    lines = [
        "# Atomic Note Audit",
        "",
        "## Summary",
        "",
        f"- Run ID: {manifest.get('run_id', 'unknown')}",
        f"- Total notes: {total_notes}",
        f"- Average score: {average_score}",
        f"- No-change notes: {no_change_notes} / {total_notes} ({_percentage(no_change_notes, total_notes)})",
        "- Bucket counts: "
        + ", ".join(
            f"{BUCKET_LABELS[bucket]} {priority_counts[bucket]}" for bucket in BUCKET_ORDER
        ),
        _model_judgment_summary(reviewed_models, pending_models, total_notes),
    ]

    for priority in PRIORITY_ORDER:
        lines.extend(
            _section(
                PRIORITY_SECTION_TITLES[priority],
                [
                    row
                    for row in sorted_rows
                    if _bucket_key(row) == priority
                ],
            )
        )

    lines.extend(_section("No Changes", [row for row in sorted_rows if _bucket_key(row) == NO_CHANGE_BUCKET]))
    lines.extend(_section("Factual-Risk Notes", [row for row in sorted_rows if _is_factual_risk(row)]))
    lines.extend(
        _section(
            "Duplicate Or Overlap Candidates",
            [row for row in sorted_rows if _has_finding(row, "duplicate_overlap")],
        )
    )
    lines.extend(
        [
            "",
            "## Remediation Next Steps",
            "",
            f"- Resolve P0 critical remediation first: {_note_count(priority_counts['P0'])}.",
            f"- Work P1 high-impact remediation next: {_note_count(priority_counts['P1'])}.",
            f"- Review P2 improvements after blockers are clear: {_note_count(priority_counts['P2'])}.",
            f"- Keep P3 polish as low-risk cleanup: {_note_count(priority_counts['P3'])}.",
            f"- Leave no-change notes alone unless a later audit finds new issues: {_note_count(priority_counts[NO_CHANGE_BUCKET])}.",
            f"- Fact-check factual-risk notes before relying on them: "
            f"{_note_count(sum(1 for row in sorted_rows if _is_factual_risk(row)))}.",
            f"- Review duplicate or overlap candidates before rewriting related notes: "
            f"{_note_count(sum(1 for row in sorted_rows if _has_finding(row, 'duplicate_overlap')))}.",
        ]
    )
    return "\n".join(lines) + "\n"


def _model_judgment_summary(reviewed: int, pending: int, total: int) -> str:
    if reviewed == 0 and pending == 0:
        return "- Model judgment: not run; deterministic audit complete"
    return f"- Model judgment coverage: {reviewed} / {total} reviewed; {pending} pending"


def _section(title: str, rows: list[dict[str, object]]) -> list[str]:
    lines = ["", f"## {title}", ""]
    if not rows:
        lines.append("- None")
        return lines
    lines.extend(
        [
            "| Note | Score | Clean | Findings | Recommendations |",
            "|---|---:|:---:|---|---|",
        ]
    )
    lines.extend(_note_table_row(row) for row in rows)
    return lines


def _note_table_row(row: dict[str, object]) -> str:
    note_link = str(row.get("note_link") or row.get("note_path") or "Unknown note")
    score = row.get("score")
    score_text = str(score) if isinstance(score, int) else "n/a"
    clean_text = "yes" if row.get("clean") is True else "no"
    return (
        f"| {_escape_table_cell(note_link)} "
        f"| {_escape_table_cell(score_text)} "
        f"| {_escape_table_cell(clean_text)} "
        f"| {_escape_table_cell(_format_findings(row.get('findings')))} "
        f"| {_escape_table_cell(_format_recommendations(row.get('recommendations')))} |"
    )


def _format_findings(findings: object) -> str:
    if not isinstance(findings, list) or not findings:
        return "none"
    rendered: list[str] = []
    for finding in findings:
        if isinstance(finding, dict):
            code = str(finding.get("code") or "unknown")
            message = str(finding.get("message") or "")
            rendered.append(f"{code}: {message}" if message else code)
        else:
            rendered.append(str(finding))
    return "<br>".join(rendered)


def _format_recommendations(recommendations: object) -> str:
    if not isinstance(recommendations, list) or not recommendations:
        return "none"
    rendered: list[str] = []
    for recommendation in recommendations:
        if isinstance(recommendation, dict):
            mode = str(recommendation.get("mode") or "recommendation")
            message = str(recommendation.get("message") or "")
            rendered.append(f"{mode}: {message}" if message else mode)
        else:
            rendered.append(str(recommendation))
    return "<br>".join(rendered)


def _escape_table_cell(value: str) -> str:
    return value.replace("\n", "<br>").replace("|", r"\|")


def _priority_counts(
    rows: list[dict[str, object]],
    manifest: dict[str, object],
) -> dict[str, int]:
    counts = {priority: 0 for priority in BUCKET_ORDER}
    manifest_counts = manifest.get("priority_counts")
    if isinstance(manifest_counts, dict):
        for priority in BUCKET_ORDER:
            counts[priority] = _int_or_default(manifest_counts.get(priority), 0)
        return counts
    for row in rows:
        counts[_bucket_key(row)] += 1
    return counts


def _row_sort_key(row: dict[str, object]) -> tuple[int, int, str]:
    priority = _bucket_key(row)
    score = row.get("score")
    score_sort = score if isinstance(score, int) else 101
    return (
        BUCKET_ORDER.index(priority),
        score_sort,
        str(row.get("note_path") or row.get("note_link") or ""),
    )


def _bucket_key(row: dict[str, object]) -> str:
    priority = row.get("priority")
    if priority is None:
        return NO_CHANGE_BUCKET
    text = str(priority)
    if text not in PRIORITY_ORDER:
        raise ValueError(f"Unexpected priority value: {text!r}")
    return text


def _has_finding(row: dict[str, object], code: str) -> bool:
    findings = row.get("findings")
    if not isinstance(findings, list):
        return False
    return any(isinstance(finding, dict) and finding.get("code") == code for finding in findings)


def _is_factual_risk(row: dict[str, object]) -> bool:
    return (
        row.get("factual_risk") is True
        or row.get("fact_check_required") is True
        or _has_finding(row, "factual_risk")
    )


def _int_or_default(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def _average_score(rows: list[dict[str, object]]) -> str:
    scores = [row["score"] for row in rows if isinstance(row.get("score"), int)]
    if not scores:
        return "n/a"
    return f"{sum(scores) / len(scores):.1f} / 100"


def _note_count(count: int) -> str:
    return f"{count} note" if count == 1 else f"{count} notes"


def _plain(value: object) -> str:
    text = " ".join(str(value).split())
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", text)


def _quality_action(code: str) -> str:
    short_actions = {
        "title_body_mismatch": "Align the filename, title and Definition.",
        "dae_sentence_case": "Capitalize the first visible letter of the affected DAE sentence.",
        "factual_risk": "Verify the flagged claim against its source.",
    }
    return short_actions.get(code, FINDING_MESSAGES[code])


def _model_led_actions(row: dict[str, object]) -> list[str]:
    checks = [c for c in row["integrity_checks"] if c["status"] == "failed"]
    exact_codes = {"frontmatter": "missing_frontmatter", "parent_link": "missing_parent",
                   "card_markers": "malformed_anki", "literal_corruption": "decayed_latex_command"}
    represented = {exact_codes.get(c["code"]) for c in checks}
    actions = []
    for finding in row["findings"]:
        if finding["code"] in represented:
            continue
        action = _quality_action(finding["code"])
        reason = finding["message"]
        label = "Fact-check pending" if finding["code"] == "factual_risk" else "Note quality"
        suffix = "" if reason == action else " " + _plain(reason)
        actions.append(f"**{_plain(action)}** {label}.{suffix}")
    for check in checks:
        label = "Anki integrity" if check["source"] == "anki" else "Exact integrity check"
        actions.append(f"**{_plain(check['message'])}** {label}.")
    return list(dict.fromkeys(actions))


def _render_model_led_report(rows: list[dict[str, object]], manifest: dict[str, object]) -> str:
    rows = sorted(rows, key=_row_sort_key)
    coverage = manifest["model_coverage"]
    total = manifest["total_notes"]
    unfinished = total - coverage["reviewed"]
    queue = [row for row in rows if row.get("priority") in PRIORITY_ORDER]
    unchanged = sum(row["review_status"] == "reviewed" and row["clean"] and row["priority"] is None for row in rows)
    counts = {p: sum(row["priority"] == p for row in queue) for p in PRIORITY_ORDER}
    if queue:
        first = next(p for p in PRIORITY_ORDER if counts[p])
        first_actions = []
        for row in queue:
            if row["priority"] == first:
                first_actions.extend(c["message"] for c in row["integrity_checks"] if c["status"] == "failed" and c["priority"] == first)
                first_actions.extend(_quality_action(f["code"]) for f in row["findings"])
        actions = list(dict.fromkeys(first_actions))
        recommendation = " ".join(_plain(a) for a in actions[:2])
        recommendation += f" Start with {first} ({_note_count(counts[first])}), then work through the remaining priority buckets."
        if unfinished:
            recommendation += f" Finish model review for {unfinished} notes before treating this audit as complete."
    elif unfinished:
        recommendation = f"Finish model review for {unfinished} notes before drawing a conclusion."
    else:
        recommendation = "No actions were identified in the completed review and checks."
    lines = ["# Atomic note audit", "", "## Recommendation", "", recommendation,
             "", "## Coverage", "", f"{coverage['reviewed']} / {total} model-reviewed. {len(queue)} need action; {unchanged} need no changes."]
    states = [f"{coverage[s]} {s}" for s in ("pending", "failed", "unavailable", "stale") if coverage[s]]
    if states:
        lines.append("Unfinished: " + "; ".join(states) + ".")
    pending_facts = sum(bool(row["fact_check_required"]) for row in rows)
    if pending_facts:
        lines.append(f"Fact-checks pending: {pending_facts}; model review does not verify those claims.")
    anki = manifest["integrity_coverage"].get("anki", {})
    checked = anki.get("passed", 0) + anki.get("failed", 0)
    lines.append(f"Anki: {checked} / {total} checked; {anki.get('not_checked', total)} not checked.")
    if not counts["P0"]:
        lines.extend(["", "P0 - Critical: none identified in completed checks."])
    titles = {"P0": "Critical", "P1": "Fix first", "P2": "Improve next", "P3": "Optional polish"}
    for priority in PRIORITY_ORDER:
        entries = [row for row in queue if row["priority"] == priority]
        if not entries:
            continue
        lines.extend(["", f"## {priority} - {titles[priority]}", ""])
        for row in entries:
            lines.append(f"- {row['note_link']}")
            for action in _model_led_actions(row):
                lines.append(f"  - {action}")
            if row["review_status"] != "reviewed":
                lines.append(f"  - Model review {row['review_status']}; quality is unscored.")
    decisions = manifest.get("decisions", [])
    if decisions:
        links = {row["note_path"]: row["note_link"] for row in rows}
        lines.extend(["", "## Recorded decisions", ""])
        for decision in decisions:
            label = "Completed" if decision["status"] == "completed" else "Held"
            lines.append(f"- {label}: {links[decision['note_path']]} - {_plain(decision['message'])}")
    evidence = manifest.get("outputs", {}).get("evidence")
    if evidence:
        path = Path(str(evidence))
        link = path.resolve().as_uri() if path.is_absolute() else path.as_posix().replace(" ", "%20")
        lines.extend(["", f"[Supporting evidence](<{link}>)"])
    return "\n".join(lines) + "\n"
