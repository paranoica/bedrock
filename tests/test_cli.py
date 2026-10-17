import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import bedrock_cli
import pytest

ORIGINAL_PATH = os.environ.get("PATH", "")
TRAILER = "Co-Authored" + "-By: Claude <noreply@anthropic.com>"


BIN = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "bin" / "bedrock"


@pytest.fixture(autouse=True)
def no_desktop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Only git on PATH: no test can raise a real popup or depend on the local gitleaks.
    tools = tmp_path / "bin"
    tools.mkdir()
    git = shutil.which("git")
    assert git is not None
    (tools / "git").symlink_to(git)
    monkeypatch.setenv("PATH", str(tools))


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def workspace(home: Path) -> Path:
    root = home / "work" / "app"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "bedrock.json").write_text('{"project": "Acme"}')
    (root / "src").mkdir()
    return root


def env_at(home: Path, now: str) -> dict[str, str]:
    return {"HOME": str(home), "BEDROCK_NOW": now}


def run(
    capsys: pytest.CaptureFixture[str], argv: list[str], env: dict[str, str], cwd: Path
) -> tuple[int, str, str]:
    code = bedrock_cli.main(argv, env=env, cwd=cwd)
    out, err = capsys.readouterr()
    return code, out, err


def test_log_and_minutes_use_the_workspace_project(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    cwd = workspace / "src"
    assert (
        run(capsys, ["log", "taken", "--block", "T1"], env_at(home, "2026-10-17T12:00:00Z"), cwd)[0]
        == 0
    )
    assert (
        run(capsys, ["log", "closed", "--block", "T1"], env_at(home, "2026-10-17T12:45:00Z"), cwd)[
            0
        ]
        == 0
    )
    code, out, _ = run(capsys, ["minutes", "T1"], env_at(home, "2026-10-17T13:00:00Z"), cwd)
    assert code == 0
    assert out.strip() == "45"
    assert (home / "projects-days" / "Acme" / "2026-10-17" / "log.jsonl").exists()


def test_minutes_open_counts_to_now(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    run(capsys, ["log", "taken", "--block", "T1"], env_at(home, "2026-10-17T12:00:00Z"), workspace)
    code, out, _ = run(
        capsys, ["minutes", "T1", "--open"], env_at(home, "2026-10-17T12:30:00Z"), workspace
    )
    assert (code, out.strip()) == (0, "30")


def test_no_project_is_an_error(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    code, out, err = run(capsys, ["minutes", "T1"], env_at(home, "2026-10-17T12:00:00Z"), home)
    assert code == 1
    assert out == ""
    assert err.startswith("bedrock: ")


def test_project_flag_works_outside_a_workspace(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    code, out, _ = run(
        capsys, ["minutes", "T1", "--project", "Other"], env_at(home, "2026-10-17T12:00:00Z"), home
    )
    assert (code, out.strip()) == (0, "0")


def test_bad_event_is_an_error_not_a_traceback(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys,
        ["log", "finished", "--block", "T1"],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 1
    assert "unknown event" in err
    assert "Traceback" not in err


def test_ledger_add_and_summary(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    entry = {
        "project": "Acme",
        "role": "critic",
        "model": "opus",
        "reason": "b",
        "estimate": 500000,
        "actual": 420000,
        "turns": 12,
        "cap_hit": False,
        "accepted": True,
    }
    env = env_at(home, "2026-10-17T12:00:00Z")
    assert run(capsys, ["ledger", "add", json.dumps(entry)], env, workspace)[0] == 0
    code, out, _ = run(capsys, ["ledger", "summary"], env, workspace)
    assert code == 0
    assert json.loads(out)["critic"]["actual"] == 420000.0


def test_ledger_add_rejects_broken_json(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys, ["ledger", "add", "{nope"], env_at(home, "2026-10-17T12:00:00Z"), workspace
    )
    assert code == 1
    assert err.startswith("bedrock: ")


def test_ledger_spend_reads_a_transcript(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    transcript = home / "t.jsonl"
    usage = {"input_tokens": 10, "cache_read_input_tokens": 1000, "output_tokens": 2}
    transcript.write_text(
        json.dumps({"type": "assistant", "message": {"id": "m1", "usage": usage}}) + "\n"
    )
    code, out, _ = run(
        capsys,
        ["ledger", "spend", str(transcript)],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 0
    assert json.loads(out) == {
        "weighted": 120.0,
        "turns": 1,
        "start_context": 1010,
        "peak_context": 1010,
    }


def test_question_log_answer_similar(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(
        capsys, ["question", "log", "How are documents split into chunks?"], env, workspace
    )
    qid = out.strip()
    assert code == 0 and len(qid) == 12
    assert (
        run(
            capsys,
            ["question", "answer", qid, "512 tokens", "--source", "ingest.md"],
            env,
            workspace,
        )[0]
        == 0
    )
    code, out, _ = run(
        capsys, ["question", "similar", "how do we split documents into chunks"], env, workspace
    )
    hits = json.loads(out)
    assert hits[0]["answer"] == "512 tokens"
    assert hits[0]["source"] == "ingest.md"
    assert hits[0]["score"] > 0.5


def test_answer_to_unknown_question_fails(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(
        capsys,
        ["question", "answer", "nope", "x", "--source", "y"],
        env_at(home, "2026-10-17T12:00:00Z"),
        workspace,
    )
    assert code == 1
    assert "no question" in err


def test_notify_prints_the_decision(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, out, _ = run(
        capsys, ["notify", "p0", "down", "api is down", "--action", "ok=OK"], env, workspace
    )
    result = json.loads(out)
    assert code == 0
    assert result["popup"] is False
    assert result["shown"] is False
    assert result["phone"] is True
    assert result["reason"] == "no notify-send"
    assert result["action"] is None


def test_notify_rejects_a_malformed_button(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, _, err = run(
        capsys, ["notify", "question", "t", "b", "--action", "nolabel"], env, workspace
    )
    assert code == 1
    assert "key=Label" in err


def test_bin_entry_point_runs(home: Path) -> None:
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin", "BEDROCK_NOW": "2026-10-17T12:00:00Z"}
    completed = subprocess.run(
        [sys.executable, str(BIN), "minutes", "T1", "--project", "X"],
        env=env,
        cwd=home,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "0"


def test_ledger_summary_with_a_bad_since_is_an_error(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["ledger", "summary", "--since", "yesterday"], env, workspace)
    assert code == 1
    assert err.startswith("bedrock: ")


def test_notify_accepts_a_timeout(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T05:00:00Z")
    code, out, _ = run(capsys, ["notify", "question", "t", "b", "--timeout", "30"], env, workspace)
    assert code == 0
    assert json.loads(out)["reason"] == "no notify-send"


def test_machine_reports_memory_cores_and_heavy_run(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, out, _ = run(capsys, ["machine"], env_at(home, "2026-10-17T12:00:00Z"), workspace)
    state = json.loads(out)
    assert code == 0
    assert state["available_mb"] > 0
    assert state["cores"] >= 1
    assert state["heavy"] is None


def test_test_wrapper_passes_exit_code_and_records_the_profile(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    argv = ["test", "unit", "--", sys.executable, "-c", "raise SystemExit(3)"]
    assert bedrock_cli.main(argv, env=env, cwd=workspace) == 3
    _, err = capfd.readouterr()
    assert "unit" in err
    profile = json.loads((home / ".local/state/bedrock/profiles/Acme.json").read_text())
    assert profile["unit"]["runs"] == 1
    assert profile["unit"]["last_exit"] == 3


def test_test_wrapper_hands_the_worker_count_to_the_command(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    script = "import os, sys; print(os.environ['BEDROCK_WORKERS'], sys.argv[1])"
    argv = ["test", "unit", "--workers", "2", "--", sys.executable, "-c", script, "{workers}"]
    assert bedrock_cli.main(argv, env=env, cwd=workspace) == 0
    out, _ = capfd.readouterr()
    assert out.strip() == "2 2"


def test_heavy_run_refuses_without_waiting_when_the_lock_is_held(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    from bedrock_lib import runlock
    from bedrock_lib.config import load_user_config

    env = env_at(home, "2026-10-17T12:00:00Z")
    with runlock.heavy(load_user_config(env), "Other: e2e"):
        argv = ["test", "e2e", "--heavy", "--no-wait", "--", sys.executable, "-c", "print(1)"]
        assert bedrock_cli.main(argv, env=env, cwd=workspace) == 1
    out, err = capfd.readouterr()
    assert "Other: e2e" in err
    assert out == ""


def test_test_wrapper_needs_a_command(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    code, _, err = run(capsys, ["test", "unit"], env_at(home, "2026-10-17T12:00:00Z"), workspace)
    assert code == 1
    assert "command" in err


def test_double_dash_is_plain_text_outside_test(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["log", "note", "--detail", "a -- b"], env, workspace)
    assert code == 0, err
    code, _, err = run(
        capsys, ["question", "log", "--project", "X", "--", "--why?"], env, workspace
    )
    assert code == 0, err


def with_commands(workspace: Path, commands: dict[str, object]) -> None:
    config = {"project": "Acme", "commands": commands}
    (workspace / ".claude" / "bedrock.json").write_text(json.dumps(config))


def test_cmd_runs_at_the_project_root_and_passes_the_exit_code(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    script = "import os, sys; print(os.getcwd()); sys.exit(4)"
    with_commands(workspace, {"build": {"run": f"{sys.executable} -c {json.dumps(script)}"}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    assert bedrock_cli.main(["cmd", "build"], env=env, cwd=workspace / "src") == 4
    out, _ = capfd.readouterr()
    assert out.strip() == str(workspace)


def test_cmd_arguments_are_never_run_as_shell(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    script = "import sys; print(sys.argv[1:])"
    with_commands(workspace, {"one": {"run": f"{sys.executable} -c {json.dumps(script)} {{args}}"}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    hostile = "x; touch pwned"
    assert bedrock_cli.main(["cmd", "one", "--", hostile, "$(id)"], env=env, cwd=workspace) == 0
    out, _ = capfd.readouterr()
    assert out.strip() == str([hostile, "$(id)"])
    assert not (workspace / "pwned").exists()


def test_cmd_appends_arguments_when_there_is_no_placeholder(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    script = "import sys; print(sys.argv[1:])"
    with_commands(workspace, {"one": {"run": f"{sys.executable} -c {json.dumps(script)}"}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    assert bedrock_cli.main(["cmd", "one", "--", "a b"], env=env, cwd=workspace) == 0
    out, _ = capfd.readouterr()
    assert out.strip() == str(["a b"])


def test_cmd_test_suite_is_measured_with_workers_and_lock(
    capfd: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    state = home / ".local/state/bedrock"
    script = (
        "import json, os, sys; "
        f"print(json.load(open({str(state / 'heavy.json')!r}))['label'], sys.argv[1])"
    )
    run_line = f"{sys.executable} -c {json.dumps(script)} {{workers}}"
    with_commands(workspace, {"test": {"run": run_line, "suite": "unit", "heavy": True}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    assert bedrock_cli.main(["cmd", "test"], env=env, cwd=workspace) == 0
    out, err = capfd.readouterr()
    assert out.strip() == "Acme: unit 1"
    assert "unit passed" in err
    assert json.loads((state / "profiles/Acme.json").read_text())["unit"]["runs"] == 1


def test_cmd_unknown_name_lists_the_known_ones(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    with_commands(workspace, {"lint": {"run": "true"}, "build": {"run": "true"}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["cmd", "deploy"], env, workspace)
    assert code == 1
    assert "build, lint" in err


def test_cmd_list_shows_the_commands(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    with_commands(workspace, {"lint": {"run": "ruff check ."}})
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["cmd", "--list"], env, workspace)
    assert code == 0
    assert json.loads(out) == {"lint": {"run": "ruff check ."}}


@pytest.mark.parametrize(
    "commands",
    [None, {"lint": "ruff check ."}, {"lint": {"run": ""}}, {"lint": {"run": 3}}],
)
def test_cmd_refuses_missing_or_malformed_commands(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path, commands: object
) -> None:
    config: dict[str, object] = {"project": "Acme"}
    if commands is not None:
        config["commands"] = commands
    (workspace / ".claude" / "bedrock.json").write_text(json.dumps(config))
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["cmd", "lint"], env, workspace)
    assert code == 1
    assert err.startswith("bedrock: ")


def test_cmd_outside_a_workspace_is_an_error(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    code, _, err = run(capsys, ["cmd", "lint"], env_at(home, "2026-10-17T12:00:00Z"), home)
    assert code == 1
    assert "bedrock.json" in err


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"]):
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)
    return path


def test_leaks_clean_staged_change_passes(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    repo = git_repo(home / "repo")
    (repo / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "a.py"], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["leaks", "--no-gitleaks"], env, repo)
    assert (code, out) == (0, "")


def test_leaks_reports_listed_names_from_the_private_list(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    terms = home / ".config" / "bedrock" / "leak-terms.txt"
    terms.parent.mkdir(parents=True)
    terms.write_text("Quentin\n")
    repo = git_repo(home / "repo")
    (repo / "a.md").write_text("ask Quentin\n")
    subprocess.run(["git", "-C", str(repo), "add", "a.md"], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["leaks", "--no-gitleaks", "--message", "docs: note"], env, repo)
    assert code == 1
    assert out.strip() == "a.md:1: listed name: ask Q******"


def test_leaks_checks_the_commit_message(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    repo = git_repo(home / "repo")
    message = f"fix: x\n\n{TRAILER}"
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["leaks", "--no-gitleaks", "--message", message], env, repo)
    assert code == 1
    assert "message:3: ai co-authorship" in out


def test_leaks_ignores_listed_paths_and_allowed_words(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    repo = git_repo(home / "repo")
    (repo / ".claude").mkdir()
    settings = {"project": "demo", "leaks": {"allow": ["claude"], "ignore": ["tests/*"]}}
    (repo / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    (repo / "tests").mkdir()
    (repo / "tests" / "t.py").write_text(f"# {TRAILER}\n")
    (repo / "a.py").write_text("# Claude Code sends the hook input\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["leaks", "--no-gitleaks"], env, repo)
    assert (code, out) == (0, "")


def test_leaks_without_gitleaks_cannot_run(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    repo = git_repo(home / "repo")
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["leaks"], env, repo)
    assert code == 2
    assert "gitleaks" in err


def test_backlog_add_next_claim_done(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    fields = json.dumps({"title": "dedupe", "priority": "P1", "risk": "R2"})
    code, out, _ = run(capsys, ["backlog", "add", fields], env, workspace)
    assert (code, out.strip()) == (0, "T1")
    code, out, _ = run(capsys, ["backlog", "next", "--session", "s1"], env, workspace)
    assert json.loads(out)["id"] == "T1"
    assert run(capsys, ["backlog", "claim", "T1", "--session", "s1"], env, workspace)[0] == 0
    code, _, err = run(capsys, ["backlog", "claim", "T1", "--session", "s2"], env, workspace)
    assert code == 1 and "s1" in err
    assert run(capsys, ["backlog", "status", "T1", "done"], env, workspace)[0] == 0
    code, out, _ = run(capsys, ["backlog", "next"], env, workspace)
    assert (code, json.loads(out)) == (0, None)
    assert run(capsys, ["backlog", "validate"], env, workspace)[:2] == (0, "[]\n")
    assert (home / "projects-memory-bank" / "Acme" / "backlog.md").exists()


def test_backlog_validate_fails_on_a_hand_edit(
    capsys: pytest.CaptureFixture[str], home: Path, workspace: Path
) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    fields = json.dumps({"title": "x", "priority": "P2", "risk": "R1"})
    run(capsys, ["backlog", "add", fields], env, workspace)
    (home / "projects-memory-bank" / "Acme" / "backlog.md").write_text("edited\n")
    code, out, _ = run(capsys, ["backlog", "validate"], env, workspace)
    assert code == 1
    assert "out of sync" in out


def test_check_reports_violations_and_the_commit_format(
    capsys: pytest.CaptureFixture[str], home: Path
) -> None:
    repo = git_repo(home / "repo")
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / "README.md").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "chore: x"], check=True)
    (repo / "app").mkdir()
    (repo / "app" / "utils.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    argv = ["check", "--no-network", "--message", "Fix stuff"]
    code, out, _ = run(capsys, argv, env, repo)
    assert code == 1
    assert "app/utils.py:1: dump name" in out
    assert "message:1: commit format" in out


def test_check_outside_git_cannot_run(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, _, err = run(capsys, ["check", "--no-network"], env, home)
    assert code == 2
    assert err.startswith("bedrock: ")


def test_check_ignores_listed_paths(capsys: pytest.CaptureFixture[str], home: Path) -> None:
    repo = git_repo(home / "repo")
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
    (repo / ".claude").mkdir()
    settings = {"project": "demo", "checks": {"ignore": ["tests/fixtures/*"]}}
    (repo / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "chore: x"], check=True)
    (repo / "tests" / "fixtures").mkdir(parents=True)
    (repo / "tests" / "fixtures" / "bad.py").write_text("breakpoint" + "()\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["check", "--no-network"], env, repo)
    assert (code, out) == (0, "")


def test_leaks_ignore_never_hides_a_secret(
    capsys: pytest.CaptureFixture[str], home: Path, tmp_path: Path
) -> None:
    real = shutil.which("gitleaks", path=ORIGINAL_PATH)
    if real is None:
        pytest.skip("gitleaks is not installed")
    (tmp_path / "bin" / "gitleaks").symlink_to(real)
    repo = git_repo(home / "repo")
    (repo / ".claude").mkdir()
    settings = {"project": "demo", "leaks": {"ignore": ["fixtures/*"]}}
    (repo / ".claude" / "bedrock.json").write_text(json.dumps(settings))
    (repo / "fixtures").mkdir()
    token = "ghp_" + "9fZq2Lw8Xc3Vb7Nm1Kp4Rt6Yh0Ju5Ie2Wo8a"
    (repo / "fixtures" / "conf.py").write_text(f'token = "{token}"\n')
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    env = env_at(home, "2026-10-17T12:00:00Z")
    code, out, _ = run(capsys, ["leaks"], env, repo)
    assert code == 1
    assert "fixtures/conf.py:1: secret" in out
    assert token not in out
