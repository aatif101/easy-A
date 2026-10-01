"""Independent, read-only re-measure of the historical (instructor, course) join.

Phase 10 success criterion 1: the join coverage re-measured against the database must match the
2026-09-28 feasibility report (``.planning/research/instructor-grade-feasibility-2026-09-28.md``,
section 1). This module deliberately does not reuse the scoring code (``analytics.queries``), so it
can cross-check it: it reads grade rows, joins them to sections by term + CRN, reads the section's
instructor names, and counts pairs itself.

The measurement is the raw join exactly as the research did it: every section type counts, and
"Staff" and blank names are excluded. The effect of the laboratory rule appears in the ranking diff
(``easy_a.rankings.diff``), not here, so these numbers stay comparable to the report. For one
(instructor, course) pair, ``effective_n = min(sum of A-F counts, sum of total_grades)`` with
recency off, matching the report's definition.

Callers own the transaction; nothing here writes. Output is counts only: no instructor names, no
per-CRN grade buckets (D-19).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from easy_a.common.instructors import is_usable_instructor
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term

# The report's section 1 histogram and term-span numbers (3,216 pairs; 1,329 / 2,178 / 2,829 /
# 3,208 / 3,216 at effective_n >= 60 / 30 / 15 / 5 / 1). "pairs" is the pairs_total measurement.
REFERENCE_2026_09_28: Mapping[str, Any] = {
    "pairs": 3216,
    "n_ge_60": 1329,
    "n_ge_30": 2178,
    "n_ge_15": 2829,
    "n_ge_5": 3208,
    "n_ge_1": 3216,
    "instructors": 1796,
    "courses": 1117,
    "multi_term_pairs": 1439,
    "n_ge_30_multi_term": 1308,
    "grade_rows_total": 8662,
    "grade_rows_named": 8661,
    "term_span": {"1": 1777, "2": 965, "3": 359, "4": 110, "5": 5},
}

# The reference keys that must all match for matches_reference (the report's headline numbers).
_MATCH_KEYS: tuple[str, ...] = ("pairs", "n_ge_60", "n_ge_30", "n_ge_15")

# Reference key -> PairCoverage attribute carrying the measured value.
_MEASURED_ATTRIBUTE: Mapping[str, str] = {
    "pairs": "pairs_total",
    "n_ge_60": "n_ge_60",
    "n_ge_30": "n_ge_30",
    "n_ge_15": "n_ge_15",
    "n_ge_5": "n_ge_5",
    "n_ge_1": "n_ge_1",
    "instructors": "instructors",
    "courses": "courses",
    "multi_term_pairs": "multi_term_pairs",
    "n_ge_30_multi_term": "n_ge_30_multi_term",
    "grade_rows_total": "grade_rows_total",
    "grade_rows_named": "grade_rows_named",
}


@dataclass(frozen=True)
class PairCoverage:
    before_term: str
    pairs_total: int
    n_ge_60: int
    n_ge_30: int
    n_ge_15: int
    n_ge_5: int
    n_ge_1: int
    instructors: int
    courses: int
    multi_term_pairs: int
    n_ge_30_multi_term: int
    term_span: dict[str, int]
    grade_rows_total: int
    grade_rows_with_section: int
    grade_rows_named: int
    grade_rows_staff_or_blank: int
    section_type_histogram: dict[str, int]
    reference: Mapping[str, Any] = field(default_factory=dict)

    @property
    def matches_reference(self) -> bool:
        """True only when pairs, n >= 60, n >= 30 and n >= 15 all equal the reference."""
        return all(
            key in self.reference
            and getattr(self, _MEASURED_ATTRIBUTE[key]) == self.reference[key]
            for key in _MATCH_KEYS
        )

    @property
    def deltas(self) -> dict[str, Any]:
        """Measured minus reference for every reference key (term_span per span bucket)."""
        output: dict[str, Any] = {}
        for key, expected in self.reference.items():
            if key == "term_span":
                spans = sorted(
                    set(expected) | set(self.term_span),
                    key=int,
                )
                output[key] = {
                    span: self.term_span.get(span, 0) - expected.get(span, 0) for span in spans
                }
            elif key in _MEASURED_ATTRIBUTE:
                output[key] = getattr(self, _MEASURED_ATTRIBUTE[key]) - expected
        return output

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_term": self.before_term,
            "pairs_total": self.pairs_total,
            "n_ge_60": self.n_ge_60,
            "n_ge_30": self.n_ge_30,
            "n_ge_15": self.n_ge_15,
            "n_ge_5": self.n_ge_5,
            "n_ge_1": self.n_ge_1,
            "instructors": self.instructors,
            "courses": self.courses,
            "multi_term_pairs": self.multi_term_pairs,
            "n_ge_30_multi_term": self.n_ge_30_multi_term,
            "term_span": dict(self.term_span),
            "grade_rows_total": self.grade_rows_total,
            "grade_rows_with_section": self.grade_rows_with_section,
            "grade_rows_named": self.grade_rows_named,
            "grade_rows_staff_or_blank": self.grade_rows_staff_or_blank,
            "section_type_histogram": dict(self.section_type_histogram),
            "reference": dict(self.reference),
            "deltas": self.deltas,
            "matches_reference": self.matches_reference,
        }


@dataclass
class _PairTotals:
    completed: int = 0
    total: int = 0
    terms: set[str] = field(default_factory=set)

    @property
    def effective_n(self) -> int:
        return min(self.completed, self.total)


def _clean_name(name: str) -> str:
    return " ".join(name.split())


def measure_instructor_pairs(session: Session, *, before_term: str | int) -> PairCoverage:
    """Count (instructor, course) pairs over grade rows of terms before ``before_term``."""
    normalized_before = normalize_banner_term_code(before_term)

    grade_rows = session.execute(
        select(
            GradeDistribution.a_count,
            GradeDistribution.b_count,
            GradeDistribution.c_count,
            GradeDistribution.d_count,
            GradeDistribution.f_count,
            GradeDistribution.total_grades,
            Term.banner_code,
            Section.id,
            Section.section_type,
            Course.subject,
            Course.number,
        )
        .join(Term, GradeDistribution.term_id == Term.id)
        .outerjoin(
            Section,
            and_(
                Section.term_id == GradeDistribution.term_id,
                Section.crn == GradeDistribution.crn,
            ),
        )
        .outerjoin(Course, Course.id == Section.course_id)
        .where(Term.banner_code < normalized_before)
    ).all()

    section_ids = {row[7] for row in grade_rows if row[7] is not None}
    names_by_section: dict[int, dict[str, str]] = {}
    if section_ids:
        for section_id, name_raw in session.execute(
            select(SectionInstructor.section_id, SectionInstructor.name_raw).where(
                SectionInstructor.section_id.in_(section_ids)
            )
        ):
            if not is_usable_instructor(name_raw):
                continue
            cleaned = _clean_name(name_raw)
            names_by_section.setdefault(section_id, {}).setdefault(cleaned.casefold(), cleaned)

    pairs: dict[tuple[str, str, str], _PairTotals] = {}
    grade_rows_with_section = 0
    grade_rows_named = 0
    section_type_histogram: dict[str, int] = {}

    for a, b, c, d, f, total_grades, term_code, section_id, section_type, subject, number in (
        grade_rows
    ):
        if section_id is None:
            continue
        grade_rows_with_section += 1
        section_type_histogram[section_type] = section_type_histogram.get(section_type, 0) + 1
        names = names_by_section.get(section_id)
        if not names:
            continue
        grade_rows_named += 1
        for name_key in names:
            totals = pairs.setdefault((name_key, subject, number), _PairTotals())
            totals.completed += a + b + c + d + f
            totals.total += total_grades
            totals.terms.add(term_code)

    effective = {key: totals.effective_n for key, totals in pairs.items()}
    term_span: dict[str, int] = {}
    for totals in pairs.values():
        span = str(len(totals.terms))
        term_span[span] = term_span.get(span, 0) + 1

    return PairCoverage(
        before_term=normalized_before,
        pairs_total=len(pairs),
        n_ge_60=sum(1 for n in effective.values() if n >= 60),
        n_ge_30=sum(1 for n in effective.values() if n >= 30),
        n_ge_15=sum(1 for n in effective.values() if n >= 15),
        n_ge_5=sum(1 for n in effective.values() if n >= 5),
        n_ge_1=sum(1 for n in effective.values() if n >= 1),
        instructors=len({name_key for name_key, _, _ in pairs}),
        courses=len({(subject, number) for _, subject, number in pairs}),
        multi_term_pairs=sum(1 for totals in pairs.values() if len(totals.terms) >= 2),
        n_ge_30_multi_term=sum(
            1
            for key, totals in pairs.items()
            if len(totals.terms) >= 2 and effective[key] >= 30
        ),
        term_span=dict(sorted(term_span.items(), key=lambda item: int(item[0]))),
        grade_rows_total=len(grade_rows),
        grade_rows_with_section=grade_rows_with_section,
        grade_rows_named=grade_rows_named,
        grade_rows_staff_or_blank=grade_rows_with_section - grade_rows_named,
        section_type_histogram=dict(
            sorted(section_type_histogram.items(), key=lambda item: (-item[1], item[0]))
        ),
        # Read at call time so a test (or a re-baselined report) can substitute the reference.
        reference=dict(REFERENCE_2026_09_28),
    )
