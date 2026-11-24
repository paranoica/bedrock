#!/usr/bin/env python3
"""Checks a draft against the owner's profile before it is handed over.

Errors are hard bans (``ё`` when the owner never types it, dashes, stop-list phrases,
contractions the owner avoids, markdown that leaks into chat). Warnings compare the
draft with the register's p90: more commas or words than the owner almost ever uses.
Both mean "rewrite and lint again".

Usage:
    python3 lint.py [--register NAME] [--platform slack] [--mode chat|doc] [FILE] < draft

Exit codes: 0 clean, 1 issues found, 2 usage or profile error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import profilelib
import similar
import textmetrics as tm

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = profilelib.default_profile_dir(SKILL_DIR)
BUILTIN_STOPLIST = SKILL_DIR / "references" / "stoplist.txt"

_NORMALISE_DROP = re.compile(r"[,;:«»\"“”]")
_SPACES = re.compile(r"\s+")
_MD_LINK = re.compile(r"\[[^\]\n]+\]\([^)\s]+\)")
_EMPHASIS = re.compile(r"(?<![\w*])\*(?!\s)[^*\n]+(?<!\s)\*(?![\w*])")
_CONTRACTION = re.compile(r"\b[^\W\d_]+['’][^\W\d_]+\b")
_CONTRAST_RU = re.compile(
    r"(?<![а-яё])(?:"
    r"не\s+(?:в|про|о|об)\s+[^,.!?\n]{1,40},\s*(?:а|это)\s+(?:в|про|о|об)\s"
    r"|не\s+потому\s+что\s+[^,.!?\n]{1,60},\s*а\s+потому\s+что"
    r"|не\s+просто\s+[^,.!?\n]{1,40},\s*а\s"
    r")",
    re.IGNORECASE,
)
_CONTRAST_EN = re.compile(
    r"\b(?:it'?s|it is|this is|that'?s)\s+not\s+[^,.;!?\n]{1,40}[,;.]\s*"
    r"(?:it'?s|it is|this is|that'?s)\b"
    r"|\bnot\s+(?:just|only|because)\s+[^,.;!?\n]{1,60},\s*but\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    """One problem in the draft."""

    level: str
    code: str
    message: str


def normalise(text: str) -> str:
    """Lowercases, maps ``ё`` to ``е``, drops commas and quotes, collapses whitespace."""
    text = _NORMALISE_DROP.sub(" ", text.lower().replace("ё", "е").replace("’", "'"))
    return _SPACES.sub(" ", text).strip()


def load_stoplist(path: Path = BUILTIN_STOPLIST) -> list[str]:
    """Reads the built-in phrase list; section headers and comments are skipped."""
    if not path.exists():
        return []
    phrases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "[")):
            phrases.append(line)
    return phrases


def split_messages(text: str) -> list[str]:
    """Each non-empty line is one chat message."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _stoplist_hits(text: str, phrases: list[str]) -> list[str]:
    norm = f" {normalise(text)} "
    hits = []
    for phrase in phrases:
        p = normalise(phrase)
        if p and re.search(rf"(?<![\w-]){re.escape(p)}(?![\w-])", norm):
            hits.append(phrase)
    return hits


def _markdown_issues(text: str, platform: str) -> list[Issue]:
    if platform == "discord":
        return []
    issues = []
    if "**" in text or re.search(r"(?<!\w)__\S", text):
        issues.append(
            Issue("error", "markdown", "double-asterisk/underscore bold renders as symbols")
        )
    lines = text.splitlines()
    if any(re.match(r"\s{0,3}#{1,6}\s", ln) for ln in lines):
        issues.append(Issue("error", "markdown", "markdown heading (#) in a chat message"))
    if any(ln.lstrip().startswith(">") for ln in lines):
        issues.append(Issue("error", "markdown", "blockquote (>) wraps the text in a bar"))
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        issues.append(Issue("error", "markdown", "the whole draft is inside a code fence"))
    if "~~" in text:
        issues.append(Issue("error", "markdown", "~~strike~~ renders as symbols here"))
    if platform != "slack" and _EMPHASIS.search(text):
        issues.append(Issue("error", "markdown", f"*emphasis* is not rendered on {platform}"))
    if _MD_LINK.search(text):
        fix = "<url|text>" if platform == "slack" else "the bare URL"
        issues.append(Issue("error", "markdown", f"markdown link [text](url); use {fix}"))
    return issues


def check(
    text: str,
    rules: profilelib.Rules,
    platform: str = "plain",
    mode: str = "chat",
    builtin: list[str] | None = None,
) -> list[Issue]:
    """Runs every check on a draft.

    Args:
        text: The draft, one chat message per line.
        rules: Resolved rules of the register (or the no-profile defaults).
        platform: Target platform; only Discord accepts standard markdown.
        mode: ``chat`` compares against the register's numbers, ``doc`` skips them.
        builtin: Built-in stop phrases; read from ``references/stoplist.txt`` if omitted.

    Returns:
        Issues, errors first.
    """
    issues: list[Issue] = []
    ws = tm.words(text)

    if rules.yo == "never":
        yo = sorted({w for w in ws if "ё" in w.lower()})
        if yo:
            issues.append(Issue("error", "yo", f"'ё' in: {', '.join(yo)}; write 'е'"))
    if rules.dashes == "never":
        dashes = tm.dash_counts(text)
        if any(dashes.values()):
            found = ", ".join(f"{k} x{v}" for k, v in dashes.items() if v)
            issues.append(
                Issue("error", "dash", f"dashes ({found}); use a comma, colon, period or rephrase")
            )
    if rules.emoji == "never" and tm.emojis(text):
        issues.append(Issue("error", "emoji", f"emoji: {' '.join(tm.emojis(text))}"))
    if rules.en_apostrophes == "never" and tm.detect_lang(text) == "en":
        found = sorted(set(_CONTRACTION.findall(tm.clean(text))))
        if found:
            issues.append(
                Issue("error", "apostrophe", f"no apostrophes in English: {', '.join(found)}")
            )
    if rules.profanity == "never" and tm.has_profanity(text):
        issues.append(Issue("error", "profanity", "profanity is off for this profile"))

    phrases = (load_stoplist() if builtin is None else builtin) + list(rules.stoplist)
    hits = _stoplist_hits(text, phrases)
    if hits:
        issues.append(Issue("error", "stoplist", f"stop phrases: {'; '.join(hits)}"))
    issues.extend(_markdown_issues(text, platform))

    for pattern in (_CONTRAST_RU, _CONTRAST_EN):
        match = pattern.search(text)
        if match:
            issues.append(
                Issue("warn", "contrast", f"'not X, but Y' frame: {match.group(0).strip()!r}")
            )

    if mode == "chat":
        issues.extend(_threshold_issues(text, ws, rules))
    return sorted(issues, key=lambda i: i.level != "error")


def _threshold_issues(text: str, ws: list[str], rules: profilelib.Rules) -> list[Issue]:
    issues: list[Issue] = []
    n_words = len(ws)
    commas = tm.count_commas(text)
    if n_words >= rules.min_words and rules.commas_rate_p90 is not None:
        rate = 100 * commas / n_words
        if rate > rules.commas_rate_p90 + 1e-9:
            issues.append(
                Issue(
                    "warn",
                    "commas",
                    f"{rate:.0f} commas per 100 words, owner's p90 is {rules.commas_rate_p90:.0f}",
                )
            )
    elif rules.commas_per_burst_p90 is not None and commas > rules.commas_per_burst_p90:
        issues.append(
            Issue(
                "warn",
                "commas",
                f"{commas} commas, owner's p90 per turn is {rules.commas_per_burst_p90:.0f}",
            )
        )
    if rules.words_per_burst_p90 is not None and n_words > rules.words_per_burst_p90:
        issues.append(
            Issue(
                "warn",
                "length",
                f"{n_words} words, owner's p90 per turn is {rules.words_per_burst_p90:.0f}",
            )
        )
    messages = split_messages(text)
    if rules.messages_per_burst_p90 is not None and len(messages) > rules.messages_per_burst_p90:
        issues.append(
            Issue(
                "warn",
                "messages",
                f"{len(messages)} messages, owner's p90 per turn is "
                f"{rules.messages_per_burst_p90:.0f}",
            )
        )
    starts = [s for s in (tm.starts_upper(m) for m in messages) if s is not None]
    share = rules.capital_start_share
    if starts and share is not None:
        upper = sum(starts)
        if (share <= 0.2 and upper * 2 > len(starts)) or (share >= 0.8 and upper * 2 < len(starts)):
            issues.append(
                Issue("warn", "capital", f"owner starts with a capital in {share:.0%} of messages")
            )
    period = rules.period_end_share
    if period is not None and period <= 0.1 and any(tm.ending(m) == "period" for m in messages):
        issues.append(Issue("warn", "period", f"owner ends {period:.0%} of messages with a period"))
    return issues


def similar_length_issue(
    text: str, incoming: str, profile_dir: Path, register: str
) -> Issue | None:
    """Warns when the draft is far longer than the owner's replies to similar messages.

    More than twice the typical length and at least three words over it: one or two extra
    words on a one-word reply are fine, a paragraph where the owner says "оке" is not.
    """
    pool_path = profile_dir / "registers" / register / "pairs.jsonl"
    if not pool_path.is_file():
        return None
    top = similar.rank(incoming, similar.load_pool(pool_path), k=12)
    usual, _ = similar.typical(top)
    n = len(tm.words(text))
    if usual and n > 2 * usual and n - usual >= 3:
        return Issue(
            "warn",
            "similar_length",
            f"{n} words, your replies to similar messages are usually {usual}",
        )
    return None


def pick_rules(
    profile_dir: Path | None, register: str | None, text: str
) -> tuple[profilelib.Rules, str]:
    """Finds the rules to lint with and says where they came from.

    Without a profile the chat defaults apply. With one, a single register is used as
    is; with several, the register must be named unless exactly one matches the
    draft's language.

    Raises:
        ProfileError: The profile is broken or the register cannot be chosen.
    """
    if profile_dir is None or not (profile_dir / "stats.json").exists():
        if register:
            raise profilelib.ProfileError(f"--register given but no profile at {profile_dir}")
        return profilelib.default_rules(), "defaults (no profile)"
    profile = profilelib.load_profile(profile_dir)
    if register is None:
        regs = profile.registers
        if len(regs) != 1:
            lang = tm.detect_lang(text)
            same = [r for r in regs if profile.stats["registers"][r].get("lang") == lang]
            if len(same) != 1:
                raise profilelib.ProfileError(
                    f"several registers ({', '.join(regs)}); pass --register"
                )
            regs = same
        register = regs[0]
    return profile.rules(register), f"register {register}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a draft against the owner's profile.")
    parser.add_argument("file", nargs="?", type=Path, help="draft file; stdin if omitted")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="profile directory")
    parser.add_argument("--no-profile", action="store_true", help="ignore any profile")
    parser.add_argument("--register", help="register name from the profile")
    parser.add_argument(
        "--platform", default="plain", choices=profilelib.PLATFORMS, help="target platform"
    )
    parser.add_argument("--mode", default="chat", choices=("chat", "doc"))
    parser.add_argument("--json", action="store_true", help="print issues as JSON")
    parser.add_argument(
        "--incoming", type=Path, help="the message being answered, to compare reply length"
    )
    args = parser.parse_args(argv)

    try:
        text = args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"lint: cannot read the draft: {exc}", file=sys.stderr)
        return 2
    if not text.strip():
        print("lint: empty draft", file=sys.stderr)
        return 2
    try:
        rules, source = pick_rules(None if args.no_profile else args.profile, args.register, text)
    except profilelib.ProfileError as exc:
        print(f"lint: {exc}", file=sys.stderr)
        return 2

    issues = check(text, rules, platform=args.platform, mode=args.mode)
    if args.incoming and rules.register and not args.no_profile and args.mode == "chat":
        try:
            incoming = args.incoming.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"lint: cannot read --incoming: {exc}", file=sys.stderr)
            return 2
        extra = similar_length_issue(text, incoming, args.profile, rules.register)
        if extra:
            issues.append(extra)
    if args.json:
        print(
            json.dumps(
                {"source": source, "issues": [asdict(i) for i in issues]}, ensure_ascii=False
            )
        )
    elif not issues:
        print(f"lint: clean ({source})")
    else:
        errors = sum(i.level == "error" for i in issues)
        print(f"lint: {errors} error(s), {len(issues) - errors} warning(s) ({source})")
        for issue in issues:
            print(f"{issue.level:5}  {issue.code:10} {issue.message}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
