"""Time: stored in UTC, shown in the owner's or the client's zone, days roll over at a set hour."""

from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo


def now_utc(env: Mapping[str, str] | None = None) -> datetime:
    """Return the current UTC time, or the time pinned by BEDROCK_NOW (used by tests)."""
    pinned = (env if env is not None else os.environ).get("BEDROCK_NOW")
    return parse(pinned) if pinned else datetime.now(UTC)


def parse(text: str) -> datetime:
    """Parse an ISO 8601 timestamp; a naive one is taken as UTC."""
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def iso(moment: datetime) -> str:
    """Format a timestamp as UTC ISO 8601 with a trailing Z, to the second."""
    return moment.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_zone(moment: datetime, zone: str) -> datetime:
    """Convert a timestamp to a named time zone."""
    return moment.astimezone(ZoneInfo(zone))


def work_date(moment: datetime, zone: str, rollover_hour: int) -> date:
    """Return the work day a moment belongs to: before the rollover hour it is the previous day."""
    local = in_zone(moment, zone)
    day = local.date()
    return day - timedelta(days=1) if local.hour < rollover_hour else day
