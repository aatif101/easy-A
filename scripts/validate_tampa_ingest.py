from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy.orm import Session

from easy_a.refresh.targets import CourseTarget, load_targets

DEFAULT_TERM = "202701"
DEFAULT_TARGETS = Path("config/course_targets.toml")


def derive_suffix_pairs(
    targets: tuple[CourseTarget, ...],
) -> tuple[tuple[str, str, str], ...]:
    """(subject, base_number, suffix_number) triples where both a base course number
    and a base+trailing-letter course number exist as targets for the same subject."""
    raise NotImplementedError("derive_suffix_pairs: GREEN phase pending")


def assert_suffix_exact_ingest(
    session: Session, term: str, pairs: Iterable[tuple[str, str, str]]
) -> None:
    """Every stored section for a base course belongs to the base course only; the
    suffix (L-variant) course owns its own stored sections. Raises AssertionError
    naming the offending course on any leak."""
    raise NotImplementedError("assert_suffix_exact_ingest: GREEN phase pending")


def assert_coverage_reconciled(
    session: Session, term: str, targets: tuple[CourseTarget, ...]
) -> None:
    """Stored Section count == coverage_metadata section-count sum == rankings-search
    total for the term, and every distinct stored (subject, number) is a configured
    target. Raises AssertionError with the mismatch on failure."""
    raise NotImplementedError("assert_coverage_reconciled: GREEN phase pending")


def assert_honest_coverage(session: Session, term: str) -> None:
    """Every section_rankings row with score_source in {course, instructor_course} has
    effective_n > 0, and every effective_n == 0 row has score_source == global.
    Raises AssertionError naming the offending CRN otherwise (D-20)."""
    raise NotImplementedError("assert_honest_coverage: GREEN phase pending")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only scale validation for the full Tampa ingestion (REQ-COVERAGE-03)."
    )
    parser.add_argument("--term", default=DEFAULT_TERM, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument(
        "--targets", type=Path, default=DEFAULT_TARGETS, help="Course targets TOML."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from easy_a.db import get_session_factory

    args = build_parser().parse_args(argv)
    config = load_targets(args.targets)
    pairs = derive_suffix_pairs(config.targets)

    checks: list[tuple[str, bool, str]] = []
    session_factory = get_session_factory()
    with session_factory() as session:
        for name, fn in (
            ("suffix-exact", lambda: assert_suffix_exact_ingest(session, args.term, pairs)),
            (
                "reconciliation",
                lambda: assert_coverage_reconciled(session, args.term, config.targets),
            ),
            ("honest-coverage", lambda: assert_honest_coverage(session, args.term)),
        ):
            try:
                fn()
            except AssertionError as exc:
                checks.append((name, False, str(exc)))
            else:
                checks.append((name, True, ""))

    exit_code = 0
    for name, passed, detail in checks:
        if passed:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: {detail}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
