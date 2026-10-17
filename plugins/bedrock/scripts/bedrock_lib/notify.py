"""Desktop notifications: which events may raise a popup, and the notify-send call that shows it."""

from __future__ import annotations

import fcntl
import hashlib
import json
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any

from . import clock
from .config import UserConfig, parse_hhmm

WINDOW = timedelta(minutes=2)
APP = "Claude Code"
SOUND = ["canberra-gtk-play", "-i", "message-new-instant"]


@dataclass(frozen=True)
class Kind:
    """How one kind of event is shown."""

    urgency: str
    sound: bool
    icon: str
    rate_limited: bool
    phone_by_day: bool
    phone_at_night: bool


KINDS = {
    "question": Kind("critical", True, "dialog-question", False, False, False),
    "p0": Kind("critical", True, "dialog-error", False, True, True),
    "blocked": Kind("critical", True, "dialog-warning", True, False, True),
    "waiting": Kind("normal", False, "dialog-information", True, False, False),
}


class NotifyError(Exception):
    """A notification request is invalid."""


@dataclass(frozen=True)
class Decision:
    """Whether and how an event is shown; `reason` says why a popup was held back."""

    popup: bool
    sound: bool
    urgency: str
    icon: str
    phone: bool
    reason: str = ""


@dataclass(frozen=True)
class Result:
    """Outcome of `send`: the decision, whether a popup appeared, and the button clicked."""

    decision: Decision
    shown: bool
    action: str | None = None


def is_quiet(cfg: UserConfig, moment: datetime) -> bool:
    """Return True inside the owner's quiet hours, read in the display zone."""
    local = clock.in_zone(moment, cfg.display_tz).time()
    start, end = parse_hhmm(cfg.quiet_start), parse_hhmm(cfg.quiet_end)
    if start <= end:
        return start <= local < end
    return local >= start or local < end


def _locked_state(cfg: UserConfig) -> Any:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    return (cfg.state_dir / "notify.lock").open("a")


def _load(cfg: UserConfig) -> dict[str, Any]:
    path = cfg.state_dir / "notify.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(cfg: UserConfig, state: dict[str, Any]) -> None:
    path = cfg.state_dir / "notify.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state), encoding="utf-8")
    temporary.replace(path)


def _kind(name: str) -> Kind:
    kind = KINDS.get(name)
    if kind is None:
        raise NotifyError(f"unknown notification kind '{name}'")
    return kind


def _fingerprint(kind_name: str, title: str, body: str) -> str:
    return hashlib.sha256(f"{kind_name}\n{title}\n{body}".encode()).hexdigest()[:16]


def _hold(kind: Kind, seen: bool, last: str | None, now: datetime) -> str:
    if seen:
        return "duplicate"
    if kind.rate_limited and last and now - clock.parse(last) < WINDOW:
        return "rate"
    return ""


def decide(
    cfg: UserConfig, kind_name: str, title: str, body: str, now: datetime | None = None
) -> Decision:
    """Decide how an event is shown, and remember what was shown for rate limiting and merging.

    Identical events merge for two minutes, whatever their kind. One popup per two minutes,
    except P0 and questions. Popups show at night too; quiet hours only add the phone for
    everything-blocked.
    """
    kind = _kind(kind_name)
    moment = now or clock.now_utc()
    night = is_quiet(cfg, moment)
    fingerprint = _fingerprint(kind_name, title, body)
    with _locked_state(cfg) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _load(cfg)
        recent = {
            key: ts
            for key, ts in state.get("recent", {}).items()
            if moment - clock.parse(ts) < WINDOW
        }
        reason = _hold(kind, fingerprint in recent, state.get("last_popup"), moment)
        wants_phone = kind.phone_at_night if night else kind.phone_by_day
        phone = wants_phone and reason != "duplicate"
        if not reason or phone:
            recent[fingerprint] = clock.iso(moment)
            previous = state.get("last_popup")
            last = previous if reason else clock.iso(moment)
            _save(cfg, {"last_popup": last, "previous_popup": previous, "recent": recent})
    return Decision(not reason, kind.sound, kind.urgency, kind.icon, phone, reason)


def _forget(cfg: UserConfig, fingerprint: str, moment: datetime, keep_fingerprint: bool) -> None:
    """Undo what `decide` recorded for a popup that never appeared."""
    stamp = clock.iso(moment)
    with _locked_state(cfg) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _load(cfg)
        recent = state.get("recent", {})
        if not keep_fingerprint and recent.get(fingerprint) == stamp:
            del recent[fingerprint]
        if state.get("last_popup") == stamp:
            state["last_popup"] = state.get("previous_popup")
        _save(cfg, state)


def send(
    cfg: UserConfig,
    kind_name: str,
    title: str,
    body: str,
    *,
    actions: Mapping[str, str] | None = None,
    timeout: float | None = None,
    now: datetime | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    which: Callable[[str], str | None] = shutil.which,
) -> Result:
    """Show the event if allowed; with buttons, wait up to `timeout` seconds for a click.

    A missing or failing notify-send is reported in the result, never raised: a notification
    must not break the work it reports on. A popup that did not appear is not counted.
    """
    moment = now or clock.now_utc()
    decision = decide(cfg, kind_name, title, body, moment)
    if not decision.popup:
        return Result(decision, False)
    fingerprint = _fingerprint(kind_name, title, body)
    if which("notify-send") is None:
        _forget(cfg, fingerprint, moment, keep_fingerprint=decision.phone)
        return Result(replace(decision, popup=False, reason="no notify-send"), False)
    if decision.sound and which(SOUND[0]):
        run(SOUND, check=False, capture_output=True, text=True)
    argv = ["notify-send", "-a", APP, "-u", decision.urgency, "-i", decision.icon]
    argv += [f"--action={key}={label}" for key, label in (actions or {}).items()]
    try:
        completed = run(
            [*argv, "--", title, body], check=False, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return Result(decision, True, None)
    if completed.returncode != 0:
        _forget(cfg, fingerprint, moment, keep_fingerprint=decision.phone)
        return Result(replace(decision, popup=False, reason="notify-send failed"), False)
    clicked = completed.stdout.strip() if actions else ""
    return Result(decision, True, clicked or None)
