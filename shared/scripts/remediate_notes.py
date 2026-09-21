from __future__ import annotations

import argparse
from collections.abc import Callable
from copy import deepcopy
import json
import sys
from pathlib import Path
import signal

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
    dispatched: list[str] = []
    operations = None
    _install_termination_handler()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        if args.execute:
            # The execute gate runs first and alone. It calls `validate_plan`
            # itself, and running that first here would refuse an unexecutable
            # operation with authoring advice — telling an operator to
            # authorise or repair something that can never execute. Holding
            # the returned list also lets the manifest document what the gates
            # checked rather than a second reading of the plan.
            operations = validate_executable_plan(plan)
            execute_plan(
                plan,
                ObsidianAdapter(
                    binary=args.obsidian_binary,
                    timeout_seconds=COMMAND_TIMEOUT_SECONDS,
                ),
                vault=args.vault,
                on_written=dispatched.append,
            )
        else:
            validate_plan(plan, destructive_allowed=args.destructive_allowed)
        manifest = _manifest(plan, executed=args.execute, dispatched=dispatched, operations=operations)
        _write_manifest(args.manifest, manifest)
    except (RemediationError, OSError, json.JSONDecodeError) as exc:
        _warn(str(exc))
        if dispatched:
            _report_dispatched(args.manifest, plan, dispatched, operations)
        return 1
    except BaseException:
        # An interrupt or an unexpected error still leaves changed notes
        # behind, and the operator needs their names to roll them back.
        if dispatched:
            _report_dispatched(args.manifest, plan, dispatched, operations)
        raise
    _announce(f"operation_count={manifest['operation_count']}")
    if args.execute:
        _announce(f"dispatched_note_count={len(dispatched)}")
    return 0


def _announce(message: str) -> None:
    """Print a closing line without letting the stream fail the run.

    The work is already done and persisted by the time these are written, so a
    closed stdout — the run piped into `head`, say — must not turn a finished
    remediation into a traceback and a non-zero exit. On this tool that is
    worse than cosmetic: an operator who reads failure may run it again.
    """
    try:
        print(message)
    except OSError:
        pass


def _install_termination_handler() -> None:
    """Route SIGTERM through the reporting path, where the platform allows it."""
    try:
        signal.signal(signal.SIGTERM, _raise_on_termination)
    except (AttributeError, ValueError, OSError):
        # No SIGTERM, or not the main thread. The run still works; only the
        # account on a termination signal is lost, which is the status quo.
        pass


def _raise_on_termination(signal_number: int, frame: object) -> None:
    """Turn SIGTERM into an exception so the account still gets written.

    Python raises `KeyboardInterrupt` for SIGINT by itself, but SIGTERM
    terminates the process without raising, so the handler that reports which
    notes were dispatched never runs. A long vault repair is exactly what an
    operator, a CI timeout or a supervisor kills, which makes this the more
    likely interruption of the two. Raising `KeyboardInterrupt` funnels it
    through the same path Ctrl-C already proved.
    """
    raise KeyboardInterrupt(f"terminated by signal {signal_number}")


def _warn(message: str) -> None:
    """Emit an operator-facing line, falling back when stderr itself fails.

    A broken pipe, a full disk, or a capture shim raising on write must not be
    what loses the record of which notes changed, so stdout is tried next and
    a failure of both is swallowed rather than raised over the account it was
    trying to deliver. An interrupt still propagates, so a second Ctrl-C can
    always stop the run.
    """
    for stream in (sys.stderr, sys.stdout):
        try:
            print(message, file=stream)
            return
        except Exception:
            continue


def _report_dispatched(
    manifest_path: Path,
    plan: dict,
    dispatched: list[str],
    operations: list[dict] | None,
) -> None:
    """Account for the notes a halted batch sent a write for.

    The vault has changed, so the names are reported whether or not the
    manifest can be saved. Losing the account to a second failure would leave
    the operator without the list of notes to roll back.
    """
    for note_path in dispatched:
        _warn(f"dispatched_note={note_path}")
    _warn(f"dispatched_note_count={len(dispatched)}")
    try:
        _write_manifest(
            manifest_path,
            _manifest(plan, executed=True, dispatched=dispatched, operations=operations),
        )
    except OSError as exc:
        _warn(f"Unable to write manifest: {exc}")


def _manifest(
    plan: dict,
    *,
    executed: bool,
    dispatched: list[str],
    operations: list[dict] | None = None,
) -> dict:
    manifest = build_dry_run_manifest(plan)
    if operations is not None:
        manifest["operations"] = deepcopy(operations)
        manifest["operation_count"] = len(operations)
    if executed:
        manifest["executed"] = True
        # Every note the run sent a write for. On a clean run each one is also
        # a verified repair; on a halt the last one may not be.
        manifest["dispatched_note_paths"] = list(dispatched)
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
