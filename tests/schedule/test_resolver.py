from __future__ import annotations

from pathlib import Path

from easy_a.schedule.resolver import ResolutionOutcome, resolve_historical_section

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_known_historical_section_matches_exactly() -> None:
    result = resolve_historical_section(
        _fixture("schedule_historical_202408_89033.html"),
        crn="89033",
        expected_subject="MAC",
        expected_course="1105",
    )

    assert result.outcome is ResolutionOutcome.matched
    assert result.candidate_count == 1
    assert result.section is not None
    assert result.section.section_number == "001"
    assert result.section.instructor_raw == "I. Rothstein"
    assert result.section.campus == "Tampa"
    assert result.section.delivery_method == "CL"
    assert result.section.primary_status == "Closed"
    assert result.section.secondary_status == "A"


def test_no_rows_is_business_not_found_outcome() -> None:
    result = resolve_historical_section(_fixture("schedule_not_found.html"), crn="50750")
    assert result.outcome is ResolutionOutcome.not_found
    assert result.section is None


def test_multiple_rows_is_ambiguous_without_guessing() -> None:
    result = resolve_historical_section(_fixture("schedule_ambiguous.html"), crn="99999")
    assert result.outcome is ResolutionOutcome.ambiguous
    assert result.candidate_count == 2
    assert result.section is None


def test_expected_course_mismatch_does_not_fuzzy_match() -> None:
    result = resolve_historical_section(
        _fixture("schedule_historical_202408_89033.html"),
        crn="89033",
        expected_subject="ENC",
    )
    assert result.outcome is ResolutionOutcome.not_found
    assert result.reason is not None
