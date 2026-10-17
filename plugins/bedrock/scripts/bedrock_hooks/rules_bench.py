"""The bench answer key stays closed to agents (D010).

Static reading of a command line is best effort: an interpreter (`python -c`), `env -C`,
`sudo -D`, `~user` paths or `CDPATH` can still reach the key. The measurement's integrity
rests first on where the key lives (outside the repository and outside an eval sandbox's
home) and on Claude Code's sandbox; this guard closes the ordinary routes.
"""

from __future__ import annotations

import re
from pathlib import Path

from bedrock_hooks import paths, shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict


def _answer_key(env: Env) -> Path | None:
    key = env.setting("bench").get("answer_key")
    if not key or not env.project:
        return None
    return paths.expand(env, str(key), env.project.root)


RECURSIVE = {"rg", "ag", "ack", "find", "fd", "tree", "tar", "zip", "rsync", "du"}
RECURSIVE_LONG = ("--recursive", "--dereference-recursive", "--directories=recurse")
PATTERN_FIRST = {"rg", "ag", "ack", "grep", "egrep", "fgrep"}
PATTERN_OPTIONS = {"-e", "--regexp", "-f", "--file"}
VALUE_OPTIONS = PATTERN_OPTIONS | {"-d", "--directories", "-C"}
GLOB = re.compile(r"[*?\[]|(?<!\$)\{")
HOME_FORMS = re.compile(r"\$\{HOME[^}A-Za-z0-9_][^}]*\}")
BRACES = re.compile(r"(?<!\$)\{([^{}]*,[^{}]*)\}")
XARGS_VALUES = {"-a", "-d", "-E", "-I", "-i", "-L", "-l", "-n", "-P", "-s"}


def _git_grep(simple: shell.Simple) -> bool:
    return simple.program == "git" and "grep" in simple.argv[1:]


def _recursive(simple: shell.Simple) -> bool:
    args = simple.argv[1:]
    flags = [a for a in args if a.startswith("-")]
    letters = "R" if simple.program == "ls" else "rR"  # `ls -r` reverses, `ls -R` recurses
    cluster = any(not f.startswith("--") and any(c in f for c in letters) for f in flags)
    by_value = any(a == "-d" and args[i + 1 : i + 2] == ["recurse"] for i, a in enumerate(args))
    long = any(f.startswith(RECURSIVE_LONG) for f in flags)
    return simple.program in RECURSIVE or _git_grep(simple) or cluster or by_value or long


def _positionals(simple: shell.Simple) -> list[str]:
    """The words naming what a command reads: option values and a search pattern left out."""
    args = simple.argv[1:]
    if _git_grep(simple):
        args = args[args.index("grep") + 1 :]
    words: list[str] = []
    skip = given = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in VALUE_OPTIONS:
            skip, given = True, given or arg in PATTERN_OPTIONS
            continue
        given = given or arg.startswith(("--regexp=", "--file="))
        if not arg.startswith("-"):
            words.append(arg)
    if (simple.program in PATTERN_FIRST or _git_grep(simple)) and words and not given:
        words = words[1:]
    return words


def _variants(word: str) -> list[str]:
    """A word with its `{a,b}` lists spelled out, as the shell would."""
    match = BRACES.search(word)
    if not match:
        return [word]
    head, tail = word[: match.start()], word[match.end() :]
    return [w for part in match.group(1).split(",") for w in _variants(head + part + tail)]


def _xargs_runs_a_recursive(simple: shell.Simple) -> bool:
    args, index = simple.argv[1:], 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in XARGS_VALUES else 1
    inner = args[index:]
    return bool(inner) and _recursive(shell.Simple(inner))


def _option_values(simple: shell.Simple) -> list[str]:
    """Paths an option may carry: `--file=X`, `-fX`, and the word after `-f`, `-e`, ..."""
    args, found = simple.argv[1:], []
    for index, arg in enumerate(args):
        if arg.startswith("--") and "=" in arg:
            found.append(arg.split("=", 1)[1])
        elif arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
            found.append(arg[2:])
        if arg in VALUE_OPTIONS and index + 1 < len(args):
            found.append(args[index + 1])
    return found


def _reach(env: Env, word: str, folder: Path) -> tuple[list[Path], list[Path]]:
    """What a word may name: exact paths, and folders under which a glob may reach anything."""
    word = HOME_FORMS.sub("${HOME}", word)  # ${HOME%/}, ${HOME:-x}: still the home folder
    exact, under = [], []
    for variant in _variants(word):
        if match := GLOB.search(variant):  # a glob: anything under its fixed part
            static = variant[: match.start()].rsplit("/", 1)[0] or "."
            under.append(paths.expand(env, static, folder))
        else:
            exact.append(paths.expand(env, variant, folder))
    return exact, under


def _simple_reaches(simple: shell.Simple, folders: list[Path], env: Env, key: Path) -> bool:
    deep = _recursive(simple)
    reads = _positionals(simple) if deep else [*simple.argv, *simple.redirects]
    if deep and not reads:
        reads = ["."]
    reads += simple.inputs
    if simple.program == "git" and "-C" in simple.argv[1:-1]:
        reads.append(simple.argv[simple.argv.index("-C") + 1])
    values = _option_values(simple)
    for folder in folders:
        if any(paths.under(p, key) for v in values for p in _reach(env, v, folder)[0]):
            return True
        for word in reads:
            exact, under = _reach(env, word, folder)
            if any(paths.under(p, key) for p in exact):
                return True
            if any(paths.touches(p, key) for p in under + (exact if deep else [])):
                return True
    return False


def _bash_reaches(event: Event, env: Env, key: Path) -> bool:
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError:
        words = str(event.tool_input.get("command", "")).split()
        return any(paths.under(paths.expand(env, w, event.cwd), key) for w in words)
    if any(s.program == "xargs" and _xargs_runs_a_recursive(s) for s in simples):
        return True  # the paths arrive on stdin and cannot be seen
    walked = paths.walk(simples, event.cwd, env)
    return any(_simple_reaches(simple, folders, env, key) for simple, folders in walked)


def _tool_reaches(event: Event, env: Env, key: Path) -> bool:
    data = event.tool_input
    given = [str(data.get(k)) for k in ("file_path", "path", "notebook_path") if data.get(k)]
    base = paths.expand(env, given[0], event.cwd) if given else event.cwd
    if any(paths.under(paths.expand(env, w, event.cwd), key) for w in given):
        return True
    if event.tool == "Grep" and paths.touches(base, key):
        return True
    if event.tool == "Glob":
        exact, under = _reach(env, str(data.get("pattern", "")), base)
        return any(paths.touches(p, key) for p in exact + under)
    return False


def check_answer_key(event: Event, env: Env) -> Verdict | None:
    """Agents never read the bench answer key, by any tool (D010).

    A recursive read or a glob over a folder that holds the key reaches it too, so a folder
    above the key counts as well as the key itself. Paths that arrive on stdin (`xargs`) cannot
    be seen, so an agent's `xargs` with a recursive reader is refused outright.
    """
    key = _answer_key(env)
    if key is None or not event.agent_id:
        return None
    reaches = _bash_reaches if event.tool == "Bash" else _tool_reaches
    if reaches(event, env, key):
        return Verdict(deny="refused: the bench answer key is closed to agents (D010).")
    return None


KEY_TOOLS = {"Read", "Grep", "Glob", "Bash", "NotebookRead"}
RULES = [
    Rule(
        "answer-key",
        frozenset({"PreToolUse"}),
        GUARD,
        check_answer_key,
        lambda e: e.tool in KEY_TOOLS,
    ),
]
