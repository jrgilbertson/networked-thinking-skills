# Npx Skills Publishable Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `atomic-note` and `atomic-note-audit` install as self-contained `npx skills add` directories with their references, schemas, and runnable helper code included.

**Architecture:** Keep `shared/` as the canonical development source for references, schemas, and helper Python. Add a sync/validation script that generates checked-in skill-local artifacts under `skills/<skill>/`, rewrites installed paths/imports, and fails on drift or stale shared references. Update skill instructions, docs, tests, and hooks so the installable skill directory is the verified contract.

**Tech Stack:** Python 3.11 stdlib, `unittest`, `npx skills`, existing `lefthook` pre-commit checks.

---

## File Structure

- Create `shared/scripts/sync_skill_artifacts.py`
  - Owns artifact specs, path/import rewrites, sync mode, and check mode.
  - Reads canonical files from `shared/references`, `shared/schemas`, and `shared/scripts`.
  - Writes generated copies to `skills/<skill>/{references,schemas,scripts}`.
- Create `tests/test_skill_artifact_sync.py`
  - Unit tests for artifact specs, script import rewriting, stale-reference detection, and check-mode drift.
- Modify `tests/test_skill_integrity.py`
  - Replace old shared-layout assertions with skill-local reference and copied-layout assertions.
- Modify `tests/test_repo_smoke.py`
  - Require the new artifact sync check in `lefthook.yml` and validate plugin repository metadata.
- Modify `lefthook.yml`
  - Add `python3 -m shared.scripts.sync_skill_artifacts --check`.
- Modify `skills/atomic-note/SKILL.md`
  - Use skill-local `references/*` and `scripts/obsidian_cli.py`.
- Modify `skills/atomic-note-audit/SKILL.md`
  - Use skill-local references, schemas, and scripts.
- Modify `shared/references/install-matrix.md`
  - Replace the old runtime-home shared-reference layout with self-contained skill directory guidance.
- Generate checked-in files under:
  - `skills/atomic-note/references/`
  - `skills/atomic-note/scripts/`
  - `skills/atomic-note-audit/references/`
  - `skills/atomic-note-audit/schemas/`
  - `skills/atomic-note-audit/scripts/`
- Modify `README.md` and `docs/install.md`
  - Make `npx skills add` the public install path.
  - Remove post-install `shared/references` copy commands.
- Modify `docs/audit-workflow.md`, `docs/remediation.md`, and `docs/rubric.md`
  - Make user-facing workflow commands consistent with installed skill-root helper paths or explicitly label repo-development-only commands.
- Modify `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`
  - Correct stale repository metadata if still present.

Do not add `skills.sh.json` in this implementation unless live verification shows a public display problem that it solves. It is not needed for runtime correctness.

## Artifact Inventory

`atomic-note` copies:

- references: `doctrine.md`, `remediation-context.md`
- scripts: `obsidian_adapter.py`, `obsidian_cli.py`, `verify_anki_notes.py`

`atomic-note-audit` copies:

- references: `doctrine.md`, `audit-rubric.md`, `model-judgment-prompt.md`, `remediation-context.md`, `install-matrix.md`
- schemas: `audit-row.schema.json`, `config.schema.json`, `model-judgment.schema.json`, `remediation-plan.schema.json`, `run-manifest.schema.json`
- scripts: `__init__.py`, `apply_model_judgments.py`, `audit_engine.py`, `audit_notes.py`, `base_generation.py`, `collect_model_judgments.py`, `config.py`, `finding_codes.py`, `generate_base.py`, `generate_report.py`, `markdown_parse.py`, `model_contract.py`, `model_prompt.py`, `obsidian_adapter.py`, `obsidian_cli.py`, `preflight_obsidian.py`, `prepare_model_judgment.py`, `remediate_notes.py`, `remediation.py`, `reporting.py`, `schema_validation.py`, `scoring.py`, `split_note.py`, `validate_jsonl.py`, `verify_anki_notes.py`

Explicitly exclude repo-only helpers from installed skills: `make_fixture_vault.py` and `verify_install_commands.py`.

### Task 1: Add Artifact Sync Unit Tests

**Files:**
- Create: `tests/test_skill_artifact_sync.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_skill_artifact_sync.py` with:

```python
from pathlib import Path
import tempfile
import textwrap
import unittest

from shared.scripts.sync_skill_artifacts import (
    ARTIFACT_SPECS,
    ROOT,
    SkillArtifactSpec,
    find_stale_shared_references,
    render_markdown_text,
    render_script_text,
    sync_artifacts,
)


class SkillArtifactSyncTest(unittest.TestCase):
    def test_specs_include_required_runtime_files(self):
        self.assertEqual(
            ARTIFACT_SPECS["atomic-note"].references,
            ("doctrine.md", "remediation-context.md"),
        )
        self.assertEqual(
            ARTIFACT_SPECS["atomic-note"].scripts,
            ("obsidian_adapter.py", "obsidian_cli.py", "verify_anki_notes.py"),
        )
        audit = ARTIFACT_SPECS["atomic-note-audit"]
        self.assertIn("model-judgment.schema.json", audit.schemas)
        self.assertIn("audit_notes.py", audit.scripts)
        self.assertIn("obsidian_cli.py", audit.scripts)
        self.assertNotIn("make_fixture_vault.py", audit.scripts)
        self.assertNotIn("verify_install_commands.py", audit.scripts)

    def test_render_markdown_rewrites_shared_paths(self):
        source = textwrap.dedent(
            """\
            Load `../../shared/references/doctrine.md`.
            Run `python3 -m shared.scripts.audit_notes --help`.
            Validate `shared/schemas/model-judgment.schema.json`.
            See `shared/scripts/finding_codes.py`.
            """
        )

        rendered = render_markdown_text(source)

        self.assertIn("`references/doctrine.md`", rendered)
        self.assertIn("`python3 scripts/audit_notes.py --help`", rendered)
        self.assertIn("`schemas/model-judgment.schema.json`", rendered)
        self.assertIn("`scripts/finding_codes.py`", rendered)
        self.assertEqual(find_stale_shared_references(rendered), [])

    def test_render_script_rewrites_imports(self):
        source = textwrap.dedent(
            """\
            from shared.scripts.schema_validation import ValidationError
            from shared.scripts.scoring import compute_clean
            """
        )

        rendered = render_script_text(source)

        self.assertIn("from schema_validation import ValidationError", rendered)
        self.assertIn("from scoring import compute_clean", rendered)
        self.assertEqual(find_stale_shared_references(rendered), [])

    def test_find_stale_shared_references_reports_all_forms(self):
        text = " ".join(
            [
                "../../shared/references/doctrine.md",
                "../shared/references/doctrine.md",
                "shared/scripts/audit_notes.py",
                "shared.scripts.audit_notes",
                "from shared import scripts",
            ]
        )

        findings = find_stale_shared_references(text)

        self.assertEqual(
            findings,
            [
                "../../shared",
                "../shared",
                "shared/",
                "shared.scripts",
                "from shared",
            ],
        )

    def test_sync_check_reports_drift_without_writing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "shared/references").mkdir(parents=True)
            (root / "shared/schemas").mkdir(parents=True)
            (root / "shared/scripts").mkdir(parents=True)
            (root / "skills/demo").mkdir(parents=True)
            (root / "skills/demo/SKILL.md").write_text(
                "---\nname: demo\ndescription: Use when testing.\n---\n",
                encoding="utf-8",
            )
            (root / "shared/references/doctrine.md").write_text("doctrine\n", encoding="utf-8")
            spec = {
                "demo": SkillArtifactSpec(
                    name="demo",
                    references=("doctrine.md",),
                    schemas=(),
                    scripts=(),
                )
            }

            errors = sync_artifacts(root=root, specs=spec, check=True)

            self.assertEqual(
                errors,
                ["skills/demo/references/doctrine.md is missing or out of sync"],
            )
            self.assertFalse((root / "skills/demo/references/doctrine.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m unittest tests.test_skill_artifact_sync -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'shared.scripts.sync_skill_artifacts'`.

- [ ] **Step 3: Keep the failing test uncommitted**

Do not commit at this red step. The repo's pre-commit hook runs the full test
suite, so commit only after Task 2 makes this test pass.

### Task 2: Implement Artifact Sync Tool

**Files:**
- Create: `shared/scripts/sync_skill_artifacts.py`

- [ ] **Step 1: Add the sync tool**

Create `shared/scripts/sync_skill_artifacts.py` with:

```python
"""Sync generated self-contained skill artifacts from canonical shared files."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SkillArtifactSpec:
    name: str
    references: tuple[str, ...]
    schemas: tuple[str, ...]
    scripts: tuple[str, ...]


ARTIFACT_SPECS: dict[str, SkillArtifactSpec] = {
    "atomic-note": SkillArtifactSpec(
        name="atomic-note",
        references=("doctrine.md", "remediation-context.md"),
        schemas=(),
        scripts=("obsidian_adapter.py", "obsidian_cli.py", "verify_anki_notes.py"),
    ),
    "atomic-note-audit": SkillArtifactSpec(
        name="atomic-note-audit",
        references=(
            "doctrine.md",
            "audit-rubric.md",
            "model-judgment-prompt.md",
            "remediation-context.md",
            "install-matrix.md",
        ),
        schemas=(
            "audit-row.schema.json",
            "config.schema.json",
            "model-judgment.schema.json",
            "remediation-plan.schema.json",
            "run-manifest.schema.json",
        ),
        scripts=(
            "__init__.py",
            "apply_model_judgments.py",
            "audit_engine.py",
            "audit_notes.py",
            "base_generation.py",
            "collect_model_judgments.py",
            "config.py",
            "finding_codes.py",
            "generate_base.py",
            "generate_report.py",
            "markdown_parse.py",
            "model_contract.py",
            "model_prompt.py",
            "obsidian_adapter.py",
            "obsidian_cli.py",
            "preflight_obsidian.py",
            "prepare_model_judgment.py",
            "remediate_notes.py",
            "remediation.py",
            "reporting.py",
            "schema_validation.py",
            "scoring.py",
            "split_note.py",
            "validate_jsonl.py",
            "verify_anki_notes.py",
        ),
    ),
}

STALE_PATTERNS = (
    ("../../shared", re.compile(r"\.\./\.\./shared")),
    ("../shared", re.compile(r"\.\./shared")),
    ("shared/", re.compile(r"shared/")),
    ("shared.scripts", re.compile(r"shared\.scripts")),
    ("from shared", re.compile(r"\bfrom shared\b")),
    ("import shared", re.compile(r"\bimport shared\b")),
)


def render_markdown_text(text: str) -> str:
    text = text.replace("../../shared/references/", "references/")
    text = text.replace("../shared/references/", "references/")
    text = text.replace("shared/references/", "references/")
    text = text.replace("shared/scripts/", "scripts/")
    text = text.replace("shared/schemas/", "schemas/")
    return re.sub(
        r"python3 -m shared\.scripts\.([A-Za-z_][A-Za-z0-9_]*)",
        r"python3 scripts/\1.py",
        text,
    )


def render_script_text(text: str) -> str:
    text = text.replace("from shared.scripts.", "from ")
    text = text.replace("import shared.scripts.", "import ")
    return text


def find_stale_shared_references(text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in STALE_PATTERNS:
        if pattern.search(text):
            findings.append(label)
    return findings


def sync_artifacts(
    *,
    root: Path = ROOT,
    specs: dict[str, SkillArtifactSpec] = ARTIFACT_SPECS,
    check: bool = False,
) -> list[str]:
    errors: list[str] = []
    for spec in specs.values():
        skill_dir = root / "skills" / spec.name
        if not (skill_dir / "SKILL.md").exists():
            errors.append(f"skills/{spec.name}/SKILL.md is missing")
            continue

        _sync_group(
            errors,
            root=root,
            skill_dir=skill_dir,
            source_dir=root / "shared" / "references",
            dest_name="references",
            filenames=spec.references,
            renderer=render_markdown_text,
            check=check,
        )
        _sync_group(
            errors,
            root=root,
            skill_dir=skill_dir,
            source_dir=root / "shared" / "schemas",
            dest_name="schemas",
            filenames=spec.schemas,
            renderer=lambda text: text,
            check=check,
        )
        _sync_group(
            errors,
            root=root,
            skill_dir=skill_dir,
            source_dir=root / "shared" / "scripts",
            dest_name="scripts",
            filenames=spec.scripts,
            renderer=render_script_text,
            check=check,
        )
        _validate_skill_files(errors, root=root, skill_dir=skill_dir)
    return errors


def _sync_group(
    errors: list[str],
    *,
    root: Path,
    skill_dir: Path,
    source_dir: Path,
    dest_name: str,
    filenames: tuple[str, ...],
    renderer,
    check: bool,
) -> None:
    dest_dir = skill_dir / dest_name
    if not filenames:
        if not check and dest_dir.exists():
            shutil.rmtree(dest_dir)
        return
    if not check:
        dest_dir.mkdir(parents=True, exist_ok=True)

    expected = set(filenames)
    if dest_dir.exists():
        for existing in dest_dir.iterdir():
            if existing.is_file() and existing.name not in expected:
                rel = existing.relative_to(root)
                if check:
                    errors.append(f"{rel} is not declared in artifact spec")
                else:
                    existing.unlink()

    for filename in filenames:
        source_path = source_dir / filename
        dest_path = dest_dir / filename
        if not source_path.exists():
            errors.append(f"{source_path.relative_to(root)} is missing")
            continue
        expected_text = renderer(source_path.read_text(encoding="utf-8"))
        if check:
            if not dest_path.exists() or dest_path.read_text(encoding="utf-8") != expected_text:
                errors.append(f"{dest_path.relative_to(root)} is missing or out of sync")
        else:
            dest_path.write_text(expected_text, encoding="utf-8")


def _validate_skill_files(errors: list[str], *, root: Path, skill_dir: Path) -> None:
    paths = [skill_dir / "SKILL.md"]
    for child in ("references", "schemas", "scripts"):
        child_dir = skill_dir / child
        if child_dir.exists():
            paths.extend(path for path in child_dir.rglob("*") if path.is_file())

    for path in paths:
        text = path.read_text(encoding="utf-8")
        findings = find_stale_shared_references(text)
        if findings:
            rel = path.relative_to(root)
            errors.append(f"{rel} contains stale shared reference(s): {', '.join(findings)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if generated artifacts are stale")
    args = parser.parse_args(argv)

    errors = sync_artifacts(check=args.check)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("skill_artifacts=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the sync tests**

Run:

```bash
python3 -m unittest tests.test_skill_artifact_sync -v
```

Expected: PASS.

- [ ] **Step 3: Run the sync tool in check mode to expose current drift**

Run:

```bash
python3 -m shared.scripts.sync_skill_artifacts --check
```

Expected: FAIL with missing generated artifact paths and stale `shared` references in current `SKILL.md` files.

- [ ] **Step 4: Commit the green sync tool and test**

```bash
git add shared/scripts/sync_skill_artifacts.py tests/test_skill_artifact_sync.py
git commit -m "feat: add skill artifact sync checker"
```

### Task 3: Replace Old Skill Integrity Contract

**Files:**
- Modify: `tests/test_skill_integrity.py`
- Modify: `tests/test_repo_smoke.py`
- Modify: `lefthook.yml`

- [ ] **Step 1: Rewrite `tests/test_skill_integrity.py` expectations**

Replace the old `SKILL_REFERENCES` values with skill-local references:

```python
SKILL_REFERENCES = {
    "atomic-note": [
        "references/doctrine.md",
        "references/remediation-context.md",
    ],
    "atomic-note-audit": [
        "references/doctrine.md",
        "references/audit-rubric.md",
        "references/model-judgment-prompt.md",
        "references/remediation-context.md",
        "references/install-matrix.md",
    ],
}
```

Replace `test_skills_have_frontmatter_and_shared_references` with:

```python
def test_skills_have_frontmatter_and_skill_local_references(self):
    for skill, references in SKILL_REFERENCES.items():
        with self.subTest(skill=skill):
            path = ROOT / "skills" / skill / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"))
            self.assertIn(f"name: {skill}", text)
            self.assertIn("description: Use when", text)
            self.assertIn("references/doctrine.md", text)
            self.assertNotIn("../../shared", text)
            self.assertNotIn("shared.scripts", text)
            self.assertEqual(_required_reference_paths(text), references)
```

Replace `test_raw_install_layout_preserves_skill_references` with:

```python
def test_skill_only_install_layout_preserves_skill_references(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        runtime_home = Path(temp_dir)
        for skill in SKILL_REFERENCES:
            shutil.copytree(ROOT / "skills" / skill, runtime_home / "skills" / skill)

        for skill in SKILL_REFERENCES:
            skill_dir = runtime_home / "skills" / skill
            text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self._assert_required_references_exist(skill_dir, text, skill)
```

Delete `test_skill_only_raw_install_layout_does_not_satisfy_references`.

Replace `test_install_matrix_documents_raw_skill_layout` with:

```python
def test_install_matrix_documents_self_contained_skill_layout(self):
    text = (ROOT / "shared/references/install-matrix.md").read_text(encoding="utf-8")
    self.assertIn("Self-contained skill installs", text)
    self.assertIn("`<runtime-home>/skills/<skill>`", text)
    self.assertNotIn("`<runtime-home>/shared/references`", text)
```

Add this import:

```python
from shared.scripts.sync_skill_artifacts import find_stale_shared_references
```

Add this test:

```python
def test_skill_artifacts_have_no_stale_shared_references(self):
    for skill in SKILL_REFERENCES:
        skill_dir = ROOT / "skills" / skill
        paths = [skill_dir / "SKILL.md"]
        for child in ("references", "schemas", "scripts"):
            child_dir = skill_dir / child
            if child_dir.exists():
                paths.extend(path for path in child_dir.rglob("*") if path.is_file())

        for path in paths:
            with self.subTest(skill=skill, path=path.relative_to(ROOT)):
                findings = find_stale_shared_references(path.read_text(encoding="utf-8"))
                self.assertEqual(findings, [])
```

- [ ] **Step 2: Update repo smoke tests**

In `tests/test_repo_smoke.py`, add repository checks to `test_plugin_manifests_are_valid_json`:

```python
self.assertEqual(data["repository"], "https://github.com/jrgilbertson/networked-thinking-skills")
```

In `test_lefthook_runs_required_local_ci_checks`, add:

```python
self.assertIn("python3 -m shared.scripts.sync_skill_artifacts --check", text)
```

- [ ] **Step 3: Add the sync check to `lefthook.yml`**

Add this command under `pre-commit.commands`:

```yaml
    skill-artifacts:
      run: python3 -m shared.scripts.sync_skill_artifacts --check
```

- [ ] **Step 4: Run tests to verify the new contract fails before artifacts are generated**

Run:

```bash
python3 -m unittest tests.test_skill_integrity tests.test_repo_smoke -v
```

Expected: FAIL because skill instructions and generated artifacts still use or lack the new self-contained layout.

- [ ] **Step 5: Keep the failing contract update uncommitted**

Do not commit at this red step. Task 5 commits the contract tests, instruction
rewrites, hook update, and generated artifacts together after they pass.

### Task 4: Update Skill Instructions And Canonical Install Matrix

**Files:**
- Modify: `skills/atomic-note/SKILL.md`
- Modify: `skills/atomic-note-audit/SKILL.md`
- Modify: `shared/references/install-matrix.md`

- [ ] **Step 1: Update `skills/atomic-note/SKILL.md` paths**

Change the repo-local helper sentence to:

```markdown
When working from an installed skill, prefer `python3 scripts/obsidian_cli.py`
for app-context CLI commands.
```

Change required references to:

```markdown
## Required References

- `references/doctrine.md`
- `references/remediation-context.md`
```

- [ ] **Step 2: Update `skills/atomic-note-audit/SKILL.md` paths**

Change required references to:

```markdown
## Required References

- `references/doctrine.md`
- `references/audit-rubric.md`
- `references/model-judgment-prompt.md`
- `references/remediation-context.md`
- `references/install-matrix.md`
```

Change read-only audit steps to:

```markdown
1. Resolve vault config.
2. Run `scripts/audit_notes.py`.
3. Validate JSONL with `scripts/validate_jsonl.py`.
4. Generate Markdown report with `scripts/generate_report.py`.
5. Generate Obsidian Base with `scripts/generate_base.py` when requested.
6. Summarize KPIs and P0-P3/no-change queues.
```

Change model judgment references and commands:

```markdown
Use `references/model-judgment-prompt.md` verbatim when asking an
LLM for model judgment. The prompt is generated from the scoring vocabulary
source of truth and must stay aligned with `scripts/finding_codes.py`.
```

```bash
python3 scripts/prepare_model_judgment.py --vault /path/to/vault --note-path "Atomic Notes/Example.md" --output /tmp/model-judgment-request.md
```

```bash
python3 scripts/collect_model_judgments.py --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --output-jsonl /tmp/networked-thinking-audit/model-judgments.jsonl --raw-dir /tmp/networked-thinking-model-raw --model gpt-5.5
```

```markdown
Collect model responses as JSONL, one strict
`schemas/model-judgment.schema.json` object per line.
```

```bash
python3 scripts/apply_model_judgments.py --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --model-judgments /tmp/networked-thinking-audit/model-judgments.jsonl --output-jsonl /tmp/networked-thinking-audit/model-applied.jsonl --output-manifest /tmp/networked-thinking-audit/model-applied-manifest.json
```

Change remediation references:

```markdown
single user-directed operation. Load `references/remediation-context.md`
before planning any vault mutation.
```

```markdown
prefer `python3 scripts/obsidian_cli.py` for app-context CLI commands.
```

```markdown
sequence in `references/remediation-context.md`, including warning
```

```markdown
For long-running goals, loops, or autonomous remediation batches, keep a durable
held-decision artifact as described in `references/remediation-context.md`.
```

- [ ] **Step 3: Update `shared/references/install-matrix.md`**

Replace the "Raw Skill Installs" section with:

```markdown
## Self-contained skill installs

Published skill directories must include every runtime reference, schema, and
helper script they need under the skill root.

Runtime installs copy `skills/<skill>` into `<runtime-home>/skills/<skill>`.
No separate `<runtime-home>/shared` copy step is required.
```

- [ ] **Step 4: Run the focused integrity tests**

Run:

```bash
python3 -m unittest tests.test_skill_integrity -v
```

Expected: still FAIL until generated artifact directories exist.

- [ ] **Step 5: Keep instruction rewrites uncommitted**

Do not commit until generated artifacts exist and the updated contract tests
pass in Task 5.

### Task 5: Generate And Validate Skill-Local Artifacts

**Files:**
- Generate: `skills/atomic-note/references/*`
- Generate: `skills/atomic-note/scripts/*`
- Generate: `skills/atomic-note-audit/references/*`
- Generate: `skills/atomic-note-audit/schemas/*`
- Generate: `skills/atomic-note-audit/scripts/*`

- [ ] **Step 1: Generate artifacts**

Run:

```bash
python3 -m shared.scripts.sync_skill_artifacts
```

Expected: `skill_artifacts=ok`.

- [ ] **Step 2: Validate generated artifacts are current**

Run:

```bash
python3 -m shared.scripts.sync_skill_artifacts --check
```

Expected: `skill_artifacts=ok`.

- [ ] **Step 3: Validate no stale shared references under installable skills**

Run:

```bash
! rg '\.\./\.\./shared|\.\./shared|shared/|shared\.scripts|from shared|import shared' skills/atomic-note skills/atomic-note-audit
```

Expected: no matches.

- [ ] **Step 4: Smoke helper entrypoint imports from skill roots**

Run:

```bash
python3 skills/atomic-note/scripts/obsidian_cli.py --help >/tmp/atomic-note-obsidian-help.txt
python3 skills/atomic-note/scripts/verify_anki_notes.py --help >/tmp/atomic-note-verify-anki-help.txt
python3 skills/atomic-note-audit/scripts/audit_notes.py --help >/tmp/audit-notes-help.txt
python3 skills/atomic-note-audit/scripts/validate_jsonl.py --help >/tmp/validate-jsonl-help.txt
python3 skills/atomic-note-audit/scripts/generate_report.py --help >/tmp/generate-report-help.txt
python3 skills/atomic-note-audit/scripts/generate_base.py --help >/tmp/generate-base-help.txt
python3 skills/atomic-note-audit/scripts/prepare_model_judgment.py --help >/tmp/prepare-model-help.txt
python3 skills/atomic-note-audit/scripts/collect_model_judgments.py --help >/tmp/collect-model-help.txt
python3 skills/atomic-note-audit/scripts/apply_model_judgments.py --help >/tmp/apply-model-help.txt
python3 skills/atomic-note-audit/scripts/remediate_notes.py --help >/tmp/remediate-help.txt
python3 skills/atomic-note-audit/scripts/preflight_obsidian.py --help >/tmp/preflight-help.txt
python3 skills/atomic-note-audit/scripts/verify_anki_notes.py --help >/tmp/verify-anki-help.txt
```

Expected: all commands exit 0.

- [ ] **Step 5: Run contract tests**

Run:

```bash
python3 -m unittest tests.test_skill_artifact_sync tests.test_skill_integrity tests.test_repo_smoke -v
```

Expected: PASS.

- [ ] **Step 6: Commit the self-contained artifact contract**

```bash
git add tests/test_skill_integrity.py tests/test_repo_smoke.py lefthook.yml skills/atomic-note skills/atomic-note-audit shared/references/install-matrix.md
git commit -m "feat: add self-contained skill artifacts"
```

### Task 6: Update Public Install Documentation And Metadata

**Files:**
- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/audit-workflow.md`
- Modify: `docs/remediation.md`
- Modify: `docs/rubric.md`
- Modify: `.codex-plugin/plugin.json`
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Update README quickstart**

Replace the helper and install bullets with:

```markdown
- Install `atomic-note` and `atomic-note-audit` with `npx skills add`; see [docs/install.md](docs/install.md).
- Installed skills include their runtime references and helper scripts. Run helper commands from the installed skill root when a skill instructs you to do so.
```

- [ ] **Step 2: Rewrite the package-layout paragraph in `docs/install.md`**

Replace the paragraph that says copied skill folders are incomplete with:

```markdown
Each published skill directory is self-contained. `npx skills add` copies the selected skill directory, including skill-local references, schemas, and helper scripts. No separate `shared/` copy step is required.
```

- [ ] **Step 3: Replace raw install commands**

For Codex raw skills, use:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.agents/skills/"
```

For Claude Code raw skills, use:

```bash
mkdir -p "$HOME/.claude/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.claude/skills/"
```

For Hermes, use:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/atomic-note skills/atomic-note-audit "$HOME/.agents/skills/"
```

- [ ] **Step 4: Replace local `npx skills` commands**

For Codex local clone install:

```bash
npx skills add . --agent codex -g --skill atomic-note --skill atomic-note-audit --copy -y
```

For Claude Code local clone install:

```bash
npx skills add . --agent claude-code -g --skill atomic-note --skill atomic-note-audit --copy -y
```

- [ ] **Step 5: Add public GitHub install examples without false verification claims**

Add a section named `Public GitHub Installs` with these unqualified public
commands as the post-merge user-facing form:

```bash
npx skills add jrgilbertson/networked-thinking-skills --list
```

```bash
npx skills add jrgilbertson/networked-thinking-skills --agent codex -g --skill '*' --copy -y
```

```bash
npx skills add jrgilbertson/networked-thinking-skills --agent codex -g --skill atomic-note --copy -y
```

```bash
npx skills add https://github.com/jrgilbertson/networked-thinking-skills --list
```

```bash
npx skills add https://github.com/jrgilbertson/networked-thinking-skills/tree/main/skills/atomic-note --list
```

Do not mark unqualified `main` commands as `verified-local` or
`verified-upstream` during branch implementation. Before merge, only commands
that were actually executed against the implementation branch may receive
`last_verified: 2026-06-19` metadata. Leave unqualified `main` examples outside
`install-command` metadata blocks, or mark them `blocked-with-reason` with a
reason that `main` does not contain the implementation until merge. After the
implementation is merged to `main`, rerun the unqualified commands and update
their metadata to verified status.

- [ ] **Step 6: Update workflow docs that still show repo-local helper paths**

In `docs/audit-workflow.md`, replace user-facing `python3 -m shared.scripts.*`
commands with installed skill-root commands such as:

```bash
python3 scripts/audit_notes.py --vault /path/to/vault --run-id baseline-YYYYMMDDHHMM --jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json
python3 scripts/validate_jsonl.py /tmp/networked-thinking-audit/baseline.jsonl
python3 scripts/generate_report.py --jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --output /tmp/networked-thinking-audit/baseline-report.md
python3 scripts/generate_base.py --jsonl /tmp/networked-thinking-audit/baseline.jsonl --output /tmp/networked-thinking-audit/baseline.base
python3 scripts/prepare_model_judgment.py --vault /path/to/vault --note-path "Atomic Notes/Example.md" --output /tmp/model-judgment-request.md
python3 scripts/collect_model_judgments.py --vault /path/to/vault --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --output-jsonl /tmp/networked-thinking-audit/model-judgments.jsonl --raw-dir /tmp/networked-thinking-model-raw --model gpt-5.5
python3 scripts/apply_model_judgments.py --audit-jsonl /tmp/networked-thinking-audit/baseline.jsonl --manifest /tmp/networked-thinking-audit/baseline-manifest.json --model-judgments /tmp/networked-thinking-audit/model-judgments.jsonl --output-jsonl /tmp/networked-thinking-audit/model-applied.jsonl --output-manifest /tmp/networked-thinking-audit/model-applied-manifest.json
```

In `docs/remediation.md`, replace user-facing helper commands with installed
skill-root commands such as:

```bash
python3 scripts/remediate_notes.py --plan /path/to/remediation-plan.json --manifest /tmp/networked-thinking-remediation/dry-run-manifest.json
python3 scripts/preflight_obsidian.py --require-cli
python3 scripts/obsidian_cli.py help
python3 scripts/verify_anki_notes.py --vault /path/to/vault --spec /tmp/anki-verify.json
```

In `docs/rubric.md`, replace direct `shared/scripts/finding_codes.py` wording
with `scripts/finding_codes.py` for installed-skill users and, if needed, add a
single maintainer note that the canonical development source remains
`shared/scripts/finding_codes.py` in this repo.

- [ ] **Step 7: Update plugin manifest repository metadata**

In both plugin manifests, set:

```json
"repository": "https://github.com/jrgilbertson/networked-thinking-skills"
```

- [ ] **Step 8: Run doc checks**

Run:

```bash
python3 -m shared.scripts.verify_install_commands docs/install.md
python3 -m unittest tests.test_repo_smoke tests.test_install_command_verifier -v
```

Expected: PASS.

- [ ] **Step 9: Commit docs and metadata**

```bash
git add README.md docs/install.md docs/audit-workflow.md docs/remediation.md docs/rubric.md .codex-plugin/plugin.json .claude-plugin/plugin.json
git commit -m "docs: document self-contained npx skill installs"
```

### Task 7: Local Clean-Home Install Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Verify local CLI discovery**

Run:

```bash
npx skills add . --list
```

Expected: output includes `atomic-note` and `atomic-note-audit`.

- [ ] **Step 2: Verify clean Codex copy install**

Run:

```bash
TMP_HOME=$(mktemp -d)
HOME="$TMP_HOME" npx skills add . --skill '*' --agent codex -g --copy -y
find "$TMP_HOME" -maxdepth 5 -type f | sort
```

Expected: files exist under `$TMP_HOME/.codex/skills/atomic-note` and `$TMP_HOME/.codex/skills/atomic-note-audit`, including `references/`, `scripts/`, and audit `schemas/`.

- [ ] **Step 3: Verify installed layout has no stale shared references**

Run:

```bash
! rg '\.\./\.\./shared|\.\./shared|shared/|shared\.scripts|from shared|import shared' "$TMP_HOME/.codex/skills"
```

Expected: no matches.

- [ ] **Step 4: Verify installed helper entrypoints**

Run:

```bash
python3 "$TMP_HOME/.codex/skills/atomic-note/scripts/obsidian_cli.py" --help >/tmp/installed-obsidian-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note/scripts/verify_anki_notes.py" --help >/tmp/installed-atomic-note-anki-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/audit_notes.py" --help >/tmp/installed-audit-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/validate_jsonl.py" --help >/tmp/installed-validate-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/generate_report.py" --help >/tmp/installed-report-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/generate_base.py" --help >/tmp/installed-base-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/prepare_model_judgment.py" --help >/tmp/installed-prepare-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/collect_model_judgments.py" --help >/tmp/installed-collect-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/apply_model_judgments.py" --help >/tmp/installed-apply-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/remediate_notes.py" --help >/tmp/installed-remediate-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/preflight_obsidian.py" --help >/tmp/installed-preflight-help.txt
python3 "$TMP_HOME/.codex/skills/atomic-note-audit/scripts/verify_anki_notes.py" --help >/tmp/installed-anki-help.txt
```

Expected: all commands exit 0.

- [ ] **Step 5: Run full local test suite**

Run:

```bash
python3 -m unittest discover -s tests
python3 -m shared.scripts.sync_skill_artifacts --check
python3 -m shared.scripts.validate_jsonl tests/golden/fixture-audit.jsonl
python3 -m shared.scripts.verify_install_commands docs/install.md
```

Expected: all pass.

- [ ] **Step 6: Commit any verification-driven fixes**

If local verification required fixes, commit them:

```bash
git add shared/scripts/sync_skill_artifacts.py tests/test_skill_artifact_sync.py tests/test_skill_integrity.py tests/test_repo_smoke.py lefthook.yml skills/atomic-note skills/atomic-note-audit shared/references/install-matrix.md README.md docs/install.md docs/audit-workflow.md docs/remediation.md docs/rubric.md .codex-plugin/plugin.json .claude-plugin/plugin.json
git commit -m "fix: satisfy local npx skill install verification"
```

If there were no changes, skip this commit.

### Task 8: Public GitHub Source Verification

**Files:**
- No source edits expected unless public-source verification finds defects.

- [ ] **Step 1: Push the branch so GitHub source installs can target it**

Run:

```bash
git push -u origin 3-make-skills-publishable-through-npx-installs
```

Expected: branch exists on GitHub.

- [ ] **Step 2: Verify owner/repo discovery against the branch ref**

Run:

```bash
npx skills add 'jrgilbertson/networked-thinking-skills#3-make-skills-publishable-through-npx-installs' --list
```

Expected: output includes `atomic-note` and `atomic-note-audit`.

- [ ] **Step 3: Verify full GitHub URL discovery against the branch ref**

Run:

```bash
npx skills add 'https://github.com/jrgilbertson/networked-thinking-skills#3-make-skills-publishable-through-npx-installs' --list
```

Expected: output includes `atomic-note` and `atomic-note-audit`.

- [ ] **Step 4: Verify direct tree URL discovery against the branch for both skills**

Run:

```bash
npx skills add 'https://github.com/jrgilbertson/networked-thinking-skills/tree/3-make-skills-publishable-through-npx-installs/skills/atomic-note' --list
npx skills add 'https://github.com/jrgilbertson/networked-thinking-skills/tree/3-make-skills-publishable-through-npx-installs/skills/atomic-note-audit' --list
```

Expected: first output includes `atomic-note`; second output includes
`atomic-note-audit`.

- [ ] **Step 5: Verify copied install from the owner/repo branch ref**

Run:

```bash
GITHUB_TMP_HOME=$(mktemp -d)
HOME="$GITHUB_TMP_HOME" npx skills add 'jrgilbertson/networked-thinking-skills#3-make-skills-publishable-through-npx-installs' --skill '*' --agent codex -g --copy -y
! rg '\.\./\.\./shared|\.\./shared|shared/|shared\.scripts|from shared|import shared' "$GITHUB_TMP_HOME/.codex/skills"
python3 "$GITHUB_TMP_HOME/.codex/skills/atomic-note/scripts/obsidian_cli.py" --help >/tmp/github-installed-obsidian-help.txt
python3 "$GITHUB_TMP_HOME/.codex/skills/atomic-note/scripts/verify_anki_notes.py" --help >/tmp/github-installed-atomic-note-anki-help.txt
python3 "$GITHUB_TMP_HOME/.codex/skills/atomic-note-audit/scripts/audit_notes.py" --help >/tmp/github-installed-audit-help.txt
python3 "$GITHUB_TMP_HOME/.codex/skills/atomic-note-audit/scripts/collect_model_judgments.py" --help >/tmp/github-installed-collect-help.txt
```

Expected: install succeeds, no stale shared references are found, and helper imports execute.

- [ ] **Step 6: Verify copied install from the direct audit tree URL**

Run:

```bash
GITHUB_TREE_TMP_HOME=$(mktemp -d)
HOME="$GITHUB_TREE_TMP_HOME" npx skills add 'https://github.com/jrgilbertson/networked-thinking-skills/tree/3-make-skills-publishable-through-npx-installs/skills/atomic-note-audit' --agent codex -g --copy -y
! rg '\.\./\.\./shared|\.\./shared|shared/|shared\.scripts|from shared|import shared' "$GITHUB_TREE_TMP_HOME/.codex/skills/atomic-note-audit"
python3 "$GITHUB_TREE_TMP_HOME/.codex/skills/atomic-note-audit/scripts/audit_notes.py" --help >/tmp/github-tree-audit-help.txt
python3 "$GITHUB_TREE_TMP_HOME/.codex/skills/atomic-note-audit/scripts/collect_model_judgments.py" --help >/tmp/github-tree-collect-help.txt
```

Expected: the direct tree install succeeds, no stale shared references are
found, and audit helper imports execute.

- [ ] **Step 7: Commit public-source fixes if needed**

If public-source verification required fixes:

```bash
git add shared/scripts/sync_skill_artifacts.py tests/test_skill_artifact_sync.py tests/test_skill_integrity.py tests/test_repo_smoke.py lefthook.yml skills/atomic-note skills/atomic-note-audit shared/references/install-matrix.md README.md docs/install.md docs/audit-workflow.md docs/remediation.md docs/rubric.md .codex-plugin/plugin.json .claude-plugin/plugin.json
git commit -m "fix: satisfy github npx skill install verification"
git push
```

If there were no changes, skip this commit.

### Task 9: Final Review And Handoff

**Files:**
- Modify only if final review finds an issue.

- [ ] **Step 1: Run pre-commit-equivalent checks**

Run:

```bash
python3 -m shared.scripts.sync_skill_artifacts --check
python3 -m shared.scripts.validate_jsonl tests/golden/fixture-audit.jsonl
python3 -m shared.scripts.verify_install_commands docs/install.md
python3 -m unittest discover -s tests
```

Expected: all pass.

- [ ] **Step 2: Confirm worktree**

Run:

```bash
git status --short --branch
```

Expected: branch is clean or only contains intentional final documentation updates.

- [ ] **Step 3: Summarize verification evidence**

Record in the final handoff:

```text
Local npx list: passed
Local clean Codex copy install: passed
Installed stale shared grep: passed
Installed helper import smoke checks: passed
GitHub branch owner/repo list: passed
GitHub branch full URL list: passed
GitHub branch atomic-note direct tree URL list: passed
GitHub branch atomic-note-audit direct tree URL list: passed
GitHub branch atomic-note-audit direct tree copy install: passed
Unit tests: passed
Unqualified main GitHub examples: not marked verified before merge unless main was actually tested
```

- [ ] **Step 4: Open PR only if explicitly asked**

Do not open a pull request unless the user asks. If asked, use the existing branch and include the verification evidence above in the PR body.
