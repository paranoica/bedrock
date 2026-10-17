"""The one entry point for every hook event: read the call, run the rules, print the answer."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable, Mapping
from typing import TextIO

from bedrock_lib import clock, jsonl
from bedrock_lib.config import ConfigError, load_user_config

from bedrock_hooks.core import Env, Event, Rule, answer, evaluate

OFF = "BEDROCK_HOOKS"


def refuse_all(event_name: str, reason: str) -> dict:
    """The answer when bedrock itself cannot run: refuse tools, let everything else pass."""
    if event_name != "PreToolUse":
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"bedrock guards could not run: {reason}",
        }
    }


def main(
    argv: list[str],
    stdin: TextIO,
    stdout: TextIO,
    environ: Mapping[str, str] | None = None,
    rules: Iterable[Rule] | None = None,
) -> int:
    """Handle one hook call and return the process exit code (always 0: answers are JSON)."""
    environ = environ if environ is not None else os.environ
    event_name = argv[0] if argv else ""
    if environ.get(OFF) == "off":
        return 0
    try:
        data = json.loads(stdin.read() or "{}")
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
        event = Event(event_name or str(data.get("hook_event_name", "")), data)
        cfg = load_user_config(environ)
    except (ValueError, ConfigError) as error:
        json.dump(refuse_all(event_name, str(error)), stdout)
        return 0
    if rules is None:
        from bedrock_hooks.registry import RULES

        rules = RULES
    env = Env(cfg=cfg, now=clock.now_utc(environ), environ=environ, cwd=event.cwd)
    result = answer(event.name, evaluate(event, rules, env))
    if result:
        stdout.write(jsonl.dumps(result))
    return 0


def bootstrap() -> int:
    """Run from `hooks/dispatch.py`; anything unexpected refuses tools rather than passing them."""
    event_name = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        return main(sys.argv[1:], sys.stdin, sys.stdout)
    except Exception as error:  # noqa: BLE001 - a broken bedrock must refuse, never wave through
        json.dump(refuse_all(event_name, f"{type(error).__name__}: {error}"), sys.stdout)
        return 0
