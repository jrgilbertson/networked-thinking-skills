from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


DEFAULT_OBSIDIAN_BINARY = "obsidian"
MACOS_OBSIDIAN_CLI_PATH = Path("/Applications/Obsidian.app/Contents/MacOS/obsidian-cli")
COMMAND_TIMEOUT_SECONDS = 30
TIMEOUT_RETURN_CODE = 124


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


class ObsidianAdapter:
    def __init__(self, binary: str = DEFAULT_OBSIDIAN_BINARY) -> None:
        self.binary = binary

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
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _as_text(exc.stdout)
            stderr = _as_text(exc.stderr)
            timeout_message = (
                f"Obsidian CLI command timed out after {COMMAND_TIMEOUT_SECONDS} seconds."
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
