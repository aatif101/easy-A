from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.grades.ingest import ingest_grade_file
from easy_a.models import Course, GradeDistribution, Section, Term
from easy_a.rankings.cache import SectionRankingCache, hydrate_ranking, refresh_section_rankings
from easy_a.rankings.service import rank_section

GRADE_HEADER = [
    "course",
    "A",
    "% A",
    "B",
    "% B",
    "C",
    "% C",
    "D",
    "% D",
    "F",
    "% F",
    "I",
    "% I",
    "S",
    "% S",
    "U",
    "% U",
    "W",
    "% W",
    "O",
    "% O",
    "Total Grades",
]

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


def test_generated_xlsx_attribution_reaches_cached_search_without_historical_section(
    tmp_path: Path,
) -> None:
    """One generated Fall 2024 XLSX row (no historical Section) attaches directly to its
    canonical course and shows effective_n > 0 for a Spring 2027 section after a cache rebuild,
    while a no-history control section stays an explicit global fallback (D-06, D-07, D-20)."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    workbook_path = tmp_path / "fall_2024_mac1105_89033.xlsx"
    _write_grade_workbook(workbook_path)

    with factory() as session:
        mac = Course(
            subject="MAC",
            number="1105",
            title="College Algebra",
            catalog_edition="2026-2027",
        )
        enc = Course(
            subject="ENC",
            number="1101",
            title="Composition I",
            catalog_edition="2026-2027",
        )
        session.add_all([mac, enc])
        session.flush()

        # Historical import: real term 202408. Deliberately no schedule ingestion and no
        # Section row for term 202408 / CRN 89033 — only GradeDistribution.course_id can
        # make direct attribution work for this row.
        ingest_grade_file(session, "202408", workbook_path)

        grade = session.execute(
            select(GradeDistribution).where(GradeDistribution.crn == "89033")
        ).scalar_one()
        assert grade.course_id == mac.id

        term_202701 = Term(
            banner_code="202701",
            name="Spring 2027",
            year=2027,
            season="Spring",
        )
        session.add(term_202701)
        session.flush()

        with_history_section = Section(
            term_id=term_202701.id,
            crn="70001",
            course_id=mac.id,
            section_number="001",
            campus="Tampa",
            session="Full Term",
            section_type="Class Lecture",
            primary_status="Active",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
        no_history_section = Section(
            term_id=term_202701.id,
            crn="70002",
            course_id=enc.id,
            section_number="001",
            campus="Tampa",
            session="Full Term",
            section_type="Class Lecture",
            primary_status="Active",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
        session.add_all([with_history_section, no_history_section])
        session.commit()

    with factory() as session:
        refresh_section_rankings(session, term="202701")
        session.commit()

    with factory() as session:
        with_history_rank = rank_section(session, term="202701", crn="70001", as_of=NOW)
        no_history_rank = rank_section(session, term="202701", crn="70002", as_of=NOW)

        assert with_history_rank.effective_n > 0
        assert with_history_rank.score_source == "course"
        assert no_history_rank.effective_n == 0
        assert no_history_rank.score_source == "global"

        cached_with_history = session.scalar(
            select(SectionRankingCache).where(SectionRankingCache.crn == "70001")
        )
        cached_no_history = session.scalar(
            select(SectionRankingCache).where(SectionRankingCache.crn == "70002")
        )
        assert cached_with_history is not None
        assert cached_with_history.effective_n > 0
        assert cached_with_history.score_source == "course"
        assert cached_no_history is not None
        assert cached_no_history.effective_n == 0
        assert cached_no_history.score_source == "global"

        assert hydrate_ranking(session, cached_with_history, as_of=NOW).model_dump(
            mode="json"
        ) == with_history_rank.model_dump(mode="json")
        assert hydrate_ranking(session, cached_no_history, as_of=NOW).model_dump(
            mode="json"
        ) == no_history_rank.model_dump(mode="json")

    def override_get_db_session() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/rankings/search",
                params={"term": "202701", "sort": "course"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items_by_crn = {item["crn"]: item for item in response.json()["items"]}
    assert items_by_crn["70001"]["effective_n"] > 0
    assert items_by_crn["70001"]["score_source"] == "course"
    assert items_by_crn["70002"]["effective_n"] == 0
    assert items_by_crn["70002"]["score_source"] == "global"


def _write_grade_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    worksheet.append(
        [
            "MAC-1105 -001-C (89033)",
            10,
            None,
            4,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            1,
            None,
            0,
            None,
            15,
        ]
    )
    workbook.save(path)
