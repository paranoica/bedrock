#!/usr/bin/env python3
"""Finds the owner's real replies to messages like the one being answered.

The static bank in examples.md shows the register in general; this shows how the owner
answered something close to this exact message. Matching is plain word overlap with crude
stemming and IDF weights, standard library only.

Usage:
    python3 similar.py --register NAME [--k 12] [--profile DIR] < incoming.txt
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))

import profilelib
import textmetrics as tm

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = profilelib.default_profile_dir(SKILL_DIR)
STEM = 5


def tokens(text: str) -> set[str]:
    """Lowercased word stems (first five letters), stop words dropped."""
    return {w.lower()[:STEM] for w in tm.words(text) if w.lower() not in tm.STOPWORDS}


def load_pool(path: Path) -> list[dict[str, list[str]]]:
    """Reads pairs.jsonl: one {"in": [...], "out": [...]} per line."""
    pool = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            if item.get("in") and item.get("out"):
                pool.append(item)
    return pool


def rank(incoming: str, pool: list[dict[str, list[str]]], k: int, seed: int = 0) -> list[dict]:
    """Returns the ``k`` pairs whose incoming side shares the rarest words with ``incoming``.

    Pairs with no shared word are used only to fill up, in a fixed random order, so the
    answer always has ``k`` examples when the pool allows.
    """
    query = tokens(incoming)
    docs = [tokens(" ".join(p["in"])) for p in pool]
    df = Counter(t for d in docs for t in d)
    n = len(pool) or 1
    idf = {t: math.log(1 + n / df[t]) for t in df}
    scored = []
    for i, d in enumerate(docs):
        shared = query & d
        if shared:
            # Long contexts share words by chance; dampen by their size.
            score = sum(idf[t] for t in shared) / math.sqrt(len(d))
            scored.append((score, i))
    scored.sort(key=lambda s: (-s[0], s[1]))
    chosen = [i for _, i in scored[:k]]
    if len(chosen) < k:
        taken = set(chosen)
        rest = [i for i in range(len(pool)) if i not in taken]
        random.Random(seed).shuffle(rest)
        chosen += rest[: k - len(chosen)]
    return [pool[i] for i in chosen]


def typical(pairs: list[dict]) -> tuple[int, int]:
    """Median words and messages of the owner's replies in ``pairs``; ``(0, 0)`` if none."""
    if not pairs:
        return 0, 0
    words = [len(tm.words(" ".join(p["out"]))) for p in pairs]
    return round(median(words)), round(median(len(p["out"]) for p in pairs))


def _ru_plural(n: int, forms: tuple[str, str, str]) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return forms[1]
    return forms[2]


def render(pairs: list[dict], lang: str) -> str:
    """Formats pairs like examples.md: incoming lines, then the reply, one message per line."""
    incoming, reply = ("Входящее:", "Ответ:") if lang == "ru" else ("Incoming:", "Reply:")
    out = []
    for i, p in enumerate(pairs, start=1):
        out.append(f"## {i}")
        out.append(incoming)
        out.extend("  " + line for t in p["in"] for line in t.splitlines())
        out.append(reply)
        out.extend("  " + line for t in p["out"] for line in t.splitlines())
        out.append("")
    words, messages = typical(pairs)
    if pairs and lang == "ru":
        w = _ru_plural(words, ("слово", "слова", "слов"))
        m = _ru_plural(messages, ("сообщение", "сообщения", "сообщений"))
        out.append(
            f"Обычно на похожее ты отвечаешь так: {words} {w}, {messages} {m} "
            "(медиана ответов выше)."
        )
    elif pairs:
        out.append(
            f"Typical reply to messages like this: {words} words, {messages} messages "
            "(median of the replies above)."
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show the owner's replies to similar messages.")
    parser.add_argument("--register", required=True)
    parser.add_argument("--k", type=int, default=12)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("file", nargs="?", type=Path, help="incoming text; stdin if omitted")
    args = parser.parse_args(argv)
    path = args.profile / "registers" / args.register / "pairs.jsonl"
    if not path.is_file():
        print(f"similar: no pairs for register {args.register!r} at {path}", file=sys.stderr)
        return 2
    try:
        incoming = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"similar: cannot read the incoming text: {exc}", file=sys.stderr)
        return 2
    pool = load_pool(path)
    lang = tm.detect_lang(" ".join(t for p in pool[:50] for t in p["out"]))
    print(render(rank(incoming, pool, args.k), lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
