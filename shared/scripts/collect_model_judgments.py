from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.model_contract import validate_model_judgment
from shared.scripts.schema_validation import ValidationError, validate_audit_row


PROMPT_REFERENCE = Path(__file__).resolve().parents[1] / "references" / "model-judgment-prompt.md"


class AgentRunner(Protocol):
    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        pass


@dataclass(frozen=True)
class Batch:
    index: int
    rows: list[dict[str, Any]]


class RunnerInvocationError(RuntimeError):
    """Raised when a local runner command fails before usable model output exists."""


RETRYABLE_BATCH_ERRORS = (ValidationError, subprocess.TimeoutExpired)


@dataclass(frozen=True)
class CodexRunner:
    vault_root: Path
    codex_bin: str
    model: str
    sandbox: str
    timeout_seconds: int
    ignore_user_config: bool

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        command = [
            self.codex_bin,
            "exec",
            "--model",
            self.model,
            "--cd",
            str(self.vault_root),
            "--sandbox",
            self.sandbox,
            "--output-last-message",
            str(output_path),
            "-",
        ]
        if self.ignore_user_config:
            command.insert(2, "--ignore-user-config")

        result = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
        )
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise RunnerInvocationError(f"codex exit {result.returncode}; stderr={result.stderr[-500:]}")


@dataclass(frozen=True)
class CommandRunner:
    vault_root: Path
    command_template: str
    timeout_seconds: int

    def run(self, prompt: str, *, output_path: Path, stdout_path: Path, stderr_path: Path) -> None:
        try:
            formatted = self.command_template.format(
                output_path=str(output_path),
                stdout_path=str(stdout_path),
                stderr_path=str(stderr_path),
                vault=str(self.vault_root),
                vault_root=str(self.vault_root),
            )
            command = shlex.split(formatted)
        except (KeyError, ValueError) as exc:
            raise RunnerInvocationError(f"invalid command template: {exc}") from exc
        if not command:
            raise RunnerInvocationError("command runner template produced an empty command")

        try:
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                cwd=self.vault_root,
            )
        except OSError as exc:
            raise RunnerInvocationError(f"command runner failed to start: {exc}") from exc

        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise RunnerInvocationError(
                f"command runner exit {result.returncode}; stderr={result.stderr[-500:]}"
            )
        if not output_path.exists():
            output_path.write_text(result.stdout, encoding="utf-8")


def collect_model_judgments(
    *,
    vault_root: Path,
    audit_jsonl: Path,
    output_jsonl: Path,
    raw_dir: Path,
    max_notes: int,
    max_chars: int,
    limit: int | None = None,
    runner: AgentRunner,
) -> int:
    vault_root = vault_root.resolve()
    raw_dir = raw_dir.resolve()
    rows = _read_audit_rows(audit_jsonl)
    if limit is not None:
        rows = rows[:limit]

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    completed = _read_completed_paths(output_jsonl)
    expected = {str(row["note_path"]) for row in rows}
    extra_completed = sorted(completed - expected)
    if extra_completed:
        raise ValidationError(f"existing judgment has no selected audit row: {extra_completed[0]}")
    remaining = [row for row in rows if str(row["note_path"]) not in completed]
    print(
        f"total={len(rows)} completed={len(completed)} remaining={len(remaining)}",
        flush=True,
    )

    for batch_index, batch_rows in enumerate(
        _make_batches(vault_root, remaining, max_notes=max_notes, max_chars=max_chars),
        start=1,
    ):
        _run_batch_with_split(
            Batch(batch_index, batch_rows),
            vault_root=vault_root,
            output_jsonl=output_jsonl,
            raw_dir=raw_dir,
            runner=runner,
        )

    final_completed = _read_completed_paths(output_jsonl)
    missing = sorted(expected - final_completed)
    if missing:
        raise ValidationError(f"missing={len(missing)} first={missing[0]}")

    print(f"done={len(final_completed)} output={output_jsonl}", flush=True)
    return len(final_completed)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        runner = _build_runner(args)
        collect_model_judgments(
            vault_root=args.vault,
            audit_jsonl=args.audit_jsonl,
            output_jsonl=args.output_jsonl,
            raw_dir=args.raw_dir,
            max_notes=args.max_notes,
            max_chars=args.max_chars,
            limit=args.limit,
            runner=runner,
        )
    except (
        ValidationError,
        OSError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        RunnerInvocationError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect model judgments for audit rows through a local agent runner."
    )
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--audit-jsonl", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        required=True,
        help="Directory for raw prompts and runner logs. Keep this outside the vault unless the user wants private prompt logs there.",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-notes", type=int, default=20)
    parser.add_argument("--max-chars", type=int, default=50_000)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument(
        "--runner",
        choices=("codex", "command"),
        help="Local agent runner adapter. Omit only for legacy Codex compatibility; prefer --runner codex or --runner command.",
    )
    parser.add_argument(
        "--command",
        dest="command_template",
        help=(
            "Command template for --runner command. The prompt is sent on stdin. "
            "If the command writes the final response to stdout, stdout is parsed. "
            "If it writes to {output_path}, that file is parsed instead. "
            "Quote path placeholders in the template when paths may contain spaces."
        ),
    )
    parser.add_argument("--codex-bin")
    parser.add_argument("--model")
    parser.add_argument("--codex-sandbox")
    parser.add_argument(
        "--load-user-config",
        action="store_true",
        help="Load the user's Codex config. By default the script ignores user config to avoid unrelated MCP startup failures.",
    )
    return parser.parse_args(argv)


def _build_runner(args: argparse.Namespace) -> AgentRunner:
    runner_name = args.runner or "codex"
    if args.runner is None:
        print(
            "runner not specified; using codex compatibility path. Prefer --runner codex.",
            file=sys.stderr,
        )
    if runner_name == "codex":
        return CodexRunner(
            vault_root=args.vault.resolve(),
            codex_bin=args.codex_bin or "codex",
            model=args.model or "gpt-5.5",
            sandbox=args.codex_sandbox or "read-only",
            timeout_seconds=args.timeout_seconds,
            ignore_user_config=not args.load_user_config,
        )
    if runner_name == "command":
        _reject_codex_options_for_command_runner(args)
        if not args.command_template:
            raise ValidationError("--command is required when --runner command")
        return CommandRunner(
            vault_root=args.vault.resolve(),
            command_template=args.command_template,
            timeout_seconds=args.timeout_seconds,
        )
    raise ValidationError(f"unsupported runner: {runner_name}")


def _reject_codex_options_for_command_runner(args: argparse.Namespace) -> None:
    used_options = [
        flag
        for name, flag in (
            ("codex_bin", "--codex-bin"),
            ("model", "--model"),
            ("codex_sandbox", "--codex-sandbox"),
        )
        if getattr(args, name)
    ]
    if args.load_user_config:
        used_options.append("--load-user-config")
    if used_options:
        raise ValidationError(
            f"{', '.join(used_options)} can only be used with --runner codex"
        )


def _run_batch_with_split(
    batch: Batch,
    *,
    vault_root: Path,
    output_jsonl: Path,
    raw_dir: Path,
    runner: AgentRunner,
) -> None:
    try:
        judgments = _run_batch(batch, vault_root=vault_root, raw_dir=raw_dir, runner=runner)
    except RETRYABLE_BATCH_ERRORS as exc:
        if len(batch.rows) == 1:
            raise
        midpoint = len(batch.rows) // 2
        print(
            f"batch={batch.index} size={len(batch.rows)} split_after_error={exc}",
            flush=True,
        )
        _run_batch_with_split(
            Batch(batch.index * 1000 + 1, batch.rows[:midpoint]),
            vault_root=vault_root,
            output_jsonl=output_jsonl,
            raw_dir=raw_dir,
            runner=runner,
        )
        _run_batch_with_split(
            Batch(batch.index * 1000 + 2, batch.rows[midpoint:]),
            vault_root=vault_root,
            output_jsonl=output_jsonl,
            raw_dir=raw_dir,
            runner=runner,
        )
        return

    _append_jsonl(output_jsonl, judgments)
    print(
        f"batch={batch.index} size={len(batch.rows)} wrote={len(judgments)} completed={len(_read_completed_paths(output_jsonl))}",
        flush=True,
    )


def _run_batch(
    batch: Batch,
    *,
    vault_root: Path,
    raw_dir: Path,
    runner: AgentRunner,
) -> list[dict[str, Any]]:
    prompt = render_batch_prompt(vault_root, batch.rows)
    prompt_path = raw_dir / f"batch-{batch.index:05d}-prompt.md"
    output_path = raw_dir / f"batch-{batch.index:05d}-last-message.jsonl"
    stdout_path = raw_dir / f"batch-{batch.index:05d}-stdout.log"
    stderr_path = raw_dir / f"batch-{batch.index:05d}-stderr.log"
    prompt_path.write_text(prompt, encoding="utf-8")
    output_path.unlink(missing_ok=True)
    stdout_path.unlink(missing_ok=True)
    stderr_path.unlink(missing_ok=True)

    runner.run(prompt, output_path=output_path, stdout_path=stdout_path, stderr_path=stderr_path)

    judgments = parse_model_output(output_path.read_text(encoding="utf-8"))
    _validate_batch_judgments(batch.rows, judgments)
    return judgments


def render_batch_prompt(vault_root: Path, rows: list[dict[str, Any]]) -> str:
    base_prompt = PROMPT_REFERENCE.read_text(encoding="utf-8").rstrip()
    lines = [
        base_prompt,
        "",
        "## Batch Mode Override",
        "",
        "Audit every note below using the same scoring contract.",
        "Return strict JSONL only: one complete model judgment object per line.",
        "Do not return a JSON array, Markdown fence, bullet list, explanation, score, or remediation bucket.",
        "Return exactly one line for each note_path, in the same order as shown.",
        "Use an empty findings array when no allowed finding code applies.",
        "If evidence would exceed 40 words, shorten it or omit finding-level evidence.",
        "",
        "## Notes To Judge",
        "",
    ]
    for number, row in enumerate(rows, start=1):
        note_path = str(row["note_path"])
        path = _resolve_note_path(vault_root, note_path)
        content = path.read_text(encoding="utf-8")
        lines.extend(
            [
                f"### Note {number}",
                "",
                f"Use this exact `note_path`: `{note_path}`.",
                f"Content SHA-256: `{row['content_hash']}`.",
                "",
                "NOTE_CONTENT_START",
                content.rstrip(),
                "NOTE_CONTENT_END",
                "",
            ]
        )
    return "\n".join(lines)


def parse_model_output(raw: str) -> list[dict[str, Any]]:
    text = _strip_fence(raw.strip())
    if not text:
        raise ValidationError("empty model output")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return _require_object_list(parsed)
    if isinstance(parsed, dict):
        return [parsed]

    judgments: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValidationError(f"line {line_number}: expected object")
        judgments.append(value)
    return judgments


def _validate_batch_judgments(rows: list[dict[str, Any]], judgments: list[dict[str, Any]]) -> None:
    expected_paths = [str(row["note_path"]) for row in rows]
    actual_paths = [str(judgment.get("note_path")) for judgment in judgments]
    if actual_paths != expected_paths:
        raise ValidationError(
            f"note_path mismatch expected={expected_paths!r} actual={actual_paths!r}"
        )
    for judgment in judgments:
        validate_model_judgment(judgment)


def _strip_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:jsonl|json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text


def _require_object_list(values: list[Any]) -> list[dict[str, Any]]:
    judgments: list[dict[str, Any]] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            raise ValidationError(f"array item {index}: expected object")
        judgments.append(value)
    return judgments


def _make_batches(
    vault_root: Path,
    rows: list[dict[str, Any]],
    *,
    max_notes: int,
    max_chars: int,
) -> list[list[dict[str, Any]]]:
    if max_notes < 1:
        raise ValidationError("max_notes must be at least 1")
    if max_chars < 1:
        raise ValidationError("max_chars must be at least 1")

    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for row in rows:
        path = _resolve_note_path(vault_root, str(row["note_path"]))
        note_chars = path.stat().st_size
        if current and (len(current) >= max_notes or current_chars + note_chars > max_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(row)
        current_chars += note_chars
    if current:
        batches.append(current)
    return batches


def _read_completed_paths(path: Path) -> set[str]:
    if not path.exists():
        return set()
    completed: set[str] = set()
    for judgment in _read_jsonl(path):
        validate_model_judgment(judgment)
        note_path = str(judgment["note_path"])
        if note_path in completed:
            raise ValidationError(f"duplicate model judgment note_path: {note_path}")
        completed.add(note_path)
    return completed


def _read_audit_rows(path: Path) -> list[dict[str, Any]]:
    rows = _read_jsonl(path)
    for row in rows:
        validate_audit_row(row, default_scan=True)
    return rows


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"{path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValidationError(f"{path}:{line_number}: expected object")
            rows.append(value)
    return rows


def _append_jsonl(path: Path, judgments: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for judgment in judgments:
            handle.write(json.dumps(judgment, sort_keys=True) + "\n")


def _resolve_note_path(vault_root: Path, note_path: str) -> Path:
    normalized = PurePosixPath(note_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValidationError(f"note path must stay inside vault: {note_path}")
    path = (vault_root / Path(*normalized.parts)).resolve()
    if not path.is_relative_to(vault_root):
        raise ValidationError(f"note path must stay inside vault: {note_path}")
    if path.suffix != ".md":
        raise ValidationError(f"note path must be a Markdown file: {note_path}")
    if not path.exists():
        raise ValidationError(f"note path does not exist: {note_path}")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
