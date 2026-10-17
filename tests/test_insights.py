import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_lib import daylog, insights
from bedrock_lib.config import UserConfig


def sh(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "app"
    root.mkdir()
    sh(root, "init", "-q")
    sh(root, "config", "user.email", "t@example.com")
    sh(root, "config", "user.name", "t")
    (root / "hot.py").write_text("x = 1\n" * 50)
    (root / "cold.py").write_text("y = 1\n" * 100)
    (root / "gone.py").write_text("z = 1\n")
    sh(root, "add", ".")
    sh(root, "commit", "-qm", "chore: start")
    for value in range(4):
        (root / "hot.py").write_text(f"x = {value}\n" * 50)
        sh(root, "commit", "-qam", f"fix: hot {value}")
    sh(root, "rm", "-q", "gone.py")
    sh(root, "commit", "-qm", "chore: drop")
    (root / "big.py").write_text("b = 1\n" * 200)
    (root / "kept.py").write_text("k = 1\n" * 900)
    sh(root, "add", ".")
    sh(root, "commit", "-qm", "feat: big")
    (root / "big.py").write_text("b = 2\n" * 200)
    sh(root, "commit", "-qam", "fix: big")
    sh(root, "rm", "-q", "--cached", "kept.py")
    sh(root, "commit", "-qm", "chore: untrack")
    return root


def test_hotspots_rank_churn_times_size(repo: Path) -> None:
    spots = insights.hotspots(repo, days=90)
    # big: 2 commits x 200 lines = 400; hot: 5 x 50 = 250; cold: 1 x 100 = 100.
    # kept.py is still on disk but no longer tracked; gone.py was deleted.
    assert [s.path for s in spots] == ["big.py", "hot.py", "cold.py"]
    assert (spots[1].changes, spots[1].lines) == (5, 50)
    assert (spots[2].changes, spots[2].lines) == (1, 100)


def test_hotspots_outside_git_fail_loudly(tmp_path: Path) -> None:
    with pytest.raises(insights.InsightError):
        insights.hotspots(tmp_path, days=90)


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def test_retro_calibrates_actual_against_estimate_per_risk(tmp_path: Path) -> None:
    cfg = UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")

    def log(event: str, block: str, when: str, detail: str = "") -> None:
        daylog.append_event(cfg, "Acme", event, block=block, detail=detail, now=at(when))

    log("taken", "T1", "2026-10-13T08:00:00", "R2/P1 export")
    log("plan-approved", "T1", "2026-10-13T08:10:00", "estimate=40")
    log("closed", "T1", "2026-10-13T09:00:00")
    log("taken", "T2", "2026-10-14T08:00:00", "R2/P2 import")
    log("plan-approved", "T2", "2026-10-14T08:05:00", "estimate=30")
    log("closed", "T2", "2026-10-14T08:30:00")
    log("taken", "T3", "2026-10-15T08:00:00", "R1/P3 typo")
    log("closed", "T3", "2026-10-15T08:10:00")
    log("taken", "T4", "2026-10-16T08:00:00", "R3/P1 open")
    log("taken", "T0", "2026-10-01T08:00:00", "R2/P1 old")
    log("closed", "T0", "2026-10-01T09:00:00")
    data = insights.retro(cfg, "Acme", now=at("2026-10-17T08:00:00"), days=7)
    assert [b["block"] for b in data["closed"]] == ["T1", "T2", "T3"]
    t1 = data["closed"][0]
    assert (t1["risk"], t1["minutes"], t1["estimate"]) == ("R2", 60, 40)
    assert data["calibration"] == {"R2": 1.25}
    assert data["open"] == ["T4"]


def test_hotspots_from_a_folder_inside_the_repository(repo: Path) -> None:
    (repo / "app").mkdir()
    (repo / "app" / "core.py").write_text("c = 1\n" * 10)
    sh(repo, "add", ".")
    sh(repo, "commit", "-qm", "feat: app")
    spots = insights.hotspots(repo / "app", days=90)
    assert [(s.path, s.changes, s.lines) for s in spots] == [("core.py", 1, 10)]
