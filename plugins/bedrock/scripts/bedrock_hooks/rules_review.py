"""The one refusal bedrock keeps: a pull request opens or merges only after a recorded review.

The record (`bedrock review pass --agent <id>`) names a reviewer agent that really ran and the
commit it reviewed; a new commit after the review voids it (D053).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from bedrock_lib.config import ConfigError, find_project

from bedrock_hooks import shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.dispatch import LOOKS_LIKE_PR

REPO_FLAGS = ("-R", "--repo")
BOOLEAN_FLAGS = {
    "--merge",
    "--squash",
    "--rebase",
    "--auto",
    "--admin",
    "--delete-branch",
    "-d",
    "-m",
    "-s",
    "-r",
    "--disable-auto",
}


def record_path(env: Env, cwd: Path, branch: str) -> Path:
    """Where `bedrock review` run in `cwd` keeps the record for a branch."""
    try:
        found = find_project(cwd)
    except (ConfigError, OSError):
        found = None
    project = found.name if found else env.project_name
    return env.cfg.state_dir / "reviews" / project / f"{branch.replace('/', '__')}.json"


def _value(args: list[str], *names: str) -> str:
    for index, arg in enumerate(args):
        if arg in names and index + 1 < len(args):
            return args[index + 1]
        for name in names:
            if name.startswith("--") and arg.startswith(name + "="):
                return arg.split("=", 1)[1]
    return ""


def _run(env: Env, cwd: Path, argv: list[str]) -> str | None:
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
            env=dict(env.environ),
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _target(env: Env, cwd: Path, sub: str, args: list[str]) -> tuple[str, str] | str:
    """The branch and head commit the call is about, or why they cannot be told."""
    if sub == "create":
        branch = _value(args, "--head", "-H").split(":")[-1]
        branch = branch or _run(env, cwd, ["git", "rev-parse", "--abbrev-ref", "HEAD"]) or ""
        sha = _run(env, cwd, ["git", "rev-parse", "--verify", "--end-of-options", branch])
        if not branch or not sha:
            return "bedrock cannot tell which branch and commit this pull request is for"
        return branch, sha
    positional = [a for i, a in enumerate(args) if not a.startswith("-") and _flag_value(args, i)]
    view = ["gh", "pr", "view", *positional[:1], "--json", "headRefName,headRefOid"]
    if repo := _value(args, *REPO_FLAGS):
        view += ["--repo", repo]
    shown = _run(env, cwd, view)
    try:
        data = json.loads(shown or "")
        return str(data["headRefName"]), str(data["headRefOid"])
    except (ValueError, KeyError, TypeError):
        return "bedrock could not read the pull request (gh pr view failed)"


def _flag_value(args: list[str], index: int) -> bool:
    """False when args[index] is the value of the flag before it."""
    if index == 0:
        return True
    previous = args[index - 1]
    return not (previous.startswith("-") and "=" not in previous and previous not in BOOLEAN_FLAGS)


def _review(env: Env, cwd: Path, branch: str, sha: str) -> str | None:
    """None when a passed review covers this commit, else why not."""
    try:
        record = json.loads(record_path(env, cwd, branch).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record = None
    if not isinstance(record, dict) or not record.get("passed"):
        return f"no passed review recorded for '{branch}'"
    if not record.get("agent") or not record.get("sha"):
        return f"the review of '{branch}' was recorded without a reviewer run; record it again"
    if record["sha"] != sha:
        return (
            f"'{branch}' has commits after its review ({record['sha'][:8]} reviewed, {sha[:8]} now)"
        )
    return None


def _moved(simple: shell.Simple, cwd: Path, env: Env) -> Path:
    """The folder after a `cd` or `pushd` earlier in the same command line."""
    if simple.program not in ("cd", "pushd"):
        return cwd
    targets = [a for a in simple.argv[1:] if not a.startswith("-")]
    home = Path(env.environ.get("HOME") or Path.home())
    target = Path(targets[0]).expanduser() if targets else home
    if targets and targets[0].startswith("~"):
        target = home / targets[0][2:] if targets[0] != "~" else home
    return target if target.is_absolute() else cwd / target


def check(event: Event, env: Env) -> Verdict | None:
    """Refuse `gh pr create` and `gh pr merge` without a review of the head commit."""
    command = str(event.tool_input.get("command", ""))
    if not LOOKS_LIKE_PR.search(command):
        return None
    try:
        simples = shell.commands(command)
    except shell.ParseError:
        return Verdict(deny="bedrock could not read this gh pr call; write it as a plain command.")
    cwd = event.cwd
    for simple in simples:
        cwd = _moved(simple, cwd, env)
        words = simple.argv[1:] if simple.program == "gh" else []
        if words[:1] != ["pr"] or len(words) < 2 or words[1] not in ("create", "merge"):
            continue
        target = _target(env, cwd, words[1], words[2:])
        if isinstance(target, str):
            return Verdict(deny=f"gh pr {words[1]} refused: {target}.")
        if problem := _review(env, cwd, *target):
            return Verdict(
                deny=f"gh pr {words[1]} refused: {problem}. Run a reviewer agent, then "
                "`bedrock review pass <branch> --agent <its id>` (D053)."
            )
    return None


RULES = [
    Rule("review-gate", frozenset({"PreToolUse"}), GUARD, check, lambda e: e.tool == "Bash"),
]
