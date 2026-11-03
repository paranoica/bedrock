"""The subscription limits the status line last saw."""

from __future__ import annotations

import json
from typing import Any

from .config import UserConfig


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
