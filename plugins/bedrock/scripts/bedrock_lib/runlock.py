"""One heavy run per machine: a lock every session and project shares, with who holds it."""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from . import clock
from .config import UserConfig


class Busy(Exception):
    """Another heavy run holds the lock and the caller chose not to wait."""


def describe(info: dict[str, Any] | None) -> str:
    """Say who holds the lock, for a waiting or refused caller."""
    if not info:
        return "unknown run"
    return (
        f"{info.get('label', '?')} (pid {info.get('pid', '?')}, since {info.get('started', '?')})"
    )


def holder(cfg: UserConfig) -> dict[str, Any] | None:
    """Return the current holder, or None when no heavy run is going."""
    lock_path = cfg.state_dir / "heavy.lock"
    if not lock_path.exists():
        return None
    with lock_path.open("a") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            try:
                return json.loads((cfg.state_dir / "heavy.json").read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
        fcntl.flock(probe, fcntl.LOCK_UN)
    return None


@contextmanager
def heavy(
    cfg: UserConfig,
    label: str,
    wait: bool = True,
    on_wait: Callable[[dict[str, Any] | None], None] | None = None,
) -> Iterator[None]:
    """Hold the machine-wide heavy-run lock; queue behind the current holder or refuse."""
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    info_path = cfg.state_dir / "heavy.json"
    with (cfg.state_dir / "heavy.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            current = holder(cfg)
            if not wait:
                raise Busy(f"a heavy run is going: {describe(current)}") from None
            if on_wait is not None:
                on_wait(current)
            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            info = {"label": label, "pid": os.getpid(), "started": clock.iso(clock.now_utc())}
            info_path.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            yield
        finally:
            info_path.unlink(missing_ok=True)
            fcntl.flock(handle, fcntl.LOCK_UN)
