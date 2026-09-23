from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, case, exists, func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery

from easy_a.analytics.confidence import ConfidenceLabel
from easy_a.api.dependencies import BannerTerm, DbSession
from easy_a.api.schemas import RankingSort, RankingsSearchResponse
from easy_a.models import Course, CourseAttribute, SeatSnapshot, Section
from easy_a.rankings import RankingResolutionError, SectionRanking
from easy_a.rankings.cache import SectionRankingCache, hydrate_ranking
from easy_a.rankings.service import rank_course_sections, rank_section

router = APIRouter(prefix="/api/v1/rankings", tags=["rankings"])


@router.get("/section", response_model=SectionRanking)
def get_section_ranking(
    term: BannerTerm,
    crn: Annotated[str, Query(min_length=1, description="Term-scoped CRN.")],
    session: DbSession,
) -> SectionRanking:
    try:
        return rank_section(session, term=term, crn=crn)
    except RankingResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/course", response_model=list[SectionRanking])
def get_course_rankings(
    term: BannerTerm,
    subject: Annotated[str, Query(min_length=1)],
    course_number: Annotated[str, Query(min_length=1)],
    session: DbSession,
) -> list[SectionRanking]:
    try:
        return rank_course_sections(
            session,
            term=term,
            subject=subject,
            course_number=course_number,
        )
    except RankingResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/search", response_model=RankingsSearchResponse)
def search_rankings(
    term: BannerTerm,
    session: DbSession,
    subject: Annotated[str | None, Query(min_length=1)] = None,
    course_number: Annotated[str | None, Query(min_length=1)] = None,
    gened_code: Annotated[str | None, Query(min_length=1)] = None,
    delivery_method: Annotated[str | None, Query(min_length=1)] = None,
    seats_open: Annotated[bool, Query()] = False,
    min_easiness: Annotated[float | None, Query(ge=0.0, le=10.0)] = None,
    confidence: ConfidenceLabel | None = None,
    sort: RankingSort = RankingSort.easiness_desc,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RankingsSearchResponse:
    normalized_subject = _optional_upper(subject)
    normalized_course_number = _optional_upper(course_number)
    normalized_gened_code = _optional_upper(gened_code)
    normalized_delivery_method = _optional_upper(delivery_method)

    # The count and page-key queries read only narrow cache columns, and join latest seats
    # only when seats filter or order the results. Full rows and their latest seat snapshot
    # are then fetched for the requested page alone, so neither the latest-seat window nor
    # the wide cache payload is evaluated for every section in the term.
    seats_in_keys = seats_open or sort is RankingSort.seats_desc
    key_snapshot = _latest_snapshot()
    keys = select(
        SectionRankingCache.section_id,
        SectionRankingCache.subject,
        SectionRankingCache.course_number,
        SectionRankingCache.crn,
        SectionRankingCache.easiness_score,
        SectionRankingCache.smoothed_withdrawal_rate,
    ).where(SectionRankingCache.term == term)
    if seats_in_keys or normalized_gened_code is not None:
        keys = keys.join(Section, Section.id == SectionRankingCache.section_id)
    if seats_open:
        keys = _join_latest_snapshot(keys, key_snapshot)
    if normalized_subject is not None:
        keys = keys.where(SectionRankingCache.subject == normalized_subject)
    if normalized_course_number is not None:
        keys = keys.where(SectionRankingCache.course_number == normalized_course_number)
    if normalized_gened_code is not None:
        gened_match = exists(
            select(1)
            .select_from(Course)
            .join(CourseAttribute, CourseAttribute.course_id == Course.id)
            .where(
                Course.id == Section.course_id,
                func.upper(CourseAttribute.attribute_code) == normalized_gened_code,
            )
        )
        keys = keys.where(gened_match)
    if normalized_delivery_method is not None:
        keys = keys.where(
            func.upper(SectionRankingCache.delivery_method) == normalized_delivery_method
        )
    if seats_open:
        keys = keys.where(_effective_seats_remaining(key_snapshot) > 0)
    if min_easiness is not None:
        keys = keys.where(SectionRankingCache.easiness_score >= min_easiness)
    if confidence is not None:
        keys = keys.where(SectionRankingCache.confidence_label == confidence.value)

    total = session.scalar(select(func.count()).select_from(keys.subquery())) or 0

    if seats_in_keys and not seats_open:
        keys = _join_latest_snapshot(keys, key_snapshot)
    page_keys = (
        keys.order_by(*_search_order(sort, key_snapshot)).limit(limit).offset(offset).subquery()
    )
    page_section_ids = select(page_keys.c.section_id)
    page_snapshot = _latest_snapshot(section_ids=page_section_ids)
    rows = session.execute(
        select(
            SectionRankingCache,
            Section,
            page_snapshot.c.snapshot_id,
            page_snapshot.c.snapshot_observed_at,
            page_snapshot.c.snapshot_capacity,
            page_snapshot.c.snapshot_enrollment,
            page_snapshot.c.snapshot_seats_remaining,
            page_snapshot.c.snapshot_wait_seats_available,
        )
        .join(Section, Section.id == SectionRankingCache.section_id)
        .outerjoin(
            page_snapshot,
            page_snapshot.c.snapshot_section_id == SectionRankingCache.section_id,
        )
        .where(SectionRankingCache.section_id.in_(page_section_ids))
        .order_by(*_search_order(sort, page_snapshot))
    ).all()
    as_of = datetime.now(UTC)
    rankings: list[SectionRanking] = []
    for row in rows:
        cache_row = row[0]
        section = row[1]
        snapshot_id = row.snapshot_id
        snapshot = None
        if snapshot_id is not None:
            snapshot = SeatSnapshot(
                id=snapshot_id,
                section_id=cache_row.section_id,
                observed_at=row.snapshot_observed_at,
                capacity=row.snapshot_capacity,
                enrollment=row.snapshot_enrollment,
                seats_remaining=row.snapshot_seats_remaining,
                wait_seats_available=row.snapshot_wait_seats_available,
            )
        rankings.append(
            hydrate_ranking(
                session,
                cache_row,
                seat_snapshot=snapshot,
                seat_columns=section,
                as_of=as_of,
            )
        )

    return RankingsSearchResponse(
        items=rankings,
        total=total,
        limit=limit,
        offset=offset,
    )


def _latest_snapshot(section_ids: Select[Any] | None = None) -> Subquery:
    """Each section's latest seat snapshot: newest observed_at, then highest id."""
    ranked = select(
        SeatSnapshot.id.label("snapshot_id"),
        SeatSnapshot.section_id.label("snapshot_section_id"),
        SeatSnapshot.observed_at.label("snapshot_observed_at"),
        SeatSnapshot.capacity.label("snapshot_capacity"),
        SeatSnapshot.enrollment.label("snapshot_enrollment"),
        SeatSnapshot.seats_remaining.label("snapshot_seats_remaining"),
        SeatSnapshot.wait_seats_available.label("snapshot_wait_seats_available"),
        func.row_number()
        .over(
            partition_by=SeatSnapshot.section_id,
            order_by=(SeatSnapshot.observed_at.desc(), SeatSnapshot.id.desc()),
        )
        .label("snapshot_rank"),
    )
    if section_ids is not None:
        ranked = ranked.where(SeatSnapshot.section_id.in_(section_ids))
    ranked_snapshots = ranked.subquery()
    return (
        select(
            ranked_snapshots.c.snapshot_id,
            ranked_snapshots.c.snapshot_section_id,
            ranked_snapshots.c.snapshot_observed_at,
            ranked_snapshots.c.snapshot_capacity,
            ranked_snapshots.c.snapshot_enrollment,
            ranked_snapshots.c.snapshot_seats_remaining,
            ranked_snapshots.c.snapshot_wait_seats_available,
        )
        .where(ranked_snapshots.c.snapshot_rank == 1)
        .subquery()
    )


def _join_latest_snapshot(stmt: Select[Any], latest_snapshot: Subquery) -> Select[Any]:
    return stmt.outerjoin(
        latest_snapshot,
        latest_snapshot.c.snapshot_section_id == SectionRankingCache.section_id,
    )


def _effective_seats_remaining(latest_snapshot: Subquery) -> ColumnElement[Any]:
    return case(
        (
            latest_snapshot.c.snapshot_id.is_not(None),
            latest_snapshot.c.snapshot_seats_remaining,
        ),
        else_=Section.seats_remaining,
    )


def _search_order(
    sort: RankingSort,
    latest_snapshot: Subquery,
) -> tuple[ColumnElement[Any], ...]:
    course_tiebreak = (
        SectionRankingCache.subject.asc(),
        SectionRankingCache.course_number.asc(),
        SectionRankingCache.crn.asc(),
    )
    if sort is RankingSort.easiness_asc:
        return (SectionRankingCache.easiness_score.asc(), *course_tiebreak)
    if sort is RankingSort.withdrawal_asc:
        return (SectionRankingCache.smoothed_withdrawal_rate.asc(), *course_tiebreak)
    if sort is RankingSort.seats_desc:
        return (
            func.coalesce(_effective_seats_remaining(latest_snapshot), -1).desc(),
            *course_tiebreak,
        )
    if sort is RankingSort.course:
        return course_tiebreak
    return (SectionRankingCache.easiness_score.desc(), *course_tiebreak)


def _optional_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
