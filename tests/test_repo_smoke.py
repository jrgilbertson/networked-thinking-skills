import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepoSmokeTest(unittest.TestCase):
    def test_plugin_manifests_are_valid_json(self):
        for path in [ROOT / ".codex-plugin/plugin.json", ROOT / ".claude-plugin/plugin.json"]:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["name"], "networked-thinking-skills")
            self.assertEqual(data["repository"], "https://github.com/jrgilbertson/networked-thinking-skills")
            self.assertEqual(len(data["skills"]), 2)
            for skill in data["skills"]:
                skill_path = ROOT / skill["path"]
                self.assertTrue(skill_path.exists(), f"{skill_path} does not exist")
                self.assertTrue((skill_path / "SKILL.md").exists(), f"{skill_path} lacks SKILL.md")

    def test_lefthook_runs_required_local_ci_checks(self):
        text = (ROOT / "lefthook.yml").read_text(encoding="utf-8")

        self.assertIn("python3 -m unittest discover -s tests", text)
        self.assertIn("python3 -m shared.scripts.validate_jsonl tests/golden/fixture-audit.jsonl", text)
        self.assertIn("python3 -m shared.scripts.verify_install_commands docs/install.md", text)
        self.assertIn("python3 -m shared.scripts.sync_skill_artifacts --check", text)


if __name__ == "__main__":
    unittest.main()
