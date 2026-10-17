"""Split a shell command line into the simple commands it runs, for the guards to judge.

Over-splitting is safe, under-splitting is not: every nested form (`bash -c`, `eval`, `$(...)`,
backticks, `xargs`) is opened, and wrapper prefixes (`sudo`, `env`, `timeout`, ...) are peeled.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath

OPERATORS = {"&&", "||", ";", "|", "&", "\n", "(", ")", "{", "}", ";;", "|&"}
SEPARATOR_CHARS = set(";&|()\n")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
PLAIN_PREFIXES = {"sudo", "doas", "command", "builtin", "exec", "nohup", "time", "env", "nice"}
PREFIX_OPTIONS_WITH_VALUE = {
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-U"},
    "env": {"-u", "-C", "-S"},
    "nice": {"-n"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
SUBSTITUTION = re.compile(r"\$\(((?:[^()]|\([^()]*\))*)\)|`([^`]*)`")
XARGS_VALUED = {"-n", "-I", "-L", "-P", "-d", "-s", "-E", "-a", "--max-args", "--arg-file"}
MAX_DEPTH = 5


class ParseError(Exception):
    """The command line cannot be split safely (unbalanced quotes, too deep)."""


@dataclass(frozen=True)
class Simple:
    """One simple command: its argv after prefixes, and the program's bare name."""

    argv: list[str]
    redirects: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    assignments: list[str] = field(default_factory=list)

    @property
    def program(self) -> str:
        """The program name without its directory."""
        if not self.argv:
            return ""
        return PurePosixPath(self.argv[0]).name or self.argv[0]

    @property
    def opaque(self) -> bool:
        """True when the program itself comes from a variable or substitution."""
        return bool(self.argv) and any(mark in self.argv[0] for mark in ("$", "`"))


def _tokens(line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        return list(lexer)
    except ValueError as error:
        raise ParseError(f"cannot split the command: {error}") from error


def _is_redirect(token: str) -> bool:
    return bool(token) and set(token) <= set("<>&|") and ("<" in token or ">" in token)


Segment = tuple[list[str], list[str], list[str]]


def _segments(tokens: list[str]) -> list[Segment]:
    """Split tokens into (words, output targets, input files) per simple command."""
    segments: list[Segment] = [([], [], [])]
    pending: str | None = None
    for token in tokens:
        words, targets, sources = segments[-1]
        if pending is not None:
            if ">" in pending and not token.isdigit():
                targets.append(token)
            elif pending in ("<", "<>", "0<"):
                sources.append(token)
            pending = None
        elif token in OPERATORS or (token and set(token) <= SEPARATOR_CHARS):
            segments.append(([], [], []))
        elif _is_redirect(token):
            if words and words[-1].isdigit():
                words.pop()
            pending = token
        else:
            words.append(token)
    return [segment for segment in segments if segment[0]]


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w]*)\1[^\n]*\n")


def strip_heredocs(line: str) -> str:
    """Drop heredoc bodies: they are data fed to a command, not commands of this line."""
    out, position = [], 0
    for match in HEREDOC.finditer(line):
        if match.start() < position:
            continue
        end = re.compile(rf"^\t*{re.escape(match.group(2))}\s*$", re.M).search(line, match.end())
        out.append(line[position : match.end()])
        position = end.end() if end else len(line)
    out.append(line[position:])
    return "".join(out)


def heredoc_bodies(line: str) -> list[str]:
    """The text of each heredoc in a command line, in order."""
    bodies = []
    for match in HEREDOC.finditer(line):
        end = re.compile(rf"^\t*{re.escape(match.group(2))}\s*$", re.M).search(line, match.end())
        bodies.append(line[match.end() : end.start() if end else len(line)].rstrip("\n"))
    return bodies


def _assignments(argv: list[str]) -> list[str]:
    found = []
    for word in argv:
        if ASSIGNMENT.fullmatch(word):
            found.append(word)
        elif PurePosixPath(word).name not in PLAIN_PREFIXES and not word.startswith("-"):
            break
    return found


def _peel(argv: list[str]) -> list[str]:
    """Drop variable assignments and wrapper programs in front of the real command.

    A wrapper with nothing after it (`env`, `time`) is itself the command.
    """
    words = list(argv)
    while words:
        head = PurePosixPath(words[0]).name
        if ASSIGNMENT.fullmatch(words[0]):
            words.pop(0)
        elif (head in PLAIN_PREFIXES or head == "timeout") and not any(
            not w.startswith("-") and not ASSIGNMENT.fullmatch(w) for w in words[1:]
        ):
            return words
        elif head in PLAIN_PREFIXES or head == "timeout":
            words.pop(0)
            valued = PREFIX_OPTIONS_WITH_VALUE.get(head, set())
            while words and (words[0].startswith("-") or ASSIGNMENT.fullmatch(words[0])):
                option = words.pop(0)
                if option in valued and words:
                    words.pop(0)
            if head == "timeout" and words:
                words.pop(0)
        else:
            break
    return words


def _find_exec(argv: list[str]) -> list[str]:
    found = []
    for index, word in enumerate(argv):
        if word in ("-exec", "-execdir", "-ok", "-okdir"):
            rest = argv[index + 1 :]
            end = next((i for i, w in enumerate(rest) if w in (";", "+")), len(rest))
            found.append(shlex.join(rest[:end]))
    return found


def _xargs(argv: list[str]) -> list[str]:
    rest = argv[1:]
    while rest and rest[0].startswith("-"):
        option = rest.pop(0)
        if option in XARGS_VALUED and rest:
            rest.pop(0)
    return [shlex.join(rest)] if rest else []


def _shell_c(argv: list[str]) -> list[str]:
    """The command string of `sh -c`, honouring `--` and skipping long options like --norc."""
    words = argv[1:]
    for index, word in enumerate(words):
        if word == "--":
            break
        if word.startswith("-") and not word.startswith("--") and "c" in word[1:]:
            rest = [w for w in words[index + 1 :] if w != "--" and not w.startswith("-")]
            return rest[:1]
    return []


def reads_stdin_as_commands(simple: Simple) -> bool:
    """True for a shell given no -c and no script: it runs whatever arrives on its input."""
    if simple.program not in SHELLS:
        return False
    words = [w for w in simple.argv[1:] if w != "--"]
    if any(w.startswith("-") and not w.startswith("--") and "c" in w[1:] for w in words):
        return False
    return not [w for w in words if not w.startswith("-")]


def _inner(argv: list[str]) -> list[str]:
    """Return command strings an argv runs in turn: `bash -c X`, `eval X`, `xargs`, `find -exec`."""
    program = PurePosixPath(argv[0]).name
    if program in SHELLS:
        return _shell_c(argv)
    if program == "find":
        return _find_exec(argv)
    if program == "xargs":
        return _xargs(argv)
    if program == "eval":
        return [" ".join(argv[1:])]
    return []


def commands(line: str, depth: int = 0) -> list[Simple]:
    """Return every simple command the line runs, nested ones included."""
    if depth > MAX_DEPTH:
        raise ParseError("command nests too deeply to judge")
    found: list[Simple] = []
    line = strip_heredocs(line)
    for match in SUBSTITUTION.finditer(line):
        found += commands(match.group(1) or match.group(2) or "", depth + 1)
    for words, targets, sources in _segments(_tokens(line)):
        argv = _peel(words)
        if not argv:
            continue
        found.append(Simple(argv, targets, sources, _assignments(words)))
        for inner in _inner(argv):
            found += commands(inner, depth + 1)
    return found
