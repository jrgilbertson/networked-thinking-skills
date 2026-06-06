"""Validate install command metadata blocks in documentation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import sys


ALLOWED_STATUSES = {"verified-local", "verified-upstream", "blocked-with-reason"}
REQUIRED_KEYS = {"runtime", "status", "source", "last_verified", "execution"}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
COMMAND_BLOCK_RE = re.compile(
    r"<!-- install-command\n(?P<metadata>.*?)\n-->\n```bash\n(?P<command>.*?)\n```",
    re.DOTALL,
)


@dataclass(frozen=True)
class InstallCommandBlock:
    """A parsed install command block with metadata and command text."""

    metadata: dict[str, str]
    command: str
    line: int


def find_command_blocks(text: str) -> list[InstallCommandBlock]:
    """Return install command blocks that match the required doc format."""
    blocks = []
    for match in COMMAND_BLOCK_RE.finditer(text):
        metadata = {}
        for raw_line in match.group("metadata").splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                metadata[line] = ""
                continue
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
        blocks.append(
            InstallCommandBlock(
                metadata=metadata,
                command=match.group("command").strip(),
                line=text.count("\n", 0, match.start()) + 1,
            )
        )
    return blocks


def validate_doc(text: str, doc_name: str = "<doc>") -> list[str]:
    """Validate all install command blocks in a document."""
    errors = []
    marker_count = text.count("<!-- install-command")
    blocks = find_command_blocks(text)
    if not blocks:
        return [f"{doc_name}: no install-command blocks found"]
    if marker_count != len(blocks):
        errors.append(
            f"{doc_name}: {marker_count - len(blocks)} install-command block(s) have invalid format"
        )

    runtimes = set()
    for block in blocks:
        prefix = f"{doc_name}:{block.line}"
        metadata = block.metadata

        missing = sorted(REQUIRED_KEYS - metadata.keys())
        if missing:
            errors.append(f"{prefix}: missing required metadata: {', '.join(missing)}")

        for key in sorted(REQUIRED_KEYS & metadata.keys()):
            if not metadata[key]:
                errors.append(f"{prefix}: metadata {key} must be non-empty")

        runtime = metadata.get("runtime", "")
        if runtime:
            if runtime in runtimes:
                errors.append(f"{prefix}: duplicate runtime: {runtime}")
            runtimes.add(runtime)

        status = metadata.get("status", "")
        if status and status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}: invalid status: {status}")

        last_verified = metadata.get("last_verified", "")
        if last_verified and not _is_iso_date(last_verified):
            errors.append(f"{prefix}: invalid last_verified date: {last_verified}")

        reason = metadata.get("reason", "")
        if status == "blocked-with-reason" and not reason:
            errors.append(f"{prefix}: blocked-with-reason requires a non-empty reason")

        if not block.command:
            errors.append(f"{prefix}: command must be non-empty")

    return errors


def _is_iso_date(value: str) -> bool:
    if not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Markdown documents to validate")
    args = parser.parse_args(argv)

    validated_docs = 0
    had_error = False
    for raw_path in args.paths:
        path = Path(raw_path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{path}: failed to read: {exc}", file=sys.stderr)
            had_error = True
            continue

        errors = validate_doc(text, str(path))
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            had_error = True
            continue
        validated_docs += 1

    if had_error:
        return 1

    print(f"validated_docs={validated_docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
