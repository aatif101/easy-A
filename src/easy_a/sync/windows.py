"""Registration windows and the cadence rules built on them (pure, injected clock).

The sync worker and the API both read ``config/registration_windows.toml`` through this module so
that "what is the cadence now", "when may the next sweep start" and "when is seat data stale"
have exactly one answer.

Hard rules (PROJECT.md D-22): the worker never starts two sweeps closer together than the floor of
the tier the later sweep falls in (300 s inside a registration window, 3600 s outside). Jitter
therefore only lengthens intervals (a factor drawn uniformly from [1.0, 1.2]), the gap is measured
from the previous sweep *start*, and failure backoff is never shorter than the tier floor.

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

import tomllib
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Protocol
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from easy_a.common.terms import normalize_banner_term_code
from easy_a.config import get_settings

IN_WINDOW_INTERVAL = 300
"""Seconds between sweeps inside a registration window (the floor)."""

OUTSIDE_WINDOW_INTERVAL = 3600
"""Seconds between sweeps outside every window (the floor)."""

JITTER_MAX = 1.2
"""Upper bound of the upward-only jitter factor (D-01, reconciled with D-22(b))."""

MAX_BACKOFF_SECONDS = 3600
FRESH_TO_INTERVAL_RATIO = 1.25
STALE_TO_INTERVAL_RATIO = 2

DEFAULT_TIMEZONE = "America/New_York"


class SupportsUniform(Protocol):
    """The slice of ``random.Random`` the cadence rules use (lets tests inject a stub)."""

    def uniform(self, a: float, b: float) -> float: ...


class SeatThresholds(NamedTuple):
    """Seat-observation age limits in seconds, derived from the cadence (D-10)."""

    fresh_seconds: int
    stale_seconds: int


class RegistrationWindow(BaseModel):
    label: str = Field(min_length=1)
    start: date
    end: date
    source: str
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("source")
    @classmethod
    def _source_is_usf_https(cls, value: str) -> str:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == "usf.edu" or host.endswith(".usf.edu")):
            raise ValueError("Window source must be an https URL on usf.edu.")
        return value

    @model_validator(mode="after")
    def _start_not_after_end(self) -> RegistrationWindow:
        if self.start > self.end:
            raise ValueError(f"Window {self.label!r} starts after it ends.")
        return self


class RegistrationWindows(BaseModel):
    term: str
    timezone: str = DEFAULT_TIMEZONE
    windows: tuple[RegistrationWindow, ...] = Field(min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("term")
    @classmethod
    def _term_is_banner_code(cls, value: str) -> str:
        return normalize_banner_term_code(value)

    @field_validator("timezone")
    @classmethod
    def _timezone_loads(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            raise ValueError(f"Timezone {value!r} cannot be loaded: {exc}") from exc
        return value

    @model_validator(mode="after")
    def _windows_ordered_and_disjoint(self) -> RegistrationWindows:
        for earlier, later in zip(self.windows, self.windows[1:], strict=False):
            if later.start <= earlier.end:
                raise ValueError(
                    f"Windows must be sorted and non-overlapping: {later.label!r} "
                    f"({later.start}) does not start after {earlier.label!r} ends ({earlier.end})."
                )
        return self

    # -- helpers -----------------------------------------------------------------------------

    @property
    def tz(self) -> tzinfo:
        return ZoneInfo(self.timezone)

    def _local_midnight_utc(self, day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=self.tz).astimezone(UTC)

    # -- cadence -----------------------------------------------------------------------------

    def contains(self, moment: datetime) -> bool:
        """True when ``moment`` falls on a whole local day covered by a window."""
        _require_aware(moment, "moment")
        local_day = moment.astimezone(self.tz).date()
        return any(w.start <= local_day <= w.end for w in self.windows)

    def interval_for(self, moment: datetime) -> int:
        """Base seconds between sweeps for ``moment`` (300 in a window, 3600 outside)."""
        return IN_WINDOW_INTERVAL if self.contains(moment) else OUTSIDE_WINDOW_INTERVAL

    def next_window_start_after(self, moment: datetime) -> datetime | None:
        """UTC instant of the first window's local midnight strictly after ``moment``."""
        _require_aware(moment, "moment")
        for window in self.windows:
            start = self._local_midnight_utc(window.start)
            if start > moment:
                return start
        return None

    def next_start(
        self,
        prev_start: datetime,
        now: datetime,
        *,
        rng: SupportsUniform,
        failures: int = 0,
    ) -> datetime:
        """Earliest allowed start of the next sweep (UTC), never below the later sweep's floor.

        ``prev_start`` is the previous sweep's start, ``now`` the current instant and
        ``failures`` the consecutive failed sweeps so far.
        """
        _require_aware(prev_start, "prev_start")
        _require_aware(now, "now")
        prev = prev_start.astimezone(UTC)
        current = now.astimezone(UTC)

        jitter = rng.uniform(1.0, JITTER_MAX)
        interval = self.interval_for(prev) * jitter
        if failures > 0:
            interval = max(interval, backoff_seconds(failures))
        target = max(prev + timedelta(seconds=interval), current)

        # The later sweep's floor: when it lands outside every window it needs the hourly gap,
        # which covers both a window that just ended and a late `now`.
        if not self.contains(target):
            earliest = prev + timedelta(seconds=OUTSIDE_WINDOW_INTERVAL * jitter)
            target = max(target, earliest)

        # The first sweep of a window fires at its local midnight, or as soon after as the
        # in-window floor allows when the previous sweep started less than 300 s before it.
        boundary = self.next_window_start_after(prev)
        if boundary is not None and boundary < target:
            floor = prev + timedelta(seconds=IN_WINDOW_INTERVAL)
            target = max(boundary, floor, current)
        return target

    # -- freshness ---------------------------------------------------------------------------

    def _governing_interval(self, verified_at: datetime, now: datetime) -> int:
        return max(self.interval_for(verified_at), self.interval_for(now))

    def stale_after_seconds(self, verified_at: datetime, now: datetime) -> int:
        """Age after which seat data is stale: 2 x the larger cadence of the two instants."""
        return STALE_TO_INTERVAL_RATIO * self._governing_interval(verified_at, now)

    def seat_thresholds(self, verified_at: datetime, now: datetime) -> SeatThresholds:
        """(fresh, stale) seconds: 375/600 in a window, 4500/7200 outside (D-10)."""
        interval = self._governing_interval(verified_at, now)
        return SeatThresholds(
            fresh_seconds=round(FRESH_TO_INTERVAL_RATIO * interval),
            stale_seconds=STALE_TO_INTERVAL_RATIO * interval,
        )


def backoff_seconds(failures: int) -> int:
    """Failure backoff floor: min(3600, 300 * 2**failures), so 600, 1200, 2400, 3600, ..."""
    doublings = min(max(failures, 0), 10)
    return min(MAX_BACKOFF_SECONDS, IN_WINDOW_INTERVAL * (1 << doublings))


def _require_aware(moment: datetime, name: str) -> None:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime.")


def load_windows(path: Path | str | None = None) -> RegistrationWindows:
    """Load and validate the registration-windows file (setting: registration_windows_path)."""
    source = Path(path) if path is not None else Path(get_settings().registration_windows_path)
    return RegistrationWindows.model_validate(tomllib.loads(source.read_text(encoding="utf-8")))


@lru_cache
def get_registration_windows() -> RegistrationWindows:
    return load_windows()


def assert_timezone_available(name: str = DEFAULT_TIMEZONE) -> None:
    """Fail loudly when the tz database is missing instead of silently using UTC."""
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError(
            f"Time zone data for {name!r} is not available. Install the OS tz database "
            "(for example `apt-get install tzdata`) or the `tzdata` Python package; "
            "the sync cadence cannot run without it."
        ) from exc
