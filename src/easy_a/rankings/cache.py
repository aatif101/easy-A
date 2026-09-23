from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import func

from easy_a.analytics.confidence import ConfidenceLabel, ScoreSource
from easy_a.analytics.scoring import ScoreConfig
from easy_a.common.terms import normalize_banner_term_code
from easy_a.db import Base
from easy_a.models.core import Course, Term
from easy_a.models.sections import SeatSnapshot, Section

if TYPE_CHECKING:
    from easy_a.rankings.models import SectionRanking
    from easy_a.signals.models import ResolvedSignalSet


class _LoadLatestSeatSnapshot:
    pass


_LOAD_LATEST_SEAT_SNAPSHOT = _LoadLatestSeatSnapshot()


class SectionRankingCache(Base):
    __tablename__ = "section_rankings"
    __table_args__ = (
        UniqueConstraint("section_id", name="uq_section_rankings_section_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"),
        nullable=False,
    )
    term: Mapped[str] = mapped_column(String(6), nullable=False)
    term_name: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    course_number: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    crn: Mapped[str] = mapped_column(String(16), nullable=False)
    course_title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    easiness_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    smoothed_withdrawal_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    confidence_label: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    score_source: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_n: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_method: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    historical_analytics: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    gened_attributes: Mapped[list[dict[str, Any]]] = mapped_column(sa.JSON(), nullable=False)
    signals: Mapped[list[dict[str, Any]]] = mapped_column(sa.JSON(), nullable=False)
    instructor_provenance: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    gened_provenance: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    signal_provenance: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    section_provenance: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    modality: Mapped[dict[str, Any]] = mapped_column(sa.JSON(), nullable=False)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


def refresh_section_rankings(
    session: Session,
    *,
    term: str | int,
    subject: str | None = None,
    course_number: str | None = None,
    config: ScoreConfig | None = None,
) -> int:
    """Populate or refresh derived ranking rows without committing the caller's transaction."""
    from easy_a.rankings.models import RankingFreshness, RankingProvenance
    from easy_a.rankings.service import (
        _gened_attributes_by_course_id,
        _gened_provenance,
        _historical_summary,
        _instructor_from_state,
        _modality_for,
        _signal_provenance,
        _signals_for,
    )

    if (subject is None) != (course_number is None):
        raise ValueError("subject and course_number must be provided together")

    normalized_term = normalize_banner_term_code(term)
    stmt = (
        select(Section, Course, Term)
        .join(Course, Section.course_id == Course.id)
        .join(Term, Section.term_id == Term.id)
        .where(Term.banner_code == normalized_term)
        .order_by(Course.subject, Course.number, Section.crn)
    )
    if subject is not None and course_number is not None:
        stmt = stmt.where(
            Course.subject == subject.strip().upper(),
            Course.number == course_number.strip().upper(),
        )

    # Imported lazily to avoid a circular import: easy_a.models.__init__ imports
    # this module (SectionRankingCache), and both of these depend (directly or
    # transitively) on easy_a.models — a top-level import here would deadlock
    # that cycle. Both are only used inside this function.
    from easy_a.analytics.queries import get_term_section_historical_analytics
    from easy_a.common.instructors import get_current_instructor_states
    from easy_a.signals.resolver import resolve_term_section_signals

    section_course_rows = list(session.execute(stmt).all())
    course_keys = sorted(
        {(course.subject, course.number) for _, course, _ in section_course_rows}
    )
    analytics_by_crn = {
        row.crn: row.stats
        for row in get_term_section_historical_analytics(
            session,
            term_code=normalized_term,
            course_keys=course_keys,
            config=config,
        )
    }

    section_ids = [section.id for section, _, _ in section_course_rows]
    existing_by_section_id = {
        row.section_id: row
        for row in session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.section_id.in_(section_ids))
        )
    }
    # Per-section lookups are read once for the whole selection: over a remote database
    # each per-section query is a network round trip, which dominated whole-term rebuilds.
    instructor_states = get_current_instructor_states(session, section_ids)
    gened_by_course_id = _gened_attributes_by_course_id(
        session,
        [course.id for _, course, _ in section_course_rows],
    )
    signals_by_section_id: dict[int, ResolvedSignalSet] = {}
    if section_course_rows:
        signals_by_section_id = resolve_term_section_signals(
            session,
            term=section_course_rows[0][2],
            sections=[section for section, _, _ in section_course_rows],
            current_instructors={
                section_id: state.name for section_id, state in instructor_states.items()
            },
        )
    # One statement-time value for every row, as func.now() would give within this
    # transaction, so unchanged-shape updates can be batched.
    refreshed_at = session.scalar(select(func.now()))

    for section, course, term_row in section_course_rows:
        analytics_stats = analytics_by_crn[section.crn]
        instructor, instructor_provenance = _instructor_from_state(
            instructor_states[section.id],
            term_code=term_row.banner_code,
        )
        modality = _modality_for(section, term_code=term_row.banner_code)
        gened_attributes = gened_by_course_id.get(course.id, ())
        historical_analytics = _historical_summary(
            analytics_stats,
            before_term_code=term_row.banner_code,
        )
        resolved_signals = signals_by_section_id[section.id]
        payload: dict[str, Any] = {
            "section_id": section.id,
            "term": term_row.banner_code,
            "term_name": term_row.name,
            "subject": course.subject,
            "course_number": course.number,
            "crn": section.crn,
            "course_title": course.title,
            "instructor": instructor,
            "easiness_score": analytics_stats.easiness_score,
            "smoothed_withdrawal_rate": analytics_stats.withdrawal_rate_smoothed,
            "confidence_label": analytics_stats.confidence_label.value,
            "score_source": analytics_stats.score_source.value,
            "effective_n": analytics_stats.effective_n,
            "delivery_method": modality.delivery_method,
            "historical_analytics": historical_analytics.model_dump(mode="json"),
            "gened_attributes": [
                attribute.model_dump(mode="json") for attribute in gened_attributes
            ],
            "signals": [
                signal.model_dump(mode="json") for signal in _signals_for(resolved_signals)
            ],
            "instructor_provenance": instructor_provenance.model_dump(mode="json"),
            "gened_provenance": _gened_provenance(
                course,
                gened_attributes,
            ).model_dump(mode="json"),
            "signal_provenance": _signal_provenance(resolved_signals).model_dump(mode="json"),
            "section_provenance": RankingProvenance(
                freshness=RankingFreshness.current,
                source="sections",
                source_term=term_row.banner_code,
                detail="resolved by current term and CRN",
            ).model_dump(mode="json"),
            "modality": modality.model_dump(mode="json"),
            "refreshed_at": refreshed_at,
        }
        cache_row = existing_by_section_id.get(section.id)
        if cache_row is None:
            session.add(SectionRankingCache(**payload))
        else:
            for field_name, value in payload.items():
                setattr(cache_row, field_name, value)

    session.flush()
    return len(section_course_rows)


def hydrate_ranking(
    session: Session,
    cache_row: SectionRankingCache,
    *,
    seat_snapshot: SeatSnapshot | None | _LoadLatestSeatSnapshot = _LOAD_LATEST_SEAT_SNAPSHOT,
    seat_columns: Section | Mapping[str, int | None] | None = None,
    as_of: datetime | None = None,
) -> SectionRanking:
    """Rebuild a ranking from cached non-seat data and the latest live seat state."""
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
    from easy_a.schedule.freshness import snapshot_freshness

    section = session.get(Section, cache_row.section_id)
    if section is None:
        raise ValueError(f"No section found for cached section_id={cache_row.section_id}.")

    if isinstance(seat_snapshot, _LoadLatestSeatSnapshot):
        latest_snapshot = session.scalars(
            select(SeatSnapshot)
            .where(SeatSnapshot.section_id == cache_row.section_id)
            .order_by(SeatSnapshot.observed_at.desc(), SeatSnapshot.id.desc())
            .limit(1)
        ).first()
    else:
        latest_snapshot = seat_snapshot

    if latest_snapshot is not None:
        seats = SeatInfo(
            **snapshot_freshness(
                latest_snapshot,
                as_of=as_of or datetime.now(UTC),
            ).model_dump(),
            capacity=latest_snapshot.capacity,
            enrollment=latest_snapshot.enrollment,
            seats_remaining=latest_snapshot.seats_remaining,
            wait_seats_available=latest_snapshot.wait_seats_available,
            provenance=RankingProvenance(
                freshness=RankingFreshness.current,
                source="seat_snapshots",
                source_term=cache_row.term,
                detail="latest seat snapshot for this section",
            ),
        )
    else:
        capacity, enrollment, seats_remaining, wait_seats_available = _seat_column_values(
            seat_columns or section
        )
        if any(
            value is not None
            for value in (capacity, enrollment, seats_remaining, wait_seats_available)
        ):
            seats = SeatInfo(
                capacity=capacity,
                enrollment=enrollment,
                seats_remaining=seats_remaining,
                wait_seats_available=wait_seats_available,
                provenance=RankingProvenance(
                    freshness=RankingFreshness.current,
                    source="sections.current_seat_fields",
                    source_term=cache_row.term,
                    detail="canonical section seat fields; no seat snapshot is stored",
                ),
            )
        else:
            seats = SeatInfo(
                capacity=capacity,
                enrollment=enrollment,
                seats_remaining=seats_remaining,
                wait_seats_available=wait_seats_available,
                provenance=RankingProvenance(
                    freshness=RankingFreshness.unavailable,
                    source="seat_snapshots/sections.current_seat_fields",
                    source_term=cache_row.term,
                    detail="no seat data is stored for this section",
                ),
            )

    return SectionRanking(
        term=cache_row.term,
        term_name=cache_row.term_name,
        crn=cache_row.crn,
        subject=cache_row.subject,
        course_number=cache_row.course_number,
        course_title=cache_row.course_title,
        instructor=cache_row.instructor,
        instructor_provenance=RankingProvenance.model_validate(
            cache_row.instructor_provenance
        ),
        modality=ModalityInfo.model_validate(cache_row.modality),
        seats_remaining=seats.seats_remaining,
        seats=seats,
        gened_attributes=tuple(
            GenEdAttribute.model_validate(value) for value in cache_row.gened_attributes
        ),
        gened_provenance=RankingProvenance.model_validate(cache_row.gened_provenance),
        easiness_score=cache_row.easiness_score,
        smoothed_withdrawal_rate=cache_row.smoothed_withdrawal_rate,
        confidence_label=ConfidenceLabel(cache_row.confidence_label),
        effective_n=cache_row.effective_n,
        score_source=ScoreSource(cache_row.score_source),
        historical_analytics=HistoricalAnalyticsSummary.model_validate(
            cache_row.historical_analytics
        ),
        signals=tuple(RankingSignal.model_validate(value) for value in cache_row.signals),
        signal_provenance=RankingProvenance.model_validate(cache_row.signal_provenance),
        section_provenance=RankingProvenance.model_validate(cache_row.section_provenance),
    )


def _seat_column_values(
    seat_columns: Section | Mapping[str, int | None],
) -> tuple[int | None, int | None, int | None, int | None]:
    names = ("capacity", "enrollment", "seats_remaining", "wait_seats_available")
    if isinstance(seat_columns, Mapping):
        values = tuple(seat_columns.get(name) for name in names)
    else:
        values = tuple(getattr(seat_columns, name) for name in names)
    return values  # type: ignore[return-value]
