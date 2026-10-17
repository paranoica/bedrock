import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
from bedrock_lib import backup
from bedrock_lib.config import UserConfig

pytestmark = pytest.mark.skipif(shutil.which("age") is None, reason="age is not installed")


@pytest.fixture
def setup(tmp_path: Path) -> tuple[UserConfig, Path, Path, str]:
    home = tmp_path / "home"
    bank = home / "projects-memory-bank"
    (bank / "Acme").mkdir(parents=True)
    (bank / "Acme" / "status.md").write_text("now: dedupe\n")
    memory = home / ".claude" / "projects" / "-home-x-app" / "memory"
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("- owner prefers plain words\n")
    key = tmp_path / "key.txt"
    subprocess.run(["age-keygen", "-o", str(key)], check=True, capture_output=True)
    recipient = next(r.split(": ")[1] for r in key.read_text().splitlines() if "public key" in r)
    repo = tmp_path / "backup-repo"
    cfg = UserConfig(days_dir=home / "d", state_dir=home / "s", memory_bank_dir=bank)
    return cfg, home, repo, recipient


def test_backup_is_encrypted_committed_and_restorable(setup, tmp_path: Path) -> None:
    cfg, home, repo, recipient = setup
    path = backup.run(cfg, home, repo, recipient, day="2026-10-17")
    assert path == repo / "snapshots" / "2026-10-17.tar.gz.age"
    assert b"dedupe" not in path.read_bytes()
    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--format=%s"], capture_output=True, text=True, check=True
    )
    assert log.stdout.strip() == "chore(backup): snapshot 2026-10-17"
    plain = tmp_path / "plain.tar.gz"
    subprocess.run(
        ["age", "-d", "-i", str(tmp_path / "key.txt"), "-o", str(plain), str(path)], check=True
    )
    with tarfile.open(plain) as archive:
        names = archive.getnames()
    assert "projects-memory-bank/Acme/status.md" in names
    assert ".claude/projects/-home-x-app/memory/MEMORY.md" in names


def test_backup_never_pushes(setup, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg, home, repo, recipient = setup
    calls: list[list[str]] = []
    real = subprocess.run

    def spy(argv, *args, **kwargs):
        calls.append(list(argv))
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(backup.subprocess, "run", spy)
    backup.run(cfg, home, repo, recipient, day="2026-10-17")
    assert not any("push" in argv for argv in calls)


def test_same_day_twice_replaces_the_snapshot(setup) -> None:
    cfg, home, repo, recipient = setup
    first = backup.run(cfg, home, repo, recipient, day="2026-10-17").read_bytes()
    second = backup.run(cfg, home, repo, recipient, day="2026-10-17").read_bytes()
    assert first != second
    assert len(list((repo / "snapshots").iterdir())) == 1


def test_bad_recipient_fails_loudly(setup) -> None:
    cfg, home, repo, _ = setup
    with pytest.raises(backup.BackupError):
        backup.run(cfg, home, repo, "age1notakey", day="2026-10-17")


def test_every_day_stays_restorable(setup, tmp_path: Path) -> None:
    cfg, home, repo, recipient = setup
    first = backup.run(cfg, home, repo, recipient, day="2026-10-16")
    (cfg.memory_bank_dir / "Acme" / "status.md").write_text("now: ship\n")
    second = backup.run(cfg, home, repo, recipient, day="2026-10-17")
    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--format=%s"], capture_output=True, text=True, check=True
    )
    assert log.stdout.split("\n")[:2] == [
        "chore(backup): snapshot 2026-10-17",
        "chore(backup): snapshot 2026-10-16",
    ]
    for snapshot, expected in ((first, b"now: dedupe\n"), (second, b"now: ship\n")):
        plain = tmp_path / f"{snapshot.name}.tar.gz"
        subprocess.run(
            ["age", "-d", "-i", str(tmp_path / "key.txt"), "-o", str(plain), str(snapshot)],
            check=True,
        )
        with tarfile.open(plain) as archive:
            member = archive.extractfile("projects-memory-bank/Acme/status.md")
            assert member is not None and member.read() == expected


def test_recipient_and_repo_are_checked_at_use(
    setup, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, home, _, recipient = setup
    monkeypatch.chdir(tmp_path)
    assert backup.check_recipient(recipient) == recipient
    assert backup.check_recipient("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample")
    assert backup.check_recipient("ssh-rsa AAAAB3NzaC1yc2EAAAADAQAB Quentin at work")
    for bad in ("-o /tmp/x", "age1short", "", "ssh-ed25519"):
        with pytest.raises(backup.BackupError):
            backup.check_recipient(bad)
    with pytest.raises(backup.BackupError):
        backup.run(cfg, home, Path("relative/repo"), recipient, day="2026-10-17")
    assert not (tmp_path / "relative").exists()
