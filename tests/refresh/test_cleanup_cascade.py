"""Cascade/identity coverage for section_rankings rows in clean_other_campus_sections.

Proves the cache table joins the existing explicit-delete + identity-verification
sequence used for SeatSnapshot / SectionInstructor / Syllabus (RESEARCH Pitfall 2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import easy_a.refresh.cleanup as cleanup_module
from easy_a.db import Base
from easy_a.models import Course, Section, SectionRankingCache, Term
from easy_a.refresh.cleanup import CleanupError, clean_other_campus_sections
from easy_a.refresh.targets import CourseTarget

NOW = datetime(2026, 9, 10, tzinfo=UTC)
TARGETS = (
    CourseTarget(subject="MAC", number="1105"),
    CourseTarget(subject="ENC", number="1101"),
)


def test_apply_deletes_section_rankings_for_removed_sections() -> None:
    factory = _factory()
    with factory.begin() as session:
        tampa = _add_section(session, crn="10001", campus="Tampa")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        tampa_cache = _add_ranking_cache(session, tampa)
        candidate_cache = _add_ranking_cache(session, candidate)

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert report.sections_removed == 1
        remaining_cache_ids = set(session.scalars(select(SectionRankingCache.id)))
        assert remaining_cache_ids == {tampa_cache.id}
        assert session.get(SectionRankingCache, candidate_cache.id) is None


def test_apply_leaves_no_orphaned_ranking_cache_row() -> None:
    factory = _factory()
    with factory.begin() as session:
        tampa = _add_section(session, crn="10001", campus="Tampa")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        _add_ranking_cache(session, tampa)
        _add_ranking_cache(session, candidate)

        clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        remaining_section_ids = set(session.scalars(select(Section.id)))
        orphaned = [
            row.section_id
            for row in session.scalars(select(SectionRankingCache))
            if row.section_id not in remaining_section_ids
        ]
        assert orphaned == []


def test_apply_without_cache_rows_completes_without_fk_violation() -> None:
    factory = _factory()
    with factory.begin() as session:
        _add_section(session, crn="10001", campus="Tampa")
        _add_section(session, crn="10002", campus="St. Petersburg")

        report = clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        assert report.sections_removed == 1


def test_tampa_ranking_cache_rows_are_preserved() -> None:
    factory = _factory()
    with factory.begin() as session:
        tampa = _add_section(session, crn="10001", campus="Tampa")
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        tampa_cache = _add_ranking_cache(session, tampa)
        _add_ranking_cache(session, candidate)

        clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )

        kept = session.get(SectionRankingCache, tampa_cache.id)
        assert kept is not None
        assert kept.section_id == tampa.id


def test_identity_verification_detects_leftover_ranking_cache_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A leftover cache row must fail the same identity check as the other dependent tables."""
    factory = _factory()
    with factory.begin() as session:
        candidate = _add_section(session, crn="10002", campus="St. Petersburg")
        _add_ranking_cache(session, candidate)

    real_delete_ids = cleanup_module._delete_ids

    def leave_ranking_cache_behind(session: Session, model: Any, ids: frozenset[int]) -> None:
        if getattr(model, "__tablename__", None) == "section_rankings":
            return
        real_delete_ids(session, model, ids)

    monkeypatch.setattr(cleanup_module, "_delete_ids", leave_ranking_cache_behind)

    with (
        pytest.raises(CleanupError, match="section ranking"),
        factory.begin() as session,
    ):
        clean_other_campus_sections(
            session,
            term="202701",
            targets=TARGETS,
            apply=True,
            expect_removed=1,
        )


def _factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        _seed_reference_rows(session)
    return factory


def _seed_reference_rows(session: Session) -> None:
    session.add_all(
        [
            Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
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
        ]
    )
    session.flush()


def _add_section(
    session: Session,
    *,
    crn: str,
    campus: str,
    term_id: int = 1,
    course_id: int = 10,
) -> Section:
    section = Section(
        term_id=term_id,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus=campus,
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    session.add(section)
    session.flush()
    return section


def _add_ranking_cache(session: Session, section: Section) -> SectionRankingCache:
    provenance = {
        "freshness": "unavailable",
        "source": "test",
        "source_term": "202701",
        "detail": "test fixture",
    }
    cache_row = SectionRankingCache(
        section_id=section.id,
        term="202701",
        term_name="Spring 2027",
        subject="MAC",
        course_number="1105",
        crn=section.crn,
        course_title="Test Course",
        instructor=None,
        easiness_score=7.5,
        smoothed_withdrawal_rate=0.1,
        confidence_label="low",
        score_source="global",
        effective_n=0.0,
        delivery_method=None,
        historical_analytics={},
        gened_attributes=[],
        signals=[],
        instructor_provenance=provenance,
        gened_provenance=provenance,
        signal_provenance=provenance,
        section_provenance=provenance,
        modality={"delivery_method": None, "delivery_label": None, "provenance": provenance},
    )
    session.add(cache_row)
    session.flush()
    return cache_row
