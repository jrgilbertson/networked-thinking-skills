from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills/managing-obsidian-tasks"


def normalized_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class ManagingObsidianTasksSkillTest(unittest.TestCase):
    def test_baseline_record_covers_approved_flows(self):
        text = normalized_text(
            ROOT / "tests/fixtures/managing-obsidian-tasks-skill/baseline.md"
        )

        self.assertIn("Human follow-up task", text)
        self.assertIn("Agent-first research task", text)
        self.assertIn("Waiting transition", text)
        self.assertIn("fresh agent context", text)

    def test_trigger_record_has_full_rigor_pass(self):
        text = normalized_text(
            ROOT / "tests/fixtures/managing-obsidian-tasks-skill/trigger-queries.md"
        )

        self.assertIn("eight should-trigger and eight near-miss", text)
        self.assertEqual(text.count("| yes | yes | yes | Pass |"), 8)
        self.assertEqual(text.count("| no | no | no | Pass |"), 7)
        self.assertIn("| no | no | no | Pass after tuning |", text)

    def test_skill_is_portable_and_routes_issues_away(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("name: managing-obsidian-tasks", text)
        self.assertIn("Use when the user explicitly says task, todo, or personal Kanban", text)
        self.assertIn('Requests phrased only as "track this for later"', text)
        self.assertIn("work bound for GitHub, Linear, or a Codex conversation", text)
        self.assertNotIn("/Users/", text)
        self.assertNotIn("jason-obsidian", text)

    def test_every_vault_operation_uses_obsidian_cli(self):
        text = normalized_text(SKILL_DIR / "SKILL.md")

        self.assertIn("official Obsidian CLI for every vault search", text)
        self.assertIn("Raw filesystem access is not a fallback", text)
        self.assertIn("exact vault-relative path", text)
        self.assertIn("`--vault <vault-name>`", text)
        self.assertIn("never forward a raw `vault=` argument", text)
        self.assertIn("Re-read the note after every mutation", text)
        self.assertIn("only when its CLI result was obtained", text)
        self.assertIn("app.vault.process(file, updater)", text)
        contract = normalized_text(ROOT / "shared/references/task-contract.md")
        self.assertIn("Do not invoke linting or set them manually", contract)

    def test_creation_requires_preview_and_approval(self):
        text = normalized_text(SKILL_DIR / "SKILL.md")

        self.assertIn("Present the proposed filename, complete metadata, and populated body", text)
        self.assertIn("Wait for explicit approval before writing every new task", text)
        self.assertIn("including when the request already says \"create a task.\"", text)

    def test_template_access_and_bases_compatibility_cover_runtime_operations(self):
        text = normalized_text(SKILL_DIR / "SKILL.md")

        self.assertIn("Read `assets/task-template.md` when creating a task", text)
        self.assertIn("Read the other files under `assets/` only when setting up or repairing", text)
        self.assertIn(
            "Bases plugin is required for setup, search, create, update, and close",
            text,
        )

    def test_setup_and_creation_revalidate_the_approved_baseline_before_writing(self):
        text = normalized_text(SKILL_DIR / "SKILL.md")

        self.assertIn("immediately before each write", text)
        self.assertIn("confirm that it remains absent", text)
        self.assertIn("approved baseline", text)
        self.assertIn("immediately before the write, confirm that the exact target remains absent", text)
        self.assertIn("approved absence baseline", text)
        self.assertIn("abort the write", text)
        self.assertIn("request approval again", text)
        self.assertIn("CLI `create` operation without overwrite", text)

    def test_creation_status_matches_required_field_readiness(self):
        skill = normalized_text(SKILL_DIR / "SKILL.md")
        contract = normalized_text(ROOT / "shared/references/task-contract.md")
        template = normalized_text(SKILL_DIR / "assets/task-template.md")

        self.assertIn(
            "status to `todo` when every required value is resolved", skill
        )
        self.assertIn("`triage` when any required value is `unknown`", skill)
        self.assertIn("status: todo", contract)
        self.assertIn("status: triage", template)
        self.assertIn("unknown", template)

    def test_contract_has_required_enums_without_tags_or_schema_field(self):
        text = normalized_text(ROOT / "shared/references/task-contract.md")

        for field in (
            "status",
            "priority",
            "execution_shape",
            "task_type",
            "human_energy",
            "source_type",
            "goal",
        ):
            self.assertIn(field, text)
        for value in (
            "waiting-for",
            "blocked",
            "agent-first",
            "investigate",
            "agent-recommendation",
        ):
            self.assertIn(value, text)
        self.assertIn("task notes do not carry a schema version", text)
        self.assertIn("Do not use tags in task notes", text)
        self.assertIn("required vault-managed properties", text)
        self.assertIn("YYYY-MM-DD HH:mm", text)
        self.assertNotIn("task_id", text)

    def test_task_template_has_required_body_sections(self):
        text = (SKILL_DIR / "assets/task-template.md").read_text(encoding="utf-8")

        for heading in (
            "# Descriptive task title",
            "## Context",
            "## Definition of done",
            "## Inputs",
            "## Constraints",
            "## Source",
            "## Deliverables",
            "## Result",
            "## Work log",
        ):
            self.assertIn(heading, text)
        self.assertNotIn("tags:", text)
        self.assertNotIn("schema:", text)
        self.assertNotIn("task_id:", text)
        self.assertIn("Source provenance is unresolved.", text)
        self.assertNotIn("Direct user request.", text)

    def test_closure_date_uses_the_actual_transition_date(self):
        text = normalized_text(ROOT / "shared/references/task-contract.md")

        self.assertIn('date_closed: "<actual transition date, YYYY-MM-DD>"', text)
        self.assertIn("Set `date_closed` to the actual date of the transition", text)
        self.assertNotIn("date_closed: 2026-07-20", text)

    def test_base_has_every_approved_view_and_folder_boundary(self):
        text = (SKILL_DIR / "assets/tasks.base").read_text(encoding="utf-8")

        self.assertIn('file.inFolder("Tasks")', text)
        for name in (
            "Triage",
            "Todo",
            "In progress",
            "Waiting for",
            "Blocked",
            "History",
            "All tasks",
        ):
            self.assertIn(f"name: {name}", text)

    def test_structure_note_embeds_every_base_view(self):
        text = (SKILL_DIR / "assets/tasks-structure-note.md").read_text(encoding="utf-8")

        for name in (
            "Triage",
            "Todo",
            "In progress",
            "Waiting for",
            "Blocked",
            "History",
            "All tasks",
        ):
            self.assertIn(f"![[Tasks.base#{name}]]", text)


if __name__ == "__main__":
    unittest.main()
