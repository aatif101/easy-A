"""Read-only, full-term D-21 grade-coverage inventory for REQ-GRADES-01.

For every stored section of a term, classifies whether it has sourced own-course
grade history (D-21: score_source in {course, instructor_course}, effective_n > 0,
backed by attributed GradeDistribution rows with letter-grade weight and a
reconciled raw total) or is a listed source-limited exception (no rows, or a
course whose stored history has zero letter-grade weight). Every other outcome is
a named integrity failure -- states are never absorbed or hidden.

Every counter reported under the JSON output's "integrity" key gates both
``verdicts.integrity`` and ``verdicts.d21_grade_coverage`` (and therefore the exit
code): a reported integrity anomaly can never print PASS (D-06, D-07, D-21). This
includes ``rows_at_or_after_term`` -- GradeDistribution rows stamped at or after the
inventoried term, which should be impossible for a term whose grade history has not
happened yet. The gate assumes the inventoried term is that upcoming, not-yet-scored
term; running it against a past term that already has later grade rows will report
integrity FAIL by design, not a bug.

Read-only: on PostgreSQL the whole inventory is read inside one
``SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`` transaction (matching
the pattern in ``scripts/benchmark_rankings_search.py`` / ``verify_rankings_pages.py``),
so a concurrent refresh cannot produce a mixed snapshot. No row is written, and only
identifiers, states and derived totals are emitted -- never a per-CRN grade bucket,
connection string or credential (D-19).

Exit codes: 0 both verdicts PASS, 1 otherwise, 3 NOT MEASURED (database unreachable).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.terms import TermParseError, normalize_banner_term_code
from easy_a.db import get_engine
from easy_a.models import Course, GradeDistribution, Section, SectionRankingCache, Term

GATE = "d21_grade_coverage"
DEFAULT_TERM = "202701"

# D-21's allowed source range: USF InfoCenter, Spring 2025 through Spring 2026, with
# Summer 2026 checked and confirmed empty. The 202408 (Fall 2024) pilot rows remain
# sourced history but are reported as outside_window, never silently dropped.
D21_WINDOW_TERMS: tuple[str, ...] = ("202501", "202505", "202508", "202601")
D21_CHECKED_EMPTY_TERMS: tuple[str, ...] = ("202605",)

_COURSE_BACKED_SOURCES = {ScoreSource.course.value, ScoreSource.instructor_course.value}
_VALID_SCORE_SOURCES = {
    ScoreSource.instructor_course.value,
    ScoreSource.course.value,
    ScoreSource.subject.value,
    ScoreSource.global_.value,
}

NO_ROWS_REASON_NOTE = (
    "No stored grade rows exist for the exact course key in the imported range "
    "(USF InfoCenter, Spring 2025 - Spring 2026; Summer 2026 checked empty). Stored "
    "data cannot distinguish InfoCenter's under-five-student omission, a new course, "
    "or a course not offered in the window -- no narrower cause is assigned (D-06, D-07)."
)
NON_LETTER_GRADE_REASON_NOTE = (
    "Stored own-course grade rows exist for this course key with zero A-F "
    "(letter-grade) weight -- the course reports only non-letter outcomes (e.g. "
    "S/U or pass/fail). The prior fallback is presented honestly, never as "
    "own-course letter-grade evidence (D-20, D-21)."
)


class EvidenceState(StrEnum):
    evidence_backed = "evidence_backed"
    exception_non_letter_grade = "exception_non_letter_grade"
    exception_no_rows = "exception_no_rows"
    missing_cache_row = "missing_cache_row"
    unbacked_course_claim = "unbacked_course_claim"
    raw_total_mismatch = "raw_total_mismatch"
    history_not_used = "history_not_used"
    global_nonzero_effective_n = "global_nonzero_effective_n"
    unclassified = "unclassified"


EXCEPTION_STATES = {EvidenceState.exception_non_letter_grade, EvidenceState.exception_no_rows}
FAILURE_STATES = {
    EvidenceState.missing_cache_row,
    EvidenceState.unbacked_course_claim,
    EvidenceState.raw_total_mismatch,
    EvidenceState.history_not_used,
    EvidenceState.global_nonzero_effective_n,
    EvidenceState.unclassified,
}


@dataclass(frozen=True)
class CourseKeyEvidence:
    """Attributed (course_id is not null) GradeDistribution evidence for one
    (subject, course_number) key, summed across every historical term before the
    target term."""

    row_count: int = 0
    af_sum: int = 0
    total_sum: int = 0
    term_codes: frozenset[str] = field(default_factory=frozenset)
    sources: frozenset[str] = field(default_factory=frozenset)

    @property
    def has_rows(self) -> bool:
        return self.row_count > 0


@dataclass(frozen=True)
class SectionState:
    """The D-21 classification of one section, with the evidence that produced it."""

    crn: str
    subject: str
    course_number: str
    state: EvidenceState
    score_source: str | None
    effective_n: float | None
    reason_category: str | None = None
    reason_note: str | None = None
    row_count: int = 0
    total_grades_sum: int = 0
    historical_term_codes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    cached_total_grade_count: int | None = None


@dataclass(frozen=True)
class TermGradeStats:
    term: str
    rows: int
    courses: int
    total_grades_sum: int
    sources: tuple[str, ...]
    source_hash_count: int
    ingested_at_min: str | None
    ingested_at_max: str | None


@dataclass(frozen=True)
class Inventory:
    term: str
    observed_at_utc: str
    environment: str
    sections: tuple[SectionState, ...]
    represented_course_count: int
    cache_row_count: int
    cache_refreshed_at_min: str | None
    cache_refreshed_at_max: str | None
    grade_row_count: int
    grade_ingested_at_max: str | None
    evidence_grade_ingested_at_max: str | None
    non_tampa_section_count: int
    grade_rows_by_term: tuple[TermGradeStats, ...]
    window: dict[str, Any]
    unattributed_grade_rows: int
    bucket_sum_mismatch_rows: int
    rows_at_or_after_term: int
    stale_cache: bool

    @property
    def section_count(self) -> int:
        return len(self.sections)

    def to_dict(self) -> dict[str, Any]:
        sections_by_state = _counts_by_state(self.sections)
        courses_by_state = _course_counts_by_state(self.sections)

        exceptions = [
            {
                "subject": s.subject,
                "course_number": s.course_number,
                "crn": s.crn,
                "score_source": s.score_source,
                "effective_n": s.effective_n,
                "reason_category": s.reason_category,
                "reason_note": s.reason_note,
            }
            for s in sorted(
                (s for s in self.sections if s.state in EXCEPTION_STATES),
                key=lambda s: (s.subject, s.course_number, s.crn),
            )
        ]

        exception_sections_by_reason: dict[str, int] = defaultdict(int)
        for s in self.sections:
            if s.state in EXCEPTION_STATES and s.reason_category:
                exception_sections_by_reason[s.reason_category] += 1

        evidence_backed_sections = sections_by_state.get(EvidenceState.evidence_backed.value, 0)
        failure_section_count = sum(
            count
            for state, count in sections_by_state.items()
            if state in {failure.value for failure in FAILURE_STATES}
        )
        # Every key reported under "integrity" below is built from this same mapping
        # and gates both verdicts -- a reported integrity counter can never be silently
        # absorbed into a PASS (D-06, D-07, D-21; closes CR-01). rows_at_or_after_term
        # counts GradeDistribution rows stamped at or after the inventoried term: under
        # D-21's evidence window that should never happen for a not-yet-scored term, so
        # any nonzero value is itself a named integrity failure, not merely informational.
        # This gate assumes the inventoried term has no grade history of its own yet
        # (the upcoming term being scored); run it against a past term that already has
        # later grade rows and it will report integrity FAIL by design.
        integrity = {
            "unattributed_grade_rows": self.unattributed_grade_rows,
            "bucket_sum_mismatch_rows": self.bucket_sum_mismatch_rows,
            "rows_at_or_after_term": self.rows_at_or_after_term,
            "stale_cache": self.stale_cache,
            "non_tampa_section_count": self.non_tampa_section_count,
        }
        integrity_ok = failure_section_count == 0 and not any(integrity.values())
        verdict = "PASS" if integrity_ok else "FAIL"

        return {
            "gate": GATE,
            "term": self.term,
            "observed_at_utc": self.observed_at_utc,
            "environment": self.environment,
            "snapshot": {
                "section_count": self.section_count,
                "represented_course_count": self.represented_course_count,
                "cache_row_count": self.cache_row_count,
                "cache_refreshed_at_min": self.cache_refreshed_at_min,
                "cache_refreshed_at_max": self.cache_refreshed_at_max,
                "grade_row_count": self.grade_row_count,
                "grade_ingested_at_max": self.grade_ingested_at_max,
                "evidence_grade_ingested_at_max": self.evidence_grade_ingested_at_max,
                "non_tampa_section_count": self.non_tampa_section_count,
            },
            "grade_rows_by_term": [
                {
                    "term": t.term,
                    "rows": t.rows,
                    "courses": t.courses,
                    "total_grades_sum": t.total_grades_sum,
                    "sources": list(t.sources),
                    "source_hash_count": t.source_hash_count,
                    "ingested_at_min": t.ingested_at_min,
                    "ingested_at_max": t.ingested_at_max,
                }
                for t in self.grade_rows_by_term
            ],
            "window": self.window,
            "sections_by_state": sections_by_state,
            "courses_by_state": courses_by_state,
            "integrity": integrity,
            "evidence_backed_sections": evidence_backed_sections,
            "exception_sections_by_reason": dict(sorted(exception_sections_by_reason.items())),
            "exceptions": exceptions,
            "verdicts": {"integrity": verdict, "d21_grade_coverage": verdict},
        }


def _counts_by_state(sections: Sequence[SectionState]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for s in sections:
        counts[s.state.value] += 1
    return dict(sorted(counts.items()))


def _course_counts_by_state(sections: Sequence[SectionState]) -> dict[str, int]:
    """Distinct (subject, course_number) keys with at least one section in that
    state. Non-exclusive: a course whose sections span more than one state is
    counted once under each state it actually has a section in."""
    keys_by_state: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for s in sections:
        keys_by_state[s.state.value].add((s.subject, s.course_number))
    return {state: len(keys) for state, keys in sorted(keys_by_state.items())}


def classify_section(
    *,
    crn: str,
    subject: str,
    course_number: str,
    cache_row: SectionRankingCache | None,
    key_evidence: CourseKeyEvidence,
) -> SectionState:
    """Classify one section under D-21.

    evidence_backed: score_source course/instructor_course, effective_n > 0, key
    has attributed rows with A-F sum > 0, and the cached total_grade_count
    reconciles (course: exactly equal to the key's persisted total_grades sum;
    instructor_course: a positive subset of it, i.e. in (0, key sum]).

    exception_non_letter_grade: score_source course, effective_n == 0, key rows
    exist with A-F sum == 0 and total_grades sum > 0 (a non-letter-grade course,
    e.g. S/U or pass/fail), and the cached total reconciles to the key sum.

    exception_no_rows: score_source subject (effective_n > 0, subject-level) or
    global (effective_n == 0), and the key has no attributed rows at all.

    Everything else is a named integrity failure: unbacked_course_claim (a
    course/instructor_course claim with no attributed rows at all, regardless of
    effective_n), raw_total_mismatch (rows exist and reconciliation fails),
    history_not_used (a subject/global fallback used despite the key itself
    having attributed rows, at the effective_n>0 fallback threshold),
    global_nonzero_effective_n (a global row claiming effective_n > 0, which
    D-20 forbids), or unclassified (an unknown score_source, a subject row with
    effective_n <= 0 -- D-21 defines no subject-level non-letter-grade
    exception -- or any other combination this decision tree does not name;
    never silently absorbed into evidence_backed or an exception).
    """
    row_count = key_evidence.row_count
    total_grades_sum = key_evidence.total_sum
    historical_term_codes = tuple(sorted(key_evidence.term_codes))
    sources = tuple(sorted(key_evidence.sources))

    if cache_row is None:
        return SectionState(
            crn=crn,
            subject=subject,
            course_number=course_number,
            state=EvidenceState.missing_cache_row,
            score_source=None,
            effective_n=None,
            row_count=row_count,
            total_grades_sum=total_grades_sum,
            historical_term_codes=historical_term_codes,
            sources=sources,
        )

    score_source = cache_row.score_source
    effective_n = cache_row.effective_n
    historical_analytics = cache_row.historical_analytics or {}
    cached_total = historical_analytics.get("total_grade_count")

    def make(state: EvidenceState, reason_category: str | None = None) -> SectionState:
        reason_note = None
        if reason_category == "no_rows":
            reason_note = NO_ROWS_REASON_NOTE
        elif reason_category == "non_letter_grade":
            reason_note = NON_LETTER_GRADE_REASON_NOTE
        return SectionState(
            crn=crn,
            subject=subject,
            course_number=course_number,
            state=state,
            score_source=score_source,
            effective_n=effective_n,
            reason_category=reason_category,
            reason_note=reason_note,
            row_count=row_count,
            total_grades_sum=total_grades_sum,
            historical_term_codes=historical_term_codes,
            sources=sources,
            cached_total_grade_count=cached_total,
        )

    if score_source not in _VALID_SCORE_SOURCES:
        return make(EvidenceState.unclassified)

    if effective_n is None:
        return make(EvidenceState.unclassified)

    if score_source in _COURSE_BACKED_SOURCES:
        if not key_evidence.has_rows:
            # A course/instructor_course claim with no attributed rows backing it
            # at all -- unbacked regardless of what effective_n happens to say.
            return make(EvidenceState.unbacked_course_claim)

        if effective_n > 0:
            if key_evidence.af_sum <= 0:
                # Mathematically unreachable given effective_n = min(effective_grade_n,
                # effective_withdrawal_n) -- a zero A-F sum forces effective_grade_n = 0,
                # hence effective_n = 0. Documented rather than silently trusted if a
                # stale/inconsistent cache ever produces it.
                return make(EvidenceState.unclassified)
            if score_source == ScoreSource.course.value:
                matches = cached_total == key_evidence.total_sum
            else:  # instructor_course: a positive subset of the key's own total
                matches = cached_total is not None and 0 < cached_total <= key_evidence.total_sum
            if matches:
                return make(EvidenceState.evidence_backed)
            return make(EvidenceState.raw_total_mismatch)

        # effective_n == 0, rows exist.
        is_non_letter_grade_claim = (
            score_source == ScoreSource.course.value
            and key_evidence.af_sum == 0
            and key_evidence.total_sum > 0
        )
        if is_non_letter_grade_claim:
            matches = cached_total == key_evidence.total_sum
            if matches:
                return make(
                    EvidenceState.exception_non_letter_grade,
                    reason_category="non_letter_grade",
                )
            return make(EvidenceState.raw_total_mismatch)
        return make(EvidenceState.unclassified)

    if score_source == ScoreSource.subject.value:
        if effective_n <= 0:
            # D-21 defines no subject-level non-letter-grade exception.
            return make(EvidenceState.unclassified)
        if key_evidence.has_rows:
            return make(EvidenceState.history_not_used)
        return make(EvidenceState.exception_no_rows, reason_category="no_rows")

    # global
    if effective_n > 0:
        return make(EvidenceState.global_nonzero_effective_n)
    if key_evidence.has_rows:
        return make(EvidenceState.history_not_used)
    return make(EvidenceState.exception_no_rows, reason_category="no_rows")


def _fetch_sections(session: Session, term: str) -> list[Any]:
    stmt = (
        select(Section.id, Section.crn, Section.campus, Course.subject, Course.number)
        .join(Course, Section.course_id == Course.id)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == term)
        .order_by(Course.subject, Course.number, Section.crn)
    )
    return list(session.execute(stmt).all())


def _fetch_cache_rows(session: Session, term: str) -> dict[int, SectionRankingCache]:
    stmt = select(SectionRankingCache).where(SectionRankingCache.term == term)
    return {row.section_id: row for row in session.scalars(stmt)}


def _fetch_grade_rows(session: Session) -> list[Any]:
    stmt = (
        select(
            GradeDistribution.a_count,
            GradeDistribution.b_count,
            GradeDistribution.c_count,
            GradeDistribution.d_count,
            GradeDistribution.f_count,
            GradeDistribution.i_count,
            GradeDistribution.s_count,
            GradeDistribution.u_count,
            GradeDistribution.w_count,
            GradeDistribution.other_count,
            GradeDistribution.total_grades,
            GradeDistribution.course_id,
            GradeDistribution.source,
            GradeDistribution.source_hash,
            GradeDistribution.ingested_at,
            Term.banner_code,
            Course.subject,
            Course.number,
        )
        .join(Term, GradeDistribution.term_id == Term.id)
        .outerjoin(Course, GradeDistribution.course_id == Course.id)
    )
    return list(session.execute(stmt).all())


def _aggregate_grade_rows(
    grade_rows: Sequence[Any], *, before_term: str
) -> tuple[
    dict[tuple[str, str], CourseKeyEvidence],
    tuple[TermGradeStats, ...],
    dict[str, Any],
    int,
    int,
    datetime | None,
    int,
    datetime | None,
]:
    """Roll up every fetched GradeDistribution row (one statement, no term filter)
    into per-course-key evidence, per-term reporting and the D-21 window counts.

    Returns (key_evidence, grade_rows_by_term, window, unattributed_grade_rows,
    bucket_sum_mismatch_rows, overall_ingested_at_max, rows_at_or_after_term,
    evidence_ingested_at_max). ``overall_ingested_at_max`` is the newest
    ingested_at over every fetched row, including rows at or after ``before_term``
    (unrelated to any cached score). ``evidence_ingested_at_max`` is the newest
    ingested_at over only the rows that pass the same ``term_code < before_term``
    filter src/easy_a/analytics/queries.py applies when building the cached
    scores -- i.e. the rows that actually feed ``key_evidence`` -- so it deliberately
    includes historical terms outside the D21_WINDOW_TERMS reporting window (e.g.
    the 202408 pilot) because those rows do feed the cache.
    """
    key_totals: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"row_count": 0, "af_sum": 0, "total_sum": 0, "term_codes": set(), "sources": set()}
    )
    term_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "rows": 0,
            "courses": set(),
            "total_grades_sum": 0,
            "sources": set(),
            "source_hashes": set(),
            "ingested_at_min": None,
            "ingested_at_max": None,
        }
    )
    window_counts: dict[str, int] = dict.fromkeys(D21_WINDOW_TERMS, 0)
    checked_empty_counts: dict[str, int] = dict.fromkeys(D21_CHECKED_EMPTY_TERMS, 0)
    outside_window_rows = 0
    unattributed_grade_rows = 0
    bucket_sum_mismatch_rows = 0
    rows_at_or_after_term = 0
    overall_ingested_at_max: datetime | None = None
    evidence_ingested_at_max: datetime | None = None

    for (
        a_count,
        b_count,
        c_count,
        d_count,
        f_count,
        i_count,
        s_count,
        u_count,
        w_count,
        other_count,
        total_grades,
        course_id,
        source,
        source_hash,
        ingested_at,
        term_code,
        subject,
        number,
    ) in grade_rows:
        af_sum = a_count + b_count + c_count + d_count + f_count
        bucket_sum = af_sum + i_count + s_count + u_count + w_count + other_count
        if bucket_sum != total_grades:
            bucket_sum_mismatch_rows += 1
        if course_id is None:
            unattributed_grade_rows += 1

        if overall_ingested_at_max is None or ingested_at > overall_ingested_at_max:
            overall_ingested_at_max = ingested_at

        if term_code >= before_term:
            rows_at_or_after_term += 1
            continue

        if evidence_ingested_at_max is None or ingested_at > evidence_ingested_at_max:
            evidence_ingested_at_max = ingested_at

        if course_id is not None and subject is not None and number is not None:
            key = (subject, number)
            entry = key_totals[key]
            entry["row_count"] += 1
            entry["af_sum"] += af_sum
            entry["total_sum"] += total_grades
            entry["term_codes"].add(term_code)
            entry["sources"].add(source)

        term_entry = term_totals[term_code]
        term_entry["rows"] += 1
        if subject is not None and number is not None:
            term_entry["courses"].add((subject, number))
        term_entry["total_grades_sum"] += total_grades
        term_entry["sources"].add(source)
        term_entry["source_hashes"].add(source_hash)
        if term_entry["ingested_at_min"] is None or ingested_at < term_entry["ingested_at_min"]:
            term_entry["ingested_at_min"] = ingested_at
        if term_entry["ingested_at_max"] is None or ingested_at > term_entry["ingested_at_max"]:
            term_entry["ingested_at_max"] = ingested_at

        if term_code in window_counts:
            window_counts[term_code] += 1
        elif term_code in checked_empty_counts:
            checked_empty_counts[term_code] += 1
        else:
            outside_window_rows += 1

    key_evidence = {
        key: CourseKeyEvidence(
            row_count=entry["row_count"],
            af_sum=entry["af_sum"],
            total_sum=entry["total_sum"],
            term_codes=frozenset(entry["term_codes"]),
            sources=frozenset(entry["sources"]),
        )
        for key, entry in key_totals.items()
    }

    grade_rows_by_term = tuple(
        TermGradeStats(
            term=term_code,
            rows=entry["rows"],
            courses=len(entry["courses"]),
            total_grades_sum=entry["total_grades_sum"],
            sources=tuple(sorted(entry["sources"])),
            source_hash_count=len(entry["source_hashes"]),
            ingested_at_min=(
                entry["ingested_at_min"].isoformat() if entry["ingested_at_min"] else None
            ),
            ingested_at_max=(
                entry["ingested_at_max"].isoformat() if entry["ingested_at_max"] else None
            ),
        )
        for term_code, entry in sorted(term_totals.items())
    )

    window = {
        "window_terms": window_counts,
        "checked_empty_terms": checked_empty_counts,
        "outside_window_rows": outside_window_rows,
    }

    return (
        key_evidence,
        grade_rows_by_term,
        window,
        unattributed_grade_rows,
        bucket_sum_mismatch_rows,
        overall_ingested_at_max,
        rows_at_or_after_term,
        evidence_ingested_at_max,
    )


def collect_inventory(session: Session, term: str | int) -> Inventory:
    """Read the whole D-21 inventory for one term in a fixed, small number of
    batched statements (never one query per course). Issues no writes."""
    normalized_term = normalize_banner_term_code(term)
    bind = session.get_bind()
    if getattr(getattr(bind, "dialect", None), "name", None) == "postgresql":
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))

    section_rows = _fetch_sections(session, normalized_term)
    cache_by_section_id = _fetch_cache_rows(session, normalized_term)
    grade_rows = _fetch_grade_rows(session)

    (
        key_evidence,
        grade_rows_by_term,
        window,
        unattributed_grade_rows,
        bucket_sum_mismatch_rows,
        grade_ingested_at_max_dt,
        rows_at_or_after_term,
        evidence_ingested_at_max_dt,
    ) = _aggregate_grade_rows(grade_rows, before_term=normalized_term)

    sections: list[SectionState] = []
    non_tampa_count = 0
    represented_courses: set[tuple[str, str]] = set()
    for section_id, crn, campus, subject, number in section_rows:
        represented_courses.add((subject, number))
        if not same_campus(campus, SUPPORTED_CAMPUS):
            non_tampa_count += 1
        cache_row = cache_by_section_id.get(section_id)
        evidence = key_evidence.get((subject, number), CourseKeyEvidence())
        sections.append(
            classify_section(
                crn=crn,
                subject=subject,
                course_number=number,
                cache_row=cache_row,
                key_evidence=evidence,
            )
        )

    cache_refreshed_ats = [row.refreshed_at for row in cache_by_section_id.values()]
    cache_refreshed_at_min_dt = min(cache_refreshed_ats) if cache_refreshed_ats else None
    cache_refreshed_at_max_dt = max(cache_refreshed_ats) if cache_refreshed_ats else None

    # stale_cache answers "has the evidence used by the cache changed since the cache
    # was last refreshed?" -- so it compares against evidence_ingested_at_max_dt (rows
    # that actually feed key_evidence), not grade_ingested_at_max_dt (every fetched
    # row, including any stamped at or after the inventoried term, which never feeds
    # a cached score and would otherwise cause both false positives and false
    # negatives here) (WR-01).
    stale_cache = bool(
        cache_refreshed_at_max_dt is not None
        and evidence_ingested_at_max_dt is not None
        and cache_refreshed_at_max_dt < evidence_ingested_at_max_dt
    )

    engine = bind if isinstance(bind, Engine) else None
    environment = _environment_label(engine) if engine is not None else "unknown"

    return Inventory(
        term=normalized_term,
        observed_at_utc=datetime.now(UTC).isoformat(),
        environment=environment,
        sections=tuple(sections),
        represented_course_count=len(represented_courses),
        cache_row_count=len(cache_by_section_id),
        cache_refreshed_at_min=(
            cache_refreshed_at_min_dt.isoformat() if cache_refreshed_at_min_dt else None
        ),
        cache_refreshed_at_max=(
            cache_refreshed_at_max_dt.isoformat() if cache_refreshed_at_max_dt else None
        ),
        grade_row_count=len(grade_rows),
        grade_ingested_at_max=(
            grade_ingested_at_max_dt.isoformat() if grade_ingested_at_max_dt else None
        ),
        evidence_grade_ingested_at_max=(
            evidence_ingested_at_max_dt.isoformat() if evidence_ingested_at_max_dt else None
        ),
        non_tampa_section_count=non_tampa_count,
        grade_rows_by_term=grade_rows_by_term,
        window=window,
        unattributed_grade_rows=unattributed_grade_rows,
        bucket_sum_mismatch_rows=bucket_sum_mismatch_rows,
        rows_at_or_after_term=rows_at_or_after_term,
        stale_cache=stale_cache,
    )


def write_atomic(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically: temp file in the same directory,
    then ``os.replace``. An interrupted or failed write leaves the previous file
    (or none) in place, never a truncated one."""
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=directory, suffix=".tmp")
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


def render_exceptions_markdown(inventory: Inventory) -> str:
    """Deterministic Markdown: header, counts by reason_category, one row per
    course key (section count, CRNs, score_source, effective_n, reason_category),
    then the fixed reason-note legend."""
    reason_counts: dict[str, int] = defaultdict(int)
    grouped: dict[tuple[str, str], list[SectionState]] = defaultdict(list)
    for s in inventory.sections:
        if s.state in EXCEPTION_STATES:
            if s.reason_category:
                reason_counts[s.reason_category] += 1
            grouped[(s.subject, s.course_number)].append(s)

    lines = [
        f"# D-21 Grade-Coverage Exceptions -- term {inventory.term}",
        "",
        f"Observed at: {inventory.observed_at_utc}",
        "",
        "## Counts by reason",
        "",
    ]
    for reason, count in sorted(reason_counts.items()):
        lines.append(f"- {reason}: {count}")
    lines.extend(
        [
            "",
            "## Exceptions by course key",
            "",
            "| Subject | Course Number | Section Count | CRNs | Score Source | "
            "Effective N | Reason Category |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for (subject, number), rows in sorted(grouped.items()):
        rows_sorted = sorted(rows, key=lambda s: s.crn)
        crns = ", ".join(row.crn for row in rows_sorted)
        first = rows_sorted[0]
        lines.append(
            f"| {subject} | {number} | {len(rows_sorted)} | {crns} | "
            f"{first.score_source} | {first.effective_n} | {first.reason_category} |"
        )
    lines.extend(
        [
            "",
            "## Reason-note legend",
            "",
            f"- no_rows: {NO_ROWS_REASON_NOTE}",
            f"- non_letter_grade: {NON_LETTER_GRADE_REASON_NOTE}",
            "",
        ]
    )
    return "\n".join(lines)


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


def _not_measured(*, term: str, environment: str) -> dict[str, Any]:
    return {
        "gate": GATE,
        "term": term,
        "observed_at_utc": datetime.now(UTC).isoformat(),
        "environment": environment,
        "snapshot": None,
        "grade_rows_by_term": [],
        "window": {},
        "sections_by_state": {},
        "courses_by_state": {},
        "integrity": {},
        "evidence_backed_sections": 0,
        "exception_sections_by_reason": {},
        "exceptions": [],
        "verdicts": {"integrity": "NOT MEASURED", "d21_grade_coverage": "NOT MEASURED"},
    }


def _term_code(value: str) -> str:
    try:
        return normalize_banner_term_code(value)
    except TermParseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only, full-term D-21 grade-coverage inventory (REQ-GRADES-01). "
            "Classifies every stored section as evidence_backed, a listed "
            "source-limited exception, or a named integrity failure. Never writes "
            "to the database, never fetches or imports grades. Exit codes: 0 both "
            "verdicts PASS, 1 otherwise, 3 NOT MEASURED (database unreachable)."
        )
    )
    parser.add_argument(
        "--term",
        type=_term_code,
        default=DEFAULT_TERM,
        help=f"Banner term code to inventory. Default: {DEFAULT_TERM}.",
    )
    parser.add_argument(
        "--exceptions-md",
        type=Path,
        default=None,
        help="Optional path to write a deterministic Markdown exceptions report to.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    engine = get_engine()
    environment = _environment_label(engine)
    try:
        with Session(engine) as session:
            try:
                inventory = collect_inventory(session, args.term)
            except SQLAlchemyError:
                print(json.dumps(_not_measured(term=args.term, environment=environment)))
                return 3
    finally:
        engine.dispose()

    output = inventory.to_dict()
    print(json.dumps(output))

    if args.exceptions_md is not None:
        write_atomic(args.exceptions_md, render_exceptions_markdown(inventory))

    verdicts = output["verdicts"]
    if verdicts["integrity"] == "PASS" and verdicts["d21_grade_coverage"] == "PASS":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
