from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from schema_validation import ValidationError, ValidationResult, validate_audit_row


def validate_jsonl_file(path: Path, *, default_scan: bool) -> ValidationResult:
    valid_rows = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                validate_audit_row(row, default_scan=default_scan)
            except (json.JSONDecodeError, ValidationError) as exc:
                raise ValidationError(f"{path}:{line_number}: {exc}") from exc
            valid_rows += 1
    return ValidationResult(valid_rows=valid_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Networked Thinking audit JSONL.")
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--non-default-scan", action="store_true")
    args = parser.parse_args()
    try:
        result = validate_jsonl_file(args.jsonl, default_scan=not args.non_default_scan)
    except (ValidationError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"valid_rows={result.valid_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
