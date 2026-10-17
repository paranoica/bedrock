"""Mechanical tells in text meant for people: dashes, filler phrases, markdown Slack shows raw.

The `humanize` skill does the rewriting; this only finds what a rule can find, so the model
never has to be trusted on "no dashes left".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DASH = re.compile("[\u2014\u2013]")
FILLER = re.compile(
    r"\b(?:стоит отметить|важно отметить|следует отметить|надеюсь, это поможет|"
    r"в современном мире|давайте разберёмся|давайте разберемся|не стесняйтесь|"
    r"отличный вопрос|безусловно,|в заключение,|"
    r"it'?s worth noting|it is worth noting|i hope this helps|delve|in today'?s fast-paced|"
    r"great question|certainly!|feel free to|let me know if you have any (?:other )?questions|"
    r"seamless(?:ly)?|game[- ]changer|in conclusion,)(?!\w)",
    re.IGNORECASE,
)
SLACK_MARKDOWN = (
    (re.compile(r"^#{1,6}\s"), "a # heading shows as text: use a *bold* line"),
    (re.compile(r"\*\*[^*]+\*\*"), "**double** shows raw: Slack bold is *single*"),
    (re.compile(r"^>\s?"), "a > quote renders as a bar and pastes badly: drop it"),
    (re.compile(r"\[[^\]]+\]\([^)]+\)"), "[text](url) shows raw: paste the bare link"),
)
FENCE = re.compile(r"^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$", re.MULTILINE | re.DOTALL)
CODE = re.compile(r"`[^`\n]+`")


@dataclass(frozen=True)
class Finding:
    """One tell: the line, the rule and how to fix it."""

    line: int
    rule: str
    message: str


def _blank_code(text: str) -> str:
    """Replace code with spaces, keeping line numbers."""
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return CODE.sub(lambda m: " " * len(m.group(0)), text)


def check(text: str, *, slack: bool = False) -> list[Finding]:
    """Return every tell in the text; code spans and fenced blocks are skipped."""
    found = []
    plain = _blank_code(text).replace("\u2019", "'")
    for number, line in enumerate(plain.splitlines(), start=1):
        if DASH.search(line):
            found.append(Finding(number, "dash", "a dash: split the sentence or use a comma"))
        if match := FILLER.search(line):
            found.append(Finding(number, "filler", f"filler '{match.group(0)}': cut it"))
        if slack:
            found += [
                Finding(number, "markdown", message)
                for pattern, message in SLACK_MARKDOWN
                if pattern.search(line)
            ]
    return found
