import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from bedrock_hooks import dispatch
from bedrock_hooks.registry import RULES

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "bedrock" / "skills" / "humanize"

# The acceptance set of claude-humanize-skill, with neutral names.
DRAFTS = [
    "напиши ей что я опоздаю на полчаса",
    "ответь ему: да, давай завтра",
    "что ответить на это?\n\nПривет, когда будет готово?",
    "набросай черновик ответа клиенту про сроки",
    "сделай драфт письма в поддержку",
    "draft a reply to Quentin about the deploy",
    "write back to her that I'll be late",
    "what should I say to this",
    "напиши Пете что созвон переносится",
    "humanize this: We are pleased to inform you that the release is live.",
    'ответь ему\n<pasted_content id="1">\nпривет, когда будет готово?\n</pasted_content>',
    '<pasted_content id="2">\nты завтра свободен?\n</pasted_content>\nа я что?',
]
NOT_DRAFTS = [
    "напиши тест для функции parse",
    "напиши функцию сортировки на python",
    "почему падает этот тест",
    "ответь на вопрос: что такое GIL",
    "draft PR for this branch",
    "создай draft release на гитхабе",
    "напиши сообщение об ошибке для валидации email",
    "what does this reply handler do",
    "как работает UserPromptSubmit хук",
    "напиши ответ API в формате json",
    "сделай рефакторинг модуля оплаты",
    "проверь что я наклепал",
    "ревью этого PR",
    "задеплой на дев",
    "что дальше?",
    '<pasted_content id="3">\nЗадача: любой намёк («ответь», «напиши ему/ей», «draft a reply»)'
    " должен вызывать скилл. Сначала план.\n</pasted_content>",
]


def prompt(tmp_path: Path, text: str, settings: dict | None = None, source: str = "user") -> dict:
    home = tmp_path / "home"
    if settings is not None:
        (home / ".claude").mkdir(parents=True, exist_ok=True)
        (home / ".claude" / "settings.json").write_text(json.dumps(settings))
    data = {"session_id": "s1", "cwd": str(tmp_path), "prompt": text, "source": source}
    env = {"HOME": str(home), "BEDROCK_NOW": "2026-11-24T12:00:00Z", "PATH": "/usr/bin:/bin"}
    out = io.StringIO()
    dispatch.main(["UserPromptSubmit"], io.StringIO(json.dumps(data)), out, env, RULES)
    return json.loads(out.getvalue() or "{}")


def context(result: dict) -> str:
    return result.get("hookSpecificOutput", {}).get("additionalContext", "")


@pytest.mark.parametrize("text", DRAFTS)
def test_a_draft_request_names_the_bundled_skill(tmp_path: Path, text: str) -> None:
    found = context(prompt(tmp_path, text))
    assert 'skill="bedrock:humanize"' in found
    assert "anthropic-skills:humanize" in found and "do not send" in found
    assert "decision" not in prompt(tmp_path, text)


@pytest.mark.parametrize("text", NOT_DRAFTS)
def test_other_prompts_get_no_humanize_hint(tmp_path: Path, text: str) -> None:
    assert "humanize" not in context(prompt(tmp_path, text))


PERSONAL = {
    "hooks": {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "/x/claude-humanize-skill/hooks/draft_trigger.sh",
                    }
                ]
            }
        ]
    }
}


def test_bedrock_stays_silent_when_the_personal_hook_is_installed(tmp_path: Path) -> None:
    assert "humanize" not in context(prompt(tmp_path, "напиши ей что я опоздаю", PERSONAL))


@pytest.mark.parametrize("settings", [{}, {"hooks": "broken"}, {"hooks": {"Stop": []}}])
def test_other_settings_keep_bedrock_s_trigger(tmp_path: Path, settings: dict) -> None:
    assert "bedrock:humanize" in context(prompt(tmp_path, "напиши ей что я опоздаю", settings))


def test_a_broken_settings_file_keeps_bedrock_s_trigger(tmp_path: Path) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text("{nope")
    assert "bedrock:humanize" in context(prompt(tmp_path, "напиши ей что я опоздаю"))


@pytest.mark.parametrize("source", ["loop_wakeup", "sdk"])
def test_only_the_owners_prompt_triggers(tmp_path: Path, source: str) -> None:
    assert "humanize" not in context(prompt(tmp_path, "напиши ей что я опоздаю", source=source))


def test_the_bundled_skill_is_the_new_one_without_a_profile() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: humanize\ndescription: ")
    assert "$HUMANIZE_PROFILE" in text
    assert (SKILL / "scripts" / "lint.py").is_file()
    assert not (SKILL / "profile").exists()
    assert "claude-humanize-skill at " in (SKILL / "SOURCE").read_text()


def test_the_bundled_lint_runs_without_a_profile(tmp_path: Path) -> None:
    draft = tmp_path / "draft.txt"
    draft.write_text("ок, буду в пять\n")
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    done = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "lint.py"), str(draft)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert done.returncode in (0, 1), done.stderr
    assert "Traceback" not in done.stderr


SOURCE = ROOT.parent / "claude-humanize-skill"


@pytest.mark.skipif(not (SOURCE / "skill" / "SKILL.md").is_file(), reason="source repo absent")
def test_the_copy_matches_its_source() -> None:
    done = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sync_humanize.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stdout
