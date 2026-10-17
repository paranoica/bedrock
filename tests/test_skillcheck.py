import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins" / "bedrock" / "scripts" / "skillcheck.py"


def run(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    if root.is_dir():
        write(root / ".claude-plugin" / "plugin.json", '{"name": "demo"}')
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def skill(root: Path, name: str, description: str, body: str = "Body.\n", extra: str = "") -> Path:
    front = f"---\nname: {name}\ndescription: {description}\n{extra}---\n"
    return write(root / "skills" / name / "SKILL.md", front + body)


def agent(root: Path, name: str, fields: str) -> Path:
    text = f"---\nname: {name}\n{fields}---\nYou are an agent.\n"
    return write(root / "agents" / f"{name}.md", text)


def words(n: int, word: str = "word") -> str:
    return " ".join([word] * n)


def test_empty_plugin_is_clean(tmp_path: Path) -> None:
    assert run(tmp_path).returncode == 0


def test_missing_root_cannot_run(tmp_path: Path) -> None:
    assert run(tmp_path / "absent").returncode == 2


def test_valid_skill_passes(tmp_path: Path) -> None:
    skill(tmp_path, "debug", "Diagnose a failure loop-first. Triggers debug, разберись.")
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_skill_without_frontmatter_fails(tmp_path: Path) -> None:
    write(tmp_path / "skills" / "debug" / "SKILL.md", "No frontmatter here.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "frontmatter" in result.stdout


def test_skill_name_must_match_folder(tmp_path: Path) -> None:
    write(tmp_path / "skills" / "debug" / "SKILL.md", "---\nname: other\ndescription: x\n---\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "name" in result.stdout


def test_model_invoked_description_at_token_budget_passes(tmp_path: Path) -> None:
    skill(tmp_path, "day", words(46))
    assert run(tmp_path).returncode == 0


def test_model_invoked_description_over_token_budget_fails(tmp_path: Path) -> None:
    skill(tmp_path, "day", words(47))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "description" in result.stdout


def test_cyrillic_words_weigh_three_tokens(tmp_path: Path) -> None:
    skill(tmp_path, "ok", words(20, "слово"))
    assert run(tmp_path).returncode == 0
    skill(tmp_path, "long", words(21, "слово"))
    assert run(tmp_path).returncode == 1


def test_folded_description_is_measured_whole(tmp_path: Path) -> None:
    body = "---\nname: day\ndescription: >\n  " + words(30) + "\n  " + words(17) + "\n---\nBody.\n"
    write(tmp_path / "skills" / "day" / "SKILL.md", body)
    assert run(tmp_path).returncode == 1


def test_user_invoked_skill_needs_one_line_description(tmp_path: Path) -> None:
    extra = "disable-model-invocation: true\n"
    skill(tmp_path, "retro", words(70), extra=extra)
    assert run(tmp_path).returncode == 0
    body = (
        "---\nname: retro\ndescription: >\n  first line\n  second line\n"
        "disable-model-invocation: true\n---\n"
    )
    write(tmp_path / "skills" / "retro" / "SKILL.md", body)
    assert run(tmp_path).returncode == 1


def test_skill_line_budget_boundary(tmp_path: Path) -> None:
    head = "---\nname: day\ndescription: x\n---\n"
    write(tmp_path / "skills" / "day" / "SKILL.md", head + "line\n" * (250 - 4))
    assert run(tmp_path).returncode == 0
    write(tmp_path / "skills" / "day" / "SKILL.md", head + "line\n" * (251 - 4))
    assert run(tmp_path).returncode == 1


def test_reference_line_budget_boundary(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x")
    ref = tmp_path / "skills" / "day" / "references" / "lean.md"
    write(ref, "line\n" * 300)
    assert run(tmp_path).returncode == 0
    write(ref, "line\n" * 301)
    assert run(tmp_path).returncode == 1


def test_three_semicolons_in_a_sentence_fail(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="One; two; three is fine.\n")
    assert run(tmp_path).returncode == 0
    skill(tmp_path, "day", "x", body="One; two; three; four is too many.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "semicolon" in result.stdout


def test_semicolons_in_code_are_ignored(tmp_path: Path) -> None:
    body = "Run `a; b; c; d` now.\n\n```\nx; y; z; w\n```\n"
    skill(tmp_path, "day", "x", body=body)
    assert run(tmp_path).returncode == 0


def test_broken_relative_link_fails(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="See [lean](references/lean.md).\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "lean.md" in result.stdout
    write(tmp_path / "skills" / "day" / "references" / "lean.md", "Lean.\n")
    assert run(tmp_path).returncode == 0


def test_external_and_anchor_links_are_ignored(tmp_path: Path) -> None:
    body = "See [docs](https://example.com/x.md) and [here](#section).\n"
    skill(tmp_path, "day", "x", body=body)
    assert run(tmp_path).returncode == 0


def test_backticked_reference_path_must_exist(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="Read `references/tdd.md` first.\n")
    assert run(tmp_path).returncode == 1
    write(tmp_path / "skills" / "day" / "references" / "tdd.md", "TDD.\n")
    assert run(tmp_path).returncode == 0


def test_valid_agent_passes(tmp_path: Path) -> None:
    fields = "description: Plan critic on Opus.\nmodel: opus\neffort: high\nmaxTurns: 10\n"
    agent(tmp_path, "critic", fields)
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_agent_with_unknown_model_fails(tmp_path: Path) -> None:
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: gpt\n")
    assert run(tmp_path).returncode == 1


def test_agent_full_model_id_passes(tmp_path: Path) -> None:
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: claude-opus-5-5\n")
    assert run(tmp_path).returncode == 0


def test_agent_with_unknown_effort_fails(tmp_path: Path) -> None:
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: opus\neffort: extreme\n")
    assert run(tmp_path).returncode == 1


def test_agent_max_turns_must_be_positive(tmp_path: Path) -> None:
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: opus\nmaxTurns: 0\n")
    assert run(tmp_path).returncode == 1
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: opus\nmaxTurns: 1\n")
    assert run(tmp_path).returncode == 0


def test_agent_name_must_match_file(tmp_path: Path) -> None:
    write(tmp_path / "agents" / "critic.md", "---\nname: other\ndescription: x\nmodel: opus\n---\n")
    assert run(tmp_path).returncode == 1


def test_long_agent_description_warns_and_strict_fails(tmp_path: Path) -> None:
    agent(tmp_path, "critic", f"description: {words(20)}\nmodel: opus\n")
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN" in result.stdout
    assert run(tmp_path, "--strict").returncode == 1


def test_long_sentence_warns(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body=words(45) + ".\n")
    result = run(tmp_path)
    assert result.returncode == 0
    assert "WARN" in result.stdout


def test_findings_name_file_and_line(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="Fine.\nOne; two; three; four.\n")
    result = run(tmp_path)
    assert "skills/day/SKILL.md:6:" in result.stdout


def test_links_inside_fenced_code_are_ignored(tmp_path: Path) -> None:
    body = "Example:\n\n```\nSee [x](references/missing.md) and `references/missing.md`.\n```\n"
    skill(tmp_path, "day", "x", body=body)
    assert run(tmp_path).returncode == 0


def test_table_rows_skip_sentence_checks(tmp_path: Path) -> None:
    body = "| a; b | c; d | e; f |\n|---|---|---|\n| " + words(45) + " | x | y |\n"
    skill(tmp_path, "day", "x", body=body)
    result = run(tmp_path, "--strict")
    assert result.returncode == 0, result.stdout


def test_table_rows_still_check_links(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="| see | [lean](references/lean.md) |\n")
    assert run(tmp_path).returncode == 1


def test_undecodable_file_cannot_run(tmp_path: Path) -> None:
    path = tmp_path / "skills" / "day" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe---\nname: day\n---\n")
    result = run(tmp_path)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


def test_integer_effort_is_accepted(tmp_path: Path) -> None:
    agent(tmp_path, "critic", "description: Plan critic.\nmodel: opus\neffort: 7\n")
    assert run(tmp_path).returncode == 0


def test_skill_frontmatter_model_and_effort_are_checked(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", extra="effort: extreme\n")
    assert run(tmp_path).returncode == 1
    skill(tmp_path, "day", "x", extra="model: gpt\n")
    assert run(tmp_path).returncode == 1
    skill(tmp_path, "day", "x", extra="model: opus\neffort: xhigh\n")
    assert run(tmp_path).returncode == 0


def test_byte_order_mark_is_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "skills" / "day" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text("﻿---\nname: day\ndescription: x\n---\nBody.\n", encoding="utf-8")
    result = run(tmp_path)
    assert result.returncode == 0, result.stdout


def test_link_syntax_inside_inline_code_is_ignored(tmp_path: Path) -> None:
    skill(tmp_path, "day", "x", body="Write `[a](b.md)` for a link.\n")
    assert run(tmp_path).returncode == 0


def test_reference_paths_inside_references_resolve_from_the_skill_root(tmp_path: Path) -> None:
    skill(tmp_path, "demo", "Does a thing.", "See `references/a.md`.\n")
    write(tmp_path / "skills" / "demo" / "references" / "a.md", "Then read `references/b.md`.\n")
    write(tmp_path / "skills" / "demo" / "references" / "b.md", "End.\n")
    assert run(tmp_path).returncode == 0
    write(tmp_path / "skills" / "demo" / "references" / "a.md", "Then read `references/c.md`.\n")
    assert run(tmp_path).returncode == 1


def test_a_folder_that_is_not_a_plugin_cannot_run(tmp_path: Path) -> None:
    skill(tmp_path / "plugins" / "demo", "debug", "Diagnose a failure. Triggers debug, разберись.")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 2 and "plugin.json" in result.stderr


def test_a_ported_skill_keeps_its_own_style_but_not_broken_links(tmp_path: Path) -> None:
    long_body = (words(45) + ".\n") + ("line\n" * 260) + "See [x](missing.md).\n"
    skill(
        tmp_path, "design-creator", "Web design engine. Use for редизайн, design this.", long_body
    )
    result = run(tmp_path, "--strict")
    assert result.returncode == 1
    assert "missing.md" in result.stdout
    assert "length" not in result.stdout and "long-sentence" not in result.stdout


def test_a_ported_skill_s_references_keep_their_style(tmp_path: Path) -> None:
    skill(tmp_path, "code-review", "Audit code. Use for review, проверь.")
    write(tmp_path / "skills" / "code-review" / "references" / "x.md", words(45) + ".\n" * 1)
    write(tmp_path / "skills" / "code-review" / "references" / "y.md", "line\n" * 310)
    assert run(tmp_path, "--strict").returncode == 0
    skill(tmp_path, "debug", "Diagnose a failure. Triggers debug, разберись.")
    write(tmp_path / "skills" / "debug" / "references" / "x.md", words(45) + ".\n")
    assert run(tmp_path, "--strict").returncode == 1


def _map(root: Path, names: str) -> None:
    body = "## Skill map\n| When | Skill | Check |\n|---|---|---|\n" + "".join(
        f"| x | `{n}` | y |\n" for n in names.split()
    )
    skill(root, "next", "Navigator. Use for что дальше, what next.", body)


def test_every_skill_is_in_the_navigator_map(tmp_path: Path) -> None:
    _map(tmp_path, "debug")
    skill(tmp_path, "debug", "Diagnose a failure. Triggers debug, разберись.")
    skill(tmp_path, "hunt", "Break green code. Use for сломай, break it.")
    result = run(tmp_path)
    assert result.returncode == 1 and "hunt" in result.stdout and "registry" in result.stdout


def test_the_map_names_only_real_skills(tmp_path: Path) -> None:
    _map(tmp_path, "debug ghost")
    skill(tmp_path, "debug", "Diagnose a failure. Triggers debug, разберись.")
    result = run(tmp_path)
    assert result.returncode == 1 and "ghost" in result.stdout


def test_a_complete_map_is_clean(tmp_path: Path) -> None:
    _map(tmp_path, "debug")
    skill(tmp_path, "debug", "Diagnose a failure. Triggers debug, разберись.")
    assert run(tmp_path).returncode == 0
