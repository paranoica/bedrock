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
from datetime import datetime, timedelta
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
    """The next local clock time `HH:MM` after `now`, in the owner's zone."""
    wanted = parse_hhmm(text)
    local = now.astimezone(ZoneInfo(zone))
    target = local.replace(hour=wanted.hour, minute=wanted.minute, second=0, microsecond=0)
    return target if target > local else target + timedelta(days=1)


def _stop(process: subprocess.Popen[bytes]) -> None:
    for sig, wait in ((signal.SIGTERM, GRACE_SECONDS), (signal.SIGKILL, GRACE_SECONDS)):
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, sig)
        try:
            process.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def _run_once(argv: list[str], deadline: float) -> int | None:
    """Run the command; its exit code, or None when the deadline stopped it."""
    process = subprocess.Popen(argv, start_new_session=True)
    try:
        return process.wait(timeout=max(deadline - time.time(), 0.0))
    except subprocess.TimeoutExpired:
        _stop(process)
        return None


def watch(
    argv: list[str],
    deadline: float,
    log: Path,
    *,
    backoff: list[float] | tuple[float, ...] = BACKOFF,
    max_restarts: int = MAX_RESTARTS,
) -> Result:
    """Run `argv` until it exits cleanly, the deadline passes, or restarts run out."""
    runs = 0
    while True:
        if time.time() >= deadline:
            return Result("deadline", runs)
        started = clock.iso(clock.now_utc())
        code = _run_once(argv, deadline)
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
