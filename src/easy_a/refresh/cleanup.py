"""Targeted removal of stored sections that fall outside the supported campus.

The configured coverage refresh pins ``campus="T"`` and rejects non-Tampa rows before
ingestion, but an earlier expansion pass ran before that fix and left other-campus
sections stored. Nothing else in the pipeline deletes sections, so removing them needs
its own reviewable step.

Deletion is by explicit primary key, never by a broad ``WHERE`` clause, and every run
verifies afterwards that the grade rows and kept-campus sections survived intact. The
caller owns the transaction and must roll it back if this raises.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
    Term,
)

TAMPA_CAMPUS = "Tampa"


class CleanupError(ValueError):
    """Raised when a section cleanup cannot be performed safely."""


class SectionRef(BaseModel):
    """One stored section selected for removal, recorded before it is deleted."""

    section_id: int
    crn: str
    subject: str
    course_number: str
    section_number: str
    campus: str
    seat_snapshots: int
    instructor_observations: int
    grade_rows_same_term_crn: int

    model_config = ConfigDict(frozen=True)


class CampusCount(BaseModel):
    campus: str
    section_count: int

    model_config = ConfigDict(frozen=True)


class StoredCounts(BaseModel):
    """Measured stored counts for one term, plus repository-wide grade totals."""

    sections: int
    kept_campus_sections: int
    other_campus_sections: int
    seat_snapshots: int
    instructor_observations: int
    syllabi: int
    grade_rows_term: int
    grade_rows_all_terms: int
    by_campus: tuple[CampusCount, ...]

    model_config = ConfigDict(frozen=True)


class CleanupReport(BaseModel):
    term: str
    kept_campus: str
    criteria: str
    generated_at: datetime
    applied: bool
    before: StoredCounts
    after: StoredCounts | None
    matched: tuple[SectionRef, ...]
    sections_removed: int
    seat_snapshots_removed: int
    instructor_observations_removed: int
    grade_rows_removed: int
    kept_campus_sections_removed: int

    model_config = ConfigDict(frozen=True)


def same_campus(stored: str, expected: str) -> bool:
    """Compare campus labels the way the schedule pipeline stores them."""
    return stored.strip().casefold() == expected.strip().casefold()


def _require_term(session: Session, term: str) -> Term:
    term_row = session.scalar(select(Term).where(Term.banner_code == term))
    if term_row is None:
        raise CleanupError(f"Term {term} is not present in the database.")
    return term_row


def _count(session: Session, statement: Select[tuple[int]]) -> int:
    return session.scalar(statement) or 0


def stored_counts(session: Session, term: str, kept_campus: str = TAMPA_CAMPUS) -> StoredCounts:
    """Measure stored counts for ``term`` without changing anything."""
    term = normalize_banner_term_code(term)
    term_row = _require_term(session, term)
    section_ids = select(Section.id).where(Section.term_id == term_row.id)
    rows = session.execute(
        select(Section.campus, func.count(Section.id))
        .where(Section.term_id == term_row.id)
        .group_by(Section.campus)
        .order_by(Section.campus)
    ).all()
    kept = sum(count for campus, count in rows if same_campus(campus, kept_campus))
    total = sum(count for _, count in rows)
    return StoredCounts(
        sections=total,
        kept_campus_sections=kept,
        other_campus_sections=total - kept,
        seat_snapshots=_count(
            session,
            select(func.count(SeatSnapshot.id)).where(SeatSnapshot.section_id.in_(section_ids)),
        ),
        instructor_observations=_count(
            session,
            select(func.count(SectionInstructor.id)).where(
                SectionInstructor.section_id.in_(section_ids)
            ),
        ),
        syllabi=_count(
            session, select(func.count(Syllabus.id)).where(Syllabus.section_id.in_(section_ids))
        ),
        grade_rows_term=_count(
            session,
            select(func.count(GradeDistribution.id)).where(
                GradeDistribution.term_id == term_row.id
            ),
        ),
        grade_rows_all_terms=_count(session, select(func.count(GradeDistribution.id))),
        by_campus=tuple(
            CampusCount(campus=campus, section_count=count) for campus, count in rows
        ),
    )


def find_other_campus_sections(
    session: Session, term: str, kept_campus: str = TAMPA_CAMPUS
) -> tuple[SectionRef, ...]:
    """List the stored sections in ``term`` whose campus is not ``kept_campus``."""
    term = normalize_banner_term_code(term)
    term_row = _require_term(session, term)
    rows = session.execute(
        select(Section, Course)
        .join(Course, Section.course_id == Course.id)
        .where(Section.term_id == term_row.id)
        .order_by(Section.campus, Course.subject, Course.number, Section.crn)
    ).all()
    refs = []
    for section, course in rows:
        if same_campus(section.campus, kept_campus):
            continue
        refs.append(
            SectionRef(
                section_id=section.id,
                crn=section.crn,
                subject=course.subject,
                course_number=course.number,
                section_number=section.section_number,
                campus=section.campus,
                seat_snapshots=_count(
                    session,
                    select(func.count(SeatSnapshot.id)).where(
                        SeatSnapshot.section_id == section.id
                    ),
                ),
                instructor_observations=_count(
                    session,
                    select(func.count(SectionInstructor.id)).where(
                        SectionInstructor.section_id == section.id
                    ),
                ),
                grade_rows_same_term_crn=_count(
                    session,
                    select(func.count(GradeDistribution.id)).where(
                        GradeDistribution.term_id == term_row.id,
                        GradeDistribution.crn == section.crn,
                    ),
                ),
            )
        )
    return tuple(refs)


def clean_other_campus_sections(
    session: Session,
    *,
    term: str,
    kept_campus: str = TAMPA_CAMPUS,
    apply: bool = False,
    expect_removed: int | None = None,
    as_of: datetime | None = None,
) -> CleanupReport:
    """Remove stored sections in ``term`` whose campus is not ``kept_campus``.

    Dry run by default: with ``apply=False`` nothing is deleted and ``after`` is ``None``.
    Raises :class:`CleanupError` — leaving the caller's transaction to roll back — when the
    matched count contradicts ``expect_removed``, when a matched section has a stored
    syllabus, or when the post-deletion verification finds a lost grade row or a lost
    kept-campus section.
    """
    term = normalize_banner_term_code(term)
    kept_campus = kept_campus.strip()
    if not kept_campus:
        raise CleanupError("A campus to keep is required.")
    _require_term(session, term)

    before = stored_counts(session, term, kept_campus)
    matched = find_other_campus_sections(session, term, kept_campus)

    if expect_removed is not None and len(matched) != expect_removed:
        raise CleanupError(
            f"Expected to remove {expect_removed} sections but matched {len(matched)}. "
            "Nothing was deleted; re-check the term and campus before applying."
        )
    with_syllabi = [ref for ref in matched if _has_syllabus(session, ref.section_id)]
    if with_syllabi:
        crns = ", ".join(ref.crn for ref in with_syllabi)
        raise CleanupError(
            f"Refusing to delete sections with stored syllabi (CRN {crns}). "
            "Removing them needs a separate reviewed decision about the syllabus rows."
        )

    report = CleanupReport(
        term=term,
        kept_campus=kept_campus,
        criteria=(
            f"sections in term {term} whose stored campus is not {kept_campus!r} "
            "(compared case-insensitively after stripping), deleted by explicit section id"
        ),
        generated_at=as_of or datetime.now(UTC),
        applied=apply,
        before=before,
        after=None,
        matched=matched,
        sections_removed=0,
        seat_snapshots_removed=0,
        instructor_observations_removed=0,
        grade_rows_removed=0,
        kept_campus_sections_removed=0,
    )
    if not apply or not matched:
        return report

    for ref in matched:
        section = session.get(Section, ref.section_id)
        if section is None:
            raise CleanupError(f"Section id {ref.section_id} disappeared mid-cleanup.")
        session.delete(section)
    session.flush()

    after = stored_counts(session, term, kept_campus)
    _verify(before, after, len(matched))
    return report.model_copy(
        update={
            "after": after,
            "sections_removed": before.sections - after.sections,
            "seat_snapshots_removed": before.seat_snapshots - after.seat_snapshots,
            "instructor_observations_removed": (
                before.instructor_observations - after.instructor_observations
            ),
            "grade_rows_removed": before.grade_rows_all_terms - after.grade_rows_all_terms,
            "kept_campus_sections_removed": (
                before.kept_campus_sections - after.kept_campus_sections
            ),
        }
    )


def _has_syllabus(session: Session, section_id: int) -> bool:
    return (
        session.scalar(select(Syllabus.id).where(Syllabus.section_id == section_id).limit(1))
        is not None
    )


def _verify(before: StoredCounts, after: StoredCounts, matched: int) -> None:
    if after.grade_rows_all_terms != before.grade_rows_all_terms:
        raise CleanupError(
            f"Cleanup would change stored grade rows "
            f"({before.grade_rows_all_terms} -> {after.grade_rows_all_terms}). Rolled back."
        )
    if after.kept_campus_sections != before.kept_campus_sections:
        lost = before.kept_campus_sections - after.kept_campus_sections
        raise CleanupError(f"Cleanup would remove {lost} kept-campus sections. Rolled back.")
    removed = before.sections - after.sections
    if removed != matched:
        raise CleanupError(
            f"Cleanup removed {removed} sections but matched {matched}. Rolled back."
        )
    if after.other_campus_sections:
        raise CleanupError(
            f"{after.other_campus_sections} other-campus sections remain after cleanup. "
            "Rolled back."
        )
