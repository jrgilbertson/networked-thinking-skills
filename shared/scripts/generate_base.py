from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.base_generation import render_base
from shared.scripts.schema_validation import ValidationError
from shared.scripts.validate_jsonl import validate_jsonl_file


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        validate_jsonl_file(args.jsonl, default_scan=True)
        base = render_base(str(args.jsonl))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(base, encoding="utf-8")
    except (ValidationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(str(args.output))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Obsidian Base from audit JSONL.")
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
