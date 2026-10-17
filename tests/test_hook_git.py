import io
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_hooks import dispatch, grants
from bedrock_hooks.registry import RULES
from bedrock_lib.config import load_user_config
from conftest import owner_transcript

NOW = "2026-10-17T12:00:00Z"


def sh(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )
    return done.stdout


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "work" / "app"
    root.mkdir(parents=True)
    sh(root, "init", "-q", "-b", "main")
    sh(root, "config", "user.email", "t@example.com")
    sh(root, "config", "user.name", "t")
    (root / ".claude").mkdir()
    settings = {"project": "Acme", "leaks": {"gitleaks": False}}
    (root / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    (root / "README.md").write_text("x\n")
    sh(root, "add", ".")
    sh(root, "commit", "-q", "-m", "chore: start")
    return root


def environ(home: Path) -> dict[str, str]:
    return {"HOME": str(home), "BEDROCK_NOW": NOW, "PATH": "/usr/bin:/bin"}


def deny(
    home: Path, cwd: Path, command: str, agent: str | None = None, path: str = "/usr/bin:/bin"
) -> str:
    data = {
        "hook_event_name": "PreToolUse",
        "session_id": "s1",
        "cwd": str(cwd),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if agent:
        data["agent_id"] = agent
    out = io.StringIO()
    env = {**environ(home), "PATH": path}
    dispatch.main(["PreToolUse"], io.StringIO(json.dumps(data)), out, env, RULES)
    result = json.loads(out.getvalue() or "{}")
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def grant(home: Path, prompt: str, project: str = "Acme") -> None:
    cfg = load_user_config(environ(home))
    now = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
    grants.record(
        cfg, grants.from_prompt(prompt, project, now, cfg, owner_transcript(home, prompt))
    )


@pytest.mark.parametrize(
    "command",
    [
        *("git status", "git diff HEAD~1", "git log --oneline -5", "git add -A"),
        *("git switch -c fix/x", "git rebase main", "git branch -d old", "git stash"),
    ],
)
def test_ordinary_git_passes(home: Path, repo: Path, command: str) -> None:
    assert deny(home, repo, command) == ""


def test_push_needs_a_grant(home: Path, repo: Path) -> None:
    assert "needs the owner's word" in deny(home, repo, "git push origin main")
    grant(home, "запушь")
    assert deny(home, repo, "git push origin main") == ""
    assert "needs the owner's word" in deny(home, repo, "git push origin main")


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f",
        "git push --force-with-lease",
        "git push origin +main",
        "git push origin --delete old",
        "git push origin :old",
        "git push --mirror",
        "git -C . push -f",
        "cd x && git push -f",
        'bash -c "git push --force"',
    ],
)
def test_force_and_remote_deletes_are_irreversible(home: Path, repo: Path, command: str) -> None:
    grant(home, "до конца плана: пушь")
    assert "irreversible" in deny(home, repo, command)


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard HEAD~1",
        "git clean -fd",
        "git clean --force",
        "git branch -D feature",
        "git checkout .",
        "git checkout -- .",
        "git restore .",
        "git filter-branch --tree-filter x HEAD",
        "git filter-repo --path x",
        "git commit --no-verify -m 'fix: x'",
        "git commit -n -m 'fix: x'",
        "git -c core.hooksPath=/dev/null commit -m 'fix: x'",
        "git config core.hooksPath /tmp/none",
        "gh auth switch",
    ],
)
def test_destructive_git_is_refused(home: Path, repo: Path, command: str) -> None:
    assert "irreversible" in deny(home, repo, command)


def test_override_key_allows_one_force_push_and_takes_a_safety_tag(home: Path, repo: Path) -> None:
    sh(repo, "update-ref", "refs/remotes/origin/feature", "HEAD")
    grant(home, "разрешаю: форс-пуш feature")
    assert deny(home, repo, "git push --force origin feature") == ""
    assert sh(repo, "tag", "--list", "bedrock-safety/*").strip()
    assert "irreversible" in deny(home, repo, "git push --force origin feature")


def test_owner_only_push_repo_refuses_even_with_a_grant(home: Path, repo: Path) -> None:
    settings = {"project": "Acme", "git": {"push": "owner"}, "leaks": {"gitleaks": False}}
    (repo / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    grant(home, "запушь")
    assert "owner pushes" in deny(home, repo, "git push origin main")


def test_knowledge_base_repo_is_never_pushed(home: Path, tmp_path: Path) -> None:
    kb = home / "projects-memory-bank"
    kb.mkdir(parents=True)
    sh(kb, "init", "-q")
    grant(home, "запушь", project="global")
    assert "knowledge base" in deny(home, kb, "git push origin main")


@pytest.mark.parametrize("command", ["git commit -m 'fix: x'", "git push", "git merge main"])
def test_agents_only_read_git(home: Path, repo: Path, command: str) -> None:
    assert "main session" in deny(home, repo, command, agent="a1")


@pytest.mark.parametrize("command", ["git status", "git diff", "git log -3", "git show HEAD"])
def test_agents_may_read_git(home: Path, repo: Path, command: str) -> None:
    assert deny(home, repo, command, agent="a1") == ""


def test_commit_runs_the_checks_on_what_is_staged(home: Path, repo: Path) -> None:
    (repo / "app.py").write_text("x = 1\n")
    sh(repo, "add", "app.py")
    assert deny(home, repo, "git commit -m 'feat(app): add x'") == ""
    assert "commit format" in deny(home, repo, "git commit -m 'Add x'")
    (repo / "utils.py").write_text("y = 2\n")
    sh(repo, "add", "utils.py")
    assert "dump name" in deny(home, repo, "git commit -m 'feat(app): add x'")


def test_commit_message_body_is_refused(home: Path, repo: Path) -> None:
    (repo / "app.py").write_text("x = 1\n")
    sh(repo, "add", "app.py")
    assert "one line" in deny(home, repo, "git commit -m 'feat(app): x' -m 'more text'")


def test_commit_leak_is_refused(home: Path, repo: Path) -> None:
    terms = home / ".config" / "bedrock" / "leak-terms.txt"
    terms.parent.mkdir(parents=True)
    terms.write_text("Quentin\n")
    (repo / "notes.md").write_text("ask Quentin\n")
    sh(repo, "add", "notes.md")
    reason = deny(home, repo, "git commit -m 'docs: add notes'")
    assert "listed name" in reason
    assert "Quentin" not in reason


def test_commit_all_must_stage_first(home: Path, repo: Path) -> None:
    assert "stage" in deny(home, repo, "git commit -am 'fix: x'")


def test_unparseable_command_is_refused(home: Path, repo: Path) -> None:
    assert "could not" in deny(home, repo, 'git commit -m "oops')


def fake_gh(tmp_path: Path, exit_code: int) -> str:
    folder = tmp_path / "fakebin"
    folder.mkdir(exist_ok=True)
    script = folder / "gh"
    script.write_text(f"#!/bin/sh\nexit {exit_code}\n")
    script.chmod(0o755)
    return f"{folder}:/usr/bin:/bin"


def passed_review(home: Path, branch: str = "main") -> None:
    folder = home / ".local/state/bedrock/reviews/Acme"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{branch}.json").write_text('{"passed": true}')


def test_pr_needs_a_passed_review_then_a_grant(home: Path, repo: Path) -> None:
    assert "no passed review" in deny(home, repo, "gh pr create --fill")
    passed_review(home)
    assert "needs the owner's word" in deny(home, repo, "gh pr create --fill")
    grant(home, "открой пр")
    assert deny(home, repo, "gh pr create --fill") == ""


def test_merge_needs_green_ci(home: Path, repo: Path, tmp_path: Path) -> None:
    passed_review(home)
    grant(home, "до конца плана: мержь")
    assert "not green" in deny(home, repo, "gh pr merge 12 --squash", path=fake_gh(tmp_path, 1))
    assert deny(home, repo, "gh pr merge 12 --squash", path=fake_gh(tmp_path, 0)) == ""


@pytest.mark.parametrize(
    ("command", "refused"),
    [
        ("gh api repos/o/r/issues -X POST -f title=x", True),
        ("gh api repos/o/r/issues -f title=x", True),
        ("gh api repos/o/r/pulls", False),
        ("gh pr view 12", False),
        ("gh issue comment 3 -b hi", True),
        ("gh pr list", False),
    ],
)
def test_github_writes_need_a_grant(home: Path, repo: Path, command: str, refused: bool) -> None:
    assert ("needs the owner's word" in deny(home, repo, command)) is refused


def test_agents_never_use_gh(home: Path, repo: Path) -> None:
    assert "only the main session" in deny(home, repo, "gh pr view 12", agent="a1")


def test_commit_message_inside_a_heredoc_is_checked(home: Path, repo: Path) -> None:
    (repo / "app.py").write_text("x = 1\n")
    sh(repo, "add", "app.py")
    bad = "git commit -m \"$(cat <<'EOF'\nFixed stuff\nEOF\n)\""
    good = "git commit -m \"$(cat <<'EOF'\nfix(app): handle x\nEOF\n)\""
    assert "commit format" in deny(home, repo, bad)
    assert deny(home, repo, good) == ""
