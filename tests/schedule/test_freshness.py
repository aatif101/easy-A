"""Cadence-aware seat freshness: override precedence, window boundaries and the legacy path."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from easy_a.config import get_settings
from easy_a.models import SeatSnapshot
from easy_a.schedule import freshness
from easy_a.schedule.freshness import snapshot_freshness
from easy_a.sync.windows import get_registration_windows

OUTSIDE_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
IN_WINDOW_NOW = datetime(2026, 11, 10, 15, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.delenv("EASY_A_SEAT_FRESH_SECONDS", raising=False)
    monkeypatch.delenv("EASY_A_SEAT_STALE_SECONDS", raising=False)
    monkeypatch.setattr(freshness, "_partial_override_warned", False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_overrides(
    monkeypatch: pytest.MonkeyPatch, *, fresh: int | None, stale: int | None
) -> None:
    if fresh is not None:
        monkeypatch.setenv("EASY_A_SEAT_FRESH_SECONDS", str(fresh))
    if stale is not None:
        monkeypatch.setenv("EASY_A_SEAT_STALE_SECONDS", str(stale))
    get_settings.cache_clear()


def _snapshot(observed_at: datetime, **seats: int | None) -> SeatSnapshot:
    values: dict[str, int | None] = {
        "capacity": 30,
        "enrollment": 10,
        "seats_remaining": 20,
        "wait_seats_available": 0,
    }
    values.update(seats)
    return SeatSnapshot(section_id=1, observed_at=observed_at, **values)


def _label(verified_age_seconds: int, now: datetime) -> str:
    """Freshness of a section verified ``verified_age_seconds`` ago with an ancient snapshot."""
    result = snapshot_freshness(
        _snapshot(now - timedelta(days=30)),
        as_of=now,
        verified_at=now - timedelta(seconds=verified_age_seconds),
    )
    return result.freshness.value


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, "fresh"),
        (375, "fresh"),
        (376, "aging"),
        (600, "aging"),
        (601, "stale"),
    ],
)
def test_in_window_thresholds_are_375_and_600(age: int, expected: str) -> None:
    assert _label(age, IN_WINDOW_NOW) == expected


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, "fresh"),
        (4500, "fresh"),
        (4501, "aging"),
        (7200, "aging"),
        (7201, "stale"),
    ],
)
def test_outside_window_thresholds_are_4500_and_7200(age: int, expected: str) -> None:
    assert _label(age, OUTSIDE_NOW) == expected


def test_thresholds_match_seat_thresholds_for_the_shared_windows() -> None:
    windows = get_registration_windows()
    for now in (IN_WINDOW_NOW, OUTSIDE_NOW):
        limits = windows.seat_thresholds(now, now)
        assert _label(limits.fresh_seconds, now) == "fresh"
        assert _label(limits.fresh_seconds + 1, now) == "aging"
        assert _label(limits.stale_seconds, now) == "aging"
        assert _label(limits.stale_seconds + 1, now) == "stale"


def test_window_start_boundary_uses_the_larger_outside_tier() -> None:
    # Nov 2 local midnight (EST) is 05:00Z. verified_at is just before it (outside), now is at it
    # (inside): the larger outside tier applies, so 30 minutes is still fresh (<= 4500 s).
    now = datetime(2026, 11, 2, 5, 0, tzinfo=UTC)
    verified_at = datetime(2026, 11, 2, 4, 30, tzinfo=UTC)
    result = snapshot_freshness(
        _snapshot(now - timedelta(days=2)), as_of=now, verified_at=verified_at
    )
    assert result.freshness == "fresh"
    assert result.age_seconds == 1800


def test_window_end_boundary_uses_the_larger_outside_tier() -> None:
    # The Nov window ends after Nov 30 local: Dec 1 local midnight (EST) is 05:00Z. verified_at is
    # inside the window, now is outside it: the outside tier applies here too.
    verified_at = datetime(2026, 12, 1, 4, 50, tzinfo=UTC)
    now = datetime(2026, 12, 1, 5, 20, tzinfo=UTC)
    result = snapshot_freshness(
        _snapshot(now - timedelta(days=2)), as_of=now, verified_at=verified_at
    )
    assert result.freshness == "fresh"
    assert result.age_seconds == 1800


def test_both_overrides_win_over_the_cadence(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_overrides(monkeypatch, fresh=100, stale=200)
    # 150 s is fresh under the outside cadence (4500) but aging under the override.
    assert _label(100, OUTSIDE_NOW) == "fresh"
    assert _label(150, OUTSIDE_NOW) == "aging"
    assert _label(201, OUTSIDE_NOW) == "stale"
    # And the override is also looser than the in-window cadence (375/600) where set higher.
    _set_overrides(monkeypatch, fresh=1000, stale=2000)
    assert _label(900, IN_WINDOW_NOW) == "fresh"
    assert _label(2001, IN_WINDOW_NOW) == "stale"


@pytest.mark.parametrize(("fresh", "stale"), [(100, None), (None, 200)])
def test_partial_override_is_ignored_and_warned_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    fresh: int | None,
    stale: int | None,
) -> None:
    _set_overrides(monkeypatch, fresh=fresh, stale=stale)
    with caplog.at_level(logging.WARNING, logger="easy_a.schedule.freshness"):
        # Cadence applies: 150 s would be aging/stale under either partial override values.
        assert _label(150, OUTSIDE_NOW) == "fresh"
        assert _label(4501, OUTSIDE_NOW) == "aging"
        assert _label(376, IN_WINDOW_NOW) == "aging"
    warnings = [r for r in caplog.records if "partial seat-freshness override" in r.getMessage()]
    assert len(warnings) == 1


def test_no_override_logs_no_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="easy_a.schedule.freshness"):
        _label(60, OUTSIDE_NOW)
    assert not caplog.records


def test_verified_at_older_than_snapshot_uses_the_snapshot_time() -> None:
    snapshot_at = OUTSIDE_NOW - timedelta(minutes=1)
    result = snapshot_freshness(
        _snapshot(snapshot_at), as_of=OUTSIDE_NOW, verified_at=OUTSIDE_NOW - timedelta(days=1)
    )
    assert result.freshness == "fresh"
    assert result.observed_at == snapshot_at
    assert result.age_seconds == 60


def test_naive_verified_at_is_treated_as_utc() -> None:
    verified = (OUTSIDE_NOW - timedelta(minutes=2)).replace(tzinfo=None)
    result = snapshot_freshness(
        _snapshot(OUTSIDE_NOW - timedelta(days=3)), as_of=OUTSIDE_NOW, verified_at=verified
    )
    assert result.freshness == "fresh"
    assert result.observed_at == verified.replace(tzinfo=UTC)


def test_future_verified_at_is_observed_but_unclassified() -> None:
    future = OUTSIDE_NOW + timedelta(minutes=5)
    result = snapshot_freshness(
        _snapshot(OUTSIDE_NOW - timedelta(days=1)), as_of=OUTSIDE_NOW, verified_at=future
    )
    assert result.observed_at == future
    assert result.freshness == "unavailable"
    assert result.age_seconds is None


def test_all_none_seat_values_stay_unavailable_with_the_verified_time() -> None:
    verified = OUTSIDE_NOW - timedelta(minutes=2)
    empty = _snapshot(
        OUTSIDE_NOW - timedelta(days=3),
        capacity=None,
        enrollment=None,
        seats_remaining=None,
        wait_seats_available=None,
    )
    result = snapshot_freshness(empty, as_of=OUTSIDE_NOW, verified_at=verified)
    assert result.freshness == "unavailable"
    assert result.observed_at == verified
    assert result.age_seconds is None


def test_no_snapshot_is_unavailable_even_when_verified() -> None:
    result = snapshot_freshness(None, as_of=OUTSIDE_NOW, verified_at=OUTSIDE_NOW)
    assert result.freshness == "unavailable"
    assert result.observed_at is None


@pytest.mark.parametrize(
    ("age", "expected"),
    [(600, "fresh"), (601, "aging"), (1800, "aging"), (1801, "stale")],
)
def test_without_verified_at_the_legacy_600_1800_thresholds_apply(age: int, expected: str) -> None:
    result = snapshot_freshness(_snapshot(OUTSIDE_NOW - timedelta(seconds=age)), as_of=OUTSIDE_NOW)
    assert result.freshness == expected


def test_legacy_path_uses_overrides_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_overrides(monkeypatch, fresh=5, stale=10)
    result = snapshot_freshness(_snapshot(OUTSIDE_NOW - timedelta(seconds=11)), as_of=OUTSIDE_NOW)
    assert result.freshness == "stale"


def test_unreadable_windows_fall_back_to_legacy_thresholds_never_optimistic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom() -> None:
        raise OSError("registration_windows.toml missing")

    monkeypatch.setattr("easy_a.sync.windows.get_registration_windows", _boom)
    # 7000 s is aging under the cadence (outside) but stale under the stricter legacy 1800 s.
    assert _label(7000, OUTSIDE_NOW) == "stale"
    assert _label(60, OUTSIDE_NOW) == "fresh"
