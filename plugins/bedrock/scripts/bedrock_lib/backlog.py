"""The project backlog: `backlog.json` is the only source of task state, `backlog.md` its render.

Both live in the project's knowledge-base folder, never in a client repository. State changes
only through this module; a hand edit of either file shows up in `validate`.
"""

from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import clock
from .config import SAFE_NAME, UserConfig

PRIORITIES = ("P0", "P1", "P2", "P3")
RISKS = ("R1", "R2", "R3")
STATES = ("todo", "doing", "done", "blocked", "dropped")
MARK = {"todo": "[ ]", "doing": "[~]", "done": "[x]", "blocked": "[/]", "dropped": "[-]"}
WHO = re.compile(r"session|agent:[a-z0-9.-]+")
BANNER = "<!-- GENERATED from backlog.json by `bedrock backlog` — do not edit by hand. -->"


class BacklogError(Exception):
    """A backlog request is invalid or the backlog files are broken."""


def _folder(cfg: UserConfig, project: str) -> Path:
    if not SAFE_NAME.match(project):
        raise BacklogError(f"project name '{project}' is not a safe folder name")
    return cfg.memory_bank_dir / project


def _load(folder: Path) -> dict[str, Any]:
    try:
        data = json.loads((folder / "backlog.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"next_id": 1, "tasks": []}
    except json.JSONDecodeError as error:
        raise BacklogError(f"{folder / 'backlog.json'}: {error.msg}") from error
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise BacklogError(f"{folder / 'backlog.json'} has no task list")
    return data


def _write(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def render(project: str, data: dict[str, Any]) -> str:
    """Render the backlog as markdown, grouped by priority."""
    lines = [BANNER, "", f"# Backlog — {project}", ""]
    for priority in PRIORITIES:
        group = [t for t in data["tasks"] if t.get("priority") == priority]
        if not group:
            continue
        lines += [f"## {priority}", ""]
        for task in group:
            extra = [task.get("risk", "")]
            if task.get("estimate_min"):
                extra.append(f"{task['estimate_min']}m")
            if task.get("depends"):
                extra.append("after " + ", ".join(task["depends"]))
            if task.get("claimed_by"):
                extra.append(f"claimed by {task['claimed_by']}")
            mark = MARK.get(task.get("status", ""), "[?]")
            lines.append(f"- {mark} **{task['id']}** {task['title']} — {' · '.join(extra)}")
            lines += [f"    - {note}" for note in task.get("notes", [])]
        lines.append("")
    return "\n".join(lines)


@contextmanager
def _editing(cfg: UserConfig, project: str) -> Iterator[dict[str, Any]]:
    folder = _folder(cfg, project)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".backlog.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = _load(folder)
        yield data
        _write(folder / "backlog.json", json.dumps(data, indent=1, ensure_ascii=False) + "\n")
        _write(folder / "backlog.md", render(project, data))


def tasks(cfg: UserConfig, project: str) -> list[dict[str, Any]]:
    """Return every task in insertion order."""
    return _load(_folder(cfg, project))["tasks"]


def _find(data: dict[str, Any], task_id: str) -> dict[str, Any]:
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise BacklogError(f"no task '{task_id}'")


def get(cfg: UserConfig, project: str, task_id: str) -> dict[str, Any]:
    """Return one task."""
    return _find(_load(_folder(cfg, project)), task_id)


def _check_list(fields: dict[str, Any], key: str) -> None:
    value = fields.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BacklogError(f"{key} must be a list of strings")


CHECKS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("title", lambda v: isinstance(v, str) and bool(v.strip()), "a non-empty string"),
    ("priority", lambda v: v in PRIORITIES, "one of " + ", ".join(PRIORITIES)),
    ("risk", lambda v: v in RISKS, "one of " + ", ".join(RISKS)),
    ("who", lambda v: isinstance(v, str) and bool(WHO.fullmatch(v)), "session or agent:<model>"),
    (
        "estimate_min",
        lambda v: v is None or (type(v) is int and v > 0),
        "a positive whole number of minutes",
    ),
    ("night_ok", lambda v: isinstance(v, bool), "true or false"),
    ("test", lambda v: isinstance(v, str), "a string"),
)


def _check(fields: dict[str, Any], known: set[str]) -> None:
    defaults = {"who": "session", "night_ok": False, "test": "", "estimate_min": None}
    for key, valid, wanted in CHECKS:
        if not valid(fields.get(key, defaults.get(key))):
            raise BacklogError(f"{key} must be {wanted}")
    for key in ("files", "depends", "refs"):
        _check_list(fields, key)
    missing = [dep for dep in fields.get("depends", []) if dep not in known]
    if missing:
        raise BacklogError(f"unknown dependencies: {', '.join(missing)}")


def add(cfg: UserConfig, project: str, fields: dict[str, Any]) -> str:
    """Add a task and return its id."""
    with _editing(cfg, project) as data:
        _check(fields, {task["id"] for task in data["tasks"]})
        task_id = f"T{data['next_id']}"
        data["next_id"] += 1
        data["tasks"].append(
            {
                "id": task_id,
                "title": fields["title"].strip(),
                "priority": fields["priority"],
                "risk": fields["risk"],
                "status": "todo",
                "who": fields.get("who", "session"),
                "estimate_min": fields.get("estimate_min"),
                "files": fields.get("files", []),
                "test": fields.get("test", ""),
                "depends": fields.get("depends", []),
                "refs": fields.get("refs", []),
                "night_ok": fields.get("night_ok", False),
                "claimed_by": None,
                "notes": [],
                "added": clock.iso(clock.now_utc()),
            }
        )
    return task_id


def _unmet(data: dict[str, Any], task: dict[str, Any]) -> list[str]:
    done = {t["id"] for t in data["tasks"] if t["status"] in ("done", "dropped")}
    return [dep for dep in task.get("depends", []) if dep not in done]


def next_task(
    cfg: UserConfig, project: str, *, night: bool = False, session: str | None = None
) -> dict[str, Any] | None:
    """Return the most urgent ready task: unclaimed (or this session's), dependencies done."""
    data = _load(_folder(cfg, project))
    ready = [
        task
        for task in data["tasks"]
        if task["status"] in ("todo", "doing")
        and task.get("claimed_by") in (None, session)
        and not _unmet(data, task)
        and (task.get("night_ok") or not night)
    ]
    ready.sort(key=lambda task: PRIORITIES.index(task["priority"]))
    return ready[0] if ready else None


def claim(cfg: UserConfig, project: str, task_id: str, session: str) -> None:
    """Take a task for a session; another session's claim or unmet dependencies refuse it."""
    with _editing(cfg, project) as data:
        task = _find(data, task_id)
        holder = task.get("claimed_by")
        if holder not in (None, session):
            raise BacklogError(f"{task_id} is claimed by session {holder}")
        if unmet := _unmet(data, task):
            raise BacklogError(f"{task_id} waits on {', '.join(unmet)}")
        if task["status"] not in ("todo", "doing"):
            raise BacklogError(f"{task_id} is {task['status']}, not open")
        task["claimed_by"] = session
        task["status"] = "doing"


def set_status(
    cfg: UserConfig, project: str, task_id: str, state: str, note: str | None = None
) -> None:
    """Move a task to a state; done needs its dependencies done, blocked needs a reason."""
    if state not in STATES:
        raise BacklogError(f"state must be one of {', '.join(STATES)}")
    if state == "blocked" and not note:
        raise BacklogError("a blocked task needs a note with the reason and what unblocks it")
    with _editing(cfg, project) as data:
        task = _find(data, task_id)
        if state == "done" and (unmet := _unmet(data, task)):
            raise BacklogError(f"{task_id} cannot be done before {', '.join(unmet)}")
        task["status"] = state
        if state != "doing":
            task["claimed_by"] = None
        if note:
            task.setdefault("notes", []).append(f"{clock.iso(clock.now_utc())} {note}")


def _cycle(data: dict[str, Any]) -> list[str] | None:
    graph = {task["id"]: task.get("depends", []) for task in data["tasks"]}
    visiting: list[str] = []
    finished: set[str] = set()

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            return [*visiting[visiting.index(node) :], node]
        if node in finished or node not in graph:
            return None
        visiting.append(node)
        for dep in graph[node]:
            if found := visit(dep):
                return found
        visiting.pop()
        finished.add(node)
        return None

    for node in graph:
        if found := visit(node):
            return found
    return None


def validate(cfg: UserConfig, project: str) -> list[str]:
    """Return problems: bad fields, dangling dependencies, cycles, a hand-edited render."""
    folder = _folder(cfg, project)
    data = _load(folder)
    ids = {task["id"] for task in data["tasks"]}
    problems = []
    for task in data["tasks"]:
        if task.get("status") not in STATES:
            problems.append(f"{task['id']}: bad status {task.get('status')!r}")
        problems += [
            f"{task['id']}: dangling dependency {dep}"
            for dep in task.get("depends", [])
            if dep not in ids
        ]
    if cycle := _cycle(data):
        problems.append("dependency cycle: " + " -> ".join(cycle))
    markdown = folder / "backlog.md"
    if data["tasks"] and (
        not markdown.exists() or markdown.read_text(encoding="utf-8") != render(project, data)
    ):
        problems.append("backlog.md is out of sync with backlog.json (hand edit?)")
    return problems
