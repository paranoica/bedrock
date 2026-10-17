"""Subcommands for the knowledge base and its backup, and for the machine map of the code."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from bedrock_lib import backup, clock, codecheck, codemap, kb, kbdrift
from bedrock_lib.config import find_project
from cli_context import Context, UsageError, print_json


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add `bedrock kb ...`; every action takes `--project`."""
    actions = subcommands.add_parser("kb", help="the project's knowledge base").add_subparsers(
        dest="action", required=True
    )
    create = actions.add_parser("init", help="create the project's minimal folder")
    create.add_argument("--code", required=True, help="the prefix of decision codes, e.g. ACME")
    actions.add_parser("validate", help="check links, fields, headings, history, orphans")
    drift = actions.add_parser("drift", help="module notes whose code changed since verified")
    drift.add_argument("--repo", type=Path, default=None)
    bare = actions.add_parser("uncovered", help="top-level modules without a note")
    bare.add_argument("--root", action="append", default=[], help="a folder holding modules")
    bare.add_argument("--repo", type=Path, default=None)
    links = actions.add_parser("backlinks", help="notes linking to a note")
    links.add_argument("name")

    subcommands.add_parser("backup", help="encrypt and commit today's snapshot (never pushes)")

    atlas = subcommands.add_parser("map", help="the machine map of the code (leads, not facts)")
    atlas.add_argument("action", choices=("build", "check", "defs", "callers"))
    atlas.add_argument("symbol", nargs="?")
    atlas.add_argument("--repo", type=Path, default=None)
    return list(actions.choices.values())


def _repo(ctx: Context) -> Path:
    if ctx.args.repo:
        return ctx.args.repo
    return Path(codecheck.git_root(ctx.cwd))


def _kb(ctx: Context) -> int:
    args, bank, project = ctx.args, ctx.cfg.memory_bank_dir, ctx.project()
    if args.action == "init":
        print(kb.init(bank, project, args.code))
    elif args.action == "validate":
        problems = [asdict(problem) for problem in kb.validate(bank, project)]
        print_json(problems)
        return 1 if problems else 0
    elif args.action == "drift":
        print_json(kbdrift.drift(bank, project, _repo(ctx)))
    elif args.action == "uncovered":
        print_json(kb.uncovered(bank, project, _repo(ctx), args.root or ["src"]))
    else:
        print_json(kb.backlinks(bank, project, args.name))
    return 0


def _root(ctx: Context) -> Path:
    if ctx.args.repo:
        return ctx.args.repo
    found = find_project(ctx.cwd)
    return found.root if found else ctx.cwd


def _map(ctx: Context) -> int:
    args, root = ctx.args, _root(ctx)
    target = codemap.store(ctx.cfg.state_dir, root)
    if args.action == "build":
        print(codemap.write(target, codemap.build(root, previous=codemap.load(target))))
        return 0
    if args.action == "check":
        print(codemap.check(root, target))
        return 0
    if not args.symbol:
        raise UsageError(f"`bedrock map {args.action}` needs a symbol")
    if codemap.check(root, target) != "fresh":
        raise UsageError("the map is absent or stale: run `bedrock map build` first")
    data = codemap.load(target) or {}
    key = "symbols" if args.action == "defs" else "callers"
    print_json(data.get(key, {}).get(args.symbol, []))
    return 0


def _backup(ctx: Context) -> int:
    cfg = ctx.cfg
    if cfg.backup_repo is None or not cfg.backup_recipient:
        raise UsageError(
            "set backup.repo and backup.recipient in ~/.config/bedrock/config.json first"
        )
    day = clock.in_zone(ctx.now, cfg.display_tz).date().isoformat()
    home = Path(ctx.env.get("HOME", str(Path.home())))
    print(backup.run(cfg, home, cfg.backup_repo, cfg.backup_recipient, day=day))
    return 0


HANDLERS: dict[str, Callable[[Context], int]] = {"kb": _kb, "map": _map, "backup": _backup}
FAILURES: tuple[type[Exception], ...] = (codecheck.CheckError, backup.BackupError)
