import io
import json
import os
import subprocess
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES
from bedrock_lib import kb

NOW = "2026-10-17T12:00:00Z"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


def sh(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


@pytest.fixture
def work(tmp_path: Path, home: Path) -> Path:
    root = tmp_path / "work"
    (root / "src" / "ingest").mkdir(parents=True)
    (root / ".claude").mkdir()
    (root / ".claude" / "bedrock.json").write_text(json.dumps({"project": "Acme"}))
    (root / "src" / "ingest" / "chunk.py").write_text("x = 1\n")
    sh(root, "init", "-q")
    sh(root, "config", "user.email", "t@example.com")
    sh(root, "config", "user.name", "t")
    sh(root, "add", ".")
    sh(root, "commit", "-qm", "chore: start")
    bank = home / "projects-memory-bank"
    kb.init(bank, "Acme", "ACME", today="2026-10-17")
    note = (
        '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\nupdated: 2026-10-17\n'
        f"covers: [src/ingest]\nanchors: []\nverified_at: {sh(root, 'rev-parse', 'HEAD')}\n---\n"
        "# Ingest\n## Purpose\nx\n## Boundaries\nx\n## Rules\nx\n## Pitfalls\nx\n"
    )
    (bank / "Acme" / "ingest.md").write_text(note)
    (bank / "Acme" / "architecture.md").write_text(
        '---\ntype: index\ntags: [index]\nparent: "[[entry]]"\nupdated: 2026-10-17\n---\n'
        "# Architecture\n- [[ingest]]\n"
    )
    sh(bank, "config", "user.email", "t@example.com")
    sh(bank, "config", "user.name", "t")
    sh(bank, "add", ".")
    sh(bank, "commit", "-qm", "chore: start")
    return root


def hook(home: Path, event: str, data: dict) -> dict:
    out = io.StringIO()
    env = {"HOME": str(home), "BEDROCK_NOW": NOW, "PATH": "/usr/bin:/bin"}
    payload = {"session_id": "s1", "hook_event_name": event, **data}
    dispatch.main([event], io.StringIO(json.dumps(payload)), out, env, RULES)
    return json.loads(out.getvalue() or "{}")


def context(result: dict) -> str:
    return result.get("hookSpecificOutput", {}).get("additionalContext", "")


def edit(home: Path, work: Path, path: str) -> None:
    target = work / path
    target.write_text("x = 2\n")
    data = {
        "cwd": str(work),
        "tool_name": "Edit",
        "tool_input": {"file_path": str(target)},
        "tool_response": {},
    }
    hook(home, "PostToolUse", data)


def test_session_start_reports_stale_notes(home: Path, work: Path) -> None:
    assert "stale" not in context(
        hook(home, "SessionStart", {"cwd": str(work), "source": "startup"})
    )
    (work / "src" / "ingest" / "chunk.py").write_text("x = 3\n")
    sh(work, "commit", "-qam", "fix: x")
    text = context(hook(home, "SessionStart", {"cwd": str(work), "source": "startup"}))
    assert "ingest" in text and "stale" in text


def test_session_start_reports_validator_problems(home: Path, work: Path) -> None:
    (home / "projects-memory-bank" / "Acme" / "stray.md").write_text("# no frontmatter\n")
    text = context(hook(home, "SessionStart", {"cwd": str(work), "source": "startup"}))
    assert "bedrock kb validate" in text


def test_stop_asks_once_for_the_note_of_changed_code(home: Path, work: Path) -> None:
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    os.utime(note, (1_700_000_000, 1_700_000_000))
    edit(home, work, "src/ingest/chunk.py")
    result = hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False})
    assert result["decision"] == "block"
    assert "ingest" in result["reason"]
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": True}) == {}


def test_stop_is_quiet_when_the_note_was_updated(home: Path, work: Path) -> None:
    edit(home, work, "src/ingest/chunk.py")
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    note.write_text(note.read_text() + "\nverified, nothing to change, because the API stayed.\n")
    later = 1_792_238_460  # one minute after NOW: the note was updated after the code change
    os.utime(note, (later, later))
    bank = home / "projects-memory-bank"
    sh(bank, "commit", "-qam", "docs: verify ingest")
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False}) == {}


def test_stop_ignores_code_without_a_note(home: Path, work: Path) -> None:
    (work / "src" / "other.py").write_text("y = 1\n")
    edit(home, work, "src/other.py")
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False}) == {}


def test_changes_from_another_session_do_not_stop_this_one(home: Path, work: Path) -> None:
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    os.utime(note, (1_700_000_000, 1_700_000_000))
    marks = home / ".local/state/bedrock/changed/Acme.jsonl"
    marks.parent.mkdir(parents=True)
    record = {"ts": NOW, "path": "src/ingest/chunk.py", "session": "other", "agent": ""}
    marks.write_text(json.dumps(record) + "\n")
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False}) == {}


def test_restamping_only_the_commit_is_not_an_update(home: Path, work: Path) -> None:
    hook(home, "SessionStart", {"cwd": str(work), "source": "startup"})
    edit(home, work, "src/ingest/chunk.py")
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    text = note.read_text()
    old = next(line for line in text.splitlines() if line.startswith("verified_at:"))
    note.write_text(text.replace(old, "verified_at: abcdef1"))
    later = 1_792_238_460
    os.utime(note, (later, later))
    sh(home / "projects-memory-bank", "commit", "-qam", "docs: restamp")
    result = hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False})
    assert result.get("decision") == "block"
    assert "ingest" in result["reason"]


def test_a_real_update_after_session_start_is_quiet(home: Path, work: Path) -> None:
    hook(home, "SessionStart", {"cwd": str(work), "source": "startup"})
    edit(home, work, "src/ingest/chunk.py")
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    os.utime(note, (1_700_000_000, 1_700_000_000))
    note.write_text(note.read_text().replace("## Rules\nx", "## Rules\nchunks stay under 2 KB"))
    os.utime(note, (1_700_000_000, 1_700_000_000))
    sh(home / "projects-memory-bank", "commit", "-qam", "docs: ingest rule")
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False}) == {}


def test_resume_keeps_the_first_snapshot(home: Path, work: Path) -> None:
    hook(home, "SessionStart", {"cwd": str(work), "source": "startup"})
    note = home / "projects-memory-bank" / "Acme" / "ingest.md"
    note.write_text(note.read_text().replace("## Rules\nx", "## Rules\nnew rule"))
    sh(home / "projects-memory-bank", "commit", "-qam", "docs: ingest rule")
    hook(home, "SessionStart", {"cwd": str(work), "source": "resume"})
    edit(home, work, "src/ingest/chunk.py")
    os.utime(note, (1_700_000_000, 1_700_000_000))
    assert hook(home, "Stop", {"cwd": str(work), "stop_hook_active": False}) == {}


def test_session_start_lists_modules_without_a_note(home: Path, work: Path) -> None:
    (work / "src" / "billing").mkdir()
    (work / "src" / "billing" / "pay.py").write_text("x = 1\n")
    start = {"cwd": str(work), "source": "startup"}
    assert "billing" not in context(hook(home, "SessionStart", start))
    settings = {"project": "Acme", "kb": {"roots": ["src", "missing", "../..", 5]}}
    (work / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    text = context(hook(home, "SessionStart", start))
    assert "src/billing" in text and "src/ingest" not in text


def test_a_malformed_kb_setting_does_not_hide_the_rest(home: Path, work: Path) -> None:
    (work / ".claude" / "bedrock.json").write_text(json.dumps({"project": "Acme", "kb": []}))
    (home / "projects-memory-bank" / "Acme" / "stray.md").write_text("# no frontmatter\n")
    text = context(hook(home, "SessionStart", {"cwd": str(work), "source": "startup"}))
    assert "bedrock kb validate" in text
