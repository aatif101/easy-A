from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from easy_a.common.instructors import (
    CurrentInstructorStatus,
    get_current_instructor_state,
)
from easy_a.models import Section, SectionInstructor

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def test_blank_latest_instructor_state_does_not_fall_back_to_old_name(
    db_session: Session,
) -> None:
    section = _section(db_session, section_id=900)
    _observe(db_session, section_id=section.id, name="Instructor A", observed_at=NOW)
    _observe(db_session, section_id=section.id, name="  ", observed_at=NOW + timedelta(days=1))
    db_session.commit()

    state = get_current_instructor_state(db_session, section.id)

    assert state.name is None
    assert state.status is CurrentInstructorStatus.blank_latest_state
    assert state.latest_names == ()


def test_latest_staff_state_is_resolved_but_not_usable_for_scoring(
    db_session: Session,
) -> None:
    section = _section(db_session, section_id=901)
    _observe(db_session, section_id=section.id, name="Staff", observed_at=NOW)
    db_session.commit()

    state = get_current_instructor_state(db_session, section.id)

    assert state.name == "Staff"
    assert state.status is CurrentInstructorStatus.resolved
    assert state.is_usable_for_scoring is False


def test_ambiguous_latest_state_preserves_latest_names_without_choosing(
    db_session: Session,
) -> None:
    section = _section(db_session, section_id=902)
    latest_at = NOW + timedelta(days=1)
    _observe(db_session, section_id=section.id, name="Instructor B", observed_at=latest_at)
    _observe(db_session, section_id=section.id, name="Instructor C", observed_at=latest_at)
    db_session.commit()

    state = get_current_instructor_state(db_session, section.id)

    assert state.name is None
    assert state.status is CurrentInstructorStatus.ambiguous_latest_state
    assert state.latest_names == ("Instructor B", "Instructor C")


def _section(db_session: Session, *, section_id: int) -> Section:
    section = Section(
        id=section_id,
        term_id=1,
        crn=str(section_id),
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    db_session.add(section)
    db_session.flush()
    return section


def _observe(
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
            name_normalized=None,
            source="synthetic",
            observed_at=observed_at,
        )
    )
    db_session.flush()
