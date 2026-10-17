"""New dependencies of a change, checked against their registries (slopsquatting, D022.15)."""

from __future__ import annotations

import json
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .codecheck import Change

NPM_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
MIN_AGE_DAYS = 90
MIN_WEEKLY_DOWNLOADS = 1000


class RegistryError(Exception):
    """A registry could not be reached, so a package could not be verified."""


def _npm_names(text: str | None) -> set[str]:
    if not text:
        return set()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    return {name for section in NPM_SECTIONS for name in (data.get(section) or {})}


def _requirement_names(lines: Iterable[str]) -> set[str]:
    names = set()
    for line in lines:
        stripped = line.strip()
        match = REQUIREMENT.match(stripped)
        if match and not stripped.startswith(("#", "-")):
            names.add(match.group(1).lower())
    return names


def _pyproject_names(text: str | None) -> set[str]:
    if not text:
        return set()
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return set()
    project = data.get("project", {})
    specs = list(project.get("dependencies", []))
    for group in (project.get("optional-dependencies") or {}).values():
        specs += group
    for group in (data.get("dependency-groups") or {}).values():
        specs += [spec for spec in group if isinstance(spec, str)]
    return _requirement_names(specs)


def added_dependencies(changes: Iterable[Change]) -> set[tuple[str, str]]:
    """Return (ecosystem, name) for every dependency the changes add."""
    added: set[tuple[str, str]] = set()
    for change in changes:
        name = PurePosixPath(change.path).name
        if name == "package.json":
            new = _npm_names(change.new) - _npm_names(change.old)
            added |= {("npm", dep) for dep in new}
        elif re.fullmatch(r"requirements[\w.-]*\.txt", name):
            old = _requirement_names((change.old or "").splitlines())
            new = _requirement_names((change.new or "").splitlines()) - old
            added |= {("pypi", dep) for dep in new}
        elif name == "pyproject.toml":
            new = _pyproject_names(change.new) - _pyproject_names(change.old)
            added |= {("pypi", dep) for dep in new}
    return added


def fetch_json(url: str) -> dict[str, Any] | None:
    """GET a JSON document; None on 404, OSError when the registry cannot be reached."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def _age_days(stamp: str, now: float) -> float:
    return (now - datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()) / 86400


def _optional(fetch: Callable[[str], dict[str, Any] | None], url: str) -> dict[str, Any] | None:
    # Download counts are a second signal: a failed lookup leaves them unknown, not the check.
    try:
        return fetch(url)
    except OSError:
        return None


def _registry_facts(
    ecosystem: str, name: str, fetch: Callable[[str], dict[str, Any] | None]
) -> tuple[bool, str | None, int | None]:
    quoted = urllib.parse.quote(name, safe="@")
    if ecosystem == "npm":
        meta = fetch(f"https://registry.npmjs.org/{quoted.replace('/', '%2F')}")
        if meta is None:
            return False, None, None
        weekly = _optional(fetch, f"https://api.npmjs.org/downloads/point/last-week/{quoted}")
        return True, (meta.get("time") or {}).get("created"), (weekly or {}).get("downloads")
    meta = fetch(f"https://pypi.org/pypi/{quoted}/json")
    if meta is None:
        return False, None, None
    uploads = [
        item.get("upload_time_iso_8601")
        for files in (meta.get("releases") or {}).values()
        for item in files
        if item.get("upload_time_iso_8601")
    ]
    recent = _optional(fetch, f"https://pypistats.org/api/packages/{quoted.lower()}/recent")
    weekly = ((recent or {}).get("data") or {}).get("last_week")
    return True, min(uploads) if uploads else None, weekly


def check(
    packages: Iterable[tuple[str, str]],
    fetch: Callable[[str], dict[str, Any] | None] = fetch_json,
    now: float | None = None,
) -> list[tuple[str, str]]:
    """Return (package, problem) for new packages that are missing, too new or barely used."""
    moment = time.time() if now is None else now
    found: list[tuple[str, str]] = []
    for ecosystem, name in packages:
        label = f"{ecosystem}:{name}"
        try:
            exists, created, weekly = _registry_facts(ecosystem, name, fetch)
        except OSError as error:
            raise RegistryError(f"cannot verify {label}: {error}") from error
        if not exists:
            found.append((label, "not in the registry: a made-up name?"))
            continue
        if created and _age_days(created, moment) < MIN_AGE_DAYS:
            found.append((label, "younger than 90 days: check who made it"))
        if weekly is not None and weekly < MIN_WEEKLY_DOWNLOADS:
            message = f"under {MIN_WEEKLY_DOWNLOADS} downloads a week: {weekly}"
            found.append((label, message))
    return found
