import io
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bedrock_hooks import dispatch, grants
from bedrock_hooks.registry import RULES
from bedrock_lib.config import load_user_config
from conftest import owner_transcript


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "home"


@pytest.fixture
def work(tmp_path: Path) -> Path:
    root = tmp_path / "work"
    (root / ".claude").mkdir(parents=True)
    commands = {
        "deploy-dev": {"run": "./scripts/deploy.sh dev"},
        "deploy-prod": {"run": "./scripts/deploy.sh prod"},
    }
    (root / ".claude" / "bedrock.json").write_text(
        json.dumps({"project": "Acme", "commands": commands})
    )
    return root


def environ(home: Path) -> dict[str, str]:
    return {"HOME": str(home), "BEDROCK_NOW": "2026-10-17T12:00:00Z", "PATH": "/usr/bin:/bin"}


def call(home: Path, cwd: Path, tool: str, tool_input: dict, agent: str | None = None) -> str:
    data = {"session_id": "s1", "cwd": str(cwd), "tool_name": tool, "tool_input": tool_input}
    if agent:
        data["agent_id"] = agent
    out = io.StringIO()
    dispatch.main(["PreToolUse"], io.StringIO(json.dumps(data)), out, environ(home), RULES)
    result = json.loads(out.getvalue() or "{}")
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")


def bash(home: Path, cwd: Path, command: str) -> str:
    return call(home, cwd, "Bash", {"command": command})


def grant(home: Path, prompt: str) -> None:
    cfg = load_user_config(environ(home))
    now = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
    grants.record(cfg, grants.from_prompt(prompt, "Acme", now, cfg, owner_transcript(home, prompt)))


NEEDS = "needs the owner's word"
NEVER = "irreversible"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("./scripts/deploy.sh dev", NEEDS),
        ("bedrock cmd deploy-dev", NEEDS),
        ("vercel --prod", NEEDS),
        ("kubectl apply -f k8s/", NEEDS),
        ("terraform apply -auto-approve", NEEDS),
        ("npm publish", NEEDS),
        ("docker push acme/api:1", NEEDS),
        ("aws s3 cp build/ s3://bucket/ --recursive", NEEDS),
        ("aws lambda update-function-code --function-name f", NEEDS),
        ('psql "postgres://u:p@db.prod.acme.io/app" -c "UPDATE users SET a=1"', NEEDS),
        ("npx prisma migrate deploy", NEEDS),
        ("curl -X POST https://api.acme.io/v1/items -d '{}'", NEEDS),
        ("curl --data x=1 https://hooks.slack.com/services/T/B/C", NEEDS),
        ("ssh deploy@10.0.0.5 'systemctl restart api'", NEEDS),
        ("scp build.tgz deploy@host:/srv/", NEEDS),
        ("sendmail team@acme.io < note.txt", NEEDS),
        ("terraform destroy", NEVER),
        ("kubectl delete ns staging", NEVER),
        ("aws s3 rm s3://bucket --recursive", NEVER),
        ('psql "postgres://u:p@db.prod.acme.io/app" -c "DROP TABLE users"', NEVER),
        ("rm -rf /", NEVER),
        ("rm -rf ~", NEVER),
        ("rm -rf $HOME", NEVER),
        ("sudo rm -fr /etc", NEVER),
    ],
)
def test_outward_and_irreversible_commands(
    home: Path, work: Path, command: str, expected: str
) -> None:
    assert expected in bash(home, work, command)


@pytest.mark.parametrize(
    "command",
    [
        "aws s3 ls s3://bucket",
        "aws logs tail /aws/lambda/f --since 10m",
        "aws sts get-caller-identity",
        "kubectl get pods",
        "terraform plan",
        "curl https://api.acme.io/v1/health",
        "curl -X POST http://localhost:3000/api/items -d '{}'",
        'psql -h localhost app -c "UPDATE t SET a=1"',
        "sqlite3 dev.db 'DELETE FROM t'",
        "rm -rf node_modules dist",
        "rm -rf ./build/tmp",
        "npm ci",
        "npm install",
        "pip install -r requirements.txt",
        "pip install -e .",
        "git status",
    ],
)
def test_reads_and_local_work_pass(home: Path, work: Path, command: str) -> None:
    assert bash(home, work, command) == ""


def test_dev_deploy_grant_does_not_cover_production(home: Path, work: Path) -> None:
    grant(home, "задеплой на дев")
    assert "needs the owner's word" in bash(home, work, "./scripts/deploy.sh prod")
    assert bash(home, work, "./scripts/deploy.sh dev") == ""


def test_new_library_needs_a_grant(home: Path, work: Path) -> None:
    assert NEEDS in bash(home, work, "npm install left-pad")
    assert NEEDS in bash(home, work, "pip install reqeusts")
    assert NEEDS in bash(home, work, "uv add httpx")


@pytest.mark.parametrize(
    "command",
    [
        "echo '{}' > ~/.claude/settings.json",
        "cp x.md ~/.claude/CLAUDE.md",
        "sed -i 's/a/b/' $HOME/.claude/settings.json",
        "rm -rf ~/.claude/skills/old",
    ],
)
def test_changes_to_the_claude_folder_need_a_grant(home: Path, work: Path, command: str) -> None:
    assert NEEDS in bash(home, work, command)


def test_claude_memory_and_reading_the_claude_folder_pass(home: Path, work: Path) -> None:
    assert bash(home, work, "cat ~/.claude/settings.json") == ""
    assert bash(home, work, "echo x > ~/.claude/projects/p/memory/a.md") == ""


def test_edit_tool_in_the_claude_folder_needs_a_grant(home: Path, work: Path) -> None:
    path = str(home / ".claude" / "settings.json")
    assert NEEDS in call(home, work, "Write", {"file_path": path, "content": "{}"})
    memory = str(home / ".claude" / "projects" / "p" / "memory" / "a.md")
    assert call(home, work, "Write", {"file_path": memory, "content": "x"}) == ""


@pytest.mark.parametrize(
    "tool",
    [
        "mcp__plugin_slack_slack__slack_send_message",
        "mcp__plugin_slack_slack__slack_schedule_message",
    ],
)
def test_slack_sending_is_always_refused(home: Path, work: Path, tool: str) -> None:
    grant(home, "/bedrock:unleash until 18:00")
    assert "never sends" in call(home, work, tool, {"channel_id": "C1", "text": "hi"})


@pytest.mark.parametrize(
    ("tool", "refused"),
    [
        ("mcp__plugin_slack_slack__slack_send_message_draft", True),
        ("mcp__plugin_slack_slack__slack_add_reaction", True),
        ("mcp__atlassian__createJiraIssue", True),
        ("mcp__atlassian__transitionJiraIssue", True),
        ("mcp__plugin_slack_slack__slack_read_channel", False),
        ("mcp__plugin_slack_slack__slack_search_public", False),
        ("mcp__atlassian__getJiraIssue", False),
        ("mcp__context7__query-docs", False),
    ],
)
def test_mcp_writes_need_a_grant(home: Path, work: Path, tool: str, refused: bool) -> None:
    assert (NEEDS in call(home, work, tool, {})) is refused


@pytest.mark.parametrize(
    "command",
    [
        "DATABASE_URL=postgres://u:p@localhost:5432/app npx prisma migrate deploy",
        "pip install .",
        "npm install ./packages/local-lib",
        "pip install -e ./sdk",
    ],
)
def test_local_migrations_and_local_installs_pass(home: Path, work: Path, command: str) -> None:
    assert bash(home, work, command) == ""


def test_agents_never_act_outward_even_with_a_grant(home: Path, work: Path) -> None:
    grant(home, "/bedrock:allow publish")
    reason = call(home, work, "Bash", {"command": "npm publish"}, agent="a1")
    assert "agents never act outward" in reason
    assert "agents never act outward" in call(
        home, work, "mcp__atlassian__createJiraIssue", {}, agent="a1"
    )
