from __future__ import annotations

from dataclasses import dataclass, field

from easy_a.analytics.confidence import (
    Confidence,
    ConfidenceLabel,
    PriorLevel,
    ScoreSource,
    confidence_label_for,
)
from easy_a.analytics.grades import (
    HistoricalGradeAggregate,
    RecencyConfig,
    grade_favorability,
    withdrawal_rate,
)

DEFAULT_GRADE_PRIOR_STRENGTH = 60.0
DEFAULT_WITHDRAWAL_PRIOR_STRENGTH = 60.0
DEFAULT_GRADE_WEIGHT = 0.80
DEFAULT_NON_WITHDRAWAL_WEIGHT = 0.20
DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N = 60.0
DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR = 0.75
DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR = 0.10


@dataclass(frozen=True)
class ScoreConfig:
    grade_prior_strength: float = DEFAULT_GRADE_PRIOR_STRENGTH
    withdrawal_prior_strength: float = DEFAULT_WITHDRAWAL_PRIOR_STRENGTH
    grade_weight: float = DEFAULT_GRADE_WEIGHT
    non_withdrawal_weight: float = DEFAULT_NON_WITHDRAWAL_WEIGHT
    instructor_course_min_effective_n: float = DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N
    recency: RecencyConfig = field(default_factory=RecencyConfig)


@dataclass(frozen=True)
class HistoricalOutcomeStats:
    grade_favorability_raw: float | None
    grade_favorability_smoothed: float
    withdrawal_rate_raw: float | None
    withdrawal_rate_smoothed: float
    easiness_score: float
    completed_grade_count: int
    total_grade_count: int
    withdrawal_count: int
    effective_n: float
    section_count: int
    term_count: int
    mapped_instructor_section_count: int
    confidence_label: ConfidenceLabel
    prior_level: PriorLevel
    score_source: ScoreSource

    @property
    def confidence(self) -> Confidence:
        return Confidence(
            effective_n=self.effective_n,
            section_count=self.section_count,
            term_count=self.term_count,
            mapped_instructor_section_count=self.mapped_instructor_section_count,
            score_source=self.score_source,
            confidence_label=self.confidence_label,
        )


def bayesian_smooth(
    observed: float | None,
    n: float,
    prior: float,
    prior_strength: float,
) -> float:
    if prior_strength < 0:
        raise ValueError("prior_strength must be non-negative.")
    if observed is None or n <= 0:
        return _clamp_unit(prior)
    if prior_strength == 0:
        return _clamp_unit(observed)

    weight = n / (n + prior_strength)
    return _clamp_unit((weight * observed) + ((1.0 - weight) * prior))


def calculate_easiness_score(
    smoothed_grade_favorability: float,
    smoothed_withdrawal_rate: float,
    config: ScoreConfig | None = None,
) -> float:
    score_config = config or ScoreConfig()
    non_withdrawal_score = 1.0 - _clamp_unit(smoothed_withdrawal_rate)
    weighted_score = (score_config.grade_weight * _clamp_unit(smoothed_grade_favorability)) + (
        score_config.non_withdrawal_weight * non_withdrawal_score
    )
    return _clamp_10(10.0 * weighted_score)


def compute_historical_outcome_stats(
    aggregate: HistoricalGradeAggregate,
    *,
    grade_prior: float,
    withdrawal_prior: float,
    prior_level: PriorLevel,
    score_source: ScoreSource,
    config: ScoreConfig | None = None,
) -> HistoricalOutcomeStats:
    score_config = config or ScoreConfig()
    grade_raw = grade_favorability(aggregate.weighted_counts)
    withdrawal_raw = withdrawal_rate(aggregate.weighted_counts)
    grade_smoothed = bayesian_smooth(
        observed=grade_raw,
        n=aggregate.effective_grade_n,
        prior=grade_prior,
        prior_strength=score_config.grade_prior_strength,
    )
    withdrawal_smoothed = bayesian_smooth(
        observed=withdrawal_raw,
        n=aggregate.effective_withdrawal_n,
        prior=withdrawal_prior,
        prior_strength=score_config.withdrawal_prior_strength,
    )

    return HistoricalOutcomeStats(
        grade_favorability_raw=grade_raw,
        grade_favorability_smoothed=grade_smoothed,
        withdrawal_rate_raw=withdrawal_raw,
        withdrawal_rate_smoothed=withdrawal_smoothed,
        easiness_score=calculate_easiness_score(
            grade_smoothed,
            withdrawal_smoothed,
            score_config,
        ),
        completed_grade_count=aggregate.completed_grade_count,
        total_grade_count=aggregate.total_grade_count,
        withdrawal_count=aggregate.withdrawal_count,
        effective_n=aggregate.effective_n,
        section_count=aggregate.section_count,
        term_count=aggregate.term_count,
        mapped_instructor_section_count=aggregate.mapped_instructor_section_count,
        confidence_label=confidence_label_for(aggregate.effective_n, aggregate.term_count),
        prior_level=prior_level,
        score_source=score_source,
    )


def has_sufficient_instructor_course_evidence(
    stats: HistoricalOutcomeStats,
    config: ScoreConfig | None = None,
) -> bool:
    score_config = config or ScoreConfig()
    return (
        stats.score_source is ScoreSource.instructor_course
        and stats.effective_n >= score_config.instructor_course_min_effective_n
        and stats.mapped_instructor_section_count > 0
    )


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clamp_10(value: float) -> float:
    return max(0.0, min(10.0, value))
