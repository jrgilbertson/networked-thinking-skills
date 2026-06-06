from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


@dataclass
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
        completed = subprocess.run(
            [self.binary, *args],
            check=False,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            ok=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )

    def help(self) -> CommandResult:
        return self.run(["help"])
