"""What the machine can take right now: free memory, load, cores, and how many test workers fit."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

RESERVE_MB = 3072


class MachineError(Exception):
    """The machine's state cannot be read."""


@dataclass(frozen=True)
class Snapshot:
    """Memory in MB, the one-minute load average and the cores this process may use."""

    available_mb: int
    total_mb: int
    load1: float
    cores: int


def snapshot(meminfo: Path = Path("/proc/meminfo")) -> Snapshot:
    """Read the current memory, load and core count."""
    fields: dict[str, int] = {}
    try:
        for line in meminfo.read_text(encoding="ascii").splitlines():
            name, _, value = line.partition(":")
            parts = value.split()
            if parts and parts[0].isdigit():
                fields[name] = int(parts[0])
    except OSError as error:
        raise MachineError(f"cannot read {meminfo}: {error}") from error
    if "MemAvailable" not in fields or "MemTotal" not in fields:
        raise MachineError(f"{meminfo} has no MemAvailable or MemTotal")
    return Snapshot(
        available_mb=fields["MemAvailable"] // 1024,
        total_mb=fields["MemTotal"] // 1024,
        load1=os.getloadavg()[0],
        cores=len(os.sched_getaffinity(0)),
    )


def workers(state: Snapshot, per_worker_mb: float | None, serial: bool = False) -> int:
    """Return how many test workers fit beside a 3 GB reserve, from 1 to cores - 1.

    Without a measured per-worker figure the run uses one worker, which is also what makes
    the first measurement clean.
    """
    if serial or not per_worker_mb or per_worker_mb <= 0:
        return 1
    fit = int((state.available_mb - RESERVE_MB) // per_worker_mb)
    return max(1, min(fit, state.cores - 1))
