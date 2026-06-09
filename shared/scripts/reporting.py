from __future__ import annotations

from typing import Iterable


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
    return text if text in PRIORITY_ORDER else "P3"


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
