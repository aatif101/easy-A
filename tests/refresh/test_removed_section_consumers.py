"""Tracer: removal drops a section from /coverage counts; a legacy re-ingest restores it."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.models import Section
from easy_a.refresh.coverage import coverage_metadata
from easy_a.refresh.targets import CourseTarget
from easy_a.schedule.ingest import ingest_schedule_html

FIXTURES = Path(__file__).parents[1] / "fixtures"
TARGETS = (CourseTarget(subject="MAC", number="1105"),)
FIRST = datetime(2026, 9, 1, 12, tzinfo=UTC)
SECOND = datetime(2026, 9, 1, 13, tzinfo=UTC)


def test_removed_section_leaves_coverage_and_legacy_reingest_restores_it(
    db_session: Session,
) -> None:
    html = (FIXTURES / "schedule_current.html").read_text(encoding="utf-8")
    ingest_schedule_html(db_session, html, "202701", observed_at=FIRST)
    db_session.commit()

    assert coverage_metadata(db_session, "202701", TARGETS)[0].section_count == 2

    section = db_session.scalar(select(Section).where(Section.crn == "13173"))
    assert section is not None
    section.removed_at = FIRST
    db_session.commit()

    after_removal = coverage_metadata(db_session, "202701", TARGETS)[0]
    assert after_removal.section_count == 1
    assert after_removal.status == "observed"

    ingest_schedule_html(db_session, html, "202701", observed_at=SECOND)
    db_session.commit()

    assert coverage_metadata(db_session, "202701", TARGETS)[0].section_count == 2
    db_session.refresh(section)
    assert section.removed_at is None
