from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


SKILL_REFERENCES = {
    "atomic-note": [
        "../../shared/references/doctrine.md",
        "../../shared/references/remediation-context.md",
    ],
    "atomic-note-audit": [
        "../../shared/references/doctrine.md",
        "../../shared/references/audit-rubric.md",
        "../../shared/references/remediation-context.md",
        "../../shared/references/install-matrix.md",
    ],
}


def _required_reference_paths(text):
    lines = text.splitlines()
    try:
        start = lines.index("## Required References") + 1
    except ValueError as exc:
        raise AssertionError("Missing Required References section") from exc

    references = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        line = line.strip()
        if line.startswith("- `") and line.endswith("`"):
            references.append(line.removeprefix("- `").removesuffix("`"))
    return references


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
                self.assertEqual(_required_reference_paths(text), references)

    def test_required_references_resolve_from_skill_directory(self):
        for skill in SKILL_REFERENCES:
            skill_dir = ROOT / "skills" / skill
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            for reference in _required_reference_paths(text):
                with self.subTest(skill=skill, reference=reference):
                    self.assertTrue((skill_dir / reference).resolve().exists())

    def test_shared_references_exist(self):
        for name in ["doctrine.md", "audit-rubric.md", "remediation-context.md", "install-matrix.md"]:
            with self.subTest(reference=name):
                self.assertTrue((ROOT / "shared/references" / name).exists())


if __name__ == "__main__":
    unittest.main()
