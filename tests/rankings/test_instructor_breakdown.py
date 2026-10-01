from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.analytics.queries import get_instructor_course_historical_outcome_stats
from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    Section,
    SectionInstructor,
    Term,
)
from easy_a.rankings.cache import refresh_section_rankings

NOW = datetime(2026, 9, 1, tzinfo=UTC)

# The key sets web/src/types/rankings.ts (plan 10-04) implements. Changing either side without
# the other breaks the UI, so the tests pin them literally.
BREAKDOWN_KEYS = {
    "status",
    "instructors",
    "current_instructor",
    "current_instructor_has_history",
    "other_instructor_count",
    "scoring_min_effective_n",
    "collapse_min_effective_n",
    "provenance",
}
ROW_KEYS = {
    "name",
    "a_share",
    "effective_n",
    "term_count",
    "first_term",
    "last_term",
    "easiness_score",
    "scored",
    "is_current",
}

# Banner term ids used by the seeds below.
CURRENT_TERM_ID = 1
TERM_IDS = {"202408": 2, "202501": 3, "202505": 4}


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
                Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
                Term(id=3, banner_code="202501", name="Spring 2025", year=2025, season="Spring"),
                Term(id=4, banner_code="202505", name="Summer 2025", year=2025, season="Summer"),
                Course(
                    id=10,
                    subject="MAC",
                    number="1105",
                    title="College Algebra",
                    catalog_edition="2026-2027",
                ),
            ]
        )
        session.commit()
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


_crn_counter = {"value": 0}


def add_history(
    session: Session,
    *,
    term: str,
    instructor: str | None,
    a: int = 0,
    b: int = 0,
    c: int = 0,
    d: int = 0,
    f: int = 0,
    w: int = 0,
    course_id: int = 10,
    section_type: str = "Class Lecture",
    crn: str | None = None,
) -> str:
    """One past section plus its grade row. effective_n for the row is a+b+c+d+f."""
    _crn_counter["value"] += 1
    crn = crn or f"9{_crn_counter['value']:04d}"
    term_id = TERM_IDS[term]
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type=section_type,
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    if instructor is not None:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=instructor,
                name_normalized=None,
                source="synthetic",
                observed_at=NOW,
            )
        )
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
            source=f"breakdown-{term_id}-{crn}",
            source_hash="synthetic",
        )
    )
    session.flush()
    return crn


def add_current_section(
    session: Session,
    *,
    crn: str,
    instructor: str | None,
    course_id: int = 10,
    section_type: str = "Class Lecture",
) -> None:
    section = Section(
        term_id=CURRENT_TERM_ID,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type=section_type,
        primary_status="Active",
        delivery_method="CL",
        seats_remaining=5,
        capacity=30,
        enrollment=25,
        wait_seats_available=0,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    if instructor is not None:
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw=instructor,
                name_normalized=None,
                source="synthetic",
                observed_at=NOW,
            )
        )
    session.flush()


def seed_mac_1105_history(session: Session) -> None:
    """The tracer seed: three real instructors, one sparse, one Staff and one lab history."""
    # X. Ou: 175 letter grades over three terms, the current instructor.
    add_history(session, term="202408", instructor="X. Ou", a=30, b=20, c=5, d=3, f=2, w=2)
    add_history(session, term="202501", instructor="X. Ou", a=40, b=25, c=8, d=4, f=3, w=1)
    add_history(session, term="202505", instructor="X. Ou", a=20, b=10, c=3, d=1, f=1, w=0)
    # J. Ligatti: 203 over three terms.
    add_history(session, term="202408", instructor="J. Ligatti", a=20, b=30, c=15, d=10, f=5)
    add_history(session, term="202501", instructor="J. Ligatti", a=25, b=30, c=10, d=8, f=7)
    add_history(session, term="202505", instructor="J. Ligatti", a=15, b=15, c=6, d=4, f=3)
    # Y. Liu: 20 in one term, above the collapse cutoff and below the scoring gate.
    add_history(session, term="202501", instructor="Y. Liu", a=5, b=8, c=4, d=2, f=1)
    # A. Ami: 10, counted but never listed.
    add_history(session, term="202408", instructor="A. Ami", a=4, b=3, c=2, d=1)
    # A Staff section feeds course history only.
    add_history(session, term="202501", instructor="Staff", a=20, b=15, c=10, d=3, f=2)
    # A laboratory section feeds course history only (D-13).
    add_history(
        session,
        term="202501",
        instructor="T. Assistant",
        a=40,
        b=25,
        c=10,
        d=3,
        f=2,
        section_type="Laboratory",
    )
    add_current_section(session, crn="70001", instructor="X. Ou")
    session.commit()


def refresh(session_factory: sessionmaker[Session], term: str = "202701") -> None:
    with session_factory() as session:
        refresh_section_rankings(session, term=term)
        session.commit()


def search_items(client: TestClient, **params: str) -> list[dict[str, Any]]:
    response = client.get("/api/v1/rankings/search", params={"term": "202701", **params})
    assert response.status_code == 200, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


def test_search_serves_cached_breakdown_that_matches_the_on_demand_endpoint(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_mac_1105_history(session)
    refresh(session_factory)

    items = search_items(client, subject="MAC")
    assert [item["crn"] for item in items] == ["70001"]
    item = items[0]
    breakdown = item["historical_analytics"]["instructor_breakdown"]

    assert set(breakdown) == BREAKDOWN_KEYS
    assert breakdown["status"] == "ready"
    assert breakdown["current_instructor"] == "X. Ou"
    assert breakdown["current_instructor_has_history"] is True
    assert [row["name"] for row in breakdown["instructors"]] == [
        "X. Ou",
        "J. Ligatti",
        "Y. Liu",
    ]
    assert breakdown["other_instructor_count"] == 1
    assert breakdown["scoring_min_effective_n"] == 30.0
    assert breakdown["collapse_min_effective_n"] == 15.0
    assert breakdown["provenance"]["source"] == "grade_distributions+section_instructors"
    assert breakdown["provenance"]["freshness"] == "historical"
    assert breakdown["provenance"]["source_term"] is None
    assert "202701" in breakdown["provenance"]["detail"]
    assert all(set(row) == ROW_KEYS for row in breakdown["instructors"])
    names = {row["name"] for row in breakdown["instructors"]}
    assert "Staff" not in names
    assert "T. Assistant" not in names

    ou, ligatti, liu = breakdown["instructors"]
    # raw A over A-F from unweighted counts: (30 + 40 + 20) / (60 + 80 + 35)
    assert ou["a_share"] == 90 / 175
    assert ou["effective_n"] == 175.0
    assert ou["term_count"] == 3
    assert ou["first_term"] == "202408"
    assert ou["last_term"] == "202505"
    assert ou["scored"] is True
    assert ou["is_current"] is True
    assert item["score_source"] == "instructor_course"
    assert ou["easiness_score"] == item["easiness_score"]
    with session_factory() as session:
        expected = get_instructor_course_historical_outcome_stats(
            session, "MAC", "1105", "X. Ou", before_term_code="202701"
        )
    assert expected is not None
    assert ou["easiness_score"] == expected.easiness_score
    assert ou["effective_n"] == expected.effective_n

    assert ligatti["effective_n"] == 203.0
    assert ligatti["scored"] is True
    assert ligatti["is_current"] is False
    assert liu["effective_n"] == 20.0
    assert liu["scored"] is False
    assert liu["easiness_score"] is None
    assert liu["term_count"] == 1
    assert liu["first_term"] == liu["last_term"] == "202501"

    on_demand = client.get("/api/v1/rankings/section", params={"term": "202701", "crn": "70001"})
    assert on_demand.status_code == 200
    assert on_demand.json()["historical_analytics"]["instructor_breakdown"] == breakdown
