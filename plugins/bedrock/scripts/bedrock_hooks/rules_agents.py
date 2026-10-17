"""Agents under rules instead of questions (D004 to D009).

Who may start, with what brief, how many at once, which files they may touch, and what a
finished agent leaves behind (D007, D008).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any

from bedrock_lib import clock, ledger, machine, session, spend

from bedrock_hooks import paths, shell
from bedrock_hooks.core import GUARD, HELPER, Env, Event, Rule, Verdict

PLUGIN = Path(__file__).resolve().parents[2]
AGENT_TOOLS = {"Agent", "Task"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
WRITERS = {"implementer", "general-purpose", "fork", "claude"}
REVIEW_WORDS = ("review", "verif", "critic")
DEFAULT_BUDGET = 3
FORK_CONTEXT_LIMIT = 150_000
PENDING_LIMIT = timedelta(minutes=10)
ACTIVE_LIMIT = timedelta(hours=3)
LINE = re.compile(
    r"^(reason|files|report|estimate|fork|task|done when|cause)\s*:\s*(.+)$", re.I | re.M
)
IMPLEMENTERS = {"implementer", "implementer-untested"}
REASON = re.compile(r"^(a|b|c|fork)\b", re.I)
FINISHED = {"completed", "failed", "killed", "done", "stopped", "cancelled"}
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def brief(prompt: str) -> dict[str, str]:
    """Read the brief's labelled lines: Reason, Files, Report, Estimate, Fork."""
    return {match.group(1).lower(): match.group(2).strip() for match in LINE.finditer(prompt)}


def _estimate(text: str) -> float:
    match = re.fullmatch(r"\s*([\d.]+)\s*([kKmM]?)\b.*", text or "")
    if not match:
        return 0.0
    scale = {"k": 1e3, "m": 1e6}.get(match.group(2).lower(), 1.0)
    return float(match.group(1)) * scale


def _agents(env: Env, event: Event) -> dict[str, Any]:
    if not event.session:
        return {}
    return session.load(env.cfg, event.session).get("agents", {})


def _edit_agents(env: Env, event: Event, edit: Any) -> None:
    def change(data: dict[str, Any]) -> dict[str, Any]:
        agents = data.get("agents", {"pending": [], "active": {}, "started": []})
        edit(agents)
        return {**data, "agents": agents}

    if event.session:
        session.change(env.cfg, event.session, change)


def _is_writer(kind: str) -> bool:
    return kind in WRITERS


def _is_review(kind: str) -> bool:
    return any(word in kind.lower() for word in REVIEW_WORDS)


def _knob(env: Env, kind: str) -> str | None:
    mode = env.project.data.get("agents", "full") if env.project else "full"
    if mode == "off":
        return "agents are off for this project; do the work in the session (D009)."
    if mode == "read-only" and _is_writer(kind):
        return "this project allows only reading agents; the session writes the code (D009)."
    return None


def _brakes(env: Env, kind: str) -> str | None:
    five, week = spend.used(env.cfg, "five_hour"), spend.used(env.cfg, "seven_day")
    if five >= 95 or week >= 90:
        return f"no agents: the subscription limit is near (5h {five:.0f}%, week {week:.0f}%)."
    mode = spend.current(env.cfg, env.now)
    if five >= 80 and mode != "max" and not _is_review(kind):
        if mode is None:
            return (
                "the 5-hour window is past 80%: ask the owner, spend or save, before more agents."
            )
        return "save mode: above 80% of the 5-hour window only review agents run (D005)."
    return None


def _last_context(transcript: str) -> int:
    path = Path(transcript)
    if not transcript or not path.is_file():
        return 0
    last = 0
    for line in path.read_text("utf-8", errors="replace").splitlines():
        try:
            usage = (json.loads(line).get("message") or {}).get("usage") or {}
        except json.JSONDecodeError:
            continue
        keys = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        if usage:
            last = sum(int(usage.get(key) or 0) for key in keys)
    return last


def _fork(event: Event, agents: dict[str, Any], fields: dict[str, str]) -> str | None:
    if "fork" not in fields:
        return "a fork needs a 'Fork: <reason under F1>, context <N>k' line said to the owner (F3)."
    context = _last_context(str(event.data.get("transcript_path") or ""))
    if context > FORK_CONTEXT_LIMIT:
        return f"no fork above 150k of context (now {context // 1000}k): brief a fresh agent (F2)."
    forks = [a for a in agents.get("active", {}).values() if a.get("type") == "fork"]
    allowed = 3 if "alternative" in fields["fork"].lower() else 1
    if len(forks) >= allowed:
        return "one fork at a time, up to three only for alternatives (F5)."
    return None


def _window_start(env: Env) -> float:
    reset = (spend.limits(env.cfg).get("five_hour") or {}).get("resets_at")
    if isinstance(reset, int | float):
        return float(reset) - 5 * 3600
    return (env.now - timedelta(hours=5)).timestamp()


def _budget(env: Env, event: Event, agents: dict[str, Any]) -> str | None:
    budget = session.load(env.cfg, event.session).get("agent_budget", DEFAULT_BUDGET)
    since = _window_start(env)
    started = [s for s in agents.get("started", []) if clock.parse(s).timestamp() >= since]
    if len(started) >= int(budget):
        return (
            f"agent budget for this window is used ({len(started)}/{budget}); work in the session."
        )
    return None


def _live(env: Env, agents: dict[str, Any]) -> list[dict[str, Any]]:
    """Agents that still count: pending ones that started lately, active ones not long gone."""

    def recent(record: dict[str, Any], limit: timedelta) -> bool:
        at = record.get("at")
        return at is None or env.now - clock.parse(at) < limit

    pending = [p for p in agents.get("pending", []) if recent(p, PENDING_LIMIT)]
    active = [a for a in agents.get("active", {}).values() if recent(a, ACTIVE_LIMIT)]
    return active + pending


def _concurrency(env: Env, kind: str, tool_input: dict, agents: dict[str, Any]) -> str | None:
    active = _live(env, agents)
    if not _is_writer(kind):
        readers = [a for a in active if not _is_writer(a.get("type", ""))]
        limit = 1 if spend.used(env.cfg, "five_hour") > 50 else 3
        return f"{limit} reading agents at once at most (D006)." if len(readers) >= limit else None
    writers = [a for a in active if _is_writer(a.get("type", ""))]
    if tool_input.get("isolation") == "worktree":
        isolated = [a for a in writers if a.get("isolation") == "worktree"]
        if len(isolated) >= 2 or machine.snapshot().available_mb <= 4096:
            return "at most two worktree writers, and only with more than 4 GB free (D006)."
        return None
    shared = [a for a in writers if a.get("isolation") != "worktree"]
    return "one writer at a time in the shared checkout (D006)." if shared else None


def _missing_fields(kind: str, fields: dict[str, str]) -> str | None:
    needed = ["task", "done when", "report"]
    if kind in IMPLEMENTERS:
        needed += ["cause", "files"]
    missing = [name for name in needed if not fields.get(name)]
    if not missing:
        return None
    labels = ", ".join(f"'{name.capitalize()}:'" for name in missing)
    return f"the brief lacks {labels} (D038); templates are in the plugin's templates/briefs."


def check_spawn(event: Event, env: Env) -> Verdict | None:
    """Refuse an agent the rules do not allow; remember the brief of one they do."""
    tool_input = event.tool_input
    kind = str(tool_input.get("subagent_type") or "general-purpose")
    fields = brief(str(tool_input.get("prompt") or ""))
    agents = _agents(env, event)
    problem = _knob(env, kind)
    if problem is None and not REASON.match(fields.get("reason", "")):
        problem = "the brief needs 'Reason: a|b|c|fork — why' (D004)."
    problem = problem or _missing_fields(kind, fields)
    problem = problem or _brakes(env, kind)
    if problem is None and kind == "fork":
        problem = _fork(event, agents, fields)
    problem = problem or _budget(env, event, agents) or _concurrency(env, kind, tool_input, agents)
    if problem:
        return Verdict(deny=f"agent refused: {problem}")
    record = {
        "type": kind,
        "reason": REASON.match(fields["reason"]).group(1).lower(),
        "files": [f.strip() for f in fields.get("files", "").split(",") if f.strip()],
        "report": fields.get("report", ""),
        "estimate": _estimate(fields.get("estimate", "")),
        "model": str(tool_input.get("model") or ""),
        "isolation": str(tool_input.get("isolation") or ""),
        "cwd": str(event.cwd),
        "at": clock.iso(env.now),
    }

    def add(agents: dict[str, Any]) -> None:
        agents.setdefault("pending", []).append(record)
        agents.setdefault("started", []).append(clock.iso(env.now))

    _edit_agents(env, event, add)
    return None


def _definition(kind: str) -> dict[str, str]:
    path = PLUGIN / "agents" / f"{kind}.md"
    if not path.is_file():
        return {}
    text = path.read_text("utf-8")
    head = text.split("---", 2)[1] if text.startswith("---") else ""
    return dict(re.findall(r"^(\w+):\s*(.+?)\s*$", head, re.M))


def route(event: Event, env: Env) -> Verdict | None:
    """In max or save mode, shift an agent's effort one step from its definition (D009)."""
    mode = spend.current(env.cfg, env.now)
    tool_input = event.tool_input
    if mode not in ("max", "save") or tool_input.get("effort"):
        return None
    base = _definition(str(tool_input.get("subagent_type") or "")).get("effort")
    if base not in EFFORTS:
        return None
    step = 1 if mode == "max" else -1
    shifted = EFFORTS[max(0, min(len(EFFORTS) - 2, EFFORTS.index(base) + step))]
    return Verdict(updated_input={**tool_input, "effort": shifted}) if shifted != base else None


def bind(event: Event, env: Env) -> Verdict | None:
    """Tie the oldest waiting brief of this agent type to the agent that just started."""
    agent, kind = event.agent_id, str(event.data.get("agent_type") or "")

    def take(agents: dict[str, Any]) -> None:
        pending = agents.setdefault("pending", [])
        index = next((i for i, p in enumerate(pending) if p.get("type") == kind), None)
        if index is None and pending:
            index = 0
        if index is not None and agent:
            agents.setdefault("active", {})[agent] = pending.pop(index)

    _edit_agents(env, event, take)
    return None


def _normal(base: Path, path: str) -> Path:
    candidate = Path(path)
    return Path(os.path.normpath(candidate if candidate.is_absolute() else base / candidate))


def check_edit(event: Event, env: Env) -> Verdict | None:
    """An agent edits only the files its brief lists, plus its report."""
    record = _agents(env, event).get("active", {}).get(event.agent_id or "")
    path = str(event.tool_input.get("file_path") or event.tool_input.get("notebook_path") or "")
    if record is None:
        return Verdict(deny="edit refused: this agent has no brief with a 'Files:' list (D007).")
    base = Path(record.get("cwd") or event.cwd)
    allowed = {_normal(base, f) for f in record.get("files", [])}
    if record.get("report"):
        allowed.add(_normal(base, record["report"]))
    if _normal(event.cwd, path) not in allowed:
        return Verdict(deny=f"edit refused: {path} is not in its brief's Files list (D007).")
    return None


def _temp_dirs(env: Env) -> list[Path]:
    return [
        Path(os.path.realpath(p))
        for p in {"/tmp", tempfile.gettempdir(), env.environ.get("TMPDIR", "/tmp")}
    ]


def check_shell_writes(event: Event, env: Env) -> Verdict | None:
    """An agent's shell writes stay inside its brief's files, its report, or a temp folder."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    found, hidden = paths.all_writes(simples, event.cwd, env)
    targets = [target for target in found if str(target) != "/dev/null"]
    if hidden:
        return Verdict(deny=f"write refused: the target {hidden[0]!r} comes from a variable.")
    if not targets:
        return None
    record = _agents(env, event).get("active", {}).get(event.agent_id or "")
    if record is None:
        return Verdict(deny="write refused: this agent has no brief with a 'Files:' list (D007).")
    base = Path(record.get("cwd") or event.cwd)
    allowed = {paths.expand(env, f, base) for f in record.get("files", [])}
    if record.get("report"):
        allowed.add(paths.expand(env, record["report"], base))
    temp = _temp_dirs(env)
    project = [base, event.cwd, *([env.project.root] if env.project else [])]
    for target in targets:
        scratch = any(paths.under(target, folder) for folder in temp) and not any(
            paths.under(target, root) for root in project
        )
        if target not in allowed and not scratch:
            return Verdict(deny=f"write refused: {target} is not in its brief's Files list (D007).")
    return None


def _running(tasks: Any) -> list[str]:
    if not isinstance(tasks, list):
        return []
    running = []
    for task in tasks:
        if isinstance(task, dict) and str(task.get("status", "running")).lower() not in FINISHED:
            running.append(str(task.get("command") or task.get("description") or task.get("id")))
    return running


def finish(event: Event, env: Env) -> Verdict | None:
    """Keep an agent from finishing with commands running or no report; then log it."""
    record = _agents(env, event).get("active", {}).get(event.agent_id or "", {})
    if running := _running(event.data.get("background_tasks")):
        return Verdict(block="wait for your background commands to finish: " + "; ".join(running))
    report = record.get("report")
    base = Path(record.get("cwd") or event.cwd)
    if report and not _normal(base, report).exists() and not event.data.get("stop_hook_active"):
        return Verdict(block=f"write your report to {report} before finishing (D007).")
    _log(env, event, record)
    return None


def _log(env: Env, event: Event, record: dict[str, Any]) -> None:
    kind = str(event.data.get("agent_type") or record.get("type") or "unknown")
    transcript = Path(str(event.data.get("agent_transcript_path") or ""))
    spent = ledger.transcript_spend(transcript) if transcript.is_file() else None
    definition = _definition(kind)
    turns = spent.turns if spent else 0
    cap = int(definition["maxTurns"]) if definition.get("maxTurns", "").isdigit() else None
    entry = {
        "project": env.project_name,
        "role": kind,
        "model": record.get("model") or definition.get("model") or "inherit",
        "reason": record.get("reason") or "c",
        "estimate": float(record.get("estimate") or 0.0),
        "actual": spent.weighted if spent else 0.0,
        "turns": turns,
        "cap_hit": cap is not None and turns >= cap,
        "accepted": None,
    }
    ledger.add(env.cfg, entry, now=env.now)

    def drop(agents: dict[str, Any]) -> None:
        agents.setdefault("active", {}).pop(event.agent_id or "", None)

    _edit_agents(env, event, drop)


RULES = [
    Rule(
        "agent-spawn",
        frozenset({"PreToolUse"}),
        GUARD,
        check_spawn,
        lambda e: e.tool in AGENT_TOOLS,
    ),
    Rule("agent-route", frozenset({"PreToolUse"}), HELPER, route, lambda e: e.tool in AGENT_TOOLS),
    Rule("agent-bind", frozenset({"SubagentStart"}), HELPER, bind),
    Rule(
        "agent-files",
        frozenset({"PreToolUse"}),
        GUARD,
        check_edit,
        lambda e: e.tool in EDIT_TOOLS and e.agent_id is not None,
    ),
    Rule(
        "agent-shell-files",
        frozenset({"PreToolUse"}),
        GUARD,
        check_shell_writes,
        lambda e: e.tool == "Bash" and e.agent_id is not None,
    ),
    Rule("agent-finish", frozenset({"SubagentStop"}), HELPER, finish),
]
