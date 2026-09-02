from __future__ import annotations

from dataclasses import dataclass
from math import pow


@dataclass(frozen=True)
class GradeCounts:
    a_count: float = 0.0
    b_count: float = 0.0
    c_count: float = 0.0
    d_count: float = 0.0
    f_count: float = 0.0
    i_count: float = 0.0
    s_count: float = 0.0
    u_count: float = 0.0
    w_count: float = 0.0
    other_count: float = 0.0
    total_grades: float = 0.0


@dataclass(frozen=True)
class GradeObservation:
    term_id: int
    term_code: str
    crn: str
    counts: GradeCounts
    mapped_instructor: bool = False


@dataclass(frozen=True)
class RecencyConfig:
    enabled: bool = False
    half_life_terms: float = 4.0


@dataclass(frozen=True)
class HistoricalGradeAggregate:
    weighted_counts: GradeCounts
    completed_grade_count: int
    total_grade_count: int
    withdrawal_count: int
    effective_grade_n: float
    effective_withdrawal_n: float
    effective_n: float
    section_count: int
    term_count: int
    mapped_instructor_section_count: int

    @property
    def has_grade_evidence(self) -> bool:
        return self.effective_grade_n > 0

    @property
    def has_withdrawal_evidence(self) -> bool:
        return self.effective_withdrawal_n > 0

    @property
    def has_evidence(self) -> bool:
        return self.has_grade_evidence or self.has_withdrawal_evidence


EMPTY_AGGREGATE = HistoricalGradeAggregate(
    weighted_counts=GradeCounts(),
    completed_grade_count=0,
    total_grade_count=0,
    withdrawal_count=0,
    effective_grade_n=0.0,
    effective_withdrawal_n=0.0,
    effective_n=0.0,
    section_count=0,
    term_count=0,
    mapped_instructor_section_count=0,
)


def completed_grade_count(counts: GradeCounts) -> float:
    return counts.a_count + counts.b_count + counts.c_count + counts.d_count + counts.f_count


def grade_favorability(counts: GradeCounts) -> float | None:
    completed_count = completed_grade_count(counts)
    if completed_count <= 0:
        return None

    weighted_grade_points = (
        (4.0 * counts.a_count) + (3.0 * counts.b_count) + (2.0 * counts.c_count) + counts.d_count
    )
    return weighted_grade_points / (4.0 * completed_count)


def withdrawal_rate(counts: GradeCounts) -> float | None:
    if counts.total_grades <= 0:
        return None
    return counts.w_count / counts.total_grades


def aggregate_grade_observations(
    observations: list[GradeObservation],
    recency: RecencyConfig | None = None,
) -> HistoricalGradeAggregate:
    if not observations:
        return EMPTY_AGGREGATE

    recency_config = recency or RecencyConfig()
    term_weights = _term_weights(observations, recency_config)
    weighted_counts = GradeCounts()
    completed_actual = 0
    total_actual = 0
    withdrawal_actual = 0
    section_keys: set[tuple[int, str]] = set()
    term_ids: set[int] = set()
    mapped_instructor_section_keys: set[tuple[int, str]] = set()

    for observation in observations:
        weight = term_weights[observation.term_code]
        weighted_counts = _add_weighted_counts(weighted_counts, observation.counts, weight)
        completed_actual += int(completed_grade_count(observation.counts))
        total_actual += int(observation.counts.total_grades)
        withdrawal_actual += int(observation.counts.w_count)
        section_key = (observation.term_id, observation.crn)
        section_keys.add(section_key)
        term_ids.add(observation.term_id)
        if observation.mapped_instructor:
            mapped_instructor_section_keys.add(section_key)

    effective_grade_n = completed_grade_count(weighted_counts)
    effective_withdrawal_n = weighted_counts.total_grades
    effective_n = min(effective_grade_n, effective_withdrawal_n)

    return HistoricalGradeAggregate(
        weighted_counts=weighted_counts,
        completed_grade_count=completed_actual,
        total_grade_count=total_actual,
        withdrawal_count=withdrawal_actual,
        effective_grade_n=effective_grade_n,
        effective_withdrawal_n=effective_withdrawal_n,
        effective_n=effective_n,
        section_count=len(section_keys),
        term_count=len(term_ids),
        mapped_instructor_section_count=len(mapped_instructor_section_keys),
    )


def _term_weights(
    observations: list[GradeObservation],
    recency: RecencyConfig,
) -> dict[str, float]:
    if not recency.enabled:
        return {observation.term_code: 1.0 for observation in observations}
    if recency.half_life_terms <= 0:
        raise ValueError("recency half_life_terms must be positive.")

    ordered_terms = sorted({observation.term_code for observation in observations})
    newest_index = len(ordered_terms) - 1
    return {
        term_code: pow(0.5, (newest_index - index) / recency.half_life_terms)
        for index, term_code in enumerate(ordered_terms)
    }


def _add_weighted_counts(left: GradeCounts, right: GradeCounts, weight: float) -> GradeCounts:
    return GradeCounts(
        a_count=left.a_count + (right.a_count * weight),
        b_count=left.b_count + (right.b_count * weight),
        c_count=left.c_count + (right.c_count * weight),
        d_count=left.d_count + (right.d_count * weight),
        f_count=left.f_count + (right.f_count * weight),
        i_count=left.i_count + (right.i_count * weight),
        s_count=left.s_count + (right.s_count * weight),
        u_count=left.u_count + (right.u_count * weight),
        w_count=left.w_count + (right.w_count * weight),
        other_count=left.other_count + (right.other_count * weight),
        total_grades=left.total_grades + (right.total_grades * weight),
    )
