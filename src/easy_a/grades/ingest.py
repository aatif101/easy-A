from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.lookups import CoreDataLookupError, ensure_term, resolve_course_id
from easy_a.common.terms import TermParseError
from easy_a.grades.parser import (
    GradeWorkbookSchemaError,
    GradeWorkbookValidationError,
    ParsedGradeDistribution,
    parse_grade_workbook,
)
from easy_a.models import GradeDistribution, IngestRun, Term

GRADE_DISTRIBUTION_SOURCE = "usf_infocenter_grade_distribution_xlsx"


@dataclass(frozen=True)
class GradeIngestResult:
    records_seen: int
    records_inserted: int
    records_updated: int
    ingest_run_id: int


class GradeCourseResolutionError(ValueError):
    """Raised when one or more parsed grade rows reference a course key that does not resolve
    to a canonical Course. Reports every unresolved (subject, course_number) key
    deterministically so the whole workbook fails atomically before any GradeDistribution
    mutation (D-04, D-06, D-07)."""

    def __init__(
        self,
        unresolved_keys: Sequence[tuple[str, str]],
        *,
        records_failed: int,
    ) -> None:
        self.unresolved_keys = tuple(unresolved_keys)
        self.records_failed = records_failed
        keys_text = ", ".join(f"{subject} {number}" for subject, number in self.unresolved_keys)
        super().__init__(
            f"Grade workbook references {len(self.unresolved_keys)} unresolved course(s): "
            f"{keys_text}."
        )


def ingest_grade_file(
    session: Session,
    term_code: str | int,
    file_path: str | Path,
    source: str = GRADE_DISTRIBUTION_SOURCE,
) -> GradeIngestResult:
    path = Path(file_path)
    run = IngestRun(
        source=source,
        status="running",
        records_seen=0,
        records_inserted=0,
        records_updated=0,
        records_failed=0,
    )
    session.add(run)
    session.flush()

    try:
        term = ensure_term(session, term_code)
        records = parse_grade_workbook(path)
        source_hash = hash_file(path)
        inserted, updated = upsert_grade_distributions(
            session=session,
            term=term,
            records=records,
            source=source,
            source_hash=source_hash,
        )
    except GradeWorkbookValidationError as exc:
        _mark_run_failed(
            run=run,
            message=str(exc),
            records_seen=exc.records_seen,
            records_failed=len(exc.errors),
        )
        session.flush()
        raise
    except GradeCourseResolutionError as exc:
        _mark_run_failed(
            run=run,
            message=str(exc),
            records_seen=len(records),
            records_failed=exc.records_failed,
        )
        session.flush()
        raise
    except (GradeWorkbookSchemaError, TermParseError) as exc:
        _mark_run_failed(run=run, message=str(exc), records_seen=0, records_failed=1)
        session.flush()
        raise

    run.status = "succeeded"
    run.finished_at = datetime.now(UTC)
    run.records_seen = len(records)
    run.records_inserted = inserted
    run.records_updated = updated
    session.flush()

    return GradeIngestResult(
        records_seen=len(records),
        records_inserted=inserted,
        records_updated=updated,
        ingest_run_id=run.id,
    )


def upsert_grade_distributions(
    session: Session,
    term: Term,
    records: list[ParsedGradeDistribution],
    source: str,
    source_hash: str,
) -> tuple[int, int]:
    course_ids_by_key = _resolve_grade_course_ids(session, records)

    inserted = 0
    updated = 0

    for record in records:
        course_id = course_ids_by_key[(record.subject, record.course_number)]
        existing = session.execute(
            select(GradeDistribution).where(
                GradeDistribution.term_id == term.id,
                GradeDistribution.crn == record.crn,
                GradeDistribution.source == source,
            )
        ).scalar_one_or_none()

        if existing is None:
            session.add(_new_grade_distribution(term, record, course_id, source, source_hash))
            inserted += 1
            continue

        if _grade_distribution_differs(existing, record, course_id, source_hash):
            _apply_grade_distribution(existing, record, course_id, source_hash)
            updated += 1

    session.flush()
    return inserted, updated


def _resolve_grade_course_ids(
    session: Session,
    records: list[ParsedGradeDistribution],
) -> dict[tuple[str, str], int]:
    """Resolve every distinct parsed (subject, course_number) key before any
    GradeDistribution mutation. Unresolved keys are collected and reported together
    so the whole workbook fails atomically (D-04, D-06, D-07)."""
    distinct_keys = sorted({(record.subject, record.course_number) for record in records})
    resolved: dict[tuple[str, str], int] = {}
    unresolved_keys: list[tuple[str, str]] = []
    for subject, course_number in distinct_keys:
        try:
            resolved[(subject, course_number)] = resolve_course_id(session, subject, course_number)
        except CoreDataLookupError:
            unresolved_keys.append((subject, course_number))

    if unresolved_keys:
        unresolved_key_set = set(unresolved_keys)
        records_failed = sum(
            1
            for record in records
            if (record.subject, record.course_number) in unresolved_key_set
        )
        raise GradeCourseResolutionError(unresolved_keys, records_failed=records_failed)

    return resolved


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_grade_distribution(
    term: Term,
    record: ParsedGradeDistribution,
    course_id: int,
    source: str,
    source_hash: str,
) -> GradeDistribution:
    distribution = GradeDistribution(
        term_id=term.id,
        crn=record.crn,
        course_id=course_id,
        section_number_raw=record.section_number_raw,
        section_suffix_raw=record.section_suffix_raw,
        campus_raw=record.campus_raw,
        source=source,
        source_hash=source_hash,
        total_grades=record.total_grades,
    )
    _apply_grade_distribution(distribution, record, course_id, source_hash)
    return distribution


def _apply_grade_distribution(
    distribution: GradeDistribution,
    record: ParsedGradeDistribution,
    course_id: int,
    source_hash: str,
) -> None:
    distribution.course_id = course_id
    distribution.section_number_raw = record.section_number_raw
    distribution.section_suffix_raw = record.section_suffix_raw
    distribution.campus_raw = record.campus_raw
    distribution.a_count = record.a_count
    distribution.b_count = record.b_count
    distribution.c_count = record.c_count
    distribution.d_count = record.d_count
    distribution.f_count = record.f_count
    distribution.i_count = record.i_count
    distribution.s_count = record.s_count
    distribution.u_count = record.u_count
    distribution.w_count = record.w_count
    distribution.other_count = record.other_count
    distribution.total_grades = record.total_grades
    distribution.source_hash = source_hash


def _grade_distribution_differs(
    distribution: GradeDistribution,
    record: ParsedGradeDistribution,
    course_id: int,
    source_hash: str,
) -> bool:
    return (
        distribution.course_id != course_id
        or distribution.section_number_raw != record.section_number_raw
        or distribution.section_suffix_raw != record.section_suffix_raw
        or distribution.campus_raw != record.campus_raw
        or distribution.a_count != record.a_count
        or distribution.b_count != record.b_count
        or distribution.c_count != record.c_count
        or distribution.d_count != record.d_count
        or distribution.f_count != record.f_count
        or distribution.i_count != record.i_count
        or distribution.s_count != record.s_count
        or distribution.u_count != record.u_count
        or distribution.w_count != record.w_count
        or distribution.other_count != record.other_count
        or distribution.total_grades != record.total_grades
        or distribution.source_hash != source_hash
    )


def _mark_run_failed(
    run: IngestRun,
    message: str,
    records_seen: int,
    records_failed: int,
) -> None:
    run.status = "failed"
    run.finished_at = datetime.now(UTC)
    run.records_seen = records_seen
    run.records_failed = records_failed
    run.error_message = message
