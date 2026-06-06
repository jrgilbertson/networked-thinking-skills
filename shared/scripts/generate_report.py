from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.reporting import render_markdown_report
from shared.scripts.schema_validation import ValidationError, validate_run_manifest
from shared.scripts.validate_jsonl import validate_jsonl_file


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        validate_jsonl_file(args.jsonl, default_scan=True)
        rows = _read_jsonl(args.jsonl)
        manifest = _read_manifest(args.manifest)
        report = render_markdown_report(rows, manifest)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (ValidationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(str(args.output))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Atomic Note audit Markdown report.")
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _read_manifest(path: Path) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    try:
        validate_run_manifest(manifest)
    except ValidationError as exc:
        raise ValidationError(f"{path}: {exc}") from exc
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
