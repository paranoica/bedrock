"""What every `bedrock` subcommand gets: parsed arguments, settings, folder, environment, time."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bedrock_lib import jsonl
from bedrock_lib.config import ProjectConfig, UserConfig, find_project


class UsageError(Exception):
    """The command line asks for something the command cannot do."""


class CannotRun(Exception):
    """A check could not run; the command exits 2 so a guard treats it as a refusal."""


@dataclass(frozen=True)
class Context:
    """One invocation of `bedrock`."""

    args: argparse.Namespace
    cfg: UserConfig
    cwd: Path
    env: Mapping[str, str]
    now: datetime

    def project(self) -> str:
        """Return `--project`, else the name in the nearest `.claude/bedrock.json`."""
        if getattr(self.args, "project", None):
            return str(self.args.project)
        return self.workspace().name

    def workspace(self) -> ProjectConfig:
        """Return the workspace settings above the current folder."""
        found = find_project(self.cwd)
        if found is None:
            raise UsageError("no .claude/bedrock.json above this folder; pass --project")
        return found

    def settings(self, section: str) -> dict[str, Any]:
        """Return one section of the workspace settings, or nothing outside a workspace."""
        found = find_project(self.cwd)
        value = found.data.get(section) if found else None
        return value if isinstance(value, dict) else {}


def print_json(value: Any) -> None:
    """Print a value as one line of JSON."""
    print(jsonl.dumps(value))


def json_object(text: str, what: str) -> dict[str, Any]:
    """Parse a JSON object given on the command line."""
    value = json.loads(text)
    if not isinstance(value, dict):
        raise UsageError(f"{what} must be a JSON object")
    return value
