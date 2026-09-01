from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.lookups import CoreDataLookupError, ensure_term, resolve_course_id
from easy_a.common.terms import TermParseError
from easy_a.models import SeatSnapshot, Section, SectionInstructor
from easy_a.schedule.normalize import NormalizedSection, normalize_schedule_row
from easy_a.schedule.parser import parse_schedule_html

SCHEDULE_SOURCE = "usf_staff_schedule"


class ScheduleIngestError(ValueError):
    """Raised when parsed schedule data cannot be linked to core data."""


@dataclass(frozen=True)
class ScheduleIngestResult:
    records_seen: int
    records_inserted: int
    records_updated: int
    seat_snapshots_created: int
    instructor_observations_created: int


def ingest_schedule_html(
    session: Session,
    html: str,
    term_code: str,
    *,
    observed_at: datetime | None = None,
    source: str = SCHEDULE_SOURCE,
) -> ScheduleIngestResult:
    captured_at = observed_at or datetime.now(UTC)
    rows = [normalize_schedule_row(row) for row in parse_schedule_html(html)]
    try:
        term = ensure_term(session, term_code)
    except TermParseError as exc:
        raise ScheduleIngestError(str(exc)) from exc

    inserted, updated = _upsert_sections(session, term.id, rows, captured_at, source)
    session.flush()
    return ScheduleIngestResult(
        records_seen=len(rows),
        records_inserted=inserted,
        records_updated=updated,
        seat_snapshots_created=len(rows),
        instructor_observations_created=len(rows),
    )


def _upsert_sections(
    session: Session,
    term_id: int,
    rows: list[NormalizedSection],
    observed_at: datetime,
    source: str,
) -> tuple[int, int]:
    inserted = 0
    updated = 0
    for row in rows:
        try:
            course_id = resolve_course_id(session, row.subject, row.course_number)
        except CoreDataLookupError as exc:
            raise ScheduleIngestError(str(exc)) from exc

        section = session.execute(
            select(Section).where(Section.term_id == term_id, Section.crn == row.crn)
        ).scalar_one_or_none()
        if section is None:
            section = Section(
                term_id=term_id,
                course_id=course_id,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                **_section_values(row),
            )
            session.add(section)
            session.flush()
            inserted += 1
        else:
            _update_section(section, row, course_id, observed_at)
            updated += 1

        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=row.instructor_raw,
                name_normalized=None,
                source=source,
                observed_at=observed_at,
            )
        )
        session.add(
            SeatSnapshot(
                section_id=section.id,
                observed_at=observed_at,
                capacity=row.capacity,
                enrollment=row.enrollment,
                seats_remaining=row.seats_remaining,
                wait_seats_available=row.wait_seats_available,
            )
        )
    session.flush()
    return inserted, updated


def _section_values(row: NormalizedSection) -> dict[str, object]:
    return {
        "crn": row.crn,
        "section_number": row.section_number,
        "campus": row.campus,
        "session": row.session,
        "section_type": row.section_type,
        "credits": row.credits,
        "primary_status": row.primary_status,
        "secondary_status": row.secondary_status,
        "delivery_method": row.delivery_method,
        "days": row.days,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "building": row.building,
        "room": row.room,
        "capacity": row.capacity,
        "enrollment": row.enrollment,
        "seats_remaining": row.seats_remaining,
        "wait_seats_available": row.wait_seats_available,
        "section_note": row.section_note,
        "fees_raw": row.fees_raw,
    }


def _update_section(
    section: Section,
    row: NormalizedSection,
    course_id: int,
    observed_at: datetime,
) -> None:
    section.course_id = course_id
    section.last_seen_at = observed_at
    for field_name, value in _section_values(row).items():
        setattr(section, field_name, value)
