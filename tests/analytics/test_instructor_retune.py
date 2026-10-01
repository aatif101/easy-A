"""D-24 instructor-course retune and the Phase 10 laboratory rule (CONTEXT D-01..D-03, D-13)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import PriorLevel, ScoreSource
from easy_a.analytics.grades import (
    GradeCounts,
    GradeObservation,
    aggregate_grade_observations,
    grade_favorability,
    withdrawal_rate,
)
from easy_a.analytics.queries import (
    get_course_historical_outcome_stats,
    get_current_section_historical_analytics,
    get_instructor_course_historical_outcome_stats,
    get_term_section_historical_analytics,
)
from easy_a.analytics.scoring import (
    DEFAULT_GRADE_PRIOR_STRENGTH,
    DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N,
    DEFAULT_INSTRUCTOR_PRIOR_STRENGTH,
    DEFAULT_WITHDRAWAL_PRIOR_STRENGTH,
    ScoreConfig,
    bayesian_smooth,
    calculate_easiness_score,
    compute_historical_outcome_stats,
)
from easy_a.common.section_types import (
    LABORATORY_SECTION_TYPES,
    is_laboratory_section_type,
    normalize_section_type,
)
from easy_a.models import (
    Course,
    GradeDistribution,
    Section,
    SectionInstructor,
)
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings

NOW = datetime(2026, 9, 1, tzinfo=UTC)
BASELINE_CONFIG = ScoreConfig(
    instructor_course_min_effective_n=60.0,
    instructor_prior_strength=60.0,
)


# --- seeding helpers (same shape as tests/analytics/test_queries.py) ---------------------------


def _add_course(
    session: Session,
    *,
    course_id: int,
    number: str,
    subject: str = "MAC",
) -> Course:
    course = Course(
        id=course_id,
        subject=subject,
        number=number,
        title=f"Synthetic {subject} {number}",
        catalog_edition="2026-2027",
    )
    session.add(course)
    session.flush()
    return course


def _add_section(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int = 10,
    instructor: str,
    section_type: str = "Class Lecture",
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type=section_type,
        primary_status="Active",
        secondary_status=None,
        delivery_method="CL",
        first_seen_at=NOW,
        last_seen_at=NOW,
        seats_remaining=None,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=None,
            source="synthetic",
            observed_at=NOW,
        )
    )
    session.flush()
    return section


def _add_grade(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int = 10,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    w: int = 0,
) -> GradeDistribution:
    completed = a + b + c + d + f
    distribution = GradeDistribution(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number_raw="001",
        section_suffix_raw="C",
        campus_raw="Tampa",
        a_count=a,
        b_count=b,
        c_count=c,
        d_count=d,
        f_count=f,
        i_count=0,
        s_count=0,
        u_count=0,
        w_count=w,
        other_count=0,
        total_grades=completed + w,
        source=f"synthetic-{term_id}-{crn}",
        source_hash="synthetic",
    )
    session.add(distribution)
    session.flush()
    return distribution


@dataclass(frozen=True)
class _CacheSnapshot:
    easiness_score: float
    smoothed_withdrawal_rate: float
    effective_n: float
    confidence_label: str
    score_source: str


def _snapshot_cache(session: Session, term: str) -> dict[str, _CacheSnapshot]:
    session.expire_all()
    rows = session.scalars(
        select(SectionRankingCache).where(SectionRankingCache.term == term)
    ).all()
    return {
        row.crn: _CacheSnapshot(
            easiness_score=row.easiness_score,
            smoothed_withdrawal_rate=row.smoothed_withdrawal_rate,
            effective_n=row.effective_n,
            confidence_label=row.confidence_label,
            score_source=row.score_source,
        )
        for row in rows
    }


# --- Task 1: tracer, ScoreConfig defaults and per-source strength -------------------------------

XOU_COUNTS = {"a": 20, "b": 10, "c": 5, "d": 3, "f": 2, "w": 4}  # 40 A-F grades, 44 total


def _seed_retune_term(session: Session) -> None:
    """MAC 1105 history with a 40-grade instructor, a 100-grade instructor and a small one."""
    _add_course(session, course_id=12, number="1114")
    _add_section(session, term_id=2, crn="50001", instructor="X. Ou")
    _add_grade(session, term_id=2, crn="50001", **XOU_COUNTS)
    _add_section(session, term_id=2, crn="50002", instructor="O. Other")
    _add_grade(session, term_id=2, crn="50002", a=30, b=30, c=20, d=10, f=10, w=10)
    _add_section(session, term_id=2, crn="50003", instructor="S. Small")
    _add_grade(session, term_id=2, crn="50003", a=3, b=2, w=1)

    _add_section(session, term_id=1, crn="70001", instructor="X. Ou")
    _add_section(session, term_id=1, crn="70002", instructor="O. Other")
    _add_section(session, term_id=1, crn="70003", instructor="S. Small")
    _add_section(session, term_id=1, crn="70004", instructor="Staff")
    # MAC 1114 has no own history: it falls back to the MAC subject.
    _add_section(session, term_id=1, crn="70012", course_id=12, instructor="D. New")
    # ENC 1101 has no history anywhere in its subject: it falls back to global.
    _add_section(session, term_id=1, crn="70013", course_id=11, instructor="E. Writer")
    session.commit()


def test_score_config_defaults_carry_the_d24_retune() -> None:
    config = ScoreConfig()

    assert config.instructor_course_min_effective_n == 30.0
    assert config.instructor_prior_strength == 30.0
    assert config.grade_prior_strength == 60.0
    assert config.withdrawal_prior_strength == 60.0
    assert DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N == 30.0
    assert DEFAULT_INSTRUCTOR_PRIOR_STRENGTH == 30.0
    assert DEFAULT_GRADE_PRIOR_STRENGTH == 60.0
    assert DEFAULT_WITHDRAWAL_PRIOR_STRENGTH == 60.0


def _aggregate(*, a: int, b: int, c: int, d: int, f: int, w: int):
    completed = a + b + c + d + f
    return aggregate_grade_observations(
        [
            GradeObservation(
                term_id=2,
                term_code="202408",
                crn="1",
                mapped_instructor=True,
                counts=GradeCounts(
                    a_count=a,
                    b_count=b,
                    c_count=c,
                    d_count=d,
                    f_count=f,
                    w_count=w,
                    total_grades=completed + w,
                ),
            )
        ]
    )


def test_instructor_course_source_smooths_grades_with_instructor_prior_strength() -> None:
    aggregate = _aggregate(**XOU_COUNTS)
    grade_raw = grade_favorability(aggregate.weighted_counts)
    withdrawal_raw = withdrawal_rate(aggregate.weighted_counts)

    stats = compute_historical_outcome_stats(
        aggregate,
        grade_prior=0.70,
        withdrawal_prior=0.12,
        prior_level=PriorLevel.course,
        score_source=ScoreSource.instructor_course,
    )

    expected_grade = bayesian_smooth(grade_raw, aggregate.effective_grade_n, 0.70, 30.0)
    expected_withdrawal = bayesian_smooth(
        withdrawal_raw, aggregate.effective_withdrawal_n, 0.12, 60.0
    )
    assert stats.grade_favorability_smoothed == expected_grade
    assert stats.withdrawal_rate_smoothed == expected_withdrawal
    assert stats.easiness_score == calculate_easiness_score(expected_grade, expected_withdrawal)
    # The retune is real: the old 60/60 shrinkage gives a different grade value.
    assert expected_grade != bayesian_smooth(grade_raw, aggregate.effective_grade_n, 0.70, 60.0)


def test_non_instructor_sources_keep_grade_prior_strength_60() -> None:
    aggregate = _aggregate(**XOU_COUNTS)
    grade_raw = grade_favorability(aggregate.weighted_counts)
    withdrawal_raw = withdrawal_rate(aggregate.weighted_counts)

    for source, level in (
        (ScoreSource.course, PriorLevel.subject),
        (ScoreSource.subject, PriorLevel.global_),
        (ScoreSource.global_, PriorLevel.global_),
    ):
        stats = compute_historical_outcome_stats(
            aggregate,
            grade_prior=0.70,
            withdrawal_prior=0.12,
            prior_level=level,
            score_source=source,
        )
        assert stats.grade_favorability_smoothed == bayesian_smooth(
            grade_raw, aggregate.effective_grade_n, 0.70, 60.0
        )
        assert stats.withdrawal_rate_smoothed == bayesian_smooth(
            withdrawal_raw, aggregate.effective_withdrawal_n, 0.12, 60.0
        )


def test_withdrawal_strength_is_unchanged_for_instructor_source() -> None:
    aggregate = _aggregate(**XOU_COUNTS)
    withdrawal_raw = withdrawal_rate(aggregate.weighted_counts)
    config = ScoreConfig(instructor_prior_strength=5.0, withdrawal_prior_strength=77.0)

    stats = compute_historical_outcome_stats(
        aggregate,
        grade_prior=0.70,
        withdrawal_prior=0.12,
        prior_level=PriorLevel.course,
        score_source=ScoreSource.instructor_course,
        config=config,
    )

    assert stats.withdrawal_rate_smoothed == bayesian_smooth(
        withdrawal_raw, aggregate.effective_withdrawal_n, 0.12, 77.0
    )


def test_retuned_instructor_course_score_flows_through_cache_rebuild(
    db_session: Session,
) -> None:
    _seed_retune_term(db_session)

    refresh_section_rankings(db_session, term="202701", config=ScoreConfig())
    retuned = _snapshot_cache(db_session, "202701")

    course_stats = get_course_historical_outcome_stats(
        db_session, "MAC", "1105", before_term_code="202701"
    )
    xou = retuned["70001"]
    grade_raw = grade_favorability(
        GradeCounts(
            a_count=20.0, b_count=10.0, c_count=5.0, d_count=3.0, f_count=2.0
        )
    )
    withdrawal_raw = withdrawal_rate(GradeCounts(w_count=4.0, total_grades=44.0))
    expected_grade = bayesian_smooth(
        grade_raw, 40.0, course_stats.grade_favorability_smoothed, 30.0
    )
    expected_withdrawal = bayesian_smooth(
        withdrawal_raw, 44.0, course_stats.withdrawal_rate_smoothed, 60.0
    )

    assert xou.score_source == "instructor_course"
    assert xou.effective_n == 40.0
    assert xou.easiness_score == calculate_easiness_score(expected_grade, expected_withdrawal)
    assert xou.smoothed_withdrawal_rate == expected_withdrawal

    # The D-02 baseline is reproducible by config: 40 < 60 sends X. Ou back to course history.
    refresh_section_rankings(db_session, term="202701", config=BASELINE_CONFIG)
    baseline = _snapshot_cache(db_session, "202701")
    assert baseline["70001"].score_source == "course"
    assert baseline["70001"].effective_n == course_stats.effective_n
    assert baseline["70001"].easiness_score == course_stats.easiness_score

    # Course, subject and global scores are byte-identical under both configs.
    non_instructor = [
        crn for crn, row in retuned.items() if row.score_source != "instructor_course"
    ]
    assert {"70003", "70004", "70012", "70013"} <= set(non_instructor)
    assert {retuned[crn].score_source for crn in non_instructor} == {"course", "subject", "global"}
    for crn in non_instructor:
        assert baseline[crn] == retuned[crn], crn
    # Rows that are instructor_course only under the new defaults came from course history before.
    for crn, row in retuned.items():
        if row.score_source == "instructor_course":
            assert baseline[crn].score_source in {"course", "instructor_course"}
    # O. Other (100 grades) is instructor_course under both configs, but the prior differs.
    assert baseline["70002"].score_source == "instructor_course"
    assert baseline["70002"].easiness_score != retuned["70002"].easiness_score


# --- Task 2: laboratory vocabulary, D-02 label-only single term, D-08 Staff, D-14 identity -----


def test_is_laboratory_section_type_matches_only_the_laboratory_vocabulary() -> None:
    assert set(LABORATORY_SECTION_TYPES) == {"laboratory"}
    for value in ("Laboratory", "  laboratory ", "LABORATORY"):
        assert is_laboratory_section_type(value), value
    for value in ("Class Lecture", "", "   ", None, "Lecture/Lab", "Lab", "Laboratory Lecture"):
        assert not is_laboratory_section_type(value), value


def test_normalize_section_type_collapses_whitespace_and_casefolds() -> None:
    assert normalize_section_type(None) == ""
    assert normalize_section_type("  Class   Lecture ") == "class lecture"


def _rows_by_crn(session: Session, course_keys: list[tuple[str, str]]) -> dict:
    rows = get_term_section_historical_analytics(
        session, term_code="202701", course_keys=course_keys
    )
    per_course = []
    for subject, number in course_keys:
        per_course.extend(
            get_current_section_historical_analytics(
                session, term_code="202701", subject=subject, course_number=number
            )
        )
    assert rows == per_course
    return {row.crn: row.stats for row in rows}


def test_single_term_flag_is_label_only_and_adds_no_shrinkage(db_session: Session) -> None:
    # MAC 1105: one instructor, 40 grades in one term. ENC 1101: the same counts split 20/20
    # over two terms. Each course's history is only its own instructor, so every prior matches.
    _add_section(db_session, term_id=2, crn="51001", instructor="A. One")
    _add_grade(db_session, term_id=2, crn="51001", a=20, b=10, c=6, d=2, f=2, w=4)
    _add_section(db_session, term_id=2, crn="52001", course_id=11, instructor="B. Two")
    _add_grade(db_session, term_id=2, crn="52001", course_id=11, a=10, b=5, c=3, d=1, f=1, w=2)
    _add_section(db_session, term_id=3, crn="52002", course_id=11, instructor="B. Two")
    _add_grade(db_session, term_id=3, crn="52002", course_id=11, a=10, b=5, c=3, d=1, f=1, w=2)
    _add_section(db_session, term_id=1, crn="71001", instructor="A. One")
    _add_section(db_session, term_id=1, crn="72001", course_id=11, instructor="B. Two")
    db_session.commit()

    stats = _rows_by_crn(db_session, [("ENC", "1101"), ("MAC", "1105")])

    one_term, two_terms = stats["71001"], stats["72001"]
    assert one_term.score_source is ScoreSource.instructor_course
    assert two_terms.score_source is ScoreSource.instructor_course
    assert (one_term.term_count, two_terms.term_count) == (1, 2)
    assert one_term.effective_n == two_terms.effective_n == 40.0
    assert one_term.easiness_score == two_terms.easiness_score
    assert one_term.withdrawal_rate_smoothed == two_terms.withdrawal_rate_smoothed


def test_staff_sections_feed_course_history_but_never_an_instructor(db_session: Session) -> None:
    _add_section(db_session, term_id=2, crn="53001", instructor="Staff")
    _add_grade(db_session, term_id=2, crn="53001", a=40, b=15, c=5, w=3)
    _add_section(db_session, term_id=2, crn="53002", instructor="N. Named")
    _add_grade(db_session, term_id=2, crn="53002", a=4, b=3, c=2, d=1, w=1)
    _add_section(db_session, term_id=1, crn="73001", instructor="Staff")
    _add_section(db_session, term_id=1, crn="73002", instructor="N. Named")
    db_session.commit()

    for name in ("Staff", "staff", " STAFF ", ""):
        assert (
            get_instructor_course_historical_outcome_stats(
                db_session, "MAC", "1105", name, before_term_code="202701"
            )
            is None
        ), name

    named = get_instructor_course_historical_outcome_stats(
        db_session, "MAC", "1105", "N. Named", before_term_code="202701"
    )
    assert named is not None
    assert named.effective_n == 10.0  # the Staff section's grades are not attributed to anyone
    assert named.section_count == 1

    stats = _rows_by_crn(db_session, [("MAC", "1105")])
    assert stats["73001"].score_source is ScoreSource.course
    assert stats["73002"].score_source is ScoreSource.course  # 10 < the 30-grade gate
    assert stats["73001"].section_count == 2  # Staff grades raise course-level history
    assert stats["73001"].completed_grade_count == 60 + 10


def test_instructor_name_is_matched_within_one_course_never_pooled(db_session: Session) -> None:
    _add_section(db_session, term_id=2, crn="54001", instructor="X. Liu")
    _add_grade(db_session, term_id=2, crn="54001", a=20, b=10, c=5, d=3, f=2, w=2)
    _add_section(db_session, term_id=2, crn="54002", course_id=11, instructor="X. Liu")
    _add_grade(db_session, term_id=2, crn="54002", course_id=11, a=15, b=15, c=5, d=3, f=2, w=2)
    _add_section(db_session, term_id=1, crn="74001", instructor="X. Liu")
    _add_section(db_session, term_id=1, crn="74002", course_id=11, instructor="X. Liu")
    db_session.commit()

    for subject, number in (("MAC", "1105"), ("ENC", "1101")):
        per_course = get_instructor_course_historical_outcome_stats(
            db_session, subject, number, "X. Liu", before_term_code="202701"
        )
        assert per_course is not None
        assert per_course.effective_n == 40.0, subject  # not 80

    stats = _rows_by_crn(db_session, [("ENC", "1101"), ("MAC", "1105")])
    assert stats["74001"].score_source is ScoreSource.instructor_course
    assert stats["74002"].score_source is ScoreSource.instructor_course
    assert stats["74001"].effective_n == stats["74002"].effective_n == 40.0
