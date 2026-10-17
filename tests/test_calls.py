import hashlib
import json
from pathlib import Path

import pytest
from bedrock_lib import calls
from bedrock_lib.config import UserConfig

TRANSCRIPT = """[00:00:05] Quentin: Hi all, can you hear me?
[00:01:10] Quentin: We decided the export ships in CSV first, Excel later.
[00:02:30] Owner: Then I need the column list by Friday.
[00:03:45] Quentin: Sure, I'll send   the column list tomorrow.
"""


@pytest.fixture
def cfg(tmp_path: Path) -> UserConfig:
    return UserConfig(days_dir=tmp_path / "days", state_dir=tmp_path / "state")


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    path = tmp_path / "krisp.txt"
    path.write_text(TRANSCRIPT, encoding="utf-8")
    return path


def add(cfg: UserConfig, raw: Path, title: str = "Export sync") -> str:
    return calls.add(
        cfg,
        "Acme",
        raw,
        source="krisp",
        title=title,
        day="2026-10-16",
        participants=["Quentin", "Owner"],
        language="en",
    )


def test_add_archives_the_raw_text_read_only_with_its_checksum(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    assert call_id == "2026-10-16-export-sync"
    folder = cfg.days_dir / "Acme" / "calls" / call_id
    assert (folder / "transcript.txt").read_text(encoding="utf-8") == TRANSCRIPT
    assert not (folder / "transcript.txt").stat().st_mode & 0o222
    meta = json.loads((folder / "meta.json").read_text())
    assert meta["source"] == "krisp" and meta["participants"] == ["Quentin", "Owner"]
    assert meta["duration"] == "00:03:45"
    assert calls.verify(cfg, "Acme", call_id) is True


def test_the_same_title_twice_gets_its_own_id(cfg: UserConfig, raw: Path) -> None:
    assert add(cfg, raw) != add(cfg, raw)


def test_a_changed_raw_transcript_fails_verification(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    path = cfg.days_dir / "Acme" / "calls" / call_id / "transcript.txt"
    path.chmod(0o644)
    path.write_text(TRANSCRIPT.replace("CSV", "XML"), encoding="utf-8")
    assert calls.verify(cfg, "Acme", call_id) is False


def test_quotes_must_exist_in_the_transcript(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    debrief = (
        "## Decided\n"
        f"- CSV first. «the export ships in CSV first» ({call_id} @ 00:01:10)\n"
        "## They owe\n"
        f'- Column list. "I\'ll send the column list tomorrow" ({call_id} @ 00:03:45)\n'
        f"- Invented. «we will pay double» ({call_id} @ 00:02:00)\n"
    )
    found = calls.check_quotes(cfg, "Acme", call_id, debrief)
    assert [problem.quote for problem in found] == ["we will pay double"]


def test_a_quote_far_from_its_timecode_is_flagged(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    debrief = f"## Decided\n- «the export ships in CSV first» ({call_id} @ 00:03:40)\n"
    found = calls.check_quotes(cfg, "Acme", call_id, debrief)
    assert len(found) == 1 and "00:01:10" in found[0].reason


def test_an_item_without_a_quote_or_timecode_is_flagged(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    debrief = "## Decided\n- CSV first.\n## Notes\nfree text is fine here\n"
    found = calls.check_quotes(cfg, "Acme", call_id, debrief)
    assert [problem.line for problem in found] == [2]


def test_search_returns_quotes_with_call_and_time(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    hits = calls.search(cfg, "Acme", "COLUMN list")
    assert [(h.call, h.time) for h in hits] == [(call_id, "00:02:30"), (call_id, "00:03:45")]
    assert calls.search(cfg, "Acme", "nothing like this") == []


def test_unsafe_ids_are_refused(cfg: UserConfig) -> None:
    for bad in ("../x", "", "a/b"):
        with pytest.raises(calls.CallError):
            calls.verify(cfg, "Acme", bad)


def test_a_quote_without_a_timecode_is_flagged(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    debrief = "## Decided\n- «the export ships in CSV first»\n"
    assert [p.line for p in calls.check_quotes(cfg, "Acme", call_id, debrief)] == [2]


def test_a_quote_is_placed_at_the_line_where_it_starts(cfg: UserConfig, raw: Path) -> None:
    call_id = add(cfg, raw)
    debrief = f"## Decided\n- «the export ships in CSV first» ({call_id} @ 00:00:05)\n"
    found = calls.check_quotes(cfg, "Acme", call_id, debrief)
    assert len(found) == 1 and "found at 00:01:10" in found[0].reason


def test_an_id_cannot_reach_outside_the_archive(cfg: UserConfig, raw: Path) -> None:
    outside = cfg.days_dir / "Acme" / "x"
    outside.mkdir(parents=True)
    (outside / "transcript.txt").write_text("x")
    (outside / "meta.json").write_text(json.dumps({"sha256": hashlib.sha256(b"x").hexdigest()}))
    with pytest.raises(calls.CallError):
        calls.verify(cfg, "Acme", "../x")


SPOKEN = """[00:00:05] Alice: we will ship
[00:00:08] Alice: on friday, then test.
continued without a stamp, the release notes
[00:20:00] Bob: fine.
"""


def test_a_quote_may_run_across_speaker_lines(cfg: UserConfig, tmp_path: Path) -> None:
    raw = tmp_path / "t.txt"
    raw.write_text(SPOKEN, encoding="utf-8")
    call_id = add(cfg, raw, "Spoken")
    debrief = f"## Decided\n- «we will ship on friday» ({call_id} @ 00:00:05)\n"
    assert calls.check_quotes(cfg, "Acme", call_id, debrief) == []


def test_invented_or_misplaced_quotes_never_pass(cfg: UserConfig, tmp_path: Path) -> None:
    raw = tmp_path / "t.txt"
    raw.write_text(SPOKEN, encoding="utf-8")
    call_id = add(cfg, raw, "Spoken")
    debrief = (
        "## Decided:\n"
        f"- Shipping «...» ({call_id} @ 00:00:05)\n"
        f"- «ill ship on fri» ({call_id} @ 00:00:05)\n"
        f"- «the release notes» ({call_id} @ 00:19:59)\n"
        "1. invented thing with no quote\n"
        "+ another invented thing\n"
    )
    found = calls.check_quotes(cfg, "Acme", call_id, debrief)
    assert [p.line for p in found] == [2, 3, 4, 5, 6]
    assert found[0].reason == "the quote has no words"
    assert found[1].reason == "not in the transcript"


def test_search_keeps_who_said_it(cfg: UserConfig, raw: Path) -> None:
    add(cfg, raw)
    assert calls.search(cfg, "Acme", "column list by Friday")[0].text.startswith("Owner:")


def test_a_line_with_a_colon_is_not_a_speaker(cfg: UserConfig, tmp_path: Path) -> None:
    raw = tmp_path / "t.txt"
    raw.write_text("[00:02:00] The deadline is: Friday the 20th\n", encoding="utf-8")
    call_id = add(cfg, raw, "Deadline")
    debrief = f"## Decided\n- «the deadline is: Friday the 20th» ({call_id} @ 00:02:00)\n"
    assert calls.check_quotes(cfg, "Acme", call_id, debrief) == []
