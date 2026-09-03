from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from easy_a.analytics.confidence import ConfidenceLabel
from easy_a.api.dependencies import BannerTerm, DbSession
from easy_a.api.schemas import RankingSort, RankingsSearchResponse
from easy_a.models import Course, CourseAttribute, Section, Term
from easy_a.rankings import RankingResolutionError, SectionRanking
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
    rankings = [
        ranking
        for ranking in _rank_candidate_sections(
            session,
            term=term,
            subject=subject,
            course_number=course_number,
            gened_code=gened_code,
            delivery_method=delivery_method,
        )
        if _matches_derived_filters(
            ranking,
            seats_open=seats_open,
            min_easiness=min_easiness,
            confidence=confidence,
        )
    ]
    rankings.sort(key=lambda ranking: _ranking_sort_key(ranking, sort))
    total = len(rankings)
    return RankingsSearchResponse(
        items=rankings[offset : offset + limit],
        total=total,
        limit=limit,
        offset=offset,
    )


def _rank_candidate_sections(
    session: DbSession,
    *,
    term: str,
    subject: str | None,
    course_number: str | None,
    gened_code: str | None,
    delivery_method: str | None,
) -> list[SectionRanking]:
    normalized_subject = _optional_upper(subject)
    normalized_course_number = _optional_upper(course_number)
    normalized_gened_code = _optional_upper(gened_code)
    normalized_delivery_method = _optional_upper(delivery_method)

    stmt = (
        select(Section.crn)
        .join(Term, Section.term_id == Term.id)
        .join(Course, Section.course_id == Course.id)
        .where(Term.banner_code == term)
    )
    if normalized_subject is not None:
        stmt = stmt.where(Course.subject == normalized_subject)
    if normalized_course_number is not None:
        stmt = stmt.where(Course.number == normalized_course_number)
    if normalized_gened_code is not None:
        stmt = stmt.join(CourseAttribute, CourseAttribute.course_id == Course.id).where(
            func.upper(CourseAttribute.attribute_code) == normalized_gened_code
        )
    if normalized_delivery_method is not None:
        stmt = stmt.where(func.upper(Section.delivery_method) == normalized_delivery_method)

    crns = list(
        session.execute(
            stmt.distinct().order_by(Course.subject, Course.number, Section.crn)
        ).scalars()
    )
    rankings: list[SectionRanking] = []
    for crn in crns:
        try:
            rankings.append(rank_section(session, term=term, crn=crn))
        except RankingResolutionError:
            continue
    return rankings


def _matches_derived_filters(
    ranking: SectionRanking,
    *,
    seats_open: bool,
    min_easiness: float | None,
    confidence: ConfidenceLabel | None,
) -> bool:
    if seats_open and (ranking.seats_remaining is None or ranking.seats_remaining <= 0):
        return False
    if min_easiness is not None and ranking.easiness_score < min_easiness:
        return False
    return not (confidence is not None and ranking.confidence_label is not confidence)


def _ranking_sort_key(
    ranking: SectionRanking,
    sort: RankingSort,
) -> tuple[float | str, ...]:
    course_tiebreak = (ranking.subject, ranking.course_number, ranking.crn)
    if sort is RankingSort.easiness_asc:
        return (ranking.easiness_score, *course_tiebreak)
    if sort is RankingSort.withdrawal_asc:
        return (ranking.smoothed_withdrawal_rate, *course_tiebreak)
    if sort is RankingSort.seats_desc:
        seats_remaining = ranking.seats_remaining if ranking.seats_remaining is not None else -1
        return (-float(seats_remaining), *course_tiebreak)
    if sort is RankingSort.course:
        return course_tiebreak
    return (-ranking.easiness_score, *course_tiebreak)


def _optional_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
