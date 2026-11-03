"""Every rule bedrock runs, in order: the review gate before the helpers."""

from __future__ import annotations

from bedrock_hooks import rules_after, rules_kb, rules_prompt, rules_review, rules_session
from bedrock_hooks.core import Rule

RULES: list[Rule] = [
    *rules_review.RULES,
    *rules_prompt.RULES,
    *rules_after.RULES,
    *rules_session.RULES,
    *rules_kb.RULES,
]
