from __future__ import annotations

import argparse
from collections.abc import Callable
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.obsidian_adapter import (
    COMMAND_TIMEOUT_SECONDS,
    DEFAULT_OBSIDIAN_BINARY,
    ObsidianAdapter,
    ObsidianTransportError,
)
from shared.scripts.remediation import (
    RemediationError,
    assert_expected_occurrences,
    assert_repair_landed,
    build_dry_run_manifest,
    validate_executable_plan,
    validate_plan,
)


def execute_plan(
    plan: dict,
    adapter: ObsidianAdapter,
    *,
    vault: str,
    on_written: Callable[[str], None] | None = None,
) -> list[str]:
    """Apply an approved `edit` plan to the vault, one note at a time.

    Every write goes through the running Obsidian app; there is no filesystem
    fallback. A halt leaves the completed writes in place and reports through
    `on_written` every note whose write was dispatched, which is the
    operator's account of what to roll back. Reporting starts before the call
    rather than after it returns, because once the app has the operation an
    interrupt or a crash cannot be told apart from a completed write, and a
    note named in error costs an operator one diff while a note left unnamed
    costs them a silent change.
    """
    operations = validate_executable_plan(plan)

    written: list[str] = []

    def record(note_path: str) -> None:
        # A note carrying two decayed commands needs one operation each, and
        # the account names notes to roll back, not writes performed.
        if note_path in written:
            return
        written.append(note_path)
        if on_written is not None:
            on_written(note_path)

    for operation in operations:
        note_path = operation["note_path"]
        try:
            before = adapter.read_note(note_path, vault=vault)
        except ObsidianTransportError as exc:
            raise RemediationError(str(exc)) from exc

        assert_expected_occurrences(operation, before)

        record(note_path)
        try:
            adapter.replace_in_note(
                note_path,
                find=operation["find"],
                replace=operation["replace"],
                expected_occurrences=operation["expected_occurrences"],
                vault=vault,
            )
        except ObsidianTransportError as exc:
            # The call failed partway, so whether the note changed is unknown.
            raise RemediationError(f"{exc}; inspect {note_path} before rerunning") from exc

        try:
            after = adapter.read_note(note_path, vault=vault)
        except ObsidianTransportError as exc:
            raise RemediationError(str(exc)) from exc
        assert_repair_landed(operation, before, after)

    return written


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    written: list[str] = []
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        validate_plan(plan, destructive_allowed=args.destructive_allowed)
        if args.execute:
            execute_plan(
                plan,
                ObsidianAdapter(
                    binary=args.obsidian_binary,
                    timeout_seconds=COMMAND_TIMEOUT_SECONDS,
                ),
                vault=args.vault,
                on_written=written.append,
            )
        manifest = _manifest(plan, executed=args.execute, written=written)
        _write_manifest(args.manifest, manifest)
    except (RemediationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        if written:
            _report_written(args.manifest, plan, written)
        return 1
    except BaseException:
        # An interrupt or an unexpected error still leaves changed notes
        # behind, and the operator needs their names to roll them back.
        if written:
            _report_written(args.manifest, plan, written)
        raise
    print(f"operation_count={manifest['operation_count']}")
    if args.execute:
        print(f"written_note_count={len(written)}")
    return 0


def _report_written(manifest_path: Path, plan: dict, written: list[str]) -> None:
    """Account for the notes a halted batch already changed.

    The vault has changed, so this reports to stderr whether or not the
    manifest can be saved. Losing the account to a second failure would leave
    the operator without the list of notes to roll back.
    """
    for note_path in written:
        print(f"written_note={note_path}", file=sys.stderr)
    print(f"written_note_count={len(written)}", file=sys.stderr)
    try:
        _write_manifest(manifest_path, _manifest(plan, executed=True, written=written))
    except OSError as exc:
        print(f"Unable to write manifest: {exc}", file=sys.stderr)


def _manifest(plan: dict, *, executed: bool, written: list[str]) -> dict:
    manifest = build_dry_run_manifest(plan)
    if executed:
        manifest["executed"] = True
        manifest["written_note_paths"] = list(written)
    return manifest


def _write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate, dry-run, or execute Networked Thinking remediation plans.")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--destructive-allowed", action="store_true")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply the plan's approved edit operations to the vault through Obsidian.",
    )
    parser.add_argument("--vault", help="Vault name to write to. Required with --execute.")
    parser.add_argument("--obsidian-binary", default=DEFAULT_OBSIDIAN_BINARY)
    args = parser.parse_args(argv)
    if args.execute and not args.vault:
        parser.error("--execute requires --vault")
    return args


if __name__ == "__main__":
    raise SystemExit(main())
