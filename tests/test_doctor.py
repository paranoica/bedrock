import json
import subprocess
from pathlib import Path

import pytest
from bedrock_lib import doctor
from bedrock_lib.config import UserConfig


class Machine:
    """A fake machine: which programs exist, what they print, what imports."""

    def __init__(self, programs: dict[str, str], modules: set[str] = frozenset()) -> None:
        self.programs, self.modules = programs, modules

    def which(self, name: str) -> str | None:
        return f"/usr/bin/{name}" if name in self.programs else None

    def run(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        out = self.programs.get(Path(argv[0]).name, "")
        return subprocess.CompletedProcess(argv, 0, out, "")

    def has_module(self, name: str) -> bool:
        return name in self.modules


FULL = {
    "git": "git version 2.51.0",
    "python3": "Python 3.14.0",
    "uvx": "uvx 0.9.0",
    "node": "v26.1.0",
    "gitleaks": "8.28.0",
    "age": "v1.2.1",
    "notify-send": "",
    "nvidia-smi": "6144",
    "folio": "",
    "claude": "2.1.302 (Claude Code)",
}


@pytest.fixture
def home(tmp_path: Path) -> Path:
    terms = tmp_path / ".config" / "bedrock" / "leak-terms.txt"
    terms.parent.mkdir(parents=True)
    terms.write_text("Name\n")
    terms.chmod(0o600)
    (tmp_path / ".cache/bedrock/design-tools/node_modules/playwright").mkdir(parents=True)
    (tmp_path / ".cache/bedrock/design-tools/node_modules/axe-core").mkdir(parents=True)
    rules = tmp_path / ".claude" / "CLAUDE.md"
    rules.parent.mkdir()
    rules.write_text(
        "# mine\n<!-- claude-output-style:begin -->\nrules\n<!-- claude-output-style:end -->\n"
    )
    voice = tmp_path / ".config" / "humanize" / "profile"
    voice.mkdir(parents=True)
    (voice / "profile.md").write_text("# voice\n")
    return tmp_path


def results(home: Path, machine: Machine, cfg: UserConfig | None = None) -> dict[str, str]:
    cfg = cfg or UserConfig(
        backup_repo=home / "b", backup_recipient="age1" + "q" * 58, state_dir=home / "s"
    )
    return {c.name: c.level for c in doctor.run(cfg, home, machine)}


def test_a_full_machine_is_all_ok(home: Path) -> None:
    found = results(home, Machine(FULL, {"faster_whisper"}))
    assert set(found.values()) == {"ok"}, found


def test_missing_required_tools_fail_and_optional_ones_warn(home: Path) -> None:
    programs = {k: v for k, v in FULL.items() if k not in ("git", "gitleaks", "folio")}
    found = results(home, Machine(programs))
    assert found["git"] == "fail"
    assert found["gitleaks"] == "warn" and found["folio"] == "warn"
    assert found["transcription"] == "warn"


def test_an_old_python_fails(home: Path) -> None:
    found = results(home, Machine({**FULL, "python3": "Python 3.11.9"}, {"faster_whisper"}))
    assert found["python3"] == "fail"


def test_small_gpu_memory_is_a_warning(home: Path) -> None:
    found = results(home, Machine({**FULL, "nvidia-smi": "2048"}, {"faster_whisper"}))
    assert found["gpu"] == "warn"


def test_a_readable_leak_list_or_missing_backup_warns(home: Path) -> None:
    (home / ".config" / "bedrock" / "leak-terms.txt").chmod(0o644)
    found = results(home, Machine(FULL, {"faster_whisper"}), UserConfig(state_dir=home / "s"))
    assert found["leak terms"] == "warn" and found["backup"] == "warn"


def test_exit_code_follows_the_worst_level(home: Path) -> None:
    assert doctor.exit_code([doctor.Check("a", "ok", ""), doctor.Check("b", "warn", "")]) == 0
    assert doctor.exit_code([doctor.Check("a", "fail", "")]) == 1


def test_missing_design_tools_warn_with_the_fix(home: Path) -> None:
    import shutil

    shutil.rmtree(home / ".cache/bedrock/design-tools")
    checks = {c.name: c for c in doctor.run(UserConfig(state_dir=home / "s"), home, Machine(FULL))}
    assert checks["design tools"].level == "warn"
    assert "npm ci" in checks["design tools"].detail


def test_transcription_in_its_own_venv_counts(home: Path) -> None:
    venv = home / ".local/share/bedrock/whisper-venv/bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("")
    checks = {c.name: c for c in doctor.run(UserConfig(state_dir=home / "s"), home, Machine(FULL))}
    assert checks["transcription"].level == "ok"


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "# my own rules only\n",
        "<!-- claude-output-style:begin -->\nrules, end marker lost\n",
        "rules\n<!-- claude-output-style:end -->\n",
    ],
)
def test_missing_answer_rules_warn_with_the_install_command(home: Path, text: str | None) -> None:
    rules = home / ".claude" / "CLAUDE.md"
    if text is None:
        rules.unlink()
    else:
        rules.write_text(text)
    found = {c.name: c for c in doctor.run(UserConfig(state_dir=home / "s"), home, Machine(FULL))}
    check = found["answer style"]
    assert check.level == "warn"
    assert "claude-output-style.git" in check.detail and "install.sh" in check.detail


def test_installed_answer_rules_are_ok(home: Path) -> None:
    found = {c.name: c for c in doctor.run(UserConfig(state_dir=home / "s"), home, Machine(FULL))}
    assert found["answer style"].level == "ok"


def humanize_check(home: Path) -> doctor.Check:
    found = {c.name: c for c in doctor.run(UserConfig(state_dir=home / "s"), home, Machine(FULL))}
    return found["humanize"]


def test_the_bundled_humanize_without_a_profile_warns_how_to_get_one(home: Path) -> None:
    (home / ".config" / "humanize" / "profile" / "profile.md").unlink()
    check = humanize_check(home)
    assert check.level == "warn"
    assert "bedrock:humanize" in check.detail and "default voice" in check.detail


@pytest.mark.parametrize("folder", [".config/humanize/profile", ".claude/skills/humanize/profile"])
def test_a_voice_profile_is_ok(home: Path, folder: str) -> None:
    (home / ".config" / "humanize" / "profile" / "profile.md").unlink()
    (home / folder).mkdir(parents=True, exist_ok=True)
    (home / folder / "profile.md").write_text("# voice\n")
    check = humanize_check(home)
    assert check.level == "ok" and str(home / folder) in check.detail


def test_the_personal_hook_is_named_when_installed(home: Path) -> None:
    hook = {"type": "command", "command": "/x/hooks/draft_trigger.sh"}
    settings = {"hooks": {"UserPromptSubmit": [{"hooks": [hook]}]}}
    (home / ".claude" / "settings.json").write_text(json.dumps(settings))
    assert "personal" in humanize_check(home).detail
