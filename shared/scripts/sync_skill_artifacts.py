"""Sync generated self-contained skill artifacts from canonical shared files."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
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
    root: Path = ROOT,
    specs: Mapping[str, SkillArtifactSpec] = ARTIFACT_SPECS,
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
    renderer: Callable[[str], str],
    check: bool,
) -> None:
    dest_dir = skill_dir / dest_name
    expected = set(filenames)
    if dest_dir.exists():
        for existing in dest_dir.iterdir():
            if existing.is_file() and existing.name not in expected:
                rel = existing.relative_to(root)
                if check:
                    errors.append(f"{rel} is not declared in artifact spec")
                else:
                    existing.unlink()

    if not filenames:
        if not check and dest_dir.exists():
            shutil.rmtree(dest_dir)
        return
    if not check:
        dest_dir.mkdir(parents=True, exist_ok=True)

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


def main(argv: Sequence[str] | None = None) -> int:
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
