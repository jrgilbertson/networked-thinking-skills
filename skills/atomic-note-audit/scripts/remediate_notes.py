from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from remediation import (
    RemediationError,
    build_dry_run_manifest,
    validate_plan,
)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        validate_plan(plan, destructive_allowed=args.destructive_allowed)
        manifest = build_dry_run_manifest(plan)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (RemediationError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"operation_count={manifest['operation_count']}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate or dry-run Networked Thinking remediation plans.")
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--destructive-allowed", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
