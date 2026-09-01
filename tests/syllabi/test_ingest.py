from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.models import Section, Syllabus
from easy_a.syllabi.ingest import ingest_syllabus_html

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _section(*, term_id: int, crn: str) -> Section:
    observed_at = datetime(2026, 9, 1, tzinfo=UTC)
    return Section(
        term_id=term_id,
        crn=crn,
        course_id=11,
        section_number="521",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        credits="3",
        primary_status="Closed",
        secondary_status="A",
        delivery_method="CL",
        first_seen_at=observed_at,
        last_seen_at=observed_at,
    )


def test_syllabus_joins_by_term_and_crn_and_is_idempotent(db_session: Session) -> None:
    wrong_term = _section(term_id=2, crn="50750")
    correct_term = _section(term_id=3, crn="50750")
    db_session.add_all([wrong_term, correct_term])
    db_session.commit()
    html = (FIXTURES / "syllabus_enc_1101.html").read_text(encoding="utf-8")

    first = ingest_syllabus_html(
        db_session,
        html,
        document_id="bpvdotxa9",
        fetched_at=datetime(2026, 9, 1, 12, tzinfo=UTC),
    )
    db_session.commit()
    second = ingest_syllabus_html(
        db_session,
        html,
        document_id="bpvdotxa9",
        fetched_at=datetime(2026, 9, 1, 13, tzinfo=UTC),
    )
    db_session.commit()

    assert first.inserted is True
    assert first.joined_to_section is True
    assert second.inserted is False
    assert second.content_changed is False
    assert db_session.scalar(select(func.count()).select_from(Syllabus)) == 1
    syllabus = db_session.scalar(select(Syllabus))
    assert syllabus is not None
    assert syllabus.section_id == correct_term.id
    assert syllabus.section_id != wrong_term.id
    # SQLite drops timezone metadata; PostgreSQL preserves the UTC-aware value.
    assert syllabus.fetched_at == datetime(2026, 9, 1, 13)
