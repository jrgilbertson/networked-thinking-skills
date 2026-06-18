from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ANKI_ID_RE = re.compile(r"<!--ID:\s*(\d+)-->")
DEFAULT_ANKICONNECT_URLS = ("http://127.0.0.1:8765", "http://localhost:8765")


@dataclass(frozen=True)
class VerificationResult:
    checked_anki_notes: int
    checked_non_anki_notes: int
    failures: list[str]


class AnkiConnectClient:
    def __init__(self, urls: tuple[str, ...] = DEFAULT_ANKICONNECT_URLS) -> None:
        self.urls = urls

    def invoke(self, action: str, params: dict[str, Any] | None = None) -> Any:
        body = json.dumps(
            {"action": action, "version": 6, "params": params or {}}
        ).encode("utf-8")
        last_error: Exception | None = None
        for url in self.urls:
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(url, data=body), timeout=10
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except (OSError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                continue
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            return payload.get("result")
        raise RuntimeError(f"Unable to reach AnkiConnect: {last_error}")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        entries = json.loads(args.spec.read_text(encoding="utf-8"))
        result = verify_entries(entries, vault=args.vault, client=AnkiConnectClient())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if result.failures:
        for failure in result.failures:
            print(failure, file=sys.stderr)
        return 1

    print(
        "anki_verification=ok "
        f"anki_notes={result.checked_anki_notes} "
        f"non_anki_notes={result.checked_non_anki_notes}"
    )
    return 0


def verify_entries(
    entries: Any,
    *,
    vault: Path,
    client: AnkiConnectClient,
) -> VerificationResult:
    if not isinstance(entries, list):
        raise ValueError("spec must be a list")

    normalized = [_normalize_entry(entry, index) for index, entry in enumerate(entries)]
    failures: list[str] = []
    anki_note_ids: dict[str, int] = {}
    non_anki_count = 0

    for entry in normalized:
        note_path = vault / entry["note_path"]
        try:
            text = note_path.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"{entry['note_path']}: unable to read note: {exc}")
            continue

        note_id = extract_anki_id(text)
        if entry["anki"]:
            if note_id is None:
                failures.append(f"{entry['note_path']}: missing Obsidian-to-Anki ID")
                continue
            anki_note_ids[entry["note_path"]] = note_id
        else:
            non_anki_count += 1
            if note_id is not None:
                failures.append(
                    f"{entry['note_path']}: expected no Obsidian-to-Anki ID, found {note_id}"
                )

    if not anki_note_ids:
        return VerificationResult(0, non_anki_count, failures)

    notes = client.invoke("notesInfo", {"notes": list(anki_note_ids.values())})
    if not isinstance(notes, list):
        raise RuntimeError("AnkiConnect notesInfo returned a non-list result")

    notes_by_id: dict[int, dict[str, Any]] = {}
    for note in notes:
        if isinstance(note, dict) and isinstance(note.get("noteId"), int):
            notes_by_id[note["noteId"]] = note

    card_ids = [
        card_id
        for note in notes_by_id.values()
        for card_id in note.get("cards", [])
        if isinstance(card_id, int)
    ]
    card_by_id: dict[int, dict[str, Any]] = {}
    if card_ids:
        cards = client.invoke("cardsInfo", {"cards": card_ids})
        if not isinstance(cards, list):
            raise RuntimeError("AnkiConnect cardsInfo returned a non-list result")
        card_by_id = {
            card["cardId"]: card
            for card in cards
            if isinstance(card, dict) and isinstance(card.get("cardId"), int)
        }

    entries_by_path = {entry["note_path"]: entry for entry in normalized if entry["anki"]}
    for path, note_id in anki_note_ids.items():
        entry = entries_by_path[path]
        note = notes_by_id.get(note_id)
        if not note:
            failures.append(f"{path}: Anki note ID {note_id} does not resolve")
            continue
        failures.extend(_verify_note(path, entry, note, card_by_id))

    return VerificationResult(len(anki_note_ids), non_anki_count, failures)


def extract_anki_id(text: str) -> int | None:
    match = ANKI_ID_RE.search(text)
    return int(match.group(1)) if match else None


def _verify_note(
    path: str,
    entry: dict[str, Any],
    note: dict[str, Any],
    card_by_id: dict[int, dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    expected_model = entry["expected_model"]
    expected_deck = entry["expected_deck"]
    expected_card_count = entry["expected_card_count"]

    if note.get("modelName") != expected_model:
        failures.append(f"{path}: model={note.get('modelName')}, expected={expected_model}")

    cards = [card for card in note.get("cards", []) if isinstance(card, int)]
    if len(cards) != expected_card_count:
        failures.append(f"{path}: card_count={len(cards)}, expected={expected_card_count}")

    decks = {card_by_id[card].get("deckName") for card in cards if card in card_by_id}
    if decks != {expected_deck}:
        failures.append(f"{path}: decks={sorted(decks)}, expected={[expected_deck]}")

    fields = note.get("fields", {})
    rendered_field_text = "\n".join(
        field.get("value", "")
        for field in fields.values()
        if isinstance(field, dict)
    )
    if not rendered_field_text.strip():
        failures.append(f"{path}: rendered Anki fields are empty")

    for expected_text in entry["representative_text"]:
        if expected_text not in rendered_field_text:
            failures.append(f"{path}: representative text missing: {expected_text}")

    return failures


def _normalize_entry(entry: Any, index: int) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"spec entry {index} must be an object")
    note_path = entry.get("note_path")
    if not isinstance(note_path, str) or not note_path:
        raise ValueError(f"spec entry {index} requires note_path")

    anki = entry.get("anki", True)
    if not isinstance(anki, bool):
        raise ValueError(f"{note_path}: anki must be a boolean")
    if not anki:
        return {"note_path": note_path, "anki": False}

    expected_model = entry.get("expected_model", "Basic")
    expected_deck = entry.get("expected_deck", "General")
    expected_card_count = entry.get("expected_card_count", 1)
    representative_text = entry.get("representative_text", [])

    if not isinstance(expected_model, str) or not expected_model:
        raise ValueError(f"{note_path}: expected_model must be a non-empty string")
    if not isinstance(expected_deck, str) or not expected_deck:
        raise ValueError(f"{note_path}: expected_deck must be a non-empty string")
    if not isinstance(expected_card_count, int) or expected_card_count < 1:
        raise ValueError(f"{note_path}: expected_card_count must be a positive integer")
    if isinstance(representative_text, str):
        representative_text = [representative_text]
    if not isinstance(representative_text, list) or not all(
        isinstance(item, str) and item for item in representative_text
    ):
        raise ValueError(f"{note_path}: representative_text must be a string or string list")

    return {
        "note_path": note_path,
        "anki": True,
        "expected_model": expected_model,
        "expected_deck": expected_deck,
        "expected_card_count": expected_card_count,
        "representative_text": representative_text,
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify Obsidian-to-Anki IDs, models, decks, cards, and rendered fields."
    )
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
