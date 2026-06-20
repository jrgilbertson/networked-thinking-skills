from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from obsidian_adapter import DEFAULT_OBSIDIAN_BINARY, CommandResult, ObsidianAdapter


SANDBOX_HINT = (
    "hint=verify Obsidian is running and owns ~/.obsidian-cli.sock; in Codex CLI, "
    "rerun this helper in an approved unsandboxed context if the local CLI socket "
    "is blocked by the sandbox"
)


def main(argv: list[str] | None = None) -> int:
    args, obsidian_args = _parse_args(argv)
    if obsidian_args and obsidian_args[0] == "--":
        obsidian_args = obsidian_args[1:]
    if not obsidian_args:
        obsidian_args = ["help"]

    result = ObsidianAdapter(binary=args.obsidian_binary).run(obsidian_args)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
    if not result.ok and _is_attach_failure(result):
        print(SANDBOX_HINT, file=sys.stderr)
    return result.returncode


def _parse_args(argv: list[str] | None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Resolve and invoke the real Obsidian CLI binary.",
        add_help=True,
    )
    parser.add_argument(
        "--obsidian-binary",
        default=DEFAULT_OBSIDIAN_BINARY,
        help=f"Obsidian CLI executable to use. Defaults to {DEFAULT_OBSIDIAN_BINARY}.",
    )
    return parser.parse_known_args(argv)


def _is_attach_failure(result: CommandResult) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    return "unable to find obsidian" in text or "cli socket" in text


if __name__ == "__main__":
    raise SystemExit(main())
