"""Secrets stay on the machine (D019, D022.9).

An env file reached by any route (argument, `@file`, `:path`, glob, symlink, input redirect)
may be used by programs that load it, never printed, copied or sent. Limit: code run through
an interpreter (`python -c "open('.env')"`) cannot be judged statically.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path, PurePosixPath

from bedrock_hooks import paths, shell
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict

ENV_FILE = re.compile(r"\.env(?:\.[\w.-]+)?|\.envrc|[\w.-]+\.env")
SAFE_ENV = re.compile(r"\.(?:example|sample|template|dist|defaults)$")
# Programs that load an env file to run something, or only look at the file's metadata.
LOADERS = {"ls", "stat", "test", "[", "chmod", "chown", "touch", "rm", "source", ".", "wc"}
LOADERS |= {"node", "deno", "bun", "docker", "docker-compose", "podman", "dotenv", "env-cmd"}
LOADERS |= {"direnv", "uvicorn", "foreman", "honcho", "op"}
GIT_SAFE = {"rm", "check-ignore", "status"}
COPIERS = {"cp", "mv", "install", "ln", "rsync"}
NETWORK = {"curl", "wget", "http", "https", "nc", "ncat", "netcat", "socat", "ssh", "scp"}
NETWORK |= {"sftp", "rsync", "ftp", "telnet"}
GREPS = {"grep", "egrep", "fgrep"}
MIN_SECRET = 12
ASSIGN = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
GLOB_CHARS = re.compile(r"[*?\[]")


def is_env_name(name: str) -> bool:
    """True for `.env`, `.env.<x>`, `.envrc` and `<x>.env`; false for examples and templates."""
    return bool(ENV_FILE.fullmatch(name)) and not SAFE_ENV.search(name)


def _candidates(word: str) -> list[str]:
    found = [word]
    for marker in ("=", "@", ":"):
        if marker in word:
            found.append(word.split(marker, 1)[1].lstrip("@"))
    return [w for w in found if w]


def names_env_file(word: str, cwd: Path, env: Env) -> bool:
    """True when a word can reach an env file: directly, by glob, or through a symlink."""
    for candidate in _candidates(word):
        if is_env_name(PurePosixPath(candidate).name):
            return True
        if GLOB_CHARS.search(candidate):
            if fnmatch.fnmatch(".env", PurePosixPath(candidate).name):
                return True
            base = Path("/") if candidate.startswith("/") else cwd
            matches = base.glob(candidate.lstrip("/")) if candidate.strip("/") else []
            if any(is_env_name(match.name) for match in matches):
                return True
        path = paths.expand(env, candidate, cwd)
        if path.exists() and is_env_name(path.name):
            return True
    return False


def _uses_env_file(simple: shell.Simple, cwd: Path, env: Env) -> bool:
    words = [
        w
        for w in simple.argv[1:]
        if (not w.startswith("--") or "=" in w) and not w.startswith(("--exclude", "--ignore"))
    ]
    if simple.program in COPIERS:
        # Writing an env file is fine; reading one (a source) is what leaks it.
        positional = [w for w in words if not w.startswith("-")]
        words = positional[:-1]
    return any(names_env_file(word, cwd, env) for word in words)


def _prints(simple: shell.Simple, cwd: Path, env: Env) -> str | None:
    if any(names_env_file(source, cwd, env) for source in simple.inputs):
        return "redirecting an env file into a command"
    if simple.program in LOADERS:
        return None
    if simple.program == "git" and set(simple.argv[1:2]) & GIT_SAFE:
        return None
    if _uses_env_file(simple, cwd, env):
        return f"`{simple.program}` on an env file"
    return None


SKIP = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
READERS = {"cat", "less", "more", "head", "tail", "bat", "batcat", "nl", "xxd", "od", "strings"}
READERS |= {"grep", "rg", "ag", "awk", "sed", "cut", "sort", "uniq", "base64", "hexdump", "tac"}
READERS |= {"rev", "dd", "fold", "paste", "column", "jq"}
PRINTERS = {"echo", "printf", "print", "tee", "logger", "xargs"}
HIDDEN_SEARCH = {
    "rg": ("--hidden", "-u", "-uu", "-uuu", "--no-ignore", "-.", "--unrestricted"),
    "ag": ("-u", "--unrestricted", "--hidden", "-a", "--all-types"),
}


def env_files_under(root: Path, depth: int = 3) -> list[Path]:
    """Env files in a folder tree, a few levels deep, skipping vendored folders."""
    found: list[Path] = []
    frontier = [root]
    for _ in range(depth + 1):
        following = []
        for folder in frontier:
            try:
                entries = list(folder.iterdir())
            except OSError:
                continue
            for entry in entries:
                if entry.is_file() and is_env_name(entry.name):
                    found.append(entry)
                elif entry.is_dir() and entry.name not in SKIP and not entry.is_symlink():
                    following.append(entry)
        frontier = following
    return found


def _search_roots(simple: shell.Simple, cwd: Path) -> list[Path]:
    dirs = [cwd / a for a in simple.argv[1:] if not a.startswith("-") and (cwd / a).is_dir()]
    return dirs or [cwd]


def _excluded(args: list[str]) -> bool:
    return any(
        (a.startswith(("--exclude", "--glob", "-g", "--ignore")) and ".env" in a)
        or a in ("!.env*", "!.env")
        for a in args
    )


def _searches_secrets(simple: shell.Simple, cwd: Path) -> bool:
    """A recursive or hidden-file search over a tree that holds an env file."""
    args = simple.argv[1:]
    if simple.program in GREPS:
        wide = any(
            a in ("--recursive", "--dereference-recursive")
            or (a.startswith("-") and not a.startswith("--") and set(a[1:]) & {"r", "R"})
            for a in args
        )
    elif simple.program in HIDDEN_SEARCH:
        wide = any(a in HIDDEN_SEARCH[simple.program] for a in args)
    elif simple.program == "git" and args[:1] == ["grep"]:
        wide = any(a in ("--untracked", "--no-index") for a in args)
    else:
        return False
    if not wide or _excluded(args):
        return False
    return any(env_files_under(root) for root in _search_roots(simple, cwd))


def _archives_secrets(simple: shell.Simple, cwd: Path) -> bool:
    args = simple.argv[1:]
    creating = (
        simple.program == "tar"
        and (any(a.startswith("-") and "c" in a for a in args) or (args and "c" in args[0]))
    ) or simple.program in ("zip", "7z")
    if not creating or _excluded(args):
        return False
    sources = [cwd / a for a in args if not a.startswith("-") and (cwd / a).is_dir()]
    return any(env_files_under(source) for source in sources)


def _env_files(env: Env, event: Event) -> list[Path]:
    roots = {event.cwd, *([env.project.root] if env.project else [])}
    return list(dict.fromkeys(path for root in roots for path in env_files_under(root)))


def secrets(env: Env, event: Event) -> tuple[set[str], set[str]]:
    """The names and the secret-looking values in the project's env files."""
    names, values = set(), set()
    for path in _env_files(env, event):
        for line in path.read_text("utf-8", errors="replace").splitlines():
            if match := ASSIGN.match(line.strip()):
                value = match.group(2).strip().strip("'\"")
                if len(value) >= MIN_SECRET and value.lower() not in ("true", "false"):
                    names.add(match.group(1))
                    values.add(value)
    return names, values


def _references(command: str, names: set[str]) -> bool:
    return "${!" in command or any(
        re.search(rf"\$\{{?{re.escape(name)}\b", command) for name in names
    )


def _leaks_secret(command: str, simples: list[shell.Simple], env: Env, event: Event) -> str | None:
    names, values = secrets(env, event)
    networked = "://" in command or any(simple.program in NETWORK for simple in simples)
    if networked and (any(value in command for value in values) or _references(command, names)):
        return "the command sends a secret from the project's env files to the network (D019)"
    for simple in simples:
        words = " ".join(simple.argv[1:])
        if simple.program in PRINTERS and _references(words, names):
            return "the command prints a secret variable from the project's env files"
        if simple.program in READERS and any(paths.hidden(w) for w in simple.argv[1:]):
            return "a reader on a file named by a variable may print .env; name the file"
    return None


def _dumps(simple: shell.Simple) -> bool:
    args = [a for a in simple.argv[1:] if a not in ("-0", "--null")]
    if simple.program in ("env", "printenv"):
        return not [a for a in args if not a.startswith("-") and "=" not in a]
    if simple.program in ("set", "export"):
        return not args or args == ["-p"]
    if simple.program in ("declare", "typeset"):
        return bool(set(args) & {"-p", "-x"}) and not [a for a in args if not a.startswith("-")]
    return simple.program == "compgen"


def _sources_env(simples: list[shell.Simple], cwd: Path, env: Env) -> bool:
    return any(
        s.program in ("source", ".") and _uses_env_file(s, cwd, env) for s in simples
    ) or any(s.program == "set" and "-a" in s.argv for s in simples)


def _per_folder(simple: shell.Simple, cwd: Path, env: Env) -> str | None:
    if what := _prints(simple, cwd, env):
        return f"{what}; .env values never reach the chat (D022)"
    if _searches_secrets(simple, cwd):
        return (
            "a recursive or hidden-file search here reads .env; exclude it "
            "(--exclude='.env*', -g '!.env*')"
        )
    if _archives_secrets(simple, cwd):
        return "an archive of a folder holding .env; exclude it (--exclude='.env*')"
    return None


def check_bash(event: Event, env: Env) -> Verdict | None:
    """No env file printed, copied or sent; no secret value or name going to the network."""
    command = str(event.tool_input.get("command", ""))
    try:
        simples = shell.commands(command)
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    if leak := _leaks_secret(command, simples, env, event):
        return Verdict(deny=f"refused: {leak}; the owner runs such commands himself.")
    for simple, folders in paths.walk(simples, event.cwd, env):
        for cwd in folders:
            if problem := _per_folder(simple, cwd, env):
                return Verdict(deny=f"refused: {problem}.")
    if _sources_env(simples, event.cwd, env) and any(_dumps(s) for s in simples):
        return Verdict(deny="refused: loading .env and dumping the environment prints secrets.")
    return None


def _grep_glob_hits_env(pattern: str) -> bool:
    for part in re.sub(r"[{}]", ",", pattern).split(","):
        name = PurePosixPath(part.strip()).name
        if name and (fnmatch.fnmatch(".env", name) or is_env_name(name)):
            return True
    return False


def check_tool(event: Event, env: Env) -> Verdict | None:
    """Read, Grep and notebook reads never open env files, symlinks included."""
    data = event.tool_input
    targets = [
        str(data.get(key)) for key in ("file_path", "path", "notebook_path") if data.get(key)
    ]
    hits = [t for t in targets if names_env_file(t, event.cwd, env)]
    if hits or _grep_glob_hits_env(str(data.get("glob") or "")):
        return Verdict(deny="opening .env files refused: their values never reach the chat.")
    return None


READ_TOOLS = {"Read", "Grep", "NotebookRead"}
RULES = [
    Rule("env-print", frozenset({"PreToolUse"}), GUARD, check_bash, lambda e: e.tool == "Bash"),
    Rule("env-read", frozenset({"PreToolUse"}), GUARD, check_tool, lambda e: e.tool in READ_TOOLS),
]
