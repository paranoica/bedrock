"""Keep the knowledge base honest about the code (D026): stale notes are reported at the start."""

from __future__ import annotations

from pathlib import Path

from bedrock_lib import kb, kbdrift

from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict


def _repo(env: Env) -> Path | None:
    if env.project and (env.project.root / ".git").exists():
        return env.project.root
    return None


def _roots(env: Env) -> list[str]:
    """The folders holding modules, from the project's `kb.roots` setting."""
    assert env.project is not None
    section = env.project.data.get("kb")
    roots = section.get("roots") if isinstance(section, dict) else None
    return [r for r in roots if isinstance(r, str)] if isinstance(roots, list) else []


def on_start(event: Event, env: Env) -> Verdict | None:
    """Tell the session which notes went stale and how many problems the base has."""
    if env.project is None or not (env.cfg.memory_bank_dir / env.project.name).is_dir():
        return None
    bank, name = env.cfg.memory_bank_dir, env.project.name
    lines = []
    if (repo := _repo(env)) is not None:
        stale = kbdrift.drift(bank, name, repo)
        lines += stale[:5]
        if len(stale) > 5:
            lines.append(f"... and {len(stale) - 5} more stale notes (bedrock kb drift)")
        if bare := kb.uncovered(bank, name, repo, _roots(env)):
            lines.append(f"Modules without a note: {', '.join(bare[:10])} (bedrock kb uncovered).")
    problems = kb.validate(bank, name)
    if problems:
        lines.append(f"The knowledge base has {len(problems)} problems: run `bedrock kb validate`.")
    return Verdict(context="Knowledge base:\n" + "\n".join(lines)) if lines else None


RULES = [
    Rule("kb-start", frozenset({"SessionStart"}), HELPER, on_start),
]
