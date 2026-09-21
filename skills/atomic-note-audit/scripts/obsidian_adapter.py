from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any


DEFAULT_OBSIDIAN_BINARY = "obsidian"
MACOS_OBSIDIAN_CLI_PATH = Path("/Applications/Obsidian.app/Contents/MacOS/obsidian-cli")
COMMAND_TIMEOUT_SECONDS = 30
TIMEOUT_RETURN_CODE = 124


class ObsidianTransportError(Exception):
    pass


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


class ObsidianAdapter:
    def __init__(
        self,
        binary: str = DEFAULT_OBSIDIAN_BINARY,
        timeout_seconds: float | None = None,
    ) -> None:
        self.binary = binary
        self.timeout_seconds = timeout_seconds

    def available(self) -> bool:
        return resolve_obsidian_binary(self.binary) is not None

    def run(self, args: list[str]) -> CommandResult:
        resolved_binary = resolve_obsidian_binary(self.binary)
        if resolved_binary is None:
            return CommandResult(
                ok=False,
                stdout="",
                stderr=f"Unable to resolve Obsidian CLI binary: {self.binary}",
                returncode=127,
            )
        try:
            completed = subprocess.run(
                [resolved_binary, *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _as_text(exc.stdout)
            stderr = _as_text(exc.stderr)
            timeout_message = (
                f"Obsidian CLI command timed out after {self.timeout_seconds} seconds."
            )
            if stderr:
                stderr = f"{stderr.rstrip()}\n{timeout_message}"
            else:
                stderr = timeout_message
            return CommandResult(
                ok=False,
                stdout=stdout,
                stderr=stderr,
                returncode=TIMEOUT_RETURN_CODE,
            )
        except OSError as exc:
            return CommandResult(ok=False, stdout="", stderr=str(exc), returncode=126)
        return CommandResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )

    def help(self) -> CommandResult:
        return self.run(["help"])

    def read_note(self, note_path: str, *, vault: str | None = None) -> str:
        """Return a note's current content, read inside the running app."""
        result = self.run(_eval_args(build_read_note_code(note_path), vault))
        if not result.ok:
            raise ObsidianTransportError(f"Unable to read {note_path}: {_failure_text(result)}")
        return decode_eval_base64_output(result.stdout)

    def replace_in_note(
        self,
        note_path: str,
        *,
        find: str,
        replace: str,
        expected_occurrences: int,
        vault: str | None = None,
    ) -> None:
        """Substitute one exact string inside a note, inside the running app.

        The operation travels as a base64 payload because the CLI decodes
        ``\\t`` and ``\\n`` in a ``content=`` argument, which is the very
        corruption this substitution repairs. Only the matched substring is
        replaced, so other commands in the same note are never rewritten.
        """
        code = build_replace_in_note_code(
            note_path,
            find=find,
            replace=replace,
            expected_occurrences=expected_occurrences,
        )
        result = self.run(_eval_args(code, vault))
        if not result.ok:
            raise ObsidianTransportError(f"Unable to write {note_path}: {_failure_text(result)}")


def build_read_note_code(note_path: str) -> str:
    return _eval_code(
        {"action": "read", "path": note_path},
        "const data = await app.vault.read(file);"
        " const bytes = new TextEncoder().encode(data);"
        ' let binary = "";'
        " for (const byte of bytes) { binary += String.fromCharCode(byte); }"
        " return btoa(binary);",
    )


def build_replace_in_note_code(
    note_path: str,
    *,
    find: str,
    replace: str,
    expected_occurrences: int,
) -> str:
    return _eval_code(
        {
            "action": "replace",
            "path": note_path,
            "find": find,
            "replace": replace,
            "expected_occurrences": expected_occurrences,
        },
        " let replaced = 0;"
        " await app.vault.process(file, (data) => {"
        " const parts = data.split(payload.find);"
        " replaced = parts.length - 1;"
        " if (replaced !== payload.expected_occurrences) {"
        ' throw new Error("occurrence count changed: " + payload.path); }'
        " return parts.join(payload.replace); });"
        " return replaced;",
    )


def decode_eval_base64_output(stdout: str) -> str:
    """Decode the base64 string an eval prints, tolerating the `=> ` prefix.

    Every line is joined rather than only the last one. Wrapped output would
    otherwise decode cleanly from its final line, since base64 wrapped at a
    multiple of four is still valid base64, and hand back a silently truncated
    note that the write gates would then compare against.
    """
    token = stdout.strip()
    if not token:
        raise ObsidianTransportError("Obsidian eval returned no output")
    if token.startswith("=>"):
        token = token[2:]
    token = token.strip().strip("\"'")
    token = "".join(token.split())
    try:
        return base64.b64decode(token, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ObsidianTransportError(f"Obsidian eval returned unreadable output: {exc}") from exc


def _eval_code(payload: dict[str, Any], body: str) -> str:
    """Wrap a payload and a body in an app-context IIFE.

    The generated JavaScript carries no backslash of its own and the payload
    travels as base64, so nothing in the argument can be escape-decoded on the
    way to the vault.
    """
    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    ).decode("ascii")
    return (
        "(async () => {"
        f' const payload = JSON.parse(atob("{encoded}"));'
        " const file = app.vault.getAbstractFileByPath(payload.path);"
        ' if (!file) { throw new Error("missing file: " + payload.path); }'
        f" {body}"
        " })()"
    )


def _eval_args(code: str, vault: str | None) -> list[str]:
    args = ["eval", f"code={code}"]
    if vault is not None:
        args.insert(0, f"vault={vault}")
    return args


def _failure_text(result: CommandResult) -> str:
    return (result.stderr or result.stdout or f"exit code {result.returncode}").strip()


def resolve_obsidian_binary(binary: str = DEFAULT_OBSIDIAN_BINARY) -> str | None:
    candidate = _resolve_candidate(binary)
    if candidate is not None:
        resolved_candidate = candidate.resolve()
        if not _looks_like_macos_gui_binary(resolved_candidate):
            return str(candidate)

    if (
        _is_bare_command(binary)
        and binary in {DEFAULT_OBSIDIAN_BINARY, "obsidian-cli"}
        and _is_executable_file(MACOS_OBSIDIAN_CLI_PATH)
    ):
        return str(MACOS_OBSIDIAN_CLI_PATH)

    return None


def _resolve_candidate(binary: str) -> Path | None:
    binary_path = Path(binary).expanduser()
    if _is_bare_command(binary):
        found = shutil.which(binary)
        return Path(found) if found else None
    if _is_executable_file(binary_path):
        return binary_path
    found = shutil.which(binary)
    if found:
        return Path(found)
    return None


def _is_bare_command(binary: str) -> bool:
    binary_path = Path(binary)
    return binary_path.parent == Path(".") and not binary_path.is_absolute() and not binary.startswith(("~", "."))


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _looks_like_macos_gui_binary(path: Path) -> bool:
    return (
        path.name.casefold() == "obsidian"
        and path.parent.as_posix().endswith("/Obsidian.app/Contents/MacOS")
    )


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value
