"""MCP tools: writes need a grant; Slack messages are never sent by Claude (D044, D016)."""

from __future__ import annotations

import re

from bedrock_hooks import gate
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.gate import Action

SLACK_NEVER = {"slack_send_message", "slack_schedule_message"}
MCP_READ_VERBS = {"read", "get", "list", "search", "query", "fetch", "resolve", "lookup", "find"}
MCP_READ_VERBS |= {"view", "describe", "guide", "authenticate", "complete"}
MCP_ALLOWED = ("mcp__claude_ai_Claude_Docs__",)


def _mcp_action(tool: str) -> Action | None:
    if tool.startswith(MCP_ALLOWED):
        return None
    name = tool.rsplit("__", 1)[-1]
    words = {w.lower() for w in re.split(r"[_\-]|(?<=[a-z])(?=[A-Z])", name) if w}
    if words & MCP_READ_VERBS:
        return None
    lowered = tool.lower()
    if "slack" in lowered:
        kind = "slack-draft" if "draft" in words else "slack-write"
    elif any(key in lowered for key in ("atlassian", "jira", "linear")):
        kind = "tracker"
    else:
        kind = "mcp-write"
    return Action(kind, f"the outward tool {name}")


def check_mcp(event: Event, env: Env) -> Verdict | None:
    """MCP writes need a grant; Slack messages are never sent by Claude (drafts only)."""
    name = event.tool.rsplit("__", 1)[-1]
    if "slack" in event.tool.lower() and name in SLACK_NEVER:
        return Verdict(
            deny="Claude never sends Slack messages (they are labelled as sent by Claude); write "
            "the text in the chat for the owner to send, or a draft on their word (D044)."
        )
    action = _mcp_action(event.tool)
    if action is None:
        return None
    if event.agent_id:
        return Verdict(deny=f"refused for an agent: {action.why}; agents never act outward (D005).")
    return gate.decide(env, event, [action])


RULES = [
    Rule("mcp", frozenset({"PreToolUse"}), GUARD, check_mcp, lambda e: e.tool.startswith("mcp__"))
]
