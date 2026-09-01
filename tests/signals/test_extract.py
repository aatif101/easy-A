from __future__ import annotations

from easy_a.signals import SignalSourceKind, SignalType, extract_signals


def _values(text: str, signal_type: SignalType) -> list[str]:
    return [
        signal.value
        for signal in extract_signals(
            text,
            source_kind=SignalSourceKind.current_term_syllabus,
            source_identifier="syllabus:test",
            source_term="202701",
        )
        if signal.signal_type is signal_type
    ]


def test_attendance_required() -> None:
    assert _values("Attendance is required for this course.", SignalType.attendance) == [
        "required"
    ]


def test_attendance_explicitly_not_required() -> None:
    assert _values("Attendance is not required for this course.", SignalType.attendance) == [
        "not_required"
    ]


def test_attendance_not_strictly_required_remains_unknown() -> None:
    assert _values(
        "Attendance is not strictly required.", SignalType.attendance
    ) == []


def test_attendance_not_generally_required_remains_unknown() -> None:
    assert _values(
        "Attendance is not generally required.", SignalType.attendance
    ) == []


def test_students_not_required_to_maintain_attendance_is_negated() -> None:
    assert _values(
        "Students are not required to maintain attendance.", SignalType.attendance
    ) == ["not_required"]


def test_adverb_between_not_and_required_cannot_create_required_attendance() -> None:
    assert _values(
        "Students are not generally required to maintain attendance.",
        SignalType.attendance,
    ) == []


def test_late_work_allowed() -> None:
    values = _values(
        "Late assignments are accepted with a 10% late penalty.", SignalType.late_work
    )
    assert values == ["allowed"]


def test_late_work_prohibited() -> None:
    assert _values("Late work is not accepted.", SignalType.late_work) == ["not_allowed"]


def test_exam_signal() -> None:
    assert _values("The final exam is cumulative.", SignalType.exams) == ["present"]


def test_online_exam() -> None:
    assert _values("The online exam will be completed in Canvas.", SignalType.exam_location) == [
        "online"
    ]


def test_in_person_exam() -> None:
    assert _values("All exams are administered in person.", SignalType.exam_location) == [
        "in_person"
    ]


def test_mixed_exam_location_is_not_silently_reduced() -> None:
    assert _values(
        "The midterm is an online exam, but the final exam is in person.",
        SignalType.exam_location,
    ) == ["mixed"]


def test_curve_present() -> None:
    assert _values("A grading curve will be applied to the final grades.", SignalType.curve) == [
        "present"
    ]


def test_explicit_no_curve() -> None:
    assert _values("No curve will be applied.", SignalType.curve) == ["not_present"]


def test_participation() -> None:
    values = _values(
        "Class participation counts for 10% of the grade.", SignalType.participation
    )
    assert values == ["required"]


def test_smart_lab_requirement() -> None:
    assert _values("Students must attend a weekly SMART Lab.", SignalType.lab) == ["required"]


def test_section_note_extracts_multiple_contextual_signals() -> None:
    note = (
        "This is a hybrid course. There will be NO in-person classes. Material will be "
        "delivered through Video Lectures posted on Canvas. Students must spend 2h per "
        "week in the SMART Lab working on assignments. Quizzes and Exams must be done "
        "in-person, in the SMART Lab."
    )
    signals = extract_signals(
        note,
        source_kind=SignalSourceKind.schedule_section_note,
        source_identifier="section:19410:note",
        source_term="202701",
    )
    values = {signal.signal_type: signal.value for signal in signals}

    assert values[SignalType.delivery_format] == "online"
    assert values[SignalType.lab] == "required"
    assert values[SignalType.quiz] == "present"
    assert values[SignalType.exams] == "present"
    assert values[SignalType.exam_location] == "in_person"
    assert all(signal.source_kind is SignalSourceKind.schedule_section_note for signal in signals)


def test_smart_lab_note_requires_attendance_without_keyword_only_guessing() -> None:
    note = (
        "This course has a lab component. Students are required to complete exams, "
        "quizzes, and weekly attendance in the SMART lab."
    )

    assert _values(note, SignalType.attendance) == ["required"]
    assert _values(note, SignalType.lab) == ["required"]


def test_evidence_is_present_and_short() -> None:
    signal = extract_signals(
        f"{'Background material. ' * 30}Attendance will be taken each class.",
        source_kind=SignalSourceKind.current_term_syllabus,
        source_identifier="syllabus:test",
        source_term="202701",
    )[0]

    assert signal.evidence_text
    assert len(signal.evidence_text) <= 240
    assert "Attendance will be taken" in signal.evidence_text


def test_unknown_remains_absent() -> None:
    assert extract_signals(
        "Welcome to College Algebra. Office hours are posted in Canvas.",
        source_kind=SignalSourceKind.current_term_syllabus,
        source_identifier="syllabus:test",
        source_term="202701",
    ) == ()
