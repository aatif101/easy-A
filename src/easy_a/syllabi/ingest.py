from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.lookups import CoreDataLookupError, ensure_term, resolve_course_id
from easy_a.common.terms import TermParseError
from easy_a.models import Section, Syllabus
from easy_a.syllabi.parser import ParsedSyllabus, parse_syllabus_html


class SyllabusIngestError(ValueError):
    """Raised when syllabus metadata cannot be linked to core data."""


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
    try:
        term = ensure_term(session, parsed.term_code)
        course_id = resolve_course_id(session, parsed.subject, parsed.course_number)
    except (CoreDataLookupError, TermParseError) as exc:
        raise SyllabusIngestError(str(exc)) from exc

    section = session.execute(
        select(Section).where(Section.term_id == term.id, Section.crn == parsed.crn)
    ).scalar_one_or_none()
    syllabus = session.execute(
        select(Syllabus).where(Syllabus.document_id == parsed.document_id)
    ).scalar_one_or_none()
    if syllabus is None:
        syllabus = Syllabus(
            term_id=term.id,
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
        syllabus.term_id = term.id
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
