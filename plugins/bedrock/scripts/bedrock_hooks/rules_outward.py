"""Outward and irreversible actions outside git (D016, D019, D022.15, D044).

Deploy, cloud, data, messages, remote shells, catastrophic deletes, the owner's `~/.claude`,
new libraries and MCP writes.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from bedrock_hooks import gate, paths, shell, web_calls
from bedrock_hooks.core import GUARD, Env, Event, Rule, Verdict
from bedrock_hooks.gate import Action

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", ""}
RUNNERS = {"npx", "bunx", "pnpx", "uvx"}
SCRIPT_RUNNERS = {"npm", "pnpm", "yarn", "bun"}
DEPLOY_TOOLS = {
    "kubectl": (
        {"apply", "create", "replace", "patch", "scale", "rollout", "set", "edit"},
        {"delete"},
    ),
    "helm": ({"install", "upgrade", "rollback"}, {"uninstall", "delete"}),
    "terraform": ({"apply", "import", "taint", "untaint"}, {"destroy"}),
    "tofu": ({"apply", "import"}, {"destroy"}),
    "pulumi": ({"up", "import"}, {"destroy"}),
    "serverless": ({"deploy"}, {"remove"}),
    "sls": ({"deploy"}, {"remove"}),
    "sam": ({"deploy", "sync"}, {"delete"}),
    "cdk": ({"deploy"}, {"destroy"}),
    "fly": ({"deploy"}, {"destroy"}),
    "flyctl": ({"deploy"}, {"destroy"}),
    "netlify": ({"deploy"}, set()),
}  # fmt: skip
PUBLISH = {
    ("npm", "publish"), ("pnpm", "publish"), ("yarn", "publish"), ("docker", "push"),
    ("twine", "upload"), ("gem", "push"), ("cargo", "publish"), ("poetry", "publish"),
    ("uv", "publish"),
}  # fmt: skip
AWS_READ = ("describe", "list", "get", "head", "scan", "query", "filter", "lookup", "search")
AWS_READ += ("tail", "wait", "help", "batch-get", "test-", "validate", "estimate")
AWS_DELETE = ("delete", "terminate", "remove", "purge", "deregister")
DB_CLIENTS = {"psql", "mysql", "mariadb", "mongosh", "mongo", "redis-cli", "cqlsh"}
SQL_DESTROY = re.compile(r"\b(?:DROP|TRUNCATE)\b|\bDELETE\s+FROM\b(?![^;]*\bWHERE\b)", re.I)
SQL_WRITE = re.compile(r"\b(?:INSERT|UPDATE|DELETE|CREATE|ALTER|GRANT|REVOKE|MERGE)\b", re.I)
MIGRATIONS = (
    (("prisma", "migrate", "deploy"), False), (("prisma", "migrate", "reset"), True),
    (("prisma", "db", "push"), False), (("alembic", "upgrade"), False),
    (("alembic", "downgrade"), False), (("rails", "db:migrate"), False),
    (("rails", "db:drop"), True), (("rails", "db:reset"), True),
    (("knex", "migrate:latest"), False), (("sequelize", "db:migrate"), False),
    (("flyway", "migrate"), False), (("flyway", "clean"), True),
    (("typeorm", "migration:run"), False), (("drizzle-kit", "push"), False),
)  # fmt: skip
MAILERS = {"sendmail", "mail", "mailx", "mutt", "msmtp", "swaks"}
CURL_DATA = {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "-F", "--form"}
CURL_DATA |= {"-T", "--upload-file", "--json"}
CURL_DATA_PREFIXES = ("--data", "--json", "--form", "--upload-file", "-d", "-F", "-T")
CURL_VALUED = {"-H", "--header", "-o", "--output", "-u", "--user", "-A", "--user-agent", "-e"}
CURL_VALUED |= {"-X", "--request", "-d", "--data", "-F", "--form", "-T", "--upload-file"}
CURL_VALUED |= {"--data-raw", "--data-binary", "--data-urlencode", "--json", "-b", "--cookie"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CATASTROPHIC = {"/", "/*", "~", "~/", "$HOME", "${HOME}", ".", "..", "*", "./*", "~/*", ".git"}
SLACK_NEVER = {"slack_send_message", "slack_schedule_message"}
MCP_READ_VERBS = {"read", "get", "list", "search", "query", "fetch", "resolve", "lookup", "find"}
MCP_READ_VERBS |= {"view", "describe", "guide", "authenticate", "complete"}
MCP_ALLOWED = ("mcp__claude_ai_Claude_Docs__",)


def unrun(argv: list[str]) -> list[str]:
    """Drop package runners (`npx x`, `uv run x`, `poetry run x`) to see the real program."""
    words = list(argv)
    program = PurePosixPath(words[0]).name
    if program in RUNNERS:
        rest = words[1:]
        while rest and rest[0].startswith("-"):
            option = rest.pop(0)
            if option in ("-p", "--package", "--from", "--with") and rest:
                rest.pop(0)
        words = rest or words
    elif (
        (program in ("uv", "poetry", "pipenv", "pdm") and words[1:2] == ["run"])
        or (program in ("pnpm", "yarn") and words[1:2] in (["exec"], ["dlx"]))
        or (program.startswith("python") and words[1:2] == ["-m"])
    ):
        words = words[2:] or words
    return words


def _local(host: str) -> bool:
    return host.lower().split(":")[0] in LOCAL_HOSTS or host.endswith(".localhost")


def _project_deploys(env: Env, argv: list[str]) -> list[Action]:
    commands = (env.project.data.get("commands") if env.project else None) or {}
    for name, spec in commands.items():
        if not name.startswith(("deploy", "release", "publish")) or not isinstance(spec, dict):
            continue
        run = shlex.split(str(spec.get("run", "")))
        via_bedrock = argv[:3] == ["bedrock", "cmd", name]
        if via_bedrock or (run and argv[: len(run)] == run):
            kind = "deploy-prod" if "prod" in name else "deploy"
            return [Action(kind, f"the project command '{name}'", None)]
    return []


def _script_deploy(argv: list[str]) -> list[Action]:
    program = PurePosixPath(argv[0]).name
    if program in SCRIPT_RUNNERS and argv[1:2] == ["run"] and len(argv) > 2:
        script = argv[2]
        if script.startswith(("deploy", "release", "publish")):
            return [
                Action("deploy-prod" if "prod" in script else "deploy", f"`{program} run {script}`")
            ]
    return []


def _deploy_tools(argv: list[str]) -> list[Action]:
    program = PurePosixPath(argv[0]).name
    sub = argv[1] if len(argv) > 1 else ""
    if (program, sub) in PUBLISH:
        return [Action("publish", f"`{program} {sub}`")]
    if program == "vercel" and (sub in ("", "deploy") or sub.startswith("-")):
        return [Action("deploy-prod" if "--prod" in argv else "deploy", "a vercel deploy")]
    if program in DEPLOY_TOOLS:
        writes, destroys = DEPLOY_TOOLS[program]
        if sub in destroys:
            return [Action("data-delete", f"`{program} {sub}`", program, level4=True)]
        if sub in writes:
            prod = "--prod" in argv
            return [Action("deploy-prod" if prod else "deploy", f"`{program} {sub}`")]
    return []


def _aws(argv: list[str]) -> list[Action]:
    if PurePosixPath(argv[0]).name != "aws" or len(argv) < 3:
        return []
    service, operation = argv[1], argv[2]
    positional = [arg for arg in argv[3:] if not arg.startswith("-")]
    if service in ("configure", "sts") or operation.startswith(AWS_READ):
        return []
    if service == "s3":
        if operation in ("ls", "presign"):
            return []
        if operation in ("rm", "rb"):
            return [Action("data-delete", f"`aws s3 {operation}`", "s3", level4=True)]
        if operation in ("cp", "sync", "mv") and not (
            positional and positional[-1].startswith("s3://")
        ):
            return []
    if operation.startswith(AWS_DELETE):
        return [Action("data-delete", f"`aws {service} {operation}`", service, level4=True)]
    return [Action("aws-write", f"`aws {service} {operation}`")]


def _db_target(argv: list[str]) -> str:
    for index, arg in enumerate(argv):
        if "://" in arg:
            return urlparse(arg).hostname or ""
        if arg in ("-h", "--host") and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--host="):
            return arg.split("=", 1)[1]
    return ""


def _database(argv: list[str]) -> list[Action]:
    if PurePosixPath(argv[0]).name not in DB_CLIENTS or _local(_db_target(argv)):
        return []
    statements = [
        argv[index + 1]
        for index, arg in enumerate(argv[:-1])
        if arg in ("-c", "--command", "-e", "--execute", "--eval")
    ]
    text = " ".join(statements)
    if SQL_DESTROY.search(text):
        return [Action("data-delete", "destructive SQL on a shared database", "db", level4=True)]
    if not statements or SQL_WRITE.search(text):
        return [Action("db-write", "writing to a shared database")]
    return []


def _migration(argv: list[str], raw: str) -> list[Action]:
    words = unrun(argv)
    names = [PurePosixPath(words[0]).name, *words[1:]]
    if names[0].startswith("python") and len(names) > 2 and names[1].endswith("manage.py"):
        names = ["manage.py", *names[2:]]
    for pattern, destroys in (*MIGRATIONS, (("manage.py", "migrate"), False)):
        if tuple(names[: len(pattern)]) == pattern:
            if "localhost" in raw or "127.0.0.1" in raw:
                return []
            if destroys:
                return [Action("data-delete", f"`{' '.join(pattern)}`", "db", level4=True)]
            return [Action("migrate", f"the migration `{' '.join(pattern)}`")]
    return []


def _remote(argv: list[str]) -> list[Action]:
    program = PurePosixPath(argv[0]).name
    if program in MAILERS:
        return [Action("message", "sending mail")]
    if program == "ssh":
        return [Action("remote-exec", "running a command on a remote machine")]
    if program in ("scp", "rsync", "sftp"):
        remote = [a for a in argv[1:] if re.match(r"^[\w.@-]+:", a) and not a.startswith("-")]
        if remote:
            return [Action("remote-write", "copying to a remote machine")]
    return []


def _in_claude(env: Env, path: Path) -> bool:
    claude = Path(os.path.realpath(paths.home(env) / ".claude"))
    if not path.is_relative_to(claude):
        return False
    parts = path.relative_to(claude).parts
    return not (len(parts) >= 3 and parts[0] == "projects" and parts[2] == "memory")


FIND_FILTERS = {"-name", "-iname", "-path", "-ipath", "-regex", "-type", "-newer", "-mtime"}


def _dangerous_target(env: Env, word: str, cwd: Path) -> bool:
    if paths.hidden(word):
        return True
    path = paths.expand(env, word, cwd)
    home = paths.home(env)
    shallow = len(path.parts) <= 2
    near_home = path == home or path.parent == home
    return word in CATASTROPHIC or path.name == ".git" or shallow or near_home


def _find(env: Env, argv: list[str], cwd: Path) -> list[Action]:
    if not any(a in ("-delete", "-exec", "-execdir") for a in argv):
        return []
    roots = [a for a in argv[1:] if not a.startswith("-")][:1]
    if not roots:
        return []
    filtered = bool(FIND_FILTERS & set(argv))
    if roots[0] in (".", "./") and filtered:
        return []
    if _dangerous_target(env, roots[0], cwd):
        return [Action("data-delete", f"`find {roots[0]}` deleting", roots[0], level4=True)]
    return []


def _rsync_delete(env: Env, argv: list[str], cwd: Path) -> list[Action]:
    if not any(a.startswith("--delete") for a in argv):
        return []
    positional = [a for a in argv[1:] if not a.startswith("-")]
    if positional and ":" not in positional[-1] and _dangerous_target(env, positional[-1], cwd):
        return [Action("data-delete", "`rsync --delete` into a top folder", None, level4=True)]
    return []


def _catastrophic(env: Env, argv: list[str], cwd: Path) -> list[Action]:
    program = PurePosixPath(argv[0]).name
    if program == "find":
        return _find(env, argv, cwd)
    if program == "rsync":
        return _rsync_delete(env, argv, cwd)
    if program != "rm":
        return []
    flags = "".join(a.lstrip("-") for a in argv[1:] if a.startswith("-") and not a.startswith("--"))
    recursive = "r" in flags.lower() or "--recursive" in argv
    forced = "f" in flags or "--force" in argv
    if not (recursive and forced):
        return []
    targets = [a for a in argv[1:] if not a.startswith("-")]
    if not targets:
        return [Action("data-delete", "`rm -rf` with targets from its input", None, level4=True)]
    for target in targets:
        if _dangerous_target(env, target, cwd):
            return [Action("data-delete", f"`rm -rf {target}`", target, level4=True)]
    return []


def _claude_writes(env: Env, simple: shell.Simple, cwd: Path) -> list[Action]:
    if any(_in_claude(env, target) for target in paths.write_targets(simple, cwd, env)):
        return [Action("claude-config", "changing the owner's ~/.claude")]
    return []


def classify(env: Env, event: Event, simple: shell.Simple, cwd: Path) -> list[Action]:
    """Return the outward or irreversible actions of one simple command."""
    argv = simple.argv
    command = str(event.tool_input.get("command", ""))
    for finder in (_project_deploys,):
        if found := finder(env, argv):
            return found
    found: list[Action] = []
    for check in (_script_deploy, _deploy_tools, _aws, _database, web_calls.http_write, _remote):
        found += check(unrun(argv) if check is _deploy_tools else argv)
    found += _migration(argv, command)
    found += _catastrophic(env, argv, cwd)
    found += _claude_writes(env, simple, cwd)
    return found


def check_bash(event: Event, env: Env) -> Verdict | None:
    """Judge a Bash command's outward effects."""
    try:
        simples = shell.commands(str(event.tool_input.get("command", "")))
    except shell.ParseError as error:
        return Verdict(deny=f"bedrock could not judge this command safely ({error}); simplify it.")
    seen: dict[tuple[str, str | None], Action] = {}
    for simple, folders in paths.walk(simples, event.cwd, env):
        for folder in folders:
            for action in classify(env, event, simple, folder):
                seen.setdefault((action.kind, action.target), action)
    actions = list(seen.values())
    if not actions:
        return None
    if event.agent_id:
        return Verdict(
            deny=f"refused for an agent: {actions[0].why}; agents never act outward (D005)."
        )
    return gate.decide(env, event, actions)


def check_edit(event: Event, env: Env) -> Verdict | None:
    """File tools writing into the owner's `~/.claude` need a grant."""
    path = event.tool_input.get("file_path") or event.tool_input.get("notebook_path")
    if not path or not _in_claude(env, paths.expand(env, str(path), event.cwd)):
        return None
    return gate.decide(env, event, [Action("claude-config", "changing the owner's ~/.claude")])


EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
RULES = [
    Rule("outward", frozenset({"PreToolUse"}), GUARD, check_bash, lambda e: e.tool == "Bash"),
    Rule(
        "claude-folder",
        frozenset({"PreToolUse"}),
        GUARD,
        check_edit,
        lambda e: e.tool in EDIT_TOOLS,
    ),
]
