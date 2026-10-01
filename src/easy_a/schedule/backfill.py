"""One-off historical section backfill under PROJECT.md D-22(e).

Production holds no Section or SectionInstructor rows for the five grade terms, so the
instructor-course grade join can never match. This module turns one whole-term USF response per
historical term into Section and SectionInstructor rows, keeping only the rows that back a stored
grade row (D-06). It is not part of the Render worker, it never writes seat snapshots and it never
sets ``removed_at``, so historical rows cannot be marked removed by a live sweep (D-07).

The row selection is pure (``select_backfill_rows``); the database side reads in bulk and writes
in bulk. Nothing here imports the live sync's change-only or removal logic (D-05).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.instructors import is_usable_instructor
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term
from easy_a.schedule.ingest import _section_values
from easy_a.schedule.normalize import NormalizedSection

HISTORICAL_GRADE_TERMS: tuple[str, ...] = ("202408", "202501", "202505", "202508", "202601")
"""The five terms D-22(e) allows; nothing else can be backfilled, least of all the live term."""

BACKFILL_SOURCE = "usf_schedule_backfill"

CourseKey = tuple[str, str]
"""A course identity as (subject, number), both upper-cased."""


class BackfillGuardError(RuntimeError):
    """Raised before any write when the selected rows are unsafe to store."""


def backfill_ingest_source(term: str | int) -> str:
    """IngestRun.source for the backfill of one term (IngestRun has no term column)."""
    return f"{BACKFILL_SOURCE}:{normalize_banner_term_code(term)}"


@dataclass(frozen=True)
class GradeKeys:
    """Per term, CRN -> course keys of its grade rows (None: the grade row is unattributed)."""

    by_term: Mapping[str, Mapping[str, frozenset[CourseKey | None]]]

    def for_term(self, term: str) -> Mapping[str, frozenset[CourseKey | None]]:
        return self.by_term.get(term, {})

    def needed_course_keys(self) -> frozenset[CourseKey]:
        return frozenset(
            key
            for crns in self.by_term.values()
            for keys in crns.values()
            for key in keys
            if key is not None
        )


def load_grade_keys(session: Session, terms: Iterable[str]) -> GradeKeys:
    """Read the grade-row identity of every graded term+CRN with one query."""
    wanted = tuple(terms)
    collected: dict[str, dict[str, set[CourseKey | None]]] = {term: {} for term in wanted}
    if wanted:
        rows = session.execute(
            select(Term.banner_code, GradeDistribution.crn, Course.subject, Course.number)
            .select_from(GradeDistribution)
            .join(Term, GradeDistribution.term_id == Term.id)
            .outerjoin(Course, GradeDistribution.course_id == Course.id)
            .where(Term.banner_code.in_(wanted))
        ).all()
        for banner_code, crn, subject, number in rows:
            key: CourseKey | None = (
                (subject.strip().upper(), number.strip().upper()) if subject is not None else None
            )
            collected[banner_code].setdefault(str(crn).strip(), set()).add(key)
    return GradeKeys(
        by_term={
            term: {crn: frozenset(keys) for crn, keys in crns.items()}
            for term, crns in collected.items()
        }
    )


def resolve_course_ids(session: Session, keys: Iterable[CourseKey]) -> dict[CourseKey, int]:
    """Course id per key with the same rule as resolve_course_id: highest catalog edition."""
    wanted = set(keys)
    if not wanted:
        return {}
    subjects = sorted({subject for subject, _ in wanted})
    resolved: dict[CourseKey, int] = {}
    rows = session.execute(
        select(Course.subject, Course.number, Course.id)
        .where(Course.subject.in_(subjects))
        .order_by(Course.catalog_edition.desc(), Course.id.desc())
    ).all()
    for subject, number, course_id in rows:
        key = (subject.strip().upper(), number.strip().upper())
        if key in wanted:
            resolved.setdefault(key, course_id)
    return resolved


@dataclass(frozen=True)
class SelectedRow:
    row: NormalizedSection
    course_id: int


@dataclass(frozen=True)
class TermSelection:
    """What one fetched term contributes: the rows to write and a count for every other outcome."""

    term: str
    fetched_rows: int
    grade_crns: int
    rows: tuple[SelectedRow, ...]
    not_graded: int
    non_tampa: int
    grade_course_unattributed: int
    course_key_mismatch: int
    uncataloged: int
    unmatched_grade_crns: int
    staff_or_blank: int
    section_type_histogram: Mapping[str, int] = field(default_factory=dict)
    delivery_method_histogram: Mapping[str, int] = field(default_factory=dict)

    @property
    def to_write(self) -> int:
        return len(self.rows)

    @property
    def matched_grade_rows(self) -> int:
        """Fetched rows whose CRN has a grade row."""
        return self.fetched_rows - self.not_graded

    @property
    def skipped_graded_rows(self) -> int:
        return (
            self.non_tampa
            + self.grade_course_unattributed
            + self.course_key_mismatch
            + self.uncataloged
        )

    @property
    def unmatched_fraction(self) -> float:
        return self.unmatched_grade_crns / self.grade_crns if self.grade_crns else 0.0


def select_backfill_rows(
    term: str,
    rows: Sequence[NormalizedSection],
    grade_keys: Mapping[str, frozenset[CourseKey | None]],
    course_ids_by_key: Mapping[CourseKey, int],
) -> TermSelection:
    """Pure: keep the rows that back a stored grade row and count every other outcome (D-06)."""
    selected: list[SelectedRow] = []
    not_graded = non_tampa = unattributed = mismatch = uncataloged = 0
    for row in rows:
        keys = grade_keys.get(row.crn)
        if keys is None:
            not_graded += 1
        elif not same_campus(row.campus, SUPPORTED_CAMPUS):
            non_tampa += 1
        elif None in keys:
            unattributed += 1
        else:
            row_key = (row.subject.strip().upper(), row.course_number.strip().upper())
            if any(key != row_key for key in keys):
                mismatch += 1
            elif row_key not in course_ids_by_key:
                uncataloged += 1
            else:
                selected.append(SelectedRow(row=row, course_id=course_ids_by_key[row_key]))

    fetched_crns = {row.crn for row in rows}
    return TermSelection(
        term=term,
        fetched_rows=len(rows),
        grade_crns=len(grade_keys),
        rows=tuple(selected),
        not_graded=not_graded,
        non_tampa=non_tampa,
        grade_course_unattributed=unattributed,
        course_key_mismatch=mismatch,
        uncataloged=uncataloged,
        unmatched_grade_crns=sum(1 for crn in grade_keys if crn not in fetched_crns),
        staff_or_blank=sum(
            1 for item in selected if not is_usable_instructor(item.row.instructor_raw)
        ),
        section_type_histogram=dict(sorted(Counter(i.row.section_type for i in selected).items())),
        delivery_method_histogram=dict(
            sorted(Counter(str(i.row.delivery_method) for i in selected).items())
        ),
    )


@dataclass(frozen=True)
class WriteCounts:
    inserted: int
    updated: int
    unchanged: int
    instructor_rows_added: int


def write_term_backfill(
    session: Session,
    *,
    term_id: int,
    selection: TermSelection,
    observed_at: datetime,
) -> WriteCounts:
    """Insert the selected sections and one instructor row each. The caller owns the transaction."""
    if not selection.rows:
        return WriteCounts(inserted=0, updated=0, unchanged=0, instructor_rows_added=0)

    crns = [item.row.crn for item in selection.rows]
    existing_crns = set(
        session.scalars(
            select(Section.crn).where(Section.term_id == term_id, Section.crn.in_(crns))
        )
    )

    new_sections: list[tuple[Section, NormalizedSection]] = []
    for item in selection.rows:
        if item.row.crn in existing_crns:
            continue
        section = Section(
            term_id=term_id,
            course_id=item.course_id,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            removed_at=None,
            **_section_values(item.row),
        )
        session.add(section)
        new_sections.append((section, item.row))
    session.flush()
    for section, row in new_sections:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=row.instructor_raw,
                name_normalized=None,
                source=BACKFILL_SOURCE,
                observed_at=observed_at,
            )
        )
    session.flush()
    return WriteCounts(
        inserted=len(new_sections),
        updated=0,
        unchanged=len(selection.rows) - len(new_sections),
        instructor_rows_added=len(new_sections),
    )
