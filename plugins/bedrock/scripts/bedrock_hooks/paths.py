"""Where a command reads and writes: home expansion, symlinks, `cd`, redirect and writer targets."""

from __future__ import annotations

import os
import re
from pathlib import Path

from bedrock_hooks import shell
from bedrock_hooks.core import Env

WRITERS = {"cp", "mv", "rm", "tee", "touch", "mkdir", "ln", "chmod", "chown", "install", "rsync"}
WRITERS |= {"truncate", "rmdir", "unlink", "shred"}
IN_PLACE = {"sed", "perl", "ruby"}
# program -> options whose value is a path the program writes into
OUTPUT_OPTIONS = {
    "curl": {"-o", "--output"},
    "wget": {"-O", "--output-document", "-P", "--directory-prefix"},
    "tar": {"-C", "--directory"},
    "unzip": {"-d"},
    "cp": {"-t", "--target-directory"},
    "mv": {"-t", "--target-directory"},
    "install": {"-t", "--target-directory"},
    "sort": {"-o", "--output"},
    "git": {"--output"},
}
VARIABLE = re.compile(r"[$`]")
KNOWN = re.compile(r"\$\{?HOME\}?")


def hidden(word: str) -> bool:
    """True when a word's value comes from a variable or substitution other than $HOME."""
    return bool(VARIABLE.search(KNOWN.sub("", word)))


def home(env: Env) -> Path:
    """The owner's home folder as the hook sees it."""
    return Path(env.environ.get("HOME", str(Path.home())))


def expand(env: Env, word: str, cwd: Path) -> Path:
    """Expand `~`, `$HOME` and `${HOME}`, make relative paths absolute, and resolve symlinks."""
    base = str(home(env))
    text = re.sub(r"^~(?=/|$)", base, word).replace("${HOME}", base).replace("$HOME", base)
    path = Path(text)
    absolute = path if path.is_absolute() else cwd / path
    return Path(os.path.realpath(absolute))


def under(path: Path, folder: Path) -> bool:
    """True when `path` is `folder` or inside it, symlinks resolved on both sides."""
    return path.is_relative_to(Path(os.path.realpath(folder)))


def touches(path: Path, folder: Path) -> bool:
    """True when writing `path` affects `folder`: inside it, or an ancestor that contains it."""
    real = Path(os.path.realpath(folder))
    return path.is_relative_to(real) or real.is_relative_to(path)


def walk(simples: list[shell.Simple], cwd: Path, env: Env) -> list[tuple[shell.Simple, list[Path]]]:
    """Pair each simple command with the folders it may run in.

    A `cd` may or may not take effect (`;`, `&`, a subshell), so later commands are judged
    from the starting folder and from every folder a `cd` named before them.
    """
    paired = []
    folders = [cwd]
    for simple in simples:
        if simple.program in ("cd", "pushd"):
            targets = [w for w in simple.argv[1:] if not w.startswith("-")]
            target = expand(env, targets[0], folders[-1]) if targets else home(env)
            folders = [*folders, target]
            continue
        paired.append((simple, list(dict.fromkeys(folders))))
    return paired


def _option_values(simple: shell.Simple) -> list[str]:
    options = OUTPUT_OPTIONS.get(simple.program, set())
    args = simple.argv[1:]
    found = []
    for index, arg in enumerate(args):
        name, eq, value = arg.partition("=")
        if eq and name in options:
            found.append(value)
        elif arg in options and index + 1 < len(args):
            found.append(args[index + 1])
        elif arg.startswith("-") and not arg.startswith("--") and len(arg) > 2:
            if f"-{arg[-1]}" in options and index + 1 < len(args):
                found.append(args[index + 1])
            elif arg[:2] in options:
                found.append(arg[2:])
    return found


def write_words(simple: shell.Simple) -> list[str]:
    """The raw words naming what a simple command may write."""
    words = list(simple.redirects) + _option_values(simple)
    args = simple.argv[1:]
    in_place = simple.program in IN_PLACE and any(a.startswith("-i") for a in args)
    awk_in_place = simple.program in ("awk", "gawk") and "inplace" in args
    if simple.program in WRITERS or in_place or awk_in_place:
        words += [a for a in args if not a.startswith("-") and a != "inplace"]
    if simple.program == "dd":
        words += [a[3:] for a in args if a.startswith("of=")]
    if simple.program == "git" and args[:1] == ["clone"]:
        words += [a for a in args[1:] if not a.startswith("-")][1:2]
    return words


def write_targets(simple: shell.Simple, cwd: Path, env: Env) -> list[Path]:
    """Every path a simple command may write, resolved from one folder."""
    return [expand(env, word, cwd) for word in write_words(simple) if not hidden(word)]


def all_writes(simples: list[shell.Simple], cwd: Path, env: Env) -> tuple[list[Path], list[str]]:
    """Every resolved write target of a command line, and the targets named by a variable."""
    targets: list[Path] = []
    unseen: list[str] = []
    for simple, folders in walk(simples, cwd, env):
        unseen += [w for w in write_words(simple) if hidden(w)]
        for folder in folders:
            targets += write_targets(simple, folder, env)
    return list(dict.fromkeys(targets)), unseen
