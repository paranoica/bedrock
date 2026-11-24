"""Profile loading and rule resolution, shared by the linter and the profile builder.

A profile directory holds ``settings.toml`` (the owner's choices) and ``stats.json``
(measured from their messages). Each rule set to ``auto`` is decided from the stats,
so the guide the model reads and the checks lint runs come from one place.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 in some sandboxes
    tomllib = None  # type: ignore[assignment]

RULE_VALUES = {
    "yo": ("auto", "never", "allow"),
    "dashes": ("auto", "never", "allow"),
    "emoji": ("auto", "never", "allow"),
    "en_apostrophes": ("auto", "never", "allow"),
    "profanity": ("never", "mirror", "allow"),
}
PLATFORMS = ("plain", "slack", "telegram", "discord", "email")

DEFAULT_SETTINGS: dict[str, Any] = {
    "owner": "",
    "default_platform": "plain",
    "rules": {
        "yo": "auto",
        "dashes": "auto",
        "emoji": "auto",
        "en_apostrophes": "auto",
        "profanity": "mirror",
    },
    "stoplist": {"ru": [], "en": []},
    "registers": {},
}

# Without a profile: chat-like defaults that keep the text from reading as generated.
DEFAULT_COMMAS_RATE_P90 = 12.0
DEFAULT_WORDS_PER_BURST_P90 = 60.0

# Shares below these mean the owner practically never does it.
RARE_SHARE = 0.02
RARE_YO = 0.1
RARE_APOSTROPHE = 0.05
MIN_YO_EVIDENCE = 5
MIN_EN_MESSAGES = 20


class ProfileError(ValueError):
    """A profile file is missing or malformed."""


@dataclass(frozen=True)
class Rules:
    """Everything lint checks for one register.

    Hard rules are ``never`` or ``allow``; thresholds are the register's p90 values,
    ``None`` where there is nothing to compare against.
    """

    register: str | None = None
    lang: str | None = None
    yo: str = "never"
    dashes: str = "never"
    emoji: str = "allow"
    en_apostrophes: str = "allow"
    profanity: str = "mirror"
    stoplist: tuple[str, ...] = ()
    min_words: int = 5
    commas_rate_p90: float | None = DEFAULT_COMMAS_RATE_P90
    commas_per_burst_p90: float | None = None
    words_per_burst_p90: float | None = DEFAULT_WORDS_PER_BURST_P90
    messages_per_burst_p90: float | None = None
    capital_start_share: float | None = None
    period_end_share: float | None = None
    sources: dict[str, str] = field(default_factory=dict)


@dataclass
class Profile:
    """A loaded profile directory."""

    path: Path
    settings: dict[str, Any]
    stats: dict[str, Any]

    @property
    def registers(self) -> list[str]:
        return list(self.stats.get("registers", {}))

    def rules(self, register: str | None) -> Rules:
        """Resolves rules for a register; ``None`` or an unknown name raises."""
        regs = self.stats.get("registers", {})
        if register not in regs:
            known = ", ".join(regs) or "none"
            raise ProfileError(f"unknown register {register!r}; known: {known}")
        block = {**regs[register], "min_words_for_rate": self.stats.get("min_words_for_rate")}
        return resolve(self.settings, block, register)


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise ProfileError("reading settings.toml needs Python 3.11+")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path}: {exc}") from exc


def validate_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Merges user settings over the defaults and checks every value.

    Raises:
        ProfileError: Unknown keys or values outside the allowed sets.
    """
    for key in ("rules", "stoplist", "registers"):
        if not isinstance(data.get(key, {}), dict):
            raise ProfileError(f"settings: [{key}] must be a table")
    for name, override in data.get("registers", {}).items():
        if not isinstance(override, dict):
            raise ProfileError(f"settings: [registers.{name}] must be a table")
    unknown = set(data) - set(DEFAULT_SETTINGS)
    if unknown:
        raise ProfileError(f"settings: unknown key(s): {', '.join(sorted(unknown))}")
    rules = {**DEFAULT_SETTINGS["rules"], **data.get("rules", {})}
    _check_rules(rules, "settings.rules")
    platform = data.get("default_platform", DEFAULT_SETTINGS["default_platform"])
    if platform not in PLATFORMS:
        raise ProfileError(f"settings.default_platform must be one of {PLATFORMS}")
    stoplist = {**DEFAULT_SETTINGS["stoplist"], **data.get("stoplist", {})}
    for lang, phrases in stoplist.items():
        if not isinstance(phrases, list) or not all(isinstance(p, str) for p in phrases):
            raise ProfileError(f"settings.stoplist.{lang} must be a list of strings")
    registers = data.get("registers", {})
    for name, override in registers.items():
        _check_rules(override, f"settings.registers.{name}")
    return {
        "owner": str(data.get("owner", "")),
        "default_platform": platform,
        "rules": rules,
        "stoplist": stoplist,
        "registers": registers,
    }


def _check_rules(rules: dict[str, Any], where: str) -> None:
    for key, value in rules.items():
        if key not in RULE_VALUES:
            raise ProfileError(f"{where}: unknown rule {key!r}")
        if value not in RULE_VALUES[key]:
            raise ProfileError(f"{where}.{key} must be one of {RULE_VALUES[key]}, got {value!r}")


def load_profile(path: Path) -> Profile:
    """Reads settings (optional) and ``stats.json`` (required) from a profile dir.

    ``settings.toml`` is the source; the claude.ai package also carries a
    ``settings.json`` copy, read when ``tomllib`` is not available.
    """
    stats_path = path / "stats.json"
    if not stats_path.exists():
        raise ProfileError(f"{stats_path} not found; build the profile first")
    try:
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        if not isinstance(stats, dict) or not isinstance(stats.get("registers", {}), dict):
            raise ProfileError(f"{stats_path}: unexpected structure")
    except json.JSONDecodeError as exc:
        raise ProfileError(f"{stats_path}: {exc}") from exc
    toml_path, json_path = path / "settings.toml", path / "settings.json"
    if toml_path.exists() and (tomllib is not None or not json_path.exists()):
        raw = read_toml(toml_path)
    elif json_path.exists():
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ProfileError(f"{json_path}: {exc}") from exc
    else:
        raw = {}
    return Profile(path=path, settings=validate_settings(raw), stats=stats)


def _get(stats: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if not isinstance(stats, dict):
            return None
        stats = stats.get(key)  # type: ignore[assignment]
    return stats


def _auto_yo(stats: dict[str, Any]) -> tuple[str, str]:
    with_yo = _get(stats, "yo", "known_with_yo") or 0
    total = _get(stats, "yo", "known_total") or 0
    if total >= MIN_YO_EVIDENCE:
        verdict = "never" if with_yo / total < RARE_YO else "allow"
        return verdict, f"{with_yo} of {total} words that take it"
    share = _get(stats, "yo", "word_share")
    if share:
        return "allow", f"{share:.1%} of words"
    return "never", "not enough evidence, chat default"


def _auto_share(value: float | None, limit: float, fallback: str, label: str) -> tuple[str, str]:
    if value is None:
        return fallback, "no data, default"
    return ("never" if value < limit else "allow"), f"{value:.1%} of {label}"


def resolve(settings: dict[str, Any], stats: dict[str, Any] | None, register: str | None) -> Rules:
    """Turns settings plus a register's stats into concrete rules.

    A per-register override in ``settings.registers`` beats the global rule; ``auto``
    is decided from the stats.

    Args:
        settings: Validated settings (see :func:`validate_settings`).
        stats: The register's block from ``stats.json``, or ``None`` without a profile.
        register: Register name, for messages and per-register overrides.

    Returns:
        The resolved rules.
    """
    stats = stats or {}
    chosen = {**settings["rules"], **settings["registers"].get(register or "", {})}
    sources: dict[str, str] = {}
    resolved: dict[str, str] = {}

    autos = {
        "yo": lambda: _auto_yo(stats) if stats else ("never", "chat default"),
        "dashes": lambda: _auto_share(
            _get(stats, "dashes", "message_share"), RARE_SHARE, "never", "messages"
        ),
        "emoji": lambda: _auto_share(
            _get(stats, "emoji", "message_share"), RARE_SHARE, "allow", "messages"
        ),
        "en_apostrophes": lambda: (
            _auto_share(
                _get(stats, "en", "apostrophe_message_share"),
                RARE_APOSTROPHE,
                "allow",
                "English messages",
            )
            if (_get(stats, "en", "messages") or 0) >= MIN_EN_MESSAGES
            else ("allow", "not enough English messages")
        ),
    }
    for key, auto in autos.items():
        if chosen[key] == "auto":
            resolved[key], sources[key] = auto()
        else:
            resolved[key], sources[key] = chosen[key], "set in settings"

    stoplist = tuple(p for lang in ("ru", "en") for p in settings["stoplist"].get(lang, []))
    hard = {
        "yo": resolved["yo"],
        "dashes": resolved["dashes"],
        "emoji": resolved["emoji"],
        "en_apostrophes": resolved["en_apostrophes"],
        "profanity": chosen["profanity"],
    }
    if not stats:
        return Rules(register=register, stoplist=stoplist, sources=sources, **hard)
    return Rules(
        register=register,
        lang=stats.get("lang"),
        stoplist=stoplist,
        min_words=int(stats.get("min_words_for_rate") or 5),
        commas_rate_p90=_get(stats, "commas", "per_100_words_per_burst", "p90"),
        commas_per_burst_p90=_get(stats, "commas", "per_burst", "p90"),
        words_per_burst_p90=_get(stats, "words_per_burst", "p90"),
        messages_per_burst_p90=_get(stats, "messages_per_burst", "p90"),
        capital_start_share=stats.get("capital_start_share"),
        period_end_share=_get(stats, "ending", "period"),
        sources=sources,
        **hard,
    )


def default_rules(settings: dict[str, Any] | None = None) -> Rules:
    """Rules when there is no profile: chat defaults, optional settings applied."""
    return resolve(validate_settings(settings or {}), None, None)


def default_profile_dir(skill_dir: Path, environ: Mapping[str, str] | None = None) -> Path:
    """Return the profile folder: $HUMANIZE_PROFILE, `profile/` beside the skill, or config.

    The config folder is `~/.config/humanize/profile`. A skill installed from a plugin is replaced on every update, so a profile cannot live
    inside it; the config folder survives updates.
    """
    environ = environ if environ is not None else os.environ
    if configured := environ.get("HUMANIZE_PROFILE"):
        return Path(configured).expanduser()
    if (skill_dir / "profile").exists():
        return skill_dir / "profile"
    home = environ.get("HOME")
    return (Path(home) if home else Path.home()) / ".config" / "humanize" / "profile"
