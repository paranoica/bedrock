"""The `bedrock` command: how skills, hooks and the owner write logs, ledger and questions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bedrock_lib import clock, daylog, ledger, notify, questions
from bedrock_lib.config import ConfigError, UserConfig, find_project, load_user_config
from bedrock_lib.jsonl import JsonlError

FAILURES = (
    ConfigError,
    JsonlError,
    daylog.LogError,
    ledger.LedgerError,
    questions.QuestionError,
    notify.NotifyError,
)


class UsageError(Exception):
    """The command line asks for something the command cannot do."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bedrock")
    commands = parser.add_subparsers(dest="command", required=True)

    log = commands.add_parser("log", help="append a day-log event")
    log.add_argument("event")
    log.add_argument("--block", default="")
    log.add_argument("--detail", default="")
    log.add_argument("--ref", action="append", default=[])
    log.add_argument("--session", default="")

    minutes = commands.add_parser("minutes", help="working minutes of a block")
    minutes.add_argument("block")
    minutes.add_argument("--open", action="store_true", help="count an open span up to now")

    book = commands.add_parser("ledger", help="agent ledger").add_subparsers(
        dest="action", required=True
    )
    book.add_parser("add").add_argument("entry", help="the entry as a JSON object")
    book.add_parser("summary").add_argument("--since", default=None)
    book.add_parser("spend").add_argument("transcript", type=Path)

    asked = commands.add_parser("question", help="question log").add_subparsers(
        dest="action", required=True
    )
    asked.add_parser("log").add_argument("text")
    answer = asked.add_parser("answer")
    answer.add_argument("qid")
    answer.add_argument("text")
    answer.add_argument("--source", required=True)
    asked.add_parser("similar").add_argument("text")

    note = commands.add_parser("notify", help="desktop notification")
    note.add_argument("kind", choices=sorted(notify.KINDS))
    note.add_argument("title")
    note.add_argument("body")
    note.add_argument("--action", action="append", default=[], help="a button as key=Label")
    note.add_argument("--timeout", type=float, default=None, help="seconds to wait for a click")

    for sub in (log, minutes, *asked.choices.values()):
        sub.add_argument("--project", default=None)
    return parser


def _project(args: argparse.Namespace, cwd: Path) -> str:
    if args.project:
        return args.project
    found = find_project(cwd)
    if found is None:
        raise UsageError("no .claude/bedrock.json above this folder; pass --project")
    return found.name


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False))


def _log(args: argparse.Namespace, cfg: UserConfig, project: str, now: Any) -> None:
    daylog.append_event(
        cfg,
        project,
        args.event,
        block=args.block,
        detail=args.detail,
        refs=args.ref,
        session=args.session,
        now=now,
    )


def _minutes(args: argparse.Namespace, cfg: UserConfig, project: str, now: Any) -> None:
    print(daylog.minutes(cfg, project, args.block, now=now if args.open else None))


def _ledger(args: argparse.Namespace, cfg: UserConfig, now: Any) -> None:
    if args.action == "add":
        entry = json.loads(args.entry)
        if not isinstance(entry, dict):
            raise UsageError("the ledger entry must be a JSON object")
        ledger.add(cfg, entry, now=now)
    elif args.action == "summary":
        _print(ledger.summary(cfg, since=clock.parse(args.since) if args.since else None))
    else:
        _print(asdict(ledger.transcript_spend(args.transcript)))


def _question(args: argparse.Namespace, cfg: UserConfig, project: str, now: Any) -> None:
    if args.action == "log":
        print(questions.log_question(cfg, project, args.text, now=now))
    elif args.action == "answer":
        questions.answer(cfg, project, args.qid, args.text, args.source)
    else:
        hits = questions.similar(cfg, project, args.text)
        _print([{"score": round(hit.score, 3), **hit.record} for hit in hits])


def _buttons(specs: Sequence[str]) -> dict[str, str]:
    buttons: dict[str, str] = {}
    for spec in specs:
        key, _, label = spec.partition("=")
        if not key or not label:
            raise UsageError(f"button '{spec}' is not key=Label")
        buttons[key] = label
    return buttons


def _notify(args: argparse.Namespace, cfg: UserConfig, now: Any) -> None:
    result = notify.send(
        cfg,
        args.kind,
        args.title,
        args.body,
        actions=_buttons(args.action) or None,
        timeout=args.timeout,
        now=now,
    )
    _print({**asdict(result.decision), "shown": result.shown, "action": result.action})


def _dispatch(args: argparse.Namespace, cfg: UserConfig, cwd: Path, now: Any) -> None:
    global_commands: dict[str, Callable[[argparse.Namespace, UserConfig, Any], None]] = {
        "ledger": _ledger,
        "notify": _notify,
    }
    project_commands = {"log": _log, "minutes": _minutes, "question": _question}
    if args.command in global_commands:
        global_commands[args.command](args, cfg, now)
    else:
        project_commands[args.command](args, cfg, _project(args, cwd), now)


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> int:
    """Run one command; return 0 on success and 1 on a refused or failed request."""
    env = env if env is not None else os.environ
    args = _parser().parse_args(argv)
    try:
        cfg = load_user_config(env)
        _dispatch(args, cfg, cwd or Path.cwd(), clock.now_utc(env))
    except (UsageError, OSError, ValueError, *FAILURES) as error:
        print(f"bedrock: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
