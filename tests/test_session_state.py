import io
import json
import threading
from pathlib import Path

import pytest
import statusline
from bedrock_lib import session
from bedrock_lib.config import UserConfig


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "d", state_dir=tmp_path / "s")


def test_missing_session_is_empty(cfg: UserConfig) -> None:
    assert session.load(cfg, "s1") == {}


def test_update_merges_and_persists(cfg: UserConfig) -> None:
    session.update(cfg, "s1", {"state": "work", "task": "x"})
    session.update(cfg, "s1", {"task": "y"})
    assert session.load(cfg, "s1") == {"state": "work", "task": "y"}


def test_none_removes_a_key(cfg: UserConfig) -> None:
    session.update(cfg, "s1", {"a": 1, "b": 2})
    session.update(cfg, "s1", {"a": None})
    assert session.load(cfg, "s1") == {"b": 2}


def test_parallel_updates_lose_nothing(cfg: UserConfig) -> None:
    def bump(key: str) -> None:
        for _ in range(20):
            session.change(cfg, "s1", lambda data, key=key: {**data, key: data.get(key, 0) + 1})

    threads = [threading.Thread(target=bump, args=(k,)) for k in ("a", "b", "c")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert session.load(cfg, "s1") == {"a": 20, "b": 20, "c": 20}


@pytest.mark.parametrize("bad", ["../x", "a/b", ""])
def test_unsafe_session_id_is_rejected(cfg: UserConfig, bad: str) -> None:
    with pytest.raises(session.SessionError):
        session.update(cfg, bad, {"a": 1})


def test_status_line_leaves_a_limits_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    data = {
        "session_id": "s1",
        "rate_limits": {
            "five_hour": {"used_percentage": 81.5, "resets_at": 1792000000},
            "seven_day": {"used_percentage": 40, "resets_at": 1792500000},
        },
    }
    statusline.main(io.StringIO(json.dumps(data)), io.StringIO())
    snapshot = json.loads((tmp_path / ".local/state/bedrock/limits.json").read_text())
    assert snapshot["five_hour"] == {"used_percentage": 81.5, "resets_at": 1792000000}
    assert snapshot["seven_day"]["used_percentage"] == 40
    assert "ts" in snapshot
