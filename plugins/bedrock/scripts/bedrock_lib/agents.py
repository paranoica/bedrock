"""Agent runs read from the transcripts Claude Code writes, not from hooks.

Claude Code keeps every subagent at
`<claude>/projects/<folder>/<session>/subagents/agent-<id>.jsonl` with `agent-<id>.meta.json`.
Reading those files sees every run, including ones that crashed or were cut off, and does not
depend on what a hook is handed.
"""

from __future__ import annotations

import json
import os
import re
import statistics
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import clock

# Spend in units of one fresh input token of the run's own model.
WEIGHTS = {"input": 1.0, "cache_5m": 1.25, "cache_1h": 2.0, "cache_read": 0.1, "output": 5.0}
AGENT_ID = re.compile(r"^[0-9a-z]{6,64}$")
REVIEWER = re.compile(r"review", re.I)


@dataclass
class Run:
    """One subagent run."""

    agent_id: str
    session: str
    path: Path
    kind: str = "unknown"
    description: str = ""
    model: str = ""
    finished: bool | None = None
    cwd: str = ""
    started: datetime | None = None
    ended: datetime | None = None
    turns: int = 0
    tokens: dict[str, int] = field(default_factory=dict)
    weighted: float = 0.0
    broken_lines: int = 0

    @property
    def minutes(self) -> float:
        """Wall time from the first to the last record."""
        if self.started is None or self.ended is None:
            return 0.0
        return (self.ended - self.started).total_seconds() / 60


@dataclass
class Scan:
    """What a scan read, and what it could not."""

    runs: list[Run] = field(default_factory=list)
    files: int = 0
    unreadable: list[str] = field(default_factory=list)
    broken_lines: int = 0
    without_meta: int = 0


def claude_dir(environ: Mapping[str, str] | None = None) -> Path:
    """Claude Code's own folder: `CLAUDE_CONFIG_DIR`, else `.claude` in the home folder."""
    environ = environ if environ is not None else os.environ
    if configured := environ.get("CLAUDE_CONFIG_DIR"):
        return Path(configured).expanduser()
    home = environ.get("HOME")
    return (Path(home) if home else Path.home()) / ".claude"


def _number(value: object) -> int | None:
    """A token count, or None when the value is not a whole non-negative number."""
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _weigh(usage: dict[str, Any]) -> tuple[float, dict[str, int], bool]:
    """The weighted spend and token counts of one request, and whether a count was unreadable."""
    creation = usage.get("cache_creation")
    if isinstance(creation, dict) and creation:
        raw = {
            "cache_5m": creation.get("ephemeral_5m_input_tokens"),
            "cache_1h": creation.get("ephemeral_1h_input_tokens"),
        }
    else:
        raw = {"cache_5m": usage.get("cache_creation_input_tokens"), "cache_1h": None}
    raw |= {
        "input": usage.get("input_tokens"),
        "cache_read": usage.get("cache_read_input_tokens"),
        "output": usage.get("output_tokens"),
    }
    numbers = {name: _number(value) for name, value in raw.items()}
    counts = {name: number or 0 for name, number in numbers.items()}
    odd = any(number is None for number in numbers.values())
    return sum(counts[k] * WEIGHTS[k] for k in counts), counts, odd


def _meta(run: Run) -> bool:
    path = run.path.with_name(run.path.name.removesuffix(".jsonl") + ".meta.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    run.kind = str(data.get("agentType") or run.kind)
    run.description = str(data.get("description") or "")
    run.model = str(data.get("model") or "")
    if isinstance(data.get("finished"), bool):
        run.finished = data["finished"]
    return True


def _records(path: Path, run: Run) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                record = None
            if isinstance(record, dict):
                yield record
            else:
                run.broken_lines += 1


def _note_time(run: Run, stamp: object) -> None:
    if not isinstance(stamp, str):
        return
    try:
        moment = clock.parse(stamp)
    except ValueError:
        return
    run.started = min(run.started, moment) if run.started else moment
    run.ended = max(run.ended, moment) if run.ended else moment


def read_run(path: Path, session: str) -> Run:
    """Read one subagent transcript; one request counts once, however many lines repeat it."""
    agent_id = path.name.removeprefix("agent-").removesuffix(".jsonl")
    run = Run(agent_id=agent_id, session=session, path=path)
    usages: dict[str, dict[str, Any]] = {}
    models: dict[str, str] = {}
    for record in _records(path, run):
        _note_time(run, record.get("timestamp"))
        run.cwd = run.cwd or str(record.get("cwd") or "")
        message = record.get("message")
        if record.get("type") != "assistant" or not isinstance(message, dict):
            continue
        usage = message.get("usage")
        model = str(message.get("model") or "")
        if not isinstance(usage, dict) or model == "<synthetic>":
            continue
        key = str(message.get("id") or f"line{len(usages)}")
        usages[key] = usage
        models[key] = model
    totals: dict[str, int] = {}
    for usage in usages.values():
        weight, counts, odd = _weigh(usage)
        run.broken_lines += 1 if odd else 0
        run.weighted += weight
        for name, count in counts.items():
            totals[name] = totals.get(name, 0) + count
    run.tokens = totals
    run.turns = len(usages)
    if models:
        counted = list(models.values())
        run.model = max(set(counted), key=counted.count)
    return run


def transcripts(root: Path) -> Iterator[tuple[Path, str]]:
    """Every subagent transcript under `<root>/projects`, with its session id."""
    for path in sorted((root / "projects").glob("*/*/subagents/agent-*.jsonl")):
        yield path, path.parent.parent.name


def scan(root: Path, since: datetime | None = None) -> Scan:
    """Read every subagent run; count what could not be read instead of hiding it."""
    result = Scan()
    for path, session in transcripts(root):
        result.files += 1
        try:
            run = read_run(path, session)
        except OSError as error:
            result.unreadable.append(f"{path}: {error}")
            continue
        if not _meta(run):
            result.without_meta += 1
        result.broken_lines += run.broken_lines
        if since is not None and (run.started is None or run.started < since):
            continue
        result.runs.append(run)
    return result


def find(root: Path, session: str, agent_id: str) -> Run | None:
    """The run of one agent in one session, or None."""
    if not AGENT_ID.match(agent_id) or not re.match(r"^[0-9A-Za-z-]{1,80}$", session):
        return None
    for path in sorted((root / "projects").glob(f"*/{session}/subagents/agent-{agent_id}.jsonl")):
        run = read_run(path, session)
        _meta(run)
        return run
    return None


def _key(run: Run, by: str, project: Callable[[Run], str]) -> str:
    if by == "model":
        return run.model or "unknown"
    if by == "day":
        return run.started.strftime("%Y-%m-%d") if run.started else "unknown"
    if by == "project":
        return project(run)
    return run.kind


def report(result: Scan, by: str, project: Callable[[Run], str]) -> str:
    """A table of runs grouped by role, model, day or project, the costliest first."""
    groups: dict[str, list[Run]] = {}
    for run in result.runs:
        groups.setdefault(_key(run, by, project), []).append(run)
    total = sum(run.weighted for run in result.runs) or 1.0
    rows = [f"{by:<32} {'runs':>5} {'turns':>6} {'output':>9} {'spend':>9} {'share':>6} {'min':>6}"]
    ordered = sorted(groups.items(), key=lambda item: -sum(r.weighted for r in item[1]))
    for key, runs in ordered:
        spend = sum(r.weighted for r in runs)
        output = sum(r.tokens.get("output", 0) for r in runs)
        rows.append(
            f"{key[:32]:<32} {len(runs):>5} {sum(r.turns for r in runs):>6} "
            f"{output / 1e3:>8.0f}k {spend / 1e6:>8.1f}M {100 * spend / total:>5.1f}% "
            f"{statistics.median(r.minutes for r in runs):>6.1f}"
        )
    return "\n".join(rows)


def coverage(result: Scan) -> str:
    """What was read and what was not, so a format change shows up instead of silent zeros."""
    parts = [f"read {result.files} agent transcripts, {len(result.runs)} runs in range"]
    if result.without_meta:
        parts.append(f"{result.without_meta} without a meta file (role unknown)")
    if result.broken_lines:
        parts.append(f"{result.broken_lines} unreadable lines or token counts skipped")
    if result.unreadable:
        parts.append(f"{len(result.unreadable)} files unreadable: {result.unreadable[0]}")
    return "; ".join(parts) + ". Spend is in fresh-input-token units of each run's model."


def is_reviewer(run: Run) -> bool:
    """A reviewer by its agent type (bedrock:reviewer, bedrock:security-reviewer, ...)."""
    return bool(REVIEWER.search(run.kind))
