"""The owner's prompt: grants and modes from their own words, the question log, turn timing."""

from __future__ import annotations

import re

from bedrock_lib import clock, questions, session, spend

from bedrock_hooks import grants
from bedrock_hooks.core import HELPER, Env, Event, Rule, Verdict

OWNER_SOURCES = {"user", ""}
SPEND = (
    ("max", re.compile(r"до талого|не экономь|тратим|spend (?:on|max)|no limits today", re.I)),
    ("save", re.compile(r"\bэкономим\b|\bэкономь\b|save mode|save tokens", re.I)),
    ("normal", re.compile(r"обычный режим|normal mode", re.I)),
)
QUESTION_START = re.compile(
    r"^(?:как|что|где|почему|зачем|когда|какой|какая|какие|каким|кто|сколько|можно ли|есть ли"
    r"|how|what|where|why|when|which|who|can|does|do|is|are)\b",
    re.I,
)
SPEND_QUESTION_AT = 80.0


def _owner(event: Event) -> bool:
    return str(event.data.get("source") or "") in OWNER_SOURCES


def _text(event: Event) -> str:
    return grants.QUOTED.sub(" ", str(event.data.get("prompt") or "")).strip()


def record_grants(event: Event, env: Env) -> Verdict | None:
    """Store grants and revocations from the owner's own words, and tell the owner."""
    if not _owner(event):
        return None
    prompt = str(event.data.get("prompt") or "")
    project = env.project_name
    if grants.wants_revoke(prompt):
        grants.revoke(env.cfg, project)
        return Verdict(notice=f"bedrock: all grants for {project} revoked.")
    transcript = str(event.data.get("transcript_path") or "")
    found = grants.from_prompt(prompt, project, env.now, env.cfg, transcript)
    if not found:
        return None
    grants.record(env.cfg, found)
    listed = "; ".join(grants.describe(grant, env.cfg) for grant in found)
    return Verdict(
        notice=f"bedrock: grant from your words: {listed}.", context=f"Granted: {listed}."
    )


def switch_spend(event: Event, env: Env) -> Verdict | None:
    """Set the spend mode when the owner names one."""
    if not _owner(event):
        return None
    text = _text(event)
    for mode, pattern in SPEND:
        if pattern.search(text):
            until = spend.choose(env.cfg, mode, env.now)
            local = clock.in_zone(clock.parse(until), env.cfg.display_tz).strftime("%H:%M")
            return Verdict(notice=f"bedrock: spend mode {mode} until {local}.")
    return None


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


def mark_turn(event: Event, env: Env) -> Verdict | None:
    """Remember when the turn started (long tasks notify the owner when they finish)."""
    if event.session:
        session.update(env.cfg, event.session, {"turn_started": clock.iso(env.now)})
    return None


def spend_question(event: Event, env: Env) -> Verdict | None:
    """At 80% of the 5-hour window, ask once per window: spend on or save (D006)."""
    if spend.used(env.cfg, "five_hour") < SPEND_QUESTION_AT or spend.current(env.cfg, env.now):
        return None
    percent = round(spend.used(env.cfg, "five_hour"))
    return Verdict(
        context=f"The 5-hour window is at {percent}%. Before more agent work, ask the owner with "
        "the question buttons: spend or save? No answer means save (D006, D009)."
    )


EVENTS = frozenset({"UserPromptSubmit"})
RULES = [
    Rule("grants", EVENTS, HELPER, record_grants),
    Rule("spend-mode", EVENTS, HELPER, switch_spend),
    Rule("question-log", EVENTS, HELPER, log_question),
    Rule("turn-start", EVENTS, HELPER, mark_turn),
    Rule("spend-question", EVENTS, HELPER, spend_question),
]
