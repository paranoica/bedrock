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
