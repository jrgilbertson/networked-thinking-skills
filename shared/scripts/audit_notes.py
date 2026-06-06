from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.scripts.audit_engine import audit_vault


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    rows, manifest = audit_vault(args.vault, run_id=args.run_id)
    manifest["outputs"] = {
        "audit_rows": str(args.jsonl),
        "manifest": str(args.manifest),
    }

    args.jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.jsonl.open("w", encoding="utf-8") as handle:
        for row in sorted(rows, key=lambda item: str(item["note_path"])):
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"rows={len(rows)}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Atomic Notes deterministically.")
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
