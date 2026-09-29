"""Removed sections leave current-term listings; historical grade evidence is untouched (D-02)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.analytics.queries import (
    get_course_historical_outcome_stats,
    get_current_section_historical_analytics,
    get_term_section_historical_analytics,
)
from easy_a.models import Section
from easy_a.refresh import RefreshConfig, refresh_data
from tests.analytics.test_queries import _add_grade, _add_section
from tests.refresh.test_service import NOW, _offline_refresh

TERM = "202701"
KEY = ("MAC", "1105")


def _seed(session: Session) -> None:
    # Historical evidence in Fall 2024 (term 2) plus two current Spring 2027 sections.
    _add_section(session, term_id=2, crn="80001", instructor="H. Historical")
    _add_grade(session, term_id=2, crn="80001", a=20, b=10, c=5, d=2, f=1, w=3)
    _add_section(session, term_id=1, crn="90001", instructor="A. Current")
    _add_section(session, term_id=1, crn="90002", instructor="B. Current")
    session.commit()


def _mark_removed(session: Session, crn: str) -> None:
    section = session.scalar(select(Section).where(Section.term_id == 1, Section.crn == crn))
    assert section is not None
    section.removed_at = datetime(2026, 9, 2, tzinfo=UTC)
    session.commit()


def test_current_term_listings_omit_removed_sections(db_session: Session) -> None:
    _seed(db_session)
    assert [r.crn for r in get_current_section_historical_analytics(db_session, TERM, *KEY)] == [
        "90001",
        "90002",
    ]
    assert [
        r.crn for r in get_term_section_historical_analytics(db_session, TERM, [KEY])
    ] == ["90001", "90002"]

    _mark_removed(db_session, "90002")

    assert [r.crn for r in get_current_section_historical_analytics(db_session, TERM, *KEY)] == [
        "90001"
    ]
    assert [
        r.crn for r in get_term_section_historical_analytics(db_session, TERM, [KEY])
    ] == ["90001"]


def test_historical_course_aggregate_is_unchanged_by_removal(db_session: Session) -> None:
    _seed(db_session)
    before = get_course_historical_outcome_stats(
        db_session, *KEY, before_term_code=TERM
    )
    remaining_before = get_current_section_historical_analytics(db_session, TERM, *KEY)[0].stats

    _mark_removed(db_session, "90002")

    after = get_course_historical_outcome_stats(db_session, *KEY, before_term_code=TERM)
    remaining_after = get_current_section_historical_analytics(db_session, TERM, *KEY)[0].stats
    assert after == before
    assert remaining_after == remaining_before


def test_refresh_report_counts_active_sections_only(tmp_path: Path) -> None:
    factory, config = _offline_refresh(tmp_path)
    first = refresh_data(config, session_factory=factory, observed_at=NOW, quality_as_of=NOW)
    assert (first.courses, first.sections) == (1, 2)

    with factory.begin() as session:
        section = session.scalar(select(Section).where(Section.crn == "13173"))
        assert section is not None
        section.removed_at = NOW

    # A term-only refresh runs no ingest stage, so nothing restores the removed section.
    second = refresh_data(
        RefreshConfig(term="202701"),
        session_factory=factory,
        observed_at=NOW,
        quality_as_of=NOW,
    )
    assert (second.courses, second.sections) == (1, 1)
