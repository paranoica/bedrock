import os
import subprocess
from pathlib import Path

import pytest
from bedrock_lib import kb, kbdrift

DECISION = """---
type: decision
code: ACME-D1
status: {status}
date: 2026-10-01
decided_by: owner
tags: [decision]
parent: "[[decisions]]"
updated: 2026-10-01
---
# ACME-D1. Chunk size

## Decision
512 tokens.

## Why
Measured on the eval set (evals/chunks.md:12).

## Rejected
1024: recall dropped.

## Consequences
More chunks.

## Does not cancel
Nothing.

## Risk accepted
Slightly higher cost.
"""


INDEX = '---\ntype: index\ntags: [index]\nparent: "[[entry]]"\nupdated: 2026-10-17\n---\n'
MODULE_HEAD = (
    '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\n'
    "updated: 2026-10-17\ncovers: [src/ingest]\nanchors: []\nverified_at: abc\n---\n"
)
RUNBOOK_HEAD = '---\ntype: runbook\ntags: [runbook]\nparent: "[[runbooks]]"\n'


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def bank(tmp_path: Path) -> Path:
    root = tmp_path / "bank"
    kb.init(root, "Acme", "ACME", today="2026-10-17")
    return root


def problems(bank: Path, today: str = "2026-10-17") -> list[str]:
    return [p.message for p in kb.validate(bank, "Acme", today=today)]


def test_init_creates_a_valid_minimal_project(bank: Path) -> None:
    folder = bank / "Acme"
    for name in (
        "entry",
        "summary",
        "status",
        "architecture",
        "decisions",
        "failures",
        "runbooks",
        "handoffs",
        "faq",
        "open-questions",
    ):
        assert (folder / f"{name}.md").exists(), name
    assert (bank / ".git").exists()
    assert problems(bank) == []


def test_frontmatter_is_parsed() -> None:
    note = kb.parse(
        "x", '---\ntype: module\ncovers: [src/a, src/b]\nparent: "[[architecture]]"\n---\n# X\n'
    )
    assert note.meta["covers"] == ["src/a", "src/b"]
    assert note.meta["parent"] == "[[architecture]]"
    assert note.links == ["architecture"]


def test_broken_link_is_found(bank: Path) -> None:
    write(
        bank / "Acme",
        "decisions",
        INDEX + "# Decisions\n- [[ACME-D9]]\n",
    )
    assert any("ACME-D9" in m and "broken link" in m for m in problems(bank))


def test_missing_fields_and_headings(bank: Path) -> None:
    write(
        bank / "Acme" / "decisions",
        "ACME-D1",
        "---\ntype: decision\ncode: ACME-D1\n---\n# ACME-D1\n## Decision\nx\n",
    )
    found = " ".join(problems(bank))
    assert "missing field 'status'" in found
    assert "missing heading 'Why'" in found


def test_decision_code_needs_the_project_prefix(bank: Path) -> None:
    text = DECISION.format(status="accepted").replace("ACME-D1", "D1")
    write(bank / "Acme" / "decisions", "D1", text)
    assert any("project prefix" in m for m in problems(bank))


def test_edit_history_in_the_body_is_flagged(bank: Path) -> None:
    text = DECISION.format(status="accepted").replace(
        "512 tokens.", "512 tokens (previously 1024, updated on 2026-10-05)."
    )
    write(bank / "Acme" / "decisions", "ACME-D1", text)
    assert any("edit history" in m for m in problems(bank))


def test_superseded_decision_linked_as_current(bank: Path) -> None:
    write(bank / "Acme" / "decisions", "ACME-D1", DECISION.format(status="superseded"))
    body = "# Ingest\n## Purpose\nx\n## Boundaries\nx\n## Rules\nChunks follow [[ACME-D1]].\n"
    module = MODULE_HEAD + body + "## Pitfalls\nx\n"
    write(bank / "Acme" / "architecture", "ingest", module)
    assert any("superseded" in m and "ACME-D1" in m for m in problems(bank))


def test_orphan_and_long_notes(bank: Path) -> None:
    write(
        bank / "Acme" / "runbooks",
        "deploy",
        RUNBOOK_HEAD
        + "updated: 2026-10-17\nverified: 2026-10-17\n---\n# Deploy\n## Steps\n"
        + "x\n" * 310
        + "## Check it worked\n## Traps\n",
    )
    found = " ".join(problems(bank))
    assert "orphan" in found
    assert "over 300 lines" in found


def test_runbook_older_than_thirty_days_needs_reverification(bank: Path) -> None:
    write(
        bank / "Acme" / "runbooks",
        "deploy",
        RUNBOOK_HEAD
        + "updated: 2026-09-01\nverified: 2026-09-01\n---\n"
        + "# Deploy\n## Steps\n## Check it worked\n## Traps\n",
    )
    write(
        bank / "Acme",
        "runbooks",
        INDEX + "# Runbooks\n- [[deploy]]\n",
    )
    assert any("re-verify" in m for m in problems(bank))
    assert not any("re-verify" in m for m in problems(bank, today="2026-09-20"))


def sh(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def code(tmp_path: Path) -> Path:
    repo = tmp_path / "code"
    (repo / "src" / "ingest").mkdir(parents=True)
    (repo / "src" / "search").mkdir(parents=True)
    sh(repo, "init", "-q")
    sh(repo, "config", "user.email", "t@example.com")
    sh(repo, "config", "user.name", "t")
    (repo / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 1\n\n\ndef join():\n    return 2\n"
    )
    (repo / "src" / "search" / "find.py").write_text("x = 1\n")
    sh(repo, "add", ".")
    sh(repo, "commit", "-qm", "chore: start")
    return repo


def module_note(bank: Path, commit: str, anchors: str = "[]") -> None:
    text = (
        '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\nupdated: 2026-10-17\n'
        f"covers: [src/ingest]\nanchors: {anchors}\nverified_at: {commit}\n---\n# Ingest\n"
        "## Purpose\nx\n## Boundaries\nx\n## Rules\nx\n## Pitfalls\nx\n"
    )
    write(bank / "Acme" / "architecture", "ingest", text)


def test_drift_lists_notes_whose_code_changed(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert kbdrift.drift(bank, "Acme", code) == []
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 2\n"
    )
    sh(code, "commit", "-qam", "fix: x")
    found = kbdrift.drift(bank, "Acme", code)
    assert len(found) == 1
    assert "ingest" in found[0] and "src/ingest/chunk.py" in found[0]


def test_drift_with_anchors_counts_only_the_anchored_symbols(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 2\n"
    )
    sh(code, "commit", "-qam", "fix: x")
    assert kbdrift.drift(bank, "Acme", code) == []
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 3\n\n\ndef join():\n    return 9\n"
    )
    sh(code, "commit", "-qam", "fix: y")
    assert len(kbdrift.drift(bank, "Acme", code)) == 1


def test_drift_with_an_unknown_commit_says_so(bank: Path, code: Path) -> None:
    module_note(bank, "deadbeef")
    assert "unknown commit" in kbdrift.drift(bank, "Acme", code)[0]


def test_module_without_a_note_is_flagged(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert kb.uncovered(bank, "Acme", code, ["src"]) == ["src/search"]


def test_backlinks(bank: Path) -> None:
    assert "entry" in kb.backlinks(bank, "Acme", "status")


def test_notes_covering_changed_files(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    assert [n.name for n in kb.covering(bank, "Acme", ["src/ingest/chunk.py"])] == ["ingest"]
    assert kb.covering(bank, "Acme", ["src/search/find.py"]) == []


def test_hidden_folders_are_not_modules(bank: Path, code: Path) -> None:
    (code / ".github").mkdir()
    assert kb.uncovered(bank, "Acme", code, ["."]) == ["src"]


# review round


def test_block_lists_in_frontmatter_are_read() -> None:
    note = kb.parse(
        "x", "---\ntype: module\ncovers:\n  - src/a\n  - src/b\ntags:\n  - x\n---\n# X\n"
    )
    assert note.meta["covers"] == ["src/a", "src/b"]
    assert note.meta["tags"] == ["x"]


def test_duplicate_note_names_are_flagged_and_both_validated(bank: Path) -> None:
    write(bank / "Acme" / "runbooks", "deploy", "---\ntype: runbook\n---\n# a\n")
    write(bank / "Acme" / "archive", "deploy", "---\ntype: runbook\n---\n# b [[nowhere]]\n")
    found = " ".join(problems(bank))
    assert "name collision" in found
    assert "nowhere" in found


def test_empty_and_placeholder_fields_count_as_missing(bank: Path) -> None:
    text = DECISION.format(status="accepted").replace("decided_by: owner", "decided_by:")
    text = text.replace("date: 2026-10-01", "date: {date}")
    write(bank / "Acme" / "decisions", "ACME-D1", text)
    found = " ".join(problems(bank))
    assert "missing field 'decided_by'" in found
    assert "missing field 'date'" in found


def test_bad_runbook_date_is_reported(bank: Path) -> None:
    head = RUNBOOK_HEAD + "updated: 2026-10-17\nverified: soon\n---\n"
    write(
        bank / "Acme" / "runbooks", "deploy", head + "# D\n## Steps\n## Check it worked\n## Traps\n"
    )
    write(bank / "Acme", "runbooks", INDEX + "# Runbooks\n- [[deploy]]\n")
    assert any("not a date" in m for m in problems(bank))


def test_superseded_decision_linked_by_path(bank: Path) -> None:
    write(bank / "Acme" / "decisions", "ACME-D1", DECISION.format(status="superseded"))
    body = "# Ingest\n## Purpose\nx\n## Boundaries\nx\n## Rules\nSee [[decisions/ACME-D1]].\n"
    write(bank / "Acme" / "architecture", "ingest", MODULE_HEAD + body + "## Pitfalls\nx\n")
    assert any("superseded" in m for m in problems(bank))


def test_failure_notes_may_describe_history(bank: Path) -> None:
    text = (
        "---\ntype: failure\ncode: ACME-F1\ndate: 2026-10-01\ntags: [failure]\n"
        'parent: "[[failures]]"\n'
        "updated: 2026-10-01\n---\n# ACME-F1. Lock\n## Tried\nThe flag was changed to 0.\n"
        "## Failed because\nIt previously held the lock.\n## Mechanism\nx\n## Caught now by\nx\n"
    )
    write(bank / "Acme" / "failures", "ACME-F1", text)
    assert not any("edit history" in m for m in problems(bank))


def test_escaped_pipe_and_fenced_links(bank: Path) -> None:
    write(
        bank / "Acme",
        "status",
        (bank / "Acme" / "status.md").read_text()
        + "\n| a | [[entry\\|Home]] |\n```\n[[not-a-note]]\n```\n",
    )
    found = " ".join(problems(bank))
    assert "entry\\" not in found
    assert "not-a-note" not in found


def test_drift_inside_a_class_method_with_anchors(bank: Path, code: Path) -> None:
    cls = (
        "class Chunker:\n    def split(self):\n        return 1\n\n"
        "    def join(self):\n        return 2\n"
    )
    (code / "src" / "ingest" / "chunk.py").write_text(cls)
    sh(code, "commit", "-qam", "chore: class")
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    (code / "src" / "ingest" / "chunk.py").write_text(cls.replace("return 2", "return 9"))
    sh(code, "commit", "-qam", "fix: join")
    assert len(kbdrift.drift(bank, "Acme", code)) == 1


def test_drift_reports_covered_paths_that_do_not_exist(bank: Path, code: Path) -> None:
    text = (
        '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\nupdated: 2026-10-17\n'
        f"covers: [src/ingets]\nanchors: []\nverified_at: {sh(code, 'rev-parse', 'HEAD')}\n"
        "---\n# I\n"
    )
    write(bank / "Acme" / "architecture", "ingest", text)
    assert "does not exist" in " ".join(kbdrift.drift(bank, "Acme", code))


def test_uncovered_skips_vendored_folders(bank: Path, code: Path) -> None:
    (code / "node_modules").mkdir()
    (code / "dist").mkdir()
    assert kb.uncovered(bank, "Acme", code, ["."]) == ["src"]


def test_stale_handoff_is_flagged_after_a_newer_decision(bank: Path) -> None:
    write(
        bank / "Acme" / "decisions",
        "ACME-D2",
        DECISION.format(status="accepted")
        .replace("ACME-D1", "ACME-D2")
        .replace("date: 2026-10-01", "date: 2026-10-10"),
    )
    handoff = (
        '---\ntype: handoff\ntags: [handoff]\nparent: "[[handoffs]]"\nupdated: 2026-10-05\n'
        "stands_on: [ACME-D1]\n---\n# Handoff\n"
    )
    write(bank / "Acme" / "handoffs", "h1", handoff)
    assert any("re-check before use" in m for m in problems(bank))


def test_drift_sees_a_file_moved_out_of_the_covered_folder(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    sh(code, "mv", "src/ingest/chunk.py", "src/search/chunk.py")
    sh(code, "commit", "-qm", "refactor: move")
    found = kbdrift.drift(bank, "Acme", code)
    assert len(found) == 1 and "src/ingest/chunk.py" in found[0]


def test_drift_with_non_ascii_and_spaced_names(bank: Path, code: Path) -> None:
    source = "def split():\n    return 1\n\n\ndef join():\n    return 2\n"
    for name in ("файл.py", "my chunk.py"):
        (code / "src" / "ingest" / name).write_text(source)
    sh(code, "add", ".")
    sh(code, "commit", "-qm", "chore: more")
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    for name in ("файл.py", "my chunk.py"):
        (code / "src" / "ingest" / name).write_text(source.replace("return 2", "return 9"))
    sh(code, "commit", "-qam", "fix: join")
    found = " ".join(kbdrift.drift(bank, "Acme", code))
    assert "stale" in found and "файл.py" in found and "my chunk.py" in found
    assert "does not exist" not in found


def test_a_single_anchor_without_brackets_still_counts(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="join")
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 1\n\n\ndef join():\n    return 9\n"
    )
    sh(code, "commit", "-qam", "fix: join")
    assert len(kbdrift.drift(bank, "Acme", code)) == 1


def test_code_added_or_removed_next_to_an_anchor_is_not_drift(bank: Path, code: Path) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    chunk = code / "src" / "ingest" / "chunk.py"
    chunk.write_text(chunk.read_text() + "\n\ndef other():\n    return 3\n")
    sh(code, "commit", "-qam", "feat: other")
    assert kbdrift.drift(bank, "Acme", code) == []
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[split]")
    chunk.write_text("def split():\n    return 1\n")
    sh(code, "commit", "-qam", "refactor: drop join and other")
    assert kbdrift.drift(bank, "Acme", code) == []


def test_drift_ignores_forced_colour_in_git_config(bank: Path, code: Path) -> None:
    sh(code, "config", "color.ui", "always")
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    (code / "src" / "ingest" / "chunk.py").write_text(
        "def split():\n    return 1\n\n\ndef join():\n    return 9\n"
    )
    sh(code, "commit", "-qam", "fix: join")
    assert len(kbdrift.drift(bank, "Acme", code)) == 1


def test_drift_budget_holds_inside_one_note(
    bank: Path, code: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    for index in range(3):
        (code / "src" / "ingest" / f"m{index}.py").write_text("def join():\n    return 1\n")
    sh(code, "add", ".")
    sh(code, "commit", "-qm", "feat: more")
    ticks = iter(range(1000))
    monkeypatch.setattr(kbdrift.time, "monotonic", lambda: next(ticks))
    found = kbdrift.drift(bank, "Acme", code, budget=1.5)
    assert any("truncated" in line for line in found)


def test_a_hanging_git_is_reported_not_raised(
    bank: Path, code: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    real = kbdrift.subprocess.run

    def slow(argv, *args, **kwargs):
        if "diff" in argv:
            raise subprocess.TimeoutExpired(argv, 30)
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(kbdrift.subprocess, "run", slow)
    assert "truncated" in " ".join(kbdrift.drift(bank, "Acme", code))


def test_block_lists_without_indent_are_read() -> None:
    note = kb.parse("n", "---\ntype: module\ncovers:\n- src/a\n- src/b\nupdated: x\n---\n")
    assert note.meta["covers"] == ["src/a", "src/b"]


def test_compact_or_week_dates_are_not_dates(bank: Path) -> None:
    text = (
        (bank / "Acme" / "status.md")
        .read_text()
        .replace("updated: 2026-10-17", "updated: 20261017")
    )
    write(bank / "Acme", "status", text)
    assert any("is not a date" in m for m in problems(bank))


def test_fingerprint_sees_body_lines_that_look_like_stamps() -> None:
    head = "---\ntype: module\nverified_at: a\nupdated: 2026-10-17\n---\n"
    assert kb.fingerprint(head + "updated: chunks are 2KB\n") != kb.fingerprint(
        head + "updated: chunks are 4KB\n"
    )
    restamped = head.replace("verified_at: a", "verified_at: b").replace("10-17", "10-18")
    assert kb.fingerprint(head + "x\n") == kb.fingerprint(restamped + "x\n")


def test_a_rechecked_or_finished_handoff_is_clean(bank: Path) -> None:
    write(
        bank / "Acme" / "decisions",
        "ACME-D2",
        DECISION.format(status="accepted")
        .replace("ACME-D1", "ACME-D2")
        .replace("date: 2026-10-01", "date: 2026-10-10"),
    )
    head = '---\ntype: handoff\ntags: [handoff]\nparent: "[[handoffs]]"\n'
    write(bank / "Acme" / "handoffs", "h1", head + "updated: 2026-10-11\n---\n# H\n")
    write(bank / "Acme" / "handoffs", "h2", head + "updated: 2026-10-05\nstatus: done\n---\n# H\n")
    assert not any("re-check before use" in m for m in problems(bank))


def test_a_faq_card_from_the_template_validates(bank: Path) -> None:
    assert (bank / "Acme" / "faq.md").exists()
    card = (kb.TEMPLATES / "faq.md").read_text().replace("{date}", "2026-10-17")
    card = card.replace("{commit}", "abc").replace("{the question, as the owner asks it}", "Q")
    write(bank / "Acme" / "faq", "chunk-size", card)
    faq = bank / "Acme" / "faq.md"
    faq.write_text(faq.read_text() + "- [[chunk-size]]\n")
    found = [p for p in kb.validate(bank, "Acme", today="2026-10-17") if "chunk-size" in p.path]
    assert found == []


def test_a_hanging_git_stops_at_the_budget(
    bank: Path, code: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_note(bank, sh(code, "rev-parse", "HEAD"))
    timeouts: list[float] = []

    def hang(argv, *args, **kwargs):
        timeouts.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr(kbdrift.subprocess, "run", hang)
    found = " ".join(kbdrift.drift(bank, "Acme", code, budget=2.0))
    assert "truncated" in found and "unknown commit" not in found
    assert timeouts and max(timeouts) <= 2.0


def test_drift_survives_undecodable_and_binary_files(bank: Path, code: Path) -> None:
    odd = code / "src" / "ingest" / os.fsdecode(b"caf\xe9.py")
    odd.write_text("def join():\n    return 1\n")
    (code / "src" / "ingest" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
    sh(code, "add", ".")
    sh(code, "commit", "-qm", "chore: odd")
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    odd.write_text("def join():\n    return 2\n")
    (code / "src" / "ingest" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xfe")
    sh(code, "commit", "-qam", "fix: odd")
    found = kbdrift.drift(bank, "Acme", code)
    assert len(found) == 1 and "stale" in found[0]
    assert "caf" in found[0].encode("utf-8").decode("utf-8")


def test_glob_characters_in_a_name_match_only_that_file(bank: Path, code: Path) -> None:
    source = "def split():\n    return 1\n\n\ndef join():\n    return 2\n"
    for name in ("a[1].py", "a1.py"):
        (code / "src" / "ingest" / name).write_text(source)
    sh(code, "add", ".")
    sh(code, "commit", "-qm", "chore: two")
    module_note(bank, sh(code, "rev-parse", "HEAD"), anchors="[join]")
    (code / "src" / "ingest" / "a[1].py").write_text(source + "\n\ndef other():\n    return 3\n")
    (code / "src" / "ingest" / "a1.py").write_text(source.replace("return 2", "return 9"))
    sh(code, "commit", "-qam", "fix: one")
    found = " ".join(kbdrift.drift(bank, "Acme", code))
    assert "a1.py" in found and "a[1].py" not in found


def test_the_head_tree_is_listed_once(
    bank: Path, code: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit = sh(code, "rev-parse", "HEAD")
    for name in ("n1", "n2", "n3"):
        text = (
            '---\ntype: module\ntags: [architecture]\nparent: "[[architecture]]"\n'
            f"updated: 2026-10-17\ncovers: [src/ingest]\nverified_at: {commit}\n---\n# N\n"
        )
        write(bank / "Acme" / "architecture", name, text)
    calls: list[list[str]] = []
    real = kbdrift.subprocess.run

    def spy(argv, *args, **kwargs):
        calls.append(list(argv))
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(kbdrift.subprocess, "run", spy)
    kbdrift.drift(bank, "Acme", code)
    assert sum("ls-tree" in argv for argv in calls) == 2
