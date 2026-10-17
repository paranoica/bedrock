"""The words of a grant: phrases, end times and environments (D016).

A message grants only when it holds nothing else.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta

from bedrock_lib import clock
from bedrock_lib.config import UserConfig

SINGLE_USE_HOURS = 2
PHRASES = {
    "push": r"(?:за)?пуш(?:ь|ни|ните|ай)\b|пушить можно|(?:можешь|можно) (?:за)?пушить"
    r"|\bpush (?:it|this|that|them|the branch|the changes|changes)\b|\bgo ahead(?: and|,)? push\b"
    r"|\byou can push\b|\bplease push\b|^push\b",
    "merge": r"(?:с|за)?мерж(?:ь|ни|и|ите)\b|(?:можешь|можно) (?:с|за)?мерж\w*|мержить можно"
    r"|(?:пушить )?\bи (?:с|за)?мержить\b"
    r"|\bmerge (?:it|this|that|the pr)\b|\byou can merge\b|^merge\b",
    "pr": r"(?:открой|создай|сделай|заведи) (?:pr|пр|пулл? ?реквест)\b"
    r"|\b(?:open|create) (?:a |the )?(?:pr|pull request)\b",
    "deploy": r"(?:за)?деплой(?:ни|те)?\b|(?:можешь|можно) (?:за)?деплоить|деплоить можно"
    r"|\bdeploy (?:it|this|to \w+)\b"
    r"|\byou can deploy\b",
}
PROD = re.compile(r"прод\b|продакш[еэ]?н\w*|\bproduction\b|\bprod\b", re.IGNORECASE)
UNTIL_PLAN = re.compile(r"до конца (?:плана|блока)|until the end of the plan|end of (?:the )?plan")
UNTIL_DAY = re.compile(r"на сегодня|на весь день|до конца дня|\btoday\b|for the day")
UNTIL_TIME = re.compile(r"(?:до|until)\s+(\d{1,2})(?::(\d{2}))?\b")
UNTIL_MORNING = re.compile(r"до утра|until (?:the )?morning")
MORNING_HOUR = 12  # the night mode ends at noon local (D046)
# A phrase grant needs a message made of nothing but the grant: the phrase, its end time, its
# environment and these few words. Anything else (a take-back, a condition, a joke, a stray
# letter) and the words grant nothing; `/bedrock:allow` is the exact way.
FILLER = {
    "ок",
    "окей",
    "ok",
    "okay",
    "давай",
    "да",
    "yes",
    "и",
    "and",
    "go",
    "ahead",
    "please",
    "пожалуйста",
    "это",
    "его",
    "их",
    "it",
    "this",
    "that",
    "them",
    "сейчас",
    "now",
    "автономно",
    "можно",
    "можешь",
    "you",
    "can",
    "ну",
    "the",
    "a",
    "pr",
    "пр",
    "ветку",
    "branch",
    "закоммить",
    "изменения",
    "спасибо",
    "thanks",
    "утра",  # «до 7 утра» is 07:00; «вечера» stays out, the time would read as 07:00
}
ENVIRONMENT = re.compile(
    r"\b(?:на|в|to|on)\s+(?:дев\w*|прод\w*|стейдж\w*|staging|production|prod|dev)\b"
    r"|\b(?:прод|prod|production)\b"
)
LEFTOVER = re.compile(r"[^\w\s.,!:;]|\w+")


def _clock_time(cfg: UserConfig, now: datetime, hour: int, minute: int) -> datetime:
    local = clock.in_zone(now, cfg.display_tz)
    target = datetime.combine(local.date(), time(hour % 24, minute), tzinfo=local.tzinfo)
    if target <= local:
        target += timedelta(days=1)
    return target


def _end_of_day(cfg: UserConfig, now: datetime) -> datetime:
    return _clock_time(cfg, now, cfg.rollover_hour, 0)


def expiry(text: str, cfg: UserConfig, now: datetime) -> tuple[datetime, int | None]:
    """Return when a grant from this text ends and how many uses it has."""
    if match := UNTIL_TIME.search(text):
        return _clock_time(cfg, now, int(match.group(1)), int(match.group(2) or 0)), None
    if UNTIL_MORNING.search(text):
        return _clock_time(cfg, now, MORNING_HOUR, 0), None
    if UNTIL_PLAN.search(text) or UNTIL_DAY.search(text):
        return _end_of_day(cfg, now), None
    return now + timedelta(hours=SINGLE_USE_HOURS), 1


def _valid_time(match: re.Match[str]) -> str:
    hour, minute = int(match.group(1)), int(match.group(2) or 0)
    return " " if hour < 24 and minute < 60 else match.group(0)


def nothing_else(text: str, patterns: list[str]) -> bool:
    """True when the text holds nothing the owner might mean beside the grant.

    Allowed: what the patterns match, valid end times, environments and filler words.
    """
    rest = UNTIL_TIME.sub(_valid_time, text.lower())
    for pattern in [*patterns, UNTIL_MORNING.pattern, UNTIL_PLAN.pattern, UNTIL_DAY.pattern]:
        rest = re.sub(pattern, " ", rest, flags=re.MULTILINE)
    rest = ENVIRONMENT.sub(" ", rest)
    return all(token in FILLER for token in LEFTOVER.findall(rest))


def only_the_grant(text: str) -> bool:
    """True when the message holds a grant phrase and nothing the owner might mean beside it."""
    return nothing_else(text, list(PHRASES.values()))
