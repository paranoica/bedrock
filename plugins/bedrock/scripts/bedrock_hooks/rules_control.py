"""Bedrock guards its own controls, and refuses commands it cannot see through.

The model must not write grants, reviews, spend mode, limits or bedrock's settings (that would
let it grant itself anything), nor run a program named by a variable or a shell fed on stdin.
"""

from __future__ import annotations

from pathlib import Path

from bedrock_hooks import gate, paths, shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.gate import Action

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
OWN = "bedrock's own state and settings are written only by bedrock and the owner"


def _never(env: Env) -> list[Path]:
    config = env.environ.get("BEDROCK_CONFIG")
    config_dir = Path(config).parent if config else paths.home(env) / ".config" / "bedrock"
    return [env.cfg.state_dir, config_dir]


def _granted(env: Env, event: Event) -> dict[Path, Action]:
    roots = {event.cwd, *([env.project.root] if env.project else [])}
    found = {}
    for root in roots:
        claude = root / ".claude"
        found[claude / "bedrock.json"] = Action(
            "bedrock-config", "changing the project's bedrock settings"
        )
        for name in ("settings.json", "settings.local.json"):
            found[claude / name] = Action(
                "claude-config", "changing the project's Claude Code settings"
            )
    return found


def _git_internals(path: Path) -> bool:
    parts = path.parts
    if ".git" not in parts:
        return False
    after = parts[parts.index(".git") + 1 :]
    return bool(after) and after[0] in ("config", "hooks", "config.worktree", "info")


def _judge(env: Env, event: Event, targets: list[Path]) -> Verdict | None:
    for target in targets:
        if any(paths.touches(target, folder) for folder in _never(env)):
            return Verdict(deny=f"write to {target} refused: {OWN}.")
        if _git_internals(target):
            return Verdict(
                deny=f"write to {target} refused: git config and hooks change only through "
                "git commands bedrock can judge."
            )
    granted = _granted(env, event)
    actions = []
    for target in targets:
        for path, action in granted.items():
            if paths.touches(target, path):
                actions.append(action)
    return gate.decide(env, event, actions) if actions else None


def check_bash(event: Event, env: Env) -> Verdict | None:
    """Refuse opaque commands and writes to bedrock's controls."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    for simple in simples:
        if simple.opaque:
            return Verdict(
                deny=f"refused: the program '{simple.argv[0]}' comes from a variable, so bedrock "
                "cannot judge it; write the command plainly."
            )
        if shell.reads_stdin_as_commands(simple):
            return Verdict(
                deny="refused: piping commands into a shell hides them; run them directly."
            )
    targets, hidden = paths.all_writes(simples, event.cwd, env)
    if hidden:
        return Verdict(
            deny=f"refused: the write target {hidden[0]!r} comes from a variable, so bedrock "
            "cannot see where it goes; name the path plainly."
        )
    return _judge(env, event, targets)


def check_edit(event: Event, env: Env) -> Verdict | None:
    """File tools may not write bedrock's controls either."""
    raw = event.tool_input.get("file_path") or event.tool_input.get("notebook_path")
    if not raw:
        return None
    return _judge(env, event, [paths.expand(env, str(raw), event.cwd)])


RULES = [
    Rule(
        "bedrock-controls", frozenset({"PreToolUse"}), GUARD, check_bash, lambda e: e.tool == "Bash"
    ),
    Rule(
        "bedrock-controls-edit",
        frozenset({"PreToolUse"}),
        GUARD,
        check_edit,
        lambda e: e.tool in EDIT_TOOLS,
    ),
]
