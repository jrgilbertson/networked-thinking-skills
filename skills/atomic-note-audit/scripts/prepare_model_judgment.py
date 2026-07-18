from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from model_prompt import render_model_judgment_prompt
from schema_validation import ValidationError, validate_audit_row


def render_model_judgment_request(vault_root: Path, note_path: str) -> str:
    vault_root = vault_root.resolve()
    resolved_note_path = _resolve_note_path(vault_root, note_path)
    relative_note_path = resolved_note_path.relative_to(vault_root).as_posix()
    content = resolved_note_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return "\n".join(
        [
            render_model_judgment_prompt().rstrip(),
            "",
            "## Note To Judge",
            "",
            f"Use this exact `note_path`: `{relative_note_path}`.",
            f"Content SHA-256: `{digest}`.",
            "",
            "NOTE_CONTENT_START",
            content.rstrip(),
            "NOTE_CONTENT_END",
            "",
        ]
    )


def prepare_collector_input(audit_jsonl: Path, note_path: str) -> str:
    selected: dict[str, Any] | None = None
    for line_number, line in enumerate(audit_jsonl.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            validate_audit_row(row, default_scan=True)
        except ValidationError as exc:
            raise ValidationError(f"audit row line {line_number}: {exc}") from exc
        if row["note_path"] != note_path:
            continue
        if selected is not None:
            raise ValidationError(f"duplicate audit row note_path: {note_path}")
        selected = row

    if selected is None:
        raise ValidationError(f"audit row not found for note_path: {note_path}")
    return json.dumps(selected, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        _resolve_note_path(args.vault.resolve(), args.note_path)
        if args.collector_input:
            if args.audit_jsonl is None:
                raise ValidationError("--collector-input requires --audit-jsonl")
            collector_input = prepare_collector_input(args.audit_jsonl, args.note_path)
            args.collector_input.parent.mkdir(parents=True, exist_ok=True)
            args.collector_input.write_text(collector_input, encoding="utf-8")
            print(str(args.collector_input))
        elif args.audit_jsonl is not None:
            raise ValidationError("--audit-jsonl requires --collector-input")
        else:
            request = render_model_judgment_request(args.vault, args.note_path)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(request, encoding="utf-8")
                print(str(args.output))
            else:
                print(request, end="")
    except (json.JSONDecodeError, OSError, ValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a model-judgment prompt or trusted-collector input for one note."
    )
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument(
        "--note-path",
        required=True,
        help="Path to the note relative to the vault root, such as 'Atomic Notes/Example.md'.",
    )
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--output", type=Path, help="Write the raw content prompt for inspection.")
    outputs.add_argument(
        "--collector-input",
        type=Path,
        help="Write the note's validated audit row as collector input JSONL.",
    )
    parser.add_argument(
        "--audit-jsonl",
        type=Path,
        help="Deterministic audit JSONL; required with --collector-input.",
    )
    return parser.parse_args(argv)


def _resolve_note_path(vault_root: Path, note_path: str) -> Path:
    normalized = PurePosixPath(note_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise OSError(f"note path must stay inside vault: {note_path}")
    path = (vault_root / Path(*normalized.parts)).resolve()
    if not path.is_relative_to(vault_root):
        raise OSError(f"note path must stay inside vault: {note_path}")
    if path.suffix != ".md":
        raise OSError(f"note path must be a Markdown file: {note_path}")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
