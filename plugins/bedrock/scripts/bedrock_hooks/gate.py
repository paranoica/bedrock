"""Turn the actions a tool call would take into a verdict: allowed by a grant, or refused."""

from __future__ import annotations

import fcntl
import json
import re
from dataclasses import dataclass

from bedrock_hooks import grants
from bedrock_hooks.core import Env, Event, Verdict

SAFE_SESSION = re.compile(r"[A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Action:
    """An effect of a command: its kind, its target, whether it is irreversible (level 4)."""

    kind: str
    why: str
    target: str | None = None
    level4: bool = False


def _remember_refusal(env: Env, event: Event, effect: str) -> int:
    """Count refusals of one effect in this session; the count drives the wording."""
    session = event.session if SAFE_SESSION.fullmatch(event.session or "") else "unknown"
    folder = env.cfg.state_dir / "refusals"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{session}.json"
    with (folder / f"{session}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            counts = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            counts = {}
        counts[effect] = counts.get(effect, 0) + 1
        path.write_text(json.dumps(counts), encoding="utf-8")
    return counts[effect]


def refuse(env: Env, event: Event, effect: str, message: str) -> Verdict:
    """Refuse, and say plainly when the same effect was already refused in this session."""
    count = _remember_refusal(env, event, effect)
    if count > 1:
        message = (
            f"refused again ({count} attempts at the same effect): {message} "
            "A refused effect is not retried another way; stop and report to the owner."
        )
    return Verdict(deny=message)


def _instruction(action: Action) -> str:
    target = f" {action.target}" if action.target else ""
    if action.level4:
        return (
            f"{action.why} is irreversible and never covered by a grant. Only the owner's "
            f"override key allows it once: «разрешаю: {action.kind}{target}»."
        )
    return (
        f"{action.why} needs the owner's word. Ask the owner; a grant comes only from their "
        f"own message (for example «запушь», or /bedrock:allow {action.kind}{target})."
    )


def decide(env: Env, event: Event, actions: list[Action]) -> Verdict | None:
    """Allow when every action has a grant (then use them); otherwise refuse the first gap."""
    project = env.project_name
    for action in actions:
        if grants.available(env.cfg, action.kind, project, action.target, env.now) is None:
            effect = f"{action.kind}:{action.target or ''}"
            return refuse(env, event, effect, _instruction(action))
    for action in actions:
        grants.consume(env.cfg, action.kind, project, action.target, env.now)
    return None
