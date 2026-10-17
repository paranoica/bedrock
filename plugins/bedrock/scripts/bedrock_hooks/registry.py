"""Every rule bedrock runs, in order: guards before helpers."""

from __future__ import annotations

from bedrock_hooks import (
    rules_after,
    rules_agents,
    rules_bench,
    rules_control,
    rules_git,
    rules_heavy,
    rules_installs,
    rules_kb,
    rules_mcp,
    rules_outward,
    rules_prompt,
    rules_secrets,
    rules_session,
)
from bedrock_hooks.core import Rule

RULES: list[Rule] = [
    *rules_control.RULES,
    *rules_secrets.RULES,
    *rules_bench.RULES,
    *rules_git.RULES,
    *rules_outward.RULES,
    *rules_installs.RULES,
    *rules_mcp.RULES,
    *rules_heavy.RULES,
    *rules_prompt.RULES,
    *rules_agents.RULES,
    *rules_after.RULES,
    *rules_session.RULES,
    *rules_kb.RULES,
]
