"""Style metrics shared by the profile pipeline and the draft linter.

The same functions measure the owner's corpus and the generated draft, so the
thresholds in a profile and the lint verdicts always agree. Standard library
only, because the module also runs inside the claude.ai sandbox.
"""

from __future__ import annotations

import re
import statistics
from collections.abc import Iterable, Sequence

_FENCED = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`\n]*`")
_URL = re.compile(r"(?:https?://|www\.)[^\s<>]*[^\s<>.,;:!?)\]'\"]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_MENTION = re.compile(r"(?<!\w)[@#][\w.-]*\w")
_SHORTCODE = re.compile(r":[a-z0-9_+-]*[a-z][a-z0-9_+-]*:")

_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")
_CYR = re.compile(r"[Ѐ-ӿ]")
_LAT = re.compile(r"[A-Za-z]")
_DECIMAL_COMMA = re.compile(r"\d,\d")
_SPACED_HYPHEN = re.compile(r"(?<=\S)[ \t]+-{1,2}[ \t]+(?=\S)")
_APOSTROPHE = re.compile(r"[^\W\d_]['’][^\W\d_]")
_NEG_CONTRACTED = re.compile(r"\b\w+n['’]t\b", re.IGNORECASE)
_NEG_EXPANDED = re.compile(
    r"\b(?:(?:do|does|did|is|are|was|were|will|would|could|should|have|has|had|must|need|can)"
    r" not|cannot)\b",
    re.IGNORECASE,
)

_EMOJI_BASE = (
    "\U0001f300-\U0001f5ff\U0001f600-\U0001f64f\U0001f680-\U0001f6ff\U0001f700-\U0001f7ff"
    "\U0001f800-\U0001f8ff\U0001f900-\U0001f9ff\U0001fa00-\U0001faff☀-⛿✀-➿"
    "⭐⭕⬛⬜⌚⌛⏩-⏳⏸-⏺"
)
_EMOJI_MOD = "\ufe0f\U0001f3fb-\U0001f3ff"
_EMOJI = re.compile(
    rf"[\U0001f1e6-\U0001f1ff]{{2}}"
    rf"|[{_EMOJI_BASE}][{_EMOJI_MOD}]*(?:\u200d[{_EMOJI_BASE}][{_EMOJI_MOD}]*)*"
)
_EMOTICON = re.compile(r"[:;]-?[()]+")

_PROFANITY = re.compile(
    r"(?<![а-яёa-z])(?:ху[йеёияю]|пизд|бля|еб[аунлиы]|ёб|заеб|заёб|выеб|наеб|отъеб|съеб|уеб|поеб|"
    r"доеб|мудак|мудил|сука|суки|сучк|fuck|shit|bitch|asshole|bullshit)",
    re.IGNORECASE,
)

# Words whose spelling with "е" instead of "ё" is unambiguous, so their two forms
# show whether the writer types "ё" at all.
YO_KNOWN = frozenset(
    {
        "ещё",
        "её",
        "чё",
        "причём",
        "моё",
        "твоё",
        "своё",
        "пришёл",
        "пошёл",
        "нашёл",
        "ушёл",
        "зашёл",
        "даёт",
        "даёшь",
        "идёт",
        "идёшь",
        "живёт",
        "берёт",
        "ждёт",
        "придёт",
        "пойдёт",
        "найдёт",
        "зовёт",
        "ведёт",
        "несёт",
        "растёт",
    }
)
_YO_PLAIN = {w.replace("ё", "е"): w for w in YO_KNOWN}

FILLERS = {
    "ru": frozenset(
        {
            "ну",
            "просто",
            "прост",
            "типо",
            "типа",
            "вроде",
            "короче",
            "кароч",
            "кст",
            "вообще",
            "ваще",
            "же",
            "ли",
            "бы",
            "вот",
            "ща",
            "щас",
            "ок",
            "оке",
            "окей",
            "ага",
            "неа",
            "лан",
            "ладно",
            "мб",
            "норм",
            "хз",
            "плиз",
            "спс",
            "пж",
            "слушай",
            "блин",
            "кажется",
            "наверное",
            "реально",
            "прям",
            "чет",
            "чето",
            "щя",
        }
    ),
    "en": frozenset(
        {
            "yeah",
            "yep",
            "like",
            "just",
            "so",
            "btw",
            "actually",
            "basically",
            "kinda",
            "oh",
            "ok",
            "okay",
            "lol",
            "well",
            "anyway",
            "sure",
            "really",
            "pretty",
            "totally",
            "literally",
            "honestly",
            "maybe",
            "guess",
        }
    ),
}

STOPWORDS = frozenset(
    {
        "и",
        "в",
        "во",
        "на",
        "не",
        "что",
        "с",
        "со",
        "а",
        "я",
        "ты",
        "это",
        "как",
        "по",
        "к",
        "у",
        "о",
        "об",
        "из",
        "за",
        "то",
        "так",
        "он",
        "она",
        "оно",
        "мы",
        "вы",
        "они",
        "его",
        "ее",
        "её",
        "их",
        "мне",
        "меня",
        "тебе",
        "тебя",
        "там",
        "тут",
        "для",
        "от",
        "до",
        "но",
        "или",
        "если",
        "уже",
        "все",
        "всё",
        "есть",
        "да",
        "нет",
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "is",
        "it",
        "i",
        "you",
        "we",
        "that",
        "this",
        "with",
        "be",
        "are",
        "was",
        "at",
        "as",
        "not",
        "do",
        "have",
        "will",
        "can",
        "my",
        "your",
        "if",
        "but",
    }
)


def clean(text: str) -> str:
    """Strips parts of a message that do not carry the writer's prose style.

    Code, URLs, emails, @mentions, #channels and Slack emoji shortcodes are removed,
    so their dots, commas and letters do not skew punctuation and word counts.

    Args:
        text: Raw message text.

    Returns:
        The text with those fragments replaced by a space.
    """
    for pattern in (_FENCED, _INLINE, _URL, _EMAIL, _MENTION, _SHORTCODE):
        text = pattern.sub(" ", text)
    return text


def words(text: str) -> list[str]:
    """Returns the words of a cleaned message, keeping inner hyphens and apostrophes."""
    return _WORD.findall(clean(text))


def detect_lang(text: str) -> str:
    """Guesses the language by script: ``"ru"``, ``"en"`` or ``"other"`` on a tie or no letters."""
    cleaned = clean(text)
    cyr = len(_CYR.findall(cleaned))
    lat = len(_LAT.findall(cleaned))
    if cyr > lat:
        return "ru"
    if lat > cyr:
        return "en"
    return "other"


def count_commas(text: str) -> int:
    """Counts commas outside code and URLs, ignoring decimal commas like ``1,5``."""
    cleaned = clean(text)
    return cleaned.count(",") - len(_DECIMAL_COMMA.findall(cleaned))


def ending(text: str) -> str:
    """Classifies how a message ends.

    Returns:
        One of ``empty``, ``ellipsis``, ``period``, ``question``, ``exclamation``,
        ``bracket``, ``emoji``, ``none`` (ends on a letter or digit) or ``other``.
    """
    stripped = clean(text).rstrip()
    if not stripped:
        return "empty"
    if stripped.endswith(("...", "…")):
        return "ellipsis"
    last = stripped[-1]
    simple = {".": "period", "?": "question", "!": "exclamation", ")": "bracket", "(": "bracket"}
    if last in simple:
        return simple[last]
    if last.isalnum():
        return "none"
    if any(m.end() == len(stripped) for m in _EMOJI.finditer(stripped)):
        return "emoji"
    return "other"


def starts_upper(text: str) -> bool | None:
    """Tells whether a message opens with a capital letter, or ``None`` if it opens otherwise."""
    stripped = clean(text).lstrip()
    if not stripped or not stripped[0].isalpha():
        return None
    return stripped[0].isupper()


def dash_counts(text: str) -> dict[str, int]:
    """Counts em dashes, en dashes and a hyphen used as a dash between spaces."""
    cleaned = clean(text)
    return {
        "em": cleaned.count("—") + cleaned.count("―"),
        "en": cleaned.count("–") + cleaned.count("‒"),
        "spaced_hyphen": len(_SPACED_HYPHEN.findall(cleaned)),
    }


def count_dashes(text: str) -> int:
    """Total of :func:`dash_counts`."""
    return sum(dash_counts(text).values())


def has_apostrophe(text: str) -> bool:
    """True if an apostrophe sits between two letters (a contraction or possessive)."""
    return bool(_APOSTROPHE.search(clean(text)))


def negation_counts(text: str) -> tuple[int, int]:
    """Counts contracted (``don't``) and expanded (``do not``, ``cannot``) English negations."""
    cleaned = clean(text)
    return len(_NEG_CONTRACTED.findall(cleaned)), len(_NEG_EXPANDED.findall(cleaned))


def emojis(text: str) -> list[str]:
    """Lists emoji in the raw text: Unicode sequences and Slack ``:shortcodes:``."""
    found = _SHORTCODE.findall(text)
    found.extend(_EMOJI.findall(_SHORTCODE.sub(" ", text)))
    return found


def bracket_smileys(text: str) -> int:
    """Counts smileys made of brackets: ``))``, ``((``, ``:)``.

    A run of unmatched ``)`` or ``(`` counts once; brackets that close a pair are
    ordinary punctuation.
    """
    cleaned = clean(text)
    count = len(_EMOTICON.findall(cleaned))
    cleaned = _EMOTICON.sub(" ", cleaned)
    unmatched: set[int] = set()
    stack: list[int] = []
    for i, ch in enumerate(cleaned):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if stack:
                stack.pop()
            else:
                unmatched.add(i)
    unmatched.update(stack)
    prev = -2
    prev_ch = ""
    for i in sorted(unmatched):
        if not (i == prev + 1 and cleaned[i] == prev_ch):
            count += 1
        prev, prev_ch = i, cleaned[i]
    return count


def has_profanity(text: str) -> bool:
    """Rough check for Russian mat and common English swearing."""
    return bool(_PROFANITY.search(text))


def count_yo_words(ws: Iterable[str]) -> int:
    """Counts words that contain ``ё``."""
    return sum(1 for w in ws if "ё" in w.lower())


def yo_known_counts(ws: Iterable[str]) -> tuple[int, int]:
    """Counts words from :data:`YO_KNOWN` written with ``ё`` against all their occurrences.

    Returns:
        ``(with_yo, total)``, where total includes the same words spelled with ``е``.
    """
    with_yo = total = 0
    for w in ws:
        low = w.lower()
        if low in YO_KNOWN:
            with_yo += 1
            total += 1
        elif low in _YO_PLAIN:
            total += 1
    return with_yo, total


def percentile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolated percentile, ``q`` in ``[0, 1]``; ``None`` for no values."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (pos - lower)


def distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    """Summarises values as count, mean, median and 90th percentile."""
    if not values:
        return {"n": 0, "mean": None, "median": None, "p90": None}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p90": percentile(values, 0.9),
    }
