"""One-off command line for the historical section backfill (PROJECT.md D-22(e)).

``uv run python scripts/backfill_historical_sections.py --terms 202408 --dry-run`` fetches each
requested grade term with exactly one whole-term StaffScheduleSearch request, keeps only the rows
that back a stored grade row and writes Section plus SectionInstructor rows. It is separate from the
Render worker and accepts only the five historical grade terms.

Exit codes: 0 success or dry run; 1 refused or failed with nothing written; 2 argparse usage error,
or (apply) the sweep lock is held by a live sweep and nothing was written.

``--rollback`` previews (always rolled back) or, with ``--yes``, commits the deletion of backfilled
sections that carry no seat snapshot, syllabus link or other-source instructor row, plus a cache
rebuild. ``--rebuild-only`` rebuilds one term's cache with no data write. Neither makes a USF
request, and both take the sweep lock first and need ``--rebuild-term``.

``--apply`` needs ``--rebuild-term``: it takes the sweep advisory lock first, writes the backfill,
rebuilds that term's section_rankings in the same transaction and commits only when the
course-level invariant holds and any ``--expect-inserted`` count matches (D-04, D-07).

``--dry-run`` also reports the D-04 what-if (PROJECT.md D-04, D-07) from the same write path as
apply, inside a transaction that is always rolled back: whether the new code alone reproduces the
stored ranking cache, the stored-versus-after-backfill ranking diff, and the instructor-pair join
re-measure against the 2026-09-28 report.

One request per term, never retried, and no URL (request or database) is ever printed: stdout is a
single JSON object of counts.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from easy_a.analytics.pair_coverage import PairCoverage, measure_instructor_pairs
from easy_a.analytics.scoring import ScoreConfig
from easy_a.common.lookups import ensure_term
from easy_a.config import DatabaseConfigError
from easy_a.db import get_engine, get_session_factory
from easy_a.models import IngestRun
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.rankings.diff import (
    RankingDiff,
    ScoreRow,
    computed_score_rows,
    diff_score_rows,
    stored_score_rows,
)
from easy_a.schedule.backfill import (
    HISTORICAL_GRADE_TERMS,
    BackfillGuardError,
    TermSelection,
    WriteCounts,
    backfill_ingest_source,
    delete_backfilled_sections,
    load_grade_keys,
    resolve_course_ids,
    select_backfill_rows,
    select_rollback_sections,
    validate_selection,
    write_term_backfill,
)
from easy_a.schedule.client import StaffScheduleClient, WholeTermResponseError
from easy_a.schedule.parser import ScheduleParseError
from easy_a.sync.fetch import FetchedTerm, fetch_whole_term
from easy_a.sync.lock import try_sweep_lock

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BUSY = 2

DEFAULT_PAUSE_SECONDS = 30.0
MIN_PAUSE_SECONDS = 10.0
DEFAULT_MAX_UNMATCHED_FRACTION = 0.02
DEFAULT_WHAT_IF_TERM = "202701"

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


def _live_term(value: str) -> str:
    """A six-digit Banner term that is not one of the historical backfill terms."""
    term = value.strip()
    if not (len(term) == 6 and term.isdigit()):
        raise argparse.ArgumentTypeError(f"{value!r} is not a six-digit term code")
    if term in HISTORICAL_GRADE_TERMS:
        raise argparse.ArgumentTypeError(
            f"{term} is a historical backfill term; name the live term instead"
        )
    return term


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


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
    mode.add_argument(
        "--rollback",
        action="store_true",
        help="Preview (always rolled back), or with --yes commit, deleting backfilled sections "
        "that have no seat snapshot, syllabus link or other-source instructor row; no USF request.",
    )
    mode.add_argument(
        "--rebuild-only",
        action="store_true",
        help="Rebuild --rebuild-term's section_rankings under the sweep lock; no USF request and "
        "no data write (the undo for a scoring revert).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="With --rollback: commit the deletion instead of only previewing it.",
    )
    parser.add_argument(
        "--rebuild-term",
        type=_live_term,
        default=None,
        help="Live term whose section_rankings cache is rebuilt in the same transaction "
        "(required with --apply, --rollback and --rebuild-only).",
    )
    parser.add_argument(
        "--expect-inserted",
        type=_non_negative_int,
        default=None,
        metavar="N",
        help="With --apply: roll back unless exactly N sections are inserted in total "
        "(use the count the reviewed dry run reported).",
    )
    parser.add_argument(
        "--what-if-term",
        type=_live_term,
        default=DEFAULT_WHAT_IF_TERM,
        help="Live term whose ranking cache the --dry-run what-if is computed for "
        f"(default {DEFAULT_WHAT_IF_TERM}).",
    )
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
        parser = build_parser()
        args = parser.parse_args(argv)
        _check_mode_arguments(parser, args)
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


def _check_mode_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Cross-argument rules argparse cannot express: exit 2 before any work or request."""
    if (args.apply or args.rollback or args.rebuild_only) and args.rebuild_term is None:
        parser.error(
            "--apply, --rollback and --rebuild-only require --rebuild-term "
            "(the live term whose cache is rebuilt)"
        )
    if args.expect_inserted is not None and not args.apply:
        parser.error("--expect-inserted only applies to --apply")
    if args.yes and not args.rollback:
        parser.error("--yes only applies to --rollback")


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
    if args.rollback or args.rebuild_only:
        return _run_undo(args, session_factory=session_factory)

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
    what_if: WhatIf | None = None
    applied: Applied | None = None
    committed = False
    if can_write:
        session = session_factory()
        try:
            if not dry_run and not try_sweep_lock(session):
                # First locking statement of the transaction (D-22 c): a live sweep holds it.
                session.rollback()
                return _emit(args, _busy_report(), EXIT_BUSY)
            before: _WhatIfBefore | None = None
            stored_before: dict[str, ScoreRow] | None = None
            if dry_run:
                # Read before any backfill write: the stored cache and the new code's recomputation.
                before = _what_if_before(session, args.what_if_term)
            else:
                stored_before = stored_score_rows(session, args.rebuild_term)
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
            if before is not None:
                what_if = _what_if_after(session, args.what_if_term, before)
            if stored_before is not None:
                applied = _rebuild_and_diff(
                    session,
                    args.rebuild_term,
                    stored_before,
                    inserted=sum(counts.inserted for counts in writes.values()),
                    expected_inserted=args.expect_inserted,
                )
            if dry_run or (applied is not None and applied.gate_failures):
                session.rollback()
            else:
                session.commit()
                committed = True
        except SQLAlchemyError as exc:
            session.rollback()
            return _emit(args, _failure("database", detail=str(exc)), EXIT_FAILED)
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    failed = (
        guard_failed
        or (what_if is not None and not what_if.gate_passed)
        or (applied is not None and bool(applied.gate_failures))
    )
    outcome = _Outcome(
        selections=selections,
        writes=writes,
        guards=guards,
        what_if=what_if,
        applied=applied,
        committed=committed,
    )
    return _emit(
        args,
        _report(args, outcome, include_changes=False),
        EXIT_FAILED if failed else EXIT_OK,
        file_report=_report(args, outcome, include_changes=True),
    )


def _busy_report() -> dict[str, Any]:
    return {"status": "busy", "error_kind": "sweep_lock_busy", "written": False}


@dataclass(frozen=True)
class Applied:
    """The stored-before versus stored-after cache diff of one apply, and its commit gate."""

    rebuild_term: str
    rows_rebuilt: int
    diff: RankingDiff
    inserted: int
    expected_inserted: int | None
    gated: bool = True
    """False for the undo modes: the diff is reported, but it never blocks an undo."""

    @property
    def gate_failures(self) -> list[str]:
        """Reasons the transaction must roll back (T-10-19): empty means it may commit."""
        failures: list[str] = []
        if not self.gated:
            return failures
        if not self.diff.course_level_invariant:
            failures.append("course_level_invariant")
        if self.expected_inserted is not None and self.expected_inserted != self.inserted:
            failures.append("expect_inserted")
        return failures

    def to_dict(self, *, include_changes: bool) -> dict[str, Any]:
        output: dict[str, Any] = self.diff.to_dict(include_changes=include_changes)
        output.update(
            rebuild_term=self.rebuild_term,
            rows_rebuilt=self.rows_rebuilt,
            gated=self.gated,
            gate_failures=self.gate_failures,
            verdicts={
                "course_level_invariant": "PASS" if self.diff.course_level_invariant else "FAIL"
            },
        )
        if self.expected_inserted is not None:
            output["expect_inserted"] = {
                "expected": self.expected_inserted,
                "actual": self.inserted,
                "matched": self.expected_inserted == self.inserted,
            }
        return output


def _rebuild_and_diff(
    session: Session,
    term: str,
    stored_before: dict[str, ScoreRow],
    *,
    inserted: int,
    expected_inserted: int | None,
    gated: bool = True,
) -> Applied:
    """Rebuild the term's cache in the caller's transaction and diff it against the stored rows."""
    rows_rebuilt = refresh_section_rankings(session, term=term)
    stored_after = stored_score_rows(session, term)
    return Applied(
        rebuild_term=term,
        rows_rebuilt=rows_rebuilt,
        diff=diff_score_rows(stored_before, stored_after),
        inserted=inserted,
        expected_inserted=expected_inserted,
        gated=gated,
    )


def _run_undo(args: argparse.Namespace, *, session_factory: SessionFactory) -> int:
    """--rollback and --rebuild-only: no USF request, the sweep lock first, then a cache rebuild.

    --rebuild-only changes only the derived cache. --rollback also deletes the eligible backfilled
    sections; without --yes it does all of it and rolls back, so the preview is the real thing.
    """
    terms: list[str] = list(dict.fromkeys(args.terms))
    commit = bool(args.rebuild_only or args.yes)
    session = session_factory()
    try:
        if not try_sweep_lock(session):
            session.rollback()
            return _emit(args, _busy_report(), EXIT_BUSY)
        stored_before = stored_score_rows(session, args.rebuild_term)
        report: dict[str, Any] = {"status": "succeeded"}
        if args.rollback:
            selection = select_rollback_sections(session, terms)
            deleted = delete_backfilled_sections(session, selection.section_ids)
            report.update(
                preview=not args.yes,
                deleted_sections=deleted,
                terms={
                    term: {
                        "eligible_sections": selection.eligible_by_term.get(term, 0),
                        "ineligible_sections": selection.ineligible_by_term.get(term, 0),
                    }
                    for term in terms
                },
            )
        applied = _rebuild_and_diff(
            session,
            args.rebuild_term,
            stored_before,
            inserted=0,
            expected_inserted=None,
            gated=False,
        )
        if commit:
            session.commit()
        else:
            session.rollback()
    except SQLAlchemyError as exc:
        session.rollback()
        return _emit(args, _failure("database", detail=str(exc)), EXIT_FAILED)
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()

    report["written"] = commit
    full = {**report, "applied": applied.to_dict(include_changes=True)}
    report["applied"] = applied.to_dict(include_changes=False)
    return _emit(args, report, EXIT_OK, file_report=full)


@dataclass(frozen=True)
class _Outcome:
    selections: dict[str, TermSelection]
    writes: dict[str, WriteCounts]
    guards: dict[str, list[str]]
    what_if: WhatIf | None
    applied: Applied | None
    committed: bool


@dataclass(frozen=True)
class _WhatIfBefore:
    stored: dict[str, ScoreRow]
    computed: dict[str, ScoreRow]


@dataclass(frozen=True)
class WhatIf:
    """The D-04 what-if of one dry run: code-only parity, the ranking diff and the pair join.

    Both gates read ``RankingDiff`` verdicts, which compare float scores within
    ``easy_a.rankings.diff.SCORE_TOLERANCE``; the apply gate (``Applied``) does the same.
    """

    term: str
    code_only_parity: RankingDiff
    ranking_diff: RankingDiff
    pairs: PairCoverage

    @property
    def verdicts(self) -> dict[str, str]:
        def verdict(passed: bool) -> str:
            return "PASS" if passed else "FAIL"

        return {
            "code_only_parity": verdict(self.code_only_parity.identical),
            "course_level_invariant": verdict(self.ranking_diff.course_level_invariant),
            "pairs_match_reference": verdict(self.pairs.matches_reference),
        }

    @property
    def gate_passed(self) -> bool:
        """Exit-code gate: parity and the course-level invariant. The pairs verdict only reports."""
        return self.code_only_parity.identical and self.ranking_diff.course_level_invariant

    def to_dict(self, *, include_changes: bool) -> dict[str, Any]:
        return {
            "term": self.term,
            "code_only_parity": self.code_only_parity.to_dict(include_changes=include_changes),
            "ranking_diff": self.ranking_diff.to_dict(include_changes=include_changes),
            "pairs": self.pairs.to_dict(),
            "verdicts": self.verdicts,
        }


def _what_if_before(session: Session, term: str) -> _WhatIfBefore:
    return _WhatIfBefore(
        stored=stored_score_rows(session, term),
        computed=computed_score_rows(session, term, ScoreConfig()),
    )


def _what_if_after(session: Session, term: str, before: _WhatIfBefore) -> WhatIf:
    after_computed = computed_score_rows(session, term, ScoreConfig())
    return WhatIf(
        term=term,
        code_only_parity=diff_score_rows(before.stored, before.computed),
        ranking_diff=diff_score_rows(before.stored, after_computed),
        pairs=measure_instructor_pairs(session, before_term=term),
    )


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
    args: argparse.Namespace, outcome: _Outcome, *, include_changes: bool
) -> dict[str, Any]:
    guard_failed = any(outcome.guards.values())
    what_if = outcome.what_if
    applied = outcome.applied
    what_if_failed = what_if is not None and not what_if.gate_passed
    apply_failures = applied.gate_failures if applied is not None else []
    report: dict[str, Any] = {
        "status": "failed" if guard_failed or what_if_failed or apply_failures else "succeeded",
        "written": outcome.committed,
        "terms": {
            term: _term_report(selection, outcome.writes.get(term), outcome.guards[term])
            for term, selection in outcome.selections.items()
        },
    }
    if what_if is not None:
        report["what_if"] = what_if.to_dict(include_changes=include_changes)
    if applied is not None:
        report["applied"] = applied.to_dict(include_changes=include_changes)
    if guard_failed:
        report["error_kind"] = "guard"
    elif what_if_failed:
        report["error_kind"] = "what_if"
    elif apply_failures:
        report["error_kind"] = apply_failures[0]
    return report


def _mode_name(args: argparse.Namespace) -> str:
    if args.rollback:
        return "rollback"
    if args.rebuild_only:
        return "rebuild_only"
    return "dry_run" if args.dry_run else "apply"


def _redact(text: str) -> str:
    return _URL_RE.sub("[redacted-url]", text)


def _emit(
    args: argparse.Namespace,
    report: dict[str, Any],
    exit_code: int,
    *,
    file_report: dict[str, Any] | None = None,
) -> int:
    """Print one JSON line; --report-json gets ``file_report`` (the full detail) when given."""
    mode = _mode_name(args)
    # Defence in depth: nothing URL-shaped may reach stdout or the report file.
    print(_redact(json.dumps({"mode": mode, **report}, sort_keys=True)))
    if args.report_json is not None:
        full = {"mode": mode, **(file_report if file_report is not None else report)}
        args.report_json.write_text(_redact(json.dumps(full, indent=2, sort_keys=True)) + "\n")
    return exit_code
