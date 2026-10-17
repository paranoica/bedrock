"""The night watchdog (D046.6): keep one command alive until a deadline.

A crash (non-zero exit) is restarted after a growing pause; a clean exit means the session
decided it is done or blocked, so the watchdog stops too. At the deadline the command's whole
process group is stopped. Every run is one line in the night log.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from . import clock, jsonl
from .config import parse_hhmm

BACKOFF = (30.0, 60.0, 120.0, 300.0, 600.0)
MAX_RESTARTS = 10
GRACE_SECONDS = 10.0


@dataclass(frozen=True)
class Result:
    """Why the watchdog stopped and how many runs it made."""

    reason: str
    runs: int


def until(text: str, now: datetime, zone: str) -> datetime:
    """The first moment after `now` when the local clock shows `HH:MM`.

    Compared in UTC, so the hour the clocks go back is seen twice, as it really happens.
    """
    wanted = parse_hhmm(text)
    local = now.astimezone(ZoneInfo(zone))
    moments = []
    for days in (0, 1):
        day = local + timedelta(days=days)
        for fold in (0, 1):
            moment = day.replace(
                hour=wanted.hour, minute=wanted.minute, second=0, microsecond=0, fold=fold
            )
            moments.append(moment)
    real = [_existing(m) for m in moments]
    after = [m for m in real if m.astimezone(UTC) > now.astimezone(UTC)]
    return min(after, key=lambda m: m.astimezone(UTC))


def _existing(moment: datetime) -> datetime:
    """The moment itself, or the first minute after it when the clocks skipped it."""
    zone = moment.tzinfo
    wall = moment.replace(tzinfo=None)
    if moment.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == wall:
        return moment
    start = moment.replace(fold=1).astimezone(UTC)
    for minutes in range(0, 181):
        local = (start + timedelta(minutes=minutes)).astimezone(zone)
        if local.replace(tzinfo=None) >= wall:
            return local
    return moment


def _kill_group(pid: int, sig: signal.Signals) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(pid, sig)


def _stop(process: subprocess.Popen[bytes]) -> None:
    """Stop the command's whole process group: SIGTERM, a grace period, then SIGKILL."""
    _kill_group(process.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=GRACE_SECONDS)
    time.sleep(min(GRACE_SECONDS, 0.2))
    _kill_group(process.pid, signal.SIGKILL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=GRACE_SECONDS)


def _run_once(argv: list[str], deadline: float, env: dict[str, str] | None) -> int | None:
    """Run the command; its exit code, or None when the deadline stopped it.

    Whatever ends the run (an exit, the deadline, an interrupt of the watchdog), nothing the
    command started is left behind.
    """
    process = subprocess.Popen(argv, start_new_session=True, env=env)
    code: int | None = None
    try:
        code = process.wait(timeout=max(deadline - time.time(), 0.0))
    except subprocess.TimeoutExpired:
        code = None
    finally:
        _stop(process)
    return code


def watch(
    argv: list[str],
    deadline: float,
    log: Path,
    *,
    backoff: list[float] | tuple[float, ...] = BACKOFF,
    max_restarts: int = MAX_RESTARTS,
    env: dict[str, str] | None = None,
) -> Result:
    """Run `argv` until it exits cleanly, the deadline passes, or restarts run out."""
    runs = 0
    while True:
        if time.time() >= deadline:
            return Result("deadline", runs)
        started = clock.iso(clock.now_utc())
        code = _run_once(argv, deadline, env)
        runs += 1
        jsonl.append(log, {"started": started, "ended": clock.iso(clock.now_utc()), "exit": code})
        if code is None:
            return Result("deadline", runs)
        if code == 0:
            return Result("finished", runs)
        if runs > max_restarts:
            return Result("gave-up", runs)
        pause = backoff[min(runs - 1, len(backoff) - 1)]
        time.sleep(min(pause, max(deadline - time.time(), 0.0)))
