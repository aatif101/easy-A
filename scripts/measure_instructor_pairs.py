"""Read-only re-measure of the historical (instructor, course) join (Phase 10 success criterion 1).

Counts (instructor, course) pairs over grade rows of terms before ``--before-term`` and compares
them with the 2026-09-28 feasibility report (3,216 pairs; 1,329 / 2,178 / 2,829 at effective_n
>= 60 / 30 / 15). The whole measurement runs inside one read-only transaction (REPEATABLE READ
READ ONLY on PostgreSQL); no row is written. Output is one JSON object of counts only: no
instructor names, per-CRN grade buckets or connection strings (D-19).

Exit codes: 0 matches the reference, 1 differs, 3 NOT MEASURED (database unreachable).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from easy_a.analytics.pair_coverage import PairCoverage, measure_instructor_pairs
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_engine

GATE = "instructor_pair_coverage"
DEFAULT_BEFORE_TERM = "202701"


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only re-measure of the historical (instructor, course) join, compared with "
            "the 2026-09-28 report. Exit codes: 0 matches the reference, 1 differs, 3 NOT "
            "MEASURED (database unreachable)."
        )
    )
    parser.add_argument(
        "--before-term",
        type=_term_code,
        default=DEFAULT_BEFORE_TERM,
        help=f"Only grade rows of terms before this one count. Default: {DEFAULT_BEFORE_TERM}.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path to also write the JSON report to.",
    )
    return parser


def _environment_label(engine: Engine) -> str:
    dialect = engine.dialect.name
    if dialect == "sqlite":
        return "SQLite"
    if dialect != "postgresql":
        return dialect
    host = (engine.url.host or "").lower()
    if host.endswith((".supabase.com", ".supabase.co")):
        return "Supabase"
    return "Postgres (other host)"


def collect_pair_coverage(session: Session, before_term: str) -> PairCoverage:
    """Measure inside one read-only transaction. Issues no writes."""
    bind = session.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) == "postgresql":
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    return measure_instructor_pairs(session, before_term=before_term)


def _envelope(*, before_term: str, environment: str) -> dict[str, Any]:
    return {
        "gate": GATE,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
        "before_term": before_term,
    }


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    engine = get_engine()
    environment = _environment_label(engine)
    try:
        with Session(engine) as session:
            try:
                coverage = collect_pair_coverage(session, args.before_term)
            except SQLAlchemyError:
                print(
                    json.dumps(
                        {
                            **_envelope(before_term=args.before_term, environment=environment),
                            "verdict": "NOT MEASURED",
                        }
                    )
                )
                return 3
    finally:
        engine.dispose()

    output = {
        **_envelope(before_term=args.before_term, environment=environment),
        **coverage.to_dict(),
        "verdict": "PASS" if coverage.matches_reference else "FAIL",
    }
    print(json.dumps(output))
    if args.report_json is not None:
        _write_atomic(args.report_json, json.dumps(output, indent=2) + "\n")

    return 0 if coverage.matches_reference else 1


if __name__ == "__main__":
    raise SystemExit(main())
