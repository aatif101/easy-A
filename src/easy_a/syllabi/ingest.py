from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from easy_a.models import Section, Syllabus
from easy_a.syllabi.parser import ParsedSyllabus, parse_syllabus_html


class SyllabusIngestError(ValueError):
    """Raised when syllabus metadata cannot be linked to core data."""


TERMS = table("terms", column("id"), column("banner_code"))
COURSES = table(
    "courses",
    column("id"),
    column("subject"),
    column("number"),
    column("catalog_edition"),
)


@dataclass(frozen=True)
class SyllabusIngestResult:
    syllabus_id: int
    inserted: bool
    content_changed: bool
    joined_to_section: bool


def ingest_syllabus_html(
    session: Session,
    html: str,
    *,
    document_id: str,
    fetched_at: datetime | None = None,
    view_url: str | None = None,
    organization: str | None = None,
    last_updated_at: datetime | None = None,
) -> SyllabusIngestResult:
    parsed = parse_syllabus_html(
        html,
        document_id=document_id,
        view_url=view_url,
        organization=organization,
        last_updated_at=last_updated_at,
    )
    captured_at = fetched_at or datetime.now(UTC)
    term_id = session.execute(
        select(TERMS.c.id).where(TERMS.c.banner_code == parsed.term_code)
    ).scalar_one_or_none()
    if term_id is None:
        raise SyllabusIngestError(f"Term {parsed.term_code} is not present in the terms table.")
    course_id = _resolve_course_id(session, parsed.subject, parsed.course_number)
    section = session.execute(
        select(Section).where(Section.term_id == int(term_id), Section.crn == parsed.crn)
    ).scalar_one_or_none()
    syllabus = session.execute(
        select(Syllabus).where(Syllabus.document_id == parsed.document_id)
    ).scalar_one_or_none()
    if syllabus is None:
        syllabus = Syllabus(
            term_id=int(term_id),
            course_id=course_id,
            section_id=section.id if section is not None else None,
            fetched_at=captured_at,
            **_syllabus_values(parsed),
        )
        session.add(syllabus)
        inserted = True
        content_changed = True
    else:
        inserted = False
        content_changed = syllabus.content_hash != parsed.content_hash
        syllabus.term_id = int(term_id)
        syllabus.course_id = course_id
        syllabus.section_id = section.id if section is not None else None
        syllabus.fetched_at = captured_at
        for field_name, value in _syllabus_values(parsed).items():
            setattr(syllabus, field_name, value)
    session.flush()
    return SyllabusIngestResult(
        syllabus_id=syllabus.id,
        inserted=inserted,
        content_changed=content_changed,
        joined_to_section=section is not None,
    )


def _resolve_course_id(session: Session, subject: str, number: str) -> int:
    course_id = session.execute(
        select(COURSES.c.id)
        .where(COURSES.c.subject == subject, COURSES.c.number == number)
        .order_by(COURSES.c.catalog_edition.desc())
        .limit(1)
    ).scalar_one_or_none()
    if course_id is None:
        raise SyllabusIngestError(f"Course {subject} {number} is not present in the courses table.")
    return int(course_id)


def _syllabus_values(parsed: ParsedSyllabus) -> dict[str, object]:
    return {
        "document_id": parsed.document_id,
        "crn": parsed.crn,
        "section_number": parsed.section_number,
        "instructor_raw": parsed.instructor_raw,
        "organization": parsed.organization,
        "title": parsed.title,
        "view_url": parsed.view_url,
        "print_url": parsed.print_url,
        "last_updated_at": parsed.last_updated_at,
        "content_html": parsed.content_html,
        "content_text": parsed.content_text,
        "content_hash": parsed.content_hash,
    }
