"""Measured test runs: wall time and peak memory of the whole process tree, kept per project."""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import clock
from .config import SAFE_NAME, UserConfig

PAGE = os.sysconf("SC_PAGE_SIZE")
GRACE = 2.0


class TestRunError(Exception):
    """A test profile cannot be read or written as asked."""


@dataclass(frozen=True)
class Measured:
    """Outcome of one run: exit code, seconds, peak resident memory of the tree in MB."""

    returncode: int
    seconds: float
    peak_mb: float
    timed_out: bool = False


def _session_rss(session: int, proc: Path = Path("/proc")) -> int:
    total = 0
    for stat in proc.glob("[0-9]*/stat"):
        try:
            fields = stat.read_text(encoding="ascii", errors="replace").rpartition(")")[2].split()
        except OSError:
            continue
        # Fields after the command name start at field 3 (state); session is 6, rss is 24.
        if len(fields) > 21 and fields[3] == str(session):
            total += int(fields[21]) * PAGE
    return total


def _stop(group: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(group, sig)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + GRACE
        while time.monotonic() < deadline:
            try:
                os.killpg(group, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)


def run_measured(
    argv: Sequence[str],
    cwd: Path,
    *,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    sample_every: float = 0.25,
) -> Measured:
    """Run a command in its own session, sampling the memory of every process in it.

    On timeout, and after the command exits, whatever is left of its process group is stopped,
    so a test run never leaves workers behind.
    """
    started = time.monotonic()
    child = subprocess.Popen(list(argv), cwd=cwd, env=env, start_new_session=True)
    peak = 0
    timed_out = False
    try:
        while child.poll() is None:
            peak = max(peak, _session_rss(child.pid))
            if timeout is not None and time.monotonic() - started > timeout:
                timed_out = True
                break
            time.sleep(sample_every)
    finally:
        _stop(child.pid)
        returncode = child.wait()
    seconds = time.monotonic() - started
    return Measured(returncode, round(seconds, 2), round(peak / 2**20, 1), timed_out)


def _profile_path(cfg: UserConfig, project: str) -> Path:
    if not SAFE_NAME.match(project):
        raise TestRunError(f"project name '{project}' is not a safe folder name")
    return cfg.state_dir / "profiles" / f"{project}.json"


def profile(cfg: UserConfig, project: str) -> dict[str, Any]:
    """Return the project's test profile: one entry per suite."""
    path = _profile_path(cfg, project)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise TestRunError(f"{path}: {error.msg}") from error


def record(cfg: UserConfig, project: str, suite: str, run: Measured, workers: int) -> None:
    """Fold one run into the suite's profile; per-worker memory keeps the worst run seen."""
    path = _profile_path(cfg, project)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = profile(cfg, project)
        old = data.get(suite, {})
        data[suite] = {
            "runs": old.get("runs", 0) + 1,
            "last_seconds": run.seconds,
            "last_peak_mb": run.peak_mb,
            "max_peak_mb": max(old.get("max_peak_mb", 0.0), run.peak_mb),
            "per_worker_mb": max(old.get("per_worker_mb", 0.0), run.peak_mb / max(workers, 1)),
            "last_workers": workers,
            "last_exit": run.returncode,
            "updated": clock.iso(clock.now_utc()),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


def per_worker_mb(cfg: UserConfig, project: str, suite: str) -> float | None:
    """Return the measured memory per worker of a suite, or None before its first run."""
    value = profile(cfg, project).get(suite, {}).get("per_worker_mb")
    return float(value) if value else None
