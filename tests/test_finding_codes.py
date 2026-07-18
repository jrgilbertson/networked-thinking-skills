from pathlib import Path
import unittest

from shared.scripts.finding_codes import FINDING_MESSAGES


ROOT = Path(__file__).resolve().parents[1]


class FindingCodeContractTest(unittest.TestCase):
    def test_title_body_mismatch_covers_both_naming_pairs(self):
        message = FINDING_MESSAGES["title_body_mismatch"]

        self.assertIn("timestamp-stripped filename", message)
        self.assertIn("applicable Definition source", message)
        self.assertIn("exactly match", message)
        self.assertIn("YAML title and H1", message)
        self.assertIn("short concept name", message)
        self.assertIn("approved rename flow", message)

    def test_model_prompt_explains_canonical_filename_alignment(self):
        prompt = " ".join(
            (ROOT / "shared/references/model-judgment-prompt.md")
            .read_text(encoding="utf-8")
            .split()
        )

        self.assertIn("canonical Networked Thinking filename rule", prompt)
        self.assertIn("exactly match the reader-visible", prompt)
        self.assertIn(
            "All other visible words, capitalization, punctuation, and word order must match",
            prompt,
        )
        self.assertIn("title_body_mismatch", prompt)
        self.assertIn("first visible DAE sentence after the H1", prompt)
        self.assertIn("first Definition sentence in `Back:`", prompt)
        self.assertIn("rendered cloze-bearing Definition sentence", prompt)
        self.assertIn("Anki cloze syntax", prompt)
        self.assertIn("model judgment evaluates the canonical contract", prompt)
        self.assertNotIn("provided vault context", prompt)
        self.assertNotIn("proposition-style", prompt)


if __name__ == "__main__":
    unittest.main()
