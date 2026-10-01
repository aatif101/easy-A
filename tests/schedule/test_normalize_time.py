"""The time-cell rules of the row normaliser (shared by the live sync, ingest and the backfill).

Phase 10 gap 06 added one rule: a time cell whose every component is an unscheduled placeholder
(``TBA TBA``) is no time. The tests pin that rule narrowly. ``legacy_parse_time_range`` below is a
verbatim copy of the function as it was before the change, used as an oracle, so every other shape
is proven to behave exactly as it did.
"""

from __future__ import annotations

import itertools
import re
from datetime import time

import pytest

from easy_a.schedule.normalize import (
    RowNormalizationError,
    _parse_time_range,
    row_failure_from,
    time_cell_shape,
)
from easy_a.schedule.parser import ParsedScheduleRow, ScheduleParseError

_LEGACY_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*[ap]m)\s*[-–—]\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*[ap]m)",
    re.IGNORECASE,
)


def legacy_parse_time_range(value: str | None) -> tuple[time | None, time | None]:
    """The pre-gap-06 ``_parse_time_range`` (the oracle): raises ScheduleParseError or returns."""
    from datetime import datetime

    if value is None or value.strip().upper() in {"", "TBA", "ARR"}:
        return None, None
    ranges = list(_LEGACY_RANGE_RE.finditer(value.strip()))
    if not ranges:
        raise ScheduleParseError(f"Invalid schedule time range {value!r}.")
    if len(ranges) > 1:
        return None, None
    match = ranges[0]
    try:
        return tuple(  # type: ignore[return-value]
            datetime.strptime(re.sub(r"\s+", "", match.group(g)).upper(), "%I:%M%p").time()
            for g in ("start", "end")
        )
    except ValueError as exc:
        raise ScheduleParseError(f"Invalid schedule time range {value!r}.") from exc


@pytest.mark.parametrize("value", [None, "", "  ", "TBA", "tba", " ARR ", "Arr"])
def test_a_single_placeholder_or_empty_cell_is_still_no_time(value: str | None) -> None:
    assert _parse_time_range(value) == (None, None)


@pytest.mark.parametrize(
    "value",
    ["TBA TBA", "tba tba", "TBA  TBA", "TBA\nTBA", " TBA TBA ", "ARR ARR", "TBA ARR", "ARR TBA"]
    + ["TBA TBA TBA", "TBA ARR TBA ARR"],
)
def test_a_cell_of_only_placeholders_is_no_time(value: str) -> None:
    assert _parse_time_range(value) == (None, None)


def test_one_clock_range_and_several_ranges_behave_as_before() -> None:
    assert _parse_time_range("11:00am-12:15pm") == (time(11, 0), time(12, 15))
    assert _parse_time_range("11:00am-12:15pm 2:00pm-3:15pm") == (None, None)
    # A placeholder next to exactly one range was accepted as that range, and still is.
    assert _parse_time_range("TBA 8:00am-9:00am") == (time(8, 0), time(9, 0))


@pytest.mark.parametrize(
    "value",
    [
        "8:00am",  # a lone clock, no range
        "TBA 8:00am",  # placeholder mixed with a real time that is not a range
        "8:00am TBA",
        "TBA xyz",  # placeholder plus an unknown token
        "xyz",
        "TBA TBD",  # TBD is not an accepted placeholder
        "TBD",
        "TBA, TBA",  # punctuation is not a separator we accept
        "TBA/TBA",
        "TBA-TBA",
        "TBA TBA 9",
        "ARR?",
        "N/A",
        "13:99pm-1:00pm",  # a range-shaped cell with an impossible clock
        "25:00am-26:00pm",
    ],
)
def test_every_other_previously_rejected_shape_is_still_rejected(value: str) -> None:
    with pytest.raises(ScheduleParseError):
        legacy_parse_time_range(value)  # the oracle: it was rejected before
    with pytest.raises(ScheduleParseError) as raised:
        _parse_time_range(value)
    assert isinstance(raised.value, RowNormalizationError)
    assert raised.value.field == "time"
    assert str(raised.value) == f"Invalid schedule time range {value!r}."  # message unchanged


def test_new_behaviour_differs_from_the_old_only_on_all_placeholder_multi_component_cells() -> None:
    """Exhaustive over every 1 to 4 token combination of a small vocabulary."""
    vocabulary = ["TBA", "ARR", "tba", "TBD", "xyz", "8:00am", "8:00am-9:00am", "9:00am - 10:00am"]
    differences: list[str] = []
    for length in range(1, 5):
        for tokens in itertools.product(vocabulary, repeat=length):
            value = " ".join(tokens)
            try:
                old: object = legacy_parse_time_range(value)
            except ScheduleParseError:
                old = ScheduleParseError
            try:
                new: object = _parse_time_range(value)
            except ScheduleParseError:
                new = ScheduleParseError
            if old != new:
                differences.append(value)
                assert old is ScheduleParseError
                assert new == (None, None)
                assert all(token.upper() in {"TBA", "ARR"} for token in value.split())
                assert len(value.split()) > 1
    assert differences  # the new rule did fire
    # ...and fired on every multi-component all-placeholder cell (3 placeholder spellings in the
    # vocabulary: TBA, ARR, tba), nowhere else.
    assert len(differences) == sum(3**length for length in range(2, 5))


def test_time_cell_shape_is_a_fixed_vocabulary_with_no_cell_text() -> None:
    assert time_cell_shape("TBA TBA") == "P P"
    assert time_cell_shape("TBA xyz") == "P ?"
    assert time_cell_shape("8:00am-9:00am xyz") == "R ?"
    assert time_cell_shape("13:99pm-1:00pm") == "R"
    assert time_cell_shape("8:00am") == "?"
    assert time_cell_shape("TBA " * 12).endswith("+")
    for value in ["Doe Jane TBA", "http://x.example/a?b=1"]:
        assert set(time_cell_shape(value)) <= set("P R?+ ")


def test_a_bad_integer_cell_names_its_field_with_a_fixed_shape() -> None:
    from easy_a.schedule.normalize import normalize_schedule_row

    base = _row()
    for raw_field, expected in [
        ("capacity_raw", "capacity"),
        ("enrollment_raw", "enrollment"),
        ("seats_remaining_raw", "seats_remaining"),
        ("wait_seats_available_raw", "wait_seats_available"),
    ]:
        bad = base.model_copy(update={raw_field: "twelve"})
        with pytest.raises(RowNormalizationError) as raised:
            normalize_schedule_row(bad)
        assert (raised.value.field, raised.value.shape) == (expected, "non_integer")
        failure = row_failure_from(raised.value, position=7, row=bad)
        assert (failure.position, failure.field, failure.shape) == (7, expected, "non_integer")
        assert "twelve" not in repr(failure)


def _row() -> ParsedScheduleRow:
    return ParsedScheduleRow(
        session="Full Term",
        college="AC",
        department="MTH",
        crn="1",
        subject="MAC",
        course_number="1105",
        section_number="001",
        section_type="Class Lecture",
        title="College Algebra",
        section_note=None,
        credits_raw="3",
        payment_raw=None,
        primary_status="A",
        secondary_status=None,
        seats_remaining_raw="1",
        wait_seats_available_raw="0",
        capacity_raw="10",
        enrollment_raw="9",
        days_raw="MW",
        time_raw="TBA TBA",
        building=None,
        room=None,
        instructor_raw="Staff",
        campus="Tampa",
        delivery_method="CL",
        fees_raw=None,
    )
