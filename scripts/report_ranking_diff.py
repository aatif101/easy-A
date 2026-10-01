"""Read-only D-04 ranking diff: stored section_rankings versus a fresh recomputation.

Compares the stored score fields for one term with a recomputation of the same fields inside a
single read-only transaction (REPEATABLE READ READ ONLY on PostgreSQL), so a concurrent cache
rebuild cannot produce a mixed snapshot. No row is written. Output is one JSON object of CRNs,
course keys and derived numbers only (D-19): no grade buckets, instructor names or connection
strings.

Exit codes: 0 every section identical, 1 any difference, 3 NOT MEASURED (database unreachable).
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

from easy_a.analytics.scoring import ScoreConfig
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_engine
from easy_a.rankings.diff import (
    RankingDiff,
    computed_score_rows,
    diff_score_rows,
    stored_score_rows,
)

GATE = "ranking_diff"


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only D-04 ranking diff: compare stored section_rankings score fields with a "
            "fresh recomputation of the same term. Exit codes: 0 identical, 1 any difference, "
            "3 NOT MEASURED (database unreachable)."
        )
    )
    parser.add_argument("--term", type=_term_code, required=True, help="Banner term code.")
    parser.add_argument(
        "--top",
        type=_positive_int,
        default=50,
        help="Number of largest changes to list. Default: 50.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path for the full report including every per-CRN change.",
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


def collect_diff(session: Session, term: str, *, top: int) -> RankingDiff:
    """Read stored and recomputed rows inside one read-only transaction. Issues no writes."""
    bind = session.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) == "postgresql":
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
    before = stored_score_rows(session, term)
    after = computed_score_rows(session, term, ScoreConfig())
    return diff_score_rows(before, after, top=top)


def _verdict(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _envelope(*, term: str, environment: str) -> dict[str, Any]:
    return {
        "gate": GATE,
        "term": term,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
    }


def _not_measured(*, term: str, environment: str) -> dict[str, Any]:
    return {
        **_envelope(term=term, environment=environment),
        "verdicts": {"identical": "NOT MEASURED", "course_level_invariant": "NOT MEASURED"},
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
                diff = collect_diff(session, args.term, top=args.top)
            except SQLAlchemyError:
                print(json.dumps(_not_measured(term=args.term, environment=environment)))
                return 3
    finally:
        engine.dispose()

    verdicts = {
        "identical": _verdict(diff.identical),
        "course_level_invariant": _verdict(diff.course_level_invariant),
    }
    envelope = _envelope(term=args.term, environment=environment)
    print(json.dumps({**envelope, **diff.to_dict(), "verdicts": verdicts}))

    if args.report_json is not None:
        full = {**envelope, **diff.to_dict(include_changes=True), "verdicts": verdicts}
        _write_atomic(args.report_json, json.dumps(full, indent=2) + "\n")

    return 0 if diff.identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
