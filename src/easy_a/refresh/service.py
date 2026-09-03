from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.catalog.client import fetch_catalog_html
from easy_a.catalog.ingest import CatalogIngestResult, ingest_catalog_html
from easy_a.common.lookups import ensure_term
from easy_a.db import get_session_factory
from easy_a.grades.ingest import GradeIngestResult, ingest_grade_file
from easy_a.models import GradeDistribution, Section, Syllabus, Term
from easy_a.quality.checks import run_quality_checks
from easy_a.refresh.models import (
    CatalogInput,
    RefreshConfig,
    RefreshResult,
    ScheduleInput,
    SourceMode,
    SyllabusInput,
)
from easy_a.schedule.client import ScheduleSearchQuery, StaffScheduleClient
from easy_a.schedule.ingest import ScheduleIngestResult, ingest_schedule_html
from easy_a.syllabi.client import SimpleSyllabusClient
from easy_a.syllabi.ingest import SyllabusIngestResult, ingest_syllabus_html


class RefreshStageError(RuntimeError):
    """Raised when one independently committed refresh stage fails."""

    def __init__(self, stage: str, cause: Exception) -> None:
        self.stage = stage
        self.cause = cause
        super().__init__(f"{stage} stage failed: {cause}")


def refresh_data(
    config: RefreshConfig,
    *,
    session_factory: sessionmaker[Session] | None = None,
    observed_at: datetime | None = None,
    quality_as_of: datetime | None = None,
) -> RefreshResult:
    factory = session_factory or get_session_factory()
    captured_at = _as_utc(observed_at or datetime.now(UTC))

    _run_stage("term setup", lambda: _ensure_term(factory, config.term))
    catalog_input = config.catalog
    if catalog_input is not None:
        _run_stage("catalog", lambda: _refresh_catalog(factory, catalog_input))

    schedule_result: ScheduleIngestResult | None = None
    schedule_input = config.schedule
    if schedule_input is not None:
        schedule_result = _run_stage(
            "schedule",
            lambda: _refresh_schedule(
                factory,
                schedule_input,
                term=config.term,
                observed_at=captured_at,
            ),
        )

    grade_input = config.grades
    if grade_input is not None:
        _run_stage(
            "grades",
            lambda: _refresh_grades(factory, config.term, grade_input.file_path),
        )

    syllabus_input = config.syllabi
    if syllabus_input is not None:
        _run_stage(
            "syllabi",
            lambda: _refresh_syllabi(
                factory,
                syllabus_input,
                term=config.term,
                fetched_at=captured_at,
            ),
        )

    with factory() as session:
        term_row = session.scalar(select(Term).where(Term.banner_code == config.term))
        assert term_row is not None
        courses = session.scalar(
            select(func.count(distinct(Section.course_id))).where(
                Section.term_id == term_row.id
            )
        )
        sections = session.scalar(
            select(func.count()).select_from(Section).where(Section.term_id == term_row.id)
        )
        grade_rows = session.scalar(
            select(func.count())
            .select_from(GradeDistribution)
            .where(GradeDistribution.term_id == term_row.id)
        )
        syllabi = session.scalar(
            select(func.count()).select_from(Syllabus).where(Syllabus.term_id == term_row.id)
        )
        quality_report = run_quality_checks(
            session,
            config.term,
            stale_after=config.stale_after,
            as_of=quality_as_of,
        )

    return RefreshResult(
        term=config.term,
        courses=courses or 0,
        sections=sections or 0,
        instructor_observations_added=(
            schedule_result.instructor_observations_created
            if schedule_result is not None
            else 0
        ),
        seat_snapshots_added=(
            schedule_result.seat_snapshots_created if schedule_result is not None else 0
        ),
        grade_rows=grade_rows or 0,
        syllabi=syllabi or 0,
        quality_report=quality_report,
    )


def _ensure_term(factory: sessionmaker[Session], term: str) -> None:
    with factory.begin() as session:
        ensure_term(session, term)


def _refresh_catalog(
    factory: sessionmaker[Session],
    source: CatalogInput,
) -> CatalogIngestResult:
    if source.source is SourceMode.live:
        assert source.url is not None
        html = fetch_catalog_html(source.url)
    else:
        assert source.file_path is not None
        html = _read_html(source.file_path, "catalog")

    with factory.begin() as session:
        return ingest_catalog_html(session, html, source.catalog_edition)


def _refresh_schedule(
    factory: sessionmaker[Session],
    source: ScheduleInput,
    *,
    term: str,
    observed_at: datetime,
) -> ScheduleIngestResult:
    if source.source is SourceMode.live:
        query = ScheduleSearchQuery(
            term=term,
            campus=source.campus,
            subject=source.subject,
            course=source.course,
            crn=source.crn,
        )
        with StaffScheduleClient() as client:
            html = client.search(query)
    else:
        assert source.file_path is not None
        html = _read_html(source.file_path, "schedule")

    with factory.begin() as session:
        return ingest_schedule_html(session, html, term, observed_at=observed_at)


def _refresh_grades(
    factory: sessionmaker[Session],
    term: str,
    file_path: Path,
) -> GradeIngestResult:
    if not file_path.is_file():
        raise ValueError("Configured grade file is not a readable file.")
    with factory.begin() as session:
        return ingest_grade_file(session, term, file_path)


def _refresh_syllabi(
    factory: sessionmaker[Session],
    source: SyllabusInput,
    *,
    term: str,
    fetched_at: datetime,
) -> list[SyllabusIngestResult]:
    results: list[SyllabusIngestResult] = []
    if source.source is SourceMode.live:
        with SimpleSyllabusClient() as client:
            for document in source.documents:
                document_id, html = client.fetch_document_html(document)
                results.append(
                    _ingest_one_syllabus(
                        factory,
                        html,
                        document_id=document_id,
                        term=term,
                        fetched_at=fetched_at,
                    )
                )
        return results

    for syllabus_file in source.files:
        html = _read_html(syllabus_file.file_path, "syllabus")
        results.append(
            _ingest_one_syllabus(
                factory,
                html,
                document_id=syllabus_file.document_id,
                term=term,
                fetched_at=fetched_at,
            )
        )
    return results


def _ingest_one_syllabus(
    factory: sessionmaker[Session],
    html: str,
    *,
    document_id: str,
    term: str,
    fetched_at: datetime,
) -> SyllabusIngestResult:
    with factory.begin() as session:
        return ingest_syllabus_html(
            session,
            html,
            document_id=document_id,
            fetched_at=fetched_at,
            expected_term_code=term,
        )


def _read_html(path: Path, source_name: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Configured {source_name} HTML file could not be read.") from exc


def _run_stage[T](stage: str, operation: Callable[[], T]) -> T:
    try:
        return operation()
    except RefreshStageError:
        raise
    except Exception as exc:
        raise RefreshStageError(stage, exc) from exc


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
