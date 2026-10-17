"""Subcommands that write records: day log, minutes, ledger, questions, backlog, notify."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path

from bedrock_lib import backlog, clock, daylog, ledger, notify, questions
from cli_context import Context, UsageError, json_object, print_json


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add the subcommands; return the parsers that take `--project`."""
    log = subcommands.add_parser("log", help="append a day-log event")
    log.add_argument("event")
    log.add_argument("--block", default="")
    log.add_argument("--detail", default="")
    log.add_argument("--ref", action="append", default=[])
    log.add_argument("--session", default="")

    minutes = subcommands.add_parser("minutes", help="working minutes of a block")
    minutes.add_argument("block")
    minutes.add_argument("--open", action="store_true", help="count an open span up to now")

    book = subcommands.add_parser("ledger", help="agent ledger").add_subparsers(
        dest="action", required=True
    )
    book.add_parser("add").add_argument("entry", help="the entry as a JSON object")
    book.add_parser("summary").add_argument("--since", default=None)
    book.add_parser("spend").add_argument("transcript", type=Path)

    note = subcommands.add_parser("notify", help="desktop notification")
    note.add_argument("kind", choices=sorted(notify.KINDS))
    note.add_argument("title")
    note.add_argument("body")
    note.add_argument("--action", action="append", default=[], help="a button as key=Label")
    note.add_argument("--timeout", type=float, default=None, help="seconds to wait for a click")
    return [log, minutes, *_register_questions(subcommands), *_register_backlog(subcommands)]


def _register_questions(subcommands: argparse._SubParsersAction) -> list:
    asked = subcommands.add_parser("question", help="question log").add_subparsers(
        dest="action", required=True
    )
    asked.add_parser("log").add_argument("text")
    answer = asked.add_parser("answer")
    answer.add_argument("qid")
    answer.add_argument("text")
    answer.add_argument("--source", required=True)
    asked.add_parser("similar").add_argument("text")
    return list(asked.choices.values())


def _register_backlog(subcommands: argparse._SubParsersAction) -> list:
    tasks = subcommands.add_parser("backlog", help="the project backlog").add_subparsers(
        dest="action", required=True
    )
    tasks.add_parser("add").add_argument("fields", help="the task as a JSON object")
    upcoming = tasks.add_parser("next")
    upcoming.add_argument("--night", action="store_true", help="only tasks marked ok at night")
    upcoming.add_argument("--session", default=None)
    take = tasks.add_parser("claim")
    take.add_argument("task")
    take.add_argument("--session", required=True)
    move = tasks.add_parser("status")
    move.add_argument("task")
    move.add_argument("state", choices=backlog.STATES)
    move.add_argument("--note", default=None)
    tasks.add_parser("show").add_argument("task")
    tasks.add_parser("list")
    tasks.add_parser("validate")
    return list(tasks.choices.values())


def _log(ctx: Context) -> int:
    args = ctx.args
    daylog.append_event(
        ctx.cfg,
        ctx.project(),
        args.event,
        block=args.block,
        detail=args.detail,
        refs=args.ref,
        session=args.session,
        now=ctx.now,
    )
    return 0


def _minutes(ctx: Context) -> int:
    now = ctx.now if ctx.args.open else None
    print(daylog.minutes(ctx.cfg, ctx.project(), ctx.args.block, now=now))
    return 0


def _ledger(ctx: Context) -> int:
    args = ctx.args
    if args.action == "add":
        ledger.add(ctx.cfg, json_object(args.entry, "the ledger entry"), now=ctx.now)
    elif args.action == "summary":
        print_json(ledger.summary(ctx.cfg, since=clock.parse(args.since) if args.since else None))
    else:
        print_json(asdict(ledger.transcript_spend(args.transcript)))
    return 0


def _question(ctx: Context) -> int:
    args, project = ctx.args, ctx.project()
    if args.action == "log":
        print(questions.log_question(ctx.cfg, project, args.text, now=ctx.now))
    elif args.action == "answer":
        questions.answer(ctx.cfg, project, args.qid, args.text, args.source)
    else:
        hits = questions.similar(ctx.cfg, project, args.text)
        print_json([{"score": round(hit.score, 3), **hit.record} for hit in hits])
    return 0


def _backlog(ctx: Context) -> int:
    args, cfg, project = ctx.args, ctx.cfg, ctx.project()
    if args.action == "add":
        print(backlog.add(cfg, project, json_object(args.fields, "the task")))
    elif args.action == "next":
        print_json(backlog.next_task(cfg, project, night=args.night, session=args.session))
    elif args.action == "claim":
        backlog.claim(cfg, project, args.task, args.session)
    elif args.action == "status":
        backlog.set_status(cfg, project, args.task, args.state, args.note)
    elif args.action == "show":
        print_json(backlog.get(cfg, project, args.task))
    elif args.action == "list":
        print_json(backlog.tasks(cfg, project))
    else:
        problems = backlog.validate(cfg, project)
        print_json(problems)
        return 1 if problems else 0
    return 0


def _buttons(specs: Sequence[str]) -> dict[str, str]:
    buttons: dict[str, str] = {}
    for spec in specs:
        key, _, label = spec.partition("=")
        if not key or not label:
            raise UsageError(f"button '{spec}' is not key=Label")
        buttons[key] = label
    return buttons


def _notify(ctx: Context) -> int:
    args = ctx.args
    result = notify.send(
        ctx.cfg,
        args.kind,
        args.title,
        args.body,
        actions=_buttons(args.action) or None,
        timeout=args.timeout,
        now=ctx.now,
    )
    print_json({**asdict(result.decision), "shown": result.shown, "action": result.action})
    return 0


HANDLERS: dict[str, Callable[[Context], int]] = {
    "log": _log,
    "minutes": _minutes,
    "ledger": _ledger,
    "question": _question,
    "backlog": _backlog,
    "notify": _notify,
}
FAILURES = (
    daylog.LogError,
    ledger.LedgerError,
    questions.QuestionError,
    notify.NotifyError,
    backlog.BacklogError,
)
