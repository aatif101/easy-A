from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from easy_a.api.dependencies import DbSession
from easy_a.api.schemas import (
    DeliveryMethodMetadata,
    GenEdAttributeMetadata,
    SubjectMetadata,
    SyncStatusResponse,
    TermMetadata,
)
from easy_a.models import Course, CourseAttribute, IngestRun, Section, Term
from easy_a.refresh.coverage import TargetCoverage, coverage_metadata
from easy_a.refresh.targets import load_targets
from easy_a.schedule.freshness import as_utc
from easy_a.schedule.normalize import DELIVERY_METHOD_LABELS
from easy_a.sync import SYNC_ERROR_KINDS, sync_source
from easy_a.sync.windows import get_registration_windows

TERM_PATTERN = r"^\d{4}(01|05|08)$"
FAILURE_WINDOW = timedelta(hours=24)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.get("/terms", response_model=list[TermMetadata])
def list_terms(session: DbSession) -> list[TermMetadata]:
    terms = session.execute(select(Term).order_by(Term.banner_code.desc())).scalars().all()
    return [
        TermMetadata(
            term=term.banner_code,
            term_name=term.name,
            year=term.year,
            season=term.season,
        )
        for term in terms
    ]


@router.get("/subjects", response_model=list[SubjectMetadata])
def list_subjects(session: DbSession) -> list[SubjectMetadata]:
    subjects = session.execute(select(Course.subject).distinct().order_by(Course.subject)).scalars()
    return [SubjectMetadata(subject=subject) for subject in subjects]


@router.get("/gened-attributes", response_model=list[GenEdAttributeMetadata])
def list_gened_attributes(session: DbSession) -> list[GenEdAttributeMetadata]:
    rows = session.execute(
        select(CourseAttribute.attribute_code, CourseAttribute.attribute_label)
        .distinct()
        .order_by(CourseAttribute.attribute_code, CourseAttribute.attribute_label)
    )
    return [GenEdAttributeMetadata(code=code, label=label) for code, label in rows]


@router.get("/delivery-methods", response_model=list[DeliveryMethodMetadata])
def list_delivery_methods(session: DbSession) -> list[DeliveryMethodMetadata]:
    codes = session.execute(
        select(Section.delivery_method)
        .where(Section.delivery_method.is_not(None), Section.removed_at.is_(None))
        .distinct()
        .order_by(Section.delivery_method)
    ).scalars()
    return [
        DeliveryMethodMetadata(code=code, label=DELIVERY_METHOD_LABELS.get(code))
        for code in codes
        if code is not None
    ]


@router.get("/coverage", response_model=list[TargetCoverage])
def get_coverage(
    session: DbSession, term: str = Query(pattern=TERM_PATTERN)
) -> list[TargetCoverage]:
    return coverage_metadata(session, term, load_targets().targets)


def _now() -> datetime:
    """Module-level clock so tests can pin the instant."""
    return datetime.now(UTC)


def _error_kind(error_message: str | None) -> str:
    """Map a worker ``"kind: detail"`` message to the fixed vocabulary; never echo the detail."""
    if error_message:
        token = error_message.split(":", 1)[0].strip()
        if token in SYNC_ERROR_KINDS:
            return token
    return "unexpected"


@router.get("/sync-status", response_model=SyncStatusResponse)
def get_sync_status(
    session: DbSession, term: str = Query(pattern=TERM_PATTERN)
) -> SyncStatusResponse:
    source = sync_source(term)
    now = _now()

    last_success = session.execute(
        select(IngestRun)
        .where(
            IngestRun.source == source,
            IngestRun.status == "succeeded",
            IngestRun.finished_at.is_not(None),
        )
        .order_by(IngestRun.finished_at.desc(), IngestRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    last_run = session.execute(
        select(IngestRun)
        .where(IngestRun.source == source)
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    failures_last_24h = session.execute(
        select(func.count(IngestRun.id)).where(
            IngestRun.source == source,
            IngestRun.status == "failed",
            IngestRun.started_at >= now - FAILURE_WINDOW,
        )
    ).scalar_one()

    last_success_at = (
        as_utc(last_success.finished_at)
        if last_success is not None and last_success.finished_at is not None
        else None
    )
    windows = get_registration_windows()
    stale_after = windows.stale_after_seconds(last_success_at or now, now)
    is_stale = last_success_at is None or (now - last_success_at).total_seconds() > stale_after

    last_status: Literal["succeeded", "failed"] | None = None
    last_error_kind: str | None = None
    if last_run is not None and last_run.status in ("succeeded", "failed"):
        last_status = "succeeded" if last_run.status == "succeeded" else "failed"
        if last_status == "failed":
            last_error_kind = _error_kind(last_run.error_message)

    return SyncStatusResponse(
        term=term,
        last_success_at=last_success_at,
        last_run_at=as_utc(last_run.started_at) if last_run is not None else None,
        last_status=last_status,
        last_error_kind=last_error_kind,
        last_records_failed=last_run.records_failed if last_run is not None else None,
        failures_last_24h=int(failures_last_24h),
        in_registration_window=windows.contains(now),
        cadence_seconds=windows.interval_for(now),
        stale_after_seconds=stale_after,
        is_stale=is_stale,
        as_of=now,
    )
