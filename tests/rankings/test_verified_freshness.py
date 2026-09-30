"""Seat freshness is judged from the verified time (Section.last_seen_at), against the cadence.

A change-only sweep writes a SeatSnapshot only when seats change, so an unchanged section that a
sweep re-verified minutes ago must read fresh even though its snapshot is days old (09-05, D-10).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from easy_a.api.routes import rankings as rankings_route
from easy_a.config import get_settings
from easy_a.models import SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.rankings.service import rank_section

OUTSIDE_WINDOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
IN_WINDOW = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)

SNAPSHOT_SEATS = {"capacity": 40, "enrollment": 33, "seats_remaining": 7, "wait_seats_available": 2}


@pytest.fixture(autouse=True)
def _no_seat_overrides(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("EASY_A_SEAT_FRESH_SECONDS", raising=False)
    monkeypatch.delenv("EASY_A_SEAT_STALE_SECONDS", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _freeze_route_clock(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[no-untyped-def, override]
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr(rankings_route, "datetime", FrozenDatetime)


def _seed_section(
    session: Session,
    *,
    last_seen_at: datetime,
    snapshot_at: datetime,
    crn: str = "70001",
) -> Section:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        secondary_status=None,
        delivery_method="CL",
        # The section's own seat columns deliberately differ from the snapshot: the counts a
        # student sees must come from the latest SeatSnapshot.
        capacity=99,
        enrollment=99,
        seats_remaining=0,
        wait_seats_available=0,
        section_note=None,
        first_seen_at=snapshot_at,
        last_seen_at=last_seen_at,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw="Dr. Example",
            name_normalized="dr. example",
            source="synthetic",
            observed_at=snapshot_at,
        )
    )
    session.add(SeatSnapshot(section_id=section.id, observed_at=snapshot_at, **SNAPSHOT_SEATS))
    session.flush()
    refresh_section_rankings(session, term="202701")
    session.commit()
    return section


def _assert_seat_counts_from_snapshot(seats: object) -> None:
    for name, value in SNAPSHOT_SEATS.items():
        assert getattr(seats, name) == value


@pytest.mark.parametrize(
    ("as_of", "verified_age", "expected"),
    [
        # Outside every window: fresh <= 4500 s, stale > 7200 s.
        pytest.param(OUTSIDE_WINDOW, timedelta(minutes=2), "fresh", id="outside-recent-fresh"),
        pytest.param(OUTSIDE_WINDOW, timedelta(hours=3), "stale", id="outside-3h-stale"),
        # Inside the Nov window: fresh <= 375 s, stale > 600 s.
        pytest.param(IN_WINDOW, timedelta(minutes=8), "aging", id="window-8m-aging"),
        pytest.param(IN_WINDOW, timedelta(minutes=11), "stale", id="window-11m-stale"),
    ],
)
def test_search_route_judges_freshness_from_verified_time(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    as_of: datetime,
    verified_age: timedelta,
    expected: str,
) -> None:
    last_seen_at = as_of - verified_age
    _seed_section(db_session, last_seen_at=last_seen_at, snapshot_at=as_of - timedelta(days=3))
    _freeze_route_clock(monkeypatch, as_of)

    response = rankings_route.search_rankings(term="202701", session=db_session)

    assert response.total == 1
    seats = response.items[0].seats
    assert seats.freshness == expected
    assert seats.observed_at == last_seen_at
    assert seats.age_seconds == verified_age.total_seconds()
    _assert_seat_counts_from_snapshot(seats)


@pytest.mark.parametrize(
    ("as_of", "verified_age", "expected"),
    [
        (OUTSIDE_WINDOW, timedelta(minutes=2), "fresh"),
        (OUTSIDE_WINDOW, timedelta(hours=3), "stale"),
        (IN_WINDOW, timedelta(minutes=8), "aging"),
        (IN_WINDOW, timedelta(minutes=11), "stale"),
    ],
)
def test_rank_section_judges_freshness_from_verified_time(
    db_session: Session, as_of: datetime, verified_age: timedelta, expected: str
) -> None:
    last_seen_at = as_of - verified_age
    _seed_section(db_session, last_seen_at=last_seen_at, snapshot_at=as_of - timedelta(days=3))

    ranking = rank_section(db_session, term="202701", crn="70001", as_of=as_of)

    assert ranking.seats.freshness == expected
    assert ranking.seats.observed_at == last_seen_at
    _assert_seat_counts_from_snapshot(ranking.seats)


def test_old_verification_is_never_labelled_fresh(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No optimistic freshness: neither the snapshot nor the last verification is recent."""
    old = OUTSIDE_WINDOW - timedelta(days=3)
    _seed_section(db_session, last_seen_at=old, snapshot_at=old)
    _freeze_route_clock(monkeypatch, OUTSIDE_WINDOW)

    seats = rankings_route.search_rankings(term="202701", session=db_session).items[0].seats

    assert seats.freshness == "stale"
    assert seats.observed_at == old
    _assert_seat_counts_from_snapshot(seats)


def test_snapshot_newer_than_verification_is_the_observation_time(db_session: Session) -> None:
    snapshot_at = OUTSIDE_WINDOW - timedelta(minutes=1)
    _seed_section(
        db_session, last_seen_at=OUTSIDE_WINDOW - timedelta(days=1), snapshot_at=snapshot_at
    )

    ranking = rank_section(db_session, term="202701", crn="70001", as_of=OUTSIDE_WINDOW)

    assert ranking.seats.freshness == "fresh"
    assert ranking.seats.observed_at == snapshot_at
