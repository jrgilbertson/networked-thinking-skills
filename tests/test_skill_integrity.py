from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


SKILL_REFERENCES = {
    "atomic-note": [
        "shared/references/doctrine.md",
        "shared/references/remediation-context.md",
    ],
    "atomic-note-audit": [
        "shared/references/doctrine.md",
        "shared/references/audit-rubric.md",
        "shared/references/remediation-context.md",
        "shared/references/install-matrix.md",
    ],
}


class SkillIntegrityTest(unittest.TestCase):
    def test_skills_have_frontmatter_and_shared_references(self):
        for skill, references in SKILL_REFERENCES.items():
            with self.subTest(skill=skill):
                path = ROOT / "skills" / skill / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                self.assertIn(f"name: {skill}", text)
                self.assertIn("description: Use when", text)
                self.assertIn("shared/references/doctrine.md", text)
                for reference in references:
                    self.assertIn(reference, text)

    def test_shared_references_exist(self):
        for name in ["doctrine.md", "audit-rubric.md", "remediation-context.md", "install-matrix.md"]:
            with self.subTest(reference=name):
                self.assertTrue((ROOT / "shared/references" / name).exists())


if __name__ == "__main__":
    unittest.main()
