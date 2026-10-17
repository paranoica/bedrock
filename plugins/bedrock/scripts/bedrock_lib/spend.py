"""The spend mode (D009 knob 2): max, normal or save, until the 5-hour window resets."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from . import clock
from .config import UserConfig

MODES = ("max", "normal", "save")


def limits(cfg: UserConfig) -> dict[str, Any]:
    """The last subscription-limit snapshot the status line left, empty when there is none."""
    try:
        data = json.loads((cfg.state_dir / "limits.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def used(cfg: UserConfig, window: str) -> float:
    """Percent used of a window (`five_hour`, `seven_day`); 0 when unknown."""
    value = (limits(cfg).get(window) or {}).get("used_percentage")
    return float(value) if isinstance(value, int | float) else 0.0


def _window_end(cfg: UserConfig, now: datetime) -> datetime:
    reset = (limits(cfg).get("five_hour") or {}).get("resets_at")
    if isinstance(reset, int | float) and reset > now.timestamp():
        return datetime.fromtimestamp(reset, UTC)
    return now + timedelta(hours=5)


def choose(cfg: UserConfig, mode: str, now: datetime) -> str:
    """Set the mode until the current 5-hour window resets; return the end as ISO."""
    if mode not in MODES:
        raise ValueError(f"spend mode must be one of {', '.join(MODES)}")
    until = clock.iso(_window_end(cfg, now))
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    record = {"mode": mode, "until": until, "set": clock.iso(now)}
    (cfg.state_dir / "spend.json").write_text(json.dumps(record), encoding="utf-8")
    return until


def current(cfg: UserConfig, now: datetime) -> str | None:
    """The chosen mode while it lasts; None when the owner has not chosen for this window."""
    try:
        data = json.loads((cfg.state_dir / "spend.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if data.get("mode") in MODES and clock.parse(str(data.get("until"))) > now:
        return str(data["mode"])
    return None
