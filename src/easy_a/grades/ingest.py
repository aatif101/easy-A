from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.common.lookups import ensure_term
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
    inserted = 0
    updated = 0

    for record in records:
        existing = session.execute(
            select(GradeDistribution).where(
                GradeDistribution.term_id == term.id,
                GradeDistribution.crn == record.crn,
                GradeDistribution.source == source,
            )
        ).scalar_one_or_none()

        if existing is None:
            session.add(_new_grade_distribution(term, record, source, source_hash))
            inserted += 1
            continue

        if _grade_distribution_differs(existing, record, source_hash):
            _apply_grade_distribution(existing, record, source_hash)
            updated += 1

    session.flush()
    return inserted, updated


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _new_grade_distribution(
    term: Term,
    record: ParsedGradeDistribution,
    source: str,
    source_hash: str,
) -> GradeDistribution:
    distribution = GradeDistribution(
        term_id=term.id,
        crn=record.crn,
        course_id=None,
        section_number_raw=record.section_number_raw,
        section_suffix_raw=record.section_suffix_raw,
        campus_raw=record.campus_raw,
        source=source,
        source_hash=source_hash,
        total_grades=record.total_grades,
    )
    _apply_grade_distribution(distribution, record, source_hash)
    return distribution


def _apply_grade_distribution(
    distribution: GradeDistribution,
    record: ParsedGradeDistribution,
    source_hash: str,
) -> None:
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
    source_hash: str,
) -> bool:
    return (
        distribution.section_number_raw != record.section_number_raw
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
