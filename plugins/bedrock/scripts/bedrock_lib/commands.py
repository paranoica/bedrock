"""A project's own commands (setup, test, lint, build, ...), read from its bedrock settings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ProjectConfig

SHELL = "/bin/bash" if Path("/bin/bash").exists() else "/bin/sh"


class CommandError(Exception):
    """The project has no such command, or its settings describe one wrongly."""


@dataclass(frozen=True)
class Command:
    """One command line; a `suite` makes it a measured test run, `heavy` takes the machine lock."""

    name: str
    run: str
    suite: str | None = None
    heavy: bool = False
    serial: bool = False


def _parse(name: str, spec: Any) -> Command:
    if not isinstance(spec, dict) or not isinstance(spec.get("run"), str) or not spec["run"]:
        raise CommandError(f"command '{name}' needs a non-empty \"run\" string")
    suite = spec.get("suite")
    if suite is not None and not isinstance(suite, str):
        raise CommandError(f"command '{name}': \"suite\" must be a string")
    return Command(
        name, spec["run"], suite, bool(spec.get("heavy", False)), bool(spec.get("serial", False))
    )


def load(project: ProjectConfig) -> dict[str, Command]:
    """Return the project's commands, checked."""
    raw = project.data.get("commands")
    if not isinstance(raw, dict) or not raw:
        raise CommandError(f'{project.root}/.claude/bedrock.json has no "commands" section')
    return {name: _parse(name, spec) for name, spec in raw.items()}


def find(project: ProjectConfig, name: str) -> Command:
    """Return one command, or name the ones that exist."""
    known = load(project)
    if name not in known:
        raise CommandError(f"no command '{name}'; the project has: {', '.join(sorted(known))}")
    return known[name]


def argv(command: Command, args: Sequence[str], workers: int) -> list[str]:
    """Build the shell call; arguments travel as "$@", so they are never parsed as shell code."""
    line = command.run.replace("{workers}", str(workers))
    if "{args}" in line:
        line = line.replace("{args}", '"$@"')
    elif args:
        line += ' "$@"'
    return [SHELL, "-c", line, "bedrock", *args]
