import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests/fixtures/atomic-note-skill"
NAMING_FIXTURE_PATH = FIXTURE_DIR / "filename-definition-alignment.json"
RECALL_FIXTURE_PATH = FIXTURE_DIR / "recall-friendly-structure-note.json"
STRUCTURE_LINK_FIXTURE_PATH = FIXTURE_DIR / "structure-note-link.json"


def normalized_text(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def filename_definition_text(path):
    return re.sub(r"^\d{12} ", "", Path(path).stem)


def definition_filename_text(sentence):
    return sentence.removesuffix(".")


class AtomicNoteSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(NAMING_FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.recall_fixture = json.loads(RECALL_FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.structure_link_fixture = json.loads(
            STRUCTURE_LINK_FIXTURE_PATH.read_text(encoding="utf-8")
        )

    def test_guidance_supports_recall_friendly_structure_notes(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")
        rubric = normalized_text(ROOT / "shared/references/audit-rubric.md")

        for text in (doctrine, skill):
            self.assertIn("conceptual navigation", text)
            self.assertIn("factual recall", text)
            self.assertIn("trivia", text)
            self.assertIn("learner", text)
            self.assertIn("not itself a DAE atomic note", text)

        self.assertIn("explicitly wants to practice factual recall or trivia", rubric)
        self.assertNotIn("rather than only as literary trivia", doctrine)
        self.assertNotIn("rather than only as literary trivia", skill)

    def test_fake_mythology_structure_example_preserves_recall_goal_and_quality_bar(self):
        expected = self.recall_fixture["expected"]
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        self.assertEqual(expected["structure_note"], "Structure Notes/Mythology.md")
        self.assertEqual(
            set(expected["supported_purposes"]),
            {"conceptual_navigation", "factual_recall", "trivia_review"},
        )
        self.assertTrue(expected["preserve_broad_topic_scope"])
        self.assertTrue(expected["children_remain_dae_atomic_notes"])
        self.assertTrue(expected["source_factual_claims_when_appropriate"])
        self.assertEqual(expected["quality_penalty_for_recall_orientation"], "none")

        if expected["preserve_broad_topic_scope"]:
            self.assertIn("navigation hub", doctrine)
            self.assertIn("narrowing or splitting the hub", skill)
        if expected["children_remain_dae_atomic_notes"]:
            self.assertIn("one concept in DAE form", doctrine)
            self.assertIn("apply the one-concept and DAE rules", skill)
        if expected["source_factual_claims_when_appropriate"]:
            self.assertIn("sources factual claims when appropriate", doctrine)
        self.assertEqual(expected["anki_decision"], "learner_goal_and_yagni_check")
        self.assertIn("Anki remains optional and learner-specific", doctrine)
        self.assertIn("learner-specific Anki-YAGNI check", skill)
        if expected["quality_penalty_for_recall_orientation"] == "none":
            self.assertIn("Recall or trivia orientation is not by itself a quality defect", doctrine)

    def test_production_instructions_define_the_two_matching_pairs(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        for text in (doctrine, skill):
            self.assertIn("Definition's first sentence", text)
            self.assertIn("final period", text)
            self.assertIn("YAML `title`", text)
            self.assertIn("H1", text)
            self.assertIn("short concept name", text)

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

    def test_structure_note_guidance_requires_full_unaliased_entries(self):
        remediation = normalized_text(ROOT / "shared/references/remediation-context.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        for text in (remediation, skill):
            self.assertIn("Structure Note entries", text)
            self.assertIn("`[[full note filename]]`", text)
            self.assertIn("`[[full note filename|display alias]]`", text)
            self.assertIn("explicitly requests an alias", text)
            self.assertIn("ordinary prose", text)

    def test_parent_link_fixture_adds_full_unaliased_filename(self):
        fixture = self.structure_link_fixture
        full_note_filename = Path(fixture["note_path"]).stem
        expected_entry = f"- [[{full_note_filename}]]"

        self.assertFalse(fixture["explicit_alias_requested"])
        self.assertEqual(fixture["expected_inserted_entry"], expected_entry)
        self.assertNotIn("|", fixture["expected_inserted_entry"])
        self.assertEqual(
            fixture["existing_structure_note_entries"] + [expected_entry],
            fixture["expected_structure_note_entries"],
        )

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
