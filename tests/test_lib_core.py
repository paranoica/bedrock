import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from bedrock_lib import clock, config, jsonl


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# clock


def test_work_date_before_rollover_belongs_to_previous_day() -> None:
    # 06:59 UTC is 09:59 in Minsk (UTC+3), before the 10:00 rollover.
    assert clock.work_date(utc("2026-10-17T06:59:00"), "Europe/Minsk", 10) == date(2026, 10, 16)


def test_work_date_at_rollover_belongs_to_same_day() -> None:
    assert clock.work_date(utc("2026-10-17T07:00:00"), "Europe/Minsk", 10) == date(2026, 10, 17)


def test_work_date_late_night_stays_on_the_evening_day() -> None:
    # 04:00 UTC = 07:00 Minsk, when the owner goes to sleep: still the previous work day.
    assert clock.work_date(utc("2026-10-18T04:00:00"), "Europe/Minsk", 10) == date(2026, 10, 17)


def test_client_zone_follows_daylight_saving() -> None:
    before = clock.in_zone(utc("2026-10-24T12:00:00"), "Europe/Warsaw")
    after = clock.in_zone(utc("2026-10-26T12:00:00"), "Europe/Warsaw")
    assert before.utcoffset().total_seconds() == 7200
    assert after.utcoffset().total_seconds() == 3600


def test_now_can_be_pinned_by_environment() -> None:
    assert clock.now_utc({"BEDROCK_NOW": "2026-10-17T12:00:00Z"}) == utc("2026-10-17T12:00:00")


def test_iso_is_utc_with_z() -> None:
    assert clock.iso(utc("2026-10-17T12:00:05")) == "2026-10-17T12:00:05Z"


def test_parse_round_trips_iso() -> None:
    assert clock.parse("2026-10-17T12:00:05Z") == utc("2026-10-17T12:00:05")


# config


def test_user_config_defaults_without_file(tmp_path: Path) -> None:
    cfg = config.load_user_config({"BEDROCK_CONFIG": str(tmp_path / "none.json"), "HOME": "/h"})
    assert cfg.display_tz == "Europe/Minsk"
    assert cfg.client_tz == "Europe/Warsaw"
    assert cfg.rollover_hour == 10
    assert cfg.days_dir == Path("/h/projects-days")
    assert cfg.state_dir == Path("/h/.local/state/bedrock")


def test_user_config_file_overrides_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"rollover_hour": 9, "language": "en"}))
    cfg = config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h"})
    assert cfg.rollover_hour == 9
    assert cfg.language == "en"
    assert cfg.display_tz == "Europe/Minsk"


def test_environment_overrides_directories(tmp_path: Path) -> None:
    env = {"BEDROCK_CONFIG": str(tmp_path / "none.json"), "HOME": "/h"}
    env |= {"BEDROCK_DAYS_DIR": str(tmp_path / "days"), "BEDROCK_STATE_DIR": str(tmp_path / "s")}
    cfg = config.load_user_config(env)
    assert cfg.days_dir == tmp_path / "days"
    assert cfg.state_dir == tmp_path / "s"


def test_invalid_user_config_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not json")
    with pytest.raises(config.ConfigError):
        config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h"})


def test_unknown_time_zone_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"display_tz": "Mars/Base"}))
    with pytest.raises(config.ConfigError):
        config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h"})


def test_project_found_by_walking_up(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "bedrock.json").write_text(json.dumps({"project": "Acme"}))
    deep = tmp_path / "repo" / "src"
    deep.mkdir(parents=True)
    project = config.find_project(deep)
    assert project is not None
    assert project.name == "Acme"
    assert project.root == tmp_path


def test_no_project_returns_none(tmp_path: Path) -> None:
    assert config.find_project(tmp_path) is None


@pytest.mark.parametrize("name", ["../x", "a/b", "", ".hidden", "x y"])
def test_unsafe_project_names_are_rejected(tmp_path: Path, name: str) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "bedrock.json").write_text(json.dumps({"project": name}))
    with pytest.raises(config.ConfigError):
        config.find_project(tmp_path)


# jsonl


def test_jsonl_append_and_read(tmp_path: Path) -> None:
    path = tmp_path / "a" / "log.jsonl"
    jsonl.append(path, {"n": 1})
    jsonl.append(path, {"n": 2, "text": "привет"})
    assert jsonl.read(path) == [{"n": 1}, {"n": 2, "text": "привет"}]


def test_jsonl_read_missing_is_empty(tmp_path: Path) -> None:
    assert jsonl.read(tmp_path / "none.jsonl") == []


def test_jsonl_corrupt_line_is_an_error_naming_the_line(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text('{"n": 1}\n{broken\n')
    with pytest.raises(jsonl.JsonlError, match=":2"):
        jsonl.read(path)


def test_jsonl_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text('{"n": 1}\n\n')
    assert jsonl.read(path) == [{"n": 1}]


def test_project_name_with_trailing_newline_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "bedrock.json").write_text('{"project": "Acme\\n"}')
    with pytest.raises(config.ConfigError):
        config.find_project(tmp_path)


def test_read_waits_for_a_writer_holding_the_lock(tmp_path: Path) -> None:
    import fcntl
    import threading

    path = tmp_path / "log.jsonl"
    jsonl.append(path, {"n": 1})
    done = threading.Event()
    with path.open("a") as holder:
        fcntl.flock(holder, fcntl.LOCK_EX)
        reader = threading.Thread(target=lambda: (jsonl.read(path), done.set()))
        reader.start()
        assert not done.wait(0.3)
        fcntl.flock(holder, fcntl.LOCK_UN)
    assert done.wait(2)
    reader.join()


@pytest.mark.parametrize("value", ["7", "25:00", "07:60", "seven", 7])
def test_bad_quiet_hour_is_rejected_at_load(tmp_path: Path, value: object) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"quiet_start": value}))
    with pytest.raises(config.ConfigError):
        config.load_user_config({"HOME": str(tmp_path), "BEDROCK_CONFIG": str(path)})


def test_good_quiet_hours_load(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"quiet_start": "23:00", "quiet_end": "00:00"}))
    loaded = config.load_user_config({"HOME": str(tmp_path), "BEDROCK_CONFIG": str(path)})
    assert (loaded.quiet_start, loaded.quiet_end) == ("23:00", "00:00")


@pytest.mark.parametrize("value", [99999, 1000001, "300000", True])
def test_bad_compact_window_is_rejected(tmp_path: Path, value: object) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"compact_window": value}))
    with pytest.raises(config.ConfigError):
        config.load_user_config({"HOME": str(tmp_path), "BEDROCK_CONFIG": str(path)})


def test_compact_window_defaults_to_300k_and_loads(tmp_path: Path) -> None:
    assert config.load_user_config({"HOME": str(tmp_path)}).compact_window == 300000
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"compact_window": 400000}))
    env = {"HOME": str(tmp_path), "BEDROCK_CONFIG": str(path)}
    assert config.load_user_config(env).compact_window == 400000


def test_a_bad_backup_setting_does_not_break_loading(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    backup = {"repo": "~/snap~old/mem", "recipient": "not a key"}
    path.write_text(json.dumps({"backup": backup}))
    cfg = config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h"})
    assert cfg.backup_repo == Path("/h/snap~old/mem")
    assert cfg.backup_recipient == "not a key"
    path.write_text(json.dumps({"backup": {"repo": "/srv/snap~old/mem"}}))
    cfg = config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h"})
    assert cfg.backup_repo == Path("/srv/snap~old/mem")


def test_a_backslash_in_home_does_not_break_loading(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"backup": {"repo": "~/b"}}))
    cfg = config.load_user_config({"BEDROCK_CONFIG": str(path), "HOME": "/h\\x"})
    assert cfg.backup_repo == Path("/h\\x/b")


def test_jsonl_append_keeps_a_record_with_undecodable_text(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    jsonl.append(path, {"path": "src/caf\udce9.py"})
    jsonl.append(path, {"path": "src/ok.py"})
    assert [r["path"] for r in jsonl.read(path)] == ["src/caf\udce9.py", "src/ok.py"]
