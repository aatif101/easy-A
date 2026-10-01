from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.analytics.confidence import PriorLevel, ScoreSource
from easy_a.analytics.grades import GradeCounts, GradeObservation, aggregate_grade_observations
from easy_a.analytics.queries import (
    InstructorBreakdownStatus,
    build_instructor_breakdown,
    get_instructor_course_historical_outcome_stats,
)
from easy_a.analytics.scoring import (
    HistoricalOutcomeStats,
    ScoreConfig,
    compute_historical_outcome_stats,
)
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
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings
from easy_a.rankings.service import rank_section
from tests.analytics.test_queries import seed_breakdown_branches

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


def add_course(session: Session, *, course_id: int, subject: str, number: str) -> None:
    session.add(
        Course(
            id=course_id,
            subject=subject,
            number=number,
            title=f"{subject} {number}",
            catalog_edition="2026-2027",
        )
    )
    session.flush()


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


def item_for(items: list[dict[str, Any]], crn: str) -> dict[str, Any]:
    return next(item for item in items if item["crn"] == crn)


def breakdown_of(item: dict[str, Any]) -> dict[str, Any] | None:
    value: dict[str, Any] | None = item["historical_analytics"]["instructor_breakdown"]
    return value


# --- D-20: no instructor claim without course-level history and mapped instructors ------------


def _seed_subject_fallback(session: Session) -> str:
    add_course(session, course_id=12, subject="MAC", number="2222")
    seed_mac_1105_history(session)
    add_current_section(session, crn="72001", instructor="X. Ou", course_id=12)
    return "subject"


def _seed_global_fallback(session: Session) -> str:
    add_course(session, course_id=11, subject="ENC", number="1101")
    seed_mac_1105_history(session)
    add_current_section(session, crn="72001", instructor="X. Ou", course_id=11)
    return "global"


def _seed_no_letter_grades(session: Session) -> str:
    add_course(session, course_id=12, subject="BSC", number="1005")
    add_history(session, term="202408", instructor="X. Ou", w=9, course_id=12)
    add_current_section(session, crn="72001", instructor="X. Ou", course_id=12)
    return "course"


def _seed_unmapped_history(session: Session) -> str:
    # The pre-backfill state: course-level grades exist, no section lists an instructor.
    add_course(session, course_id=12, subject="BSC", number="1005")
    add_history(session, term="202408", instructor=None, a=60, b=30, c=10, course_id=12)
    add_current_section(session, crn="72001", instructor="X. Ou", course_id=12)
    return "course"


@pytest.mark.parametrize(
    "seed",
    [_seed_subject_fallback, _seed_global_fallback, _seed_no_letter_grades, _seed_unmapped_history],
    ids=["subject_fallback", "global_fallback", "no_letter_grades", "no_mapped_instructors"],
)
def test_breakdown_is_null_where_an_instructor_claim_is_unsupported(
    client: TestClient,
    session_factory: sessionmaker[Session],
    seed: Any,
) -> None:
    with session_factory() as session:
        expected_source = seed(session)
        session.commit()
    refresh(session_factory)

    item = item_for(search_items(client), "72001")

    assert item["score_source"] == expected_source
    assert item["historical_analytics"]["instructor_breakdown"] is None
    assert "instructor_breakdown" in item["historical_analytics"]


# --- Edge states over the search API ------------------------------------------------------------


def test_current_laboratory_section_gets_no_rows_and_a_course_level_score(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_mac_1105_history(session)
        add_current_section(session, crn="70002", instructor="X. Ou", section_type="Laboratory")
        session.commit()
    refresh(session_factory)

    items = search_items(client, subject="MAC")
    lab = item_for(items, "70002")
    breakdown = breakdown_of(lab)

    assert breakdown is not None
    assert set(breakdown) == BREAKDOWN_KEYS
    assert breakdown["status"] == "lab_section"
    assert breakdown["instructors"] == []
    assert breakdown["other_instructor_count"] == 0
    assert lab["score_source"] == "course"
    # The lecture section of the same instructor still scores from their own history.
    assert item_for(items, "70001")["score_source"] == "instructor_course"


def test_course_whose_mapped_sections_are_all_labs_or_staff_has_no_instructor_history(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        add_history(
            session,
            term="202408",
            instructor="T. Assistant",
            a=40,
            b=25,
            c=10,
            d=3,
            f=2,
            section_type="Laboratory",
        )
        add_history(session, term="202501", instructor="Staff", a=20, b=15, c=10, d=3, f=2)
        add_current_section(session, crn="70001", instructor="N. Newcomer")
        session.commit()
    refresh(session_factory)

    item = item_for(search_items(client, subject="MAC"), "70001")
    breakdown = breakdown_of(item)

    assert breakdown is not None
    assert breakdown["status"] == "no_instructor_history"
    assert breakdown["instructors"] == []
    assert breakdown["current_instructor"] == "N. Newcomer"
    assert breakdown["current_instructor_has_history"] is False
    assert breakdown["other_instructor_count"] == 0
    assert item["score_source"] == "course"


def test_staff_current_section_lists_rows_display_only_and_keeps_course_score(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        seed_mac_1105_history(session)
        add_current_section(session, crn="70003", instructor="Staff")
        session.commit()
    refresh(session_factory)

    item = item_for(search_items(client, subject="MAC"), "70003")
    breakdown = breakdown_of(item)

    assert breakdown is not None
    assert breakdown["status"] == "ready"
    assert breakdown["current_instructor"] is None
    assert breakdown["current_instructor_has_history"] is False
    assert [row["name"] for row in breakdown["instructors"]] == ["J. Ligatti", "X. Ou", "Y. Liu"]
    assert not any(row["is_current"] for row in breakdown["instructors"])
    assert item["score_source"] == "course"


def test_current_instructor_below_cutoff_is_pinned_and_other_small_instructors_only_counted(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        add_history(session, term="202408", instructor="S. Small", a=4, b=2, c=1, d=1)
        add_history(session, term="202408", instructor="J. Ligatti", a=50, b=30, c=15, d=3, f=2)
        add_history(session, term="202501", instructor="Q. Quiet", a=4, b=3, c=2, d=1)
        add_history(session, term="202501", instructor="R. Roe", a=5, b=4, c=2, d=1)
        add_current_section(session, crn="70001", instructor="S. Small")
        session.commit()
    refresh(session_factory)

    item = item_for(search_items(client, subject="MAC"), "70001")
    breakdown = breakdown_of(item)

    assert breakdown is not None
    pinned, other = breakdown["instructors"]
    assert pinned["name"] == "S. Small"
    assert pinned["effective_n"] == 8.0
    assert pinned["is_current"] is True
    assert pinned["scored"] is False
    assert pinned["easiness_score"] is None
    assert other["name"] == "J. Ligatti"
    assert breakdown["other_instructor_count"] == 2
    assert breakdown["current_instructor_has_history"] is True
    assert item["score_source"] == "course"


def test_ties_sort_by_name_and_other_courses_never_leak_into_a_row(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        add_course(session, course_id=12, subject="MAC", number="1114")
        add_history(session, term="202408", instructor="B. Bravo", a=20, b=10, c=5, d=3, f=2)
        add_history(session, term="202408", instructor="A. Alpha", a=20, b=10, c=5, d=3, f=2)
        add_history(session, term="202501", instructor="Z. Zed", a=30, b=15, c=5, d=3, f=2)
        # The same name teaching a different course is never pooled in (D-14).
        add_history(
            session,
            term="202501",
            instructor="A. Alpha",
            a=300,
            b=100,
            c=50,
            d=20,
            f=10,
            course_id=12,
        )
        add_current_section(session, crn="70001", instructor="Z. Zed")
        session.commit()
    refresh(session_factory)

    items = search_items(client, subject="MAC", course_number="1105")
    breakdown = breakdown_of(item_for(items, "70001"))

    assert breakdown is not None
    assert [row["name"] for row in breakdown["instructors"]] == ["Z. Zed", "A. Alpha", "B. Bravo"]
    alpha = breakdown["instructors"][1]
    assert alpha["effective_n"] == 40.0
    assert alpha["term_count"] == 1
    assert alpha["first_term"] == alpha["last_term"] == "202408"


def test_breakdown_thresholds_follow_the_active_score_config(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        add_history(session, term="202408", instructor="F. Forty", a=20, b=10, c=5, d=3, f=2)
        add_history(session, term="202501", instructor="J. Ligatti", a=50, b=30, c=15, d=3, f=2)
        add_current_section(session, crn="70001", instructor="F. Forty")
        session.commit()
        default = rank_section(session, term="202701", crn="70001")
        strict = rank_section(
            session,
            term="202701",
            crn="70001",
            config=ScoreConfig(
                instructor_course_min_effective_n=60.0,
                instructor_prior_strength=60.0,
            ),
        )

    default_breakdown = default.historical_analytics.instructor_breakdown
    strict_breakdown = strict.historical_analytics.instructor_breakdown
    assert default_breakdown is not None and strict_breakdown is not None
    assert default_breakdown.scoring_min_effective_n == 30.0
    assert default_breakdown.instructors[0].scored is True
    assert default.score_source is ScoreSource.instructor_course
    assert strict_breakdown.scoring_min_effective_n == 60.0
    assert strict_breakdown.instructors[0].effective_n == 40.0
    assert strict_breakdown.instructors[0].scored is False
    assert strict_breakdown.instructors[0].easiness_score is None
    assert strict.score_source is ScoreSource.course


@pytest.mark.parametrize(
    "config",
    [None, ScoreConfig(instructor_course_min_effective_n=60.0, instructor_prior_strength=60.0)],
    ids=["default", "strict"],
)
def test_section_scores_from_instructor_course_exactly_when_the_pinned_row_is_scored(
    db_session: Session,
    config: ScoreConfig | None,
) -> None:
    seed_breakdown_branches(db_session)
    refresh_section_rankings(db_session, term="202701", config=config)
    db_session.commit()

    checked = 0
    for cache_row, section_type in db_session.execute(
        select(SectionRankingCache, Section.section_type).join(
            Section, Section.id == SectionRankingCache.section_id
        )
    ):
        breakdown = cache_row.historical_analytics["instructor_breakdown"]
        current_rows = (
            []
            if breakdown is None
            else [row for row in breakdown["instructors"] if row["is_current"]]
        )
        is_lab = section_type == "Laboratory"
        scored_current = [row for row in current_rows if row["scored"]]
        expects_instructor_course = bool(scored_current) and not is_lab

        assert (cache_row.score_source == ScoreSource.instructor_course.value) == (
            expects_instructor_course
        ), cache_row.crn
        if expects_instructor_course:
            assert scored_current[0]["easiness_score"] == cache_row.easiness_score
            assert scored_current[0]["effective_n"] == cache_row.effective_n
            checked += 1
    assert checked >= 1


# --- Builder-level contract -----------------------------------------------------------------------


def _observation(term_id: int, term_code: str, crn: str, **counts: float) -> GradeObservation:
    completed = sum(counts.get(f"{letter}_count", 0.0) for letter in "abcdf")
    return GradeObservation(
        term_id=term_id,
        term_code=term_code,
        crn=crn,
        mapped_instructor=True,
        counts=GradeCounts(**counts, total_grades=completed + counts.get("w_count", 0.0)),
    )


def _course_stats(
    *,
    source: ScoreSource = ScoreSource.course,
    config: ScoreConfig | None = None,
) -> HistoricalOutcomeStats:
    observations = [
        GradeObservation(
            term_id=2,
            term_code="202408",
            crn="1",
            mapped_instructor=True,
            counts=GradeCounts(a_count=60.0, b_count=30.0, c_count=10.0, total_grades=100.0),
        )
    ]
    return compute_historical_outcome_stats(
        aggregate_grade_observations(observations),
        grade_prior=0.7,
        withdrawal_prior=0.05,
        prior_level=PriorLevel.subject,
        score_source=source,
        config=config or ScoreConfig(),
    )


def test_builder_returns_none_for_fallback_empty_and_unmapped_course_stats() -> None:
    from dataclasses import replace

    base = _course_stats()
    observations = {"A. Alpha": [_observation(2, "202408", "1", a_count=40.0, b_count=10.0)]}
    for stats in (
        replace(base, score_source=ScoreSource.subject),
        replace(base, score_source=ScoreSource.global_),
        replace(base, effective_n=0.0),
        replace(base, mapped_instructor_section_count=0),
    ):
        assert (
            build_instructor_breakdown(
                course_stats=stats,
                observations_by_instructor=observations,
                current_instructor="A. Alpha",
                current_section_is_lab=False,
                config=ScoreConfig(),
            )
            is None
        )


def test_builder_ignores_staff_and_blank_names_and_blank_current_instructor() -> None:
    result = build_instructor_breakdown(
        course_stats=_course_stats(),
        observations_by_instructor={
            "Staff": [_observation(2, "202408", "1", a_count=40.0, b_count=10.0)],
            " ": [_observation(2, "202408", "2", a_count=40.0, b_count=10.0)],
            "A. Alpha": [_observation(2, "202408", "3", a_count=40.0, b_count=10.0)],
        },
        current_instructor="Staff",
        current_section_is_lab=False,
        config=ScoreConfig(),
    )

    assert result is not None
    assert result.status is InstructorBreakdownStatus.ready
    assert result.current_instructor is None
    assert [row.name for row in result.instructors] == ["A. Alpha"]
    assert not result.instructors[0].is_current


def test_builder_a_share_uses_unweighted_counts_and_term_span() -> None:
    result = build_instructor_breakdown(
        course_stats=_course_stats(),
        observations_by_instructor={
            "A. Alpha": [
                _observation(2, "202408", "1", a_count=10.0, b_count=10.0, w_count=4.0),
                _observation(3, "202605", "2", a_count=30.0, c_count=10.0),
            ]
        },
        current_instructor=None,
        current_section_is_lab=False,
        config=ScoreConfig(),
    )

    assert result is not None
    row = result.instructors[0]
    assert row.a_share == 40 / 60
    assert (row.term_count, row.first_term, row.last_term) == (2, "202408", "202605")
