"""Per-session state shared by hooks, skills and the status line: task, plan, flags."""

from __future__ import annotations

import fcntl
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import SAFE_NAME, UserConfig


class SessionError(Exception):
    """The session id cannot name a state file."""


def path(cfg: UserConfig, session: str) -> Path:
    """Return the session's state file; the id must be a safe file name."""
    if not SAFE_NAME.match(session or ""):
        raise SessionError(f"session id '{session}' is not a safe file name")
    return cfg.state_dir / "sessions" / f"{session}.json"


def load(cfg: UserConfig, session: str) -> dict[str, Any]:
    """Return the session's state, empty when there is none or it is unreadable."""
    try:
        data = json.loads(path(cfg, session).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def change(
    cfg: UserConfig, session: str, edit: Callable[[dict[str, Any]], dict[str, Any]]
) -> dict[str, Any]:
    """Apply `edit` to the state under a lock and store the result."""
    target = path(cfg, session)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = edit(load(cfg, session))
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)
    return data


def update(cfg: UserConfig, session: str, values: dict[str, Any]) -> dict[str, Any]:
    """Merge values into the state; a None value removes its key.

    A key `outer.inner` sets one field of the object under `outer` and keeps its other fields.
    """

    def merge(data: dict[str, Any]) -> dict[str, Any]:
        merged = dict(data)
        for key, value in values.items():
            outer, dot, inner = key.partition(".")
            target = merged
            if dot:
                nested = merged.get(outer)
                target = merged[outer] = dict(nested) if isinstance(nested, dict) else {}
                key = inner
            if value is None:
                target.pop(key, None)
            else:
                target[key] = value
        return merged

    return change(cfg, session, merge)
