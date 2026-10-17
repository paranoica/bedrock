"""Rules, their two classes, and how their verdicts become one Claude Code hook answer.

A guard that crashes refuses ("could not verify"), because a crashed hook would let the action
through. A helper that crashes is logged and skipped, because it must never block the work.
"""

from __future__ import annotations

import contextlib
import traceback
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from bedrock_lib import clock, jsonl
from bedrock_lib.config import ProjectConfig, UserConfig, find_project

GUARD = "guard"
HELPER = "helper"


@dataclass(frozen=True)
class Event:
    """One hook call from Claude Code."""

    name: str
    data: dict[str, Any]

    @property
    def tool(self) -> str:
        """The tool name, empty outside tool events."""
        return str(self.data.get("tool_name") or "")

    @property
    def tool_input(self) -> dict[str, Any]:
        """The tool's input, empty outside tool events."""
        value = self.data.get("tool_input")
        return value if isinstance(value, dict) else {}

    @property
    def agent_id(self) -> str | None:
        """The subagent's id; None in the main session."""
        value = self.data.get("agent_id")
        return str(value) if value else None

    @property
    def session(self) -> str:
        """The session id."""
        return str(self.data.get("session_id") or "")

    @property
    def cwd(self) -> Path:
        """The folder the session works in."""
        return Path(str(self.data.get("cwd") or "."))


@dataclass
class Env:
    """What every rule may read: settings, the workspace, the time, the process environment."""

    cfg: UserConfig
    now: datetime
    environ: Mapping[str, str]
    cwd: Path
    _project: ProjectConfig | None = None
    _looked: bool = False

    @property
    def project(self) -> ProjectConfig | None:
        """The workspace the session runs in, looked up once."""
        if not self._looked:
            self._project = find_project(self.cwd)
            self._looked = True
        return self._project

    @property
    def project_name(self) -> str:
        """The project name, `global` outside a workspace."""
        return self.project.name if self.project else "global"

    def setting(self, section: str) -> dict[str, Any]:
        """One section of the workspace settings."""
        value = self.project.data.get(section) if self.project else None
        return value if isinstance(value, dict) else {}


@dataclass
class Verdict:
    """What one rule says: refuse a tool, block a stop or prompt, add context, rewrite input."""

    deny: str = ""
    block: str = ""
    context: str = ""
    notice: str = ""
    updated_input: dict[str, Any] | None = None


@dataclass(frozen=True)
class Rule:
    """A named check on some events; `applies` is cheap, `check` does the work."""

    name: str
    events: frozenset[str]
    kind: str
    check: Callable[[Event, Env], Verdict | None]
    applies: Callable[[Event], bool] = lambda event: True


@dataclass
class Outcome:
    """The merged verdicts of every rule that ran."""

    denials: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    updated_input: dict[str, Any] | None = None


def _log_failure(env: Env | None, event: Event, rule: str, error: BaseException) -> None:
    if env is None:
        return
    record = {
        "ts": clock.iso(env.now),
        "event": event.name,
        "rule": rule,
        "error": f"{type(error).__name__}: {error}",
        "trace": traceback.format_exc(limit=4),
    }
    with contextlib.suppress(OSError):
        jsonl.append(env.cfg.state_dir / "hook-errors.jsonl", record)


def evaluate(event: Event, rules: Iterable[Rule], env: Env) -> Outcome:
    """Run every rule for the event; a guard's crash becomes a refusal, a helper's is logged."""
    outcome = Outcome()
    for rule in rules:
        if event.name not in rule.events:
            continue
        # The class of the rule decides what a crash means.
        try:
            verdict = rule.check(event, env) if rule.applies(event) else None
        except Exception as error:  # noqa: BLE001
            _log_failure(env, event, rule.name, error)
            if rule.kind == GUARD:
                outcome.denials.append(f"bedrock guard '{rule.name}' could not verify: {error}")
            continue
        if verdict is not None:
            _merge(outcome, verdict)
    return outcome


def _merge(outcome: Outcome, verdict: Verdict) -> None:
    for text, bucket in (
        (verdict.deny, outcome.denials),
        (verdict.block, outcome.blocks),
        (verdict.context, outcome.contexts),
        (verdict.notice, outcome.notices),
    ):
        if text:
            bucket.append(text)
    if verdict.updated_input is not None:
        outcome.updated_input = verdict.updated_input


def answer(event_name: str, outcome: Outcome) -> dict[str, Any]:
    """Turn the outcome into the JSON Claude Code expects for this event."""
    result: dict[str, Any] = {}
    if outcome.notices:
        result["systemMessage"] = "\n".join(outcome.notices)
    context = "\n".join(outcome.contexts)
    if event_name == "PreToolUse":
        specific: dict[str, Any] = {"hookEventName": event_name}
        if outcome.denials:
            specific["permissionDecision"] = "deny"
            specific["permissionDecisionReason"] = "\n".join(outcome.denials)
        elif outcome.updated_input is not None:
            specific["updatedInput"] = outcome.updated_input
        if context:
            specific["additionalContext"] = context
        if len(specific) > 1:
            result["hookSpecificOutput"] = specific
        return result
    if outcome.blocks and event_name in ("Stop", "SubagentStop", "UserPromptSubmit"):
        result["decision"] = "block"
        result["reason"] = "\n".join(outcome.blocks)
    if context and event_name in CONTEXT_EVENTS:
        result["hookSpecificOutput"] = {"hookEventName": event_name, "additionalContext": context}
    return result


CONTEXT_EVENTS = {
    "UserPromptSubmit",
    "SessionStart",
    "PostToolUse",
    "SubagentStart",
    "Notification",
    "Stop",
    "SubagentStop",
}
