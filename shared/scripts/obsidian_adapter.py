from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


class ObsidianAdapter:
    def __init__(self, binary: str = "obsidian") -> None:
        self.binary = binary

    def available(self) -> bool:
        return shutil.which(self.binary) is not None

    def run(self, args: list[str]) -> CommandResult:
        try:
            completed = subprocess.run(
                [self.binary, *args],
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
