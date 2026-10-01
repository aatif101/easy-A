"""One-off command line for the historical section backfill (PROJECT.md D-22(e)).

``uv run python scripts/backfill_historical_sections.py --terms 202408 --dry-run`` fetches each
requested grade term with exactly one whole-term StaffScheduleSearch request, keeps only the rows
that back a stored grade row and writes Section plus SectionInstructor rows. It is separate from the
Render worker and accepts only the five historical grade terms.

Exit codes: 0 success or dry run; 1 refused or failed with nothing written; 2 argparse usage error.

One request per term, never retried, and no URL (request or database) is ever printed: stdout is a
single JSON object of counts.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.lookups import ensure_term
from easy_a.config import DatabaseConfigError
from easy_a.db import get_engine, get_session_factory
from easy_a.models import IngestRun
from easy_a.schedule.backfill import (
    HISTORICAL_GRADE_TERMS,
    BackfillGuardError,
    TermSelection,
    WriteCounts,
    backfill_ingest_source,
    load_grade_keys,
    resolve_course_ids,
    select_backfill_rows,
    validate_selection,
    write_term_backfill,
)
from easy_a.schedule.client import StaffScheduleClient, WholeTermResponseError
from easy_a.schedule.parser import ScheduleParseError
from easy_a.sync.fetch import FetchedTerm, fetch_whole_term

EXIT_OK = 0
EXIT_FAILED = 1

DEFAULT_PAUSE_SECONDS = 30.0
MIN_PAUSE_SECONDS = 10.0
DEFAULT_MAX_UNMATCHED_FRACTION = 0.02

ERROR_DETAIL_LIMIT = 200
_URL_RE = re.compile(r"[a-z][a-z0-9+.-]*://\S*", re.I)

SessionFactory = sessionmaker[Session]
ClientFactory = Callable[[], StaffScheduleClient]
NowFn = Callable[[], datetime]
SleepFn = Callable[[float], None]


def _pause_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from exc
    if seconds < MIN_PAUSE_SECONDS:
        raise argparse.ArgumentTypeError(
            f"must be at least {MIN_PAUSE_SECONDS:g} seconds between whole-term requests"
        )
    return seconds


def _fraction(value: str) -> float:
    try:
        fraction = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number") from exc
    if not 0.0 <= fraction <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return fraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backfill_historical_sections",
        description=(
            "One-off backfill of Section and SectionInstructor rows for the five historical "
            "grade terms (one whole-term USF request per term, graded CRNs only)."
        ),
    )
    parser.add_argument(
        "--terms",
        nargs="+",
        choices=HISTORICAL_GRADE_TERMS,
        default=list(HISTORICAL_GRADE_TERMS),
        metavar="TERM",
        help="Historical grade terms to backfill (default: all of "
        + ", ".join(HISTORICAL_GRADE_TERMS)
        + ").",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Write inside one transaction that is always rolled back, then print counts.",
    )
    mode.add_argument("--apply", action="store_true", help="Write the rows and commit.")
    parser.add_argument(
        "--pause-seconds",
        type=_pause_seconds,
        default=DEFAULT_PAUSE_SECONDS,
        help="Pause between term requests (default 30, at least 10).",
    )
    parser.add_argument(
        "--max-unmatched-fraction",
        type=_fraction,
        default=DEFAULT_MAX_UNMATCHED_FRACTION,
        help="Stop when more than this fraction of a term's grade CRNs is missing from USF.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Also write the printed JSON object, indented, to this path.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    session_factory: SessionFactory | None = None,
    client_factory: ClientFactory | None = None,
    now_fn: NowFn | None = None,
    sleep: SleepFn = time.sleep,
) -> int:
    """Run the CLI and return the exit code. Keyword arguments exist for tests."""
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_OK

    clock = now_fn or (lambda: datetime.now(UTC))
    engine = None
    if session_factory is None:
        try:
            engine = get_engine()
            session_factory = get_session_factory(engine)
        except DatabaseConfigError:
            return _emit(args, {"status": "failed", "error_kind": "database_config"}, EXIT_FAILED)
    try:
        return _run(
            args,
            session_factory=session_factory,
            client_factory=client_factory,
            now_fn=clock,
            sleep=sleep,
        )
    finally:
        if engine is not None:
            engine.dispose()


def _scrub(text: str) -> str:
    """Strip anything URL-shaped and cap the length, so error text is safe to print."""
    return _URL_RE.sub("[redacted-url]", text)[:ERROR_DETAIL_LIMIT]


def _fetch_error_kind(exc: Exception) -> str | None:
    """A coarse, URL-free kind for a fetch or parse failure; None for anything unexpected."""
    if isinstance(exc, httpx.TimeoutException):
        return "usf_timeout"
    if isinstance(exc, httpx.HTTPStatusError | httpx.TransportError):
        return "usf_http"
    if isinstance(exc, WholeTermResponseError):
        return "usf_response"
    if isinstance(exc, ScheduleParseError):
        return "parse"
    return None


def _failure(kind: str, *, term: str | None = None, detail: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"status": "failed", "error_kind": kind, "written": False}
    if term is not None:
        report["failed_term"] = term
    if detail:
        report["error"] = _scrub(detail)
    return report


def _guard_failures(selection: TermSelection, max_unmatched_fraction: float) -> list[str]:
    failures: list[str] = []
    if selection.fetched_rows == 0:
        failures.append("zero_rows")
    if selection.unmatched_fraction > max_unmatched_fraction:
        failures.append("unmatched_fraction")
    try:
        validate_selection(selection)
    except BackfillGuardError:
        failures.append("duplicate_crn")
    return failures


def _run(
    args: argparse.Namespace,
    *,
    session_factory: SessionFactory,
    client_factory: ClientFactory | None,
    now_fn: NowFn,
    sleep: SleepFn,
) -> int:
    terms: list[str] = list(dict.fromkeys(args.terms))
    dry_run = bool(args.dry_run)
    run_started = now_fn()

    try:
        with session_factory() as session:
            grade_keys = load_grade_keys(session, terms)
            course_ids = resolve_course_ids(session, grade_keys.needed_course_keys())
    except SQLAlchemyError as exc:
        return _emit(args, _failure("database", detail=str(exc)), EXIT_FAILED)

    # No transaction is open while the slow, polite USF requests run. One request per term, never
    # retried, never narrowed: the first failure stops the run with nothing written (D-22 d/e).
    fetched: dict[str, FetchedTerm] = {}
    client = (client_factory or StaffScheduleClient)()
    try:
        for index, term in enumerate(terms):
            if index > 0:
                sleep(args.pause_seconds)
            try:
                fetched[term] = fetch_whole_term(client, term, now_fn=now_fn)
            except Exception as exc:
                kind = _fetch_error_kind(exc)
                if kind is None:
                    raise
                return _emit(args, _failure(kind, term=term, detail=str(exc)), EXIT_FAILED)
    finally:
        client.close()

    selections = {
        term: select_backfill_rows(
            term, fetched[term].parse.rows, dict(grade_keys.for_term(term)), course_ids
        )
        for term in terms
    }
    guards = {
        term: _guard_failures(selection, args.max_unmatched_fraction)
        for term, selection in selections.items()
    }
    guard_failed = any(guards.values())
    # Apply never writes past a failed guard. A dry run still shows the what-if counts, unless a
    # duplicate CRN makes the write itself unsafe.
    can_write = not any("duplicate_crn" in failures for failures in guards.values()) and (
        dry_run or not guard_failed
    )

    writes: dict[str, WriteCounts] = {}
    if can_write:
        session = session_factory()
        try:
            for term in terms:
                term_row = ensure_term(session, term)
                writes[term] = write_term_backfill(
                    session,
                    term_id=term_row.id,
                    selection=selections[term],
                    observed_at=fetched[term].fetched_at,
                )
                if not dry_run:
                    run = _ingest_run(term, selections[term], writes[term], run_started, now_fn())
                    session.add(run)
            if dry_run:
                session.rollback()
            else:
                session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            return _emit(args, _failure("database", detail=str(exc)), EXIT_FAILED)
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    report = _report(args, selections, writes, guards)
    return _emit(args, report, EXIT_FAILED if guard_failed else EXIT_OK)


def _ingest_run(
    term: str,
    selection: TermSelection,
    counts: WriteCounts,
    started_at: datetime,
    finished_at: datetime,
) -> IngestRun:
    return IngestRun(
        source=backfill_ingest_source(term),
        status="succeeded",
        started_at=started_at,
        finished_at=finished_at,
        records_seen=selection.matched_grade_rows,
        records_inserted=counts.inserted,
        records_updated=counts.updated,
        records_failed=selection.skipped_graded_rows,
    )


def _term_report(
    selection: TermSelection, counts: WriteCounts | None, guards: list[str]
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "fetched_rows": selection.fetched_rows,
        "grade_crns": selection.grade_crns,
        "not_graded": selection.not_graded,
        "non_tampa": selection.non_tampa,
        "grade_course_unattributed": selection.grade_course_unattributed,
        "course_key_mismatch": selection.course_key_mismatch,
        "uncataloged": selection.uncataloged,
        "to_write": selection.to_write,
        "unmatched_grade_crns": selection.unmatched_grade_crns,
        "unmatched_fraction": round(selection.unmatched_fraction, 6),
        "guard_failures": list(guards),
        "staff_or_blank": selection.staff_or_blank,
        "section_type_histogram": dict(selection.section_type_histogram),
        "delivery_method_histogram": dict(selection.delivery_method_histogram),
    }
    if counts is not None:
        report.update(
            inserted=counts.inserted,
            updated=counts.updated,
            unchanged=counts.unchanged,
            refreshed_last_seen=counts.refreshed_last_seen,
            instructor_rows_added=counts.instructor_rows_added,
            instructor_changes=counts.instructor_changes,
        )
    return report


def _report(
    args: argparse.Namespace,
    selections: dict[str, TermSelection],
    writes: dict[str, WriteCounts],
    guards: dict[str, list[str]],
) -> dict[str, Any]:
    failed = any(guards.values())
    report: dict[str, Any] = {
        "status": "failed" if failed else "succeeded",
        "written": bool(writes) and not args.dry_run,
        "terms": {
            term: _term_report(selection, writes.get(term), guards[term])
            for term, selection in selections.items()
        },
    }
    if failed:
        report["error_kind"] = "guard"
    return report


def _emit(args: argparse.Namespace, report: dict[str, Any], exit_code: int) -> int:
    full = {"mode": "dry_run" if args.dry_run else "apply", **report}
    # Defence in depth: nothing URL-shaped may reach stdout or the report file.
    line = _URL_RE.sub("[redacted-url]", json.dumps(full, sort_keys=True))
    print(line)
    if args.report_json is not None:
        pretty = _URL_RE.sub("[redacted-url]", json.dumps(full, indent=2, sort_keys=True))
        args.report_json.write_text(pretty + "\n")
    return exit_code

