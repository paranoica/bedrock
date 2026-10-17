"""Subcommands that guard a change: `leaks` and `check`. Exit 0 clean, 1 found, 2 cannot run."""

from __future__ import annotations

import argparse
import fnmatch
from collections.abc import Callable, Iterable
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


def _kept(found: Iterable[tuple[str, str, str]], ignore: list[str]) -> list[str]:
    # Ignore globs are for a checker's own fixtures; a found secret is never ignored.
    return [
        line
        for path, rule, line in found
        if rule == "secret" or not any(fnmatch.fnmatch(path, glob) for glob in ignore)
    ]


def _leaks(ctx: Context) -> int:
    args = ctx.args
    home = Path(ctx.env.get("HOME", str(Path.home())))
    terms = leaks.load_terms(args.terms or home / ".config" / "bedrock" / "leak-terms.txt")
    settings = ctx.settings("leaks")
    workspace = ctx.workspace() if settings else None
    root = workspace.root if workspace else ctx.cwd
    allow = [*args.allow, *settings.get("allow", [])]
    try:
        found = leaks.check_staged(root, terms, allow=allow, gitleaks=not args.no_gitleaks)
    except leaks.LeakCheckError as error:
        raise CannotRun(str(error)) from error
    if message := _message(ctx):
        found += leaks.scan_text(message, terms)
    lines = [(f.path, f.rule, f"{f.path}:{f.line}: {f.rule}: {f.excerpt}") for f in found]
    report = _kept(lines, settings.get("ignore", []))
    for line in report:
        print(line)
    return 1 if report else 0


def _check(ctx: Context) -> int:
    args = ctx.args
    settings = ctx.settings("checks")
    limits = codecheck.Limits(
        file_lines=int(settings.get("file_lines", codecheck.Limits.file_lines)),
        function_lines=int(settings.get("function_lines", codecheck.Limits.function_lines)),
    )
    try:
        repo = Path(codecheck.git_root(ctx.cwd))
        found = codecheck.run_checks(
            repo,
            base=args.base,
            network=not args.no_network,
            allow_test_changes=args.allow_test_changes,
            limits=limits,
            allow_hosts=tuple(settings.get("allow_hosts", ())),
        )
    except (codecheck.CheckError, packages.RegistryError) as error:
        raise CannotRun(str(error)) from error
    message = _message(ctx)
    if message is not None:
        found += codecheck.check_message(message)
    lines = [(f.path, f.check, f"{f.path}:{f.line}: {f.check}: {f.message}") for f in found]
    report = _kept(lines, settings.get("ignore", []))
    for line in report:
        print(line)
    return 1 if report else 0


HANDLERS: dict[str, Callable[[Context], int]] = {"leaks": _leaks, "check": _check}
FAILURES: tuple[type[Exception], ...] = ()
