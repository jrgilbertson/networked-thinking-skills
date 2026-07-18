from pathlib import Path
import unittest

from shared.scripts.finding_codes import FINDING_MESSAGES


ROOT = Path(__file__).resolve().parents[1]


class FindingCodeContractTest(unittest.TestCase):
    def test_title_body_mismatch_covers_filename_stem_drift(self):
        message = FINDING_MESSAGES["title_body_mismatch"]

        self.assertIn("filename stem", message)
        self.assertIn("Definition", message)
        self.assertIn("specificity", message)
        self.assertIn("display title", message)

    def test_model_prompt_explains_when_filename_drift_applies(self):
        prompt = " ".join(
            (ROOT / "shared/references/model-judgment-prompt.md")
            .read_text(encoding="utf-8")
            .split()
        )

        self.assertIn("proposition-style timestamp filename", prompt)
        self.assertIn("broader, narrower, or different concept", prompt)
        self.assertIn("timestamp prefix alone", prompt)
        self.assertIn("title_body_mismatch", prompt)
        self.assertIn("first definition sentence in `Back:` for `Basic`", prompt)
        self.assertIn("cloze-bearing definition sentence for `Cloze`", prompt)
        self.assertIn("first visible Definition sentence for non-Anki DAE", prompt)


if __name__ == "__main__":
    unittest.main()
