from datetime import time

from easy_a.schedule.meetings import Meeting, parse_meetings


def _parse(**overrides: object) -> tuple[Meeting, ...]:
    values: dict[str, object] = {
        "days": None,
        "meeting_times": None,
        "start_time": None,
        "end_time": None,
        "building": None,
        "room": None,
    }
    return parse_meetings(**{**values, **overrides})  # type: ignore[arg-type]


def test_several_meetings_pair_days_times_and_rooms_in_order() -> None:
    lecture, recitation, exam = _parse(
        days="MW F S",
        meeting_times="09:30am-10:45am 11:00am-11:50am 07:30am-09:30am",
        building="CHE CHE EXAM",
        room="101A 303 F100",
    )

    assert (lecture.days, lecture.start_time, lecture.end_time) == ("MW", "09:30", "10:45")
    assert (recitation.days, recitation.building, recitation.room) == ("F", "CHE", "303")
    assert exam.is_exam and not lecture.is_exam
    assert (exam.days, exam.start_time) == ("S", "07:30")


def test_preliminary_exam_building_counts_as_an_exam() -> None:
    _, prelim, final = _parse(days="MW F F", building="ISA PRLD EXAM", room="1061 F100 F100")

    assert prelim.is_exam and final.is_exam


def test_mismatched_time_cell_leaves_times_unset_instead_of_guessing() -> None:
    meetings = _parse(days="MW F", meeting_times="09:30am-10:45am")

    assert [(m.days, m.start_time) for m in meetings] == [("MW", None), ("F", None)]


def test_mismatched_building_cell_never_marks_an_exam() -> None:
    meetings = _parse(days="TR F", building="TBA", room="TBA")

    assert [(m.building, m.is_exam) for m in meetings] == [(None, False), (None, False)]


def test_placeholder_time_stays_aligned_with_its_meeting() -> None:
    first, second = _parse(days="MW F", meeting_times="TBA 01:00pm-01:50pm")

    assert first.start_time is None
    assert (second.start_time, second.end_time) == ("13:00", "13:50")


def test_section_stored_before_meeting_times_uses_its_single_time_pair() -> None:
    (meeting,) = _parse(days="MW", start_time=time(19, 0), end_time=time(20, 45))

    assert (meeting.start_time, meeting.end_time) == ("19:00", "20:45")


def test_no_days_means_no_meetings() -> None:
    assert _parse(meeting_times="TBA") == ()
