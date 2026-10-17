from bedrock_lib import slop


def rules(text: str, slack: bool = False) -> list[str]:
    return [finding.rule for finding in slop.check(text, slack=slack)]


def test_dashes_are_flagged_with_their_line() -> None:
    found = slop.check("ok line\nэто \u2014 тире\nи это \u2013 тоже\nа это-дефис\n")
    assert [(f.line, f.rule) for f in found] == [(2, "dash"), (3, "dash")]


def test_filler_phrases_in_both_languages() -> None:
    assert rules("Стоит отметить, что всё готово.") == ["filler"]
    assert rules("I hope this helps!") == ["filler"]
    assert rules("Let's delve into it.") == ["filler"]
    assert rules("Отметить в календаре.") == []


def test_markdown_that_breaks_in_slack() -> None:
    text = "# Title\n**bold**\n> quote\n[link](https://x.y)\n*fine* and • bullet\n"
    assert rules(text, slack=True) == ["markdown"] * 4
    assert rules(text) == []


def test_clean_text_has_no_findings() -> None:
    assert slop.check("Готово, проверил на деве: экспорт отдаёт CSV.\n") == []


def test_code_spans_and_fences_are_not_checked() -> None:
    assert rules("run `a \u2014 b`\n```\n# not a heading \u2014 ever\n```\n", slack=True) == []


def test_phrases_match_whole_words_only() -> None:
    assert rules("It ended uncertainly!") == []
