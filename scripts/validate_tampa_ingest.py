from __future__ import annotations

import argparse
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.terms import normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.models import Course, GradeDistribution, Section, Term
from easy_a.rankings.cache import SectionRankingCache
from easy_a.refresh.coverage import coverage_metadata
from easy_a.refresh.targets import CourseTarget, load_targets
from easy_a.sync.scope import is_undergraduate_number

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
    naming the offending course on any leak.

    The suffix Course existence lookup below is catalog-scoped: Course rows carry no
    term_id (src/easy_a/models/core.py), so a course either exists in the catalog or
    it doesn't -- there is no per-term Course row to filter on. The section-count
    check immediately after it, by contrast, is term-scoped, because Section rows do
    carry a term. The schedule response that would otherwise disambiguate ("is this
    course offered this term?") is not persisted anywhere, so stored data has no
    other term-scoped signal to consult. Narrowing the existence lookup to only
    courses that already own sections in the validated term would make the
    zero-section branch below unreachable, silently deleting the Phase 06 L-variant
    leak guard -- so it stays catalog-wide on purpose. A catalog suffix course that
    owns 0 sections in the validated term is therefore genuinely ambiguous between a
    leak into the base course and the suffix course not being offered that term, and
    this function fails closed on that ambiguity rather than guessing (D-06, D-07)."""
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

        # Intentionally catalog-wide: Course rows carry no term (src/easy_a/models/core.py),
        # so this lookup cannot be scoped to the validated term the way the section-count
        # query below is. See the docstring above for why narrowing this to
        # term-having courses would silently disable the leak guard.
        suffix_course_id = session.scalar(
            select(Course.id).where(Course.subject == subject, Course.number == suffix_number)
        )
        if suffix_course_id is None:
            continue

        # Deliberately counts ALL stored sections, including soft-removed ones (removed_at):
        # a removed section was still ingested under the right course, so it still proves
        # the suffix course owns its own sections. Only the guard's inputs are unchanged.
        suffix_section_count = session.scalar(
            select(func.count(Section.id))
            .join(Term, Section.term_id == Term.id)
            .where(Term.banner_code == normalized_term, Section.course_id == suffix_course_id)
        )
        if not suffix_section_count:
            raise AssertionError(
                f"{subject} {suffix_number}: suffix course is ingested but owns 0 stored "
                f"sections for term {normalized_term}. Stored data cannot distinguish "
                f"between two possibilities: its sections leaked into {subject} "
                f"{base_number}, or {subject} {suffix_number} is simply not offered in "
                f"term {normalized_term} -- confirm against the USF schedule for that "
                "term before treating this as a leak."
            )


def assert_coverage_reconciled(
    session: Session, term: str, targets: tuple[CourseTarget, ...]
) -> list[tuple[str, str]]:
    """Active stored Section count == coverage_metadata section-count sum + auto-added
    active sections == rankings-search total for the term.

    Only active sections (``removed_at IS NULL``) are counted. A stored course that is not a
    configured target is legitimate only as a D-05 auto-add: every one of its active sections
    is Tampa and its course number is undergraduate (``is_undergraduate_number`` from
    ``easy_a.sync.scope``). Any other untargeted course (graduate, non-Tampa) raises
    AssertionError. Returns the sorted auto-added (subject, number) keys."""
    normalized_term = normalize_banner_term_code(term)

    target_keys = {(target.subject, target.number) for target in targets}
    rows = session.execute(
        select(Course.subject, Course.number, Section.campus)
        .join(Section, Section.course_id == Course.id)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == normalized_term, Section.removed_at.is_(None))
    ).all()

    sections_by_key: dict[tuple[str, str], list[str | None]] = {}
    for subject, number, campus in rows:
        sections_by_key.setdefault((subject, number), []).append(campus)

    auto_added: list[tuple[str, str]] = []
    illegitimate: list[tuple[str, str]] = []
    for key in sorted(set(sections_by_key) - target_keys):
        all_tampa = all(same_campus(campus, SUPPORTED_CAMPUS) for campus in sections_by_key[key])
        if all_tampa and is_undergraduate_number(key[1]):
            auto_added.append(key)
        else:
            illegitimate.append(key)
    if illegitimate:
        raise AssertionError(
            f"term {normalized_term}: {len(illegitimate)} stored course(s) are not present "
            f"in the configured targets and are not undergraduate Tampa auto-adds (D-05): "
            f"{illegitimate}."
        )
    auto_added_sections = sum(len(sections_by_key[key]) for key in auto_added)

    stored_count = session.scalar(
        select(func.count(Section.id))
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == normalized_term, Section.removed_at.is_(None))
    )
    coverage_sum = sum(row.section_count for row in coverage_metadata(session, term, targets))
    rankings_total = session.scalar(
        select(func.count(SectionRankingCache.id)).where(
            SectionRankingCache.term == normalized_term
        )
    )
    if not (stored_count == coverage_sum + auto_added_sections == rankings_total):
        raise AssertionError(
            f"term {normalized_term}: counts disagree -- stored active Section rows="
            f"{stored_count}, coverage_metadata sum={coverage_sum} + auto-added active "
            f"sections={auto_added_sections} = {coverage_sum + auto_added_sections}, "
            f"rankings-search total={rankings_total}."
        )
    return auto_added


@dataclass(frozen=True)
class _CourseKeyGradeTotals:
    row_count: int
    af_sum: int
    total_sum: int


def _course_key_grade_totals(
    session: Session, term: str, course_keys: Iterable[tuple[str, str]]
) -> dict[tuple[str, str], _CourseKeyGradeTotals]:
    """One grouped query: attributed (course_id is not null) GradeDistribution row
    count, A-F sum and total_grades sum per (subject, number) course key, for
    historical terms earlier than ``term``. Grouped the same way as `_course_ids`
    in src/easy_a/analytics/queries.py (subject + number only, so every catalog
    edition sharing that key is combined -- uq_courses_identity allows several)."""
    keys = set(course_keys)
    if not keys:
        return {}
    normalized_term = normalize_banner_term_code(term)
    af_expr = (
        GradeDistribution.a_count
        + GradeDistribution.b_count
        + GradeDistribution.c_count
        + GradeDistribution.d_count
        + GradeDistribution.f_count
    )
    stmt = (
        select(
            Course.subject,
            Course.number,
            func.count(GradeDistribution.id),
            func.sum(af_expr),
            func.sum(GradeDistribution.total_grades),
        )
        .join(Course, GradeDistribution.course_id == Course.id)
        .join(Term, GradeDistribution.term_id == Term.id)
        .where(
            Term.banner_code < normalized_term,
            tuple_(Course.subject, Course.number).in_(keys),
        )
        .group_by(Course.subject, Course.number)
    )
    return {
        (subject, number): _CourseKeyGradeTotals(
            row_count=row_count,
            af_sum=int(af_sum or 0),
            total_sum=int(total_sum or 0),
        )
        for subject, number, row_count, af_sum, total_sum in session.execute(stmt).all()
    }


def assert_honest_coverage(session: Session, term: str) -> int:
    """Every section_rankings row with score_source in {course, instructor_course} has
    effective_n > 0, and every effective_n == 0 row has score_source == global --
    except a D-21 listed exception: a score_source=course row with effective_n == 0
    is accepted only when stored grade rows prove the course key's history has zero
    A-F (letter-grade) weight and a nonzero total (a non-letter-grade course, e.g.
    S/U or pass/fail). That acceptance is narrow and evidence-proven, never a
    relaxation of D-20 -- every other zero-sample course-backed claim still raises.
    These accepted sections remain listed exceptions, never own-course letter-grade
    history (D-20, D-21). Raises AssertionError naming the offending CRN on any
    other violation. Returns the number of verified non-letter-grade exceptions."""
    normalized_term = normalize_banner_term_code(term)
    rows = session.execute(
        select(
            SectionRankingCache.crn,
            SectionRankingCache.subject,
            SectionRankingCache.course_number,
            SectionRankingCache.score_source,
            SectionRankingCache.effective_n,
        )
        .join(Section, Section.id == SectionRankingCache.section_id)
        .where(SectionRankingCache.term == normalized_term, Section.removed_at.is_(None))
    ).all()

    course_backed_sources = {ScoreSource.course.value, ScoreSource.instructor_course.value}
    zero_course_keys = {
        (subject, course_number)
        for _crn, subject, course_number, score_source, effective_n in rows
        if score_source == ScoreSource.course.value and effective_n == 0
    }
    key_totals = _course_key_grade_totals(session, normalized_term, zero_course_keys)

    verified_exceptions = 0
    for crn, subject, course_number, score_source, effective_n in rows:
        if score_source == ScoreSource.course.value and effective_n == 0:
            totals = key_totals.get((subject, course_number))
            if (
                totals is not None
                and totals.row_count > 0
                and totals.af_sum == 0
                and totals.total_sum > 0
            ):
                verified_exceptions += 1
                continue

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

    return verified_exceptions


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
    verified_exceptions = 0
    auto_added: list[tuple[str, str]] = []
    session_factory = get_session_factory()
    with session_factory() as session:
        checkers: list[tuple[str, Callable[[], object]]] = [
            ("suffix-exact", lambda: assert_suffix_exact_ingest(session, args.term, pairs)),
            (
                "reconciliation",
                lambda: assert_coverage_reconciled(session, args.term, config.targets),
            ),
            ("honest-coverage", lambda: assert_honest_coverage(session, args.term)),
        ]
        for name, fn in checkers:
            try:
                result = fn()
            except AssertionError as exc:
                checks.append((name, False, str(exc)))
            else:
                if name == "honest-coverage" and isinstance(result, int):
                    verified_exceptions = result
                if name == "reconciliation" and isinstance(result, list):
                    auto_added = result
                checks.append((name, True, ""))

    exit_code = 0
    for name, passed, detail in checks:
        if not passed:
            print(f"FAIL {name}: {detail}")
            exit_code = 1
        elif name == "reconciliation":
            listing = ", ".join(f"{subject} {number}" for subject, number in auto_added)
            print(
                f"INFO auto-added (D-05): {len(auto_added)} course(s)"
                + (f": {listing}" if auto_added else "")
            )
            print(f"PASS {name}")
        elif name == "honest-coverage":
            print(f"PASS {name} (verified non-letter-grade exceptions: {verified_exceptions})")
        else:
            print(f"PASS {name}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
