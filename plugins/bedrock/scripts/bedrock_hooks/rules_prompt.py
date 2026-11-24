"""The owner's prompt: the question log and the humanize trigger."""

from __future__ import annotations

import re

from bedrock_lib import agents, humanize, questions

from bedrock_hooks import draft_trigger
from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict

OWNER_SOURCES = {"user", ""}
QUESTION_START = re.compile(
    r"^(?:как|что|где|почему|зачем|когда|какой|какая|какие|каким|кто|сколько|можно ли|есть ли"
    r"|how|what|where|why|when|which|who|can|does|do|is|are)\b",
    re.I,
)
BUNDLED_HUMANIZE = draft_trigger.context(
    "bedrock:humanize",
    "the skill bundled with the bedrock plugin",
    "humanize, not anthropic-skills:humanize",
)


def _owner(event: Event) -> bool:
    return str(event.data.get("source") or "") in OWNER_SOURCES


def _text(event: Event) -> str:
    return draft_trigger.own_words(str(event.data.get("prompt") or "")).strip()


def _is_question(text: str) -> bool:
    return text.rstrip().endswith("?") or bool(QUESTION_START.match(text.strip()))


def log_question(event: Event, env: Env) -> Verdict | None:
    """Log the owner's questions; bring earlier answers to similar ones, to be re-verified."""
    text = _text(event)
    if not _owner(event) or not text or not _is_question(text):
        return None
    hits = questions.similar(env.cfg, env.project_name, text, limit=3)
    questions.log_question(env.cfg, env.project_name, text, session=event.session, now=env.now)
    answered = [hit.record for hit in hits if hit.record.get("answer")]
    if not answered:
        return None
    lines = [
        f"- {r['ts'][:10]}: {r['question']} -> {r['answer']} (source: {r.get('source', '?')})"
        for r in answered
    ]
    return Verdict(
        context="This was asked before; re-verify before reusing the answer (D058):\n"
        + "\n".join(lines)
    )


def trigger_humanize(event: Event, env: Env) -> Verdict | None:
    """Point a request for a message the owner will send at the bundled humanize skill.

    When the personal hook is installed it gives the same hint for the personal skill, so
    this one stays silent and the hint never comes twice.
    """
    prompt = str(event.data.get("prompt") or "")
    if not _owner(event) or not draft_trigger.wants_message(prompt):
        return None
    if humanize.personal_hook(agents.claude_dir(env.environ)):
        return None
    return Verdict(context=BUNDLED_HUMANIZE)


EVENTS = frozenset({"UserPromptSubmit"})
RULES = [
    Rule("question-log", EVENTS, HELPER, log_question),
    Rule("humanize-trigger", EVENTS, HELPER, trigger_humanize),
]
