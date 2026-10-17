"""The owner's settings and a project's settings, with defaults and environment overrides."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

PROJECT_FILE = Path(".claude") / "bedrock.json"
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


class ConfigError(Exception):
    """A settings file is unreadable or holds an invalid value."""


@dataclass(frozen=True)
class UserConfig:
    """Settings that belong to the owner and hold for every project."""

    display_tz: str = "Europe/Minsk"
    client_tz: str = "Europe/Warsaw"
    rollover_hour: int = 10
    language: str = "ru"
    quiet_start: str = "07:00"
    quiet_end: str = "13:00"
    compact_window: int = 300000
    days_dir: Path = Path("projects-days")
    memory_bank_dir: Path = Path("projects-memory-bank")
    state_dir: Path = Path(".local/state/bedrock")
    backup_repo: Path | None = None
    backup_recipient: str = ""


@dataclass(frozen=True)
class ProjectConfig:
    """A project's own settings, read from `<workspace>/.claude/bedrock.json`."""

    name: str
    root: Path
    data: dict[str, Any] = field(default_factory=dict)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold a JSON object")
    return data


def parse_hhmm(text: object) -> time:
    """Parse a local clock time written as HH:MM."""
    match = re.fullmatch(r"(\d{2}):(\d{2})", text) if isinstance(text, str) else None
    if match is None or int(match[1]) > 23 or int(match[2]) > 59:
        raise ConfigError(f"'{text}' is not a time of day as HH:MM")
    return time(int(match[1]), int(match[2]))


def _check_zone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ConfigError(f"unknown time zone '{name}'") from error
    return name


def _check_hhmm(text: str) -> str:
    parse_hhmm(text)
    return text


def _backup(data: dict[str, Any], home: Path) -> tuple[Path | None, str]:
    """Read the backup settings; they are checked when `bedrock backup` runs, not here."""
    section = data.get("backup")
    section = section if isinstance(section, dict) else {}
    repo, recipient = section.get("repo"), section.get("recipient")
    path = None
    if isinstance(repo, str) and repo:
        path = Path(str(home) + repo[1:]) if repo == "~" or repo.startswith("~/") else Path(repo)
    return path, recipient if isinstance(recipient, str) else ""


def load_user_config(env: Mapping[str, str] | None = None) -> UserConfig:
    """Load the owner's settings from BEDROCK_CONFIG or `~/.config/bedrock/config.json`."""
    env = env if env is not None else os.environ
    home = Path(env.get("HOME", str(Path.home())))
    path = Path(env.get("BEDROCK_CONFIG", str(home / ".config" / "bedrock" / "config.json")))
    data = _read_json(path) if path.exists() else {}
    defaults = UserConfig()
    rollover = data.get("rollover_hour", defaults.rollover_hour)
    if not isinstance(rollover, int) or not 0 <= rollover <= 23:
        raise ConfigError("rollover_hour must be an integer from 0 to 23")
    window = data.get("compact_window", defaults.compact_window)
    if isinstance(window, bool) or not isinstance(window, int) or not 100000 <= window <= 1000000:
        raise ConfigError("compact_window must be an integer from 100000 to 1000000")

    backup_repo, backup_recipient = _backup(data, home)

    def directory(key: str, env_key: str, default: Path) -> Path:
        value = env.get(env_key) or data.get(key)
        return Path(value).expanduser() if value else home / default

    return UserConfig(
        display_tz=_check_zone(data.get("display_tz", defaults.display_tz)),
        client_tz=_check_zone(data.get("client_tz", defaults.client_tz)),
        rollover_hour=rollover,
        language=data.get("language", defaults.language),
        quiet_start=_check_hhmm(data.get("quiet_start", defaults.quiet_start)),
        quiet_end=_check_hhmm(data.get("quiet_end", defaults.quiet_end)),
        compact_window=window,
        days_dir=directory("days_dir", "BEDROCK_DAYS_DIR", defaults.days_dir),
        memory_bank_dir=directory(
            "memory_bank_dir", "BEDROCK_MEMORY_BANK", defaults.memory_bank_dir
        ),
        state_dir=directory("state_dir", "BEDROCK_STATE_DIR", defaults.state_dir),
        backup_repo=backup_repo,
        backup_recipient=backup_recipient,
    )


def find_project(start: Path) -> ProjectConfig | None:
    """Walk up from `start` to the first workspace holding `.claude/bedrock.json`."""
    for folder in (start.resolve(), *start.resolve().parents):
        path = folder / PROJECT_FILE
        if path.is_file():
            data = _read_json(path)
            name = data.get("project", "")
            if not isinstance(name, str) or not SAFE_NAME.match(name):
                raise ConfigError(f"{path}: project name '{name}' is not a safe folder name")
            return ProjectConfig(name=name, root=folder, data=data)
    return None
