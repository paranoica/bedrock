"""New libraries need the owner's word and a real, established package (D022.15)."""

from __future__ import annotations

from pathlib import PurePosixPath

from bedrock_lib import packages

from bedrock_hooks import gate, shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.gate import Action
from bedrock_hooks.rules_outward import SCRIPT_RUNNERS, unrun

INSTALL_VERBS = {
    "npm": {"install", "i", "add"}, "pnpm": {"add", "install", "i"}, "yarn": {"add"},
    "bun": {"add", "install", "i"}, "pip": {"install"}, "pip3": {"install"},
    "uv": {"add"}, "poetry": {"add"}, "pipx": {"install"}, "cargo": {"add", "install"},
    "go": {"get", "install"}, "gem": {"install"}, "brew": {"install"},
    "apt": {"install"}, "apt-get": {"install"}, "dnf": {"install"}, "pacman": {"-S"},
    "yay": {"-S"}, "paru": {"-S"},
}  # fmt: skip
VALUED_INSTALL_FLAGS = {"-r", "--requirement", "-c", "--constraint", "-i", "--index-url"}
VALUED_INSTALL_FLAGS |= {"--extra-index-url", "-e", "--editable", "--target", "-t", "--prefix"}


def install_targets(argv: list[str]) -> list[str]:
    """Return the packages an install command adds; empty for lockfile installs."""
    words = unrun(argv) if PurePosixPath(argv[0]).name.startswith("python") else argv
    program = PurePosixPath(words[0]).name
    if program == "uv" and words[1:3] == ["pip", "install"]:
        words, program = ["pip", *words[2:]], "pip"
    verbs = INSTALL_VERBS.get(program)
    if not verbs or len(words) < 2 or words[1] not in verbs:
        return []
    names, skip = [], False
    for word in words[2:]:
        if skip:
            skip = False
        elif word in VALUED_INSTALL_FLAGS:
            skip = True
        elif not word.startswith("-") and not word.startswith((".", "/")) and "/" not in word[:1]:
            names.append(word)
    return names


def _installs(argv: list[str]) -> list[Action]:
    return [Action("install", f"installing {name}", name) for name in install_targets(argv)]


def _registry_problems(actions: list[Action], argv_programs: set[str]) -> list[str]:
    ecosystem = "npm" if argv_programs & SCRIPT_RUNNERS else "pypi"
    if not argv_programs & (SCRIPT_RUNNERS | {"pip", "pip3", "uv", "poetry", "python", "python3"}):
        return []
    names = [(ecosystem, action.target) for action in actions if action.kind == "install"]
    names = [(eco, name.split("==")[0].split("@")[0] or name) for eco, name in names if name]
    return [f"{label}: {problem}" for label, problem in packages.check(names)]


def check(event: Event, env: Env) -> Verdict | None:
    """Refuse an install without a grant, or of a package that looks made up or too new."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    actions = [action for simple in simples for action in _installs(simple.argv)]
    if not actions:
        return None
    if event.agent_id:
        return Verdict(deny="install refused for an agent: new libraries are the owner's word.")
    if verdict := gate.decide(env, event, actions):
        return verdict
    try:
        problems = _registry_problems(actions, {simple.program for simple in simples})
    except packages.RegistryError as error:
        return Verdict(deny=f"install refused: the package could not be verified: {error}")
    if problems:
        return Verdict(deny="install refused, check the name (D022.15): " + "; ".join(problems))
    return None


RULES = [Rule("installs", frozenset({"PreToolUse"}), GUARD, check, lambda e: e.tool == "Bash")]
