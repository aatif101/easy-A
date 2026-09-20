from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib.util import find_spec
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ScoreSource
from easy_a.models import Course, GradeDistribution, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.models import SectionRanking
from easy_a.rankings.service import rank_section

AS_OF = datetime(2026, 9, 20, 12, tzinfo=UTC)
OBSERVED_AT = AS_OF - timedelta(minutes=5)
SEAT_FIELDS = {"seats", "seats_remaining"}


def test_cache_module_contract_exists() -> None:
    spec = find_spec("easy_a.rankings.cache")

    assert spec is not None, "ranking cache module must provide the derived-cache spine"


def test_cached_rankings_match_on_demand_for_history_and_global_fallback(
    db_session: Session,
) -> None:
    SectionRankingCache, hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    enc = _course(db_session, "ENC", "1101")
    _add_grade(db_session, course_id=mac.id, crn="89033", a=80, b=20, w=5)
    history_section = _add_section(
        db_session,
        course_id=mac.id,
        crn="70001",
        instructor="I. Rothstein",
    )
    no_history_section = _add_section(
        db_session,
        course_id=enc.id,
        crn="70002",
        instructor=None,
    )
    _add_snapshot(db_session, history_section.id, seats_remaining=3)
    db_session.commit()

    assert refresh_section_rankings(db_session, term="202701") == 2
    db_session.commit()

    cached_rows = db_session.scalars(
        select(SectionRankingCache).order_by(SectionRankingCache.crn)
    ).all()
    assert [row.crn for row in cached_rows] == ["70001", "70002"]

    for cache_row in cached_rows:
        cached = hydrate_ranking(db_session, cache_row, as_of=AS_OF)
        on_demand = rank_section(db_session, term="202701", crn=cache_row.crn)
        _assert_non_seat_parity(cached, on_demand)

    fallback = next(row for row in cached_rows if row.crn == no_history_section.crn)
    fallback_ranking = hydrate_ranking(db_session, fallback, as_of=AS_OF)
    assert fallback_ranking.score_source is ScoreSource.global_
    assert fallback_ranking.effective_n == 0
    assert fallback_ranking.historical_analytics.effective_n == 0
    assert fallback_ranking.instructor is None
    assert fallback_ranking.instructor_provenance.freshness.value == "unavailable"


def test_cache_schema_excludes_all_seat_display_fields(db_session: Session) -> None:
    columns = {column["name"] for column in inspect(db_session.bind).get_columns("section_rankings")}

    assert {
        "observed_at",
        "freshness",
        "age_seconds",
        "seats_remaining",
        "capacity",
        "enrollment",
        "wait_seats_available",
    }.isdisjoint(columns)


def _cache_api() -> tuple[type[Any], Any, Any]:
    from easy_a.rankings.cache import (
        SectionRankingCache,
        hydrate_ranking,
        refresh_section_rankings,
    )

    return SectionRankingCache, hydrate_ranking, refresh_section_rankings


def _assert_non_seat_parity(cached: SectionRanking, on_demand: SectionRanking) -> None:
    field_names = set(SectionRanking.model_fields) - SEAT_FIELDS
    cached_values = cached.model_dump(mode="json")
    on_demand_values = on_demand.model_dump(mode="json")

    assert {name: cached_values[name] for name in field_names} == {
        name: on_demand_values[name] for name in field_names
    }


def _course(session: Session, subject: str, number: str) -> Course:
    return session.scalar(select(Course).where(Course.subject == subject, Course.number == number))  # type: ignore[return-value]


def _add_grade(
    session: Session,
    *,
    course_id: int,
    crn: str,
    a: int,
    b: int,
    w: int,
) -> None:
    session.add(
        GradeDistribution(
            term_id=2,
            crn=crn,
            course_id=course_id,
            section_number_raw="001",
            section_suffix_raw="C",
            campus_raw="Tampa",
            a_count=a,
            b_count=b,
            c_count=0,
            d_count=0,
            f_count=0,
            i_count=0,
            s_count=0,
            u_count=0,
            w_count=w,
            other_count=0,
            total_grades=a + b + w,
            source=f"cache-parity-{course_id}-{crn}",
            source_hash="cache-parity",
        )
    )


def _add_section(
    session: Session,
    *,
    course_id: int,
    crn: str,
    instructor: str | None,
) -> Section:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        capacity=40,
        enrollment=37,
        seats_remaining=3,
        wait_seats_available=0,
        first_seen_at=AS_OF,
        last_seen_at=AS_OF,
    )
    session.add(section)
    session.flush()
    if instructor is not None:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=instructor,
                name_normalized=instructor.lower(),
                source="cache-parity",
                observed_at=AS_OF,
            )
        )
    return section


def _add_snapshot(session: Session, section_id: int, *, seats_remaining: int) -> None:
    session.add(
        SeatSnapshot(
            section_id=section_id,
            observed_at=OBSERVED_AT,
            capacity=40,
            enrollment=40 - seats_remaining,
            seats_remaining=seats_remaining,
            wait_seats_available=0,
        )
    )
