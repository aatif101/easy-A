"""Quality scans ignore removed sections and judge seat staleness from the verified time."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from easy_a.config import get_settings
from easy_a.models import SeatSnapshot, Section
from easy_a.quality.checks import run_quality_checks
from easy_a.quality.models import QualityFinding
from easy_a.refresh.targets import CourseTarget
from easy_a.schedule import freshness

# Outside every registration window, so the cadence stale threshold is 7200 s.
AS_OF = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
TARGETS = (CourseTarget(subject="MAC", number="1105"),)


@pytest.fixture(autouse=True)
def _cadence_thresholds(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("EASY_A_SEAT_FRESH_SECONDS", raising=False)
    monkeypatch.delenv("EASY_A_SEAT_STALE_SECONDS", raising=False)
    monkeypatch.setattr(freshness, "_partial_override_warned", False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _add_section(
    session: Session,
    *,
    crn: str,
    last_seen_at: datetime,
    snapshot_at: datetime,
    removed_at: datetime | None = None,
    inconsistent_seats: bool = False,
) -> Section:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Open",
        delivery_method="CL",
        first_seen_at=snapshot_at,
        last_seen_at=last_seen_at,
        removed_at=removed_at,
    )
    session.add(section)
    session.flush()
    # capacity 30 / enrollment 20 / remaining 5 is internally inconsistent (an error finding).
    session.add(
        SeatSnapshot(
            section_id=section.id,
            observed_at=snapshot_at,
            capacity=30,
            enrollment=20,
            seats_remaining=5 if inconsistent_seats else 10,
            wait_seats_available=0,
        )
    )
    session.commit()
    return section


def _checks(session: Session, crn: str, check_id: str) -> list[QualityFinding]:
    report = run_quality_checks(session, "202701", as_of=AS_OF, targets=TARGETS)
    return [f for f in report.findings if f.check_id == check_id and f.crn == crn]


def test_removed_section_produces_no_seat_anomaly_finding(db_session: Session) -> None:
    recent = AS_OF - timedelta(minutes=1)
    _add_section(
        db_session, crn="11111", last_seen_at=recent, snapshot_at=recent, inconsistent_seats=True
    )
    _add_section(
        db_session,
        crn="22222",
        last_seen_at=recent,
        snapshot_at=recent,
        inconsistent_seats=True,
        removed_at=AS_OF,
    )

    report = run_quality_checks(db_session, "202701", as_of=AS_OF, targets=TARGETS)
    anomalies = [f for f in report.findings if f.check_id == "inconsistent_seat_count"]

    assert [f.crn for f in anomalies] == ["11111"]
    assert report.section_count == 1


def test_removed_section_produces_no_stale_seat_finding(db_session: Session) -> None:
    ancient = AS_OF - timedelta(days=30)
    _add_section(
        db_session, crn="33333", last_seen_at=ancient, snapshot_at=ancient, removed_at=AS_OF
    )

    assert _checks(db_session, "33333", "stale_seat_observation") == []


def test_old_snapshot_with_recent_verification_is_not_stale(db_session: Session) -> None:
    _add_section(
        db_session,
        crn="44444",
        last_seen_at=AS_OF - timedelta(minutes=5),
        snapshot_at=AS_OF - timedelta(days=30),
    )

    assert _checks(db_session, "44444", "stale_seat_observation") == []


def test_verification_older_than_the_stale_threshold_is_stale(db_session: Session) -> None:
    _add_section(
        db_session,
        crn="55555",
        last_seen_at=AS_OF - timedelta(hours=3),
        snapshot_at=AS_OF - timedelta(days=30),
    )

    findings = _checks(db_session, "55555", "stale_seat_observation")

    assert len(findings) == 1
    assert findings[0].severity == "warning"
    assert findings[0].message == (
        "Seat data has not been verified within the cadence-derived stale threshold."
    )
