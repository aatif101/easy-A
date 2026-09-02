from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import PriorLevel, ScoreSource
from easy_a.analytics.grades import (
    GradeCounts,
    GradeObservation,
    HistoricalGradeAggregate,
    aggregate_grade_observations,
    grade_favorability,
    withdrawal_rate,
)
from easy_a.analytics.scoring import (
    DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR,
    DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR,
    HistoricalOutcomeStats,
    ScoreConfig,
    compute_historical_outcome_stats,
    has_sufficient_instructor_course_evidence,
)
from easy_a.common.instructors import get_current_instructor_state, is_usable_instructor
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term


@dataclass(frozen=True)
class SectionHistoricalAnalytics:
    crn: str
    instructor: str | None
    stats: HistoricalOutcomeStats

    @property
    def historical_easiness(self) -> float:
        return self.stats.easiness_score

    @property
    def historical_withdrawal_rate(self) -> float:
        return self.stats.withdrawal_rate_smoothed


def get_course_historical_outcome_stats(
    session: Session,
    subject: str,
    course_number: str,
    *,
    before_term_code: str | int | None = None,
    config: ScoreConfig | None = None,
) -> HistoricalOutcomeStats:
    score_config = config or ScoreConfig()
    normalized_subject = subject.strip().upper()
    normalized_number = course_number.strip().upper()
    course_ids = _course_ids(session, normalized_subject, normalized_number)
    subject_course_ids = _subject_course_ids_excluding(
        session,
        normalized_subject,
        excluded_course_ids=course_ids,
    )

    course_aggregate = _aggregate_for_course_ids(
        session,
        course_ids,
        before_term_code=before_term_code,
        config=score_config,
    )
    subject_aggregate = _aggregate_for_course_ids(
        session,
        subject_course_ids,
        before_term_code=before_term_code,
        config=score_config,
    )
    global_aggregate = _aggregate_for_course_ids(
        session,
        None,
        before_term_code=before_term_code,
        config=score_config,
    )
    return _stats_with_course_subject_global_fallback(
        course_aggregate=course_aggregate,
        subject_aggregate=subject_aggregate,
        global_aggregate=global_aggregate,
        config=score_config,
    )


def get_instructor_course_historical_outcome_stats(
    session: Session,
    subject: str,
    course_number: str,
    instructor_name: str,
    *,
    before_term_code: str | int | None = None,
    config: ScoreConfig | None = None,
) -> HistoricalOutcomeStats | None:
    if not is_usable_instructor(instructor_name):
        return None

    score_config = config or ScoreConfig()
    normalized_subject = subject.strip().upper()
    normalized_number = course_number.strip().upper()
    course_ids = _course_ids(session, normalized_subject, normalized_number)
    instructor_aggregate = aggregate_grade_observations(
        _fetch_instructor_course_grade_observations(
            session,
            course_ids,
            instructor_name.strip(),
            before_term_code=before_term_code,
        ),
        score_config.recency,
    )
    if not instructor_aggregate.has_evidence:
        return None

    course_stats = get_course_historical_outcome_stats(
        session,
        normalized_subject,
        normalized_number,
        before_term_code=before_term_code,
        config=score_config,
    )
    return compute_historical_outcome_stats(
        instructor_aggregate,
        grade_prior=course_stats.grade_favorability_smoothed,
        withdrawal_prior=course_stats.withdrawal_rate_smoothed,
        prior_level=PriorLevel.course,
        score_source=ScoreSource.instructor_course,
        config=score_config,
    )


def get_current_section_historical_analytics(
    session: Session,
    term_code: str | int,
    subject: str,
    course_number: str,
    *,
    config: ScoreConfig | None = None,
) -> list[SectionHistoricalAnalytics]:
    score_config = config or ScoreConfig()
    normalized_term_code = normalize_banner_term_code(term_code)
    term = session.execute(
        select(Term).where(Term.banner_code == normalized_term_code)
    ).scalar_one_or_none()
    if term is None:
        return []

    course_ids = _course_ids(session, subject.strip().upper(), course_number.strip().upper())
    if not course_ids:
        return []

    course_stats = get_course_historical_outcome_stats(
        session,
        subject,
        course_number,
        before_term_code=normalized_term_code,
        config=score_config,
    )
    sections = (
        session.execute(
            select(Section)
            .where(Section.term_id == term.id, Section.course_id.in_(course_ids))
            .order_by(Section.crn)
        )
        .scalars()
        .all()
    )

    rows: list[SectionHistoricalAnalytics] = []
    for section in sections:
        instructor_state = get_current_instructor_state(session, section.id)
        instructor = instructor_state.name
        stats = course_stats
        if instructor_state.is_usable_for_scoring:
            assert instructor is not None
            instructor_stats = get_instructor_course_historical_outcome_stats(
                session,
                subject,
                course_number,
                instructor,
                before_term_code=normalized_term_code,
                config=score_config,
            )
            if instructor_stats is not None and has_sufficient_instructor_course_evidence(
                instructor_stats,
                score_config,
            ):
                stats = instructor_stats
        rows.append(SectionHistoricalAnalytics(crn=section.crn, instructor=instructor, stats=stats))

    return rows


def _stats_with_course_subject_global_fallback(
    *,
    course_aggregate: HistoricalGradeAggregate,
    subject_aggregate: HistoricalGradeAggregate,
    global_aggregate: HistoricalGradeAggregate,
    config: ScoreConfig,
) -> HistoricalOutcomeStats:
    global_grade_prior = (
        grade_favorability(global_aggregate.weighted_counts)
        if global_aggregate.has_grade_evidence
        else DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR
    )
    global_withdrawal_prior = (
        withdrawal_rate(global_aggregate.weighted_counts)
        if global_aggregate.has_withdrawal_evidence
        else DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR
    )
    assert global_grade_prior is not None
    assert global_withdrawal_prior is not None

    if course_aggregate.has_evidence:
        subject_grade_prior = grade_favorability(subject_aggregate.weighted_counts)
        subject_withdrawal_prior = withdrawal_rate(subject_aggregate.weighted_counts)
        return compute_historical_outcome_stats(
            course_aggregate,
            grade_prior=(
                subject_grade_prior
                if subject_grade_prior is not None
                else global_grade_prior
            ),
            withdrawal_prior=(
                subject_withdrawal_prior
                if subject_withdrawal_prior is not None
                else global_withdrawal_prior
            ),
            prior_level=(
                PriorLevel.subject
                if subject_grade_prior is not None or subject_withdrawal_prior is not None
                else PriorLevel.global_
            ),
            score_source=ScoreSource.course,
            config=config,
        )

    if subject_aggregate.has_evidence:
        return compute_historical_outcome_stats(
            subject_aggregate,
            grade_prior=global_grade_prior,
            withdrawal_prior=global_withdrawal_prior,
            prior_level=PriorLevel.global_,
            score_source=ScoreSource.subject,
            config=config,
        )

    return compute_historical_outcome_stats(
        course_aggregate,
        grade_prior=global_grade_prior,
        withdrawal_prior=global_withdrawal_prior,
        prior_level=PriorLevel.global_,
        score_source=ScoreSource.global_,
        config=config,
    )


def _aggregate_for_course_ids(
    session: Session,
    course_ids: Sequence[int] | None,
    *,
    before_term_code: str | int | None,
    config: ScoreConfig,
) -> HistoricalGradeAggregate:
    return aggregate_grade_observations(
        _fetch_course_grade_observations(session, course_ids, before_term_code=before_term_code),
        config.recency,
    )


def _fetch_course_grade_observations(
    session: Session,
    course_ids: Sequence[int] | None,
    *,
    before_term_code: str | int | None,
) -> list[GradeObservation]:
    if course_ids is not None and not course_ids:
        return []

    stmt = (
        select(GradeDistribution, Term.banner_code, Section.id)
        .join(Term, GradeDistribution.term_id == Term.id)
        .outerjoin(
            Section,
            and_(
                Section.term_id == GradeDistribution.term_id,
                Section.crn == GradeDistribution.crn,
            ),
        )
    )
    if course_ids is not None:
        stmt = stmt.where(
            or_(
                GradeDistribution.course_id.in_(course_ids),
                Section.course_id.in_(course_ids),
            )
        )
    if before_term_code is not None:
        stmt = stmt.where(Term.banner_code < normalize_banner_term_code(before_term_code))

    rows = session.execute(stmt).all()
    section_ids = [section_id for _, _, section_id in rows if section_id is not None]
    mapped_section_ids = _mapped_instructor_section_ids(session, section_ids)
    return [
        _grade_observation(
            distribution=distribution,
            term_code=term_code,
            mapped_instructor=section_id in mapped_section_ids,
        )
        for distribution, term_code, section_id in rows
    ]


def _fetch_instructor_course_grade_observations(
    session: Session,
    course_ids: Sequence[int],
    instructor_name: str,
    *,
    before_term_code: str | int | None,
) -> list[GradeObservation]:
    if not course_ids:
        return []

    instructor_section_ids = _instructor_section_ids(session, course_ids, instructor_name)
    if not instructor_section_ids:
        return []

    stmt = (
        select(GradeDistribution, Term.banner_code)
        .join(Term, GradeDistribution.term_id == Term.id)
        .join(
            Section,
            and_(
                Section.term_id == GradeDistribution.term_id,
                Section.crn == GradeDistribution.crn,
            ),
        )
        .where(Section.id.in_(instructor_section_ids))
    )
    if before_term_code is not None:
        stmt = stmt.where(Term.banner_code < normalize_banner_term_code(before_term_code))

    return [
        _grade_observation(
            distribution=distribution,
            term_code=term_code,
            mapped_instructor=True,
        )
        for distribution, term_code in session.execute(stmt).all()
    ]


def _grade_observation(
    *,
    distribution: GradeDistribution,
    term_code: str,
    mapped_instructor: bool,
) -> GradeObservation:
    return GradeObservation(
        term_id=distribution.term_id,
        term_code=term_code,
        crn=distribution.crn,
        mapped_instructor=mapped_instructor,
        counts=GradeCounts(
            a_count=distribution.a_count,
            b_count=distribution.b_count,
            c_count=distribution.c_count,
            d_count=distribution.d_count,
            f_count=distribution.f_count,
            i_count=distribution.i_count,
            s_count=distribution.s_count,
            u_count=distribution.u_count,
            w_count=distribution.w_count,
            other_count=distribution.other_count,
            total_grades=distribution.total_grades,
        ),
    )


def _course_ids(session: Session, subject: str, course_number: str) -> list[int]:
    return list(
        session.execute(
            select(Course.id).where(
                Course.subject == subject.strip().upper(),
                Course.number == course_number.strip().upper(),
            )
        ).scalars()
    )


def _subject_course_ids_excluding(
    session: Session,
    subject: str,
    *,
    excluded_course_ids: Sequence[int],
) -> list[int]:
    excluded_course_id_set = set(excluded_course_ids)
    stmt = select(Course.id).where(Course.subject == subject.strip().upper())
    if excluded_course_id_set:
        stmt = stmt.where(Course.id.not_in(excluded_course_id_set))
    return list(session.execute(stmt).scalars())


def _mapped_instructor_section_ids(session: Session, section_ids: list[int]) -> set[int]:
    if not section_ids:
        return set()
    rows = session.execute(
        select(SectionInstructor.section_id, SectionInstructor.name_raw).where(
            SectionInstructor.section_id.in_(section_ids)
        )
    )
    return {section_id for section_id, name_raw in rows if is_usable_instructor(name_raw)}


def _instructor_section_ids(
    session: Session,
    course_ids: Sequence[int],
    instructor_name: str,
) -> set[int]:
    return set(
        session.execute(
            select(Section.id)
            .join(SectionInstructor, SectionInstructor.section_id == Section.id)
            .where(
                Section.course_id.in_(course_ids),
                SectionInstructor.name_raw == instructor_name,
            )
        ).scalars()
    )
