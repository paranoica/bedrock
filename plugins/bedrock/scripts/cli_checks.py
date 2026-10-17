"""Subcommands that guard a change: `leaks` and `check`. Exit 0 clean, 1 found, 2 cannot run."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from bedrock_lib import codecheck, leaks, packages
from cli_context import CannotRun, Context


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add the subcommands; none of them takes `--project`."""
    leak = subcommands.add_parser("leaks", help="check staged changes and commit text for leaks")
    leak.add_argument("--message", default=None, help="commit or PR text to check too")
    leak.add_argument("--message-file", type=Path, default=None)
    leak.add_argument("--terms", type=Path, default=None, help="the private list of names")
    leak.add_argument("--allow", action="append", default=[], help="a model word allowed here")
    leak.add_argument("--no-gitleaks", action="store_true", help="skip the secret scan")

    audit = subcommands.add_parser("check", help="code checks on the staged change (D022)")
    audit.add_argument("--base", default=None, help="check HEAD against this ref instead")
    audit.add_argument("--message", default=None, help="commit message to check")
    audit.add_argument("--message-file", type=Path, default=None)
    audit.add_argument("--allow-test-changes", action="store_true", help="the task edits tests")
    audit.add_argument("--no-network", action="store_true", help="skip the package registry")
    return []


def _message(ctx: Context) -> str | None:
    if ctx.args.message_file:
        return ctx.args.message_file.read_text("utf-8")
    return ctx.args.message


def _leaks(ctx: Context) -> int:
    args = ctx.args
    home = Path(ctx.env.get("HOME", str(Path.home())))
    terms = leaks.load_terms(args.terms or home / ".config" / "bedrock" / "leak-terms.txt")
    settings = dict(ctx.settings("leaks"))
    settings["allow"] = [*args.allow, *settings.get("allow", [])]
    if args.no_gitleaks:
        settings["gitleaks"] = False
    workspace = ctx.workspace() if ctx.settings("leaks") else None
    try:
        lines = leaks.report(
            workspace.root if workspace else ctx.cwd, terms, settings, _message(ctx)
        )
    except leaks.LeakCheckError as error:
        raise CannotRun(str(error)) from error
    for line in lines:
        print(line)
    return 1 if lines else 0


def _check(ctx: Context) -> int:
    args = ctx.args
    try:
        repo = Path(codecheck.git_root(ctx.cwd))
        lines = codecheck.report(
            repo,
            ctx.settings("checks"),
            _message(ctx),
            base=args.base,
            network=not args.no_network,
            allow_test_changes=args.allow_test_changes,
        )
    except (codecheck.CheckError, packages.RegistryError) as error:
        raise CannotRun(str(error)) from error
    for line in lines:
        print(line)
    return 1 if lines else 0


HANDLERS: dict[str, Callable[[Context], int]] = {"leaks": _leaks, "check": _check}
FAILURES: tuple[type[Exception], ...] = ()
