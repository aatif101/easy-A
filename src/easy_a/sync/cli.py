"""Command line for the live schedule sync worker: ``python -m easy_a.sync``.

Modes (mutually exclusive): the always-on loop (default), ``--once`` (one sweep), ``--dry-run`` (one
read-only sweep) and ``--restore-crn`` (un-mark removed sections without any USF request).

Exit codes: 0 succeeded, dry run or clean stop; 1 failed sweep (or nothing restorable); 2 sweep
lock busy (argparse usage errors also use 2); 3 refused by the cadence floor; 4 startup check
failed.

The cadence floor is enforced from the database (the latest IngestRun start for the term, in any
status), so a restart or a manual run can never start a sweep sooner than the tier floor after the
last recorded one (PROJECT.md D-22(b)). No flag bypasses it.

This module must stay light: no pandas and nothing from ``easy_a.refresh``. It never logs a
connection URL.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.config import DatabaseConfigError
from easy_a.db import get_engine, get_session_factory
from easy_a.models import IngestRun
from easy_a.schedule.client import StaffScheduleClient
from easy_a.schema_guard import SchemaNotCurrentError, require_sync_schema
from easy_a.sync import sync_source
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import SweepOutcome, run_sweep, sanitize_error_detail
from easy_a.sync.windows import (
    RegistrationWindows,
    assert_timezone_available,
    get_registration_windows,
)

LOGGER_NAME = "easy_a.sync"
DEFAULT_MAX_MISSING_FRACTION = 0.10

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BUSY = 2
EXIT_REFUSED = 3
EXIT_STARTUP = 4

logger = logging.getLogger(LOGGER_NAME)

_CRN_RE = re.compile(r"\d{5}")
_URL_RE = re.compile(r"[a-z][a-z0-9+.-]*://\S*", re.I)

SessionFactory = sessionmaker[Session]
ClientFactory = Callable[[], StaffScheduleClient]
NowFn = Callable[[], datetime]


class _NoJitter:
    """A rng whose uniform(a, b) is always a: yields the pure tier floor from next_start."""

    def uniform(self, a: float, b: float) -> float:
        return a


class _JsonLineFormatter(logging.Formatter):
    """One JSON object per line: dict messages verbatim, anything else wrapped and scrubbed."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            payload: dict[str, Any] = record.msg
        else:
            payload = {
                "event": "log",
                "level": record.levelname.lower(),
                "logger": record.name,
                "message": sanitize_error_detail(record.getMessage()),
            }
        return _URL_RE.sub("[redacted-url]", json.dumps(payload, default=str, sort_keys=False))


# -- argument parsing ------------------------------------------------------------------------


def _term_arg(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _crn_arg(value: str) -> str:
    if not _CRN_RE.fullmatch(value.strip()):
        raise argparse.ArgumentTypeError(f"CRN must be exactly five digits, got {value!r}.")
    return value.strip()


def _fraction_arg(value: str) -> float:
    try:
        fraction = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a number: {value!r}") from exc
    if not 0.0 <= fraction <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return fraction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m easy_a.sync",
        description=(
            "Live USF schedule sync worker. With no mode flag it runs the always-on loop "
            "(one whole-term request per sweep on the tiered cadence). No option starts a sweep "
            "sooner than the cadence floor after the last recorded one."
        ),
    )
    parser.add_argument("--term", required=True, type=_term_arg, help="Banner term, e.g. 202701.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once", action="store_true", help="Run one sweep and exit (refused inside the floor)."
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Run one read-only sweep, log what a real sweep would do, write nothing.",
    )
    mode.add_argument(
        "--restore-crn",
        action="append",
        type=_crn_arg,
        metavar="CRN",
        help="Clear removed_at for this CRN and rebuild the ranking cache; repeatable. "
        "Makes no USF request.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default INFO).",
    )
    parser.add_argument(
        "--max-missing-fraction",
        type=_fraction_arg,
        default=None,
        metavar="FRACTION",
        help="Sanity-gate override for a legitimate mass removal (default "
        f"{DEFAULT_MAX_MISSING_FRACTION}); only with --once or --dry-run.",
    )
    return parser


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_missing_fraction is not None and not (args.once or args.dry_run):
        parser.error("--max-missing-fraction is only allowed with --once or --dry-run")
    return args


# -- outcome logging -------------------------------------------------------------------------


def peak_rss_mb() -> float:
    """Peak resident set size of this process in MiB (0.0 where ``resource`` is unavailable)."""
    try:
        import resource
    except ImportError:  # pragma: no cover - non-POSIX
        return 0.0
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return round(raw / divisor, 1)


def outcome_log_dict(
    outcome: SweepOutcome, *, next_start_at: datetime | None = None
) -> dict[str, Any]:
    """The single JSON line for a sweep. Typed fields only, so no connection URL can reach it."""
    counts = outcome.counts
    page = outcome.page or {}
    extra = outcome.extra
    return {
        "event": f"sweep_{outcome.status.value}",
        "term": outcome.term,
        "started_at": outcome.started_at.isoformat(),
        "duration_s": round((outcome.finished_at - outcome.started_at).total_seconds(), 3),
        "bytes": page.get("bytes"),
        "content_encoding": page.get("content_encoding"),
        "tail_error": outcome.tail_error,
        "scope": outcome.scope,
        "inserted": None if counts is None else counts.records_inserted,
        "updated": None if counts is None else counts.records_updated,
        "removed": extra.get("removed"),
        "restored": extra.get("restored"),
        "instructor_changes": extra.get("instructor_changes"),
        "seat_changes": extra.get("seat_changes"),
        "unapplied_course_keys": list(outcome.unknown_course_keys),
        "would_add": list(outcome.would_add),
        "gate_reasons": list(outcome.gate_reasons),
        "error_kind": outcome.error_kind,
        "error_detail": outcome.error_detail,
        "peak_rss_mb": peak_rss_mb(),
        "next_start_at": None if next_start_at is None else next_start_at.isoformat(),
    }


def log_outcome(outcome: SweepOutcome, *, next_start_at: datetime | None = None) -> None:
    logger.info(outcome_log_dict(outcome, next_start_at=next_start_at))


def earliest_next_start(
    windows: RegistrationWindows, last_start: datetime, *, failures: int = 0
) -> datetime:
    """Pure tier floor after ``last_start`` (no jitter), including the later-sweep rule."""
    return windows.next_start(last_start, last_start, rng=_NoJitter(), failures=failures)


_EXIT_BY_STATUS = {
    SweepStatus.succeeded: EXIT_OK,
    SweepStatus.dry_run: EXIT_OK,
    SweepStatus.failed: EXIT_FAILED,
    SweepStatus.busy: EXIT_BUSY,
}


# -- startup ---------------------------------------------------------------------------------


def _startup_failure(message: str) -> int:
    print(f"startup check failed: {sanitize_error_detail(message)}")
    return EXIT_STARTUP


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def latest_sweep_start(session_factory: SessionFactory, term: str) -> datetime | None:
    """Start of the latest recorded sweep for ``term`` in any status, normalized to UTC."""
    with session_factory() as session:
        latest = session.scalar(
            select(func.max(IngestRun.started_at)).where(IngestRun.source == sync_source(term))
        )
    return None if latest is None else _as_utc(latest)


def _configure_logging(level: str) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonLineFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level))
    logger.propagate = False
    return handler


def main(
    argv: list[str] | None = None,
    *,
    session_factory: SessionFactory | None = None,
    client_factory: ClientFactory | None = None,
    now_fn: NowFn | None = None,
    windows: RegistrationWindows | None = None,
) -> int:
    """Run the CLI and return the exit code. Keyword arguments exist for tests."""
    try:
        args = _parse(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_OK

    handler = _configure_logging(args.log_level)
    try:
        return _run(
            args,
            session_factory=session_factory,
            client_factory=client_factory,
            now_fn=now_fn or (lambda: datetime.now(UTC)),
            windows=windows,
        )
    finally:
        logger.removeHandler(handler)


def _run(
    args: argparse.Namespace,
    *,
    session_factory: SessionFactory | None,
    client_factory: ClientFactory | None,
    now_fn: NowFn,
    windows: RegistrationWindows | None,
) -> int:
    term: str = args.term

    # Startup checks: everything below runs before any USF request (RESEARCH Pitfalls 8 and 16).
    try:
        assert_timezone_available()
    except RuntimeError as exc:
        return _startup_failure(str(exc))
    try:
        active_windows = windows or get_registration_windows()
    except Exception as exc:
        return _startup_failure(
            f"registration windows could not be loaded ({type(exc).__name__}); "
            "check config/registration_windows.toml"
        )
    if active_windows.term != term:
        return _startup_failure(
            f"registration windows are for term {active_windows.term}, not {term}"
        )

    engine = None
    if session_factory is None:
        try:
            engine = get_engine()
            session_factory = get_session_factory(engine)
        except DatabaseConfigError as exc:
            return _startup_failure(str(exc))
        except Exception as exc:
            return _startup_failure(f"could not create the database engine ({type(exc).__name__})")
    try:
        bind = session_factory.kw.get("bind")
        try:
            if bind is not None:
                require_sync_schema(bind)
        except SchemaNotCurrentError as exc:
            return _startup_failure(str(exc))

        if args.once or args.dry_run:
            return _run_single_sweep(
                args,
                session_factory=session_factory,
                client_factory=client_factory,
                now_fn=now_fn,
                windows=active_windows,
            )
        print("loop and restore modes are not available yet", file=sys.stderr)
        return EXIT_FAILED
    finally:
        if engine is not None:
            engine.dispose()


def _run_single_sweep(
    args: argparse.Namespace,
    *,
    session_factory: SessionFactory,
    client_factory: ClientFactory | None,
    now_fn: NowFn,
    windows: RegistrationWindows,
) -> int:
    term: str = args.term
    last_start = latest_sweep_start(session_factory, term)
    if last_start is not None:
        earliest = earliest_next_start(windows, last_start)
        if now_fn() < earliest:
            print(f"refused: next sweep allowed at {earliest.isoformat()}")
            return EXIT_REFUSED

    max_missing = (
        DEFAULT_MAX_MISSING_FRACTION
        if args.max_missing_fraction is None
        else args.max_missing_fraction
    )
    client = (client_factory or StaffScheduleClient)()
    try:
        outcome = run_sweep(
            session_factory,
            term=term,
            client=client,
            now_fn=now_fn,
            dry_run=bool(args.dry_run),
            max_missing_fraction=max_missing,
        )
    finally:
        client.close()
    failures = 1 if outcome.status is SweepStatus.failed else 0
    log_outcome(
        outcome, next_start_at=earliest_next_start(windows, outcome.started_at, failures=failures)
    )
    return _EXIT_BY_STATUS[outcome.status]
