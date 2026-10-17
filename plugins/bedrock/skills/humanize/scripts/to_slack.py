#!/usr/bin/env python3
"""
to_slack.py — sanitize standard-markdown text into Slack mrkdwn.

Safety net for when a draft was written in normal markdown out of habit. It fixes the
unambiguous, high-value cases only. It does NOT try to guess single-asterisk italic
(ambiguous in Slack, where a single asterisk means bold), so write mrkdwn directly and use
this as a last pass.

What it does:
  **bold** / __bold__            -> *bold*
  # / ## / ### heading           -> *heading*   (bold line, hashes removed)
  [text](url)                    -> <url|text>
  ~~strike~~                     -> ~strike~
  leading "- " / "* " bullet     -> "• "
  leading "> " blockquote        -> unwrapped (bar removed)
  code fences (``` ... ```)      -> left untouched (real code should stay a block)

Usage:
  python3 to_slack.py < input.txt
  echo "text" | python3 to_slack.py
  python3 to_slack.py "text as an argument"
"""

import re
import sys


def _protect_code(text):
    """Pull fenced and inline code out so we never rewrite inside them."""
    blocks = []

    def stash(m):
        blocks.append(m.group(0))
        return f"\x00{len(blocks) - 1}\x00"

    text = re.sub(r"```.*?```", stash, text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", stash, text)
    return text, blocks


def _restore_code(text, blocks):
    def unstash(m):
        return blocks[int(m.group(1))]

    return re.sub(r"\x00(\d+)\x00", unstash, text)


def to_slack(text):
    text, code = _protect_code(text)

    # Links [text](url) -> <url|text>  (before bold, so brackets are clean)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"<\2|\1>", text)

    # Bold: **x** and __x__ -> *x*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)

    # Strikethrough: ~~x~~ -> ~x~
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)

    out_lines = []
    for line in text.split("\n"):
        # Headings -> bold line
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            content = m.group(1).strip()
            out_lines.append(f"*{content}*" if content else "")
            continue

        # Blockquote -> unwrap (drop the vertical bar)
        mq = re.match(r"^\s*>\s?(.*)$", line)
        if mq:
            out_lines.append(mq.group(1))
            continue

        # Bullets "- " or "* " (not "**") -> "• "
        mb = re.match(r"^(\s*)([-*])\s+(?!\*)(.*)$", line)
        if mb:
            indent, _, rest = mb.groups()
            out_lines.append(f"{indent}• {rest}")
            continue

        out_lines.append(line)

    text = "\n".join(out_lines)
    text = _restore_code(text, code)
    return text


def main():
    if len(sys.argv) > 1:
        src = " ".join(sys.argv[1:])
    else:
        src = sys.stdin.read()
    sys.stdout.write(to_slack(src))


if __name__ == "__main__":
    main()
