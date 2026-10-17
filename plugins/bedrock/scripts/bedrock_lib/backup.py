"""Daily encrypted backup of the knowledge base and Claude's memory folders (D030 B10).

The archive is encrypted with `age` to the owner's public key and committed to a local backup
repository. This module never pushes: pushing is the owner's daily job, so the model cannot use
it to publish anything.
"""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
from datetime import date
from pathlib import Path

from .config import UserConfig

RECIPIENT = re.compile(
    r"age1[02-9ac-hj-np-z]{58,}|ssh-(?:ed25519|rsa) [A-Za-z0-9+/]+={0,2}(?: [^\n]+)?"
)


class BackupError(Exception):
    """The backup could not be made."""


def check_recipient(recipient: str) -> str:
    """Return the recipient when it is an age or SSH public key, else fail."""
    if not RECIPIENT.fullmatch(recipient):
        raise BackupError("backup.recipient must be an age public key (age1...) or an SSH key")
    return recipient


def _archive(cfg: UserConfig, home: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        if cfg.memory_bank_dir.is_dir():
            archive.add(cfg.memory_bank_dir, arcname=cfg.memory_bank_dir.name)
        for memory in sorted((home / ".claude" / "projects").glob("*/memory")):
            archive.add(memory, arcname=str(memory.relative_to(home)))
    return buffer.getvalue()


def _git(repo: Path, *args: str) -> None:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise BackupError(f"git {args[0]} failed: {done.stderr.strip()}")


def run(cfg: UserConfig, home: Path, repo: Path, recipient: str, day: str | None = None) -> Path:
    """Write today's encrypted snapshot into the backup repository and commit it."""
    check_recipient(recipient)
    if not repo.is_absolute():
        raise BackupError(f"backup.repo must be an absolute path, not {repo}")
    stamp = day or date.today().isoformat()
    target = repo / "snapshots" / f"{stamp}.tar.gz.age"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        _git(repo, "init", "-q")
    done = subprocess.run(
        ["age", "-r", recipient, "-o", str(target)],
        input=_archive(cfg, home),
        capture_output=True,
        check=False,
    )
    if done.returncode != 0:
        raise BackupError(f"age failed: {done.stderr.decode(errors='replace').strip()}")
    _git(repo, "add", str(target.relative_to(repo)))
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if status.stdout.strip():
        _git(
            repo,
            "-c",
            "user.name=bedrock",
            "-c",
            "user.email=bedrock@localhost",
            "commit",
            "-qm",
            f"chore(backup): snapshot {stamp}",
        )
    return target
