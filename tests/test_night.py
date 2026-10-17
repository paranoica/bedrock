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
