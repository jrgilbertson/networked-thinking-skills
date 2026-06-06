from __future__ import annotations

import json
from pathlib import Path


VIEW_ORDER = (
    "All Audited Notes",
    "P0 Critical",
    "P1 High Impact",
    "P2 Improvements",
    "P3 Polish",
    "Clean Notes",
    "Factual Risk",
    "Multi-Note Split Candidates",
    "Missing Parent Candidates",
    "Duplicate Or Overlap Candidates",
)


def render_base(jsonl_path: str) -> str:
    path = Path(jsonl_path)
    rows = sorted(_read_jsonl(path), key=lambda row: str(row.get("note_path") or ""))
    view_rows = {
        "All Audited Notes": rows,
        "P0 Critical": [row for row in rows if row.get("priority") == "P0"],
        "P1 High Impact": [row for row in rows if row.get("priority") == "P1"],
        "P2 Improvements": [row for row in rows if row.get("priority") == "P2"],
        "P3 Polish": [row for row in rows if row.get("priority") == "P3"],
        "Clean Notes": [row for row in rows if row.get("clean") is True],
        "Factual Risk": [row for row in rows if _is_factual_risk(row)],
        "Multi-Note Split Candidates": [row for row in rows if _has_finding(row, "multi_note_file")],
        "Missing Parent Candidates": [row for row in rows if _has_finding(row, "missing_parent")],
        "Duplicate Or Overlap Candidates": [
            row for row in rows if _has_finding(row, "duplicate_overlap")
        ],
    }

    lines = [
        "# Generated from validated audit JSONL. This Base is a derived triage view, not source of truth.",
        "formulas:",
        f"  source_jsonl: {_yaml_single_quoted(json.dumps(str(path)))}",
        "properties:",
        "  formula.source_jsonl:",
        '    displayName: "Source JSONL"',
        "  file.path:",
        '    displayName: "Note Path"',
        "views:",
    ]
    for view_name in VIEW_ORDER:
        lines.extend(_view_lines(view_name, view_rows[view_name]))
    return "\n".join(lines) + "\n"


def _view_lines(view_name: str, rows: list[dict[str, object]]) -> list[str]:
    lines = [
        "  - type: table",
        f"    name: {json.dumps(view_name)}",
        "    filters:",
    ]
    filters = _path_filters(rows)
    if len(filters) == 1:
        lines.extend(["      and:", f"        - {_yaml_single_quoted(filters[0])}"])
    else:
        lines.append("      or:")
        lines.extend(f"        - {_yaml_single_quoted(filter_text)}" for filter_text in filters)
    lines.extend(
        [
            "    order:",
            "      - file.name",
            "      - file.path",
            "      - formula.source_jsonl",
        ]
    )
    return lines


def _path_filters(rows: list[dict[str, object]]) -> list[str]:
    note_paths = [str(row["note_path"]) for row in rows if isinstance(row.get("note_path"), str)]
    if not note_paths:
        return ['file.path == "__no_matching_audit_rows__"']
    return [f'file.path == "{note_path}"' for note_path in note_paths]


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


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


def _yaml_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
