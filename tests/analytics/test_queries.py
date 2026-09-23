from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import PriorLevel, ScoreSource
from easy_a.analytics.grades import RecencyConfig
from easy_a.analytics.queries import (
    get_course_historical_outcome_stats,
    get_current_section_historical_analytics,
    get_instructor_course_historical_outcome_stats,
    get_term_section_historical_analytics,
)
from easy_a.analytics.scoring import (
    DEFAULT_GRADE_PRIOR_STRENGTH,
    DEFAULT_WITHDRAWAL_PRIOR_STRENGTH,
    ScoreConfig,
    bayesian_smooth,
)
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
)

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def test_professor_course_prior_uses_course_history(db_session: Session) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(db_session, term_id=2, crn="89033", a=0, b=0, c=0, d=0, f=5)
    _add_section(db_session, term_id=2, crn="89034", instructor="A. Instructor")
    _add_grade(db_session, term_id=2, crn="89034", a=100)
    db_session.commit()

    stats = get_instructor_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        "I. Rothstein",
        before_term_code="202701",
    )

    assert stats is not None
    assert stats.score_source is ScoreSource.instructor_course
    assert stats.prior_level is PriorLevel.course
    assert stats.grade_favorability_raw == 0.0
    assert stats.grade_favorability_smoothed > 0.80


def test_zero_subject_grade_prior_remains_zero(db_session: Session) -> None:
    _add_course(db_session, course_id=12, number="1114")
    _add_grade(db_session, term_id=2, crn="88001", a=10)
    _add_grade(db_session, term_id=2, crn="88002", course_id=12, f=100)
    db_session.commit()

    stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert stats.prior_level is PriorLevel.subject
    assert stats.grade_favorability_smoothed == pytest.approx(
        bayesian_smooth(
            observed=1.0,
            n=10,
            prior=0.0,
            prior_strength=DEFAULT_GRADE_PRIOR_STRENGTH,
        )
    )


def test_zero_subject_withdrawal_prior_remains_zero(db_session: Session) -> None:
    _add_course(db_session, course_id=12, number="1114")
    _add_grade(db_session, term_id=2, crn="88001", a=10, w=10)
    _add_grade(db_session, term_id=2, crn="88002", course_id=12, a=100)
    db_session.commit()

    stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert stats.prior_level is PriorLevel.subject
    assert stats.withdrawal_rate_smoothed == pytest.approx(
        bayesian_smooth(
            observed=0.5,
            n=20,
            prior=0.0,
            prior_strength=DEFAULT_WITHDRAWAL_PRIOR_STRENGTH,
        )
    )


def test_target_course_data_is_excluded_from_subject_prior(db_session: Session) -> None:
    _add_course(db_session, course_id=12, number="1114")
    _add_grade(db_session, term_id=2, crn="88001", a=20)
    _add_grade(db_session, term_id=2, crn="88002", course_id=12, c=100)
    db_session.commit()

    stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert stats.prior_level is PriorLevel.subject
    assert stats.grade_favorability_smoothed == pytest.approx(
        bayesian_smooth(
            observed=1.0,
            n=20,
            prior=0.5,
            prior_strength=DEFAULT_GRADE_PRIOR_STRENGTH,
        )
    )


def test_subject_with_only_target_course_falls_back_to_global(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="88001", a=20)
    _add_grade(db_session, term_id=2, crn="88002", course_id=11, f=100)
    db_session.commit()

    stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert stats.prior_level is PriorLevel.global_


def test_same_subject_comparison_course_can_influence_subject_prior(
    db_session: Session,
) -> None:
    _add_course(db_session, course_id=12, number="1114")
    _add_grade(db_session, term_id=2, crn="88001", a=20)
    _add_grade(db_session, term_id=2, crn="88002", course_id=12, b=100)
    db_session.commit()

    stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert stats.prior_level is PriorLevel.subject
    assert stats.grade_favorability_smoothed == pytest.approx(
        bayesian_smooth(
            observed=1.0,
            n=20,
            prior=0.75,
            prior_strength=DEFAULT_GRADE_PRIOR_STRENGTH,
        )
    )


def test_staff_instructor_falls_back_to_course_level(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=40, b=20, w=5)
    _add_section(db_session, term_id=1, crn="12345", instructor="Staff")
    db_session.commit()

    rows = get_current_section_historical_analytics(
        db_session,
        term_code="202701",
        subject="MAC",
        course_number="1105",
    )

    assert len(rows) == 1
    assert rows[0].instructor == "Staff"
    assert rows[0].stats.score_source is ScoreSource.course


def test_missing_historical_instructor_mapping_only_contributes_to_course_history(
    db_session: Session,
) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=12, b=8, w=2)
    db_session.commit()

    course_stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )
    instructor_stats = get_instructor_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        "I. Rothstein",
        before_term_code="202701",
    )

    assert course_stats.section_count == 1
    assert course_stats.completed_grade_count == 20
    assert instructor_stats is None


def test_same_crn_in_different_terms_remains_separate(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=20)
    _add_section(db_session, term_id=1, crn="89033", instructor="I. Rothstein")
    db_session.commit()

    instructor_stats = get_instructor_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        "I. Rothstein",
        before_term_code="202701",
    )
    course_stats = get_course_historical_outcome_stats(
        db_session,
        "MAC",
        "1105",
        before_term_code="202701",
    )

    assert instructor_stats is None
    assert course_stats.section_count == 1


def test_known_safe_historical_identity_scores_current_rothstein_section(
    db_session: Session,
) -> None:
    _add_section(db_session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(db_session, term_id=2, crn="89033", a=60, b=30, c=10, w=5)
    _add_section(db_session, term_id=1, crn="70001", instructor="I. Rothstein")
    db_session.commit()

    rows = get_current_section_historical_analytics(
        db_session,
        term_code="202701",
        subject="MAC",
        course_number="1105",
    )

    assert len(rows) == 1
    assert rows[0].crn == "70001"
    assert rows[0].instructor == "I. Rothstein"
    assert rows[0].stats.score_source is ScoreSource.instructor_course
    assert rows[0].stats.confidence.score_source is ScoreSource.instructor_course
    assert rows[0].stats.mapped_instructor_section_count == 1
    assert 0.0 <= rows[0].historical_easiness <= 10.0


def test_seat_and_syllabus_fields_do_not_affect_score(db_session: Session) -> None:
    _add_grade(db_session, term_id=2, crn="89033", a=30, b=10, w=4)
    current_section = _add_section(
        db_session,
        term_id=1,
        crn="70002",
        instructor="Staff",
        seats_remaining=0,
    )
    db_session.commit()

    before = get_current_section_historical_analytics(
        db_session,
        term_code="202701",
        subject="MAC",
        course_number="1105",
    )[0].stats

    current_section.seats_remaining = 999
    db_session.add(
        SeatSnapshot(
            section_id=current_section.id,
            observed_at=NOW,
            capacity=999,
            enrollment=1,
            seats_remaining=998,
            wait_seats_available=10,
        )
    )
    db_session.add(
        Syllabus(
            document_id="demo-syllabus-70002",
            section_id=current_section.id,
            term_id=1,
            crn="70002",
            course_id=10,
            section_number="002",
            instructor_raw="Staff",
            organization="Synthetic",
            title="Synthetic syllabus",
            view_url="https://example.test/syllabus",
            content_html="<p>Very easy coursework.</p>",
            content_text="Very easy coursework.",
            content_hash="synthetic",
        )
    )
    db_session.commit()

    after = get_current_section_historical_analytics(
        db_session,
        term_code="202701",
        subject="MAC",
        course_number="1105",
    )[0].stats

    assert after.easiness_score == pytest.approx(before.easiness_score)
    assert after.withdrawal_rate_smoothed == pytest.approx(before.withdrawal_rate_smoothed)


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


def _add_course(
    session: Session,
    *,
    course_id: int,
    number: str,
    subject: str = "MAC",
    catalog_edition: str = "2026-2027",
) -> Course:
    course = Course(
        id=course_id,
        subject=subject,
        number=number,
        title=f"Synthetic {subject} {number}",
        catalog_edition=catalog_edition,
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
    seats_remaining: int | None = None,
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        secondary_status=None,
        delivery_method="CL",
        first_seen_at=NOW,
        last_seen_at=NOW,
        seats_remaining=seats_remaining,
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


def _seed_mixed_evidence_term(session: Session, *, extra_courses: int = 0) -> None:
    """Seed every evidence branch: course, subject, global and instructor-course."""
    # MAC 1105 (id 10) keeps course history; a second catalog edition shares its identity.
    _add_course(session, course_id=14, number="1105", catalog_edition="2025-2026")
    _add_course(session, course_id=12, number="1114")
    _add_course(session, course_id=13, number="2311")
    _add_course(session, course_id=15, number="2048", subject="PHY")

    # Sourced history for MAC 1105 across two past terms, with instructor mappings.
    _add_section(session, term_id=2, crn="89033", instructor="I. Rothstein")
    _add_grade(session, term_id=2, crn="89033", a=60, b=30, c=10, w=5)
    _add_section(session, term_id=3, crn="60001", instructor="I. Rothstein")
    _add_grade(session, term_id=3, crn="60001", a=10, b=5, f=3, w=1)
    _add_section(session, term_id=3, crn="60002", instructor="B. Sparse")
    _add_grade(session, term_id=3, crn="60002", a=2, b=1, w=1)
    _add_section(session, term_id=3, crn="60003", instructor="Staff")
    _add_grade(session, term_id=3, crn="60003", b=7, c=4, d=2)
    # Grade attributed to the other catalog edition, joined through no section.
    _add_grade(session, term_id=2, crn="89040", course_id=14, a=5, c=5)
    # Grade attributed to MAC 1114 but whose term+CRN section belongs to MAC 1105:
    # it must count once for both courses under the existing OR policy.
    _add_section(session, term_id=2, crn="89050", instructor="C. Cross")
    _add_grade(session, term_id=2, crn="89050", course_id=12, a=3, d=4, w=2)
    # Other subject-level MAC history.
    _add_grade(session, term_id=2, crn="88002", course_id=12, a=20, b=20, f=10, w=6)
    # ENC history only feeds the global prior.
    _add_grade(session, term_id=3, crn="77001", course_id=11, a=40, c=5, w=3)
    # A current-term grade row must be excluded by the pre-term filter.
    _add_grade(session, term_id=1, crn="99999", a=500)

    # Current-term sections covering each instructor state.
    _add_section(session, term_id=1, crn="70001", instructor="I. Rothstein")
    _add_section(session, term_id=1, crn="70002", instructor="B. Sparse")
    _add_section(session, term_id=1, crn="70003", instructor="Staff")
    _add_section(session, term_id=1, crn="70004", instructor=" ")
    ambiguous = _add_section(session, term_id=1, crn="70005", instructor="I. Rothstein")
    session.add(
        SectionInstructor(
            section_id=ambiguous.id,
            name_raw="B. Sparse",
            name_normalized=None,
            source="synthetic",
            observed_at=NOW,
        )
    )
    _add_section(session, term_id=1, crn="70006", course_id=14, instructor="I. Rothstein")
    _add_section(session, term_id=1, crn="70011", course_id=12, instructor="C. Cross")
    _add_section(session, term_id=1, crn="70012", course_id=13, instructor="D. New")
    _add_section(session, term_id=1, crn="70013", course_id=11, instructor="E. Writer")
    _add_section(session, term_id=1, crn="70014", course_id=15, instructor="F. Physics")
    for index in range(extra_courses):
        course_id = 100 + index
        _add_course(session, course_id=course_id, number=f"3{index:03d}", subject="ZZZ")
        _add_section(
            session,
            term_id=1,
            crn=f"8{index:04d}",
            course_id=course_id,
            instructor="Z. Extra",
        )
    session.commit()


def _per_course_rows(
    session: Session,
    course_keys: list[tuple[str, str]],
    config: ScoreConfig | None,
) -> list:
    rows = []
    for subject, number in course_keys:
        rows.extend(
            get_current_section_historical_analytics(
                session,
                term_code="202701",
                subject=subject,
                course_number=number,
                config=config,
            )
        )
    return rows


@pytest.mark.parametrize(
    "config",
    [None, ScoreConfig(recency=RecencyConfig(enabled=True, half_life_terms=1.0))],
    ids=["unweighted", "recency"],
)
def test_term_batch_matches_per_course_analytics_exactly(
    db_session: Session,
    config: ScoreConfig | None,
) -> None:
    _seed_mixed_evidence_term(db_session)
    course_keys = [
        ("ENC", "1101"),
        ("MAC", "1105"),
        ("MAC", "1114"),
        ("MAC", "2311"),
        ("PHY", "2048"),
    ]

    expected = _per_course_rows(db_session, course_keys, config)
    actual = get_term_section_historical_analytics(
        db_session,
        term_code="202701",
        course_keys=course_keys,
        config=config,
    )

    assert actual == expected
    sources = {row.crn: row.stats.score_source for row in actual}
    assert sources["70001"] is ScoreSource.instructor_course
    assert sources["70002"] is ScoreSource.course
    assert sources["70011"] is ScoreSource.course
    assert sources["70012"] is ScoreSource.subject
    assert sources["70013"] is ScoreSource.course
    assert sources["70014"] is ScoreSource.global_
    assert {row.crn for row in actual} >= {"70003", "70004", "70005", "70006"}


def test_term_batch_returns_nothing_for_unknown_term_or_course(db_session: Session) -> None:
    _seed_mixed_evidence_term(db_session)

    assert (
        get_term_section_historical_analytics(
            db_session, term_code="209901", course_keys=[("MAC", "1105")]
        )
        == []
    )
    assert (
        get_term_section_historical_analytics(
            db_session, term_code="202701", course_keys=[("XYZ", "0000")]
        )
        == []
    )


def test_term_batch_statement_count_does_not_grow_with_courses(db_session: Session) -> None:
    _seed_mixed_evidence_term(db_session, extra_courses=12)
    small_keys = [("MAC", "1105"), ("ZZZ", "3000")]
    large_keys = [("MAC", "1105")] + [("ZZZ", f"3{index:03d}") for index in range(12)]

    def count_statements(course_keys: list[tuple[str, str]]) -> tuple[int, int]:
        statements: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany) -> None:
            statements.append(statement.lower())

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            get_term_section_historical_analytics(
                db_session,
                term_code="202701",
                course_keys=course_keys,
            )
        finally:
            event.remove(engine, "before_cursor_execute", record)
        grade_reads = sum("grade_distributions" in statement for statement in statements)
        return len(statements), grade_reads

    small_total, small_grade_reads = count_statements(small_keys)
    large_total, large_grade_reads = count_statements(large_keys)

    assert large_total == small_total
    assert large_grade_reads == small_grade_reads == 1
