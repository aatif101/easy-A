"""One sweep: fetch USF once, decide, and apply everything in a single transaction.

Order inside the transaction (PROJECT.md D-23, RESEARCH Pattern 1): the xact advisory lock, one
whole-term fetch, chunked parse, scope, sanity gate, three bulk reads, the pure diff, the apply and
the succeeded IngestRun, then commit. Any exception rolls every write back; a failed IngestRun is
recorded afterwards in a second short transaction so the evidence survives the rollback.

This module must stay light: no pandas, nothing from ``easy_a.refresh`` or ``easy_a.api``.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.lookups import ensure_term
from easy_a.models import Course, IngestRun
from easy_a.schedule.client import StaffScheduleClient, WholeTermResponseError
from easy_a.schedule.normalize import NormalizedSection
from easy_a.schedule.parser import ScheduleParseError
from easy_a.schema_guard import SchemaNotCurrentError
from easy_a.sync import SYNC_ERROR_KINDS, sync_source
from easy_a.sync.apply import apply_sweep_plan, load_db_state
from easy_a.sync.courses import (
    AutoAddResult,
    CourseAdderLike,
    CourseKey,
    default_course_adder,
    label,
)
from easy_a.sync.fetch import FetchedTerm, fetch_whole_term
from easy_a.sync.gate import GateInput, evaluate_gate, gate_thresholds
from easy_a.sync.lock import try_sweep_lock
from easy_a.sync.plan import (
    SweepCounts,
    SweepPlan,
    build_sweep_plan,
    describe_unknown_courses,
    missing_active_count,
    new_course_keys,
)
from easy_a.sync.runner import SweepStatus
from easy_a.sync.scope import SweepScopeError, apply_scope

logger = logging.getLogger(__name__)

ERROR_DETAIL_LIMIT = 500
UNAPPLIED_MESSAGE_LIMIT = 2000
_DB_URL_RE = re.compile(r"postgres(?:ql)?(?:\+\w+)?://\S*", re.I)


class SweepGateError(RuntimeError):
    """Raised when the sanity gate refuses a scoped response; carries the failed rules."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass(frozen=True)
class SweepOutcome:
    status: SweepStatus
    term: str
    started_at: datetime
    finished_at: datetime
    counts: SweepCounts | None = None
    scope: dict[str, Any] | None = None
    gate_reasons: tuple[str, ...] = ()
    unknown_course_keys: tuple[str, ...] = ()
    would_add: tuple[str, ...] = ()
    auto_added: tuple[str, ...] = ()
    unapplied: tuple[str, ...] = ()
    page: dict[str, Any] | None = None
    tail_error: bool = False
    error_kind: str | None = None
    error_detail: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_log_dict(self) -> dict[str, Any]:
        """One JSON-serializable summary for the CLI log line."""
        return {
            "status": self.status.value,
            "term": self.term,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "counts": None
            if self.counts is None
            else {
                "records_seen": self.counts.records_seen,
                "records_inserted": self.counts.records_inserted,
                "records_updated": self.counts.records_updated,
                "records_failed": self.counts.records_failed,
            },
            "scope": self.scope,
            "gate_reasons": list(self.gate_reasons),
            "unknown_course_keys": list(self.unknown_course_keys),
            "would_add": list(self.would_add),
            "auto_added": list(self.auto_added),
            "unapplied": list(self.unapplied),
            "page": self.page,
            "tail_error": self.tail_error,
            "error_kind": self.error_kind,
            "error_detail": self.error_detail,
        }


def sanitize_error_detail(detail: str) -> str:
    """Strip connection URLs and cap the length so error text is safe to store."""
    cleaned = _DB_URL_RE.sub("[redacted-url]", detail)
    return cleaned[:ERROR_DETAIL_LIMIT]


def classify_error(exc: BaseException) -> str:
    """Map an exception to a SYNC_ERROR_KINDS member."""
    if isinstance(exc, httpx.TimeoutException):
        kind = "usf_timeout"
    elif isinstance(exc, httpx.HTTPStatusError | httpx.TransportError):
        kind = "usf_http"
    elif isinstance(exc, WholeTermResponseError):
        kind = "usf_response"
    elif isinstance(exc, ScheduleParseError):
        kind = "parse"
    elif isinstance(exc, SweepScopeError):
        kind = "scope"
    elif isinstance(exc, SweepGateError):
        kind = "gate"
    elif isinstance(exc, SchemaNotCurrentError):
        kind = "schema"
    elif isinstance(exc, SQLAlchemyError):
        kind = "database"
    else:
        kind = "unexpected"
    assert kind in SYNC_ERROR_KINDS
    return kind


def _page_metadata(fetched: FetchedTerm) -> dict[str, Any]:
    return {
        "bytes": fetched.byte_count,
        "content_encoding": fetched.content_encoding,
        "elapsed_seconds": round(fetched.elapsed_seconds, 3),
    }


def _unapplied_reasons(plan: SweepPlan, reasons: dict[CourseKey, str]) -> tuple[str, ...]:
    """'SUBJ NNNN (reason)' for every course the plan could not apply, sorted by course."""
    return tuple(
        f"{label(key)} ({reasons.get(key, 'course not in Easy-A')})"
        for key in sorted(plan.unknown_course_keys)
    )


def _unapplied_message(unapplied: tuple[str, ...]) -> str | None:
    if not unapplied:
        return None
    message = "unapplied courses: " + "; ".join(unapplied)
    return _DB_URL_RE.sub("[redacted-url]", message)[:UNAPPLIED_MESSAGE_LIMIT]


def _resolve_added_course_ids(
    session: Session, added: tuple[CourseKey, ...]
) -> dict[CourseKey, int]:
    """Course id per added key, choosing the highest catalog edition (as load_db_state does)."""
    wanted = set(added)
    rows = session.execute(
        select(Course.subject, Course.number, Course.id)
        .where(Course.subject.in_(sorted({subject for subject, _ in wanted})))
        .order_by(Course.catalog_edition.desc(), Course.id.desc())
    ).all()
    resolved: dict[CourseKey, int] = {}
    for subject, number, course_id in rows:
        key = (subject, number)
        if key in wanted:
            resolved.setdefault(key, course_id)
    return resolved


def run_sweep(
    session_factory: sessionmaker[Session],
    *,
    term: str,
    client: StaffScheduleClient,
    now_fn: Callable[[], datetime],
    dry_run: bool = False,
    max_missing_fraction: float | None = None,
    course_adder: CourseAdderLike | None = None,
) -> SweepOutcome:
    """Run one sweep of ``term``. Exactly one USF request; one database transaction.

    ``max_missing_fraction`` is the operator's gate override; None means no override, which is the
    worker loop's path and leaves the gate at its default thresholds.
    """
    started_at = now_fn()
    progress: dict[str, Any] = {"records_seen": None}
    try:
        with session_factory.begin() as session:
            if dry_run and session.get_bind().dialect.name == "postgresql":
                session.execute(text("SET TRANSACTION READ ONLY"))
            if not try_sweep_lock(session):
                return SweepOutcome(
                    status=SweepStatus.busy,
                    term=term,
                    started_at=started_at,
                    finished_at=now_fn(),
                )
            outcome = _sweep_in_transaction(
                session,
                term=term,
                client=client,
                now_fn=now_fn,
                started_at=started_at,
                dry_run=dry_run,
                max_missing_fraction=max_missing_fraction,
                progress=progress,
                course_adder=course_adder,
            )
            if dry_run:
                session.rollback()
            return outcome
    except Exception as exc:
        return _record_failure(
            session_factory,
            exc,
            term=term,
            started_at=started_at,
            now_fn=now_fn,
            dry_run=dry_run,
            records_seen=progress["records_seen"],
        )


def _sweep_in_transaction(
    session: Session,
    *,
    term: str,
    client: StaffScheduleClient,
    now_fn: Callable[[], datetime],
    started_at: datetime,
    dry_run: bool,
    max_missing_fraction: float | None,
    progress: dict[str, Any],
    course_adder: CourseAdderLike | None = None,
) -> SweepOutcome:
    fetched = fetch_whole_term(client, term, now_fn=now_fn)
    rows: tuple[NormalizedSection, ...]
    rows, report = apply_scope(fetched.parse.rows)
    progress["records_seen"] = len(rows)
    term_row = ensure_term(session, term)
    state = load_db_state(session, term_row.id, rows, term_code=term_row.banner_code)

    missing = missing_active_count(rows, state)
    thresholds = gate_thresholds(max_missing_fraction)
    gate = evaluate_gate(
        GateInput(
            in_scope_rows=report.in_scope_rows,
            db_active_in_scope=state.active_in_scope_count,
            missing_active=missing,
            last_success_records_seen=state.last_success_records_seen,
            db_active_subjects=state.active_subjects,
            sweep_subjects=report.subjects,
        ),
        max_missing_fraction=thresholds.max_missing_fraction,
        min_row_ratio=thresholds.min_row_ratio,
        max_absent_subject_fraction=thresholds.max_absent_subject_fraction,
        min_absent_subjects=thresholds.min_absent_subjects,
    )
    if not gate.passed:
        raise SweepGateError(gate.reasons)

    add_result = AutoAddResult()
    if not dry_run:
        # D-05: bounded, paced catalog lookups for new in-scope courses; a dry run never fetches.
        new_keys = new_course_keys(rows, state)
        if new_keys:
            adder = course_adder if course_adder is not None else default_course_adder()
            add_result = adder.add_missing(session, new_keys)
            if add_result.added:
                added_ids = _resolve_added_course_ids(session, add_result.added)
                state = replace(state, course_ids={**state.course_ids, **added_ids})

    plan = build_sweep_plan(rows, state)
    counts = plan.counts()
    unapplied = _unapplied_reasons(plan, add_result.unapplied())
    unknown_labels = tuple(describe_unknown_courses(plan))
    common: dict[str, Any] = {
        "term": term,
        "started_at": started_at,
        "counts": counts,
        "scope": report.as_dict(),
        "page": _page_metadata(fetched),
        "tail_error": fetched.parse.tail_error,
        "auto_added": tuple(label(key) for key in sorted(add_result.added)),
        "extra": {
            "removed": len(plan.removals),
            "restored": len(plan.restores),
            "instructor_changes": len(plan.instructor_appends),
            "seat_changes": len(plan.snapshot_appends),
        },
    }

    if dry_run:
        return SweepOutcome(
            status=SweepStatus.dry_run,
            finished_at=now_fn(),
            would_add=unknown_labels,
            **common,
        )

    apply_sweep_plan(
        session,
        plan,
        term_id=term_row.id,
        term_code=term_row.banner_code,
        observed_at=fetched.fetched_at,
    )
    finished_at = now_fn()
    session.add(
        IngestRun(
            source=sync_source(term),
            status="succeeded",
            started_at=started_at,
            finished_at=finished_at,
            records_seen=counts.records_seen,
            records_inserted=counts.records_inserted,
            records_updated=counts.records_updated,
            records_failed=counts.records_failed,
            error_message=_unapplied_message(unapplied),
        )
    )
    session.flush()
    return SweepOutcome(
        status=SweepStatus.succeeded,
        finished_at=finished_at,
        unknown_course_keys=unknown_labels,
        unapplied=unapplied,
        **common,
    )


def _record_failure(
    session_factory: sessionmaker[Session],
    exc: Exception,
    *,
    term: str,
    started_at: datetime,
    now_fn: Callable[[], datetime],
    dry_run: bool,
    records_seen: int | None,
) -> SweepOutcome:
    kind = classify_error(exc)
    detail = sanitize_error_detail(str(exc) or type(exc).__name__)
    finished_at = now_fn()
    gate_reasons = exc.reasons if isinstance(exc, SweepGateError) else ()
    logger.warning("sweep failed: %s", f"{kind}: {detail}")
    if not dry_run:
        try:
            with session_factory.begin() as session:
                session.add(
                    IngestRun(
                        source=sync_source(term),
                        status="failed",
                        started_at=started_at,
                        finished_at=finished_at,
                        records_seen=records_seen or 0,
                        records_inserted=0,
                        records_updated=0,
                        records_failed=1,
                        error_message=f"{kind}: {detail}",
                    )
                )
        except Exception:
            logger.exception("could not record the failed IngestRun")
    return SweepOutcome(
        status=SweepStatus.failed,
        term=term,
        started_at=started_at,
        finished_at=finished_at,
        gate_reasons=gate_reasons,
        error_kind=kind,
        error_detail=detail,
    )
