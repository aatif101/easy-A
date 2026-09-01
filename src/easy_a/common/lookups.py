from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.terms import parse_banner_term
from easy_a.models import Course, Term


class CoreDataLookupError(ValueError):
    """Raised when shared core data cannot satisfy a pipeline lookup."""


def ensure_term(session: Session, term_code: str | int) -> Term:
    term_info = parse_banner_term(term_code)
    existing = session.execute(
        select(Term).where(Term.banner_code == term_info.banner_code)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    term = Term(
        banner_code=term_info.banner_code,
        name=term_info.name,
        year=term_info.year,
        season=term_info.season.value,
    )
    session.add(term)
    session.flush()
    return term


def resolve_course_id(session: Session, subject: str, number: str) -> int:
    normalized_subject = subject.strip().upper()
    normalized_number = number.strip().upper()
    if not normalized_subject or not normalized_number:
        raise CoreDataLookupError("Course subject and number must be non-empty.")

    course_id = session.execute(
        select(Course.id)
        .where(Course.subject == normalized_subject, Course.number == normalized_number)
        .order_by(Course.catalog_edition.desc())
        .limit(1)
    ).scalar_one_or_none()
    if course_id is None:
        raise CoreDataLookupError(
            f"Course {normalized_subject} {normalized_number} is not present in the courses table."
        )
    return course_id
