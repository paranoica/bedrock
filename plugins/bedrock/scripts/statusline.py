"""Claude Code status line, design 1b: a state dot and word, calm values, colour only on trouble.

Reads Claude Code's JSON on stdin and the session state that bedrock hooks write; prints one
line. It never fails: any error still prints a minimal line, because a broken status line hides
everything else.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, TextIO

from bedrock_lib import clock, daylog
from bedrock_lib.config import SAFE_NAME, UserConfig, find_project, load_user_config

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
GREY, MAGENTA, CYAN, RED, YELLOW = 245, 176, 80, 203, 221
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
SEP = f" {DIM}·{RESET} "

TEXT = {
    "ru": {
        "idle": "готов", "work": "работаю", "wait": "жду тебя", "night": "автоном",
        "alert": "внимание", "plan": "план", "min": "м", "h5": "5ч", "week": "нед",
        "until": "до", "done": "сделано", "blocked": "заблок.",
    },
    "en": {
        "idle": "ready", "work": "working", "wait": "waiting", "night": "autonomous",
        "alert": "attention", "plan": "plan", "min": "m", "h5": "5h", "week": "wk",
        "until": "until", "done": "done", "blocked": "blocked",
    },
}  # fmt: skip
DOT = {"idle": GREY, "work": GREY, "wait": MAGENTA, "night": CYAN, "alert": RED}

# (warn, critical): yellow from warn, red above critical (D055).
CONTEXT = (40, 60)
FIVE_HOUR = (70, 85)
WEEK = (70, 85)
OVERRUN = (100, 150)


def fg(code: int) -> str:
    """Return the 256-colour foreground escape."""
    return f"\033[38;5;{code}m"


def clean(text: Any) -> str:
    """Make outside text safe for one terminal line: no escapes, no line breaks."""
    return CONTROL.sub(lambda m: " " if m.group() in "\n\r\t\x85" else "", str(text)).strip()


def level(value: int, limits: tuple[int, int]) -> int:
    """Return 2 above the critical limit, 1 from the warning limit, else 0."""
    warn, critical = limits
    return 2 if value > critical else 1 if value >= warn else 0


def paint(text: str, severity: int) -> str:
    """Colour a value only when it needs attention."""
    if severity == 2:
        return f"{fg(RED)}{BOLD}{text}{RESET}"
    if severity == 1:
        return f"{fg(YELLOW)}{text}{RESET}"
    return text


def context_percent(data: dict[str, Any], window: int) -> int | None:
    """Return context use against the compact window, not the model's full window.

    A session already past the compact window evidently compacts later, so it is measured
    against the window Claude Code reports for it.
    """
    context = data.get("context_window") or {}
    usage = context.get("current_usage")
    if not isinstance(usage, dict):
        return None
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    tokens = sum(int(usage.get(key) or 0) for key in keys)
    size = context.get("context_window_size")
    if tokens > window and isinstance(size, int) and size > 0:
        window = size
    return round(tokens * 100 / window)


def _limit(data: dict[str, Any], key: str) -> int | None:
    value = ((data.get("rate_limits") or {}).get(key) or {}).get("used_percentage")
    return round(float(value)) if isinstance(value, int | float) else None


def _meters(
    cfg: UserConfig, data: dict[str, Any], t: dict[str, str], quiet: bool
) -> list[tuple[str, int, str]]:
    fields: list[tuple[str, int, str]] = []
    context = context_percent(data, cfg.compact_window)
    five = _limit(data, "five_hour")
    week = _limit(data, "seven_day")
    if context is not None and not (quiet and level(context, CONTEXT) == 0):
        fields.append((f"{DIM}ctx{RESET} ", level(context, CONTEXT), f"{context}%"))
    if five is not None:
        fields.append((f"{DIM}{t['h5']}{RESET} ", level(five, FIVE_HOUR), f"{five}%"))
    if week is not None and week >= WEEK[0]:
        fields.append((f"{DIM}{t['week']}{RESET} ", level(week, WEEK), f"{week}%"))
    return fields


def _pair(value: Any) -> str | None:
    if isinstance(value, list) and len(value) == 2 and all(isinstance(v, int) for v in value):
        return f"{value[0]}/{value[1]}"
    return None


def _work_fields(session: dict[str, Any], t: dict[str, str], minutes: int) -> list[str]:
    fields = []
    if session.get("task"):
        fields.append(f"{BOLD}{clean(session['task'])}{RESET}")
    tags = " ".join(clean(session[key]) for key in ("risk", "priority") if session.get(key))
    if tags:
        fields.append(f"{DIM}{tags}{RESET}")
    if plan := _pair(session.get("plan")):
        fields.append(f"{DIM}{t['plan']}{RESET} {plan}")
    estimate = session.get("estimate_min")
    if isinstance(estimate, int) and estimate > 0:
        severity = level(minutes * 100 // estimate, OVERRUN)
        fields.append(paint(f"{minutes}/{estimate}{t['min']}", severity))
    return fields


def _state_fields(session: dict[str, Any], t: dict[str, str], minutes: int) -> list[str]:
    state = session.get("state")
    if state == "work":
        return _work_fields(session, t, minutes)
    if state == "wait":
        return [clean(session["waiting_for"])] if session.get("waiting_for") else []
    if state == "night":
        fields = [f"{t['until']} {clean(session['until'])}"] if session.get("until") else []
        if done := _pair(session.get("done")):
            fields.append(f"{t['done']} {done}")
        if session.get("blocked"):
            fields.append(f"{fg(YELLOW)}{t['blocked']} {clean(session['blocked'])}{RESET}")
        return fields
    if state == "alert" and session.get("alert"):
        return [f"{fg(RED)}{clean(session['alert'])}{RESET}"]
    return []


def render(
    cfg: UserConfig, data: dict[str, Any], session: dict[str, Any] | None, minutes: int
) -> str:
    """Build the status line from Claude Code's data, the session state and block minutes."""
    t = TEXT.get(cfg.language, TEXT["en"])
    session = session or {}
    state = session.get("state") if session.get("state") in DOT else "idle"
    meters = _meters(cfg, data, t, quiet=state in ("wait", "night"))
    fields = _state_fields(session, t, minutes)
    fields += [label + paint(value, severity) for label, severity, value in meters]
    critical = state == "alert" or any(severity == 2 for _, severity, _ in meters)
    dot = f"{fg(RED if critical else DOT[state])}●{RESET} {DIM}{t[state]}{RESET}"
    return f"{dot}  {SEP.join(fields)}" if fields else dot


def _session(cfg: UserConfig, session_id: Any) -> dict[str, Any] | None:
    if not isinstance(session_id, str) or not SAFE_NAME.match(session_id):
        return None
    try:
        loaded = json.loads((cfg.state_dir / "sessions" / f"{session_id}.json").read_text("utf-8"))
    except (OSError, ValueError):
        return None
    return loaded if isinstance(loaded, dict) else None


def _minutes(cfg: UserConfig, data: dict[str, Any], session: dict[str, Any] | None) -> int:
    if not session or not session.get("block") or not isinstance(data.get("cwd"), str):
        return 0
    project = find_project(Path(data["cwd"]))
    if project is None:
        return 0
    return daylog.minutes(cfg, project.name, str(session["block"]), now=clock.now_utc())


def _snapshot_limits(cfg: UserConfig, data: dict[str, Any]) -> None:
    # Hooks read the subscription limits from here: only the status line receives them.
    limits = data.get("rate_limits")
    if not isinstance(limits, dict):
        return
    snapshot = {key: limits[key] for key in ("five_hour", "seven_day") if key in limits}
    snapshot["ts"] = clock.iso(clock.now_utc())
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    temporary = cfg.state_dir / f"limits.{os.getpid()}.tmp"
    temporary.write_text(json.dumps(snapshot), encoding="utf-8")
    temporary.replace(cfg.state_dir / "limits.json")


def _with_project_window(cfg: UserConfig, data: dict[str, Any]) -> UserConfig:
    if not isinstance(data.get("cwd"), str):
        return cfg
    project = find_project(Path(data["cwd"]))
    window = project.data.get("compact_window") if project else None
    if type(window) is int and 100000 <= window <= 1000000:
        return replace(cfg, compact_window=window)
    return cfg


def main(stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> int:
    """Print the status line; on any failure print the bare state dot."""
    try:
        cfg = load_user_config()
    except Exception:  # noqa: BLE001 - a status line must print something whatever broke
        cfg = UserConfig()
    try:
        data = json.loads(stdin.read())
        if not isinstance(data, dict):
            data = {}
        _snapshot_limits(cfg, data)
        cfg = _with_project_window(cfg, data)
        session = _session(cfg, data.get("session_id"))
        line = render(cfg, data, session, _minutes(cfg, data, session))
    except Exception:  # noqa: BLE001 - same: never leave the line empty
        line = render(cfg, {}, None, 0)
    stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
