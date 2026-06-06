from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

from shared.scripts.config import resolve_config
from shared.scripts.markdown_parse import (
    analyze_dae,
    count_rendered_words,
    count_anki_blocks,
    extract_structural_heading_lines,
    extract_frontmatter,
    extract_wikilinks,
)
from shared.scripts.scoring import compute_clean, compute_final_score, highest_priority


VERSION = "1.0.0"
DETERMINISTIC_FIXTURE_TIMESTAMP = "2000-01-01T00:00:00Z"
DIMENSION_NAMES = (
    "structure",
    "atomicity",
    "dae_quality",
    "clarity",
    "connections",
    "metadata_card_safety",
)
FINDING_MESSAGES = {
    "missing_frontmatter": "Add YAML frontmatter with the note's metadata.",
    "missing_dae": "Add complete Definition, Analogy, and Example sections.",
    "definition_too_long": "Shorten the Definition to 10-50 rendered words.",
    "missing_parent": "Link this note from a structure note.",
    "malformed_anki": "Balance START and END markers for Anki card blocks.",
    "multi_note_file": "Split bundled ideas into separate atomic notes.",
    "misfiled_reference": "Move source-material notes out of Atomic Notes or rewrite them as DAE notes.",
    "weak_dae": "Strengthen the DAE content with concrete, self-contained explanations.",
    "factual_risk": "Mark the universal claim for fact checking before treating it as reliable.",
    "duplicate_overlap": "Review this note against related notes for possible overlap.",
}
RECOMMENDATION_MODES = {
    "missing_frontmatter": "improve-in-place",
    "missing_dae": "improve-in-place",
    "definition_too_long": "improve-in-place",
    "missing_parent": "link-parent",
    "malformed_anki": "improve-in-place",
    "multi_note_file": "split-multi-note",
    "misfiled_reference": "rehome-non-DAE",
    "weak_dae": "improve-in-place",
    "factual_risk": "mark-factual-risk",
    "duplicate_overlap": "duplicate-overlap-review",
}
DIMENSION_PENALTIES = {
    "missing_frontmatter": {"structure": 20, "metadata_card_safety": 40},
    "missing_dae": {"structure": 35, "dae_quality": 60, "clarity": 20},
    "definition_too_long": {"structure": 20, "dae_quality": 35, "clarity": 25},
    "missing_parent": {"connections": 60},
    "malformed_anki": {"metadata_card_safety": 50, "clarity": 10},
    "multi_note_file": {"structure": 30, "atomicity": 70, "clarity": 20},
    "misfiled_reference": {"structure": 30, "atomicity": 40, "dae_quality": 50},
    "weak_dae": {"dae_quality": 25, "clarity": 15},
    "factual_risk": {"clarity": 20, "metadata_card_safety": 10},
    "duplicate_overlap": {"atomicity": 25, "clarity": 10, "connections": 10},
}
UNIVERSAL_CLAIM_RE = re.compile(
    r"\b(all|always|every|everyone)\b",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)


def audit_vault(
    vault_root: Path,
    *,
    run_id: str,
    deterministic_fixture_output: bool = False,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    vault_root = Path(vault_root)
    config = resolve_config(vault_root)
    fixture_timestamp = DETERMINISTIC_FIXTURE_TIMESTAMP if deterministic_fixture_output else None
    started_at = fixture_timestamp or _utc_now()

    atomic_folder = vault_root / str(config["atomic_notes_folder"])
    structure_targets = _load_structure_targets(vault_root / str(config["structure_notes_folder"]))
    note_paths = sorted(atomic_folder.rglob("*.md"), key=lambda path: _relative_posix(path, vault_root))

    rows = [
        _audit_note(
            path,
            vault_root=vault_root,
            run_id=run_id,
            config=config,
            structure_targets=structure_targets,
            modified_time=fixture_timestamp or _timestamp_from_path(path),
        )
        for path in note_paths
    ]
    ended_at = fixture_timestamp or _utc_now()
    manifest = _build_manifest(rows, run_id=run_id, config=config, started_at=started_at, ended_at=ended_at)
    return rows, manifest


def _audit_note(
    path: Path,
    *,
    vault_root: Path,
    run_id: str,
    config: dict[str, object],
    structure_targets: set[str],
    modified_time: str,
) -> dict[str, object]:
    content = path.read_text(encoding="utf-8")
    relative_path = _relative_posix(path, vault_root)
    findings = _findings_for_note(path, content, structure_targets)
    dimensions = _dimensions_for_findings(findings)
    fact_check_required = any(finding["code"] == "factual_risk" for finding in findings)
    score = compute_final_score(dimensions, findings)

    row: dict[str, object] = {
        "schema_version": VERSION,
        "run_id": run_id,
        "row_status": "complete",
        "note_path": relative_path,
        "note_link": f"[[{path.stem}]]",
        "content_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "modified_time": modified_time,
        "score": score,
        "priority": highest_priority(findings) or "P3",
        "clean": compute_clean(
            score,
            findings,
            pending_model=False,
            fact_check_required=fact_check_required,
        ),
        "pending_model": False,
        "dimensions": dimensions,
        "findings": findings,
        "recommendations": _recommendations_for_findings(findings),
        "model_judgment": None,
        "cache_status": "none",
        "factual_risk": fact_check_required,
        "fact_check_required": fact_check_required,
        "config_snapshot": dict(config),
        "doctrine_version": VERSION,
        "rubric_version": VERSION,
        "prompt_version": VERSION,
    }
    if fact_check_required:
        row["factual_risk_reason"] = "Contains broad universal language that needs verification."
    return row


def _findings_for_note(
    path: Path,
    content: str,
    structure_targets: set[str],
) -> list[dict[str, str]]:
    frontmatter, body = extract_frontmatter(content)
    dae_analysis = analyze_dae(content)
    has_dae = dae_analysis.present
    anki_counts = count_anki_blocks(content)
    finding_specs: list[tuple[str, str]] = []

    if frontmatter is None:
        finding_specs.append(("missing_frontmatter", "P1"))
    if not has_dae:
        if dae_analysis.definition_too_long:
            finding_specs.append(("definition_too_long", "P1"))
        else:
            finding_specs.append(("missing_dae", "P1"))
    if path.stem not in structure_targets:
        finding_specs.append(("missing_parent", "P1"))
    if anki_counts["START"] != anki_counts["END"]:
        finding_specs.append(("malformed_anki", "P1"))
    if _looks_like_multi_note(content, anki_counts):
        finding_specs.append(("multi_note_file", "P0"))
    if _looks_like_reference_note(frontmatter, body, has_dae):
        finding_specs.append(("misfiled_reference", "P1"))
    if _looks_like_weak_dae(body, has_dae, dae_analysis.definition_too_long):
        finding_specs.append(("weak_dae", "P2"))
    if _contains_factual_risk(body):
        finding_specs.append(("factual_risk", "P2"))
    if _looks_like_duplicate_candidate(path, body):
        finding_specs.append(("duplicate_overlap", "P2"))

    return [
        {
            "priority": priority,
            "code": code,
            "message": FINDING_MESSAGES[code],
        }
        for code, priority in finding_specs
    ]


def _load_structure_targets(structure_folder: Path) -> set[str]:
    targets: set[str] = set()
    if not structure_folder.exists():
        return targets
    for path in sorted(structure_folder.rglob("*.md")):
        for target in extract_wikilinks(path.read_text(encoding="utf-8")):
            normalized = _normalize_wikilink_target(target)
            if normalized:
                targets.add(normalized)
    return targets


def _normalize_wikilink_target(target: str) -> str:
    target = target.split("#", 1)[0].strip()
    if not target:
        return ""
    if target.endswith(".md"):
        target = target[:-3]
    return PurePosixPath(target).stem


def _looks_like_multi_note(markdown: str, anki_counts: dict[str, int]) -> bool:
    complete_blocks = min(anki_counts["START"], anki_counts["END"])
    if complete_blocks > 1:
        return True
    top_level_headings = [
        heading
        for _, level, heading in extract_structural_heading_lines(markdown)
        if level == 1 and heading.strip()
    ]
    return len(top_level_headings) > 1


def _looks_like_reference_note(frontmatter: str | None, body: str, has_dae: bool) -> bool:
    if has_dae:
        return False
    text = f"{frontmatter or ''}\n{body}".casefold()
    headings = {
        heading.casefold()
        for _, _, heading in extract_structural_heading_lines(body)
    }
    has_highlights = "highlight:" in text or "highlights" in headings
    has_source_frontmatter = bool(re.search(r"(?m)^source:[ \t]*\S", frontmatter or ""))
    is_interview_template = (
        {"brainstorm", "star method"}.issubset(headings)
        or "this template will help you" in text
        or re.search(r"(?m)^# [^\n]*(tell me about a time|how do you approach)", body, re.IGNORECASE)
        is not None
    )
    return has_highlights or has_source_frontmatter or is_interview_template


def _looks_like_weak_dae(body: str, has_dae: bool, definition_too_long: bool) -> bool:
    if definition_too_long:
        return False
    if not has_dae:
        return _word_count(body) < 80
    section_counts = _dae_section_word_counts(body)
    if not section_counts:
        return False
    return min(section_counts.values()) < 6 or sum(section_counts.values()) < 30


def _contains_factual_risk(body: str) -> bool:
    matches = UNIVERSAL_CLAIM_RE.findall(body)
    return len(matches) >= 2


def _looks_like_duplicate_candidate(path: Path, body: str) -> bool:
    text = f"{path.stem}\n{body}".casefold()
    return "duplicate" in text or "overlap" in text


def _dae_section_word_counts(body: str) -> dict[str, int]:
    sections: dict[str, list[str]] = {"definition": [], "analogy": [], "example": []}
    active_section: str | None = None
    for line in body.splitlines():
        heading_match = HEADING_RE.match(line)
        if heading_match:
            heading = heading_match.group(2).strip().casefold()
            active_section = heading if heading in sections else None
            continue
        if active_section:
            sections[active_section].append(line)
    return {
        section: _word_count("\n".join(lines))
        for section, lines in sections.items()
        if lines
    }


def _word_count(text: str) -> int:
    return count_rendered_words(text)


def _dimensions_for_findings(findings: Iterable[dict[str, str]]) -> dict[str, int]:
    dimensions = {name: 100 for name in DIMENSION_NAMES}
    for finding in findings:
        for dimension, penalty in DIMENSION_PENALTIES.get(finding["code"], {}).items():
            dimensions[dimension] = max(0, dimensions[dimension] - penalty)
    return dimensions


def _recommendations_for_findings(findings: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "mode": RECOMMENDATION_MODES[finding["code"]],
            "message": finding["message"],
        }
        for finding in findings
    ]


def _build_manifest(
    rows: list[dict[str, object]],
    *,
    run_id: str,
    config: dict[str, object],
    started_at: str,
    ended_at: str,
) -> dict[str, object]:
    row_status_counts = {"complete": 0, "reused_cache": 0, "error": 0, "skipped": 0}
    priority_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for row in rows:
        row_status_counts[str(row["row_status"])] += 1
        priority_counts[str(row["priority"])] += 1
    return {
        "schema_version": VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "config_snapshot": dict(config),
        "total_notes": len(rows),
        "row_status_counts": row_status_counts,
        "priority_counts": priority_counts,
        "validation_status": "not_run",
        "outputs": {},
        "errors": [],
    }


def _timestamp_from_path(path: Path) -> str:
    return _to_iso_utc(datetime.fromtimestamp(path.stat().st_mtime, timezone.utc))


def _utc_now() -> str:
    return _to_iso_utc(datetime.now(timezone.utc))


def _to_iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()
