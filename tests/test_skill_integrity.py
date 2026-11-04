import re
import shutil
import tempfile
from pathlib import Path
import unittest

from shared.scripts.sync_skill_artifacts import find_stale_shared_references


ROOT = Path(__file__).resolve().parents[1]


SKILL_REFERENCES = {
    "managing-obsidian-tasks": [
        "references/task-contract.md",
    ],
    "atomic-note": [
        "references/doctrine.md",
        "references/remediation-context.md",
    ],
    "atomic-note-audit": [
        "references/doctrine.md",
        "references/audit-rubric.md",
        "references/model-judgment-prompt.md",
        "references/model-judgment-workflow.md",
        "references/audit-review-record.md",
        "references/remediation-context.md",
        "references/install-matrix.md",
    ],
}


def _required_reference_paths(text):
    lines = text.splitlines()
    try:
        start = next(
            index + 1
            for index, line in enumerate(lines)
            if line.lower() == "## required references"
        )
    except StopIteration as exc:
        raise AssertionError("Missing Required References section") from exc

    references = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        line = line.strip()
        match = re.match(r"- (?:`([^`]+)`|\[[^\]]+\]\(([^)]+)\))", line)
        if match:
            references.append(match.group(1) or match.group(2))
    return references


class SkillIntegrityTest(unittest.TestCase):
    def test_private_content_confirmation_precedes_model_judgment_workflow(self):
        text = (ROOT / "skills/atomic-note-audit/SKILL.md").read_text(encoding="utf-8")
        review_step = text.split("## Read-only audit", 1)[1].split("## Remediation", 1)[0]
        normalized = " ".join(review_step.split())

        confirmation = "confirm that the user accepts this provider/tool trust boundary"
        self.assertIn(confirmation, normalized)
        self.assertLess(
            normalized.index(confirmation),
            normalized.index("scripts/audit_inventory.py"),
        )

    def test_default_audit_is_model_led_plain_markdown(self):
        text = (ROOT / 'skills/atomic-note-audit/SKILL.md').read_text()
        workflow = text.split('## Read-only audit', 1)[1].split('## Remediation', 1)[0]
        self.assertIn('scripts/audit_inventory.py', workflow)
        self.assertNotIn('scripts/audit_notes.py', workflow)
        self.assertIn('recommendation first', workflow)
        self.assertIn('plain Markdown', workflow)
        self.assertIn('P0', workflow)

    def test_skills_have_frontmatter_and_skill_local_references(self):
        for skill, references in SKILL_REFERENCES.items():
            with self.subTest(skill=skill):
                path = ROOT / "skills" / skill / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                self.assertIn(f"name: {skill}", text)
                self.assertIn("description: Use when", text)
                for reference in references:
                    self.assertIn(reference, text)
                self.assertNotIn("../../shared", text)
                self.assertNotIn("shared.scripts", text)
                self.assertEqual(_required_reference_paths(text), references)

    def test_required_references_resolve_from_skill_directory(self):
        for skill in SKILL_REFERENCES:
            skill_dir = ROOT / "skills" / skill
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self._assert_required_references_exist(skill_dir, text, skill)

    def test_skill_only_install_layout_preserves_skill_references(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_home = Path(temp_dir)
            for skill in SKILL_REFERENCES:
                shutil.copytree(ROOT / "skills" / skill, runtime_home / "skills" / skill)

            for skill in SKILL_REFERENCES:
                skill_dir = runtime_home / "skills" / skill
                text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                self._assert_required_references_exist(skill_dir, text, skill)

    def test_shared_references_exist(self):
        for name in [
            "task-contract.md",
            "doctrine.md",
            "audit-rubric.md",
            "model-judgment-prompt.md",
            "model-judgment-workflow.md",
            "remediation-context.md",
            "install-matrix.md",
        ]:
            with self.subTest(reference=name):
                self.assertTrue((ROOT / "shared/references" / name).exists())

    def test_install_matrix_documents_self_contained_skill_layout(self):
        text = (ROOT / "shared/references/install-matrix.md").read_text(encoding="utf-8")
        self.assertIn("Self-contained skill installs", text)
        self.assertIn("`<runtime-home>/skills/<skill>`", text)
        self.assertNotIn("`<runtime-home>/shared/references`", text)

    def test_skill_artifacts_have_no_stale_shared_references(self):
        for skill in SKILL_REFERENCES:
            skill_dir = ROOT / "skills" / skill
            paths = [skill_dir / "SKILL.md"]
            for dirname in ("references", "schemas", "scripts"):
                artifact_dir = skill_dir / dirname
                if artifact_dir.exists():
                    paths.extend(
                        path
                        for path in sorted(artifact_dir.rglob("*"))
                        if path.is_file() and path.suffix in {".md", ".json", ".py"}
                    )

            for path in paths:
                with self.subTest(path=path.relative_to(ROOT)):
                    text = path.read_text(encoding="utf-8")
                    self.assertEqual(find_stale_shared_references(text), [])

    def test_remediation_reference_requires_durable_hold_tracking(self):
        text = (ROOT / "shared/references/remediation-context.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())

        self.assertIn("durable held-decision artifact", normalized)
        self.assertIn("Do not rely on chat history", normalized)
        self.assertIn("The artifact must include", normalized)
        self.assertIn("hold reason", normalized)
        self.assertIn("recommended decision", normalized)
        self.assertIn("next action needed from the learner", normalized)

    def _assert_required_references_exist(self, skill_dir, text, skill):
        for reference in _required_reference_paths(text):
            with self.subTest(skill=skill, reference=reference):
                self.assertTrue((skill_dir / reference).resolve().exists())


if __name__ == "__main__":
    unittest.main()
