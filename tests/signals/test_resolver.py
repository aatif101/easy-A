from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from easy_a.models import Section, SectionInstructor, Syllabus
from easy_a.signals import SignalSourceKind, SignalType
from easy_a.signals.resolver import resolve_instructor, resolve_section_signals

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def _section(
    db_session: Session,
    *,
    section_id: int,
    term_id: int,
    crn: str,
    note: str | None = None,
    instructor: str = "Leslaw Skrzypek",
) -> Section:
    section = Section(
        id=section_id,
        term_id=term_id,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Open",
        section_note=note,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    db_session.add(section)
    db_session.flush()
    db_session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=instructor.lower(),
            source="schedule",
            observed_at=NOW,
        )
    )
    db_session.flush()
    return section


def _syllabus(
    db_session: Session,
    *,
    document_id: str,
    term_id: int,
    crn: str,
    text: str,
    instructor: str,
    section_id: int | None = None,
) -> Syllabus:
    syllabus = Syllabus(
        document_id=document_id,
        section_id=section_id,
        term_id=term_id,
        crn=crn,
        course_id=10,
        section_number="001",
        instructor_raw=instructor,
        title="College Algebra",
        view_url=f"https://example.test/{document_id}",
        fetched_at=NOW,
        content_html=f"<p>{text}</p>",
        content_text=text,
        content_hash=document_id.ljust(64, "0")[:64],
    )
    db_session.add(syllabus)
    db_session.flush()
    return syllabus


def _observe_instructor(
    db_session: Session,
    *,
    section_id: int,
    name: str,
    observed_at: datetime,
) -> None:
    db_session.add(
        SectionInstructor(
            section_id=section_id,
            name_raw=name,
            name_normalized=name.lower(),
            source="schedule",
            observed_at=observed_at,
        )
    )
    db_session.flush()


def test_current_syllabus_precedes_note_and_history(db_session: Session) -> None:
    section = _section(
        db_session,
        section_id=100,
        term_id=1,
        crn="19410",
        note="Attendance is not required.",
    )
    _syllabus(
        db_session,
        document_id="current",
        term_id=1,
        crn="19410",
        text="Attendance is required.",
        instructor="Leslaw Skrzypek",
        section_id=section.id,
    )
    _syllabus(
        db_session,
        document_id="old",
        term_id=2,
        crn="89033",
        text="No curve will be applied.",
        instructor="Leslaw Skrzypek",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19410")

    assert result.provenance is SignalSourceKind.current_term_syllabus
    assert result.historical is False
    assert [(signal.signal_type, signal.value) for signal in result.signals] == [
        (SignalType.attendance, "required")
    ]


def test_schedule_note_fallback(db_session: Session) -> None:
    _section(
        db_session,
        section_id=101,
        term_id=1,
        crn="19411",
        note="Quizzes and exams are in person in the SMART Lab.",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19411")

    assert result.provenance is SignalSourceKind.schedule_section_note
    assert result.historical is False
    assert result.signals


def test_historical_same_instructor_fallback(db_session: Session) -> None:
    _section(db_session, section_id=102, term_id=1, crn="19412")
    _syllabus(
        db_session,
        document_id="same-prof",
        term_id=2,
        crn="89034",
        text="Late work is not accepted.",
        instructor="Leslaw Skrzypek",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19412")

    assert result.provenance is SignalSourceKind.historical_same_instructor_course
    assert result.historical is True
    assert result.instructor_match_confidence == 1.0
    assert result.source_term == "202408"


def test_latest_named_instructor_replaces_stale_staff_observation(
    db_session: Session,
) -> None:
    section = _section(
        db_session,
        section_id=106,
        term_id=1,
        crn="19416",
        instructor="Staff",
    )
    _observe_instructor(
        db_session,
        section_id=section.id,
        name="Leslaw Skrzypek",
        observed_at=NOW + timedelta(days=1),
    )
    _syllabus(
        db_session,
        document_id="after-staff",
        term_id=2,
        crn="89037",
        text="Attendance is required.",
        instructor="Leslaw Skrzypek",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19416")

    assert result.provenance is SignalSourceKind.historical_same_instructor_course
    assert result.instructor_match_confidence == 1.0


def test_latest_instructor_replaces_different_stale_instructor(db_session: Session) -> None:
    section = _section(
        db_session,
        section_id=107,
        term_id=1,
        crn="19417",
        instructor="Instructor A",
    )
    _observe_instructor(
        db_session,
        section_id=section.id,
        name="Instructor B",
        observed_at=NOW + timedelta(days=1),
    )
    _syllabus(
        db_session,
        document_id="stale-a",
        term_id=2,
        crn="89038",
        text="Attendance is not required.",
        instructor="Instructor A",
    )
    _syllabus(
        db_session,
        document_id="latest-b",
        term_id=2,
        crn="89039",
        text="Attendance is required.",
        instructor="Instructor B",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19417")

    assert result.provenance is SignalSourceKind.historical_same_instructor_course
    assert result.signals[0].source_identifier == "syllabus:latest-b"


def test_conflicting_instructors_in_latest_state_remain_unresolved(
    db_session: Session,
) -> None:
    section = _section(
        db_session,
        section_id=108,
        term_id=1,
        crn="19418",
        instructor="Stale Instructor",
    )
    latest_at = NOW + timedelta(days=1)
    _observe_instructor(
        db_session,
        section_id=section.id,
        name="Instructor B",
        observed_at=latest_at,
    )
    _observe_instructor(
        db_session,
        section_id=section.id,
        name="Instructor C",
        observed_at=latest_at,
    )
    _syllabus(
        db_session,
        document_id="conflicting-latest",
        term_id=2,
        crn="89040",
        text="Attendance is required.",
        instructor="Instructor B",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19418")

    assert result.provenance is SignalSourceKind.historical_same_course
    assert result.instructor_match_confidence is None


def test_latest_staff_observation_does_not_match_named_history(db_session: Session) -> None:
    section = _section(
        db_session,
        section_id=109,
        term_id=1,
        crn="19419",
        instructor="Leslaw Skrzypek",
    )
    _observe_instructor(
        db_session,
        section_id=section.id,
        name="Staff",
        observed_at=NOW + timedelta(days=1),
    )
    _syllabus(
        db_session,
        document_id="named-before-staff",
        term_id=2,
        crn="89041",
        text="Attendance is required.",
        instructor="Leslaw Skrzypek",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19419")

    assert result.provenance is SignalSourceKind.historical_same_course
    assert result.instructor_match_confidence is None


def test_historical_same_course_fallback(db_session: Session) -> None:
    _section(
        db_session,
        section_id=103,
        term_id=1,
        crn="19413",
        instructor="Different Professor",
    )
    _syllabus(
        db_session,
        document_id="course-only",
        term_id=2,
        crn="89035",
        text="A grading curve will be applied.",
        instructor="Leslaw Skrzypek",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19413")

    assert result.provenance is SignalSourceKind.historical_same_course
    assert result.historical is True
    assert result.instructor_match_confidence is None


def test_staff_never_matches_history(db_session: Session) -> None:
    _section(
        db_session,
        section_id=104,
        term_id=1,
        crn="19414",
        instructor="Staff",
    )
    _syllabus(
        db_session,
        document_id="staff-history",
        term_id=2,
        crn="89036",
        text="Attendance is required.",
        instructor="Staff",
    )

    result = resolve_section_signals(db_session, term="202701", crn="19414")

    assert result.provenance is SignalSourceKind.historical_same_course
    assert result.instructor_match_confidence is None


def test_ambiguous_abbreviated_instructor_does_not_match() -> None:
    result = resolve_instructor("L. Skrzypek", ["Leslaw Skrzypek", "Laura Skrzypek"])

    assert result.name is None
    assert result.confidence is None


def test_unique_first_initial_and_surname_resolution() -> None:
    result = resolve_instructor("L. Skrzypek", ["Leslaw Skrzypek", "Irina Rothstein"])

    assert result.name == "Leslaw Skrzypek"
    assert result.confidence == 0.85


def test_unavailable_does_not_fabricate_unknown_signals(db_session: Session) -> None:
    _section(db_session, section_id=105, term_id=1, crn="19415")

    result = resolve_section_signals(db_session, term="202701", crn="19415")

    assert result.provenance is SignalSourceKind.unavailable
    assert result.signals == ()
    assert result.source_term is None
