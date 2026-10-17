import sys
import time
from pathlib import Path

from bedrock_lib import jsonl, night

PY = sys.executable


def test_a_crash_is_restarted_until_the_command_ends_cleanly(tmp_path: Path) -> None:
    counter = tmp_path / "n"
    script = (
        "import pathlib,sys; p=pathlib.Path(sys.argv[1]); n=int(p.read_text() or 0)+1 "
        "if p.exists() else 1; p.write_text(str(n)); sys.exit(0 if n >= 3 else 1)"
    )
    log = tmp_path / "night.jsonl"
    result = night.watch([PY, "-c", script, str(counter)], time.time() + 30, log, backoff=[0.01])
    assert result == night.Result("finished", 3)
    assert [r["exit"] for r in jsonl.read(log)] == [1, 1, 0]


def test_restarts_are_capped(tmp_path: Path) -> None:
    log = tmp_path / "night.jsonl"
    result = night.watch(
        [PY, "-c", "raise SystemExit(2)"], time.time() + 30, log, backoff=[0.01], max_restarts=2
    )
    assert result == night.Result("gave-up", 3)


def test_the_deadline_stops_a_running_command(tmp_path: Path) -> None:
    log = tmp_path / "night.jsonl"
    started = time.monotonic()
    result = night.watch(
        [PY, "-c", "import time; time.sleep(60)"], time.time() + 1, log, backoff=[0.01]
    )
    assert result.reason == "deadline"
    assert time.monotonic() - started < 10


def test_until_parses_a_local_clock_time() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("Europe/Minsk")
    now = datetime(2026, 10, 17, 23, 0, tzinfo=zone)
    assert night.until("12:00", now, "Europe/Minsk") == datetime(2026, 10, 18, 12, 0, tzinfo=zone)
    morning = datetime(2026, 10, 17, 9, 0, tzinfo=zone)
    assert night.until("12:00", morning, "Europe/Minsk") == datetime(
        2026, 10, 17, 12, 0, tzinfo=zone
    )


def _alive(pid_file: Path) -> bool:
    import os

    try:
        os.kill(int(pid_file.read_text()), 0)
    except (ProcessLookupError, ValueError, FileNotFoundError):
        return False
    return True


def test_the_deadline_stops_children_that_ignore_sigterm(tmp_path: Path) -> None:
    pid = tmp_path / "pid"
    child = (
        "import signal,time,os,sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"open({str(pid)!r},'w').write(str(os.getpid())); time.sleep(60)"
    )
    spawn = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}])"
    parent = spawn + "; time.sleep(60)"
    night.GRACE_SECONDS = 0.5
    night.watch([PY, "-c", parent], time.time() + 1.5, tmp_path / "log.jsonl", backoff=[0.01])
    time.sleep(0.3)
    assert not _alive(pid)


def test_leftover_children_die_with_their_run(tmp_path: Path) -> None:
    pid = tmp_path / "pid"
    child = f"import os,time; open({str(pid)!r},'w').write(str(os.getpid())); time.sleep(60)"
    spawn = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}])"
    parent = spawn + "; time.sleep(0.5); sys.exit(3)"
    night.GRACE_SECONDS = 0.5
    night.watch(
        [PY, "-c", parent], time.time() + 30, tmp_path / "log.jsonl", backoff=[0.01], max_restarts=0
    )
    time.sleep(0.3)
    assert not _alive(pid)


def test_an_interrupted_watchdog_stops_its_command(tmp_path: Path, monkeypatch) -> None:
    import subprocess

    pid = tmp_path / "pid"
    script = f"import os,time; open({str(pid)!r},'w').write(str(os.getpid())); time.sleep(60)"
    real_wait = subprocess.Popen.wait

    def interrupted(self, timeout=None):
        if timeout and timeout > 5:
            time.sleep(0.5)
            raise KeyboardInterrupt
        return real_wait(self, timeout=timeout)

    monkeypatch.setattr(subprocess.Popen, "wait", interrupted)
    night.GRACE_SECONDS = 0.5
    import pytest

    with pytest.raises(KeyboardInterrupt):
        night.watch([PY, "-c", script], time.time() + 30, tmp_path / "log.jsonl")
    time.sleep(0.3)
    assert not _alive(pid)


def test_until_on_the_night_clocks_go_back() -> None:
    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("Europe/Berlin")
    now = datetime(2026, 10, 25, 2, 40, tzinfo=zone)  # first pass, +02:00
    target = night.until("02:20", now, "Europe/Berlin")
    assert target.astimezone(UTC) == datetime(2026, 10, 25, 1, 20, tzinfo=UTC)


def test_until_on_the_night_clocks_go_forward() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 3, 28, 23, 0, tzinfo=UTC)
    target = night.until("02:30", now, "Europe/Warsaw")  # 02:30 does not exist that night
    assert target.astimezone(UTC) == datetime(2026, 3, 29, 1, 0, tzinfo=UTC)  # 03:00 local
