"""Subcommands for texts meant for people: the call archive and the text check."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from bedrock_lib import calls, slop
from cli_context import Context, print_json


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add `bedrock call ...` and `bedrock text check`; the call actions take `--project`."""
    actions = subcommands.add_parser("call", help="the call archive").add_subparsers(
        dest="action", required=True
    )
    add = actions.add_parser("add", help="archive a raw transcript unchanged")
    add.add_argument("transcript", type=Path)
    add.add_argument("--source", required=True, help="krisp, meet, whisper, ...")
    add.add_argument("--title", required=True)
    add.add_argument("--date", required=True, help="YYYY-MM-DD")
    add.add_argument("--participant", action="append", default=[])
    add.add_argument("--language", default="en")
    actions.add_parser("verify", help="the raw transcript is unchanged").add_argument("id")
    quotes = actions.add_parser("quotes", help="every debrief item quotes the call")
    quotes.add_argument("id")
    quotes.add_argument("debrief", type=Path)
    actions.add_parser("search", help="lines of all calls with a phrase").add_argument("text")

    text = subcommands.add_parser("text", help="mechanical tells in a text for people")
    text.add_argument("action", choices=("check",))
    text.add_argument("file", nargs="?", default="-", help="a file, or - for stdin")
    text.add_argument("--slack", action="store_true", help="also flag markdown Slack shows raw")
    return list(actions.choices.values())


def _call(ctx: Context) -> int:
    args, cfg, project = ctx.args, ctx.cfg, ctx.project()
    if args.action == "add":
        print(
            calls.add(
                cfg,
                project,
                args.transcript,
                source=args.source,
                title=args.title,
                day=args.date,
                participants=args.participant,
                language=args.language,
            )
        )
        return 0
    if args.action == "verify":
        intact = calls.verify(cfg, project, args.id)
        print("intact" if intact else "changed")
        return 0 if intact else 1
    if args.action == "quotes":
        text = args.debrief.read_text(encoding="utf-8")
        problems = [asdict(p) for p in calls.check_quotes(cfg, project, args.id, text)]
        print_json(problems)
        return 1 if problems else 0
    print_json([asdict(hit) for hit in calls.search(cfg, project, args.text)])
    return 0


def _text(ctx: Context) -> int:
    source = ctx.args.file
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    found = [asdict(f) for f in slop.check(text, slack=ctx.args.slack)]
    print_json(found)
    return 1 if found else 0


HANDLERS: dict[str, Callable[[Context], int]] = {"call": _call, "text": _text}
FAILURES: tuple[type[Exception], ...] = (calls.CallError,)
