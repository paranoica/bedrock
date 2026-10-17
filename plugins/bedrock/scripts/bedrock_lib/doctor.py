"""`bedrock doctor`: what this machine has and lacks for bedrock (K2).

Required tools fail; optional ones warn, each with what it is for and how to get it. Nothing
here installs anything.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import UserConfig

MIN_PYTHON = (3, 12)
GPU_MB = 4000  # large-v3 in int8 or large-v3-turbo fit in this


@dataclass(frozen=True)
class Check:
    """One line of the report."""

    name: str
    level: str  # ok, warn, fail
    detail: str


class Machine(Protocol):
    """What the doctor asks the machine; tests pass a fake."""

    def which(self, name: str) -> str | None:
        """The program's path, or None."""

    def run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a short probe."""

    def has_module(self, name: str) -> bool:
        """Whether Python can import the module."""


class RealMachine:
    """This machine."""

    def which(self, name: str) -> str | None:
        """The program's path, or None."""
        return shutil.which(name)

    def run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a short probe; a hang or a failure gives empty output."""
        try:
            return subprocess.run(argv, capture_output=True, text=True, check=False, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return subprocess.CompletedProcess(argv, 1, "", "")

    def has_module(self, name: str) -> bool:
        """Whether Python can import the module."""
        return importlib.util.find_spec(name) is not None


TOOLS = (
    # name, required, what it is for, how to get it
    ("git", True, "everything", "install git"),
    ("python3", True, "hooks and scripts", "Python 3.12 or newer"),
    ("uvx", False, "ruff, black and pytest without installing them", "install uv"),
    ("node", False, "TypeScript projects, folio, the bench's web part", "Node 20 or newer"),
    ("gitleaks", False, "the secret scan in `bedrock leaks`", "install gitleaks"),
    ("age", False, "the encrypted backup", "install age"),
    ("notify-send", False, "desktop notifications", "install libnotify"),
    ("folio", False, "PDF documents (the `doc` skill)", "`npm link` in the folio folder"),
    ("claude", True, "Claude Code itself", "install Claude Code"),
)


def _tools(machine: Machine) -> list[Check]:
    found = []
    for name, required, purpose, fix in TOOLS:
        if machine.which(name) is None:
            found.append(Check(name, "fail" if required else "warn", f"missing: {purpose}. {fix}"))
            continue
        found.append(Check(name, "ok", purpose))
    return found


def _python(machine: Machine) -> Check | None:
    if machine.which("python3") is None:
        return None
    text = machine.run(["python3", "--version"]).stdout
    match = re.search(r"(\d+)\.(\d+)", text)
    if match and (int(match[1]), int(match[2])) >= MIN_PYTHON:
        return Check("python3", "ok", text.strip())
    return Check("python3", "fail", f"{text.strip() or 'unknown version'}: needs 3.12 or newer")


def _gpu(machine: Machine) -> list[Check]:
    if machine.which("nvidia-smi") is None:
        return [Check("gpu", "warn", "no NVIDIA GPU found: local transcription runs on the CPU")]
    query = ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"]
    memory = machine.run(query).stdout.strip().splitlines()
    total = int(memory[0]) if memory and memory[0].strip().isdigit() else 0
    if total < GPU_MB:
        return [Check("gpu", "warn", f"{total} MB: too small for large-v3, use a smaller model")]
    return [Check("gpu", "ok", f"{total} MB: large-v3 in int8 or large-v3-turbo fit")]


def _files(cfg: UserConfig, home: Path, machine: Machine) -> list[Check]:
    found = []
    venv = home / ".local" / "share" / "bedrock" / "whisper-venv" / "bin" / "python"
    if venv.exists():
        found.append(Check("transcription", "ok", f"faster-whisper in {venv.parent.parent}"))
    elif machine.has_module("faster_whisper"):
        found.append(Check("transcription", "ok", "faster-whisper imports"))
    else:
        found.append(
            Check("transcription", "warn", "faster-whisper not installed: on the owner's word")
        )
    terms = home / ".config" / "bedrock" / "leak-terms.txt"
    if not terms.is_file():
        found.append(Check("leak terms", "warn", f"{terms} missing: names are not checked"))
    elif terms.stat().st_mode & 0o077:
        found.append(Check("leak terms", "warn", f"{terms} is readable by others: chmod 600"))
    else:
        found.append(Check("leak terms", "ok", str(terms)))
    tools = home / ".cache" / "bedrock" / "design-tools"
    if all((tools / "node_modules" / name).is_dir() for name in ("playwright", "axe-core")):
        found.append(Check("design tools", "ok", f"playwright and axe-core in {tools}"))
    else:
        fix = f"copy design-creator's tools/package*.json to {tools}, then npm ci there"
        found.append(Check("design tools", "warn", f"design-creator cannot render: {fix}"))
    if cfg.backup_repo and cfg.backup_recipient:
        found.append(Check("backup", "ok", str(cfg.backup_repo)))
    else:
        found.append(Check("backup", "warn", "backup.repo and backup.recipient are not set"))
    return found


def run(cfg: UserConfig, home: Path, machine: Machine | None = None) -> list[Check]:
    """Every check, required tools first."""
    machine = machine or RealMachine()
    found = _tools(machine)
    python = _python(machine)
    if python is not None:
        found = [python if c.name == "python3" else c for c in found]
    return found + _gpu(machine) + _files(cfg, home, machine)


def exit_code(checks: list[Check]) -> int:
    """1 when anything failed, else 0."""
    return 1 if any(c.level == "fail" for c in checks) else 0
