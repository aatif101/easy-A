from __future__ import annotations

import pytest

from easy_a.common.terms import (
    Season,
    TermParseError,
    normalize_banner_term_code,
    parse_banner_term,
)


@pytest.mark.parametrize(
    ("term_code", "name", "year", "season"),
    [
        ("202408", "Fall 2024", 2024, Season.fall),
        ("202501", "Spring 2025", 2025, Season.spring),
        ("202508", "Fall 2025", 2025, Season.fall),
        ("202701", "Spring 2027", 2027, Season.spring),
    ],
)
def test_parse_banner_term_examples(
    term_code: str,
    name: str,
    year: int,
    season: Season,
) -> None:
    term = parse_banner_term(term_code)

    assert term.banner_code == term_code
    assert term.name == name
    assert term.year == year
    assert term.season == season


def test_normalize_banner_term_accepts_int() -> None:
    assert normalize_banner_term_code(202408) == "202408"


@pytest.mark.parametrize("term_code", ["2024FA", "202409", "20241", "2024010"])
def test_parse_banner_term_rejects_invalid_codes(term_code: str) -> None:
    with pytest.raises(TermParseError):
        parse_banner_term(term_code)
