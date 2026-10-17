import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from bedrock_lib import notify
from bedrock_lib.config import UserConfig

# Display zone is Europe/Minsk (UTC+3); quiet hours 07:00-13:00 local = 04:00-10:00 UTC.
DAY = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)  # 15:00 local


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 17, hour, minute, tzinfo=UTC)


def test_question_by_day_is_a_persistent_popup_with_sound(cfg: UserConfig) -> None:
    decision = notify.decide(cfg, "question", "t", "b", now=DAY)
    assert decision.popup and decision.sound
    assert decision.urgency == "critical"
    assert not decision.phone


def test_waiting_is_a_plain_popup_without_sound(cfg: UserConfig) -> None:
    decision = notify.decide(cfg, "waiting", "t", "b", now=DAY)
    assert decision.popup
    assert not decision.sound
    assert decision.urgency == "normal"


def test_p0_by_day_also_goes_to_the_phone(cfg: UserConfig) -> None:
    decision = notify.decide(cfg, "p0", "t", "b", now=DAY)
    assert decision.popup and decision.phone


def test_night_still_shows_popups_and_phones_only_p0_and_blocked(cfg: UserConfig) -> None:
    night = at(5)  # 08:00 local
    question = notify.decide(cfg, "question", "t", "b", now=night)
    assert question.popup and question.sound and not question.phone
    assert notify.decide(cfg, "p0", "t2", "b", now=night).phone
    blocked = notify.decide(cfg, "blocked", "t3", "b", now=night + timedelta(minutes=3))
    assert blocked.popup and blocked.phone
    waiting = notify.decide(cfg, "waiting", "t4", "b", now=night + timedelta(minutes=6))
    assert waiting.popup and not waiting.phone


@pytest.mark.parametrize(
    ("moment", "night"),
    [(at(3, 59), False), (at(4, 0), True), (at(9, 59), True), (at(10, 0), False)],
)
def test_quiet_window_edges(cfg: UserConfig, moment: datetime, night: bool) -> None:
    decision = notify.decide(cfg, "blocked", "t", "b", now=moment)
    assert decision.popup
    assert decision.phone is night


def test_quiet_window_wrapping_midnight(tmp_path: Path) -> None:
    cfg = UserConfig(
        days_dir=tmp_path / "d", state_dir=tmp_path / "s", quiet_start="23:00", quiet_end="07:00"
    )
    assert notify.decide(cfg, "blocked", "a", "b", now=at(21)).phone  # 00:00 local
    assert not notify.decide(cfg, "blocked", "c", "b", now=at(12)).phone  # 15:00 local


def test_second_popup_within_two_minutes_is_held_back(cfg: UserConfig) -> None:
    assert notify.decide(cfg, "waiting", "one", "b", now=DAY).popup
    held = notify.decide(cfg, "waiting", "two", "b", now=DAY + timedelta(seconds=119))
    assert not held.popup
    assert held.reason == "rate"
    assert notify.decide(cfg, "waiting", "three", "b", now=DAY + timedelta(seconds=120)).popup


def test_held_back_popup_does_not_extend_the_window(cfg: UserConfig) -> None:
    notify.decide(cfg, "waiting", "one", "b", now=DAY)
    notify.decide(cfg, "waiting", "two", "b", now=DAY + timedelta(seconds=100))
    assert notify.decide(cfg, "waiting", "three", "b", now=DAY + timedelta(seconds=121)).popup


@pytest.mark.parametrize("kind", ["p0", "question"])
def test_p0_and_questions_skip_the_rate_limit(cfg: UserConfig, kind: str) -> None:
    notify.decide(cfg, "waiting", "one", "b", now=DAY)
    assert notify.decide(cfg, kind, "two", "b", now=DAY + timedelta(seconds=5)).popup


def test_identical_notification_merges_even_for_p0(cfg: UserConfig) -> None:
    assert notify.decide(cfg, "p0", "down", "api", now=DAY).popup
    again = notify.decide(cfg, "p0", "down", "api", now=DAY + timedelta(seconds=30))
    assert not again.popup
    assert again.reason == "duplicate"
    assert notify.decide(cfg, "p0", "down", "api", now=DAY + timedelta(seconds=120)).popup


def test_unknown_kind_is_an_error(cfg: UserConfig) -> None:
    with pytest.raises(notify.NotifyError):
        notify.decide(cfg, "shout", "t", "b", now=DAY)


class FakeRun:
    def __init__(self, stdout: str = "") -> None:
        self.calls: list[list[str]] = []
        self.stdout = stdout

    def __call__(self, argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=self.stdout, stderr="")


def test_send_passes_buttons_and_returns_the_clicked_one(cfg: UserConfig) -> None:
    run = FakeRun(stdout="spend\n")
    result = notify.send(
        cfg,
        "question",
        "Limit 81%",
        "Spend or save?",
        actions={"spend": "Spend", "save": "Save"},
        now=DAY,
        run=run,
        which=lambda name: f"/usr/bin/{name}",
    )
    popup = next(call for call in run.calls if call[0] == "notify-send")
    assert popup[popup.index("-u") : popup.index("-u") + 2] == ["-u", "critical"]
    assert "--action=spend=Spend" in popup
    assert "--action=save=Save" in popup
    assert popup[-2:] == ["Limit 81%", "Spend or save?"]
    assert result.action == "spend"
    assert any(call[0] == "canberra-gtk-play" for call in run.calls)


def test_send_without_sound_does_not_play_one(cfg: UserConfig) -> None:
    run = FakeRun()
    notify.send(cfg, "waiting", "done", "b", now=DAY, run=run, which=lambda n: f"/usr/bin/{n}")
    assert [call[0] for call in run.calls] == ["notify-send"]


def test_send_held_back_runs_nothing(cfg: UserConfig) -> None:
    notify.decide(cfg, "waiting", "first", "b", now=DAY)
    run = FakeRun()
    later = DAY + timedelta(seconds=30)
    notify.send(cfg, "waiting", "t", "b", now=later, run=run, which=lambda n: f"/usr/bin/{n}")
    assert run.calls == []


def test_send_without_notify_send_reports_instead_of_failing(cfg: UserConfig) -> None:
    run = FakeRun()
    result = notify.send(cfg, "question", "t", "b", now=DAY, run=run, which=lambda _: None)
    assert run.calls == []
    assert not result.shown
    assert result.decision.reason == "no notify-send"


def test_identical_p0_at_night_reaches_the_phone_once(cfg: UserConfig) -> None:
    assert notify.decide(cfg, "p0", "down", "api", now=at(5)).phone
    again = notify.decide(cfg, "p0", "down", "api", now=at(5, 1))
    assert not again.phone
    assert again.reason == "duplicate"


def test_night_popups_count_toward_the_rate_window(cfg: UserConfig) -> None:
    notify.decide(cfg, "waiting", "one", "b", now=at(9, 59))
    assert notify.decide(cfg, "waiting", "two", "b", now=at(10, 0)).reason == "rate"


def test_blocked_by_day_is_a_persistent_popup_without_the_phone(cfg: UserConfig) -> None:
    by_day = notify.decide(cfg, "blocked", "t", "b", now=DAY)
    assert by_day.popup and by_day.urgency == "critical" and not by_day.phone


def test_missing_notify_send_keeps_the_phone_for_p0(cfg: UserConfig) -> None:
    result = notify.send(cfg, "p0", "down", "api", now=DAY, run=FakeRun(), which=lambda _: None)
    assert not result.shown
    assert result.decision.phone


def test_title_that_looks_like_an_option_stays_text(cfg: UserConfig) -> None:
    run = FakeRun()
    notify.send(cfg, "waiting", "-u", "--help", now=DAY, run=run, which=lambda n: f"/usr/bin/{n}")
    popup = run.calls[-1]
    assert popup[-3:] == ["--", "-u", "--help"]


class FailingRun(FakeRun):
    def __call__(self, argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="no bus")


def test_failed_popup_does_not_hold_back_the_next_ones(cfg: UserConfig) -> None:
    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    failed = notify.send(cfg, "waiting", "t", "b", now=DAY, run=FailingRun(), which=which)
    assert not failed.shown
    retry = notify.send(
        cfg, "waiting", "t", "b", now=DAY + timedelta(seconds=10), run=FakeRun(), which=which
    )
    assert retry.shown
    other = notify.decide(cfg, "waiting", "other", "b", now=DAY + timedelta(seconds=20))
    assert not other.popup and other.reason == "rate"


def test_failed_popup_restores_the_earlier_window(cfg: UserConfig) -> None:
    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    notify.send(cfg, "waiting", "first", "b", now=DAY, run=FakeRun(), which=which)
    notify.send(
        cfg, "p0", "down", "b", now=DAY + timedelta(seconds=30), run=FailingRun(), which=which
    )
    held = notify.decide(cfg, "waiting", "third", "b", now=DAY + timedelta(seconds=60))
    assert held.reason == "rate"


def test_missing_notify_send_does_not_hold_back_a_later_popup(cfg: UserConfig) -> None:
    notify.send(cfg, "waiting", "t", "b", now=DAY, run=FakeRun(), which=lambda _: None)
    later = notify.send(
        cfg,
        "waiting",
        "t",
        "b",
        now=DAY + timedelta(seconds=10),
        run=FakeRun(),
        which=lambda n: f"/usr/bin/{n}",
    )
    assert later.shown


class SlowRun(FakeRun):
    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        if argv[0] == "notify-send":
            assert kwargs.get("timeout") == 30
            raise subprocess.TimeoutExpired(argv, 30)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def test_unanswered_buttons_time_out_without_an_action(cfg: UserConfig) -> None:
    result = notify.send(
        cfg,
        "question",
        "t",
        "b",
        actions={"yes": "Yes"},
        timeout=30,
        now=DAY,
        run=SlowRun(),
        which=lambda n: f"/usr/bin/{n}",
    )
    assert result.shown
    assert result.action is None
