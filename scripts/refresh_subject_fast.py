"""Bulk per-subject coverage ingest that DEFERS the whole-term quality check.

The standard per-subject entrypoint (``target_cli.main(coverage=True)`` behind
``scripts/refresh_course_coverage.py``) runs ``run_quality_checks`` over the ENTIRE
term on every invocation. During a bulk all-Tampa load that is O(n^2): subject *k*
re-analyzes every course ingested so far, which is what makes a 200+ subject run
degrade into hours (see 06-RESEARCH follow-up: DB latency investigation).

This fast path reuses the SAME guarded ingestion -- ``refresh_targets`` with its
merged campus + suffix guards, and its per-course (already scoped) ranking-cache
refresh -- completely unmodified, and simply omits the per-subject whole-term
quality check. The orchestrator (``refresh_all_tampa.py``) runs a SINGLE whole-term
quality check once, after all subjects complete, turning O(n^2) back into O(n).

Guards and scoring code are untouched; only the redundant per-subject quality pass
is deferred.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from easy_a.common.lookups import ensure_term
from easy_a.db import get_session_factory
from easy_a.refresh.coverage import refresh_targets
from easy_a.refresh.targets import load_targets
from easy_a.schedule.client import StaffScheduleClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Bulk per-subject coverage ingest reusing the guarded refresh_targets path; "
            "the whole-term quality check is deferred to a single final pass run by the "
            "orchestrator (avoids the O(n^2) per-subject quality scan)."
        )
    )
    parser.add_argument("--term", required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--subject")
    parser.add_argument("--course")
    parser.add_argument("--crn")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_targets(args.targets)
    with get_session_factory().begin() as session, StaffScheduleClient() as client:
        ensure_term(session, args.term)
        rows = refresh_targets(
            session,
            term=args.term,
            config=config,
            search=client.search,
            refresh_catalog=True,
            subject=args.subject,
            course=args.course,
            crn=args.crn,
        )
    missing = sum(not row.catalog_present or not row.section_count for row in rows)
    sections = sum(row.section_count for row in rows)
    print(
        f"Term: {args.term}  Subject: {args.subject}  "
        f"Courses: {len(rows)}  Sections: {sections}  Missing: {missing}"
    )
    # Ingestion failures (e.g. a Tampa/course/CRN scope violation) raise inside
    # refresh_targets and propagate as a non-zero exit. A merely-missing target is
    # reported, not an error, and is surfaced by the final whole-term quality pass.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
