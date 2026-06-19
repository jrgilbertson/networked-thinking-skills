from pathlib import Path
import unittest
from unittest.mock import patch

import shared.scripts.model_prompt as model_prompt
from shared.scripts.finding_codes import ALLOWED_FINDING_CODES, DAE_COMPONENT_LOSS_CAP, FINDING_CODE_SPECS
from shared.scripts.model_prompt import render_model_judgment_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPT_REFERENCE = REPO_ROOT / "shared" / "references" / "model-judgment-prompt.md"


class ModelPromptTest(unittest.TestCase):
    def test_reference_prompt_matches_renderer(self):
        self.assertEqual(
            PROMPT_REFERENCE.read_text(encoding="utf-8"),
            render_model_judgment_prompt(),
        )

    def test_prompt_contains_all_allowed_codes_and_losses(self):
        prompt = render_model_judgment_prompt()
        for code in ALLOWED_FINDING_CODES:
            with self.subTest(code=code):
                self.assertIn(f"`{code}`", prompt)
                self.assertIn(f"| `{code}` | {FINDING_CODE_SPECS[code].loss} |", prompt)

    def test_prompt_blocks_score_and_code_drift(self):
        prompt = render_model_judgment_prompt()
        self.assertIn("Do not invent codes.", prompt)
        self.assertIn("Do not prefix codes with `model_`.", prompt)
        self.assertIn("Do not output a score.", prompt)

    def test_prompt_contains_deduplication_examples(self):
        prompt = render_model_judgment_prompt()
        self.assertIn("Examples:", prompt)
        self.assertIn("not `weak_definition` or `weak_example`", prompt)
        self.assertIn(f"caps those DAE component losses at {DAE_COMPONENT_LOSS_CAP}", prompt)
        self.assertIn("not both `multi_note` and `not_atomic`", prompt)
        self.assertIn("set both `factual_risk` and `fact_check_required` to true", prompt)

    def test_prompt_deduplication_example_uses_dae_cap_constant(self):
        with patch.object(model_prompt, "DAE_COMPONENT_LOSS_CAP", 42):
            prompt = model_prompt.render_model_judgment_prompt()

        self.assertIn("caps those DAE component losses at 42", prompt)
        self.assertNotIn("caps those DAE component losses at 35", prompt)

    def test_prompt_contains_anki_yagni_sanity_check(self):
        prompt = render_model_judgment_prompt()
        self.assertIn("`anki_yagni`", prompt)
        self.assertIn("Confirm this Anki card is worth memorizing", prompt)
        self.assertIn("learner's domain", prompt)


if __name__ == "__main__":
    unittest.main()
