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
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.lookups import ensure_term
from easy_a.config import DatabaseConfigError
from easy_a.db import get_engine, get_session_factory
from easy_a.models import IngestRun
from easy_a.schedule.backfill import (
    HISTORICAL_GRADE_TERMS,
    TermSelection,
    WriteCounts,
    backfill_ingest_source,
    load_grade_keys,
    resolve_course_ids,
    select_backfill_rows,
    write_term_backfill,
)
from easy_a.schedule.client import StaffScheduleClient
from easy_a.sync.fetch import FetchedTerm, fetch_whole_term

EXIT_OK = 0
EXIT_FAILED = 1

DEFAULT_PAUSE_SECONDS = 30.0
MIN_PAUSE_SECONDS = 10.0
DEFAULT_MAX_UNMATCHED_FRACTION = 0.02

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

    with session_factory() as session:
        grade_keys = load_grade_keys(session, terms)
        course_ids = resolve_course_ids(session, grade_keys.needed_course_keys())

    fetched: dict[str, FetchedTerm] = {}
    client = (client_factory or StaffScheduleClient)()
    try:
        for index, term in enumerate(terms):
            if index > 0:
                sleep(args.pause_seconds)
            fetched[term] = fetch_whole_term(client, term, now_fn=now_fn)
    finally:
        client.close()

    selections = {
        term: select_backfill_rows(
            term, fetched[term].parse.rows, dict(grade_keys.for_term(term)), course_ids
        )
        for term in terms
    }

    writes: dict[str, WriteCounts] = {}
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
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

    report = _report(args, selections, writes)
    return _emit(args, report, EXIT_OK)


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


def _term_report(selection: TermSelection, counts: WriteCounts | None) -> dict[str, Any]:
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
        "staff_or_blank": selection.staff_or_blank,
        "section_type_histogram": dict(selection.section_type_histogram),
        "delivery_method_histogram": dict(selection.delivery_method_histogram),
    }
    if counts is not None:
        report.update(
            inserted=counts.inserted,
            updated=counts.updated,
            unchanged=counts.unchanged,
            instructor_rows_added=counts.instructor_rows_added,
        )
    return report


def _report(
    args: argparse.Namespace,
    selections: dict[str, TermSelection],
    writes: dict[str, WriteCounts],
) -> dict[str, Any]:
    return {
        "mode": "dry_run" if args.dry_run else "apply",
        "status": "succeeded",
        "terms": {
            term: _term_report(selection, writes.get(term))
            for term, selection in selections.items()
        },
    }


def _emit(args: argparse.Namespace, report: dict[str, Any], exit_code: int) -> int:
    full = {"mode": "dry_run" if args.dry_run else "apply", **report}
    print(json.dumps(full, sort_keys=True))
    if args.report_json is not None:
        args.report_json.write_text(json.dumps(full, indent=2, sort_keys=True) + "\n")
    return exit_code

