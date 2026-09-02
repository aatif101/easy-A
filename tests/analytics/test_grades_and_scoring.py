from __future__ import annotations

import pytest

from easy_a.analytics.confidence import ConfidenceLabel, confidence_label_for
from easy_a.analytics.grades import (
    GradeCounts,
    GradeObservation,
    RecencyConfig,
    aggregate_grade_observations,
    grade_favorability,
    withdrawal_rate,
)
from easy_a.analytics.scoring import (
    HistoricalOutcomeStats,
    ScoreConfig,
    bayesian_smooth,
    calculate_easiness_score,
)


def test_grade_favorability_formula_uses_only_completed_letter_grades() -> None:
    counts = GradeCounts(
        a_count=2,
        b_count=1,
        c_count=1,
        d_count=1,
        f_count=1,
        i_count=99,
        s_count=99,
        u_count=99,
        w_count=99,
        other_count=99,
        total_grades=501,
    )

    assert grade_favorability(counts) == pytest.approx(14 / 24)


def test_withdrawal_rate_uses_total_grades() -> None:
    counts = GradeCounts(a_count=8, b_count=10, w_count=2, total_grades=20)

    assert withdrawal_rate(counts) == pytest.approx(0.10)


def test_zero_completed_grades_have_no_raw_grade_favorability() -> None:
    counts = GradeCounts(w_count=5, total_grades=5)

    assert grade_favorability(counts) is None


def test_zero_total_grades_have_no_raw_withdrawal_rate() -> None:
    counts = GradeCounts(a_count=5, total_grades=0)

    assert withdrawal_rate(counts) is None


def test_bayesian_shrinkage_formula() -> None:
    assert bayesian_smooth(
        observed=0.50,
        n=60,
        prior=0.75,
        prior_strength=60,
    ) == pytest.approx(0.625)


def test_small_section_shrinks_strongly_toward_prior() -> None:
    smoothed = bayesian_smooth(observed=0.0, n=5, prior=0.80, prior_strength=60)

    assert smoothed > 0.70


def test_large_sample_stays_close_to_observed_value() -> None:
    smoothed = bayesian_smooth(observed=0.60, n=600, prior=0.90, prior_strength=60)

    assert smoothed == pytest.approx(0.60, abs=0.03)


@pytest.mark.parametrize(
    ("effective_n", "term_count", "expected"),
    [
        (59.9, 2, ConfidenceLabel.low),
        (60.0, 2, ConfidenceLabel.medium),
        (179.9, 2, ConfidenceLabel.medium),
        (180.0, 2, ConfidenceLabel.high),
        (60.0, 1, ConfidenceLabel.low),
        (180.0, 1, ConfidenceLabel.medium),
    ],
)
def test_confidence_boundaries(
    effective_n: float,
    term_count: int,
    expected: ConfidenceLabel,
) -> None:
    assert confidence_label_for(effective_n, term_count) is expected


def test_easiness_score_is_clamped_to_zero_to_ten() -> None:
    assert calculate_easiness_score(2.0, -1.0) == 10.0
    assert calculate_easiness_score(-1.0, 2.0) == 0.0


def test_recency_weighting_can_emphasize_recent_terms() -> None:
    aggregate = aggregate_grade_observations(
        [
            GradeObservation(
                term_id=1,
                term_code="202408",
                crn="11111",
                counts=GradeCounts(f_count=100, total_grades=100),
            ),
            GradeObservation(
                term_id=2,
                term_code="202508",
                crn="22222",
                counts=GradeCounts(a_count=100, total_grades=100),
            ),
        ],
        recency=RecencyConfig(enabled=True, half_life_terms=1.0),
    )

    assert grade_favorability(aggregate.weighted_counts) == pytest.approx(2 / 3)


def test_output_type_does_not_use_gpa_language() -> None:
    field_names = "".join(HistoricalOutcomeStats.__dataclass_fields__)

    assert "gpa" not in field_names.lower()


def test_score_weights_are_configured_not_hidden_inside_formula() -> None:
    score = calculate_easiness_score(
        1.0,
        1.0,
        ScoreConfig(grade_weight=0.50, non_withdrawal_weight=0.50),
    )

    assert score == pytest.approx(5.0)
