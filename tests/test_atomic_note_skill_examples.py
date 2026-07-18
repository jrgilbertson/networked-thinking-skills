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


def rendered_definition_filename_text(sentence):
    text = re.sub(r"\{\{c\d+::(.*?)(?:::[^{}]*)?\}\}", r"\1", sentence)
    text = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"~~([^~\n]+)~~", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", text)
    text = re.sub(r"\*\*|__|`", "", text)
    return text.removesuffix(".")


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
        request = self.recall_fixture["request"]
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        self.assertIn("Create a DAE atomic note", request)
        self.assertIn("then update a broad Mythology structure note", request)
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
            self.assertIn("reader-visible wording", text)
            self.assertIn("applicable Definition source", text)
            self.assertIn(
                "All other visible words, capitalization, punctuation, and word order must match",
                text,
            )
            self.assertIn("Markdown wrappers", text)
            self.assertIn("Anki cloze syntax", text)
            self.assertIn("YAML `title`", text)
            self.assertIn("H1", text)
            self.assertIn("short concept name", text)
            self.assertNotIn("proposition-style", text)

    def test_rendered_definition_filename_text_removes_markdown_wrappers(self):
        cases = (
            ("[Visible words](https://example.com).", "Visible words"),
            ("*Visible words*.", "Visible words"),
            ("_Visible words_.", "Visible words"),
            ("~~Visible words~~.", "Visible words"),
        )

        for sentence, expected in cases:
            with self.subTest(sentence=sentence):
                self.assertEqual(rendered_definition_filename_text(sentence), expected)

    def test_authoring_guidance_has_note_type_alignment_table(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        expected_rows = (
            "| Plain-prose DAE, with or without Anki | First visible DAE sentence after the H1 | "
            "Exact reader-visible wording without the final period |",
            "| Legacy headed DAE, with or without Anki | First sentence under `## Definition` | "
            "Exact reader-visible wording without the final period |",
            "| Anki `Basic` with DAE stored only in `Back:` | First Definition sentence in `Back:` | "
            "Exact reader-visible wording without the final period |",
            "| Anki `Cloze` with DAE stored only in the card body | Rendered cloze-bearing Definition sentence | "
            "Exact reader-visible wording without the final period |",
        )
        for text_name, text in (("doctrine", doctrine), ("skill", skill)):
            for row in expected_rows:
                with self.subTest(text=text_name, row=row):
                    self.assertIn(row, text)

    def test_guidance_treats_nonstandard_vaults_as_a_compatibility_exception(self):
        doctrine = normalized_text(ROOT / "shared/references/doctrine.md")
        skill = normalized_text(ROOT / "skills/atomic-note/SKILL.md")

        for text in (doctrine, skill):
            self.assertIn("pre-existing user vault", text)
            self.assertIn("compatibility exception", text)
            self.assertIn("learner or governing template explicitly declares", text)
            self.assertIn("Do not describe it as another Networked Thinking naming style", text)

    def test_synthetic_cases_cover_aligned_and_misaligned_definition_sources(self):
        cases = self.fixture["alignment_cases"]
        self.assertGreaterEqual(
            {case["note_shape"] for case in cases},
            {
                "Anki Basic with DAE only in Back",
                "Anki Cloze with DAE only in card body",
                "Plain-prose DAE",
            },
        )
        self.assertIn(True, [case["expected_aligned"] for case in cases])
        self.assertIn(False, [case["expected_aligned"] for case in cases])

        for case in cases:
            with self.subTest(note_shape=case["note_shape"]):
                aligned = (
                    filename_definition_text(case["path"]),
                    rendered_definition_filename_text(case["definition_sentence"]),
                )
                self.assertEqual(aligned[0] == aligned[1], case["expected_aligned"])
                self.assertEqual(
                    case["expected_finding"],
                    None if case["expected_aligned"] else "title_body_mismatch",
                )
                self.assertTrue(case["display_title"])

    def test_optional_anki_fixture_uses_visible_dae_definition_for_its_filename(self):
        note = next(
            (ROOT / "tests/fixtures/tiny-vault/Atomic Notes").glob(
                "202601010107 *.md"
            )
        )
        body = note.read_text(encoding="utf-8")
        definition = re.search(r"# Optional Anki note\n\n(.+?\.)", body, re.DOTALL)

        self.assertIsNotNone(definition)
        visible_sentence = " ".join(definition.group(1).split())
        self.assertEqual(
            filename_definition_text(note),
            rendered_definition_filename_text(visible_sentence),
        )

    def test_compatibility_exception_is_interactive_only(self):
        exception = self.fixture["compatibility_exception"]

        self.assertEqual(exception["declaration_source"], "learner_or_governing_template")
        self.assertEqual(exception["scope"], "interactive_authoring_and_remediation")
        self.assertEqual(exception["audit_without_vault_context"], "evaluate_canonical_contract")

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
        self.assertIn("use a content-only flow", remediation)
        self.assertIn("obtain explicit approval", remediation)
        self.assertIn("Obsidian app-context modify operation", remediation)
        self.assertIn("Do not require a rename or rename approval", remediation)
        self.assertIn("only when that pair would differ", remediation)
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
            rendered_definition_filename_text(before["definition_first_sentence"]),
        )
        self.assertNotEqual(before["yaml_title"], before["h1"])
        self.assertNotEqual(
            before["definition_first_sentence"],
            expected["definition_first_sentence"],
        )
        self.assertEqual(
            filename_definition_text(expected["path"]),
            rendered_definition_filename_text(expected["definition_first_sentence"]),
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
            rendered_definition_filename_text(denied["definition_first_sentence"]),
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
            rendered_definition_filename_text(stale["definition_first_sentence"]),
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
        derived = rendered_definition_filename_text(invalid["definition_first_sentence"])

        self.assertIn("/", derived)
        self.assertNotEqual(derived, invalid["forbidden_silent_filename"])
        self.assertEqual(
            invalid["required_action"],
            "redraft_first_sentence_with_learner",
        )


if __name__ == "__main__":
    unittest.main()
