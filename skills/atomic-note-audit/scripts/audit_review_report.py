"""Read and update the review record carried by one Markdown report."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import html
from pathlib import PurePosixPath
import re
from urllib.parse import quote, unquote


FORMAT_VERSION = "1.0.0"
TABLE_HEADER = "| # | Priority | Note | Recommendation | Action taken |"
TABLE_SEPARATOR = "|---|---|---|---|---|"
RETIRED_NOTE_PREFIX = "Retired (verified deleted): "
TOKEN = r"[A-Za-z0-9_-]+"
HEADER = re.compile(r"<!-- atomic-note-audit:1\.0\.0 run=([^\s]+) scope=([^\s]+) -->")
ITEM = re.compile(rf"([1-9][0-9]*) <!-- item:({TOKEN}) -->")
ACTION = re.compile(rf"<!-- action:({TOKEN}) -->")
OUTCOME = re.compile(rf"<!-- outcome:({TOKEN}) action:({TOKEN}) -->")
OUTCOME_STATUSES = ("Pending", "Held", "Partial", "Declined", "Completed", "Unclassified")
SUMMARY_LABEL = "Current action outcomes:"
SUMMARY_PATTERN = re.compile(
    r"Current action outcomes: [0-9]+ outstanding; "
    + ", ".join(r"[0-9]+ " + status for status in OUTCOME_STATUSES) + r"\."
)


class ReviewError(ValueError):
    pass


@dataclass
class ReviewAction:
    id: str
    text: str


@dataclass
class ReviewOutcome:
    id: str
    action_id: str
    text: str


@dataclass
class ReviewItem:
    number: int
    identity: str
    priority: str
    note: str
    actions: list[ReviewAction] = field(default_factory=list)
    outcomes: list[ReviewOutcome] = field(default_factory=list)


@dataclass
class ReviewReport:
    run_id: str
    scope: str
    prefix: str
    items: list[ReviewItem]
    suffix: str = ""


def table_safe(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", "<br>")


def identity(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def note_link(path: str) -> str:
    _safe_path(path)
    label = re.sub(r"^\d{12,14}\s+", "", PurePosixPath(path).stem)
    label = re.sub(r"([\\`*_\[\]])", r"\\\1", html.escape(label))
    return f"[{table_safe(label)}](<{quote(path, safe='/')}>)"


def note_target(link: str) -> str:
    if link.startswith(RETIRED_NOTE_PREFIX):
        link = link[len(RETIRED_NOTE_PREFIX):]
    markdown = re.fullmatch(r"\[(?:\\.|[^\]])*\]\(<([^<>]+)>\)", link)
    if markdown:
        path = unquote(markdown[1])
    elif link.startswith("[[") and link.endswith("]]"):
        path = html.unescape(link[2:-2].replace(r"\|", "|")).split("|", 1)[0]
        if not path.endswith(".md"):
            path += ".md"
    else:
        raise ReviewError("Unrecognized note link; reconcile its intended target")
    _safe_path(path)
    return path


def _safe_path(path: str) -> None:
    if (not path or path.startswith("/") or "\\" in path or ":" in path
            or any(p in {".", "..", ""} for p in path.split("/")) or not path.endswith(".md")):
        raise ReviewError("Expected a vault-relative Markdown note path")


def split_cells(line: str) -> list[str]:
    """Split table syntax, leaving escaped pipes and all cell content intact."""
    cells, start = [], 0
    for index, char in enumerate(line):
        if char == "|" and (index == 0 or line[index - 1] != "\\"):
            cells.append(line[start:index].strip())
            start = index + 1
    cells.append(line[start:].strip())
    if len(cells) != 7 or cells[0] or cells[-1]:
        raise ReviewError("Expected exactly five table cells; reconcile ambiguous pipes or rows")
    return cells[1:-1]


def _segments(cell: str, pattern: re.Pattern[str], kind: str) -> list[tuple[tuple[str, ...], str]]:
    matches = list(pattern.finditer(cell))
    if not matches or cell[:matches[0].start()].strip():
        raise ReviewError(f"Missing {kind} identification; reconcile visible actions first")
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cell)
        text = cell[match.end():end].strip()
        if index + 1 < len(matches):
            text, count = re.subn(r"<br\s*/?>\s*$", "", text)
            if not count:
                raise ReviewError(f"Missing separator between {kind} entries")
        if not text or "<!--" in text or "-->" in text:
            raise ReviewError(f"Empty or damaged {kind} entry; reconcile the report")
        result.append((match.groups(), text.strip()))
    return result


def parse_report(text: str, *, run_id: str | None = None, scope: str | None = None) -> ReviewReport:
    headers = list(HEADER.finditer(text))
    if len(headers) != 1 or text.count("<!-- atomic-note-audit:") != 1:
        raise ReviewError("Missing or unsupported report identity/format; reconcile the report")
    actual_run, actual_scope = (unquote(v) for v in headers[0].groups())
    if (run_id is not None and actual_run != run_id) or (scope is not None and actual_scope != scope):
        raise ReviewError("Report run or selected scope does not match")
    lines = text.splitlines(keepends=True)
    table_indices = [i for i, line in enumerate(lines) if line.strip() == TABLE_HEADER]
    if len(table_indices) != 1:
        raise ReviewError("Expected one five-column action table; reconcile the report")
    start = table_indices[0]
    if start + 1 >= len(lines) or split_cells(lines[start + 1].strip()) != ["---"] * 5:
        raise ReviewError("Unsupported action table separator")
    items = []
    end = start + 2
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        number, priority, note, recommendations, outcomes = split_cells(lines[end].strip())
        matched = ITEM.fullmatch(number)
        if not matched or priority not in {"P0", "P1", "P2", "P3"}:
            raise ReviewError("Invalid item identity or priority; reconcile the report")
        note_target(note)
        item = ReviewItem(int(matched[1]), matched[2], priority, note)
        item.actions = [ReviewAction(ids[0], value) for ids, value in _segments(recommendations, ACTION, "action")]
        item.outcomes = [ReviewOutcome(*ids, value) for ids, value in _segments(outcomes, OUTCOME, "outcome")]
        items.append(item)
        end += 1
    report = ReviewReport(actual_run, actual_scope, "".join(lines[:start + 2]), items, "".join(lines[end:]))
    _validate_items(report)
    expected_counts = {"<!-- item:": len(items), "<!-- action:": sum(len(i.actions) for i in items),
                       "<!-- outcome:": sum(len(i.outcomes) for i in items)}
    for marker, count in expected_counts.items():
        if text.count(marker) != count:
            raise ReviewError("Orphan or damaged identification marker; reconcile the report")
    return report


def _validate_items(report: ReviewReport) -> None:
    numbers, identities, targets, events = set(), set(), set(), set()
    for item in report.items:
        target = note_target(item.note)
        if item.number in numbers or item.identity in identities or target in targets:
            raise ReviewError("Duplicate item identity or note target")
        numbers.add(item.number)
        identities.add(item.identity)
        targets.add(target)
        action_ids = [action.id for action in item.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ReviewError("Duplicate action identity")
        if set(action_ids) != {outcome.action_id for outcome in item.outcomes}:
            raise ReviewError("Orphan action or outcome identity")
        for outcome in item.outcomes:
            if outcome.id in events:
                raise ReviewError("Duplicate outcome identity")
            events.add(outcome.id)


def _current_summary(report: ReviewReport, *, include: bool) -> str:
    lines = report.prefix.splitlines(keepends=True)
    existing = [index for index, line in enumerate(lines) if line.startswith(SUMMARY_LABEL)]
    if len(existing) > 1 or any(not SUMMARY_PATTERN.fullmatch(lines[i].rstrip("\r\n")) for i in existing):
        raise ReviewError("Current action summary was edited; reconcile before updating")
    if not existing and not include:
        return report.prefix
    counts = dict.fromkeys(OUTCOME_STATUSES, 0)
    for item in report.items:
        latest = {outcome.action_id: outcome.text for outcome in item.outcomes}
        for action in item.actions:
            status = re.match(r"\*\*(Pending|Held|Partial|Declined|Completed)(?:\*\*| — )", latest[action.id])
            counts[status[1] if status else "Unclassified"] += 1
    outstanding = sum(counts[s] for s in ("Pending", "Held", "Partial", "Unclassified"))
    summary = f"{SUMMARY_LABEL} {outstanding} outstanding; " + ", ".join(
        f"{counts[s]} {s}" for s in OUTCOME_STATUSES) + ".\n"
    if existing:
        lines[existing[0]] = summary
    else:
        lines.insert(next(i for i, line in enumerate(lines) if line.strip() == TABLE_HEADER), summary + "\n")
    return "".join(lines)


def render_report(report: ReviewReport, *, include_summary: bool = False) -> str:
    rows = []
    for item in report.items:
        recommendations = "<br>".join(f"<!-- action:{a.id} -->{a.text}" for a in item.actions)
        outcomes = "<br>".join(f"<!-- outcome:{o.id} action:{o.action_id} -->{o.text}" for o in item.outcomes)
        rows.append(f"| {item.number} <!-- item:{item.identity} --> | {item.priority} | {item.note} | {recommendations} | {outcomes} |\n")
    text = _current_summary(report, include=include_summary) + "".join(rows) + report.suffix
    parse_report(text)
    return text


def new_report(run_id: str, scope: str, introduction: str, *, suffix: str = "\n") -> ReviewReport:
    if not run_id or not scope:
        raise ReviewError("Report run and scope identities are required")
    marker = f"<!-- atomic-note-audit:{FORMAT_VERSION} run={quote(run_id, safe='')} scope={quote(scope, safe='')} -->"
    prefix = introduction.rstrip() + f"\n{marker}\n\n{TABLE_HEADER}\n{TABLE_SEPARATOR}\n"
    return ReviewReport(run_id, scope, prefix, [], suffix)


def add_item(report: ReviewReport, path: str, priority: str, actions: list[tuple[str, str]]) -> ReviewItem:
    source_id = identity(path)
    item = next((i for i in report.items if note_target(i.note) == path), None)
    if item is None:
        if any(i.identity == source_id for i in report.items):
            raise ReviewError("Source path matches a historical identity at a different target; reconcile before regenerating")
        item = ReviewItem(max((i.number for i in report.items), default=0) + 1, source_id, priority, note_link(path))
        report.items.append(item)
    item.priority = priority
    for action_id, text in actions:
        old = next((a for a in item.actions if a.id == action_id), None)
        if old is not None:
            if old.text != table_safe(text):
                raise ReviewError("Recommendation text was edited; reconcile before regenerating")
            continue
        item.actions.append(ReviewAction(action_id, table_safe(text)))
        item.outcomes.append(ReviewOutcome(f"pending-{item.number}-{action_id}", action_id, "**Pending**"))
    return item
