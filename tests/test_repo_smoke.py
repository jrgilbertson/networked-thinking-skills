import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepoSmokeTest(unittest.TestCase):
    def test_plugin_manifests_are_valid_json(self):
        for path in [ROOT / ".codex-plugin/plugin.json", ROOT / ".claude-plugin/plugin.json"]:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["name"], "networked-thinking-skills")
            self.assertEqual(len(data["skills"]), 2)
            for skill in data["skills"]:
                skill_path = ROOT / skill["path"]
                self.assertTrue(skill_path.exists(), f"{skill_path} does not exist")
                self.assertTrue((skill_path / "SKILL.md").exists(), f"{skill_path} lacks SKILL.md")


if __name__ == "__main__":
    unittest.main()
