import sys
import threading
import time
from pathlib import Path

import pytest
from bedrock_lib import machine, runlock, testrun
from bedrock_lib.config import UserConfig

MEMINFO = """MemTotal:       16000000 kB
MemFree:         1000000 kB
MemAvailable:    9216000 kB
Buffers:          100000 kB
"""


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


def snap(available_mb: int, cores: int, load: float = 0.5) -> machine.Snapshot:
    return machine.Snapshot(available_mb=available_mb, total_mb=16000, load1=load, cores=cores)


# machine


def test_snapshot_reads_meminfo(tmp_path: Path) -> None:
    path = tmp_path / "meminfo"
    path.write_text(MEMINFO)
    state = machine.snapshot(meminfo=path)
    assert state.available_mb == 9000
    assert state.total_mb == 15625
    assert state.cores >= 1


def test_snapshot_without_memavailable_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "meminfo"
    path.write_text("MemTotal: 100 kB\n")
    with pytest.raises(machine.MachineError):
        machine.snapshot(meminfo=path)


@pytest.mark.parametrize(
    ("available", "cores", "per_worker", "expected"),
    [
        (9000, 8, 1500, 3),  # (9000 - 3072) // 1500
        (3072, 8, 500, 1),  # nothing above the reserve still runs one worker
        (2000, 8, 500, 1),  # below the reserve
        (100000, 8, 500, 7),  # capped at cores - 1
        (100000, 1, 500, 1),  # one core
        (3572, 8, 500, 1),  # exactly one worker's worth above the reserve
        (4072, 8, 500, 2),
    ],
)
def test_worker_count(available: int, cores: int, per_worker: int, expected: int) -> None:
    assert machine.workers(snap(available, cores), per_worker_mb=per_worker) == expected


def test_unknown_worker_memory_runs_one_worker() -> None:
    assert machine.workers(snap(100000, 8), per_worker_mb=None) == 1


def test_serial_suite_runs_one_worker() -> None:
    assert machine.workers(snap(100000, 8), per_worker_mb=100, serial=True) == 1


# heavy-run lock


def test_second_heavy_run_waits_for_the_first(cfg: UserConfig) -> None:
    with runlock.heavy(cfg, "Acme: npm test"):
        assert runlock.holder(cfg)["label"] == "Acme: npm test"
        with pytest.raises(runlock.Busy) as busy, runlock.heavy(cfg, "other", wait=False):
            pass
        assert "Acme: npm test" in str(busy.value)
    assert runlock.holder(cfg) is None
    with runlock.heavy(cfg, "other", wait=False):
        pass


def test_waiting_run_starts_when_the_lock_is_freed(cfg: UserConfig) -> None:
    started = threading.Event()
    release = threading.Event()

    def first() -> None:
        with runlock.heavy(cfg, "first"):
            started.set()
            release.wait(2)

    thread = threading.Thread(target=first)
    thread.start()
    started.wait(2)
    entered: list[float] = []

    def second() -> None:
        with runlock.heavy(cfg, "second"):
            entered.append(time.monotonic())

    waiter = threading.Thread(target=second)
    waiter.start()
    time.sleep(0.2)
    assert entered == []
    release.set()
    waiter.join(2)
    thread.join(2)
    assert len(entered) == 1


# measured runs


GROW = (
    "import subprocess, sys; "
    "subprocess.run([sys.executable, '-c', "
    "'import time; b = bytearray(80 * 1024 * 1024); time.sleep(1.0)'], check=True)"
)


def test_measured_run_counts_memory_of_the_whole_process_tree(tmp_path: Path) -> None:
    result = testrun.run_measured([sys.executable, "-c", GROW], cwd=tmp_path, sample_every=0.05)
    assert result.returncode == 0
    assert result.peak_mb >= 70
    assert result.seconds >= 1.0


def test_measured_run_passes_the_exit_code(tmp_path: Path) -> None:
    result = testrun.run_measured([sys.executable, "-c", "raise SystemExit(3)"], cwd=tmp_path)
    assert result.returncode == 3


def test_timeout_kills_the_whole_tree(tmp_path: Path) -> None:
    marker = tmp_path / "survived"
    grandchild = tmp_path / "grandchild.py"
    grandchild.write_text(
        f"import time, pathlib\ntime.sleep(1.5)\npathlib.Path({str(marker)!r}).touch()\n"
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, {str(grandchild)!r}])\n"
        "time.sleep(30)\n"
    )
    started = time.monotonic()
    result = testrun.run_measured([sys.executable, str(parent)], cwd=tmp_path, timeout=0.5)
    assert time.monotonic() - started < 5
    assert result.timed_out
    assert result.returncode != 0
    time.sleep(2)
    assert not marker.exists()


def test_leftover_workers_are_stopped_after_a_normal_exit(tmp_path: Path) -> None:
    marker = tmp_path / "survived"
    grandchild = tmp_path / "grandchild.py"
    grandchild.write_text(
        f"import time, pathlib\ntime.sleep(1.0)\npathlib.Path({str(marker)!r}).touch()\n"
    )
    parent = tmp_path / "parent.py"
    parent.write_text(
        f"import subprocess, sys\nsubprocess.Popen([sys.executable, {str(grandchild)!r}])\n"
    )
    result = testrun.run_measured([sys.executable, str(parent)], cwd=tmp_path)
    assert result.returncode == 0
    assert not result.timed_out
    time.sleep(1.5)
    assert not marker.exists()


# profile


def test_profile_keeps_runs_and_the_highest_peak(cfg: UserConfig) -> None:
    testrun.record(cfg, "Acme", "unit", testrun.Measured(0, 12.0, 900.0), workers=1)
    testrun.record(cfg, "Acme", "unit", testrun.Measured(0, 10.0, 600.0), workers=2)
    suite = testrun.profile(cfg, "Acme")["unit"]
    assert suite["runs"] == 2
    assert suite["max_peak_mb"] == 900.0
    assert suite["last_peak_mb"] == 600.0
    assert suite["last_seconds"] == 10.0
    assert suite["per_worker_mb"] == 900.0


def test_per_worker_memory_comes_from_the_peak_per_worker(cfg: UserConfig) -> None:
    testrun.record(cfg, "Acme", "unit", testrun.Measured(0, 5.0, 1200.0), workers=4)
    assert testrun.per_worker_mb(cfg, "Acme", "unit") == 300.0
    assert testrun.per_worker_mb(cfg, "Acme", "e2e") is None


def test_profile_rejects_unsafe_project(cfg: UserConfig) -> None:
    with pytest.raises(testrun.TestRunError):
        testrun.profile(cfg, "../x")
