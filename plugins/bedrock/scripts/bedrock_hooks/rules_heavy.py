"""Heavy runs go through the machine-wide lock (D040.5): full suites, type checks, builds."""

from __future__ import annotations

import shlex
from pathlib import PurePosixPath

from bedrock_hooks import shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.rules_outward import unrun

SCRIPT_RUNNERS = {"npm", "pnpm", "yarn", "bun"}
HEAVY_SCRIPTS = {"test", "t", "build", "typecheck", "type-check", "e2e"}
TEST_RUNNERS = {"jest", "vitest", "pytest", "mocha", "playwright"}
RUNNER_WORDS = {"run", "test", "watch"}
VALUED = {"-c", "--config", "-k", "-m", "--project", "-p", "--reporter", "-t", "--testNamePattern"}


def _paths(args: list[str]) -> list[str]:
    found, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in VALUED:
            skip = True
        elif not arg.startswith("-") and arg not in RUNNER_WORDS:
            found.append(arg)
    return found


def _generic(argv: list[str]) -> str | None:
    words = unrun(argv)
    program = PurePosixPath(words[0]).name
    args = words[1:]
    if program == "tsc" and not {"--version", "-v", "--help"} & set(args):
        return "a full type check"
    if program in SCRIPT_RUNNERS:
        script = args[1] if args[:1] == ["run"] and len(args) > 1 else (args[0] if args else "")
        return f"`{program} {' '.join(args[:2])}`" if script in HEAVY_SCRIPTS else None
    if program in TEST_RUNNERS and not _paths(args):
        return f"the full `{program}` suite"
    if program in ("next", "vite") and args[:1] == ["build"]:
        return "a build"
    return None


def _project_heavy(env: Env, argv: list[str]) -> str | None:
    commands = (env.project.data.get("commands") if env.project else None) or {}
    for name, spec in commands.items():
        if isinstance(spec, dict) and spec.get("heavy"):
            run = shlex.split(str(spec.get("run", "")))
            if run and argv[: len(run)] == run:
                return name
    return None


def check(event: Event, env: Env) -> Verdict | None:
    """Refuse a heavy command that bypasses `bedrock test` / `bedrock cmd`."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError:
        return None
    for simple in simples:
        if name := _project_heavy(env, simple.argv):
            return Verdict(
                deny=f"run it as `bedrock cmd {name}`: heavy commands take the machine lock and "
                "are measured (D040)."
            )
        if what := _generic(simple.argv):
            return Verdict(
                deny=f"{what} is heavy: run it through `bedrock test <suite> -- <command>` (or "
                "`bedrock cmd`), one heavy run per machine (D040); narrow runs with a file pass."
            )
    return None


RULES = [Rule("heavy", frozenset({"PreToolUse"}), GUARD, check, lambda e: e.tool == "Bash")]
