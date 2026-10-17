"""GitHub CLI calls: which write outward, and the gates on pull requests (D053 E2, E3)."""

from __future__ import annotations

import json
import subprocess

from bedrock_hooks.core import Env, Event, Verdict
from bedrock_hooks.gate import Action

GH_WRITES = {
    "pr": {"close", "reopen", "comment", "edit", "review", "ready"},
    "issue": {"create", "close", "reopen", "comment", "edit", "transfer", "pin", "lock"},
    "release": {"create", "edit", "upload"},
    "workflow": {"run", "enable", "disable"},
    "run": {"rerun", "cancel"},
    "secret": {"set", "delete"},
    "variable": {"set", "delete"},
    "label": {"create", "edit", "delete"},
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def judge(env: Env, event: Event, argv: list[str]) -> list[Action] | Verdict:
    """Return the outward actions of a `gh` call, or a refusal for a gated pull request."""
    words = argv[1:]
    group, sub = [*words, "", ""][:2]
    if group == "auth" and sub in ("switch", "logout", "login"):
        return [Action("destructive-git", f"gh auth {sub}", "auth", level4=True)]
    if group == "repo" and sub in ("delete", "archive", "rename"):
        return [Action("data-delete", f"gh repo {sub}", None, level4=True)]
    if group == "pr" and sub in ("create", "merge"):
        return _pull_request(env, event, sub, words[2:])
    if sub in GH_WRITES.get(group, set()):
        return [Action("github-write", f"gh {group} {sub}", None)]
    if group == "api" and _api_writes(words[1:]):
        return [Action("github-write", "a GitHub API write", None)]
    return []


def _api_writes(args: list[str]) -> bool:
    for index, arg in enumerate(args):
        if arg in ("-X", "--method") and index + 1 < len(args):
            return args[index + 1].upper() in WRITE_METHODS
        if arg.startswith("-X") and len(arg) > 2:
            return arg[2:].upper() in WRITE_METHODS
        if arg.startswith("--method="):
            return arg.split("=", 1)[1].upper() in WRITE_METHODS
    return any(arg in ("-f", "-F", "--field", "--raw-field", "--input") for arg in args)


def _review_passed(env: Env, branch: str) -> bool:
    safe = branch.replace("/", "__")
    path = env.cfg.state_dir / "reviews" / env.project_name / f"{safe}.json"
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get("passed"))
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _pull_request(env: Env, event: Event, sub: str, args: list[str]) -> list[Action] | Verdict:
    head = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("--head", "-H")), "")
    name = head or branch(env, event.cwd)
    if not _review_passed(env, name):
        return Verdict(
            deny=f"gh pr {sub} refused: no passed review recorded for '{name}'. A PR opens and "
            "merges only after both reviews close (D053)."
        )
    if sub == "create":
        return [Action("pr", "opening a pull request", None)]
    try:
        checks = subprocess.run(
            ["gh", "pr", "checks", *[a for a in args if not a.startswith("-")][:1]],
            capture_output=True,
            text=True,
            check=False,
            cwd=event.cwd,
            env=dict(env.environ),
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Verdict(deny=f"gh pr merge refused: CI state could not be read: {error}")
    if checks.returncode != 0:
        return Verdict(deny="gh pr merge refused: CI is not green; merge only with green CI.")
    return [Action("merge", "merging a pull request", None)]


def branch(env: Env, repo: object) -> str:
    """The current branch of a repository, empty when git cannot tell."""
    done = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        env=dict(env.environ),
        timeout=20,
    )
    return done.stdout.strip() if done.returncode == 0 else ""
