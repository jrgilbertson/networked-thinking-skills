from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


DEFAULT_OBSIDIAN_BINARY = "obsidian-cli"
MACOS_OBSIDIAN_CLI_PATH = Path("/Applications/Obsidian.app/Contents/MacOS/obsidian-cli")


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
    if candidate is not None and not _looks_like_macos_gui_binary(candidate):
        return str(candidate)

    if binary == DEFAULT_OBSIDIAN_BINARY and MACOS_OBSIDIAN_CLI_PATH.is_file():
        return str(MACOS_OBSIDIAN_CLI_PATH)

    return None


def _resolve_candidate(binary: str) -> Path | None:
    binary_path = Path(binary).expanduser()
    if binary_path.is_file():
        return binary_path
    found = shutil.which(binary)
    return Path(found) if found else None


def _looks_like_macos_gui_binary(path: Path) -> bool:
    return path.name == "obsidian" and path.parent.as_posix().endswith("/Obsidian.app/Contents/MacOS")
