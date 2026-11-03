"""Capture selected source and exact checks without assigning semantic quality."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Callable, Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.audit_engine import DOCTRINE_VERSION, RUBRIC_VERSION, _load_structure_targets, _utc_now
from shared.scripts.config import DEFAULT_CONFIG, resolve_config
from shared.scripts.markdown_parse import extract_frontmatter, extract_wikilinks, extract_headings, count_anki_blocks, decayed_latex_commands, dae_section_starts_lowercase, _structural_markdown
from shared.scripts.model_contract import MODEL_PROMPT_VERSION
from shared.scripts.schema_validation import ValidationError, validate_inventory_row
from shared.scripts.verify_anki_notes import AnkiConnectClient, extract_anki_ids, _visible_field_text


def source_path(vault: Path, note_path: str) -> Path:
    relative = PurePosixPath(note_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in note_path or relative.suffix != ".md":
        raise ValidationError(f"note path must stay inside vault: {note_path}")
    path = (vault.resolve() / str(relative)).resolve()
    if not path.is_relative_to(vault.resolve()):
        raise ValidationError(f"note path must stay inside vault: {note_path}")
    return path


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evidence_directory(vault: Path, destination: Path, *, allow_vault: bool) -> Path:
    destination = destination.resolve()
    if destination.is_relative_to(vault.resolve()):
        if not allow_vault:
            raise ValidationError("evidence must be outside vault; explicitly request --allow-vault-evidence to use one Evidence directory")
        if destination.name != "Evidence":
            destination /= "Evidence"
    return destination


def _check(code: str, source: str, message: str, *, status: str = "passed", priority: str = "P2") -> dict[str, Any]:
    return dict(code=code, source=source, status=status, message=message,
                priority=priority if status == "failed" else None)


def _file_link_resolver(vault: Path) -> Callable[[str, str], bool]:
    by_path = {}
    by_name = {}
    for path in vault.rglob("*"):
        if path.is_file() and path.resolve().is_relative_to(vault):
            by_path[path.relative_to(vault).as_posix()] = path
            by_name.setdefault(path.name, set()).add(path)

    def lookup(names: list[str], source: str) -> set[Path]:
        candidates = set()
        parent = PurePosixPath(source).parent
        for name in names:
            for relative in (name, (parent / name).as_posix()):
                if relative in by_path:
                    candidates.add(by_path[relative])
        if not candidates:
            for name in names:
                if "/" not in name:
                    candidates.update(by_name.get(name, set()))
        return candidates

    def resolve(target: str, source: str) -> bool:
        target, _, fragment = target.partition("#")
        if not target:
            candidates = [source_path(vault, source)]
        else:
            parsed = PurePosixPath(target)
            if parsed.is_absolute() or ".." in parsed.parts or "\\" in target:
                return False
            if parsed.suffix:
                candidates = lookup([target], source)
                if not candidates and not target.endswith(".md"):
                    candidates = lookup([target + ".md"], source)
            else:
                candidates = lookup([target + ".md", target], source)
        candidates = list(set(candidates))
        if len(candidates) != 1:
            return False
        if not fragment:
            return True
        text = candidates[0].read_text(encoding="utf-8")
        if fragment.startswith("^"):
            return bool(re.search(r"(?:^|\s)" + re.escape(fragment) + r"\s*$", _structural_markdown(text), re.MULTILINE))
        headings = {heading.casefold() for heading in extract_headings(text)}
        return fragment.casefold() in headings

    return resolve


def inventory_vault(vault_root: Path, *, run_id: str, note_paths: list[str] | None = None,
                    anki_client: Any = None, content_reader: Callable[[str], str] | None = None,
                    parent_targets: set[str] | None = None,
                    link_resolver: Callable[[str, str], bool] | None = None,
                    config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    vault = vault_root.resolve()
    if content_reader is not None and (note_paths is None or parent_targets is None or link_resolver is None):
        raise ValidationError("app-context inventory requires selected paths, parent targets and a link resolver; no filesystem fallback")
    config = dict(config or (DEFAULT_CONFIG if content_reader else resolve_config(vault)))
    if note_paths is None:
        note_paths = sorted(p.relative_to(vault).as_posix() for p in (vault / str(config["atomic_notes_folder"])).rglob("*.md"))
    if len(note_paths) != len(set(note_paths)):
        raise ValidationError("duplicate selected inventory note_path")
    if parent_targets is None:
        parent_targets = _load_structure_targets(vault / str(config["structure_notes_folder"]))
    resolver = link_resolver or _file_link_resolver(vault)
    mode = "selected:" + content_hash(json.dumps(sorted(note_paths)))
    rows = []
    for note_path in sorted(note_paths):
        path = source_path(vault, note_path)
        text = content_reader(note_path) if content_reader else path.read_text(encoding="utf-8")
        checks = []
        frontmatter, _ = extract_frontmatter(text)
        checks.append(_check("frontmatter", "metadata", "Required frontmatter is present." if frontmatter is not None else "Add the required frontmatter.", status="passed" if frontmatter is not None else "failed"))
        checks.append(_check("parent_link", "parent", "Parent Structure Note links to this note." if path.stem in parent_targets else "Link this note from its parent Structure Note.", status="passed" if path.stem in parent_targets else "failed"))
        counts = count_anki_blocks(text)
        ordered = [line for line in _structural_markdown(text).splitlines() if line in {"START", "END"}]
        valid_markers = counts["START"] == counts["END"] and all(ordered[i:i+2] == ["START", "END"] for i in range(0, len(ordered), 2))
        checks.append(_check("card_markers", "markers", "Card markers are balanced and ordered." if valid_markers else "Repair the malformed START/END card boundaries.", status="passed" if valid_markers else "failed", priority="P1"))
        corruption = decayed_latex_commands(text)
        checks.append(_check("literal_corruption", "literal", "Restore the escaped command: " + ", ".join(corruption) if corruption else "No known decayed command characters found.", status="failed" if corruption else "passed", priority="P1"))
        lowercase = dae_section_starts_lowercase(text)
        checks.append(_check("dae_sentence_case", "sentence_case", "Capitalize the first visible letter of the affected DAE sentence." if lowercase else "No literal DAE sentence-case violation found.", status="failed" if lowercase else "passed", priority="P3"))
        links = extract_wikilinks(text)
        if not links:
            checks.append(_check("link_targets", "links", "No wikilink targets to resolve."))
        for target in links:
            resolved = resolver(target, note_path)
            checks.append(_check("link_target" if resolved else "unresolved_link", "links", f"Link target resolves: {target}" if resolved else f"Repair the unresolved or ambiguous link: {target}", status="passed" if resolved else "failed"))
        label = re.sub(r"^\d{12,14}\s+", "", path.stem).replace("|", " ").replace("]", "")
        row = dict(artifact_type="audit_inventory", schema_version="1.0.0", run_id=run_id,
                   note_path=note_path, note_link=f"[[{PurePosixPath(note_path).with_suffix('')}|{label}]]",
                   content=text, content_hash=content_hash(text), modified_time=_utc_now(),
                   doctrine_version=DOCTRINE_VERSION, rubric_version=RUBRIC_VERSION,
                   prompt_version=MODEL_PROMPT_VERSION, audit_mode=mode, config_snapshot=config,
                   integrity_checks=checks)
        rows.append(row)
    _anki_checks(rows, anki_client)
    for row in rows:
        validate_inventory_row(row)
    return rows


def _source_card_expectations(text: str) -> dict[int, tuple[str | None, str | None, int | None]]:
    _, body = extract_frontmatter(text)
    body_lines = body.splitlines()
    structural_lines = _structural_markdown(text).splitlines()
    expectations = {}
    deck = None
    start = None
    for index, line in enumerate(structural_lines):
        deck_match = re.match(r"^TARGET DECK:\s*(.+)$", line)
        if deck_match:
            deck = deck_match.group(1).strip()
        if line == "START":
            start = index
        elif line == "END" and start is not None:
            card = "\n".join(structural_lines[start + 1:index])
            note_ids = extract_anki_ids("\n".join(body_lines[start + 1:index]))
            model = next((m for m in ("Basic", "Cloze") if re.search(r"(?m)^" + m + r"\s*$", card)), None)
            if model == "Basic":
                count = 1
            elif model == "Cloze":
                count = len(set(re.findall(r"\{\{c(\d+)::", card)))
            else:
                count = None
            for note_id in note_ids:
                expectations[note_id] = (model, deck, count if len(note_ids) == 1 else None)
            start = None
    return expectations


def _anki_checks(rows: list[dict[str, Any]], client: Any) -> None:
    ids = {row["note_path"]: extract_anki_ids(row["content"]) for row in rows}
    counts = Counter(i for values in ids.values() for i in values)
    requested = sorted(counts)
    notes = None
    cards = {}
    if client is not None and requested:
        try:
            result = client.invoke("notesInfo", {"notes": requested})
            if not isinstance(result, list):
                raise RuntimeError("notesInfo did not return a list")
            notes = {n["noteId"]: n for n in result if isinstance(n, dict) and isinstance(n.get("noteId"), int)}
            card_ids = [c for n in notes.values() for c in n.get("cards", []) if type(c) is int]
            if card_ids:
                result = client.invoke("cardsInfo", {"cards": card_ids})
                if not isinstance(result, list):
                    raise RuntimeError("cardsInfo did not return a list")
                cards = {c["cardId"]: c for c in result if isinstance(c, dict) and type(c.get("cardId")) is int}
        except (RuntimeError, OSError, ValueError):
            notes = None
    for row in rows:
        checks = row["integrity_checks"]
        note_ids = ids[row["note_path"]]
        if any(counts[i] > 1 for i in note_ids):
            checks.append(_check("shared_anki_id", "markers", "Give each source card a unique Anki ID; this ID occurs more than once in scope.", status="failed", priority="P1"))
        if not note_ids:
            has_cards = count_anki_blocks(row["content"])["START"] > 0
            if has_cards:
                checks.append(_check("unsynced_card", "markers", "Verify the unsynced source card; no Anki ID is recorded.", status="failed"))
            checks.append(_check("anki_unchecked", "anki", "No source Anki ID; integration not checked.", status="not_checked"))
            continue
        if notes is None:
            checks.append(_check("anki_unchecked", "anki", "Anki integration not checked: connection unavailable or not requested.", status="not_checked"))
            continue
        expectations = _source_card_expectations(row["content"])
        for note_id in note_ids:
            note = notes.get(note_id)
            if note is None:
                checks.append(_check("missing_anki_target", "anki", "Repair the stale Anki ID; its target does not resolve.", status="failed", priority="P1"))
                continue
            failures = []
            card_ids = note.get("cards", [])
            if not card_ids or any(c not in cards for c in card_ids):
                failures.append("Verify missing Anki cards.")
            source_model, deck, expected_count = expectations.get(note_id, (None, None, None))
            if source_model and note.get("modelName") != source_model:
                failures.append("Match the source and Anki note models.")
            if deck and any(cards.get(c, {}).get("deckName") != deck for c in card_ids):
                failures.append("Match the source and Anki card decks.")
            fields = note.get("fields", {})
            if not isinstance(fields, dict):
                fields = {}
            if expected_count and len(card_ids) != expected_count:
                failures.append("Match the source and Anki card counts.")
            if not fields or not any(_visible_field_text(fields, name).strip() for name in fields):
                failures.append("Repair empty rendered Anki fields.")
            if source_model == "Basic" and any(not _visible_field_text(fields, f).strip() for f in ("Front", "Back")):
                failures.append("Repair empty Basic Front or Back fields.")
            checks.append(_check("anki_integrity", "anki", " ".join(failures) if failures else "Anki target, cards and available source expectations verified.", status="failed" if failures else "passed", priority="P1"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture unscored selected note inventory; no semantic baseline or report.")
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--note-path", action="append", dest="note_paths")
    parser.add_argument("--allow-vault-evidence", action="store_true")
    parser.add_argument("--check-anki", action="store_true", help="Read-only notesInfo/cardsInfo checks; no sync or mutations.")
    args = parser.parse_args(argv)
    try:
        destination = evidence_directory(args.vault, args.evidence_dir, allow_vault=args.allow_vault_evidence)
        rows = inventory_vault(args.vault, run_id=args.run_id, note_paths=args.note_paths,
                               anki_client=AnkiConnectClient() if args.check_anki else None)
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "inventory.jsonl"
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
        print(path)
    except (ValidationError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
