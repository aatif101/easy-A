from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from easy_a.api.app import create_app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import Course, GradeDistribution, Section, SectionInstructor, Term

NOW = datetime(2026, 10, 7, tzinfo=UTC)


@pytest.fixture
def discovery_client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
                Term(id=2, banner_code="202601", name="Spring 2026", year=2026, season="Spring"),
                Term(id=3, banner_code="202508", name="Fall 2025", year=2025, season="Fall"),
            ]
        )
        for course_id, subject, number, title in [
            (1, "ENC", "1101", "Composition I"),
            (2, "ABC", "1101", "Program Design"),
            (3, "MAC", "2311", "Calculus I"),
            (4, "MAC", "2312", "Calculus II"),
            (5, "CHM", "2045L", "General Chemistry Laboratory"),
            (6, "CDA", "3103", "Program Design"),
        ]:
            session.add(
                Course(
                    id=course_id,
                    subject=subject,
                    number=number,
                    title=title,
                    catalog_edition="2026-2027",
                )
            )
        session.flush()

        def seed(
            section_id: int,
            course_id: int,
            term_id: int,
            names: list[str],
            *,
            lab: bool = False,
            grades: int = 50,
            removed: bool = False,
        ) -> None:
            session.add(
                Section(
                    id=section_id,
                    term_id=term_id,
                    course_id=course_id,
                    crn="14028" if section_id == 1 else str(20000 + section_id),
                    section_number="001",
                    campus="Tampa",
                    session="Regular",
                    section_type="Laboratory" if lab else "Lecture",
                    primary_status="Active",
                    first_seen_at=NOW,
                    last_seen_at=NOW,
                    removed_at=NOW if removed else None,
                )
            )
            session.flush()
            for name in names:
                session.add(
                    SectionInstructor(
                        section_id=section_id, name_raw=name, source="usf_schedule", observed_at=NOW
                    )
                )
            if term_id != 1:
                session.add(
                    GradeDistribution(
                        term_id=term_id,
                        crn=str(20000 + section_id),
                        course_id=course_id,
                        section_number_raw="001",
                        a_count=grades,
                        b_count=10,
                        total_grades=grades + 10,
                        source="usf_infocenter",
                        source_hash="a" * 64,
                        ingested_at=NOW,
                    )
                )

        seed(1, 1, 1, ["J. Smith"])
        seed(2, 1, 2, ["J. Smith"])
        seed(3, 2, 2, ["J. Smith"], grades=2)
        seed(4, 6, 3, ["Program Design"])
        seed(5, 6, 2, ["Program Design"])
        seed(6, 3, 1, ["Staff"])
        seed(7, 3, 2, ["", ""])
        seed(8, 3, 2, ["Wrong Person", "Other Person"])
        seed(9, 3, 2, ["Unavailable"])
        seed(10, 1, 2, ["J. Smith"], lab=True, grades=900)
        seed(11, 3, 1, ["Old Name"])
        session.add(
            SectionInstructor(
                section_id=11,
                name_raw="New Name",
                source="usf_schedule",
                observed_at=NOW + timedelta(hours=1),
            )
        )
        seed(12, 3, 1, ["Removed Person"], removed=True)
        seed(13, 5, 2, ["Zero Grades"], grades=0)
        # A current name containing the MAC subject code.
        seed(30, 5, 1, ["C. Maclean"])
        session.flush()
        zero = session.query(GradeDistribution).filter_by(crn="20013").one()
        zero.b_count = 0
        zero.s_count = 10
        seed(14, 5, 2, ["Changed Person"])
        session.add(
            SectionInstructor(
                section_id=14,
                name_raw="Different Person",
                source="usf_schedule",
                observed_at=NOW + timedelta(hours=1),
            )
        )
        session.commit()

    app = create_app()

    def db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = db
    with TestClient(app) as client:
        yield client
    engine.dispose()


def search(client: TestClient, q: str, **params: Any) -> dict[str, Any]:
    response = client.get("/api/v1/search", params={"term": "202701", "q": q, **params})
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


@pytest.mark.parametrize(
    ("q", "ids"),
    [
        ("14028", [1]),
        (" enc1101 ", [1]),
        ("E.N.C. 1101", [1]),
        ("ENC - 11 01", [1]),
        ("1101", [2, 1]),
        ("2045l", [5]),
        ("program-design", [2, 6]),
        (" Program   Design ", [2, 6]),
        ("calculus 1", [3]),
        ("CALCULUS I", [3]),
        ("calculus 2", [4]),
        ("MAC", [3, 4]),
        ("no match", []),
        ("%", []),
        ("   ", []),
    ],
)
def test_search_types(discovery_client: TestClient, q: str, ids: list[int]) -> None:
    assert [row["course_id"] for row in search(discovery_client, q)["courses"]] == ids


def test_mixed_and_historical_only(discovery_client: TestClient) -> None:
    result = search(discovery_client, "program design")
    assert result["course_total"] == 2
    instructor = result["instructors"][0]
    assert instructor["name"] == "Program Design"
    assert instructor["current_sections"] == 0
    assert instructor["historical_sections"] == 2
    assert "not proof" in result["identity_note"]


def test_same_name_kept_separate_by_course_and_initials_never_expanded(
    discovery_client: TestClient,
) -> None:
    result = search(discovery_client, " j smith ")
    assert [(row["course_id"], row["name"]) for row in result["instructors"]] == [
        (2, "J. Smith"),
        (1, "J. Smith"),
    ]
    assert search(discovery_client, "John Smith")["instructor_total"] == 0
    assert search(discovery_client, "smith")["instructor_total"] == 2


@pytest.mark.parametrize(
    "name",
    [
        "staff",
        "unavailable",
        "Wrong Person",
        "Other Person",
        "Old Name",
        "Removed Person",
        "Changed Person",
        "Different Person",
    ],
)
def test_unavailable_ambiguous_and_stale_names_excluded(
    discovery_client: TestClient, name: str
) -> None:
    assert search(discovery_client, name)["instructor_total"] == 0


def test_short_instructor_name_can_match_subject_shaped_query(discovery_client: TestClient) -> None:
    result = search(discovery_client, "New")
    assert result["kind"] == "text"
    assert result["instructor_total"] == 1


@pytest.mark.parametrize("q", ["MAC", "mac", "ENC 1101", "1101", "14028"])
def test_code_shaped_queries_never_match_instructor_names(
    discovery_client: TestClient, q: str
) -> None:
    # A real subject, course code, number or CRN is not a name fragment.
    assert search(discovery_client, "maclean")["instructor_total"] == 1
    assert search(discovery_client, q)["instructor_total"] == 0


def test_pagination_both_categories(discovery_client: TestClient) -> None:
    first = search(discovery_client, "program design", limit=1)
    second = search(discovery_client, "program design", limit=1, offset=1)
    assert first["course_total"] == second["course_total"] == 2
    assert first["courses"][0]["course_id"] != second["courses"][0]["course_id"]
    assert second["instructors"] == []


def get_history(client: TestClient, **params: Any) -> dict[str, Any]:
    response = client.get("/api/v1/search/history", params={"term": "202701", **params})
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def test_history_raw_buckets_provenance_lab_exclusion_and_separate_identities(
    discovery_client: TestClient,
) -> None:
    history = get_history(discovery_client, course_id=1, name="J. Smith")
    assert history["observed_grade_count"] == 60
    assert history["a_share"] == pytest.approx(50 / 60)
    assert history["terms"] == ["202601"]
    assert history["items"][0]["source_hash"] == "a" * 64
    assert history["items"][0]["ingested_at"]
    assert "easiness_score" not in history
    other = get_history(discovery_client, course_id=2, name="J. Smith")
    assert other["observed_grade_count"] == 12
    assert other["status"] == "insufficient"


def test_multi_term_historical_only_history_and_paging(discovery_client: TestClient) -> None:
    history = get_history(discovery_client, course_id=6, name="Program Design", limit=1)
    assert history["terms"] == ["202508", "202601"]
    assert history["total"] == 2
    assert len(history["items"]) == 1
    assert history["observed_grade_count"] == 120
    assert (
        get_history(discovery_client, course_id=6, name="Program Design", limit=1, offset=1)[
            "items"
        ][0]["term"]
        == "202508"
    )


@pytest.mark.parametrize(
    "name", ["Staff", "Unavailable", "Wrong Person", "Changed Person", "Different Person"]
)
def test_unsafe_history_not_attributed(discovery_client: TestClient, name: str) -> None:
    for course_id in (1, 3, 5):
        result = get_history(discovery_client, course_id=course_id, name=name)
        assert result["status"] == "unavailable"
        assert result["a_share"] is None


def test_course_history_and_no_letter_grade_states(discovery_client: TestClient) -> None:
    assert get_history(discovery_client, course_id=1)["observed_grade_count"] == 970
    zero = get_history(discovery_client, course_id=5, name="Zero Grades")
    assert zero["status"] == "no_letter_grades"
    assert zero["a_share"] is None
    assert zero["counts"]["s"] == 10


@pytest.mark.parametrize(
    "params", [{"limit": 51}, {"offset": -1}, {"q": "x" * 201}, {"term": "invalid"}]
)
def test_search_bounds(discovery_client: TestClient, params: dict[str, Any]) -> None:
    assert (
        discovery_client.get(
            "/api/v1/search", params={"term": "202701", "q": "test", **params}
        ).status_code
        == 422
    )


def test_history_unknown_course(discovery_client: TestClient) -> None:
    assert (
        discovery_client.get(
            "/api/v1/search/history", params={"term": "202701", "course_id": 999}
        ).status_code
        == 404
    )


def test_long_stored_names_and_titles(discovery_client: TestClient) -> None:
    db = discovery_client.app.dependency_overrides[get_db_session]()
    session = next(db)
    name = "Program Design " + "Long Stored Name " * 10
    course = session.get(Course, 6)
    assert course is not None
    course.title = "Program Design " + "Long Stored Title " * 10
    session.query(SectionInstructor).filter_by(name_raw="Program Design").update({"name_raw": name})
    session.commit()
    db.close()
    result = search(discovery_client, "Program Design")
    assert result["instructors"][0]["name"] == name.strip()
    history = get_history(discovery_client, course_id=6, name=name.strip())
    assert history["observed_grade_count"] == 120
    assert history["status"] == "available"


def test_discovery_has_fixed_read_only_query_count(discovery_client: TestClient) -> None:
    db = discovery_client.app.dependency_overrides[get_db_session]()
    session = next(db)
    engine = session.get_bind()
    assert isinstance(engine, Engine)
    db.close()
    statements: list[str] = []

    def record(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        result = search(discovery_client, "Program Design", limit=1)
        assert len(result["courses"]) == len(result["instructors"]) == 1
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert len(statements) == 4
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
