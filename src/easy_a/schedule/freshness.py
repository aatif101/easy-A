from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel

from easy_a.config import get_settings
from easy_a.models import SeatSnapshot


class SeatFreshness(StrEnum):
    fresh = "fresh"
    aging = "aging"
    stale = "stale"
    unavailable = "unavailable"


class SeatObservation(BaseModel):
    observed_at: datetime | None = None
    freshness: SeatFreshness = SeatFreshness.unavailable
    age_seconds: float | None = None


def classify_observation(
    observed_at: datetime | None,
    *,
    as_of: datetime | None = None,
    fresh_seconds: int | None = None,
    stale_seconds: int | None = None,
) -> SeatObservation:
    settings = get_settings()
    fresh = settings.seat_fresh_seconds if fresh_seconds is None else fresh_seconds
    stale = settings.seat_stale_seconds if stale_seconds is None else stale_seconds
    if not 0 <= fresh <= stale:
        raise ValueError("Seat thresholds must satisfy 0 <= fresh <= stale.")
    if observed_at is None:
        return SeatObservation()
    observed = as_utc(observed_at)
    age = (as_utc(as_of or datetime.now(UTC)) - observed).total_seconds()
    if age < 0:
        return SeatObservation(observed_at=observed)
    status = (
        SeatFreshness.fresh
        if age <= fresh
        else SeatFreshness.aging
        if age <= stale
        else SeatFreshness.stale
    )
    return SeatObservation(observed_at=observed, freshness=status, age_seconds=age)


def snapshot_freshness(
    snapshot: SeatSnapshot | None, *, as_of: datetime | None = None
) -> SeatObservation:
    if snapshot is None:
        return SeatObservation()
    if all(
        value is None
        for value in (
            snapshot.capacity,
            snapshot.enrollment,
            snapshot.seats_remaining,
            snapshot.wait_seats_available,
        )
    ):
        return SeatObservation(observed_at=as_utc(snapshot.observed_at))
    return classify_observation(snapshot.observed_at, as_of=as_of)


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
