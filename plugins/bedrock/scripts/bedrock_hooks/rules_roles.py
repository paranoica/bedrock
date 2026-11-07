"""Point an agent spawn at the bedrock role that fits; never stops the spawn."""

from __future__ import annotations

from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict

AGENT_TOOLS = ("Agent", "Task")
ROLES = (
    "For an agent, take the bedrock role that fits: bedrock:inventory to read many files, "
    "bedrock:researcher for the web, bedrock:implementer for code with a ready test, "
    "bedrock:reviewer or bedrock:security-reviewer for a review, bedrock:verifier to re-check "
    "findings. general-purpose runs on the session's own model: keep it for work no role fits."
)


def hint(event: Event, env: Env) -> Verdict | None:
    """Name the roles when an agent starts as general-purpose; the spawn goes ahead as asked."""
    kind = str(event.tool_input.get("subagent_type") or "general-purpose")
    if kind != "general-purpose":
        return None
    return Verdict(context="bedrock: " + ROLES)


RULES = [
    Rule("agent-roles", frozenset({"PreToolUse"}), HELPER, hint, lambda e: e.tool in AGENT_TOOLS),
]
