"""Keep the knowledge base honest about the code (D026): drift at start, notes at the end."""

from __future__ import annotations

from pathlib import Path

from bedrock_lib import clock, jsonl, kb

from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict


def _repo(env: Env) -> Path | None:
    if env.project and (env.project.root / ".git").exists():
        return env.project.root
    return None


def on_start(event: Event, env: Env) -> Verdict | None:
    """Tell the session which notes went stale and how many problems the base has."""
    if env.project is None or not (env.cfg.memory_bank_dir / env.project.name).is_dir():
        return None
    lines = []
    if (repo := _repo(env)) is not None:
        stale = kb.drift(env.cfg.memory_bank_dir, env.project.name, repo)
        lines += stale[:5]
        if len(stale) > 5:
            lines.append(f"... and {len(stale) - 5} more stale notes (bedrock kb drift)")
    problems = kb.validate(env.cfg.memory_bank_dir, env.project.name)
    if problems:
        lines.append(f"The knowledge base has {len(problems)} problems: run `bedrock kb validate`.")
    return Verdict(context="Knowledge base:\n" + "\n".join(lines)) if lines else None


def _changed_this_session(env: Env, event: Event) -> dict[str, str]:
    """Project files edited in this session, with the time of their first edit."""
    path = env.cfg.state_dir / "changed" / f"{env.project_name}.jsonl"
    first: dict[str, str] = {}
    for record in jsonl.read(path):
        if record.get("session") == event.session:
            first.setdefault(record["path"], record["ts"])
    return first


def on_stop(event: Event, env: Env) -> Verdict | None:
    """Stop once when a module's code changed this session and its note was not touched."""
    if event.data.get("stop_hook_active") or env.project is None:
        return None
    changed = _changed_this_session(env, event)
    if not changed:
        return None
    untouched = []
    for note in kb.covering(env.cfg.memory_bank_dir, env.project.name, list(changed)):
        covered = [
            p for p in changed if any(p == c or p.startswith(c + "/") for c in kb.covers(note))
        ]
        earliest = min(clock.parse(changed[p]) for p in covered)
        if note.path is not None and note.path.stat().st_mtime < earliest.timestamp():
            untouched.append(f"{note.name} ({', '.join(covered[:3])})")
    if not untouched:
        return None
    return Verdict(
        block="Code changed under these module notes, which were not updated: "
        + "; ".join(untouched)
        + ". Update each note, or add one line 'verified, nothing to change, because ...' (D026)."
    )


RULES = [
    Rule("kb-start", frozenset({"SessionStart"}), HELPER, on_start),
    Rule("kb-stop", frozenset({"Stop"}), HELPER, on_stop),
]
