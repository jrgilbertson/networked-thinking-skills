import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests/fixtures/atomic-note-skill/filename-definition-alignment.json"


def normalized_text(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def filename_definition_text(path):
    return re.sub(r"^\d{12} ", "", Path(path).stem)


def definition_filename_text(sentence):
    return sentence.removesuffix(".")


class AtomicNoteSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_production_instructions_define_the_two_matching_pairs(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        for text in (doctrine, skill):
            self.assertIn("same single concept", text)
            self.assertIn("same level of specificity", text)
            self.assertIn("YAML `title`", text)
            self.assertIn("H1", text)
            self.assertIn("short concept name", text)

    def test_authoring_guidance_has_note_type_alignment_table(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        expected_rows = (
            "| Anki `Basic` | First definition sentence in `Back:` | Same single concept and same specificity |",
            "| Anki `Cloze` | Cloze-bearing definition sentence | Same single concept and same specificity |",
            "| Non-Anki DAE | First sentence under `## Definition` | Same single concept and same specificity |",
            "| Mixed or unclear local convention | Nearby atomic-note examples and user template | Follow local convention; do not force proposition filenames without evidence |",
        )
        for text_name, text in (("doctrine", doctrine), ("skill", skill)):
            for row in expected_rows:
                with self.subTest(text=text_name, row=row):
                    self.assertIn(row, text)

    def test_guidance_requires_evidence_for_proposition_style_filenames(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        for text in (doctrine, skill):
            self.assertIn("timestamp prefix alone", text)
            self.assertIn("user template", text)
            self.assertIn("nearby atomic notes", text)
            self.assertIn("mixed", text)
            self.assertIn("do not force", text)

    def test_synthetic_mismatches_cover_each_definition_source(self):
        cases = self.fixture["semantic_alignment_cases"]
        self.assertEqual(
            [case["note_type"] for case in cases],
            ["Anki Basic", "Anki Cloze", "Non-Anki DAE"],
        )
        self.assertEqual(
            [case["definition_source"] for case in cases],
            [
                "First definition sentence in Back:",
                "Cloze-bearing definition sentence",
                "First sentence under ## Definition or first visible DAE sentence",
            ],
        )
        for case in cases:
            with self.subTest(note_type=case["note_type"]):
                self.assertNotEqual(
                    filename_definition_text(case["path"]),
                    definition_filename_text(case["definition_sentence"]),
                )
                self.assertEqual(case["expected_finding"], "title_body_mismatch")
                self.assertTrue(case["display_title"])

    def test_remediation_requires_cli_rename_and_link_verification(self):
        remediation = normalized_text(ROOT / "shared/references/remediation-context.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        self.assertIn("Automatically update internal links", remediation)
        self.assertIn("official CLI `rename` or `move`", remediation)
        self.assertIn("Never rename an atomic-note file through the raw filesystem", remediation)
        self.assertIn("same representative links or backlinks", remediation)
        self.assertIn("If rename approval is denied", remediation)
        self.assertIn("valid as one filename component", remediation)
        self.assertIn("do not silently strip or substitute characters", remediation)
        self.assertIn("preview the content change and filename change together", remediation)
        self.assertIn("existing filename/Definition mismatch", remediation)
        self.assertIn("even when the Definition's first sentence is unchanged", remediation)
        self.assertIn("approval is required before either change is applied", remediation)
        self.assertIn("If it is disabled, stop before mutation", remediation)
        self.assertIn("explicitly confirm its state", remediation)
        self.assertIn("the same representative links or backlinks", remediation)
        self.assertIn("existing filename/Definition mismatch", skill)
        self.assertIn("report an unchanged pre-existing mismatch", skill)

    def test_fake_regression_example_covers_both_mismatches(self):
        before = self.fixture["before"]
        expected = self.fixture["expected"]
        self.assertNotEqual(
            filename_definition_text(before["path"]),
            definition_filename_text(before["definition_first_sentence"]),
        )
        self.assertNotEqual(before["yaml_title"], before["h1"])
        self.assertNotEqual(
            before["definition_first_sentence"],
            expected["definition_first_sentence"],
        )
        self.assertEqual(
            filename_definition_text(expected["path"]),
            definition_filename_text(expected["definition_first_sentence"]),
        )
        self.assertEqual(expected["yaml_title"], expected["h1"])

        steps = expected["required_steps"]
        self.assertIn("preview_both_matching_pairs", steps)
        self.assertIn("confirm_automatic_internal_link_updates", steps)
        self.assertIn("request_rename_approval", steps)
        self.assertIn("rename_with_official_obsidian_cli", steps)
        self.assertIn("verify_path_and_affected_links", steps)
        self.assertNotIn("rename_through_filesystem", steps)

    def test_fake_regression_example_preserves_alignment_when_rename_is_denied(self):
        denied = self.fixture["rename_denied"]
        self.assertEqual(
            filename_definition_text(denied["path"]),
            definition_filename_text(denied["definition_first_sentence"]),
        )
        self.assertEqual(denied["yaml_title"], denied["h1"])
        self.assertFalse(denied["definition_first_sentence_changed"])
        self.assertNotEqual(
            denied["definition_first_sentence"],
            denied["rejected_definition_first_sentence"],
        )

    def test_fake_regression_repairs_stale_filename_when_definition_is_unchanged(self):
        stale = self.fixture["stale_filename_unchanged"]
        self.assertNotEqual(
            filename_definition_text(stale["path"]),
            definition_filename_text(stale["definition_first_sentence"]),
        )
        self.assertFalse(stale["definition_first_sentence_changed"])
        steps = stale["required_steps"]
        self.assertIn("derive_filename_from_existing_definition", steps)
        self.assertIn("preview_filename_change", steps)
        self.assertIn("confirm_automatic_internal_link_updates", steps)
        self.assertIn("request_rename_approval", steps)
        self.assertIn("rename_with_official_obsidian_cli", steps)

    def test_invalid_filename_text_requires_redrafting_instead_of_substitution(self):
        invalid = self.fixture["invalid_filename"]
        derived = definition_filename_text(invalid["definition_first_sentence"])

        self.assertIn("/", derived)
        self.assertNotEqual(derived, invalid["forbidden_silent_filename"])
        self.assertEqual(
            invalid["required_action"],
            "redraft_first_sentence_with_learner",
        )


if __name__ == "__main__":
    unittest.main()
