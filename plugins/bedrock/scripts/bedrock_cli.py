"""The `bedrock` command: one entry point for skills, hooks and the owner.

Exit codes: 0 done or clean, 1 refused or found something, 2 a check could not run.
`bedrock test` and `bedrock cmd` return the command's own exit code instead.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import cli_checks
import cli_kb
import cli_ops
import cli_people
import cli_records
import cli_runs
from bedrock_lib import clock
from bedrock_lib.config import ConfigError, load_user_config
from bedrock_lib.jsonl import JsonlError
from cli_context import CannotRun, Context, UsageError

GROUPS = (cli_records, cli_runs, cli_checks, cli_kb, cli_people, cli_ops)
TAKES_A_COMMAND = ("test", "cmd", "night")
FAILURES = (ConfigError, JsonlError, *(error for g in GROUPS for error in g.FAILURES))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bedrock")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for group in GROUPS:
        for sub in group.register(subcommands):
            sub.add_argument("--project", default=None)
    return parser


def _split(words: list[str]) -> tuple[list[str], list[str]]:
    # Everything after `--` is the command that `test` or `cmd` runs, never bedrock's options.
    if words[:1] and words[0] in TAKES_A_COMMAND and "--" in words:
        cut = words.index("--")
        return words[:cut], words[cut + 1 :]
    return words, []


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | None = None,
) -> int:
    """Run one subcommand and return its exit code."""
    env = env if env is not None else os.environ
    words, tail = _split(list(sys.argv[1:] if argv is None else argv))
    args = _parser().parse_args(words)
    args.argv = tail
    handlers = {name: handler for group in GROUPS for name, handler in group.HANDLERS.items()}
    try:
        ctx = Context(args, load_user_config(env), cwd or Path.cwd(), env, clock.now_utc(env))
        return handlers[args.command](ctx)
    except CannotRun as error:
        print(f"bedrock: {error}", file=sys.stderr)
        return 2
    except (UsageError, OSError, ValueError, *FAILURES) as error:
        print(f"bedrock: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
