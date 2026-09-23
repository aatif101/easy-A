#!/usr/bin/env python
"""Measure a whole-term ranking-cache rebuild and quality pass without persisting anything.

The rebuild runs inside the caller-owned transaction exactly as operators run it, flushes,
then rolls back so the stored cache is left untouched. The quality pass is read-only.
Only counts and timings are printed; the database URL is never echoed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import event

from easy_a.common.terms import normalize_banner_term_code
from easy_a.db import get_engine, get_session_factory, is_transaction_pooler
from easy_a.quality.checks import run_quality_checks
from easy_a.rankings.cache import refresh_section_rankings


class _StatementCounter:
    def __init__(self) -> None:
        self.total = 0
        self.grade_reads = 0

    def __call__(self, conn, cursor, statement, parameters, context, executemany) -> None:
        self.total += 1
        lowered = statement.lower()
        if lowered.lstrip().startswith("select") and "grade_distributions" in lowered:
            self.grade_reads += 1

    def reset(self) -> tuple[int, int]:
        counts = (self.total, self.grade_reads)
        self.total = 0
        self.grade_reads = 0
        return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--term", default="202701")
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--skip-rebuild", action="store_true")
    args = parser.parse_args(argv)
    term = normalize_banner_term_code(args.term)

    engine = get_engine()
    counter = _StatementCounter()
    event.listen(engine, "before_cursor_execute", counter)
    environment = {
        "dialect": engine.url.get_backend_name(),
        "pooler": is_transaction_pooler(engine.url.render_as_string(hide_password=False)),
    }
    results: dict = {"term": term, "environment": environment}
    try:
        session = get_session_factory(engine)()
        try:
            if not args.skip_rebuild:
                started = time.perf_counter()
                written = refresh_section_rankings(session, term=term)
                session.flush()
                elapsed = time.perf_counter() - started
                statements, grade_reads = counter.reset()
                results["rebuild"] = {
                    "rows_written": written,
                    "elapsed_s": round(elapsed, 2),
                    "statements": statements,
                    "grade_reads": grade_reads,
                    "completed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                }
                session.rollback()
                print(json.dumps(results), flush=True)
            if not args.skip_quality:
                counter.reset()
                started = time.perf_counter()
                report = run_quality_checks(session, term)
                elapsed = time.perf_counter() - started
                statements, grade_reads = counter.reset()
                findings: dict[str, int] = {}
                for finding in report.findings:
                    severity = getattr(finding.severity, "value", finding.severity)
                    key = f"{severity}:{finding.check_id}"
                    findings[key] = findings.get(key, 0) + 1
                results["quality"] = {
                    "elapsed_s": round(elapsed, 2),
                    "statements": statements,
                    "grade_reads": grade_reads,
                    "findings": dict(sorted(findings.items())),
                    "completed_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                }
                session.rollback()
        finally:
            session.close()
    finally:
        engine.dispose()
    print(json.dumps(results), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
