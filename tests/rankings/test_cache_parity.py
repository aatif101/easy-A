from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib.util import find_spec
from inspect import signature
from typing import Any

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from easy_a.analytics.confidence import ConfidenceLabel, PriorLevel, ScoreSource
from easy_a.models import (
    Course,
    CourseAttribute,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
)
from easy_a.rankings.models import SectionRanking
from easy_a.rankings.service import rank_section

AS_OF = datetime(2026, 9, 20, 12, tzinfo=UTC)
OBSERVED_AT = AS_OF - timedelta(minutes=5)
SEAT_FIELDS = {"seats", "seats_remaining"}


def test_cache_module_contract_exists() -> None:
    spec = find_spec("easy_a.rankings.cache")

    assert spec is not None, "ranking cache module must provide the derived-cache spine"


def test_rank_section_accepts_explicit_as_of_for_deterministic_seat_parity() -> None:
    assert "as_of" in signature(rank_section).parameters


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
        on_demand = rank_section(
            db_session,
            term="202701",
            crn=cache_row.crn,
            as_of=AS_OF,
        )
        _assert_non_seat_parity(cached, on_demand)
        assert cached.seats == on_demand.seats
        assert cached.seats_remaining == on_demand.seats_remaining

    fallback = next(row for row in cached_rows if row.crn == no_history_section.crn)
    fallback_ranking = hydrate_ranking(db_session, fallback, as_of=AS_OF)
    assert fallback_ranking.score_source is ScoreSource.global_
    assert fallback_ranking.effective_n == 0
    assert fallback_ranking.historical_analytics.effective_n == 0
    assert fallback_ranking.instructor is None
    assert fallback_ranking.instructor_provenance.freshness.value == "unavailable"


def test_score_source_confidence_and_prior_branches_match_on_demand(
    db_session: Session,
) -> None:
    SectionRankingCache, hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    enc = _course(db_session, "ENC", "1101")
    mac_alt = _add_course(db_session, course_id=12, subject="MAC", number="2222")
    mac_fallback = _add_course(db_session, course_id=13, subject="MAC", number="9999")

    _add_grade(
        db_session,
        term_id=2,
        course_id=mac.id,
        crn="89031",
        a=300,
        b=0,
        w=0,
    )
    _add_grade(
        db_session,
        term_id=3,
        course_id=mac.id,
        crn="89032",
        a=300,
        b=0,
        w=0,
    )
    _add_section(
        db_session,
        term_id=2,
        course_id=mac.id,
        crn="89031",
        instructor="I. Rothstein",
    )
    _add_section(
        db_session,
        term_id=3,
        course_id=mac.id,
        crn="89032",
        instructor="I. Rothstein",
    )
    _add_grade(
        db_session,
        term_id=2,
        course_id=mac_alt.id,
        crn="88001",
        a=300,
        b=0,
        w=0,
    )

    _add_section(
        db_session,
        course_id=mac.id,
        crn="71001",
        instructor="I. Rothstein",
    )
    _add_section(db_session, course_id=mac.id, crn="71002", instructor=None)
    _add_section(db_session, course_id=mac_alt.id, crn="71003", instructor=None)
    _add_section(db_session, course_id=mac_fallback.id, crn="71004", instructor=None)
    _add_section(db_session, course_id=enc.id, crn="71005", instructor=None)
    db_session.commit()

    assert refresh_section_rankings(db_session, term="202701") == 5
    db_session.commit()

    cached_rows = db_session.scalars(
        select(SectionRankingCache).order_by(SectionRankingCache.crn)
    ).all()
    hydrated = [hydrate_ranking(db_session, row, as_of=AS_OF) for row in cached_rows]
    for cached in hydrated:
        _assert_full_parity(
            cached,
            rank_section(
                db_session,
                term="202701",
                crn=cached.crn,
                as_of=AS_OF,
            ),
        )

    assert {ranking.score_source for ranking in hydrated} == set(ScoreSource)
    assert {ranking.confidence_label for ranking in hydrated} == set(ConfidenceLabel)
    assert {
        ranking.historical_analytics.prior_level for ranking in hydrated
    } == set(PriorLevel)
    no_instructor = next(ranking for ranking in hydrated if ranking.crn == "71002")
    assert no_instructor.instructor_provenance.freshness.value == "unavailable"
    no_history = next(ranking for ranking in hydrated if ranking.crn == "71005")
    assert no_history.score_source is ScoreSource.global_
    assert no_history.effective_n == 0


def test_newer_seat_snapshot_is_live_without_mutating_cached_analytics(
    db_session: Session,
) -> None:
    SectionRankingCache, hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    _add_grade(db_session, course_id=mac.id, crn="89033", a=80, b=20, w=5)
    section = _add_section(
        db_session,
        course_id=mac.id,
        crn="72001",
        instructor="Staff",
    )
    _add_snapshot(db_session, section.id, seats_remaining=3)
    db_session.commit()
    refresh_section_rankings(db_session, term="202701")
    db_session.commit()

    cache_row = db_session.scalar(
        select(SectionRankingCache).where(SectionRankingCache.section_id == section.id)
    )
    assert cache_row is not None
    cached_score = cache_row.easiness_score
    cached_analytics = cache_row.historical_analytics.copy()

    newest_at = AS_OF - timedelta(minutes=1)
    db_session.add(
        SeatSnapshot(
            section_id=section.id,
            observed_at=newest_at,
            capacity=40,
            enrollment=29,
            seats_remaining=11,
            wait_seats_available=2,
        )
    )
    db_session.commit()

    hydrated = hydrate_ranking(db_session, cache_row, as_of=AS_OF)
    on_demand = rank_section(
        db_session,
        term="202701",
        crn=section.crn,
        as_of=AS_OF,
    )
    _assert_full_parity(hydrated, on_demand)
    assert hydrated.seats_remaining == 11
    assert hydrated.seats.observed_at == newest_at
    assert cache_row.easiness_score == cached_score
    assert cache_row.historical_analytics == cached_analytics


def test_cache_schema_excludes_all_seat_display_fields(db_session: Session) -> None:
    assert db_session.bind is not None
    columns = {
        column["name"]
        for column in inspect(db_session.bind).get_columns("section_rankings")
    }

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


def _assert_full_parity(cached: SectionRanking, on_demand: SectionRanking) -> None:
    assert cached.model_dump(mode="json") == on_demand.model_dump(mode="json")


def _course(session: Session, subject: str, number: str) -> Course:
    course = session.scalar(
        select(Course).where(Course.subject == subject, Course.number == number)
    )
    assert course is not None
    return course


def _add_course(session: Session, *, course_id: int, subject: str, number: str) -> Course:
    course = Course(
        id=course_id,
        subject=subject,
        number=number,
        title=f"{subject} {number}",
        catalog_edition="2026-2027",
    )
    session.add(course)
    session.flush()
    return course


def _add_grade(
    session: Session,
    *,
    term_id: int = 2,
    course_id: int,
    crn: str,
    a: int,
    b: int,
    w: int,
) -> None:
    session.add(
        GradeDistribution(
            term_id=term_id,
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
            source=f"cache-parity-{term_id}-{course_id}-{crn}",
            source_hash="cache-parity",
        )
    )


def _add_section(
    session: Session,
    *,
    term_id: int = 1,
    course_id: int,
    crn: str,
    instructor: str | None,
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


def test_whole_term_refresh_reads_grades_a_bounded_number_of_times(
    db_session: Session,
) -> None:
    _SectionRankingCache, _hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    _add_grade(db_session, course_id=mac.id, crn="89033", a=80, b=20, w=5)
    _add_section(db_session, course_id=mac.id, crn="70001", instructor="I. Rothstein")

    def grade_reads_for_refresh(extra_courses: range) -> int:
        for index in extra_courses:
            course = _add_course(
                db_session,
                course_id=200 + index,
                subject="ZZZ",
                number=f"4{index:03d}",
            )
            _add_section(db_session, course_id=course.id, crn=f"9{index:04d}", instructor=None)
        db_session.commit()
        statements: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany) -> None:
            statements.append(statement.lower())

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            refresh_section_rankings(db_session, term="202701")
        finally:
            event.remove(engine, "before_cursor_execute", record)
        db_session.rollback()
        return sum(
            statement.lstrip().startswith("select") and "grade_distributions" in statement
            for statement in statements
        )

    assert grade_reads_for_refresh(range(2)) == grade_reads_for_refresh(range(2, 14))


def test_signal_gened_and_instructor_branches_match_on_demand(db_session: Session) -> None:
    SectionRankingCache, hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    enc = _course(db_session, "ENC", "1101")
    db_session.add_all(
        [
            CourseAttribute(course_id=mac.id, attribute_code="SMT", attribute_label="Math"),
            CourseAttribute(course_id=mac.id, attribute_code="QR", attribute_label="Quant"),
        ]
    )
    current = _add_section(db_session, course_id=mac.id, crn="71001", instructor="I. Rothstein")
    _add_syllabus(db_session, document_id="cur", term_id=1, crn="71001", course_id=mac.id,
                  text="Attendance is required.", instructor="I. Rothstein")
    noted = _add_section(db_session, course_id=mac.id, crn="71002", instructor=None)
    noted.section_note = "Attendance is not required."
    _add_section(db_session, course_id=enc.id, crn="71003", instructor="Leslaw Skrzypek")
    _add_section(db_session, course_id=enc.id, crn="71004", instructor="Someone Else")
    ambiguous = _add_section(db_session, course_id=enc.id, crn="71005", instructor="A. One")
    db_session.add(
        SectionInstructor(section_id=ambiguous.id, name_raw="B. Two", name_normalized="b. two",
                          source="cache-parity", observed_at=AS_OF)
    )
    _add_syllabus(db_session, document_id="old-same", term_id=2, crn="89001", course_id=enc.id,
                  text="No curve will be applied.", instructor="Leslaw Skrzypek")
    _add_syllabus(db_session, document_id="old-other", term_id=2, crn="89002", course_id=enc.id,
                  text="Attendance is required.", instructor="Other Person")
    db_session.commit()
    assert current.id and noted.id

    assert refresh_section_rankings(db_session, term="202701") == 5
    db_session.commit()

    signal_sources = set()
    for cache_row in db_session.scalars(select(SectionRankingCache)).all():
        cached = hydrate_ranking(db_session, cache_row, as_of=AS_OF)
        on_demand = rank_section(db_session, term="202701", crn=cache_row.crn, as_of=AS_OF)
        _assert_full_parity(cached, on_demand)
        signal_sources.add(cached.signal_provenance.source)
    assert signal_sources >= {
        "current_term_syllabus",
        "schedule_section_note",
        "historical_same_instructor_course",
        "historical_same_course",
    }


def test_whole_term_refresh_statement_count_does_not_grow_with_sections(
    db_session: Session,
) -> None:
    _SectionRankingCache, _hydrate_ranking, refresh_section_rankings = _cache_api()
    mac = _course(db_session, "MAC", "1105")
    _add_grade(db_session, course_id=mac.id, crn="89033", a=80, b=20, w=5)
    _add_section(db_session, course_id=mac.id, crn="70001", instructor="I. Rothstein")

    def statements_for_refresh(extra_courses: range) -> int:
        for index in extra_courses:
            course = _add_course(
                db_session, course_id=300 + index, subject="ZZZ", number=f"5{index:03d}"
            )
            _add_section(db_session, course_id=course.id, crn=f"8{index:04d}", instructor="X Y")
        db_session.commit()
        refresh_section_rankings(db_session, term="202701")
        db_session.commit()
        count = 0

        def record(conn, cursor, statement, parameters, context, executemany) -> None:
            nonlocal count
            count += 1

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            refresh_section_rankings(db_session, term="202701")
        finally:
            event.remove(engine, "before_cursor_execute", record)
        db_session.rollback()
        return count

    assert statements_for_refresh(range(2)) == statements_for_refresh(range(2, 14))


def _add_syllabus(
    session: Session,
    *,
    document_id: str,
    term_id: int,
    crn: str,
    course_id: int,
    text: str,
    instructor: str,
) -> None:
    session.add(
        Syllabus(
            document_id=document_id,
            term_id=term_id,
            crn=crn,
            course_id=course_id,
            section_number="001",
            instructor_raw=instructor,
            title="Syllabus",
            view_url=f"https://example.test/{document_id}",
            fetched_at=AS_OF,
            content_html=f"<p>{text}</p>",
            content_text=text,
            content_hash=document_id.ljust(64, "0")[:64],
        )
    )
