#!/usr/bin/env python3
"""UserPromptSubmit hook: when a prompt asks for a message to send, make Claude load humanize.

Reads the hook event JSON on stdin. On a match prints a JSON ``additionalContext`` that
tells Claude to load the skill; otherwise prints nothing. Never blocks a prompt.
"""

from __future__ import annotations

import json
import re
import sys

SKILL_NAME = "humanize"


def context(skill: str, where: str, others: str) -> str:
    """The instruction added to the prompt, naming the one skill to load."""
    return (
        "The user is asking for text they will send as themselves (a reply, message, email, "
        f'post or draft). Before writing it, call the Skill tool with skill="{skill}" ({where}; '
        f"not {others}) and follow it, including the lint step. Its voice rules override the "
        "global style rules for that text. A request to reply or write without the word send "
        "(отправь) means the text goes into this chat only: do not send it through Telegram, "
        "Slack or any other connector."
    )


CONTEXT = context(
    SKILL_NAME,
    "the personal skill in ~/.claude/skills/humanize",
    "bedrock:humanize, not anthropic-skills:humanize",
)

# Pasted, fenced and quoted text is someone else's words; only the user's own words ask.
QUOTED = re.compile(
    r"<pasted_content[^>]*>.*?</pasted_content>|```.*?```|^>[^\n]*$|«[^»\n]*»|„[^“\n]*“"
    r'|"[^"\n]*"',
    re.S | re.M,
)
# A short question after a pasted message: "а я что?", "что мне ответить".
ABOUT_PASTE = re.compile(
    r"^\s*(?:а\s+)?(?:я|мне)\s+что(?:\s+(?:ему|ей|им))?(?:\s+(?:скажу|отвечу|напишу|ответить"
    r"|сказать|написать))?\s*[?!.]*\s*$",
    re.I,
)

# A request is recognised by an addressee (a pronoun, a name, a role) or by an explicit
# message cue. Weak cues are ignored when the prompt is about code.
_VERB_RU = r"(?:напиши|набросай|накидай|составь|сформулируй|подготовь|черкни|отпиши|ответь)"
_PRON_RU = r"(?:ему|ей|им)\b(?!\s+(?:тест|функци|код|скрипт|класс|метод|конфиг|запрос))"
_ROLE_RU = (
    r"(?:коллег[еам]\w*|клиент(?:у|ам)|начальник(?:у|ам)|руководител(?:ю|ям)|заказчик(?:у|ам)"
    r"|менеджер(?:у|ам)|маме|папе|брату|сестре|другу|подруге|жене|мужу|девушке|парню"
    r"|сосед(?:у|ке)|арендодател(?:ю|ям)|хозя(?:ину|йке)|преподу|преподавател(?:ю|ям)"
    r"|учител(?:ю|ям)|команде|ребятам|всем|в\s+поддержку"
    r"|в\s+(?:слак|чат|группу|личку|тг|телегу|канал)\s+(?:что|про|о|об)\b)"
)
_ROLE_EN = (
    r"(?:my\s+(?:boss|manager|landlord|landlady|client|customer|colleague|coworker|co-worker"
    r"|friend|mom|mum|dad|wife|husband|partner|girlfriend|boyfriend|team|teacher|professor"
    r"|tenant|neighbou?r|recruiter|lead|ex))\b"
)
_NOUN_RU = r"(?:сообщени\w*|письм\w*|ответ\w*|пост\w*|смс\w*|текст\w*)"
_NAME_DAT = r"[А-ЯЁ][а-яё]+(?:е|у|ю|и|ой|ей)\b"
_WORDS = r"(?:[\w-]+\s+){0,2}?"
_ADDRESSEE_RU = rf"(?:{_PRON_RU}|{_ROLE_RU})"
_SAY_RU = r"(?:ответить|написать|отказать|сказать|возразить)"

STRONG = [
    re.compile(
        r"\b(?:write|post|send\s+a\s+message|tell|let)\s+(?:to\s+)?"
        r"(?:the\s+(?:team|group|channel|client|guys)|everyone|everybody)\b"
        r"(?!\s+(?:know\s+)?(?:how|what)\b)",
        re.I,
    ),
    re.compile(r"от\s+(?:моего|меня)\s+(?:имени|лица)", re.I),
    re.compile(r"\b(?:reply|respond|answer|write)\s+(?:to\s+)?(?:this|it|that)?\s*as\s+me\b", re.I),
    re.compile(rf"{_VERB_RU}\s+(?:(?:коротко|быстро|пожалуйста)\s+)?{_ADDRESSEE_RU}", re.I),
    re.compile(rf"(?i:{_VERB_RU})\s+{_NAME_DAT}"),
    re.compile(rf"{_VERB_RU}\s+{_WORDS}{_NOUN_RU}\s+{_WORDS}{_ADDRESSEE_RU}", re.I),
    re.compile(
        r"(?:сделай|напиши|набросай|накидай|подготовь)\s+(?:мне\s+)?(?:черновик|драфт)\w*\s+"
        r"(?:ответ|сообщени|письм|пост)",
        re.I,
    ),
    re.compile(rf"(?:что|как)\s+{_WORDS}{_SAY_RU}\s+{_ADDRESSEE_RU}", re.I),
    re.compile(rf"(?i:что|как)\s+{_WORDS}(?i:{_SAY_RU})\s+{_NAME_DAT}"),
    re.compile(
        r"(?:что|как)\s+(?:(?:мне|ему|ей|им|лучше|бы)\s+)*ответить"
        r"(?=\s*(?:[?:.!]|$)|\s+на\s+(?:это|его|ее|её|их|такое)\b)",
        re.I,
    ),
    re.compile(r"ответь\s+(?:за\s+меня|на\s+(?:это|его|ее|её|их)\s+(?:сообщени|письм))", re.I),
    re.compile(
        rf"помоги\s+(?:мне\s+)?(?:ответить|написать|сформулировать)\s+{_ADDRESSEE_RU}", re.I
    ),
    re.compile(
        r"(?i:reply|write|respond)\s+to\s+[A-Z][a-z]+\s*(?:,|:|and\b|that\b|about\b|saying\b)"
    ),
    re.compile(r"(?i:write\s+back|get\s+back)\s+to\s+(?:[A-Z][a-z]+\b|(?i:him|her|them)\b)"),
    re.compile(
        rf"\b(?:reply|respond|write|answer|text|message|email)\s+(?:to\s+)?{_ROLE_EN}", re.I
    ),
    re.compile(
        r"\bhow\s+(?:should|do|can|would)\s+i\s+(?:reply|respond|answer)\s+(?:to\s+)?"
        r"(?:him|her|them|my\s+\w+|th(?:is|at)\s+(?:message|email|e-mail|dm|text))",
        re.I,
    ),
    re.compile(
        r"\banswer\s+(?:this|that|the|her|his|their|my)\s+(?:\w+\s+)?"
        r"(?:email|e-mail|message|dm|text)\b",
        re.I,
    ),
    re.compile(
        r"\bhelp\s+me\s+(?:answer|reply\s+to|respond\s+to|write\s+to)\s+"
        r"(?:him|her|them|my\s+\w+|this)",
        re.I,
    ),
    re.compile(
        r"\bwrite\s+(?:a|an)\s+(?:(?:quick|short|polite)\s+)?(?:reply|response|message|note|dm"
        r"|email|e-mail|text)\s+(?:to|for)\s+(?:him|her|them|my\s+\w+|the\s+team|[A-Z][a-z]+)",
        re.I,
    ),
    re.compile(
        r"(?:^|\s)/humanize\b|\bde-?slop\b"
        r"|\bhumani[sz]e\s+(?:this|it|that|my|the\s+(?:text|message|reply|draft|email))\b",
        re.I,
    ),
]

WEAK = [
    re.compile(r"очеловеч\w*|убери\s+(?:ии|ai|нейро)", re.I),
    re.compile(
        r"(?:перепиши|переделай|сделай|напиши|звучит)\s+(?:[\w-]+\s+){0,3}?по-человечески", re.I
    ),
    re.compile(
        r"\bdraft\s+(?:(?:a|an|the|my)\s+)?(?:(?:quick|short|polite)\s+)?"
        r"(?:reply|response|message|email|e-mail|note|dm|post|answer|text)\b"
        r"(?!\s+(?:schema|queue|format|type|class|model|broker|bus|handler|template))",
        re.I,
    ),
    re.compile(
        r"\b(?:reply|respond)\s+to\s+(?:this|that|the|her|his|their|my)\s+(?:\w+\s+)?"
        r"(?:message|email|e-mail|dm|text|comment|post)\b",
        re.I,
    ),
    re.compile(r"\b(?:reply|respond|write\s+back|answer)\s+to\s+(?:him|her|them)\b", re.I),
    re.compile(r"\bwhat\s+(?:should|do|can|would)\s+i\s+(?:say|reply|answer|tell|respond)\b", re.I),
]

CODE = re.compile(
    r"\b(?:код\w*|тест\w*|функци\w*|скрипт\w*|класс\w*|метод\w*|хендлер\w*|обработчик\w*"
    r"|эндпоинт\w*|бот(?:а|у|ом)?|api|апи|json|sql|regex|redis|kafka|postgres\w*|handler\w*"
    r"|endpoint\w*|webhook\w*|schema|queue|consumer|function|class|method|script|readme"
    r"|docstring|commit|bot|server|request|http|pr|template|jinja|interview)\b",
    re.I,
)


def own_words(prompt: str) -> str:
    """The prompt without pasted, fenced or quoted text."""
    return QUOTED.sub(" ", prompt)


def wants_message(prompt: str) -> bool:
    """True if the user's own words ask for a text they will send to someone."""
    own = own_words(prompt)
    if own != prompt and ABOUT_PASTE.search(own.strip()):
        return True
    if any(p.search(own) for p in STRONG):
        return True
    return not CODE.search(own) and any(p.search(own) for p in WEAK)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = event.get("prompt") if isinstance(event, dict) else None
    if isinstance(prompt, str) and wants_message(prompt):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": CONTEXT,
            }
        }
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
