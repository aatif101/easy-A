from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel

from easy_a.config import get_settings
from easy_a.models import SeatSnapshot

logger = logging.getLogger(__name__)

LEGACY_FRESH_SECONDS = 600
LEGACY_STALE_SECONDS = 1800

_partial_override_warned = False


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
    """Classify an observation age against explicit, override or legacy (600/1800 s) thresholds."""
    settings = get_settings()
    if fresh_seconds is not None:
        fresh = fresh_seconds
    elif settings.seat_fresh_seconds is not None:
        fresh = settings.seat_fresh_seconds
    else:
        fresh = LEGACY_FRESH_SECONDS
    if stale_seconds is not None:
        stale = stale_seconds
    elif settings.seat_stale_seconds is not None:
        stale = settings.seat_stale_seconds
    else:
        stale = LEGACY_STALE_SECONDS
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
    snapshot: SeatSnapshot | None,
    *,
    as_of: datetime | None = None,
    verified_at: datetime | None = None,
) -> SeatObservation:
    """Freshness of a seat snapshot, optionally judged from the time the section was verified.

    Without ``verified_at`` the age is measured from ``snapshot.observed_at`` against the legacy
    (or override) thresholds, exactly as before.

    With ``verified_at`` (``Section.last_seen_at``) the observation time is the later of
    ``verified_at`` and ``snapshot.observed_at``: a change-only sweep writes a snapshot only when
    seats change, so an unchanged section is still fresh when a sweep re-verified it recently.
    The seat counts themselves always come from the snapshot. Thresholds follow the sync cadence
    (``easy_a.sync.windows.seat_thresholds``: 375/600 s inside a registration window, 4500/7200 s
    outside, the larger tier at a boundary), so stale means older than twice the cadence.

    ``EASY_A_SEAT_FRESH_SECONDS`` and ``EASY_A_SEAT_STALE_SECONDS`` are explicit overrides that
    replace the cadence thresholds only when BOTH are set. A partial override is ignored (the
    cadence applies) and logged once at warning level.
    """
    if snapshot is None:
        return SeatObservation()
    observation_time = as_utc(snapshot.observed_at)
    if verified_at is not None:
        observation_time = max(observation_time, as_utc(verified_at))
    if all(
        value is None
        for value in (
            snapshot.capacity,
            snapshot.enrollment,
            snapshot.seats_remaining,
            snapshot.wait_seats_available,
        )
    ):
        return SeatObservation(observed_at=observation_time)
    if verified_at is None:
        return classify_observation(snapshot.observed_at, as_of=as_of)

    now = as_utc(as_of) if as_of is not None else datetime.now(UTC)
    fresh_seconds, stale_seconds = _verified_thresholds(observation_time, now)
    return classify_observation(
        observation_time, as_of=now, fresh_seconds=fresh_seconds, stale_seconds=stale_seconds
    )


def _verified_thresholds(verified_at: datetime, now: datetime) -> tuple[int, int]:
    global _partial_override_warned
    settings = get_settings()
    fresh_override = settings.seat_fresh_seconds
    stale_override = settings.seat_stale_seconds
    if fresh_override is not None and stale_override is not None:
        return fresh_override, stale_override
    if (fresh_override is None) != (stale_override is None) and not _partial_override_warned:
        _partial_override_warned = True
        logger.warning(
            "Ignoring partial seat-freshness override: set both EASY_A_SEAT_FRESH_SECONDS and "
            "EASY_A_SEAT_STALE_SECONDS to override the cadence thresholds."
        )
    try:
        from easy_a.sync.windows import get_registration_windows

        thresholds = get_registration_windows().seat_thresholds(verified_at, now)
    except (OSError, ValueError):
        # An unreadable windows file must not break public search, and must never make seat
        # data look fresher than it is: fall back to the stricter legacy thresholds.
        logger.warning(
            "Registration windows unavailable; using legacy seat-freshness thresholds.",
            exc_info=True,
        )
        return LEGACY_FRESH_SECONDS, LEGACY_STALE_SECONDS
    return thresholds.fresh_seconds, thresholds.stale_seconds


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
