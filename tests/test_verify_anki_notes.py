import tempfile
import unittest
from pathlib import Path

from shared.scripts.verify_anki_notes import extract_anki_id, verify_entries


ANKI_BASIC_NOTE = """TARGET DECK: General
START
Basic
Front
Back
END
<!--ID: 12345-->
"""


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
            (note / "Example.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
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
            (note / "First.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            (note / "Second.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/First.md",
                        "representative_text": "First",
                    },
                    {
                        "note_path": "Atomic Notes/Second.md",
                        "representative_text": "Second",
                    },
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
            (note / "Linked.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Front": {"value": "What is durability?"},
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

    def test_verify_basic_note_rejects_empty_front(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Blank Front.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Front": {"value": ""},
                            "Back": {"value": "Visible answer text"},
                        },
                    }
                ],
                cards=[{"cardId": 67890, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Blank Front.md",
                        "representative_text": "Visible answer text",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.failures, ["Atomic Notes/Blank Front.md: Basic Front field is empty"])

    def test_verify_basic_note_rejects_visually_empty_front_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Blank Front Html.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Front": {"value": "<div><br></div>&nbsp;"},
                            "Back": {"value": "Visible answer text"},
                        },
                    }
                ],
                cards=[{"cardId": 67890, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Blank Front Html.md",
                        "representative_text": "Visible answer text",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.failures, ["Atomic Notes/Blank Front Html.md: Basic Front field is empty"])

    def test_verify_basic_note_rejects_empty_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Blank Back.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [67890],
                        "fields": {
                            "Front": {"value": "Visible prompt text"},
                            "Back": {"value": ""},
                        },
                    }
                ],
                cards=[{"cardId": 67890, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Blank Back.md",
                        "representative_text": "Visible prompt text",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.failures, ["Atomic Notes/Blank Back.md: Basic Back field is empty"])

    def test_verify_rejects_absolute_note_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            vault.mkdir()
            outside = Path(tmp) / "Outside.md"
            outside.write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {
                        "note_path": str(outside),
                        "representative_text": "Answer",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.failures, [f"{outside}: note_path must stay inside vault"])
        self.assertEqual(client.calls, [])

    def test_verify_rejects_parent_relative_note_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            vault.mkdir()
            (root / "Outside.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {
                        "note_path": "../Outside.md",
                        "representative_text": "Answer",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(result.failures, ["../Outside.md: note_path must stay inside vault"])
        self.assertEqual(client.calls, [])

    def test_verify_reports_missing_card_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Two Cards.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")
            client = FakeAnkiClient(
                notes=[
                    {
                        "noteId": 12345,
                        "modelName": "Basic",
                        "cards": [111, 222],
                        "fields": {
                            "Front": {"value": "Question"},
                            "Back": {"value": "Answer"},
                        },
                    }
                ],
                cards=[{"cardId": 111, "deckName": "General"}],
            )

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Two Cards.md",
                        "expected_card_count": 2,
                        "representative_text": "Answer",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(
            result.failures,
            ["Atomic Notes/Two Cards.md: missing cardsInfo for card IDs [222]"],
        )

    def test_verify_rejects_boolean_expected_card_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Example.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "expected_card_count must be a positive integer",
            ):
                verify_entries(
                    [
                        {
                            "note_path": "Atomic Notes/Example.md",
                            "expected_card_count": True,
                            "representative_text": "Answer",
                        }
                    ],
                    vault=vault,
                    client=FakeAnkiClient(),
                )

    def test_verify_rejects_multiple_anki_ids_in_same_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Extra Id.md").write_text(
                f"{ANKI_BASIC_NOTE}<!--ID: 99999-->\n",
                encoding="utf-8",
            )
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Extra Id.md",
                        "representative_text": "Answer",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(
            result.failures,
            ["Atomic Notes/Extra Id.md: expected exactly one Obsidian-to-Anki ID, found 2"],
        )
        self.assertEqual(client.calls, [])

    def test_verify_rejects_anki_note_without_local_card_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Id Only.md").write_text("<!--ID: 12345-->\n", encoding="utf-8")
            client = FakeAnkiClient()

            result = verify_entries(
                [
                    {
                        "note_path": "Atomic Notes/Id Only.md",
                        "representative_text": "Answer",
                    }
                ],
                vault=vault,
                client=client,
            )

        self.assertEqual(
            result.failures,
            [
                "Atomic Notes/Id Only.md: missing Obsidian-to-Anki TARGET DECK marker",
                "Atomic Notes/Id Only.md: expected balanced Obsidian-to-Anki START/END markers",
                "Atomic Notes/Id Only.md: missing Obsidian-to-Anki Basic model marker",
            ],
        )
        self.assertEqual(client.calls, [])

    def test_verify_requires_representative_text_for_anki_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            note = vault / "Atomic Notes"
            note.mkdir()
            (note / "Example.md").write_text(ANKI_BASIC_NOTE, encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "representative_text is required for Anki-backed notes",
            ):
                verify_entries(
                    [{"note_path": "Atomic Notes/Example.md"}],
                    vault=vault,
                    client=FakeAnkiClient(),
                )


if __name__ == "__main__":
    unittest.main()
