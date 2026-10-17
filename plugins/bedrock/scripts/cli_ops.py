"""Subcommands for looking back and keeping work running: retro, hot spots, night, settings."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from bedrock_lib import doctor, insights, night, notify, projectcheck
from bedrock_lib.config import find_project
from cli_context import Context, UsageError, print_json

STOP_HOOK_CAP = 60


def register(subcommands: argparse._SubParsersAction) -> list[argparse.ArgumentParser]:
    """Add `retro`, `arch`, `night` and `project`; `retro` takes `--project`."""
    retro = subcommands.add_parser("retro", help="the week's blocks, minutes and calibration")
    retro.add_argument("--days", type=int, default=7)
    arch = subcommands.add_parser("arch", help="files that change often and are large")
    arch.add_argument("action", choices=("hotspots",))
    arch.add_argument("--days", type=int, default=90)
    arch.add_argument("--top", type=int, default=15)
    watch = subcommands.add_parser("night", help="keep a command alive until a deadline")
    watch.add_argument("action", choices=("watch",))
    watch.add_argument("--until", required=True, help="local clock time, HH:MM")
    subcommands.add_parser("doctor", help="what this machine has and lacks for bedrock")
    settings = subcommands.add_parser("project", help="check the workspace settings")
    settings.add_argument("action", choices=("check",))
    return [retro]


def _retro(ctx: Context) -> int:
    print_json(insights.retro(ctx.cfg, ctx.project(), ctx.now, days=ctx.args.days))
    return 0


def _arch(ctx: Context) -> int:
    found = find_project(ctx.cwd)
    root = found.root if found else ctx.cwd
    spots = insights.hotspots(root, days=ctx.args.days, top=ctx.args.top)
    print_json([asdict(s) for s in spots])
    return 0


def _night(ctx: Context) -> int:
    argv = list(ctx.args.argv)
    if not argv:
        raise UsageError("bedrock night watch --until HH:MM -- <command>")
    # The watchdog runs on the real clock, so the deadline does too.
    deadline = night.until(ctx.args.until, datetime.now(UTC), ctx.cfg.display_tz)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    # Claude Code stops honouring Stop-hook blocks after 8 in a row; the night needs more, and
    # bedrock's own fuses (two tries per task, 40 steps) stop it first (D046).
    child = {"CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": str(STOP_HOOK_CAP), **os.environ}
    log = ctx.cfg.state_dir / "night.jsonl"
    result = night.watch(argv, deadline.timestamp(), log, env=child)
    if result.reason == "gave-up":
        notify.send(ctx.cfg, "blocked", "bedrock night", f"stopped after {result.runs} crashes")
    print_json(asdict(result))
    return 0 if result.reason != "gave-up" else 1


def _project(ctx: Context) -> int:
    problems = projectcheck.check(ctx.workspace().data)
    print_json(problems)
    return 1 if problems else 0


def _doctor(ctx: Context) -> int:
    checks = doctor.run(ctx.cfg, Path(ctx.env.get("HOME", str(Path.home()))))
    for check in checks:
        print(f"{check.level:4}  {check.name:14} {check.detail}")
    return doctor.exit_code(checks)


HANDLERS: dict[str, Callable[[Context], int]] = {
    "doctor": _doctor,
    "retro": _retro,
    "arch": _arch,
    "night": _night,
    "project": _project,
}
FAILURES: tuple[type[Exception], ...] = (insights.InsightError, notify.NotifyError)
