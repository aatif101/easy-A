from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.models import SeatSnapshot, Section, SectionInstructor
from easy_a.schedule.ingest import ingest_schedule_html

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_repeated_ingest_updates_sections_and_appends_history(db_session: Session) -> None:
    html = (FIXTURES / "schedule_current.html").read_text(encoding="utf-8")
    first = datetime(2026, 9, 1, 12, tzinfo=UTC)
    second = datetime(2026, 9, 1, 13, tzinfo=UTC)

    first_result = ingest_schedule_html(db_session, html, "202701", observed_at=first)
    db_session.commit()
    second_result = ingest_schedule_html(db_session, html, "202701", observed_at=second)
    db_session.commit()

    assert first_result.records_inserted == 2
    assert second_result.records_inserted == 0
    assert second_result.records_updated == 2
    assert db_session.scalar(select(func.count()).select_from(Section)) == 2
    assert db_session.scalar(select(func.count()).select_from(SeatSnapshot)) == 4
    assert db_session.scalar(select(func.count()).select_from(SectionInstructor)) == 4
    section = db_session.scalar(select(Section).where(Section.crn == "13173"))
    assert section is not None
    # SQLite drops timezone metadata; PostgreSQL preserves the UTC-aware values.
    assert section.first_seen_at == first.replace(tzinfo=None)
    assert section.last_seen_at == second.replace(tzinfo=None)
