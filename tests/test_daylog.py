from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_lib import daylog
from bedrock_lib.config import UserConfig


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


def log(cfg: UserConfig, event: str, at: str, block: str = "T1", detail: str = "") -> None:
    daylog.append_event(cfg, "Acme", event, block=block, detail=detail, now=utc(at))


def test_event_goes_to_the_work_day_file(cfg: UserConfig) -> None:
    # 05:00 UTC = 08:00 Minsk, before the 10:00 rollover: previous work day.
    log(cfg, "taken", "2026-10-18T05:00:00")
    path = cfg.days_dir / "Acme" / "2026-10-17" / "log.jsonl"
    assert path.exists()


def test_unknown_event_is_rejected(cfg: UserConfig) -> None:
    with pytest.raises(daylog.LogError):
        log(cfg, "finished", "2026-10-17T12:00:00")


def test_block_event_needs_a_block(cfg: UserConfig) -> None:
    with pytest.raises(daylog.LogError):
        log(cfg, "taken", "2026-10-17T12:00:00", block="")


def test_call_events_need_no_block(cfg: UserConfig) -> None:
    log(cfg, "call-start", "2026-10-17T12:00:00", block="")
    assert daylog.events(cfg, "Acme")[0]["event"] == "call-start"


def test_record_carries_utc_timestamp_and_fields(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00", detail="R2 dedupe")
    record = daylog.events(cfg, "Acme")[0]
    assert record["ts"] == "2026-10-17T12:00:00Z"
    assert record["block"] == "T1"
    assert record["detail"] == "R2 dedupe"


def test_minutes_taken_to_closed(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00")
    log(cfg, "closed", "2026-10-17T12:40:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 40


def test_minutes_skip_paused_time(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00")
    log(cfg, "paused", "2026-10-17T12:10:00")
    log(cfg, "resumed", "2026-10-17T13:00:00")
    log(cfg, "closed", "2026-10-17T13:05:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 15


def test_minutes_subtract_a_call_inside_the_block(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00")
    log(cfg, "call-start", "2026-10-17T12:10:00", block="")
    log(cfg, "call-end", "2026-10-17T12:30:00", block="")
    log(cfg, "closed", "2026-10-17T12:40:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 20


def test_minutes_subtract_only_the_overlap_of_a_call(cfg: UserConfig) -> None:
    log(cfg, "call-start", "2026-10-17T11:50:00", block="")
    log(cfg, "taken", "2026-10-17T12:00:00")
    log(cfg, "call-end", "2026-10-17T12:10:00", block="")
    log(cfg, "closed", "2026-10-17T12:40:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 30


def test_open_block_counts_to_now_only_when_asked(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 0
    now = utc("2026-10-17T12:25:00")
    assert daylog.minutes(cfg, "Acme", "T1", now=now) == 25


def test_block_spanning_two_work_days(cfg: UserConfig) -> None:
    # 06:30 UTC and 07:30 UTC fall on two work days (rollover 10:00 Minsk = 07:00 UTC).
    log(cfg, "taken", "2026-10-17T06:30:00")
    log(cfg, "closed", "2026-10-17T07:30:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 60


def test_other_blocks_do_not_count(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00", block="T2")
    log(cfg, "closed", "2026-10-17T13:00:00", block="T2")
    assert daylog.minutes(cfg, "Acme", "T1") == 0


def test_close_without_take_counts_nothing(cfg: UserConfig) -> None:
    log(cfg, "closed", "2026-10-17T12:40:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 0


def test_repeated_take_does_not_restart_the_clock(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-17T12:00:00")
    log(cfg, "taken", "2026-10-17T12:20:00")
    log(cfg, "closed", "2026-10-17T12:40:00")
    assert daylog.minutes(cfg, "Acme", "T1") == 40


def test_events_are_sorted_across_days(cfg: UserConfig) -> None:
    log(cfg, "taken", "2026-10-18T12:00:00", block="T2")
    log(cfg, "taken", "2026-10-17T12:00:00", block="T1")
    blocks = [e["block"] for e in daylog.events(cfg, "Acme")]
    assert blocks == ["T1", "T2"]


@pytest.mark.parametrize("project", ["../escape", "a/b", "", "Acme\n"])
def test_unsafe_project_name_is_rejected(cfg: UserConfig, project: str) -> None:
    with pytest.raises(daylog.LogError):
        daylog.append_event(cfg, project, "note", now=utc("2026-10-17T12:00:00"))
