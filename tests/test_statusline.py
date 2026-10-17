import io
import json
import re
from pathlib import Path

import pytest
import statusline
from bedrock_lib.config import UserConfig

ANSI = re.compile(r"\033\[[0-9;]*m")
RED = "\033[38;5;203m"
YELLOW = "\033[38;5;221m"


def plain(text: str) -> str:
    return ANSI.sub("", text)


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state", language="ru")


def payload(context_tokens: int = 114000, five: float = 42.0, week: float = 20.0) -> dict:
    return {
        "session_id": "s1",
        "cwd": "/tmp",
        "context_window": {
            "current_usage": {
                "input_tokens": 1000,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": context_tokens - 1000,
                "output_tokens": 10,
            },
            "context_window_size": 1000000,
        },
        "rate_limits": {
            "five_hour": {"used_percentage": five, "resets_at": 1792000000},
            "seven_day": {"used_percentage": week, "resets_at": 1792500000},
        },
    }


WORK = {
    "state": "work",
    "task": "дедуп поиска",
    "risk": "R2",
    "priority": "P1",
    "plan": [2, 5],
    "estimate_min": 40,
}


def test_work_line_has_task_plan_time_context_and_limit(cfg: UserConfig) -> None:
    line = statusline.render(cfg, payload(), WORK, minutes=23)
    assert plain(line) == "● работаю  дедуп поиска · R2 P1 · план 2/5 · 23/40м · ctx 38% · 5ч 42%"


def test_english_preset(tmp_path: Path) -> None:
    cfg = UserConfig(days_dir=tmp_path / "d", state_dir=tmp_path / "s", language="en")
    line = plain(statusline.render(cfg, payload(), WORK, minutes=23))
    assert line.startswith("● working  ")
    assert "plan 2/5" in line and "23/40m" in line and "5h 42%" in line


def test_context_is_measured_against_the_compact_window_not_one_million(
    cfg: UserConfig,
) -> None:
    line = plain(statusline.render(cfg, payload(context_tokens=150000), WORK, minutes=0))
    assert "ctx 50%" in line


@pytest.mark.parametrize(
    ("tokens", "colour"),
    [(117000, None), (120000, YELLOW), (180000, YELLOW), (183000, RED)],
)
def test_context_colour_thresholds(cfg: UserConfig, tokens: int, colour: str | None) -> None:
    line = statusline.render(cfg, payload(context_tokens=tokens), WORK, minutes=0)
    field = line.split("ctx")[1].split("·")[0]
    if colour is None:
        assert RED not in field and YELLOW not in field
    else:
        assert colour in field


@pytest.mark.parametrize(
    ("five", "colour"), [(69.4, None), (69.6, YELLOW), (85, YELLOW), (85.6, RED), (100, RED)]
)
def test_five_hour_thresholds(cfg: UserConfig, five: float, colour: str | None) -> None:
    line = statusline.render(cfg, payload(five=five), WORK, minutes=0)
    field = line.split("5ч")[1]
    if colour is None:
        assert RED not in field and YELLOW not in field
    else:
        assert colour in field


@pytest.mark.parametrize(
    ("spent", "colour"), [(0, None), (39, None), (40, YELLOW), (60, YELLOW), (61, RED)]
)
def test_time_against_estimate(cfg: UserConfig, spent: int, colour: str | None) -> None:
    line = statusline.render(cfg, payload(), WORK, minutes=spent)
    field = line.split(f"{spent}/40")[0][-20:]
    if colour is None:
        assert RED not in field and YELLOW not in field
    else:
        assert colour in field


def test_week_shows_only_when_it_gets_high(cfg: UserConfig) -> None:
    assert "нед" not in plain(statusline.render(cfg, payload(week=69), WORK, minutes=0))
    assert "нед 70%" in plain(statusline.render(cfg, payload(week=70), WORK, minutes=0))


def test_waiting_line(cfg: UserConfig) -> None:
    session = {"state": "wait", "waiting_for": "тратим или экономим?"}
    line = plain(statusline.render(cfg, payload(five=81), session, minutes=0))
    assert line == "● жду тебя  тратим или экономим? · 5ч 81%"


def test_night_line(cfg: UserConfig) -> None:
    session = {"state": "night", "until": "12:00", "done": [4, 7], "blocked": 1}
    line = plain(statusline.render(cfg, payload(five=55), session, minutes=0))
    assert line == "● автоном  до 12:00 · сделано 4/7 · заблок. 1 · 5ч 55%"


def test_alert_line_carries_the_reason(cfg: UserConfig) -> None:
    session = {"state": "alert", "alert": "CI красный"}
    line = statusline.render(cfg, payload(), session, minutes=0)
    assert plain(line).startswith("● внимание  CI красный")
    assert RED in line.split("CI")[0]


def test_without_session_state_shows_the_basics(cfg: UserConfig) -> None:
    line = plain(statusline.render(cfg, payload(), None, minutes=0))
    assert line == "● готов  ctx 38% · 5ч 42%"


def test_missing_rate_limits_and_context_are_left_out(cfg: UserConfig) -> None:
    line = plain(statusline.render(cfg, {"session_id": "s1"}, None, minutes=0))
    assert line == "● готов"


def test_dot_turns_red_when_anything_is_critical(cfg: UserConfig) -> None:
    line = statusline.render(cfg, payload(five=90), WORK, minutes=0)
    assert line.startswith(RED + "●")


def test_task_name_is_bold_and_cleaned_of_control_characters(cfg: UserConfig) -> None:
    session = dict(WORK, task="evil\033[31m\nname")
    line = statusline.render(cfg, payload(), session, minutes=0)
    assert "\033[31m" not in line
    assert "\n" not in line
    assert "\033[1mevil[31m name\033[0m" in line


def test_main_never_crashes_on_garbage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    out = io.StringIO()
    assert statusline.main(io.StringIO("not json"), out) == 0
    assert plain(out.getvalue()).startswith("●")


def test_main_reads_session_state_and_minutes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BEDROCK_NOW", "2026-10-17T12:23:00Z")
    workspace = tmp_path / "app"
    (workspace / ".claude").mkdir(parents=True)
    (workspace / ".claude" / "bedrock.json").write_text('{"project": "Acme"}')
    day = tmp_path / "projects-days" / "Acme" / "2026-10-17"
    day.mkdir(parents=True)
    taken = {"ts": "2026-10-17T12:00:00Z", "event": "taken", "block": "T1"}
    (day / "log.jsonl").write_text(json.dumps(taken) + "\n")
    sessions = tmp_path / ".local/state/bedrock/sessions"
    sessions.mkdir(parents=True)
    (sessions / "s1.json").write_text(json.dumps(dict(WORK, block="T1")))
    data = dict(payload(), cwd=str(workspace))
    out = io.StringIO()
    assert statusline.main(io.StringIO(json.dumps(data)), out) == 0
    assert "23/40м" in plain(out.getvalue())


def test_session_id_cannot_escape_the_sessions_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    secret = tmp_path / ".local/state/bedrock/x.json"
    secret.parent.mkdir(parents=True)
    secret.write_text(json.dumps({"state": "alert", "alert": "LEAKED"}))
    data = dict(payload(), session_id="../x")
    out = io.StringIO()
    statusline.main(io.StringIO(json.dumps(data)), out)
    assert "LEAKED" not in out.getvalue()


def test_waiting_line_shows_context_once_it_needs_attention(cfg: UserConfig) -> None:
    session = {"state": "wait", "waiting_for": "x"}
    line = plain(statusline.render(cfg, payload(context_tokens=150000), session, minutes=0))
    assert "ctx 50%" in line


def test_c1_control_characters_are_removed(cfg: UserConfig) -> None:
    session = dict(WORK, task="x\x9b31my\x85z")
    line = statusline.render(cfg, payload(), session, minutes=0)
    assert "\x9b" not in line and "\x85" not in line


def test_project_compact_window_overrides_the_owner_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace = tmp_path / "app"
    (workspace / ".claude").mkdir(parents=True)
    settings = {"project": "Acme", "compact_window": 400000}
    (workspace / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    data = dict(payload(context_tokens=150000), cwd=str(workspace))
    out = io.StringIO()
    statusline.main(io.StringIO(json.dumps(data)), out)
    assert "ctx 38%" in plain(out.getvalue())


def test_a_session_past_the_compact_window_is_measured_against_its_real_window(
    cfg: UserConfig,
) -> None:
    # 750k used: this session does not compact at 300k, which would read as 250%.
    line = plain(statusline.render(cfg, payload(context_tokens=750000), WORK, minutes=0))
    assert "ctx 75%" in line
    at_window = plain(statusline.render(cfg, payload(context_tokens=300000), WORK, minutes=0))
    assert "ctx 100%" in at_window
