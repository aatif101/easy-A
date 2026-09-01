from __future__ import annotations

from datetime import time
from pathlib import Path

from easy_a.schedule.normalize import normalize_schedule_row
from easy_a.schedule.parser import parse_schedule_html

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_current_schedule_preserves_status_instructor_notes_and_negative_seats() -> None:
    rows = parse_schedule_html((FIXTURES / "schedule_current.html").read_text(encoding="utf-8"))
    sections = [normalize_schedule_row(row) for row in rows]

    assert len(sections) == 2
    assert sections[0].primary_status == "Open"
    assert sections[0].secondary_status == "A"
    assert sections[0].instructor_raw == "Staff"
    assert sections[0].section_note == (
        "This course has a lab component. Students must attend the SMART Lab."
    )
    assert sections[0].start_time == time(11, 0)
    assert sections[0].end_time == time(12, 15)
    assert sections[1].primary_status == "Open"
    assert sections[1].secondary_status == "H"
    assert sections[1].seats_remaining == -17
    assert sections[1].capacity == 190
    assert sections[1].enrollment == 207
    assert sections[1].delivery_method == "HB"


def test_multiple_source_meeting_times_do_not_invent_a_single_time_pair() -> None:
    row = parse_schedule_html((FIXTURES / "schedule_current.html").read_text(encoding="utf-8"))[
        0
    ].model_copy(update={"time_raw": "09:30am-11:05am 11:30am-01:30pm 09:30am-11:30am"})

    section = normalize_schedule_row(row)

    assert section.start_time is None
    assert section.end_time is None
