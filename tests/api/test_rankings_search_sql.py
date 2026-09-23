from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import Course, CourseAttribute, SeatSnapshot, Section, Term
from easy_a.rankings.cache import SectionRankingCache

NOW = datetime(2026, 9, 20, 12, tzinfo=UTC)


@pytest.fixture
def sql_search_session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        _seed_sql_search_data(session)
        session.commit()

    yield factory

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sql_search_client(
    sql_search_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        with sql_search_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("sort", "expected_crns"),
    [
        ("easiness_desc", ["30001", "20001", "10001", "40001", "10002"]),
        ("easiness_asc", ["40001", "10002", "20001", "10001", "30001"]),
        ("withdrawal_asc", ["40001", "10002", "30001", "10001", "20001"]),
        ("seats_desc", ["10001", "20001", "10002", "40001", "30001"]),
        ("course", ["40001", "30001", "20001", "10001", "10002"]),
    ],
)
def test_sql_search_orders_every_supported_sort_with_deterministic_ties(
    sql_search_client: TestClient,
    sort: str,
    expected_crns: list[str],
) -> None:
    response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "sort": sort},
    )

    assert response.status_code == 200
    assert [item["crn"] for item in response.json()["items"]] == expected_crns


def test_sql_search_total_matches_complete_paging_without_gaps_or_duplicates(
    sql_search_client: TestClient,
) -> None:
    first = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "sort": "course", "limit": 2, "offset": 0},
    )
    assert first.status_code == 200
    total = first.json()["total"]

    crns: list[str] = []
    for offset in range(0, total, 2):
        page = sql_search_client.get(
            "/api/v1/rankings/search",
            params={"term": "202701", "sort": "course", "limit": 2, "offset": offset},
        )
        assert page.status_code == 200
        assert page.json()["total"] == total
        crns.extend(item["crn"] for item in page.json()["items"])

    assert len(crns) == total == 5
    assert len(set(crns)) == total
    assert crns == ["40001", "30001", "20001", "10001", "10002"]


def test_sql_search_executes_one_count_and_one_page_query(
    sql_search_client: TestClient,
    sql_search_session_factory: sessionmaker[Session],
) -> None:
    engine = sql_search_session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    statements: list[str] = []

    def record_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        response = sql_search_client.get(
            "/api/v1/rankings/search",
            params={"term": "202701", "limit": 2},
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    assert response.status_code == 200
    selects = [
        statement
        for statement in statements
        if statement.lstrip().upper().startswith(("SELECT", "WITH"))
    ]
    assert len(selects) == 2
    assert all("section_rankings" in statement for statement in selects)


def test_sql_search_uses_live_snapshot_and_section_column_seat_fallbacks(
    sql_search_client: TestClient,
) -> None:
    response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "sort": "course"},
    )
    assert response.status_code == 200
    by_crn = {item["crn"]: item for item in response.json()["items"]}

    assert by_crn["10001"]["seats_remaining"] == 9
    assert by_crn["10001"]["seats"]["provenance"]["source"] == "seat_snapshots"
    assert by_crn["10002"]["seats_remaining"] == 0
    assert by_crn["20001"]["seats_remaining"] == 4
    assert (
        by_crn["20001"]["seats"]["provenance"]["source"]
        == "sections.current_seat_fields"
    )
    assert by_crn["30001"]["seats_remaining"] is None
    assert by_crn["30001"]["seats"]["freshness"] == "unavailable"

    open_response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "seats_open": True, "sort": "course"},
    )
    assert open_response.status_code == 200
    assert [item["crn"] for item in open_response.json()["items"]] == ["20001", "10001"]


@pytest.mark.parametrize(
    ("params", "expected_crns"),
    [
        ({"subject": "mac"}, {"10001", "10002"}),
        ({"course_number": "1105"}, {"10001", "10002"}),
        ({"gened_code": "smel"}, {"10001", "10002"}),
        ({"delivery_method": "hb"}, {"10002"}),
        ({"min_easiness": 8.5}, {"10001", "20001", "30001"}),
        ({"confidence": "high"}, {"10001", "30001"}),
    ],
)
def test_sql_search_applies_each_filter(
    sql_search_client: TestClient,
    params: dict[str, str | float],
    expected_crns: set[str],
) -> None:
    response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", **params},
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["crn"] for item in body["items"]} == expected_crns
    assert len(body["items"]) == body["total"] == len(expected_crns)


def test_sql_search_treats_sql_metacharacters_as_literal_filter_text(
    sql_search_client: TestClient,
) -> None:
    response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "subject": "MAC' OR 1=1 --"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def _record_selects(
    client: TestClient,
    session_factory: sessionmaker[Session],
    params: dict[str, str | bool],
) -> list[str]:
    engine = session_factory.kw["bind"]
    assert isinstance(engine, Engine)
    statements: list[str] = []

    def record_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        response = client.get("/api/v1/rankings/search", params={"term": "202701", **params})
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)
    assert response.status_code == 200
    return [s for s in statements if s.lstrip().upper().startswith(("SELECT", "WITH"))]


@pytest.mark.parametrize(
    ("params", "count_reads_seats"),
    [
        ({"sort": "easiness_desc"}, False),
        ({"sort": "seats_desc"}, False),
        ({"sort": "course", "seats_open": True}, True),
    ],
)
def test_sql_search_count_reads_seat_snapshots_only_when_seats_filter_it(
    sql_search_client: TestClient,
    sql_search_session_factory: sessionmaker[Session],
    params: dict[str, str | bool],
    count_reads_seats: bool,
) -> None:
    count_sql, page_sql = _record_selects(sql_search_client, sql_search_session_factory, params)

    assert ("seat_snapshots" in count_sql) is count_reads_seats
    assert "seat_snapshots" in page_sql


@pytest.mark.parametrize(
    "params",
    [
        {"sort": "seats_desc"},
        {"sort": "seats_desc", "seats_open": True},
        {"sort": "easiness_desc", "seats_open": True},
        {"sort": "withdrawal_asc"},
    ],
)
def test_sql_search_pages_concatenate_to_the_unpaged_order(
    sql_search_client: TestClient,
    params: dict[str, str | bool],
) -> None:
    full = sql_search_client.get(
        "/api/v1/rankings/search", params={"term": "202701", **params}
    ).json()
    paged: list[tuple[object, object]] = []
    for offset in range(0, full["total"] + 2, 2):
        page = sql_search_client.get(
            "/api/v1/rankings/search",
            params={"term": "202701", "limit": 2, "offset": offset, **params},
        ).json()
        assert page["total"] == full["total"]
        paged.extend((item["crn"], item["seats_remaining"]) for item in page["items"])

    assert paged == [(item["crn"], item["seats_remaining"]) for item in full["items"]]


def test_sql_search_breaks_equal_snapshot_times_by_highest_snapshot_id(
    sql_search_client: TestClient,
    sql_search_session_factory: sessionmaker[Session],
) -> None:
    with sql_search_session_factory() as session:
        section_id = session.query(Section.id).filter(Section.crn == "10001").scalar()
        session.add(
            SeatSnapshot(
                section_id=section_id,
                observed_at=NOW,
                capacity=30,
                enrollment=27,
                seats_remaining=3,
                wait_seats_available=0,
            )
        )
        session.commit()

    response = sql_search_client.get(
        "/api/v1/rankings/search",
        params={"term": "202701", "sort": "seats_desc"},
    )

    assert response.status_code == 200
    items = response.json()["items"]
    by_crn = {item["crn"]: item for item in items}
    assert by_crn["10001"]["seats_remaining"] == 3
    assert [item["crn"] for item in items] == ["20001", "10001", "10002", "40001", "30001"]


def _seed_sql_search_data(session: Session) -> None:
    session.add(Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"))
    courses = [
        Course(
            id=10,
            subject="MAC",
            number="1105",
            title="College Algebra",
            catalog_edition="2026-2027",
        ),
        Course(
            id=20,
            subject="ENC",
            number="1101",
            title="Composition I",
            catalog_edition="2026-2027",
        ),
        Course(
            id=30,
            subject="BSC",
            number="1005",
            title="Life Science",
            catalog_edition="2026-2027",
        ),
        Course(
            id=40,
            subject="ANT",
            number="2000",
            title="Introduction to Anthropology",
            catalog_edition="2026-2027",
        ),
    ]
    session.add_all(courses)
    session.add_all(
        [
            CourseAttribute(course_id=10, attribute_code="SMEL", attribute_label="Mathematics"),
            CourseAttribute(
                course_id=10,
                attribute_code="SMEL",
                attribute_label="Duplicate source row",
            ),
            CourseAttribute(course_id=20, attribute_code="WRIN", attribute_label="Writing"),
        ]
    )
    session.flush()

    specs = [
        (10, "10001", "CL", 2, 8.5, 0.10, "high"),
        (10, "10002", "HB", 7, 6.0, 0.05, "medium"),
        (20, "20001", "AD", 4, 8.5, 0.20, "low"),
        (30, "30001", "CL", None, 9.5, 0.08, "high"),
        (40, "40001", None, None, 6.0, 0.05, "medium"),
    ]
    for course_id, crn, delivery, section_seats, easiness, withdrawal, confidence in specs:
        course = next(course for course in courses if course.id == course_id)
        section = Section(
            term_id=1,
            crn=crn,
            course_id=course_id,
            section_number="001",
            campus="Tampa",
            session="Full Term",
            section_type="Class Lecture",
            primary_status="Active",
            delivery_method=delivery,
            capacity=30 if section_seats is not None else None,
            enrollment=30 - section_seats if section_seats is not None else None,
            seats_remaining=section_seats,
            wait_seats_available=0 if section_seats is not None else None,
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
        session.add(section)
        session.flush()
        session.add(
            SectionRankingCache(
                section_id=section.id,
                term="202701",
                term_name="Spring 2027",
                subject=course.subject,
                course_number=course.number,
                crn=crn,
                course_title=course.title,
                instructor=None,
                easiness_score=easiness,
                smoothed_withdrawal_rate=withdrawal,
                confidence_label=confidence,
                score_source="global",
                effective_n=0.0,
                delivery_method=delivery,
                historical_analytics=_historical_analytics(
                    easiness=easiness,
                    withdrawal=withdrawal,
                    confidence=confidence,
                ),
                gened_attributes=(
                    [{"code": "SMEL", "label": "Mathematics"}] if course_id == 10 else []
                ),
                signals=[],
                instructor_provenance=_provenance("unavailable", "section_instructors"),
                gened_provenance=_provenance("current", "course_attributes"),
                signal_provenance=_provenance("unavailable", "schedule/syllabi"),
                section_provenance=_provenance("current", "sections"),
                modality={
                    "delivery_method": delivery,
                    "delivery_label": None,
                    "provenance": _provenance("current", "sections.delivery_method"),
                },
            )
        )
        if crn == "10001":
            session.add_all(
                [
                    SeatSnapshot(
                        section_id=section.id,
                        observed_at=NOW - timedelta(minutes=1),
                        capacity=30,
                        enrollment=28,
                        seats_remaining=2,
                        wait_seats_available=0,
                    ),
                    SeatSnapshot(
                        section_id=section.id,
                        observed_at=NOW,
                        capacity=30,
                        enrollment=21,
                        seats_remaining=9,
                        wait_seats_available=0,
                    ),
                ]
            )
        elif crn == "10002":
            session.add(
                SeatSnapshot(
                    section_id=section.id,
                    observed_at=NOW,
                    capacity=30,
                    enrollment=30,
                    seats_remaining=0,
                    wait_seats_available=0,
                )
            )


def _historical_analytics(
    *, easiness: float, withdrawal: float, confidence: str
) -> dict[str, object]:
    return {
        "easiness_score": easiness,
        "smoothed_withdrawal_rate": withdrawal,
        "confidence_label": confidence,
        "effective_n": 0.0,
        "score_source": "global",
        "prior_level": "global",
        "completed_grade_count": 0,
        "total_grade_count": 0,
        "withdrawal_count": 0,
        "section_count": 0,
        "term_count": 0,
        "mapped_instructor_section_count": 0,
        "provenance": _provenance("unavailable", "grade_distributions"),
    }


def _provenance(freshness: str, source: str) -> dict[str, str | None]:
    return {
        "freshness": freshness,
        "source": source,
        "source_term": "202701",
        "detail": None,
    }
