#!/usr/bin/env python3
"""Converts standard markdown to Slack mrkdwn.

A last pass for a draft written in markdown out of habit. Only unambiguous cases are
rewritten; single-asterisk italics are left alone because Slack reads them as bold.

    **bold** / __bold__    -> *bold*
    # heading              -> *heading*
    [text](url)            -> <url|text>
    ~~strike~~             -> ~strike~
    "- " / "* " bullets    -> "• "
    "> " quotes            -> unwrapped
    code                   -> untouched

Usage:
    python3 to_slack.py < draft.txt
    python3 to_slack.py "text"
"""

from __future__ import annotations

import re
import sys

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`\n]+`")
_PLACEHOLDER = re.compile(r"\x00(\d+)\x00")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_BULLET = re.compile(r"^(\s*)[-*]\s+(?!\*)(.*)$")


def to_slack(text: str) -> str:
    """Rewrites markdown constructs Slack would show as literal symbols."""
    code: list[str] = []

    def stash(match: re.Match[str]) -> str:
        code.append(match.group(0))
        return f"\x00{len(code) - 1}\x00"

    text = _INLINE.sub(stash, _FENCE.sub(stash, text))
    text = _LINK.sub(r"<\2|\1>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)

    lines = []
    for line in text.split("\n"):
        if m := _HEADING.match(line):
            lines.append(f"*{m.group(1).strip()}*" if m.group(1).strip() else "")
        elif m := _QUOTE.match(line):
            lines.append(m.group(1))
        elif m := _BULLET.match(line):
            lines.append(f"{m.group(1)}• {m.group(2)}")
        else:
            lines.append(line)
    return _PLACEHOLDER.sub(lambda m: code[int(m.group(1))], "\n".join(lines))


def main() -> None:
    src = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    sys.stdout.write(to_slack(src))


if __name__ == "__main__":
    main()
