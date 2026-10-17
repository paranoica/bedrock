from pathlib import Path

from bedrock_lib import projectcheck

GOOD = {
    "project": "Acme",
    "commands": {"test": {"run": "pytest -q", "suite": "py", "heavy": True}},
    "critical_zones": ["src/ingest/**", "migrations/**"],
    "packs": ["python"],
    "kb": {"roots": ["src"]},
    "agents": "read-only",
    "compact_window": 200000,
    "leaks": {"allow": ["claude"], "ignore": ["tests/fixtures/*"]},
    "checks": {"allow_hosts": ["pypi.org"]},
    "bench": {"answer_key": "../bench-key"},
}


def test_a_good_settings_file_is_clean(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "python.md").write_text("# Python\n")
    assert projectcheck.check(GOOD, packs) == []


def test_every_bad_section_is_named(tmp_path: Path) -> None:
    bad = {
        "project": "../x",
        "commands": {"test": {"suite": "py"}},
        "critical_zones": "src/**",
        "packs": ["cobol"],
        "kb": {"roots": "src"},
        "agents": "some",
        "compact_window": 5,
        "leaks": {"allow": "claude"},
        "bench": {"answer_key": ""},
        "colour": "red",
    }
    found = " | ".join(projectcheck.check(bad, tmp_path))
    for word in (
        "project",
        "commands",
        "critical_zones",
        "cobol",
        "kb.roots",
        "agents",
        "compact_window",
        "leaks.allow",
        "unknown key 'colour'",
    ):
        assert word in found, word


def test_no_commands_is_a_problem(tmp_path: Path) -> None:
    assert any("commands" in p for p in projectcheck.check({"project": "Acme"}, tmp_path))


def test_the_shipped_template_passes_the_check() -> None:
    template = projectcheck.PACKS.parent / "templates" / "project" / "bedrock.json"
    assert projectcheck.check(__import__("json").loads(template.read_text())) == []


def test_odd_shapes_are_problems_not_crashes(tmp_path: Path) -> None:
    for bad in ({"agents": []}, {"agents": {"x": 1}}):
        assert any("agents" in p for p in projectcheck.check({**GOOD, **bad}, tmp_path))
    found = projectcheck.check(
        {**GOOD, "kb": {"root": ["src"]}, "leaks": {"alow": []}, "packs": ["../packs/python"]},
        tmp_path,
    )
    text = " | ".join(found)
    assert "kb.root" in text and "leaks.alow" in text and "../packs/python" in text
