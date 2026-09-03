from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import (
    Course,
    CourseAttribute,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
    Term,
)

NOW = datetime(2026, 9, 1, tzinfo=UTC)


@pytest.fixture
def api_session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    local_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with local_session_factory() as session:
        _seed_reference_data(session)
        session.commit()

    yield local_session_factory

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def api_client(
    api_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        with api_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_section_ranking_endpoint_returns_typed_ranking(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/section?term=202701&crn=70001")

    assert response.status_code == 200
    body = response.json()
    assert body["term"] == "202701"
    assert body["crn"] == "70001"
    assert body["subject"] == "MAC"
    assert body["course_number"] == "1105"
    assert body["seats_remaining"] == 5
    assert body["gened_attributes"] == [
        {"code": "SMEL", "label": "Enhanced General Education Mathematics"}
    ]


def test_course_rankings_endpoint_returns_all_sections(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get(
        "/api/v1/rankings/course?term=202701&subject=MAC&course_number=1105"
    )

    assert response.status_code == 200
    assert [item["crn"] for item in response.json()] == ["70001", "70002"]


def test_search_rankings_by_term(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert {item["crn"] for item in body["items"]} == {"70001", "70002", "71001", "72001"}


def test_search_filters_by_gened(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&gened_code=SMEL")

    assert response.status_code == 200
    assert {item["subject"] for item in response.json()["items"]} == {"MAC"}


def test_search_filters_by_delivery_method(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&delivery_method=HB")

    assert response.status_code == 200
    assert [item["crn"] for item in response.json()["items"]] == ["70002"]


def test_search_filters_to_open_seats(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&seats_open=true")

    assert response.status_code == 200
    assert {item["crn"] for item in response.json()["items"]} == {"70001", "72001"}


def test_search_filters_by_minimum_easiness(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&min_easiness=9.5")

    assert response.status_code == 200
    assert [item["crn"] for item in response.json()["items"]] == ["72001"]


def test_search_filters_by_confidence(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&confidence=high")

    assert response.status_code == 200
    assert [item["crn"] for item in response.json()["items"]] == ["72001"]


def test_search_sorts_by_easiness(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&sort=easiness_asc")

    assert response.status_code == 200
    easiness_scores = [item["easiness_score"] for item in response.json()["items"]]
    assert easiness_scores == sorted(easiness_scores)


def test_search_sorts_by_seats(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/search?term=202701&sort=seats_desc")

    assert response.status_code == 200
    seats = [item["seats_remaining"] for item in response.json()["items"]]
    assert seats[:2] == [20, 5]
    assert seats[-1] is None


def test_search_paginates_after_filtering_and_sorting(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get(
        "/api/v1/rankings/search?term=202701&sort=course&limit=2&offset=1"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["crn"] for item in body["items"]] == ["71001", "70001"]


def test_missing_section_returns_404(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/section?term=202701&crn=99999")

    assert response.status_code == 404


def test_invalid_term_returns_validation_error(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/rankings/section?term=202713&crn=70001")

    assert response.status_code == 422


def test_non_grade_context_changes_do_not_change_score(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    before = api_client.get("/api/v1/rankings/section?term=202701&crn=70002")
    assert before.status_code == 200

    with api_session_factory() as session:
        section = session.execute(select(Section).where(Section.crn == "70002")).scalar_one()
        section.delivery_method = "AD"
        section.seats_remaining = 99
        session.add(
            SeatSnapshot(
                section_id=section.id,
                observed_at=NOW + timedelta(days=1),
                capacity=120,
                enrollment=20,
                seats_remaining=100,
                wait_seats_available=5,
            )
        )
        session.add(
            Syllabus(
                document_id="current-policy-change",
                section_id=section.id,
                term_id=1,
                crn=section.crn,
                course_id=section.course_id,
                section_number="001",
                instructor_raw="Staff",
                organization="Synthetic",
                title="Synthetic current syllabus",
                view_url="https://example.test/current-policy-change",
                fetched_at=NOW + timedelta(days=1),
                content_html="<p>Attendance is required.</p>",
                content_text="Attendance is required.",
                content_hash="current-policy-change".ljust(64, "0")[:64],
            )
        )
        session.commit()

    after = api_client.get("/api/v1/rankings/section?term=202701&crn=70002")

    assert after.status_code == 200
    assert after.json()["easiness_score"] == pytest.approx(before.json()["easiness_score"])
    assert after.json()["smoothed_withdrawal_rate"] == pytest.approx(
        before.json()["smoothed_withdrawal_rate"]
    )
    assert after.json()["seats_remaining"] == 100
    assert after.json()["signal_provenance"]["source"] == "current_term_syllabus"


def test_response_provenance_is_preserved(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    response = api_client.get("/api/v1/rankings/section?term=202701&crn=70001")

    assert response.status_code == 200
    body = response.json()
    assert body["section_provenance"]["source"] == "sections"
    assert body["section_provenance"]["freshness"] == "current"
    assert body["historical_analytics"]["provenance"]["source"] == "grade_distributions"
    assert body["historical_analytics"]["provenance"]["freshness"] == "historical"
    assert body["signal_provenance"]["source"] == "schedule_section_note"
    assert body["signal_provenance"]["freshness"] == "current"
    assert {signal["freshness"] for signal in body["signals"]} == {"current"}


def test_metadata_endpoints_use_canonical_db_data(
    api_client: TestClient,
    api_session_factory: sessionmaker[Session],
) -> None:
    with api_session_factory() as session:
        _seed_search_data(session)
        session.commit()

    terms_response = api_client.get("/api/v1/metadata/terms")
    subjects_response = api_client.get("/api/v1/metadata/subjects")
    gened_response = api_client.get("/api/v1/metadata/gened-attributes")
    delivery_response = api_client.get("/api/v1/metadata/delivery-methods")

    assert terms_response.status_code == 200
    assert subjects_response.status_code == 200
    assert gened_response.status_code == 200
    assert delivery_response.status_code == 200
    assert {"term": "202701", "term_name": "Spring 2027", "year": 2027, "season": "Spring"} in (
        terms_response.json()
    )
    assert {item["subject"] for item in subjects_response.json()} == {"BSC", "ENC", "MAC"}
    assert {"code": "SMEL", "label": "Enhanced General Education Mathematics"} in (
        gened_response.json()
    )
    assert {"code": "HB", "label": "Hybrid Blend 50–79%"} in delivery_response.json()


def _seed_reference_data(session: Session) -> None:
    session.add_all(
        [
            Term(
                id=1,
                banner_code="202701",
                name="Spring 2027",
                year=2027,
                season="Spring",
            ),
            Term(
                id=2,
                banner_code="202408",
                name="Fall 2024",
                year=2024,
                season="Fall",
            ),
            Term(
                id=3,
                banner_code="202605",
                name="Summer 2026",
                year=2026,
                season="Summer",
            ),
            Course(
                id=10,
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            ),
            Course(
                id=11,
                subject="ENC",
                number="1101",
                title="Composition I",
                catalog_edition="2026-2027",
            ),
            Course(
                id=12,
                subject="BSC",
                number="1005",
                title="Life Science",
                catalog_edition="2026-2027",
            ),
        ]
    )


def _seed_search_data(session: Session) -> None:
    session.add(
        CourseAttribute(
            course_id=10,
            attribute_code="SMEL",
            attribute_label="Enhanced General Education Mathematics",
        )
    )
    session.add(
        CourseAttribute(
            course_id=11,
            attribute_code="WRIN",
            attribute_label="Enhanced General Education Writing Intensive",
        )
    )
    _add_grade(session, term_id=2, crn="89033", course_id=10, a=40, b=10, w=5)
    _add_grade(session, term_id=2, crn="88001", course_id=11, f=20, w=20)
    _add_grade(session, term_id=2, crn="98001", course_id=12, a=100)
    _add_grade(session, term_id=3, crn="98002", course_id=12, a=100)
    _add_section(
        session,
        term_id=1,
        crn="70001",
        course_id=10,
        instructor="Staff",
        delivery_method="CL",
        seats_remaining=5,
        note="Attendance is required. Exams are in person in the SMART Lab.",
    )
    _add_section(
        session,
        term_id=1,
        crn="70002",
        course_id=10,
        instructor="Staff",
        delivery_method="HB",
        seats_remaining=0,
    )
    _add_section(
        session,
        term_id=1,
        crn="71001",
        course_id=11,
        instructor="Dr. Booker",
        delivery_method="AD",
        seats_remaining=None,
    )
    _add_section(
        session,
        term_id=1,
        crn="72001",
        course_id=12,
        instructor="Dr. Chen",
        delivery_method="CL",
        seats_remaining=20,
    )


def _add_grade(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    w: int = 0,
) -> None:
    completed = a + b + c + d + f
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
            c_count=c,
            d_count=d,
            f_count=f,
            i_count=0,
            s_count=0,
            u_count=0,
            w_count=w,
            other_count=0,
            total_grades=completed + w,
            source=f"synthetic-{term_id}-{crn}-{course_id}-{a}-{b}-{c}-{d}-{f}-{w}",
            source_hash="synthetic",
        )
    )


def _add_section(
    session: Session,
    *,
    term_id: int,
    crn: str,
    course_id: int,
    instructor: str,
    delivery_method: str | None,
    seats_remaining: int | None,
    note: str | None = None,
) -> None:
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
        delivery_method=delivery_method,
        capacity=30 if seats_remaining is not None else None,
        enrollment=(30 - seats_remaining) if seats_remaining is not None else None,
        seats_remaining=seats_remaining,
        wait_seats_available=0 if seats_remaining is not None else None,
        section_note=note,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=instructor.lower(),
            source="synthetic",
            observed_at=NOW,
        )
    )
