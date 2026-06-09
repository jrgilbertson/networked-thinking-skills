from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path, PurePosixPath

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.model_prompt import render_model_judgment_prompt


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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        request = render_model_judgment_request(args.vault, args.note_path)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(request, encoding="utf-8")
            print(str(args.output))
        else:
            print(request, end="")
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a model-judgment prompt for one note.")
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument(
        "--note-path",
        required=True,
        help="Path to the note relative to the vault root, such as 'Atomic Notes/Example.md'.",
    )
    parser.add_argument("--output", type=Path)
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
