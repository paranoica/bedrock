"""The session's edges: start, compaction and the end of a turn.

Auto-continue (D014, D046), the session registry and restored state (D042, D056), uncommitted
knowledge-base changes and failing helpers made visible (D023, D054). Nothing here refuses,
pops up on the desktop, or holds the session back except an auto-continue the owner switched on.
"""

from __future__ import annotations

import json
import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

from bedrock_lib import clock, jsonl, kb, session, spend

from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict

ATTEMPTS_PER_TASK = 2
STEP_CEILING = 40
REGISTRY_TTL = timedelta(hours=12)
# Skills do not switch themselves on in the middle of a conversation, so the session is told once.
ROUTE = (
    "bedrock: take a new task through the bedrock:day skill; record each decision and failure "
    "with bedrock:kb. For an agent, take the bedrock role that fits: bedrock:inventory to read "
    "many files, bedrock:researcher for the web, bedrock:implementer for code with a ready test, "
    "bedrock:reviewer for a review. general-purpose runs on the session's own model: keep it "
    "for work no role fits."
)


def _auto_continue(env: Env, event: Event) -> str | None:
    state = session.load(env.cfg, event.session)
    auto = state.get("autocontinue") or {}
    task = auto.get("next") or {}
    if not task.get("id") or not task.get("safe") or task.get("needs_owner"):
        return None
    if auto.get("until") and clock.parse(auto["until"]) <= env.now:
        return None
    if spend.used(env.cfg, "five_hour") >= 95:
        return None
    attempts = dict(auto.get("attempts") or {})
    steps = int(auto.get("steps") or 0)
    if attempts.get(task["id"], 0) >= ATTEMPTS_PER_TASK or steps >= STEP_CEILING:
        return None
    attempts[task["id"]] = attempts.get(task["id"], 0) + 1
    session.update(
        env.cfg, event.session, {"autocontinue": {**auto, "attempts": attempts, "steps": steps + 1}}
    )
    return (
        f"Continue with the next approved task: {task['id']} {task.get('title', '')}. Stop only "
        "when the plan is done, a decision is the owner's, an outward action is next, or you "
        "are blocked (D014)."
    )


def _knowledge_base(env: Env) -> str | None:
    if env.project is None:
        return None
    root = env.cfg.memory_bank_dir
    folder = root / env.project.name
    if not (root / ".git").exists() or not folder.is_dir():
        return None
    done = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--", env.project.name],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env=dict(env.environ),
    )
    if done.returncode != 0 or not done.stdout.strip():
        return None
    return (
        f"The knowledge base has uncommitted changes in {env.project.name}: commit them "
        f"(git -C {root} add {env.project.name} && git -C {root} commit) (D023)."
    )


def on_stop(event: Event, env: Env) -> Verdict | None:
    """Continue an approved plan the owner switched auto-continue on for."""
    if reason := _auto_continue(env, event):
        return Verdict(block=reason)
    return None


def _snapshot_path(env: Env, event: Event) -> Path:
    day = clock.work_date(env.now, env.cfg.display_tz, env.cfg.rollover_hour).isoformat()
    return env.cfg.days_dir / env.project_name / day / f"precompact-{event.session}.json"


def _git_state(env: Env, cwd: Path) -> dict[str, str]:
    def run(*args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            env=dict(env.environ),
        )
        return done.stdout.strip() if done.returncode == 0 else ""

    return {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "status": run("status", "--short")[:2000],
    }


def on_precompact(event: Event, env: Env) -> Verdict | None:
    """Save the session state before compaction, to be handed back afterwards."""
    if not event.session:
        return None
    snapshot = {
        "ts": clock.iso(env.now),
        "trigger": event.data.get("trigger", ""),
        "state": session.load(env.cfg, event.session),
        "git": _git_state(env, event.cwd),
    }
    path = _snapshot_path(env, event)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return None


def _restored(env: Env, event: Event) -> str:
    candidates = sorted(
        (env.cfg.days_dir / env.project_name).glob(f"*/precompact-{event.session}.json")
    )
    if not candidates:
        return ""
    snapshot = json.loads(candidates[-1].read_text(encoding="utf-8"))
    state = snapshot.get("state") or {}
    fields = ", ".join(
        f"{k}: {v}" for k, v in state.items() if k in ("task", "plan", "block", "state")
    )
    git = snapshot.get("git") or {}
    return (
        f"State before compaction ({snapshot.get('ts')}): {fields or 'no task recorded'}; "
        f"branch {git.get('branch') or '?'}; changed files:\n{git.get('status') or 'none'}"
    )


def _registry(env: Env, event: Event) -> list[str]:
    path = env.cfg.state_dir / "sessions" / "registry.json"
    try:
        registry: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        registry = {}
    live = {
        sid: info
        for sid, info in registry.items()
        if env.now - clock.parse(info.get("last_seen", "1970-01-01T00:00:00Z")) < REGISTRY_TTL
    }
    others = [
        f"session {sid} works in {info.get('cwd')} since {info.get('started')}"
        for sid, info in live.items()
        if sid != event.session and info.get("project") == env.project_name
    ]
    previous = live.get(event.session, {})
    live[event.session] = {
        "project": env.project_name,
        "cwd": str(event.cwd),
        "started": previous.get("started", clock.iso(env.now)),
        "last_seen": clock.iso(env.now),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{event.session}.tmp")
    temporary.write_text(json.dumps(live), encoding="utf-8")
    temporary.replace(path)
    return others


def _failing_helpers(env: Env) -> str:
    path = env.cfg.state_dir / "hook-errors.jsonl"
    try:
        records = jsonl.read(path)
    except jsonl.JsonlError:
        return "bedrock hook error log is unreadable"
    recent = [
        r
        for r in records
        if env.now - clock.parse(r.get("ts", "1970-01-01T00:00:00Z")) < timedelta(days=1)
    ]
    if not recent:
        return ""
    names = sorted({r.get("rule", "?") for r in recent})
    listed = ", ".join(names)
    return f"bedrock hooks failed {len(recent)} times in the last day ({listed}); see {path}."


def on_start(event: Event, env: Env) -> Verdict | None:
    """Hand the session what it should know: summary, parallel sessions, restored state, errors."""
    parts = []
    if env.project:
        summary = env.cfg.memory_bank_dir / env.project.name / "summary.md"
        if summary.is_file():
            body = kb.parse("summary", summary.read_text(encoding="utf-8")).body.strip()
            if body and not body.startswith("{"):
                parts.append("Project summary:\n" + "\n".join(body.splitlines()[:10]))
        parts.append(ROUTE)
        parts.append(_knowledge_base(env) or "")
    if event.session:
        parts += _registry(env, event)
        if event.data.get("source") in ("compact", "resume"):
            parts.append(_restored(env, event))
    parts.append(_failing_helpers(env))
    text = "\n".join(part for part in parts if part)
    return Verdict(context=text) if text else None


RULES = [
    Rule("stop", frozenset({"Stop"}), HELPER, on_stop),
    Rule("precompact", frozenset({"PreCompact"}), HELPER, on_precompact),
    Rule("session-start", frozenset({"SessionStart"}), HELPER, on_start),
]
