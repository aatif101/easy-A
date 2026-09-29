from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.api.routes.rankings import search_rankings
from easy_a.models import SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings

NOW = datetime(2026, 9, 1, tzinfo=UTC)
REMOVED_AT = datetime(2026, 9, 2, tzinfo=UTC)


def test_removed_section_leaves_search_and_returns_when_restored(db_session: Session) -> None:
    keep = _add_section(db_session, crn="70001")
    gone = _add_section(db_session, crn="70002")
    refresh_section_rankings(db_session, term="202701")
    db_session.commit()

    baseline = search_rankings(term="202701", session=db_session)
    assert baseline.total == 2
    assert {item.crn for item in baseline.items} == {"70001", "70002"}

    # Removal is a mark only, applied to one section.
    gone.removed_at = REMOVED_AT
    db_session.flush()
    refresh_section_rankings(db_session, term="202701")
    db_session.commit()

    after_removal = search_rankings(term="202701", session=db_session)
    assert after_removal.total == 1
    assert [item.crn for item in after_removal.items] == ["70001"]
    cached_crns = set(db_session.scalars(select(SectionRankingCache.crn)))
    assert cached_crns == {"70001"}

    # Removal marks history, it does not delete it (PROJECT.md D-23).
    still_there = db_session.scalar(select(Section).where(Section.crn == "70002"))
    assert still_there is not None
    assert still_there.removed_at is not None
    assert (
        db_session.scalar(
            select(func.count()).select_from(SeatSnapshot).where(SeatSnapshot.section_id == gone.id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SectionInstructor)
            .where(SectionInstructor.section_id == gone.id)
        )
        == 1
    )
    assert keep.removed_at is None

    # Clearing the mark and rebuilding restores the section.
    gone.removed_at = None
    db_session.flush()
    refresh_section_rankings(db_session, term="202701")
    db_session.commit()

    restored = search_rankings(term="202701", session=db_session)
    assert restored.total == 2
    assert {item.crn for item in restored.items} == {"70001", "70002"}


def test_scoped_rebuild_only_drops_removed_rows_in_scope(db_session: Session) -> None:
    mac = _add_section(db_session, crn="70001", course_id=10)
    enc = _add_section(db_session, crn="71001", course_id=11)
    refresh_section_rankings(db_session, term="202701")
    db_session.commit()

    mac.removed_at = REMOVED_AT
    enc.removed_at = REMOVED_AT
    db_session.flush()

    # A MAC 1105 scoped rebuild must not touch the ENC 1101 cache row.
    refresh_section_rankings(db_session, term="202701", subject="MAC", course_number="1105")
    db_session.commit()
    assert set(db_session.scalars(select(SectionRankingCache.crn))) == {"71001"}

    refresh_section_rankings(db_session, term="202701")
    db_session.commit()
    assert set(db_session.scalars(select(SectionRankingCache.crn))) == set()


def _add_section(db_session: Session, *, crn: str, course_id: int = 10) -> Section:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=course_id,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        secondary_status=None,
        delivery_method="CL",
        capacity=30,
        enrollment=10,
        seats_remaining=20,
        wait_seats_available=0,
        section_note=None,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )
    db_session.add(section)
    db_session.flush()
    db_session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw="Dr. Example",
            name_normalized="dr. example",
            source="synthetic",
            observed_at=NOW,
        )
    )
    db_session.add(
        SeatSnapshot(
            section_id=section.id,
            observed_at=NOW,
            capacity=30,
            enrollment=10,
            seats_remaining=20,
            wait_seats_available=0,
        )
    )
    db_session.flush()
    return section
