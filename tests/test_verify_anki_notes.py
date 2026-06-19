import tempfile
import unittest
from pathlib import Path

from shared.scripts.verify_anki_notes import extract_anki_id, verify_entries


class FakeAnkiClient:
    def __init__(self, notes=None, cards=None):
        self.notes = notes or []
        self.cards = cards or []
        self.calls = []

    def invoke(self, action, params=None):
        self.calls.append((action, params))
        if action == "notesInfo":
            return self.notes
        if action == "cardsInfo":
            return self.cards
        raise AssertionError(action)


class VerifyAnkiNotesTest(unittest.TestCase):
    def test_extract_anki_id(self):
        self.assertEqual(extract_anki_id("<!--ID: 12345-->"), 12345)
        self.assertIsNone(extract_anki_id("no id"))

    def test_verify_basic_note_model_deck_card_count_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Example.md").write_text(
                "TARGET DECK: General\n<!--ID: 12345-->\n",
                encoding="utf-8",
            )
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Front": {"value": "What is it?"},
                            "Back": {"value": "Rendered representative text"},
                        },
                    }
                ],
                cards=[{"cardId": 67890, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Example.md",
                        "representative_text": "representative text",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.checked_anki_notes, 1)
        self.assertEqual(result.checked_non_anki_notes, 0)
        self.assertEqual(result.failures, [])

    def test_verify_non_anki_note_requires_missing_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Formula.md").write_text("# Formula\n", encoding="utf-8")

            result = verify_entries(
                [{"note_path": "Atomic Notes/Formula.md", "anki": False}],
                vault=vault,
                client=FakeAnkiClient(),
            )

        self.assertEqual(result.checked_anki_notes, 0)
        self.assertEqual(result.checked_non_anki_notes, 1)
        self.assertEqual(result.failures, [])

    def test_verify_non_anki_note_rejects_remaining_card_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Former Card.md").write_text(
                "TARGET DECK: General\nSTART\nBasic\nFront\nBack\nEND\n",
                encoding="utf-8",
            )

            result = verify_entries(
                [{"note_path": "Atomic Notes/Former Card.md", "anki": False}],
                vault=vault,
                client=FakeAnkiClient(),
            )

        self.assertEqual(
            result.failures,
            ["Atomic Notes/Former Card.md: expected no Obsidian-to-Anki card markers"],
        )

    def test_verify_duplicate_anki_ids_fail_before_anki_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "First.md").write_text("<!--ID: 12345-->\n", encoding="utf-8")
            (note / "Second.md").write_text("<!--ID: 12345-->\n", encoding="utf-8")
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {"note_path": "Atomic Notes/First.md"},
                    {"note_path": "Atomic Notes/Second.md"},
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(
            result.failures,
            [
                "Atomic Notes/Second.md: duplicate Obsidian-to-Anki ID 12345 also appears in Atomic Notes/First.md"
            ],
        )
        self.assertEqual(client.calls, [])

    def test_verify_reports_rendered_link_text_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Linked.md").write_text("<!--ID: 12345-->\n", encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Back": {
                                "value": 'Durability is the <a href="obsidian://open">ACID</a> property'
                            },
                        },
                    }
                ],
                cards=[{"cardId": 67890, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Linked.md",
                        "representative_text": "Durability is the ACID property",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(
            result.failures,
            ["Atomic Notes/Linked.md: representative text missing: Durability is the ACID property"],
        )


if __name__ == "__main__":
    unittest.main()
