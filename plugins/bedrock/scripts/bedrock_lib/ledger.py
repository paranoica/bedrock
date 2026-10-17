"""The agent ledger: one line per agent run, and the weighted spend read from a transcript."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import clock, jsonl
from .config import UserConfig

REQUIRED = (
    "project",
    "role",
    "model",
    "reason",
    "estimate",
    "actual",
    "turns",
    "cap_hit",
    "accepted",
)
REASONS = {"a", "b", "c", "fork"}
WEIGHTS = {"input": 1.0, "cache_5m": 1.25, "cache_1h": 2.0, "cache_read": 0.1, "output": 5.0}


class LedgerError(Exception):
    """A ledger entry is incomplete or invalid."""


@dataclass(frozen=True)
class Spend:
    """Spend of one agent run, in weighted tokens of its own model."""

    weighted: float
    turns: int
    start_context: int
    peak_context: int


def path(cfg: UserConfig) -> Path:
    """Return the ledger file."""
    return cfg.state_dir / "ledger.jsonl"


def _check(entry: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED if key not in entry]
    if missing:
        raise LedgerError(f"missing fields: {', '.join(missing)}")
    if entry["reason"] not in REASONS:
        raise LedgerError(f"reason must be one of {sorted(REASONS)}")
    for key in ("project", "role", "model"):
        if not isinstance(entry[key], str) or not entry[key]:
            raise LedgerError(f"{key} must be a non-empty string")
    for key in ("estimate", "actual", "turns"):
        value = entry[key]
        whole = key == "turns"
        kinds = (int,) if whole else (int, float)
        if isinstance(value, bool) or not isinstance(value, kinds) or not 0 <= value < math.inf:
            raise LedgerError(f"{key} must be a non-negative {'integer' if whole else 'number'}")
    if not isinstance(entry["cap_hit"], bool):
        raise LedgerError("cap_hit must be true or false")
    if entry["accepted"] is not None and not isinstance(entry["accepted"], bool):
        raise LedgerError("accepted must be true, false, or null until reviewed")


def add(cfg: UserConfig, entry: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Validate and append one agent run; return the stored record."""
    _check(entry)
    record = {"ts": clock.iso(now or clock.now_utc()), **entry}
    jsonl.append(path(cfg), record)
    return record


def records(cfg: UserConfig) -> list[dict[str, Any]]:
    """Return every ledger record, oldest first."""
    return jsonl.read(path(cfg))


def summary(cfg: UserConfig, since: datetime | None = None) -> dict[str, dict[str, float]]:
    """Totals per role: runs, estimated and actual spend, cap hits, accepted results."""
    totals: dict[str, dict[str, float]] = {}
    for record in records(cfg):
        if since is not None and clock.parse(record["ts"]) < since:
            continue
        row = totals.setdefault(
            record["role"],
            {"count": 0, "estimate": 0.0, "actual": 0.0, "cap_hits": 0, "accepted": 0},
        )
        row["count"] += 1
        row["estimate"] += float(record["estimate"])
        row["actual"] += float(record["actual"])
        row["cap_hits"] += 1 if record["cap_hit"] else 0
        row["accepted"] += 1 if record["accepted"] else 0
    return totals


def _weigh(usage: dict[str, Any]) -> tuple[float, int]:
    creation = usage.get("cache_creation") or {}
    five = creation.get("ephemeral_5m_input_tokens", 0) if creation else 0
    hour = creation.get("ephemeral_1h_input_tokens", 0) if creation else 0
    if not creation:
        five = usage.get("cache_creation_input_tokens", 0)
    fresh = usage.get("input_tokens", 0)
    cached = usage.get("cache_read_input_tokens", 0)
    weighted = (
        fresh * WEIGHTS["input"]
        + five * WEIGHTS["cache_5m"]
        + hour * WEIGHTS["cache_1h"]
        + cached * WEIGHTS["cache_read"]
        + usage.get("output_tokens", 0) * WEIGHTS["output"]
    )
    context = fresh + cached + usage.get("cache_creation_input_tokens", five + hour)
    return weighted, context


def transcript_spend(transcript: Path) -> Spend:
    """Read a Claude Code transcript and return its weighted spend, one request per message id."""
    usages: dict[str, dict[str, Any]] = {}
    with transcript.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise LedgerError(f"{transcript}:{number}: {error.msg}") from error
            message = record.get("message") or {}
            if record.get("type") != "assistant" or not message.get("usage") or "id" not in message:
                continue
            if message.get("model") == "<synthetic>":
                continue
            usages[message["id"]] = message["usage"]
    weighed = [_weigh(usage) for usage in usages.values()]
    contexts = [context for _, context in weighed]
    return Spend(
        weighted=sum(weight for weight, _ in weighed),
        turns=len(weighed),
        start_context=contexts[0] if contexts else 0,
        peak_context=max(contexts, default=0),
    )
