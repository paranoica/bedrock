"""The one entry point for every hook event: read the call, run the rules, print the answer."""

from __future__ import annotations

import io
import json
import os
import re
import sys
from collections.abc import Iterable, Mapping
from typing import TextIO

from bedrock_lib import clock, jsonl
from bedrock_lib.config import ConfigError, load_user_config

from bedrock_hooks.core import Env, Event, Rule, answer, evaluate

OFF = "BEDROCK_HOOKS"
LOOKS_LIKE_PR = re.compile(r"\bgh\b.*\bpr\b.*\b(?:create|merge)\b", re.S)


def refuse_all(event_name: str, reason: str, raw: str = "") -> dict:
    """The answer when bedrock itself cannot run: refuse only what the review gate guards."""
    if event_name != "PreToolUse" or not LOOKS_LIKE_PR.search(raw):
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"bedrock review gate could not run: {reason}",
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
    raw = stdin.read()
    try:
        data = json.loads(raw or "{}")
        if not isinstance(data, dict):
            raise ValueError("hook input is not a JSON object")
        event = Event(event_name or str(data.get("hook_event_name", "")), data)
        cfg = load_user_config(environ)
    except (ValueError, ConfigError) as error:
        json.dump(refuse_all(event_name, str(error), raw), stdout)
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
    """Run from `hooks/dispatch.py`; a crash lets the work through, except a gated gh pr call."""
    event_name = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.stdin.read()
    try:
        return main(sys.argv[1:], io.StringIO(raw), sys.stdout)
    except Exception as error:  # noqa: BLE001 - only the review gate fails closed
        json.dump(refuse_all(event_name, f"{type(error).__name__}: {error}", raw), sys.stdout)
        return 0
