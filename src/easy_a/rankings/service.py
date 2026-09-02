from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.analytics.queries import get_current_section_historical_analytics
from easy_a.analytics.scoring import HistoricalOutcomeStats, ScoreConfig
from easy_a.common.terms import normalize_banner_term_code
from easy_a.models import Course, CourseAttribute, SeatSnapshot, Section, SectionInstructor, Term
from easy_a.rankings.models import (
    GenEdAttribute,
    HistoricalAnalyticsSummary,
    ModalityInfo,
    RankingFreshness,
    RankingProvenance,
    RankingSignal,
    SeatInfo,
    SectionRanking,
)
from easy_a.schedule.normalize import DELIVERY_METHOD_LABELS
from easy_a.signals.models import ResolvedSignalSet, SignalSourceKind
from easy_a.signals.resolver import resolve_section_signals


class RankingResolutionError(ValueError):
    """Raised when a section ranking request cannot be resolved."""


def rank_section(
    session: Session,
    *,
    term: str | int,
    crn: str,
    config: ScoreConfig | None = None,
) -> SectionRanking:
    normalized_term = normalize_banner_term_code(term)
    normalized_crn = crn.strip()
    section, course, term_row = _get_section_course_term(
        session,
        term=normalized_term,
        crn=normalized_crn,
    )
    instructor, instructor_provenance = _latest_instructor_state(
        session,
        section=section,
        term_code=term_row.banner_code,
    )
    modality = _modality_for(section, term_code=term_row.banner_code)
    seats = _seat_info_for(session, section=section, term_code=term_row.banner_code)
    gened_attributes = _gened_attributes_for(session, course)
    analytics_stats = _historical_stats_for_section(
        session,
        term_code=term_row.banner_code,
        crn=section.crn,
        course=course,
        config=config,
    )
    historical_analytics = _historical_summary(
        analytics_stats,
        before_term_code=term_row.banner_code,
    )
    resolved_signals = resolve_section_signals(
        session,
        term=term_row.banner_code,
        crn=section.crn,
    )

    return SectionRanking(
        term=term_row.banner_code,
        term_name=term_row.name,
        crn=section.crn,
        subject=course.subject,
        course_number=course.number,
        course_title=course.title,
        instructor=instructor,
        instructor_provenance=instructor_provenance,
        modality=modality,
        seats_remaining=seats.seats_remaining,
        seats=seats,
        gened_attributes=gened_attributes,
        gened_provenance=_gened_provenance(course, gened_attributes),
        easiness_score=analytics_stats.easiness_score,
        smoothed_withdrawal_rate=analytics_stats.withdrawal_rate_smoothed,
        confidence_label=analytics_stats.confidence_label,
        effective_n=analytics_stats.effective_n,
        score_source=analytics_stats.score_source,
        historical_analytics=historical_analytics,
        signals=_signals_for(resolved_signals),
        signal_provenance=_signal_provenance(resolved_signals),
        section_provenance=RankingProvenance(
            freshness=RankingFreshness.current,
            source="sections",
            source_term=term_row.banner_code,
            detail="resolved by current term and CRN",
        ),
    )


def rank_course_sections(
    session: Session,
    *,
    term: str | int,
    subject: str,
    course_number: str,
    config: ScoreConfig | None = None,
) -> list[SectionRanking]:
    normalized_term = normalize_banner_term_code(term)
    normalized_subject = subject.strip().upper()
    normalized_course_number = course_number.strip().upper()
    crns = (
        session.execute(
            select(Section.crn)
            .join(Term, Section.term_id == Term.id)
            .join(Course, Section.course_id == Course.id)
            .where(
                Term.banner_code == normalized_term,
                Course.subject == normalized_subject,
                Course.number == normalized_course_number,
            )
            .order_by(Section.crn)
        )
        .scalars()
        .all()
    )
    return [
        rank_section(session, term=normalized_term, crn=crn, config=config)
        for crn in crns
    ]


def _get_section_course_term(
    session: Session,
    *,
    term: str,
    crn: str,
) -> tuple[Section, Course, Term]:
    row = session.execute(
        select(Section, Course, Term)
        .join(Course, Section.course_id == Course.id)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == term, Section.crn == crn)
    ).one_or_none()
    if row is None:
        raise RankingResolutionError(f"No section found for term {term!r} and CRN {crn!r}.")
    section, course, term_row = row
    return section, course, term_row


def _latest_instructor_state(
    session: Session,
    *,
    section: Section,
    term_code: str,
) -> tuple[str | None, RankingProvenance]:
    latest_observed_at = session.scalar(
        select(func.max(SectionInstructor.observed_at)).where(
            SectionInstructor.section_id == section.id
        )
    )
    if latest_observed_at is None:
        return None, RankingProvenance(
            freshness=RankingFreshness.unavailable,
            source="section_instructors",
            source_term=term_code,
            detail="no instructor observations are stored for this section",
        )

    names = (
        session.execute(
            select(SectionInstructor.name_raw)
            .where(
                SectionInstructor.section_id == section.id,
                SectionInstructor.observed_at == latest_observed_at,
            )
            .order_by(SectionInstructor.name_raw)
        )
        .scalars()
        .all()
    )
    cleaned_names = tuple(dict.fromkeys(name.strip() for name in names if name.strip()))
    if not cleaned_names:
        return None, RankingProvenance(
            freshness=RankingFreshness.unavailable,
            source="section_instructors",
            source_term=term_code,
            detail="latest instructor observation is blank",
        )

    return " / ".join(cleaned_names), RankingProvenance(
        freshness=RankingFreshness.current,
        source="section_instructors",
        source_term=term_code,
        detail="latest observed instructor state",
    )


def _modality_for(section: Section, *, term_code: str) -> ModalityInfo:
    delivery_method = section.delivery_method.strip() if section.delivery_method else None
    if delivery_method is None:
        provenance = RankingProvenance(
            freshness=RankingFreshness.unavailable,
            source="sections.delivery_method",
            source_term=term_code,
            detail="delivery method is not stored for this section",
        )
    else:
        provenance = RankingProvenance(
            freshness=RankingFreshness.current,
            source="sections.delivery_method",
            source_term=term_code,
        )
    return ModalityInfo(
        delivery_method=delivery_method,
        delivery_label=DELIVERY_METHOD_LABELS.get(delivery_method) if delivery_method else None,
        provenance=provenance,
    )


def _seat_info_for(session: Session, *, section: Section, term_code: str) -> SeatInfo:
    latest_snapshot = (
        session.execute(
            select(SeatSnapshot)
            .where(SeatSnapshot.section_id == section.id)
            .order_by(SeatSnapshot.observed_at.desc(), SeatSnapshot.id.desc())
        )
        .scalars()
        .first()
    )
    if latest_snapshot is not None:
        return SeatInfo(
            capacity=latest_snapshot.capacity,
            enrollment=latest_snapshot.enrollment,
            seats_remaining=latest_snapshot.seats_remaining,
            wait_seats_available=latest_snapshot.wait_seats_available,
            provenance=RankingProvenance(
                freshness=RankingFreshness.current,
                source="seat_snapshots",
                source_term=term_code,
                detail="latest seat snapshot for this section",
            ),
        )

    if any(
        value is not None
        for value in (
            section.capacity,
            section.enrollment,
            section.seats_remaining,
            section.wait_seats_available,
        )
    ):
        return SeatInfo(
            capacity=section.capacity,
            enrollment=section.enrollment,
            seats_remaining=section.seats_remaining,
            wait_seats_available=section.wait_seats_available,
            provenance=RankingProvenance(
                freshness=RankingFreshness.current,
                source="sections.current_seat_fields",
                source_term=term_code,
                detail="canonical section seat fields; no seat snapshot is stored",
            ),
        )

    return SeatInfo(
        capacity=None,
        enrollment=None,
        seats_remaining=None,
        wait_seats_available=None,
        provenance=RankingProvenance(
            freshness=RankingFreshness.unavailable,
            source="seat_snapshots/sections.current_seat_fields",
            source_term=term_code,
            detail="no seat data is stored for this section",
        ),
    )


def _gened_attributes_for(session: Session, course: Course) -> tuple[GenEdAttribute, ...]:
    attributes = (
        session.execute(
            select(CourseAttribute)
            .where(CourseAttribute.course_id == course.id)
            .order_by(CourseAttribute.attribute_code, CourseAttribute.id)
        )
        .scalars()
        .all()
    )
    return tuple(
        GenEdAttribute(code=attribute.attribute_code, label=attribute.attribute_label)
        for attribute in attributes
    )


def _gened_provenance(
    course: Course,
    attributes: tuple[GenEdAttribute, ...],
) -> RankingProvenance:
    if attributes:
        freshness = RankingFreshness.current
        detail = f"catalog_edition={course.catalog_edition}"
    else:
        freshness = RankingFreshness.unavailable
        detail = f"no stored course attributes for catalog_edition={course.catalog_edition}"
    return RankingProvenance(
        freshness=freshness,
        source="course_attributes",
        source_term=None,
        detail=detail,
    )


def _historical_stats_for_section(
    session: Session,
    *,
    term_code: str,
    crn: str,
    course: Course,
    config: ScoreConfig | None,
) -> HistoricalOutcomeStats:
    analytics_rows = get_current_section_historical_analytics(
        session,
        term_code=term_code,
        subject=course.subject,
        course_number=course.number,
        config=config,
    )
    for row in analytics_rows:
        if row.crn == crn:
            return row.stats
    raise RankingResolutionError(
        f"No historical analytics row found for term {term_code!r} and CRN {crn!r}."
    )


def _historical_summary(
    stats: HistoricalOutcomeStats,
    *,
    before_term_code: str,
) -> HistoricalAnalyticsSummary:
    return HistoricalAnalyticsSummary(
        easiness_score=stats.easiness_score,
        smoothed_withdrawal_rate=stats.withdrawal_rate_smoothed,
        confidence_label=stats.confidence_label,
        effective_n=stats.effective_n,
        score_source=stats.score_source,
        prior_level=stats.prior_level,
        completed_grade_count=stats.completed_grade_count,
        total_grade_count=stats.total_grade_count,
        withdrawal_count=stats.withdrawal_count,
        section_count=stats.section_count,
        term_count=stats.term_count,
        mapped_instructor_section_count=stats.mapped_instructor_section_count,
        provenance=RankingProvenance(
            freshness=RankingFreshness.historical,
            source="grade_distributions",
            source_term=None,
            detail=f"computed from terms before {before_term_code}; non-grade data is excluded",
        ),
    )


def _signals_for(resolved: ResolvedSignalSet) -> tuple[RankingSignal, ...]:
    return tuple(
        RankingSignal(
            signal_type=signal.signal_type.value,
            value=signal.value,
            confidence=signal.confidence,
            source=signal.source_kind.value,
            source_identifier=signal.source_identifier,
            source_term=signal.source_term,
            freshness=_freshness_for_signal_source(signal.source_kind),
            evidence=signal.evidence_text,
        )
        for signal in resolved.signals
    )


def _signal_provenance(resolved: ResolvedSignalSet) -> RankingProvenance:
    freshness = _freshness_for_signal_source(resolved.provenance)
    detail = "signal resolver source precedence"
    if resolved.instructor_match_confidence is not None:
        detail = (
            f"{detail}; instructor_match_confidence="
            f"{resolved.instructor_match_confidence:.2f}"
        )
    return RankingProvenance(
        freshness=freshness,
        source=resolved.provenance.value,
        source_term=resolved.source_term,
        detail=detail,
    )


def _freshness_for_signal_source(source_kind: SignalSourceKind) -> RankingFreshness:
    if source_kind is SignalSourceKind.unavailable:
        return RankingFreshness.unavailable
    if source_kind in {
        SignalSourceKind.historical_same_instructor_course,
        SignalSourceKind.historical_same_course,
    }:
        return RankingFreshness.historical
    return RankingFreshness.current
