"""Numbers for the retro and the architecture review (D041, D061): calibration and hot spots."""

from __future__ import annotations

import re
import statistics
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import clock, daylog
from .config import UserConfig

RISK = re.compile(r"^(R[1-3])\b")
ESTIMATE = re.compile(r"\bestimate=(\d+)\b")


class InsightError(Exception):
    """The numbers cannot be computed."""


@dataclass(frozen=True)
class Hotspot:
    """A file that changes often and is large: a candidate for deepening or deletion."""

    path: str
    changes: int
    lines: int
    score: int


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )
    if done.returncode != 0:
        raise InsightError(f"git {args[0]} failed: {done.stderr.strip()}")
    return done.stdout


def hotspots(repo: Path, days: int = 90, top: int = 15) -> list[Hotspot]:
    """Files still in HEAD ranked by commits in the window times their line count."""
    log = _git(repo, "log", f"--since={days}.days", "--format=", "--name-only", "-z", "--", ".")
    root = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
    prefix = Path(repo).resolve().relative_to(root.resolve()).as_posix()
    prefix = "" if prefix == "." else prefix + "/"
    changes = Counter(name.strip("\n") for name in log.split("\0") if name.strip("\n"))
    tracked = set(_git(repo, "ls-files", "-z", "--full-name").split("\0"))
    spots = []
    for path, count in changes.items():
        if path not in tracked or not path.startswith(prefix):
            continue
        try:
            lines = (root / path).read_bytes().count(b"\n")
        except OSError:
            continue
        spots.append(Hotspot(path[len(prefix) :], count, lines, count * lines))
    return sorted(spots, key=lambda s: (-s.score, s.path))[:top]


def _blocks(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    blocks: dict[str, dict[str, Any]] = {}
    for record in records:
        if not record.get("block"):
            continue
        block = blocks.setdefault(record["block"], {"block": record["block"]})
        if record["event"] == "taken" and (risk := RISK.match(record.get("detail", ""))):
            block.setdefault("risk", risk.group(1))
        if record["event"] == "plan-approved" and (found := ESTIMATE.search(record["detail"])):
            block["estimate"] = int(found.group(1))
        if record["event"] == "closed":
            block["closed"] = record["ts"]
    return blocks


def retro(cfg: UserConfig, project: str, now: datetime, days: int = 7) -> dict[str, Any]:
    """Blocks closed in the window, the open ones, and the calibration per risk level.

    Calibration is the median of actual over estimated minutes (D041.3).
    """
    since = now - timedelta(days=days)
    blocks = _blocks(daylog.events(cfg, project))
    closed = []
    for block in blocks.values():
        if "closed" in block and clock.parse(block["closed"]) >= since:
            minutes = daylog.minutes(cfg, project, block["block"])
            closed.append({**block, "minutes": minutes})
    closed.sort(key=lambda b: b["closed"])
    ratios: dict[str, list[float]] = {}
    for block in closed:
        if block.get("estimate") and block.get("risk"):
            ratios.setdefault(block["risk"], []).append(block["minutes"] / block["estimate"])
    return {
        "closed": closed,
        "open": sorted(b["block"] for b in blocks.values() if "closed" not in b),
        "calibration": {risk: round(statistics.median(r), 2) for risk, r in sorted(ratios.items())},
    }
