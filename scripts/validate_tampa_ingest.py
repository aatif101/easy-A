from __future__ import annotations

import argparse
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.common.terms import normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.models import Course, Section, Term
from easy_a.rankings.cache import SectionRankingCache
from easy_a.refresh.coverage import coverage_metadata
from easy_a.refresh.targets import CourseTarget, load_targets

DEFAULT_TERM = "202701"
DEFAULT_TARGETS = Path("config/course_targets.toml")

# Same number-pattern semantics as CourseTarget.number (^[0-9]{4}[A-Z]?$): a suffix
# number is exactly a 4-digit base plus one trailing letter, e.g. "2045L".
_SUFFIX_NUMBER_PATTERN = re.compile(r"^(\d{4})([A-Z])$")


def derive_suffix_pairs(
    targets: tuple[CourseTarget, ...],
) -> tuple[tuple[str, str, str], ...]:
    """(subject, base_number, suffix_number) triples where both a base course number
    and a base+trailing-letter course number exist as targets for the same subject."""
    numbers_by_subject: dict[str, set[str]] = {}
    for target in targets:
        numbers_by_subject.setdefault(target.subject, set()).add(target.number)

    pairs: list[tuple[str, str, str]] = []
    for subject, numbers in numbers_by_subject.items():
        for number in numbers:
            match = _SUFFIX_NUMBER_PATTERN.match(number)
            if match is None:
                continue
            base_number = match.group(1)
            if base_number in numbers:
                pairs.append((subject, base_number, number))
    return tuple(sorted(pairs))


def assert_suffix_exact_ingest(
    session: Session, term: str, pairs: Iterable[tuple[str, str, str]]
) -> None:
    """Every stored section for a base course belongs to the base course only; the
    suffix (L-variant) course owns its own stored sections. Raises AssertionError
    naming the offending course on any leak."""
    normalized_term = normalize_banner_term_code(term)
    for subject, base_number, suffix_number in pairs:
        for number in (base_number, suffix_number):
            course_id = session.scalar(
                select(Course.id).where(Course.subject == subject, Course.number == number)
            )
            if course_id is None:
                continue

            # Defensive schema-level invariant: every section reached by joining on this
            # exact (subject, number) resolves back to a Course row with that same
            # number -- the join itself cannot produce a mismatch, but this proves it.
            mismatched = session.execute(
                select(Section.crn, Course.number)
                .join(Course, Section.course_id == Course.id)
                .join(Term, Section.term_id == Term.id)
                .where(
                    Term.banner_code == normalized_term,
                    Section.course_id == course_id,
                    Course.number != number,
                )
            ).first()
            if mismatched is not None:
                crn, resolved_number = mismatched
                raise AssertionError(
                    f"{subject} {number}: section CRN {crn} resolves to course number "
                    f"{resolved_number!r}, not the expected {number!r}."
                )

        suffix_course_id = session.scalar(
            select(Course.id).where(Course.subject == subject, Course.number == suffix_number)
        )
        if suffix_course_id is None:
            continue

        suffix_section_count = session.scalar(
            select(func.count(Section.id))
            .join(Term, Section.term_id == Term.id)
            .where(Term.banner_code == normalized_term, Section.course_id == suffix_course_id)
        )
        if not suffix_section_count:
            raise AssertionError(
                f"{subject} {suffix_number}: suffix course is ingested but owns 0 stored "
                f"sections for term {normalized_term} -- its sections were likely "
                f"mis-attributed to (leaked into) {subject} {base_number}."
            )


def assert_coverage_reconciled(
    session: Session, term: str, targets: tuple[CourseTarget, ...]
) -> None:
    """Stored Section count == coverage_metadata section-count sum == rankings-search
    total for the term, and every distinct stored (subject, number) is a configured
    target. Raises AssertionError with the mismatch on failure."""
    normalized_term = normalize_banner_term_code(term)

    target_keys = {(target.subject, target.number) for target in targets}
    stored_keys = set(
        session.execute(
            select(Course.subject, Course.number)
            .join(Section, Section.course_id == Course.id)
            .join(Term, Section.term_id == Term.id)
            .where(Term.banner_code == normalized_term)
            .distinct()
        ).all()
    )
    untargeted = sorted(stored_keys - target_keys)
    if untargeted:
        raise AssertionError(
            f"term {normalized_term}: {len(untargeted)} stored course(s) are not present "
            f"in the configured targets: {untargeted}."
        )

    stored_count = session.scalar(
        select(func.count(Section.id))
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == normalized_term)
    )
    coverage_sum = sum(row.section_count for row in coverage_metadata(session, term, targets))
    rankings_total = session.scalar(
        select(func.count(SectionRankingCache.id)).where(
            SectionRankingCache.term == normalized_term
        )
    )
    if not (stored_count == coverage_sum == rankings_total):
        raise AssertionError(
            f"term {normalized_term}: counts disagree -- stored Section rows={stored_count}, "
            f"coverage_metadata sum={coverage_sum}, rankings-search total={rankings_total}."
        )


def assert_honest_coverage(session: Session, term: str) -> None:
    """Every section_rankings row with score_source in {course, instructor_course} has
    effective_n > 0, and every effective_n == 0 row has score_source == global.
    Raises AssertionError naming the offending CRN otherwise (D-20)."""
    normalized_term = normalize_banner_term_code(term)
    rows = session.execute(
        select(
            SectionRankingCache.crn,
            SectionRankingCache.score_source,
            SectionRankingCache.effective_n,
        ).where(SectionRankingCache.term == normalized_term)
    ).all()

    course_backed_sources = {ScoreSource.course.value, ScoreSource.instructor_course.value}
    for crn, score_source, effective_n in rows:
        if score_source in course_backed_sources and effective_n <= 0:
            raise AssertionError(
                f"CRN {crn}: score_source={score_source!r} claims course-backed history "
                f"but effective_n={effective_n} (a global fallback presented as course "
                "history violates D-20)."
            )
        if effective_n == 0 and score_source != ScoreSource.global_.value:
            raise AssertionError(
                f"CRN {crn}: effective_n=0 but score_source={score_source!r} -- every "
                f"effective_n=0 row must be the explicit {ScoreSource.global_.value!r} "
                "fallback (D-20)."
            )


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
    args = build_parser().parse_args(argv)
    config = load_targets(args.targets)
    pairs = derive_suffix_pairs(config.targets)

    checks: list[tuple[str, bool, str]] = []
    session_factory = get_session_factory()
    with session_factory() as session:
        checkers: list[tuple[str, Callable[[], None]]] = [
            ("suffix-exact", lambda: assert_suffix_exact_ingest(session, args.term, pairs)),
            (
                "reconciliation",
                lambda: assert_coverage_reconciled(session, args.term, config.targets),
            ),
            ("honest-coverage", lambda: assert_honest_coverage(session, args.term)),
        ]
        for name, fn in checkers:
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
