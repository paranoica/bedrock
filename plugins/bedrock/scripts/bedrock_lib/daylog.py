"""The day log: one JSON Lines file per project and work day, written only through this module."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from . import clock, jsonl
from .config import SAFE_NAME, UserConfig

BLOCK_EVENTS = {
    "taken",
    "plan-approved",
    "task-done",
    "review",
    "merged",
    "closed",
    "paused",
    "resumed",
    "debug-start",
    "debug-loop",
    "debug-cause",
    "debug-done",
}
FREE_EVENTS = {"call-start", "call-end", "note"}
EVENTS = BLOCK_EVENTS | FREE_EVENTS
STARTS = {"taken", "resumed"}
STOPS = {"paused", "closed"}


class LogError(Exception):
    """An event cannot be logged as given."""


def project_dir(cfg: UserConfig, project: str) -> Path:
    """Return the folder holding a project's day folders; the name must be a safe folder name."""
    if not SAFE_NAME.match(project):
        raise LogError(f"project name '{project}' is not a safe folder name")
    return cfg.days_dir / project


def append_event(
    cfg: UserConfig,
    project: str,
    event: str,
    *,
    block: str = "",
    detail: str = "",
    refs: Iterable[str] = (),
    session: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append one event to the log of the work day `now` falls on and return the record."""
    if event not in EVENTS:
        raise LogError(f"unknown event '{event}'")
    if event in BLOCK_EVENTS and not block:
        raise LogError(f"event '{event}' needs a block")
    moment = now or clock.now_utc()
    record = {
        "ts": clock.iso(moment),
        "event": event,
        "block": block,
        "detail": detail,
        "refs": list(refs),
        "session": session,
    }
    day = clock.work_date(moment, cfg.display_tz, cfg.rollover_hour)
    jsonl.append(project_dir(cfg, project) / day.isoformat() / "log.jsonl", record)
    return record


def events(cfg: UserConfig, project: str) -> list[dict[str, Any]]:
    """Return every event of a project across all days, oldest first."""
    records: list[dict[str, Any]] = []
    for path in sorted(project_dir(cfg, project).glob("*/log.jsonl")):
        records.extend(jsonl.read(path))
    return sorted(records, key=lambda record: record["ts"])


def _spans(
    records: list[dict[str, Any]],
    start_events: set[str],
    stop_events: set[str],
    now: datetime | None,
) -> list[tuple[datetime, datetime]]:
    spans: list[tuple[datetime, datetime]] = []
    started: datetime | None = None
    for record in records:
        moment = clock.parse(record["ts"])
        if record["event"] in start_events and started is None:
            started = moment
        elif record["event"] in stop_events and started is not None:
            spans.append((started, moment))
            started = None
    if started is not None and now is not None:
        spans.append((started, now))
    return spans


def _overlap(span: tuple[datetime, datetime], other: tuple[datetime, datetime]) -> float:
    start, end = max(span[0], other[0]), min(span[1], other[1])
    return max((end - start).total_seconds(), 0.0)


def minutes(cfg: UserConfig, project: str, block: str, now: datetime | None = None) -> int:
    """Return a block's working minutes: active spans minus calls; an open span counts to `now`."""
    records = events(cfg, project)
    work = _spans([r for r in records if r["block"] == block], STARTS, STOPS, now)
    calls = _spans(records, {"call-start"}, {"call-end"}, now)
    seconds = sum((end - start).total_seconds() for start, end in work)
    seconds -= sum(_overlap(span, call) for span in work for call in calls)
    return round(seconds / 60)
