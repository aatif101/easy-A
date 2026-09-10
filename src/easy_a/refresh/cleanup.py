"""Transactional correction of unsupported-campus beta target sections.

The cleanup only considers configured beta courses in one explicit term, treats blank
campus values as ambiguous, and deletes rows only by IDs captured during the reviewed
run. The caller owns the transaction so failed invariants roll everything back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Select, and_, delete, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

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
from easy_a.refresh.targets import CourseTarget

SUPPORTED_CAMPUS = "Tampa"


class CleanupError(ValueError):
    """Raised when the cleanup cannot prove that the requested change is safe."""


class SectionRef(BaseModel):
    """One selected or ambiguous section as it existed before cleanup."""

    section_id: int
    crn: str
    subject: str
    course_number: str
    section_number: str
    campus: str | None
    seat_snapshots: int
    instructor_observations: int
    syllabi: int
    grade_rows_same_term_crn: int

    model_config = ConfigDict(frozen=True)


class CampusCount(BaseModel):
    campus: str
    section_count: int

    model_config = ConfigDict(frozen=True)


class CourseCount(BaseModel):
    subject: str
    course_number: str
    sections: int
    tampa_sections: int
    other_campus_sections: int
    ambiguous_campus_sections: int

    model_config = ConfigDict(frozen=True)


class StoredCounts(BaseModel):
    """Audit counts for the selected term, configured targets, and preserved data."""

    term_sections: int
    target_sections: int
    tampa_target_sections: int
    other_campus_target_sections: int
    ambiguous_target_sections: int
    unrelated_term_sections: int
    historical_sections: int
    target_seat_snapshots: int
    target_instructor_observations: int
    target_syllabi: int
    grade_rows_term: int
    grade_rows_all_terms: int
    by_campus: tuple[CampusCount, ...]
    by_course: tuple[CourseCount, ...]

    model_config = ConfigDict(frozen=True)


class CleanupReport(BaseModel):
    term: str
    kept_campus: str
    targets: tuple[str, ...]
    criteria: str
    generated_at: datetime
    applied: bool
    apply_safe: bool
    before: StoredCounts
    after: StoredCounts | None
    matched: tuple[SectionRef, ...]
    ambiguous: tuple[SectionRef, ...]
    candidate_seat_snapshots: int
    candidate_instructor_observations: int
    candidate_syllabi: int
    candidate_grade_rows: int
    sections_removed: int
    seat_snapshots_removed: int
    instructor_observations_removed: int
    syllabi_removed: int
    grade_rows_removed: int
    tampa_sections_removed: int
    ambiguous_sections_removed: int
    historical_sections_removed: int
    unrelated_term_sections_removed: int

    model_config = ConfigDict(frozen=True)


@dataclass(frozen=True)
class _IdentitySnapshot:
    section_ids: frozenset[int]
    tampa_target_ids: frozenset[int]
    ambiguous_target_ids: frozenset[int]
    historical_section_ids: frozenset[int]
    unrelated_term_section_ids: frozenset[int]
    seat_snapshot_ids: frozenset[int]
    instructor_observation_ids: frozenset[int]
    syllabus_ids: frozenset[int]
    grade_row_ids: frozenset[int]


def _campus_kind(stored: str | None) -> str:
    if stored is None or not stored.strip():
        return "ambiguous"
    if stored.strip().casefold() == SUPPORTED_CAMPUS.casefold():
        return "tampa"
    return "other"


def _require_term(session: Session, term: str) -> Term:
    term_row = session.scalar(select(Term).where(Term.banner_code == term))
    if term_row is None:
        raise CleanupError(f"Term {term} is not present in the database.")
    return term_row


def _count(session: Session, statement: Select[tuple[int]]) -> int:
    return session.scalar(statement) or 0


def _target_filter(targets: tuple[CourseTarget, ...]) -> ColumnElement[bool]:
    if not targets:
        raise CleanupError("At least one configured course target is required.")
    return or_(
        *(and_(Course.subject == item.subject, Course.number == item.number) for item in targets)
    )


def _target_rows(
    session: Session,
    *,
    term_id: int,
    targets: tuple[CourseTarget, ...],
    lock: bool,
) -> list[tuple[Section, Course]]:
    statement = (
        select(Section, Course)
        .join(Course, Section.course_id == Course.id)
        .where(Section.term_id == term_id, _target_filter(targets))
        .order_by(Course.subject, Course.number, Section.crn, Section.id)
    )
    if lock:
        statement = statement.with_for_update(of=Section)
    return list(session.execute(statement).tuples())


def _section_ref(session: Session, section: Section, course: Course) -> SectionRef:
    return SectionRef(
        section_id=section.id,
        crn=section.crn,
        subject=course.subject,
        course_number=course.number,
        section_number=section.section_number,
        campus=section.campus,
        seat_snapshots=_count(
            session,
            select(func.count(SeatSnapshot.id)).where(SeatSnapshot.section_id == section.id),
        ),
        instructor_observations=_count(
            session,
            select(func.count(SectionInstructor.id)).where(
                SectionInstructor.section_id == section.id
            ),
        ),
        syllabi=_count(
            session, select(func.count(Syllabus.id)).where(Syllabus.section_id == section.id)
        ),
        grade_rows_same_term_crn=_count(
            session,
            select(func.count(GradeDistribution.id)).where(
                GradeDistribution.term_id == section.term_id,
                GradeDistribution.crn == section.crn,
            ),
        ),
    )


def _classified_refs(
    session: Session, rows: list[tuple[Section, Course]]
) -> tuple[tuple[SectionRef, ...], tuple[SectionRef, ...]]:
    matched: list[SectionRef] = []
    ambiguous: list[SectionRef] = []
    for section, course in rows:
        kind = _campus_kind(section.campus)
        if kind == "other":
            matched.append(_section_ref(session, section, course))
        elif kind == "ambiguous":
            ambiguous.append(_section_ref(session, section, course))
    return tuple(matched), tuple(ambiguous)


def stored_counts(
    session: Session,
    term: str,
    targets: tuple[CourseTarget, ...],
) -> StoredCounts:
    """Measure the exact cleanup scope and the data that must remain untouched."""
    term = normalize_banner_term_code(term)
    term_row = _require_term(session, term)
    rows = _target_rows(session, term_id=term_row.id, targets=targets, lock=False)
    target_ids = tuple(section.id for section, _ in rows)
    kinds = {section.id: _campus_kind(section.campus) for section, _ in rows}

    campus_totals: dict[str, int] = {}
    course_totals: dict[tuple[str, str], dict[str, int]] = {
        (target.subject, target.number): {
            "all": 0,
            "tampa": 0,
            "other": 0,
            "ambiguous": 0,
        }
        for target in targets
    }
    for section, course in rows:
        campus_label = section.campus if section.campus is not None else "<NULL>"
        campus_totals[campus_label] = campus_totals.get(campus_label, 0) + 1
        bucket = course_totals[(course.subject, course.number)]
        bucket["all"] += 1
        bucket[kinds[section.id]] += 1

    term_sections = _count(
        session, select(func.count(Section.id)).where(Section.term_id == term_row.id)
    )
    target_id_query = select(Section.id).where(Section.id.in_(target_ids))
    return StoredCounts(
        term_sections=term_sections,
        target_sections=len(rows),
        tampa_target_sections=sum(kind == "tampa" for kind in kinds.values()),
        other_campus_target_sections=sum(kind == "other" for kind in kinds.values()),
        ambiguous_target_sections=sum(kind == "ambiguous" for kind in kinds.values()),
        unrelated_term_sections=term_sections - len(rows),
        historical_sections=_count(
            session, select(func.count(Section.id)).where(Section.term_id != term_row.id)
        ),
        target_seat_snapshots=(
            _count(
                session,
                select(func.count(SeatSnapshot.id)).where(
                    SeatSnapshot.section_id.in_(target_id_query)
                ),
            )
            if target_ids
            else 0
        ),
        target_instructor_observations=(
            _count(
                session,
                select(func.count(SectionInstructor.id)).where(
                    SectionInstructor.section_id.in_(target_id_query)
                ),
            )
            if target_ids
            else 0
        ),
        target_syllabi=(
            _count(
                session,
                select(func.count(Syllabus.id)).where(Syllabus.section_id.in_(target_id_query)),
            )
            if target_ids
            else 0
        ),
        grade_rows_term=_count(
            session,
            select(func.count(GradeDistribution.id)).where(
                GradeDistribution.term_id == term_row.id
            ),
        ),
        grade_rows_all_terms=_count(session, select(func.count(GradeDistribution.id))),
        by_campus=tuple(
            CampusCount(campus=campus, section_count=count)
            for campus, count in sorted(campus_totals.items())
        ),
        by_course=tuple(
            CourseCount(
                subject=target.subject,
                course_number=target.number,
                sections=course_totals[(target.subject, target.number)]["all"],
                tampa_sections=course_totals[(target.subject, target.number)]["tampa"],
                other_campus_sections=course_totals[(target.subject, target.number)]["other"],
                ambiguous_campus_sections=course_totals[(target.subject, target.number)][
                    "ambiguous"
                ],
            )
            for target in targets
        ),
    )


def find_cleanup_sections(
    session: Session,
    term: str,
    targets: tuple[CourseTarget, ...],
) -> tuple[tuple[SectionRef, ...], tuple[SectionRef, ...]]:
    """Return eligible and ambiguous configured-target sections without writing."""
    term = normalize_banner_term_code(term)
    term_row = _require_term(session, term)
    rows = _target_rows(session, term_id=term_row.id, targets=targets, lock=False)
    return _classified_refs(session, rows)


def clean_other_campus_sections(
    session: Session,
    *,
    term: str,
    targets: tuple[CourseTarget, ...],
    apply: bool = False,
    expect_removed: int | None = None,
    as_of: datetime | None = None,
) -> CleanupReport:
    """Report or remove non-Tampa configured-target sections in one transaction."""
    term = normalize_banner_term_code(term)
    term_row = _require_term(session, term)
    if apply and expect_removed is None:
        raise CleanupError("--apply requires --expect-removed so the reviewed count is pinned.")

    rows = _target_rows(session, term_id=term_row.id, targets=targets, lock=apply)
    matched, ambiguous = _classified_refs(session, rows)
    before = stored_counts(session, term, targets)
    candidate_grade_rows = sum(ref.grade_rows_same_term_crn for ref in matched)

    if expect_removed is not None and len(matched) != expect_removed:
        raise CleanupError(
            f"Expected to remove {expect_removed} sections but matched {len(matched)}. "
            "Nothing was deleted; re-check the dry-run report."
        )
    if apply and candidate_grade_rows:
        crns = ", ".join(ref.crn for ref in matched if ref.grade_rows_same_term_crn)
        raise CleanupError(
            f"Refusing to delete: {candidate_grade_rows} grade row(s) share a candidate "
            f"term+CRN ({crns}). Nothing was deleted."
        )

    report = CleanupReport(
        term=term,
        kept_campus=SUPPORTED_CAMPUS,
        targets=tuple(f"{target.subject} {target.number}" for target in targets),
        criteria=(
            f"term {term}; configured beta targets only; nonblank campus not equal to "
            f"{SUPPORTED_CAMPUS!r} after trim/casefold; explicit captured section ids"
        ),
        generated_at=as_of or datetime.now(UTC),
        applied=apply,
        apply_safe=candidate_grade_rows == 0,
        before=before,
        after=None,
        matched=matched,
        ambiguous=ambiguous,
        candidate_seat_snapshots=sum(ref.seat_snapshots for ref in matched),
        candidate_instructor_observations=sum(
            ref.instructor_observations for ref in matched
        ),
        candidate_syllabi=sum(ref.syllabi for ref in matched),
        candidate_grade_rows=candidate_grade_rows,
        sections_removed=0,
        seat_snapshots_removed=0,
        instructor_observations_removed=0,
        syllabi_removed=0,
        grade_rows_removed=0,
        tampa_sections_removed=0,
        ambiguous_sections_removed=0,
        historical_sections_removed=0,
        unrelated_term_sections_removed=0,
    )
    if not apply:
        return report

    snapshot = _identity_snapshot(session, term_row.id, rows)
    candidate_ids = frozenset(ref.section_id for ref in matched)
    candidate_seat_ids = _dependent_ids(session, SeatSnapshot, candidate_ids)
    candidate_instructor_ids = _dependent_ids(session, SectionInstructor, candidate_ids)
    candidate_syllabus_ids = _dependent_ids(session, Syllabus, candidate_ids)

    _lock_candidate_dependencies(session, candidate_ids)
    _delete_ids(session, SeatSnapshot, candidate_seat_ids)
    _delete_ids(session, SectionInstructor, candidate_instructor_ids)
    _delete_ids(session, Syllabus, candidate_syllabus_ids)
    _delete_ids(session, Section, candidate_ids)
    session.flush()

    after_rows = _target_rows(session, term_id=term_row.id, targets=targets, lock=False)
    after_snapshot = _identity_snapshot(session, term_row.id, after_rows)
    _verify_identities(
        before=snapshot,
        after=after_snapshot,
        candidate_ids=candidate_ids,
        candidate_seat_ids=candidate_seat_ids,
        candidate_instructor_ids=candidate_instructor_ids,
        candidate_syllabus_ids=candidate_syllabus_ids,
    )
    after = stored_counts(session, term, targets)
    if after.other_campus_target_sections:
        raise CleanupError(
            f"{after.other_campus_target_sections} eligible other-campus target section(s) "
            "remain after cleanup. Rolled back."
        )

    return report.model_copy(
        update={
            "after": after,
            "sections_removed": len(candidate_ids),
            "seat_snapshots_removed": len(candidate_seat_ids),
            "instructor_observations_removed": len(candidate_instructor_ids),
            "syllabi_removed": len(candidate_syllabus_ids),
            "grade_rows_removed": len(snapshot.grade_row_ids - after_snapshot.grade_row_ids),
            "tampa_sections_removed": len(
                snapshot.tampa_target_ids - after_snapshot.tampa_target_ids
            ),
            "ambiguous_sections_removed": len(
                snapshot.ambiguous_target_ids - after_snapshot.ambiguous_target_ids
            ),
            "historical_sections_removed": len(
                snapshot.historical_section_ids - after_snapshot.historical_section_ids
            ),
            "unrelated_term_sections_removed": len(
                snapshot.unrelated_term_section_ids - after_snapshot.unrelated_term_section_ids
            ),
        }
    )


def _identity_snapshot(
    session: Session,
    term_id: int,
    target_rows: list[tuple[Section, Course]],
) -> _IdentitySnapshot:
    target_ids = frozenset(section.id for section, _ in target_rows)
    all_sections: dict[int, int] = dict(
        list(session.execute(select(Section.id, Section.term_id)).tuples())
    )
    current_ids = {
        section_id for section_id, row_term_id in all_sections.items() if row_term_id == term_id
    }
    return _IdentitySnapshot(
        section_ids=frozenset(all_sections),
        tampa_target_ids=frozenset(
            section.id for section, _ in target_rows if _campus_kind(section.campus) == "tampa"
        ),
        ambiguous_target_ids=frozenset(
            section.id
            for section, _ in target_rows
            if _campus_kind(section.campus) == "ambiguous"
        ),
        historical_section_ids=frozenset(all_sections) - frozenset(current_ids),
        unrelated_term_section_ids=frozenset(current_ids) - target_ids,
        seat_snapshot_ids=frozenset(session.scalars(select(SeatSnapshot.id))),
        instructor_observation_ids=frozenset(session.scalars(select(SectionInstructor.id))),
        syllabus_ids=frozenset(session.scalars(select(Syllabus.id))),
        grade_row_ids=frozenset(session.scalars(select(GradeDistribution.id))),
    )


def _dependent_ids(
    session: Session,
    model: type[SeatSnapshot] | type[SectionInstructor] | type[Syllabus],
    section_ids: frozenset[int],
) -> frozenset[int]:
    if not section_ids:
        return frozenset()
    return frozenset(
        session.scalars(select(model.id).where(model.section_id.in_(section_ids))).all()
    )


def _lock_candidate_dependencies(session: Session, section_ids: frozenset[int]) -> None:
    if not section_ids:
        return
    for model in (SeatSnapshot, SectionInstructor, Syllabus):
        session.scalars(
            select(model.id).where(model.section_id.in_(section_ids)).with_for_update()
        ).all()


def _delete_ids(session: Session, model: Any, ids: frozenset[int]) -> None:
    if ids:
        session.execute(
            delete(model).where(model.id.in_(ids)),
            execution_options={"synchronize_session": "fetch"},
        )


def _verify_identities(
    *,
    before: _IdentitySnapshot,
    after: _IdentitySnapshot,
    candidate_ids: frozenset[int],
    candidate_seat_ids: frozenset[int],
    candidate_instructor_ids: frozenset[int],
    candidate_syllabus_ids: frozenset[int],
) -> None:
    expected = {
        "section": before.section_ids - candidate_ids,
        "seat snapshot": before.seat_snapshot_ids - candidate_seat_ids,
        "instructor observation": before.instructor_observation_ids - candidate_instructor_ids,
        "syllabus": before.syllabus_ids - candidate_syllabus_ids,
        "grade row": before.grade_row_ids,
        "Tampa target section": before.tampa_target_ids,
        "ambiguous-campus target section": before.ambiguous_target_ids,
        "historical section": before.historical_section_ids,
        "unrelated current-term section": before.unrelated_term_section_ids,
    }
    actual = {
        "section": after.section_ids,
        "seat snapshot": after.seat_snapshot_ids,
        "instructor observation": after.instructor_observation_ids,
        "syllabus": after.syllabus_ids,
        "grade row": after.grade_row_ids,
        "Tampa target section": after.tampa_target_ids,
        "ambiguous-campus target section": after.ambiguous_target_ids,
        "historical section": after.historical_section_ids,
        "unrelated current-term section": after.unrelated_term_section_ids,
    }
    for label, expected_ids in expected.items():
        if actual[label] != expected_ids:
            removed = sorted(expected_ids - actual[label])
            added = sorted(actual[label] - expected_ids)
            raise CleanupError(
                f"Cleanup changed unexpected {label} identities "
                f"(missing={removed}, added={added}). Rolled back."
            )
