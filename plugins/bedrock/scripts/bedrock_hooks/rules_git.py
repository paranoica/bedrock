"""Git and GitHub CLI guard (D053 E4, D007.5, D002): what may run, what needs the owner's word."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from bedrock_lib import clock, codecheck, leaks, packages

from bedrock_hooks import gate, github, shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.gate import Action

GIT_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
AGENT_READS = {"status", "diff", "log", "show", "rev-parse", "ls-files", "blame", "grep"}
AGENT_READS |= {"describe", "shortlog", "cat-file", "merge-base"}
FORCE_LONG = ("--force", "--force-with-lease", "--force-if-includes", "--mirror")
DELETE_LONG = ("--delete", "--prune")
RUNS_COMMANDS = re.compile(
    r"^(?:alias\.|core\.(?:pager|fsmonitor|sshcommand|editor|gitproxy|askpass)"
    r"|.*\.(?:cmd|command|helper|textconv|external|program|tool)$|filter\.|pager\."
    r"|credential\.|sequence\.editor|diff\.external|uploadpack|receivepack|gpg\.program)",
    re.IGNORECASE,
)
BUILTINS = {
    "add", "am", "apply", "archive", "bisect", "blame", "branch", "bundle", "cat-file",
    "check-ignore", "checkout", "cherry-pick", "clean", "clone", "commit", "config", "describe",
    "diff", "fetch", "format-patch", "gc", "grep", "init", "log", "ls-files", "ls-remote",
    "merge", "merge-base", "mv", "notes", "pull", "push", "range-diff", "rebase", "reflog",
    "remote", "reset", "restore", "rev-list", "rev-parse", "revert", "rm", "shortlog", "show",
    "sparse-checkout", "stash", "status", "submodule", "switch", "tag", "update-ref",
    "worktree", "filter-branch", "filter-repo", "replace", "send-pack", "subtree", "help",
    "version", "maintenance", "prune", "fsck", "count-objects", "cherry", "whatchanged",
}  # fmt: skip
WHOLE_TREE = {".", ":/", "*", ":/*"}
SAFE_VALUES = {"", "true", ":", "false", "cat"}
RISKY_ENV = re.compile(
    r"GIT_CONFIG\w*|GIT_SSH(?:_COMMAND)?|GIT_EXTERNAL_DIFF|GIT_PAGER|GIT_ASKPASS"
    r"|GIT_PROXY_COMMAND|GIT_SEQUENCE_EDITOR|GIT_EDITOR|GIT_EXEC_PATH|GIT_TEMPLATE_DIR"
)
CONFIG_VALUED = {"-f", "--file", "--blob", "--type", "--default", "--comment"}
PUSH_CONFIG = ("remote.", "push.", "branch.")


def _git(env: Env, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=dict(env.environ),
        timeout=20,
    )


def parse(argv: list[str]) -> tuple[list[str], list[str], str, list[str]]:
    """Split a git argv into (-c configs, -C dirs, subcommand, the subcommand's args)."""
    configs: list[str] = []
    dirs: list[str] = []
    words = argv[1:]
    while words and words[0].startswith("-"):
        option = words.pop(0)
        name, _, value = option.partition("=")
        if name in GIT_VALUED and not value and words:
            value = words.pop(0)
        if name == "-c":
            configs.append(value)
        elif name == "--config-env":
            configs.append(f"{value.split('=')[0]}=$ENV")
        elif name == "-C":
            dirs.append(value)
    return configs, dirs, words[0] if words else "", words[1:]


def _repo(event: Event, dirs: list[str]) -> Path:
    path = event.cwd
    for folder in dirs:
        path = path / Path(folder).expanduser()
    return path


def _branch(env: Env, repo: Path) -> str:
    done = _git(env, repo, "rev-parse", "--abbrev-ref", "HEAD")
    return done.stdout.strip() if done.returncode == 0 else ""


def has_option(args: list[str], *names: str) -> bool:
    """True when a long option is given in full or as a prefix git would accept (`--forc`)."""
    for arg in args:
        given = arg.split("=", 1)[0]
        if given.startswith("--") and len(given) >= 4 and any(n.startswith(given) for n in names):
            return True
    return False


def _push(env: Env, event: Event, repo: Path, args: list[str]) -> list[Action] | Verdict:
    if (env.setting("git").get("push")) == "owner":
        return Verdict(deny="git push refused: the owner pushes this repository himself (D002).")
    if repo.resolve().is_relative_to(env.cfg.memory_bank_dir.resolve()):
        return Verdict(deny="git push refused: the knowledge base is never pushed (D023).")
    refspecs = [arg for arg in args if not arg.startswith("-")][1:]
    configured = _git(env, repo, "config", "--get-regexp", r"^remote\..*\.(push|mirror)$")
    stored = configured.stdout.split() if configured.returncode == 0 else []
    if any(v.startswith("+") or v == "true" for v in stored[1::2]):
        return [Action("force-push", "a push the repository config forces", None, level4=True)]
    named = [r.lstrip("+").split(":")[-1] for r in refspecs if r.lstrip("+").split(":")[-1]]
    branch = named[0] if named else _branch(env, repo)
    if (
        has_option(args, *FORCE_LONG)
        or _short_flags(args, "f")
        or any(r.startswith("+") for r in refspecs)
    ):
        return [Action("force-push", "a force push", branch, level4=True)]
    if (
        has_option(args, *DELETE_LONG)
        or _short_flags(args, "d")
        or any(r.startswith(":") for r in refspecs)
    ):
        return [Action("delete-remote-branch", "deleting remote branches", branch, level4=True)]
    return [Action("push", "git push", None)]


def _config_pairs(sub: str, args: list[str], configs: list[str]) -> list[tuple[str, str]]:
    pairs = [(c.split("=", 1)[0], c.split("=", 1)[1] if "=" in c else "true") for c in configs]
    if sub == "config":
        positional, skip = [], False
        for arg in args:
            if skip:
                skip = False
            elif arg in CONFIG_VALUED:
                skip = True
            elif not arg.startswith("-"):
                positional.append(arg)
        if positional:
            pairs.append((positional[0], positional[1] if len(positional) > 1 else ""))
    return pairs


def _runs_commands(sub: str, args: list[str], configs: list[str]) -> str | None:
    found = next(
        (
            key
            for key, value in _config_pairs(sub, args, configs)
            if RUNS_COMMANDS.match(key) and value not in SAFE_VALUES
        ),
        None,
    )
    if found:
        return (
            f"git config '{found}' runs commands or aliases, which bedrock cannot judge; "
            "write the git command plainly."
        )
    return None


def _hooks_off(sub: str, args: list[str], configs: list[str]) -> bool:
    return any(key.lower() == "core.hookspath" for key, _ in _config_pairs(sub, args, configs))


def _risky_environment(simple: shell.Simple) -> str | None:
    for assignment in simple.assignments:
        name, _, value = assignment.partition("=")
        if RISKY_ENV.fullmatch(name) and value.strip("'\"") not in SAFE_VALUES:
            return name
    return None


def _destructive(sub: str, args: list[str]) -> Action | None:
    """Return the level-4 action of a local history- or work-destroying git command."""
    if has_option(args, "--no-verify") or (sub == "commit" and _short_flags(args, "n")):
        return Action("destructive-git", "skipping git hooks (--no-verify)", "hooks", level4=True)
    positional = [arg for arg in args if not arg.startswith("-")]
    paths = {a for a in positional if a in WHOLE_TREE or os.path.normpath(a) == "."}
    forced = has_option(args, "--force") or _short_flags(args, "f")
    first = positional[0] if positional else ""
    checks = {
        "reset": has_option(args, "--hard"),
        "clean": forced,
        "branch": "-D" in args or (forced and bool(positional)),
        "checkout": bool(paths) or forced,
        "restore": bool(paths),
        "stash": first in ("drop", "clear"),
        "reflog": first in ("expire", "delete"),
        "gc": has_option(args, "--prune"),
        "prune": True,
        "update-ref": True,
        "switch": forced or has_option(args, "--discard-changes"),
        "worktree": first == "remove" and forced,
    }
    if sub in ("filter-branch", "filter-repo", "replace"):
        return Action("history-rewrite", f"git {sub}", sub, level4=True)
    if checks.get(sub):
        return Action("destructive-git", f"git {sub} {' '.join(args)}".strip(), sub, level4=True)
    return None


def _alias(env: Env, repo: Path, sub: str) -> str | None:
    if not sub or sub in BUILTINS:
        return None
    done = _git(env, repo, "config", "--get", f"alias.{sub}")
    return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None


def _short_flags(args: list[str], letter: str) -> bool:
    return any(a.startswith("-") and not a.startswith("--") and letter in a[1:] for a in args)


def _message(args: list[str], repo: Path) -> tuple[str | None, bool]:
    """Return (the commit message if given on the command line, whether -a/--all is used)."""
    parts: list[str] = []
    every = "--all" in args
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-m", "--message", "-F", "--file") and index + 1 < len(args):
            value = args[index + 1]
            parts.append((repo / value).read_text("utf-8") if arg in ("-F", "--file") else value)
            index += 1
        elif arg.startswith("--message="):
            parts.append(arg.split("=", 1)[1])
        elif arg.startswith("-") and not arg.startswith("--"):
            letters = arg[1:]
            every = every or "a" in letters.split("m")[0]
            if "m" in letters:
                rest = letters.split("m", 1)[1]
                if rest:
                    parts.append(rest)
                elif index + 1 < len(args):
                    parts.append(args[index + 1])
                    index += 1
        index += 1
    return ("\n\n".join(parts) if parts else None), every


def _commit(env: Env, repo: Path, args: list[str], heredoc: str | None = None) -> Verdict | None:
    message, every = _message(args, repo)
    if message is not None and "$(" in message and heredoc is not None:
        # `git commit -m "$(cat <<'EOF' ... EOF)"`: the message is the heredoc's text.
        message = heredoc
    if every:
        return Verdict(
            deny="git commit -a refused: stage with git add first, so the checks see it."
        )
    home = Path(env.environ.get("HOME", str(Path.home())))
    terms = leaks.load_terms(home / ".config" / "bedrock" / "leak-terms.txt")
    try:
        root = Path(codecheck.git_root(repo))
        found = leaks.report(root, terms, env.setting("leaks"), message)
        found += codecheck.report(root, env.setting("checks"), message)
    except (leaks.LeakCheckError, codecheck.CheckError, packages.RegistryError) as error:
        return Verdict(deny=f"git commit refused: the commit checks could not run: {error}")
    if found:
        listed = "\n".join(f"  {line}" for line in found[:20])
        return Verdict(deny=f"git commit refused: fix these first (D022, D052):\n{listed}")
    return None


def _safety_net(env: Env, event: Event, actions: list[Action]) -> Verdict | None:
    """Before an allowed force push, tag what the remote had, so it can be restored."""
    notes = []
    for action in actions:
        if action.kind != "force-push" or not action.target:
            continue
        remote_ref = f"refs/remotes/origin/{action.target}"
        if _git(env, event.cwd, "rev-parse", "--verify", "-q", remote_ref).returncode != 0:
            continue
        stamp = clock.iso(env.now).replace(":", "").replace("-", "")
        tag = f"bedrock-safety/{action.target}-{stamp}"
        if _git(env, event.cwd, "tag", tag, remote_ref).returncode != 0:
            return Verdict(deny=f"force push refused: the safety tag {tag} could not be made.")
        notes.append(f"safety tag {tag} keeps the old origin/{action.target}")
    return Verdict(notice="; ".join(notes)) if notes else None


def _hidden_behaviour(
    env: Env, simple: shell.Simple, repo: Path, parsed: tuple[list[str], str, list[str]]
) -> list[Action] | Verdict | None:
    """Git run with config, environment or aliases that change what the command does."""
    configs, sub, args = parsed
    if name := _risky_environment(simple):
        return Verdict(deny=f"refused: {name} makes git run commands bedrock cannot judge.")
    if sub == "push" and any(c.startswith(PUSH_CONFIG) for c in configs):
        return [Action("force-push", "a push with overridden remote config", None, level4=True)]
    if _hooks_off(sub, args, configs):
        return [Action("destructive-git", "disabling git hooks", "hooks", level4=True)]
    if problem := _runs_commands(sub, args, configs):
        return Verdict(deny=f"refused: {problem}")
    if expansion := _alias(env, repo, sub):
        return Verdict(
            deny=f"refused: 'git {sub}' is an alias for '{expansion}'; write the full command."
        )
    return None


def _git_call(env: Env, event: Event, simple: shell.Simple) -> list[Action] | Verdict:
    configs, dirs, sub, args = parse(simple.argv)
    repo = _repo(event, dirs)
    hidden = _hidden_behaviour(env, simple, repo, (configs, sub, args))
    if hidden is not None:
        return hidden
    if event.agent_id and sub not in AGENT_READS:
        return Verdict(
            deny=f"git {sub} refused for an agent: agents only read git (status, diff, log, "
            "show); the main session commits (D007)."
        )
    if destructive := _destructive(sub, args):
        return [destructive]
    if sub == "push" or (sub == "subtree" and args[:1] == ["push"]):
        return _push(env, event, repo, args[1:] if sub == "subtree" else args)
    if sub == "send-pack":
        return _push(env, event, repo, ["origin", *args])
    if sub == "commit":
        bodies = shell.heredoc_bodies(str(event.tool_input.get("command", "")))
        return _commit(env, repo, args, bodies[0] if bodies else None) or []
    return []


def _judge(env: Env, event: Event, simple: shell.Simple) -> list[Action] | Verdict:
    if simple.program == "hub":
        simple = shell.Simple(["git", *simple.argv[1:]])
    if simple.program == "gh":
        if event.agent_id:
            return Verdict(deny="gh refused for an agent: only the main session acts outward.")
        return github.judge(env, event, simple.argv)
    return _git_call(env, event, simple)


def check(event: Event, env: Env) -> Verdict | None:
    """Judge every git and gh call inside a Bash command."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    actions: list[Action] = []
    for simple in simples:
        if simple.program not in ("git", "gh", "hub"):
            continue
        judged = _judge(env, event, simple)
        if isinstance(judged, Verdict):
            return judged
        actions += judged
    if not actions:
        return None
    return gate.decide(env, event, actions) or _safety_net(env, event, actions)


RULES = [
    Rule("git", frozenset({"PreToolUse"}), GUARD, check, lambda event: event.tool == "Bash"),
]
