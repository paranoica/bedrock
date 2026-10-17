"""Grants: the owner's word for outward or irreversible actions (D016).

Written only from the owner's own prompt by the UserPromptSubmit hook; Claude cannot grant itself.
Quoted, pasted and fenced text never grants anything, and a negation or a question cancels a verb.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import tempfile
from collections.abc import Iterator
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from bedrock_lib import clock
from bedrock_lib.config import UserConfig

from bedrock_hooks.grant_words import (
    PHRASES,
    PROD,
    SINGLE_USE_HOURS,
    expiry,
    nothing_else,
    only_the_grant,
)

NOT_UNDER_ALL_OUT = {"deploy-prod", "message"}
LEVEL4 = {"force-push", "delete-remote-branch", "history-rewrite", "destructive-git", "data-delete"}
ALLOW = re.compile(r"^/bedrock:allow\s+([\w-]+)(?:\s+(?!(?:until|до)\b)(\S+))?(.*)$", re.MULTILINE)
COMMAND = re.compile(
    r"<command-name>(/[^<]+)</command-name>(?:\s*<command-args>(.*?)</command-args>)?", re.S
)
UNLEASH = re.compile(r"^/bedrock:unleash\b(.*)$", re.MULTILINE)
REVOKE = re.compile(r"^/bedrock:revoke\b", re.MULTILINE)
OVERRIDE = re.compile(r"^\s*разрешаю:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
REMOTE_BRANCH = r"удалить (?:удал[её]нную )?ветку|delete (?:the )?remote branch"
OVERRIDE_ACTIONS = (
    (re.compile(r"форс[- ]?пуш|force[- ]?push", re.I), "force-push"),
    (re.compile(REMOTE_BRANCH, re.I), "delete-remote-branch"),
    (re.compile(r"переписать историю|rewrite history", re.I), "history-rewrite"),
    (re.compile(r"\b(?:удалить|drop|delete)\b", re.I), "data-delete"),
)
QUOTED = re.compile(
    r"<pasted_content[^>]*>.*?</pasted_content>|```.*?```|^>.*$|«[^»\n]*»|„[^“\n]*“|\"[^\"\n]*\"",
    re.S | re.M,
)


@dataclass(frozen=True)
class Grant:
    """One permission: what, where, which target, until when, how many uses (None: no limit)."""

    action: str
    project: str
    expires: str
    target: str | None = None
    uses: int | None = 1
    level4: bool = False
    all_out: bool = False
    source: str = ""
    transcript: str = ""
    created: str = ""


def _own_words(prompt: str) -> str:
    return QUOTED.sub(" ", prompt)


def normal(text: str) -> str:
    """The owner's own words in a comparable form: quotes cut, lower case, spaces collapsed."""
    return " ".join(_own_words(text).lower().split())


def _phrase_grants(text: str, project: str, now: datetime, cfg: UserConfig) -> list[Grant]:
    # A lost grant costs one `/bedrock:allow`; a wrong one cannot be undone. So the words grant
    # only when they hold nothing but the grant: a negation, a question, a condition or an
    # aside is a word outside the list, and voids them.
    lowered = text.lower()
    if not only_the_grant(text):
        return []
    expires, uses = expiry(lowered, cfg, now)
    found: dict[str, Grant] = {}
    for action, pattern in PHRASES.items():
        if re.search(pattern, lowered, re.MULTILINE):
            name = "deploy-prod" if action == "deploy" and PROD.search(lowered) else action
            found[name] = Grant(
                name, project, clock.iso(expires), uses=uses, source=normal(text)[:120]
            )
    return list(found.values())


def _command_grants(text: str, project: str, now: datetime, cfg: UserConfig) -> list[Grant]:
    found = []
    for match in ALLOW.finditer(text):
        action, target, rest = match.group(1), match.group(2), match.group(3)
        if not nothing_else(rest, []):
            continue
        expires, uses = expiry(rest.lower(), cfg, now)
        found.append(
            Grant(
                action,
                project,
                clock.iso(expires),
                target,
                uses,
                action in LEVEL4,
                False,
                normal(match.group(0)),
            )
        )
    for match in UNLEASH.finditer(text):
        if not nothing_else(match.group(1), []):
            continue
        expires, _ = expiry(match.group(1).lower(), cfg, now)
        found.append(
            Grant(
                "*",
                project,
                clock.iso(expires),
                uses=None,
                level4=True,
                all_out=True,
                source=normal(match.group(0)),
            )
        )
    for match in OVERRIDE.finditer(text):
        wording = match.group(1).strip()
        found_action = next(((p, n) for p, n in OVERRIDE_ACTIONS if p.search(wording)), None)
        if found_action:
            pattern, action = found_action
            target = wording.split()[-1] if len(wording.split()) > 1 else None
            rest = pattern.sub(" ", wording)
            rest = rest.rsplit(target, 1)[0] if target and target in rest else rest
            if not nothing_else(rest, [r"\b(?:на|в|to|on|into|для|for)\b"]):
                continue
            expires = clock.iso(now + timedelta(hours=SINGLE_USE_HOURS))
            found.append(
                Grant(action, project, expires, target, 1, True, False, normal(wording)[:120])
            )
    return found


def from_prompt(
    prompt: str, project: str, now: datetime, cfg: UserConfig, transcript: str = ""
) -> list[Grant]:
    """Read the grants in one owner prompt; `transcript` is where that prompt is recorded."""
    text = _own_words(prompt)
    found = _command_grants(text, project, now, cfg)
    if not found and not OVERRIDE.search(text):
        found = _phrase_grants(text, project, now, cfg)
    return [replace(g, transcript=transcript, created=clock.iso(now)) for g in found]


def _owner_texts(transcript: str) -> Iterator[str]:
    """The text of every message the owner typed in a session transcript."""
    path = Path(transcript)
    if not transcript or not path.is_file():
        return
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if '"user"' not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = record.get("message") or {}
            if record.get("type") != "user" or record.get("isMeta") or "toolUseResult" in record:
                continue
            if record.get("isCompactSummary") or record.get("isVisibleInTranscriptOnly"):
                continue
            origin = record.get("origin")
            if isinstance(origin, dict) and origin.get("kind") != "human":
                continue
            content = message.get("content") if message.get("role") == "user" else None
            if isinstance(content, str):
                yield _typed(content)
            elif (
                isinstance(content, list)
                and content
                and all(isinstance(b, dict) and b.get("type") == "text" for b in content)
            ):
                yield "\n".join(str(b.get("text", "")) for b in content)


def _typed(content: str) -> str:
    """A slash command as the owner typed it; Claude Code records it as tags.

    Only a record that is the command itself counts, never tags quoted inside other text.
    """
    if content.lstrip().startswith(("<command-message>", "<command-name>")) and (
        match := COMMAND.search(content)
    ):
        return f"{match.group(1)} {match.group(2) or ''}".strip()
    return content


def _same(stored: Grant, derived: Grant) -> bool:
    fields = ("action", "project", "target", "expires", "level4", "all_out")
    if any(getattr(stored, f) != getattr(derived, f) for f in fields):
        return False
    return derived.uses is None or (stored.uses is not None and stored.uses <= derived.uses)


def backed(grant: Grant, cfg: UserConfig) -> bool:
    """True when the owner's own message gives exactly this grant, or a use-limited part of it.

    The message is read again as of the moment the grant was made.

    A grant written or widened by anything but the owner's prompt has no such message.
    """
    if not grant.source or not grant.created:
        return False
    created = clock.parse(grant.created)
    for text in _owner_texts(grant.transcript):
        if grant.source not in normal(text):
            continue
        if any(_same(grant, d) for d in from_prompt(text, grant.project, created, cfg)):
            return True
    return False


def wants_revoke(prompt: str) -> bool:
    """True when the owner asks to drop all grants."""
    return bool(REVOKE.search(_own_words(prompt)))


def _path(cfg: UserConfig) -> Path:
    return cfg.state_dir / "grants.json"


def _edit(cfg: UserConfig, change: Any) -> Any:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    with (cfg.state_dir / "grants.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            stored = json.loads(_path(cfg).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            stored = []
        items = [Grant(**item) for item in stored if isinstance(item, dict)]
        items, result = change(items)
        # A unique name: a sandbox may leave a read-only file at any fixed path it was told to deny.
        handle, name = tempfile.mkstemp(dir=cfg.state_dir, prefix="grants.", suffix=".part")
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(json.dumps([asdict(g) for g in items], ensure_ascii=False))
        Path(name).replace(_path(cfg))
    return result


def record(cfg: UserConfig, new: list[Grant]) -> None:
    """Store grants."""
    if new:
        _edit(cfg, lambda items: ([*items, *new], None))


def revoke(cfg: UserConfig, project: str) -> None:
    """Drop every grant of a project."""
    _edit(cfg, lambda items: ([g for g in items if g.project != project], None))


def _covers(grant: Grant, action: str, project: str, target: str | None, now: datetime) -> bool:
    if grant.project != project or clock.parse(grant.expires) <= now:
        return False
    if grant.all_out:
        return action not in NOT_UNDER_ALL_OUT
    if grant.action != action:
        return False
    return grant.target is None or grant.target == target


def consume(
    cfg: UserConfig, action: str, project: str, target: str | None, now: datetime
) -> Grant | None:
    """Use a grant covering the action; a single-use grant is spent. None: no grant."""

    def change(items: list[Grant]) -> tuple[list[Grant], Grant | None]:
        live = [g for g in items if clock.parse(g.expires) > now and g.uses != 0]
        for index, grant in enumerate(live):
            if _covers(grant, action, project, target, now) and backed(grant, cfg):
                if grant.uses is not None:
                    live[index] = Grant(**{**asdict(grant), "uses": grant.uses - 1})
                return [g for g in live if g.uses != 0], grant
        return live, None

    return _edit(cfg, change)


def available(
    cfg: UserConfig, action: str, project: str, target: str | None, now: datetime
) -> Grant | None:
    """Return a grant covering the action without using it up."""
    try:
        stored = json.loads(_path(cfg).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    for item in stored:
        grant = Grant(**item)
        if grant.uses != 0 and _covers(grant, action, project, target, now) and backed(grant, cfg):
            return grant
    return None


def describe(grant: Grant, cfg: UserConfig) -> str:
    """One line for the owner: what was granted and until when."""
    until = clock.in_zone(clock.parse(grant.expires), cfg.display_tz).strftime("%H:%M")
    what = "everything except production and messages" if grant.all_out else grant.action
    target = f" {grant.target}" if grant.target else ""
    count = "once" if grant.uses == 1 else "no limit"
    return f"{what}{target} ({count}, until {until})"
