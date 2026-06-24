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
from shared.scripts.finding_codes import FINDING_MESSAGES, FINDING_RECOMMENDATION_MODES
from shared.scripts.scoring import NO_CHANGE_BUCKET, bucket_for_score, compute_clean, compute_final_score


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
DIMENSION_PENALTIES = {
    "missing_frontmatter": {"structure": 20, "metadata_card_safety": 40},
    "invalid_dae": {"structure": 35, "dae_quality": 60, "clarity": 20},
    "definition_too_long": {"structure": 20, "dae_quality": 35, "clarity": 25},
    "missing_parent": {"connections": 60},
    "malformed_anki": {"metadata_card_safety": 50, "clarity": 10},
    "multi_note": {"structure": 30, "atomicity": 70, "clarity": 20},
    "misfiled_reference": {"structure": 30, "atomicity": 40, "dae_quality": 50},
    "weak_dae": {"dae_quality": 25, "clarity": 15},
    "factual_risk": {"clarity": 20, "metadata_card_safety": 10},
    "duplicate_overlap": {"atomicity": 25, "clarity": 10, "connections": 10},
}
FACTUAL_RISK_ABSOLUTE_RE = re.compile(
    r"\b(all|always|every|everyone|never|none|only)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_NUMBER_RE = re.compile(
    r"(?<!\w)(?:\d{4}|\d+(?:\.\d+)?%|\$\d+(?:,\d{3})*(?:\.\d+)?|"
    r"\d+(?:\.\d+)?\s*(?:x|times|percent|percentage points|days|weeks|months|years|seconds|minutes|hours))(?=\W|$)",
    re.IGNORECASE,
)
FACTUAL_RISK_CURRENT_RE = re.compile(
    r"\b(as of|currently|latest|now|recently|since \d{4}|deprecated|supported|released|introduced|launched)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_SENSITIVE_RE = re.compile(
    r"\b(law|legal|regulation|regulatory|gdpr|hipaa|tax|medical|medicine|health|disease|diagnosis|treatment|brain|hormone|physiological|cardiovascular|financial|finance|revenue|profit|security|vulnerability|breach|encryption|privacy)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_ATTRIBUTION_RE = re.compile(
    r"\b(according to|found|finds|says|said|proves|"
    r"(?:research|stud(?:y|ies)|paper|report|analysis|(?:[a-z]+(?:-[a-z]+)?\s+){0,2}"
    r"(?:benchmarks?|reviews?|trials?|surveys?|experiments?))\s+"
    r"(?:found|finds|show|showed|shows|said|says|reported))\b",
    re.IGNORECASE,
)
FACTUAL_RISK_CAUSAL_RE = re.compile(
    r"\b(causes?|caused|leads? to|led to|results? in|resulted in|reduc(?:e|es|ed)|increas(?:e|es|ed)|decreas(?:e|es|ed)|improv(?:e|es|ed)|boost(?:s|ed)?|lower(?:s|ed)?|rais(?:e|es|ed)|prevent(?:s|ed)?|predict(?:s|ed)?|correlat(?:e|es|ed)|indicat(?:e|es|ed)|suggest(?:s|ed)?|(?:is|was|were) associated with|more .* than|less .* than|better .* than|worse .* than)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_EMPIRICAL_PREDICATE_RE = re.compile(
    r"\b(requires?|supports?|guarantees?|configures?|classif(?:y|ies|ied)|released|introduced|deprecated|launched|acquired|improved|increased|decreased|reduced|found|reported|defaults? to)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_PRODUCT_CLASS_RE = re.compile(
    r"\b(?:AP|CP|CA)\s+system\b|\bdefault configuration\b",
    re.IGNORECASE,
)
FACTUAL_RISK_HUMAN_CLASS_PATTERN = (
    r"(?:people|person|learners?|employees?|customers?|users?|humans?|children|child|adults?|patients?|students?)"
)
FACTUAL_RISK_ABSOLUTE_HUMAN_PREFIX_RE = re.compile(
    rf"\b(?:all|every|none|only)\s+"
    rf"(?:of\s+(?:the\s+)?)?"
    rf"(?:\w+\s+){{0,3}}(?P<human>{FACTUAL_RISK_HUMAN_CLASS_PATTERN})\b",
    re.IGNORECASE,
)
FACTUAL_RISK_HUMAN_ABSOLUTE_SUFFIX_RE = re.compile(
    rf"\b(?P<human>{FACTUAL_RISK_HUMAN_CLASS_PATTERN})\s+"
    rf"(?:\w+\s+){{0,3}}(?:always|never|only)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_EVERYONE_RE = re.compile(r"\beveryone\b", re.IGNORECASE)
FACTUAL_RISK_SELECTION_CHANCE_RE = re.compile(
    r"\b(?:same|equal)\s+(?:selection chance|chance of selection)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_SELECTION_CHANCE_BRIDGE_RE = re.compile(
    r"^(?:\s+|\b(?:receives?|gets?|has|have|had|is|are|was|were|be|being|been|"
    r"given|assigned|allocated|granted|the|a|an|same|equal|of|to|with)\b)*$",
    re.IGNORECASE,
)
FACTUAL_RISK_SELECTION_OUTCOME_AFTER_RE = re.compile(
    r"\band\s+(?:\w+\s+){0,4}"
    r"(?:remember|remembers|recall|recalls|learn|learns|retain|retains|perform|performs|score|scores)\b",
    re.IGNORECASE,
)
FACTUAL_RISK_NONHUMAN_HEADS_AFTER_SINGULAR_HUMAN_TERM = {
    "account",
    "accounts",
    "class",
    "classes",
    "element",
    "elements",
    "event",
    "events",
    "id",
    "ids",
    "input",
    "inputs",
    "interface",
    "interfaces",
    "node",
    "nodes",
    "object",
    "objects",
    "order",
    "orders",
    "permission",
    "permissions",
    "profile",
    "profiles",
    "record",
    "records",
    "role",
    "roles",
    "session",
    "sessions",
}
FORMAL_DEFINITION_RE = re.compile(
    r"\b(is|are|means|refers to|is defined as|stands for|denotes|states that|can be written as|assigns|represents)\b",
    re.IGNORECASE,
)
FORMAL_MARKER_RE = re.compile(
    r"(?:\\\(|\\\[|\$|=|∀|∃|\b(?:theorem|lemma|proof|axiom|rule|property|let|given|nonzero|integer|integers|rational|irrational|polynomial|function|subset|set|vector|matrix|equation|fraction|denominator|numerator|slope|triangle|rectangle|exponent|power|base|variable|coefficient|ratio|codomain|domain)\b)",
    re.IGNORECASE,
)
SOURCE_SECTION_RE = re.compile(
    r"(?ims)^(?:#{1,6}[ \t]+)?sources?:?[ \t]*\r?\n.*\Z"
)
REFERENCE_SECTION_RE = re.compile(
    r"(?ims)^(?:#{1,6}[ \t]+)?references?:?[ \t]*\r?\n.*\Z"
)
FENCED_BLOCK_RE = re.compile(r"(?ms)^[ \t]{0,3}(`{3,}|~{3,}).*?^[ \t]{0,3}\1[ \t]*$")
DISPLAY_MATH_RE = re.compile(r"(?ms)^\$\$.*?^\$\$")
INLINE_MATH_RE = re.compile(r"\$[^$\r\n]+\$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
URL_RE = re.compile(r"https?://\S+")
WIKILINK_RE = re.compile(r"!\[\[([^\[\]\r\n]+)\]\]|\[\[([^\[\]\r\n]+)\]\]")
HEADING_RE = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
DUPLICATE_REVIEW_RE = re.compile(
    r"\b(?:duplicate candidate|overlap candidate|may duplicate|may overlap|possible duplicate|possible overlap|duplicate[_-]overlap)\b",
    re.IGNORECASE,
)


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
    score = compute_final_score(findings)

    row: dict[str, object] = {
        "schema_version": VERSION,
        "run_id": run_id,
        "row_status": "complete",
        "note_path": relative_path,
        "note_link": f"[[{path.stem}]]",
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "modified_time": modified_time,
        "score": score,
        "priority": bucket_for_score(score),
        "clean": compute_clean(
            score,
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
        row["factual_risk_reason"] = "Contains empirical, current, attributed, or sensitive-domain claims that need verification."
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
    finding_codes: list[str] = []

    if frontmatter is None:
        finding_codes.append("missing_frontmatter")
    if not has_dae:
        if dae_analysis.definition_too_long:
            finding_codes.append("definition_too_long")
        else:
            finding_codes.append("invalid_dae")
    if path.stem not in structure_targets:
        finding_codes.append("missing_parent")
    if anki_counts["START"] != anki_counts["END"]:
        finding_codes.append("malformed_anki")
    if _looks_like_multi_note(content, anki_counts):
        finding_codes.append("multi_note")
    if _looks_like_reference_note(frontmatter, body, has_dae):
        finding_codes.append("misfiled_reference")
    if _looks_like_weak_dae(body, has_dae, dae_analysis.definition_too_long):
        finding_codes.append("weak_dae")
    if _contains_factual_risk(body):
        finding_codes.append("factual_risk")
    if _looks_like_duplicate_candidate(path, body):
        finding_codes.append("duplicate_overlap")

    return [
        {
            "code": code,
            "message": FINDING_MESSAGES[code],
        }
        for code in finding_codes
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
    return PurePosixPath(target).name


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
    for sentence in _factual_risk_sentences(body):
        if sentence.endswith("?"):
            continue
        if _is_formal_definition_sentence(sentence) and not _has_hard_empirical_trigger(sentence):
            continue
        if _is_generic_example_sentence(sentence) and not _has_non_generic_example_trigger(sentence):
            continue
        score = _factual_risk_sentence_score(sentence)
        if score >= 3:
            return True
    return False


def _factual_risk_sentence_score(sentence: str) -> int:
    score = 0
    absolute_count = len(FACTUAL_RISK_ABSOLUTE_RE.findall(sentence))
    if absolute_count:
        score += min(absolute_count, 2)
    if FACTUAL_RISK_NUMBER_RE.search(sentence):
        score += 3
    if FACTUAL_RISK_CURRENT_RE.search(sentence):
        score += 3
    if FACTUAL_RISK_SENSITIVE_RE.search(sentence):
        score += 1
    if FACTUAL_RISK_ATTRIBUTION_RE.search(sentence):
        score += 2
    if FACTUAL_RISK_CAUSAL_RE.search(sentence):
        score += 2
    if _has_absolute_human_generalization(sentence):
        score += 2
    if _has_named_entity_claim(sentence):
        score += 3
    return score


def _has_hard_empirical_trigger(sentence: str) -> bool:
    return bool(
        FACTUAL_RISK_CURRENT_RE.search(sentence)
        or FACTUAL_RISK_SENSITIVE_RE.search(sentence)
        or FACTUAL_RISK_ATTRIBUTION_RE.search(sentence)
        or _has_named_entity_claim(sentence)
    )


def _has_named_entity_claim(sentence: str) -> bool:
    return bool(
        _contains_named_entity(sentence)
        and (
            FACTUAL_RISK_EMPIRICAL_PREDICATE_RE.search(sentence)
            or FACTUAL_RISK_PRODUCT_CLASS_RE.search(sentence)
        )
    )


def _is_generic_example_sentence(sentence: str) -> bool:
    return sentence.lower().startswith("for example,")


def _has_non_generic_example_trigger(sentence: str) -> bool:
    return bool(
        FACTUAL_RISK_NUMBER_RE.search(sentence)
        or FACTUAL_RISK_CURRENT_RE.search(sentence)
        or FACTUAL_RISK_SENSITIVE_RE.search(sentence)
        or FACTUAL_RISK_ATTRIBUTION_RE.search(sentence)
        or FACTUAL_RISK_CAUSAL_RE.search(sentence)
        or _has_absolute_human_generalization(sentence)
        or _has_named_entity_claim(sentence)
    )


def _has_absolute_human_generalization(sentence: str) -> bool:
    for match in FACTUAL_RISK_EVERYONE_RE.finditer(sentence):
        if not _is_selection_chance_after(sentence, match.end()):
            return True
    for pattern in (FACTUAL_RISK_ABSOLUTE_HUMAN_PREFIX_RE, FACTUAL_RISK_HUMAN_ABSOLUTE_SUFFIX_RE):
        for match in pattern.finditer(sentence):
            if not _is_nonhuman_human_modifier(sentence, match) and not _is_selection_chance_match(
                sentence,
                match,
            ):
                return True
    return False


def _is_selection_chance_match(sentence: str, match: re.Match[str]) -> bool:
    return _is_selection_chance_after(sentence, match.end("human"))


def _is_selection_chance_after(sentence: str, start: int) -> bool:
    selection_match = FACTUAL_RISK_SELECTION_CHANCE_RE.search(sentence, start, start + 80)
    if not selection_match:
        return False
    if FACTUAL_RISK_SELECTION_OUTCOME_AFTER_RE.search(sentence, selection_match.end()):
        return False
    return FACTUAL_RISK_SELECTION_CHANCE_BRIDGE_RE.fullmatch(sentence[start : selection_match.start()]) is not None


def _is_nonhuman_human_modifier(sentence: str, match: re.Match[str]) -> bool:
    matched_term = match.group("human").lower()
    if _is_plural_human_term(matched_term):
        return False

    tail = sentence[match.end("human") :]
    if re.match(r"-[A-Za-z]+\b", tail):
        return True
    next_word_match = re.match(r"\s+([A-Za-z]+)\b", tail)
    return bool(
        next_word_match
        and next_word_match.group(1).lower() in FACTUAL_RISK_NONHUMAN_HEADS_AFTER_SINGULAR_HUMAN_TERM
    )


def _is_plural_human_term(term: str) -> bool:
    return term in {"children", "people"} or (term.endswith("s") and term != "person")


def _contains_named_entity(sentence: str) -> bool:
    without_sentence_start = re.sub(r"^\W*[A-Z][a-z]+(?:'s)?\b", "", sentence)
    return bool(
        re.search(r"\b[A-Z][A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*(?:\s+[A-Z][A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*)+\b", without_sentence_start)
        or re.search(r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b", without_sentence_start)
    )


def _is_formal_definition_sentence(sentence: str) -> bool:
    return bool(FORMAL_DEFINITION_RE.search(sentence) and FORMAL_MARKER_RE.search(sentence))


def _factual_risk_sentences(body: str) -> list[str]:
    text = REFERENCE_SECTION_RE.sub("", body)
    text = SOURCE_SECTION_RE.sub("", text)
    text = FENCED_BLOCK_RE.sub(" ", text)
    text = DISPLAY_MATH_RE.sub(" ", text)
    text = INLINE_MATH_RE.sub(" ", text)
    text = HTML_COMMENT_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = _render_wikilinks_for_factual_risk(text)
    text = re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", r"\1", text)
    text = re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+.*$", " ", text)
    text = re.sub(r"(?m)^\s*(?:TARGET DECK:.*|START|END|Basic|Cloze)\s*$", " ", text)
    return [
        sentence.strip(" \t\r\n-*")
        for sentence in re.split(r"(?<=[.!?])\s+|(?:\r?\n){2,}|^\s*[-*+]\s+", text, flags=re.MULTILINE)
        if sentence.strip(" \t\r\n-*")
    ]


def _render_wikilinks_for_factual_risk(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            return ""
        link = match.group(2)
        visible = link.split("|", 1)[1] if "|" in link else link.split("#", 1)[0]
        return visible.strip()

    return WIKILINK_RE.sub(replace, text)


def _looks_like_duplicate_candidate(path: Path, body: str) -> bool:
    text = f"{path.stem}\n{body}"
    return DUPLICATE_REVIEW_RE.search(text) is not None


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
            "mode": FINDING_RECOMMENDATION_MODES[finding["code"]],
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
    priority_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0, NO_CHANGE_BUCKET: 0}
    for row in rows:
        row_status_counts[str(row["row_status"])] += 1
        priority = row["priority"] if row["priority"] is not None else NO_CHANGE_BUCKET
        priority_counts[str(priority)] += 1
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
