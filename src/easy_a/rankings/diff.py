"""Read-only D-04 ranking diff: stored cache scores versus a fresh recomputation.

Phase 10 puts the instructor-course retune live only after a diff review (PROJECT.md D-04):
report which sections changed score and rank and by how much, and confirm that course-level
scores are unchanged. This module reads the stored ``section_rankings`` score fields,
recomputes the same fields with the scoring code that ``refresh_section_rankings`` uses, and
compares the two.

Callers own the transaction: nothing here writes, flushes or commits. Output carries only CRNs,
course keys and derived numbers (D-19): no per-CRN grade buckets, no instructor names.

Verdicts (T-10-10): ``identical`` and ``course_level_invariant`` are derived from the same
fields the report shows, so a reported anomaly can never read as a pass.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.analytics.scoring import ScoreConfig
from easy_a.common.terms import normalize_banner_term_code

# The five fields whose change makes a section "changed". The mapped instructor section count
# is deliberately not one of them: it describes the evidence, not the score a student sees.
SCORE_FIELDS: tuple[str, ...] = (
    "easiness_score",
    "smoothed_withdrawal_rate",
    "effective_n",
    "confidence_label",
    "score_source",
)

# Upper bounds (inclusive) of the absolute easiness-delta buckets; the last bucket is open.
_DELTA_BUCKET_BOUNDS: tuple[tuple[str, float], ...] = (
    ("(0,0.25]", 0.25),
    ("(0.25,0.5]", 0.5),
    ("(0.5,1]", 1.0),
    ("(1,2]", 2.0),
)
_DELTA_BUCKET_ORDER: tuple[str, ...] = (
    "0",
    "(0,0.25]",
    "(0.25,0.5]",
    "(0.5,1]",
    "(1,2]",
    ">2",
)

_INSTRUCTOR_COURSE = ScoreSource.instructor_course.value


@dataclass(frozen=True)
class ScoreRow:
    """The score-bearing slice of one section, from either side of the diff."""

    crn: str
    subject: str
    course_number: str
    easiness_score: float
    smoothed_withdrawal_rate: float
    effective_n: float
    confidence_label: str
    score_source: str
    mapped_instructor_section_count: int


@dataclass(frozen=True)
class RankingDiff:
    total_before: int
    total_after: int
    missing_in_after: tuple[str, ...]
    extra_in_after: tuple[str, ...]
    changed: int
    changes: tuple[dict[str, Any], ...]
    transitions: dict[str, int]
    abs_delta: dict[str, float]
    abs_delta_buckets: dict[str, int]
    rank_shift: dict[str, float]
    top_changes: tuple[dict[str, Any], ...]
    course_level_violations: tuple[dict[str, Any], ...]
    informational_changes: int

    @property
    def identical(self) -> bool:
        """Identity sets equal and every score field equal for every section."""
        return not self.missing_in_after and not self.extra_in_after and self.changed == 0

    @property
    def course_level_invariant(self) -> bool:
        """Identity sets equal and no course/subject/global row moved on either side."""
        return (
            not self.missing_in_after
            and not self.extra_in_after
            and not self.course_level_violations
        )

    def to_dict(self, *, include_changes: bool = False) -> dict[str, Any]:
        output: dict[str, Any] = {
            "total_before": self.total_before,
            "total_after": self.total_after,
            "missing_in_after": list(self.missing_in_after),
            "extra_in_after": list(self.extra_in_after),
            "changed": self.changed,
            "transitions": dict(self.transitions),
            "abs_delta": dict(self.abs_delta),
            "abs_delta_buckets": dict(self.abs_delta_buckets),
            "rank_shift": dict(self.rank_shift),
            "top_changes": [dict(record) for record in self.top_changes],
            "course_level_violations": [dict(record) for record in self.course_level_violations],
            "informational_changes": self.informational_changes,
            "identical": self.identical,
            "course_level_invariant": self.course_level_invariant,
        }
        if include_changes:
            output["changes"] = [dict(record) for record in self.changes]
        return output


def stored_score_rows(session: Session, term: str | int) -> dict[str, ScoreRow]:
    """Score fields exactly as stored in the section_rankings cache for a term, keyed by CRN."""
    from easy_a.rankings.cache import SectionRankingCache

    normalized_term = normalize_banner_term_code(term)
    rows: dict[str, ScoreRow] = {}
    for cache_row in session.scalars(
        select(SectionRankingCache)
        .where(SectionRankingCache.term == normalized_term)
        .order_by(
            SectionRankingCache.subject,
            SectionRankingCache.course_number,
            SectionRankingCache.crn,
        )
    ):
        historical = cache_row.historical_analytics or {}
        rows[cache_row.crn] = ScoreRow(
            crn=cache_row.crn,
            subject=cache_row.subject,
            course_number=cache_row.course_number,
            easiness_score=cache_row.easiness_score,
            smoothed_withdrawal_rate=cache_row.smoothed_withdrawal_rate,
            effective_n=cache_row.effective_n,
            confidence_label=cache_row.confidence_label,
            score_source=cache_row.score_source,
            mapped_instructor_section_count=int(
                historical.get("mapped_instructor_section_count", 0)
            ),
        )
    return rows


def computed_score_rows(
    session: Session,
    term: str | int,
    config: ScoreConfig | None = None,
) -> dict[str, ScoreRow]:
    """Score fields recomputed now, over the section selection refresh_section_rankings uses."""
    # Imported lazily for the same models/rankings import-cycle reason as cache.py.
    from easy_a.analytics.queries import get_term_section_historical_analytics
    from easy_a.models.core import Course, Term
    from easy_a.models.sections import Section

    normalized_term = normalize_banner_term_code(term)
    section_rows = list(
        session.execute(
            select(Section.crn, Course.subject, Course.number)
            .join(Course, Section.course_id == Course.id)
            .join(Term, Section.term_id == Term.id)
            .where(Term.banner_code == normalized_term, Section.removed_at.is_(None))
            .order_by(Course.subject, Course.number, Section.crn)
        ).all()
    )
    course_keys = sorted({(subject, number) for _, subject, number in section_rows})
    analytics_by_crn = {
        row.crn: row.stats
        for row in get_term_section_historical_analytics(
            session,
            term_code=normalized_term,
            course_keys=course_keys,
            config=config,
        )
    }
    rows: dict[str, ScoreRow] = {}
    for crn, subject, number in section_rows:
        stats = analytics_by_crn[crn]
        rows[crn] = ScoreRow(
            crn=crn,
            subject=subject,
            course_number=number,
            easiness_score=stats.easiness_score,
            smoothed_withdrawal_rate=stats.withdrawal_rate_smoothed,
            effective_n=stats.effective_n,
            confidence_label=stats.confidence_label.value,
            score_source=stats.score_source.value,
            mapped_instructor_section_count=stats.mapped_instructor_section_count,
        )
    return rows


def rank_rows(rows: Iterable[ScoreRow]) -> dict[str, int]:
    """1-based rank by easiness descending, then subject, course_number, crn ascending."""
    ordered = sorted(
        rows,
        key=lambda row: (-row.easiness_score, row.subject, row.course_number, row.crn),
    )
    return {row.crn: index for index, row in enumerate(ordered, start=1)}


def diff_score_rows(
    before: Mapping[str, ScoreRow],
    after: Mapping[str, ScoreRow],
    *,
    top: int = 50,
) -> RankingDiff:
    """Compare two score-row sets keyed by CRN and quantify every difference."""
    missing_in_after = tuple(sorted(set(before) - set(after)))
    extra_in_after = tuple(sorted(set(after) - set(before)))
    common = sorted(set(before) & set(after))
    rank_before = rank_rows(before.values())
    rank_after = rank_rows(after.values())

    changes: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    transitions: dict[str, int] = {}
    informational = 0
    abs_deltas: list[float] = []
    rank_shifts: list[int] = []

    for crn in common:
        old = before[crn]
        new = after[crn]
        delta = new.easiness_score - old.easiness_score
        abs_deltas.append(abs(delta))
        rank_shifts.append(abs(rank_before[crn] - rank_after[crn]))
        changed_fields = [
            name for name in SCORE_FIELDS if getattr(old, name) != getattr(new, name)
        ]
        if not changed_fields:
            if old.mapped_instructor_section_count != new.mapped_instructor_section_count:
                informational += 1
            continue

        record: dict[str, Any] = {
            "crn": crn,
            "subject": new.subject,
            "course_number": new.course_number,
            "changed_fields": changed_fields,
            "score_source_before": old.score_source,
            "score_source_after": new.score_source,
            "easiness_before": old.easiness_score,
            "easiness_after": new.easiness_score,
            "delta": delta,
            "rank_before": rank_before[crn],
            "rank_after": rank_after[crn],
            "effective_n_before": old.effective_n,
            "effective_n_after": new.effective_n,
        }
        changes.append(record)
        if old.score_source != new.score_source:
            key = f"{old.score_source}->{new.score_source}"
            transitions[key] = transitions.get(key, 0) + 1
        if old.score_source != _INSTRUCTOR_COURSE and new.score_source != _INSTRUCTOR_COURSE:
            violations.append(
                {
                    "crn": crn,
                    "subject": new.subject,
                    "course_number": new.course_number,
                    "score_source_before": old.score_source,
                    "score_source_after": new.score_source,
                    "changed_fields": changed_fields,
                }
            )

    top_changes = sorted(changes, key=lambda record: (-abs(record["delta"]), record["crn"]))[
        : max(top, 0)
    ]
    return RankingDiff(
        total_before=len(before),
        total_after=len(after),
        missing_in_after=missing_in_after,
        extra_in_after=extra_in_after,
        changed=len(changes),
        changes=tuple(changes),
        transitions=dict(sorted(transitions.items())),
        abs_delta=_delta_stats(abs_deltas),
        abs_delta_buckets=_delta_buckets(abs_deltas),
        rank_shift={
            "max": float(max(rank_shifts)) if rank_shifts else 0.0,
            "median": float(statistics.median(rank_shifts)) if rank_shifts else 0.0,
        },
        top_changes=tuple(top_changes),
        course_level_violations=tuple(violations),
        informational_changes=informational,
    )


def _delta_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"max": 0.0, "mean": 0.0, "median": 0.0, "p90": 0.0}
    ordered = sorted(values)
    # Nearest-rank 90th percentile: the smallest value with at least 90% of values at or below it.
    p90 = ordered[max(math.ceil(0.9 * len(ordered)) - 1, 0)]
    return {
        "max": ordered[-1],
        "mean": statistics.fmean(ordered),
        "median": statistics.median(ordered),
        "p90": p90,
    }


def _delta_buckets(values: list[float]) -> dict[str, int]:
    buckets = dict.fromkeys(_DELTA_BUCKET_ORDER, 0)
    for value in values:
        if value == 0:
            buckets["0"] += 1
            continue
        for label, upper in _DELTA_BUCKET_BOUNDS:
            if value <= upper:
                buckets[label] += 1
                break
        else:
            buckets[">2"] += 1
    return buckets
