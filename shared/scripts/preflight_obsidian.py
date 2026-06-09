from __future__ import annotations

import argparse
from dataclasses import dataclass
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.obsidian_adapter import DEFAULT_OBSIDIAN_BINARY, ObsidianAdapter


REQUIRED_OBSIDIAN_SKILLS = ("obsidian-cli", "obsidian-markdown", "obsidian-bases")


@dataclass(frozen=True)
class SkillPathCheck:
    ok: bool
    missing: list[str]


def check_skill_paths(skills_root: Path) -> SkillPathCheck:
    missing = [
        skill
        for skill in REQUIRED_OBSIDIAN_SKILLS
        if not (skills_root / skill / "SKILL.md").is_file()
    ]
    return SkillPathCheck(ok=not missing, missing=missing)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    skill_check = check_skill_paths(args.skills_root)
    if not skill_check.ok:
        print(f"missing_skills={','.join(skill_check.missing)}")
        return 2

    if args.require_cli:
        adapter = ObsidianAdapter(binary=args.obsidian_binary)
        if not adapter.available():
            print("obsidian_cli=missing")
            return 3
        if not adapter.help().ok:
            print("obsidian_cli=unavailable")
            return 4

    print("obsidian_preflight=ok")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight Obsidian mutation support.")
    parser.add_argument("--skills-root", type=Path, default=Path.home() / ".agents/skills")
    parser.add_argument("--require-cli", action="store_true")
    parser.add_argument(
        "--obsidian-binary",
        default=DEFAULT_OBSIDIAN_BINARY,
        help=f"Obsidian CLI executable to use. Defaults to {DEFAULT_OBSIDIAN_BINARY}.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
