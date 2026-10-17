"""Subcommands that run things within the machine: `machine`, `test`, `cmd`."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import asdict, dataclass
from typing import Any

from bedrock_lib import commands, machine, runlock, testrun
from cli_context import Context, UsageError, print_json


@dataclass(frozen=True)
class RunOptions:
    """How a measured suite run is made."""

    workers: int | None = None
    serial: bool = False
    heavy: bool = False
    wait: bool = True
    timeout: float | None = None


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add the subcommands; return the parsers that take `--project`."""
    subcommands.add_parser("machine", help="free memory, load, cores and the heavy-run holder")

    trial = subcommands.add_parser(
        "test",
        help="run a test command, measured, within the machine",
        usage="bedrock test suite [options] -- command ...",
    )
    trial.add_argument("suite", help="the suite's name in the project's test profile")
    trial.add_argument("--heavy", action="store_true", help="take the machine-wide heavy lock")
    trial.add_argument("--no-wait", action="store_true", help="refuse instead of queueing")
    trial.add_argument("--serial", action="store_true", help="run with one worker")
    trial.add_argument("--workers", type=int, default=None, help="override the worker count")
    trial.add_argument("--timeout", type=float, default=None, help="seconds before it is stopped")
    trial.set_defaults(argv=[])

    own = subcommands.add_parser("cmd", help="run one of the project's own commands")
    own.add_argument("name", nargs="?")
    own.add_argument("--list", action="store_true", help="print the commands")
    return [trial]


def exit_code(returncode: int) -> int:
    """Map a signal death (negative code) to the shell's 128 + signal."""
    return returncode if returncode >= 0 else 128 - returncode


def _waiting(info: dict[str, Any] | None) -> None:
    print(f"bedrock: waiting for {runlock.describe(info)}", file=sys.stderr, flush=True)


def run_suite(
    ctx: Context, project: str, suite: str, build: Callable[[int], list[str]], options: RunOptions
) -> int:
    """Pick the worker count, take the lock if heavy, run measured, record, report one line."""
    measured = testrun.per_worker_mb(ctx.cfg, project, suite)
    count = options.workers or machine.workers(machine.snapshot(), measured, options.serial)
    lock: AbstractContextManager[None] = (
        runlock.heavy(ctx.cfg, f"{project}: {suite}", options.wait, _waiting)
        if options.heavy
        else nullcontext()
    )
    root = ctx.cwd
    with lock:
        env = {**ctx.env, "BEDROCK_WORKERS": str(count)}
        result = testrun.run_measured(build(count), root, env=env, timeout=options.timeout)
    testrun.record(ctx.cfg, project, suite, result, count)
    if result.timed_out:
        status = "timed out"
    else:
        status = "passed" if result.returncode == 0 else f"failed ({result.returncode})"
    print(
        f"bedrock: {suite} {status} in {result.seconds:.0f}s, peak {result.peak_mb:.0f} MB, "
        f"{count} worker{'' if count == 1 else 's'}",
        file=sys.stderr,
    )
    return exit_code(result.returncode)


def _machine(ctx: Context) -> int:
    print_json({**asdict(machine.snapshot()), "heavy": runlock.holder(ctx.cfg)})
    return 0


def _test(ctx: Context) -> int:
    args = ctx.args
    if not args.argv:
        raise UsageError("no command to run; put it after --")

    def build(count: int) -> list[str]:
        return [part.replace("{workers}", str(count)) for part in args.argv]

    options = RunOptions(args.workers, args.serial, args.heavy, not args.no_wait, args.timeout)
    return run_suite(ctx, ctx.project(), args.suite, build, options)


def _cmd(ctx: Context) -> int:
    args, project = ctx.args, ctx.workspace()
    if args.list:
        commands.load(project)
        print_json(project.data["commands"])
        return 0
    if not args.name:
        raise UsageError("name a command, or pass --list")
    command = commands.find(project, args.name)
    if command.suite is None:
        argv = commands.argv(command, args.argv, 1)
        completed = subprocess.run(argv, cwd=project.root, env=dict(ctx.env), check=False)
        return exit_code(completed.returncode)

    def build(count: int) -> list[str]:
        return commands.argv(command, args.argv, count)

    at_root = Context(ctx.args, ctx.cfg, project.root, ctx.env, ctx.now)
    options = RunOptions(serial=command.serial, heavy=command.heavy)
    return run_suite(at_root, project.name, command.suite, build, options)


HANDLERS: dict[str, Callable[[Context], int]] = {"machine": _machine, "test": _test, "cmd": _cmd}
FAILURES = (machine.MachineError, runlock.Busy, testrun.TestRunError, commands.CommandError)
