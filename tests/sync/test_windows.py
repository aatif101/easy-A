from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest
from pydantic import ValidationError

import easy_a.sync.windows as windows_module
from easy_a.config import Settings
from easy_a.sync import SYNC_ERROR_KINDS, SYNC_SOURCE_PREFIX, sync_source
from easy_a.sync.windows import (
    IN_WINDOW_INTERVAL,
    JITTER_MAX,
    OUTSIDE_WINDOW_INTERVAL,
    RegistrationWindows,
    SeatThresholds,
    assert_timezone_available,
    backoff_seconds,
    load_windows,
)

REAL_CONFIG = Path(__file__).resolve().parents[2] / "config" / "registration_windows.toml"

PRIORITY_URL = "https://www.usf.edu/registrar/register/registration_times.aspx"
CALENDAR_URL = "https://www.usf.edu/registrar/calendars/index.aspx"


class FixedRng:
    """Stub rng: uniform() always returns one chosen value and records the requested range."""

    def __init__(self, value: float) -> None:
        self.value = value
        self.calls: list[tuple[float, float]] = []

    def uniform(self, a: float, b: float) -> float:
        self.calls.append((a, b))
        return self.value


def utc(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> datetime:
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


@pytest.fixture(scope="module")
def windows() -> RegistrationWindows:
    return load_windows(REAL_CONFIG)


def _toml(body: str, *, timezone: str = "America/New_York", header: str = "") -> str:
    return f'{header}term = "202701"\ntimezone = "{timezone}"\n\n{body}'


def _window(label: str, start: str, end: str, source: str = PRIORITY_URL, extra: str = "") -> str:
    return (
        f'[[windows]]\nlabel = "{label}"\nstart = {start}\nend = {end}\n'
        f'source = "{source}"\n{extra}\n'
    )


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "windows.toml"
    path.write_text(text, encoding="utf-8")
    return path


# -- config file ---------------------------------------------------------------------------


def test_real_config_has_exactly_the_three_d02_windows(windows: RegistrationWindows) -> None:
    assert windows.term == "202701"
    assert windows.timezone == "America/New_York"
    assert [(w.start, w.end, w.source) for w in windows.windows] == [
        (date(2026, 11, 2), date(2026, 11, 30), PRIORITY_URL),
        (date(2027, 1, 7), date(2027, 1, 7), CALENDAR_URL),
        (date(2027, 1, 11), date(2027, 1, 15), CALENDAR_URL),
    ]
    text = REAL_CONFIG.read_text(encoding="utf-8")
    assert text.count("[[windows]]") == 3


def test_real_config_cites_usf_sources_and_states_dates_may_change(
    windows: RegistrationWindows,
) -> None:
    for window in windows.windows:
        assert window.source.startswith("https://www.usf.edu/")
    text = REAL_CONFIG.read_text(encoding="utf-8").lower()
    assert "subject to change" in text
    assert "2026-09-29" in text


def test_default_setting_points_at_the_config_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EASY_A_REGISTRATION_WINDOWS_PATH", raising=False)
    assert Settings(_env_file=None).registration_windows_path == "config/registration_windows.toml"
    monkeypatch.setenv("EASY_A_REGISTRATION_WINDOWS_PATH", "/tmp/other.toml")
    assert Settings(_env_file=None).registration_windows_path == "/tmp/other.toml"


def test_load_windows_reads_the_configured_setting_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = _write(tmp_path, _toml(_window("only", "2026-11-02", "2026-11-03")))
    monkeypatch.setenv("EASY_A_REGISTRATION_WINDOWS_PATH", str(path))
    monkeypatch.setattr("easy_a.config.get_settings", lambda: Settings(_env_file=None))
    monkeypatch.setattr(windows_module, "get_settings", lambda: Settings(_env_file=None))
    assert len(load_windows().windows) == 1


def test_loader_rejects_unknown_keys(tmp_path: Path) -> None:
    top = _write(tmp_path, _toml(_window("a", "2026-11-02", "2026-11-03"), header="bogus = 1\n"))
    with pytest.raises(ValidationError):
        load_windows(top)
    nested = _write(
        tmp_path,
        _toml(_window("a", "2026-11-02", "2026-11-03", extra='note = "x"')),
    )
    with pytest.raises(ValidationError):
        load_windows(nested)


def test_loader_rejects_overlap_disorder_and_reversed_dates(tmp_path: Path) -> None:
    overlap = _toml(
        _window("a", "2026-11-02", "2026-11-10") + _window("b", "2026-11-10", "2026-11-12")
    )
    with pytest.raises(ValidationError, match="non-overlapping"):
        load_windows(_write(tmp_path, overlap))
    unordered = _toml(
        _window("b", "2027-01-11", "2027-01-15") + _window("a", "2026-11-02", "2026-11-10")
    )
    with pytest.raises(ValidationError, match="sorted"):
        load_windows(_write(tmp_path, unordered))
    reversed_dates = _toml(_window("a", "2026-11-10", "2026-11-02"))
    with pytest.raises(ValidationError, match="starts after it ends"):
        load_windows(_write(tmp_path, reversed_dates))


def test_loader_rejects_a_bad_timezone_and_non_usf_or_non_https_sources(tmp_path: Path) -> None:
    body = _window("a", "2026-11-02", "2026-11-03")
    with pytest.raises(ValidationError, match="cannot be loaded"):
        load_windows(_write(tmp_path, _toml(body, timezone="Mars/Olympus")))
    for bad in ("http://www.usf.edu/x", "https://example.com/x", "https://evilusf.edu/x"):
        text = _toml(_window("a", "2026-11-02", "2026-11-03", source=bad))
        with pytest.raises(ValidationError, match="usf.edu"):
            load_windows(_write(tmp_path, text))


def test_loader_rejects_an_empty_window_list_and_a_bad_term(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_windows(_write(tmp_path, 'term = "202701"\ntimezone = "America/New_York"\n'))
    with pytest.raises(ValidationError):
        load_windows(
            _write(
                tmp_path, _toml(_window("a", "2026-11-02", "2026-11-03")).replace("202701", "2027")
            )
        )


def test_adjacent_but_disjoint_windows_are_allowed(tmp_path: Path) -> None:
    text = _toml(
        _window("a", "2026-11-02", "2026-11-10") + _window("b", "2026-11-11", "2026-11-12")
    )
    assert len(load_windows(_write(tmp_path, text)).windows) == 2


# -- window membership across DST ----------------------------------------------------------


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (utc(2026, 11, 2, 4, 59, 59), False),  # 23:59:59 EST on Nov 1 (DST ended that morning)
        (utc(2026, 11, 2, 5, 0, 0), True),  # 00:00 EST on Nov 2
        (utc(2026, 12, 1, 4, 59, 59), True),  # 23:59:59 EST on Nov 30
        (utc(2026, 12, 1, 5, 0, 0), False),  # 00:00 EST on Dec 1
        (utc(2027, 1, 7, 4, 59, 59), False),
        (utc(2027, 1, 7, 5, 0, 0), True),
        (utc(2027, 1, 8, 4, 59, 59), True),
        (utc(2027, 1, 8, 5, 0, 0), False),
        (utc(2027, 1, 11, 4, 59, 59), False),
        (utc(2027, 1, 11, 5, 0, 0), True),
        (utc(2027, 1, 16, 4, 59, 59), True),
        (utc(2027, 1, 16, 5, 0, 0), False),
    ],
)
def test_contains_at_local_midnight_boundaries(
    windows: RegistrationWindows, moment: datetime, expected: bool
) -> None:
    assert windows.contains(moment) is expected
    assert windows.interval_for(moment) == (
        IN_WINDOW_INTERVAL if expected else OUTSIDE_WINDOW_INTERVAL
    )


def test_contains_accepts_any_aware_timezone_and_rejects_naive(
    windows: RegistrationWindows,
) -> None:
    eastern = ZoneInfo("America/New_York")
    assert windows.contains(datetime(2026, 11, 2, 0, 0, tzinfo=eastern))
    assert not windows.contains(datetime(2026, 11, 1, 23, 59, 59, tzinfo=eastern))
    with pytest.raises(ValueError, match="timezone-aware"):
        windows.contains(datetime(2026, 11, 2, 12, 0))
    with pytest.raises(ValueError, match="timezone-aware"):
        windows.next_start(datetime(2026, 11, 2), utc(2026, 11, 2), rng=FixedRng(1.0))


def test_next_window_start_after(windows: RegistrationWindows) -> None:
    assert windows.next_window_start_after(utc(2026, 10, 1)) == utc(2026, 11, 2, 5)
    assert windows.next_window_start_after(utc(2026, 11, 2, 5)) == utc(2027, 1, 7, 5)
    assert windows.next_window_start_after(utc(2026, 12, 1)) == utc(2027, 1, 7, 5)
    assert windows.next_window_start_after(utc(2027, 1, 8)) == utc(2027, 1, 11, 5)
    assert windows.next_window_start_after(utc(2027, 1, 11, 5)) is None


# -- next_start ----------------------------------------------------------------------------


def test_jitter_is_drawn_once_from_one_to_one_point_two(windows: RegistrationWindows) -> None:
    rng = FixedRng(1.0)
    windows.next_start(utc(2026, 11, 10, 12), utc(2026, 11, 10, 12), rng=rng)
    assert rng.calls == [(1.0, JITTER_MAX)]


@pytest.mark.parametrize(
    ("prev", "factor", "gap"),
    [
        (utc(2026, 11, 10, 12), 1.0, 300),
        (utc(2026, 11, 10, 12), 1.2, 360),
        (utc(2026, 10, 10, 12), 1.0, 3600),
        (utc(2026, 10, 10, 12), 1.2, 4320),
    ],
)
def test_gaps_in_and_out_of_window(
    windows: RegistrationWindows, prev: datetime, factor: float, gap: int
) -> None:
    target = windows.next_start(prev, prev, rng=FixedRng(factor))
    assert target - prev == timedelta(seconds=gap)


def test_first_sweep_of_a_window_fires_at_local_midnight(windows: RegistrationWindows) -> None:
    prev = utc(2026, 11, 2, 4, 10)
    for factor in (1.0, 1.2):
        assert windows.next_start(prev, prev, rng=FixedRng(factor)) == utc(2026, 11, 2, 5)


def test_previous_sweep_seconds_before_a_window_waits_for_the_in_window_floor(
    windows: RegistrationWindows,
) -> None:
    prev = utc(2026, 11, 2, 4, 58)
    assert windows.next_start(prev, prev, rng=FixedRng(1.0)) == utc(2026, 11, 2, 5, 3)


def test_first_sweep_after_a_window_waits_the_full_hourly_floor(
    windows: RegistrationWindows,
) -> None:
    prev = utc(2026, 12, 1, 4, 58)  # inside (23:58 EST Nov 30)
    assert windows.next_start(prev, prev, rng=FixedRng(1.0)) == utc(2026, 12, 1, 5, 58)
    late_now = utc(2026, 12, 1, 5, 10)
    target = windows.next_start(prev, late_now, rng=FixedRng(1.0))
    assert target - prev >= timedelta(seconds=OUTSIDE_WINDOW_INTERVAL)


def test_now_later_than_the_interval_wins(windows: RegistrationWindows) -> None:
    prev = utc(2026, 11, 10, 12)
    now = prev + timedelta(seconds=1000)
    assert windows.next_start(prev, now, rng=FixedRng(1.0)) == now


def test_failure_backoff_in_window(windows: RegistrationWindows) -> None:
    prev = utc(2026, 11, 10, 12)
    expected = {1: 600, 2: 1200, 3: 2400, 4: 3600, 5: 3600, 50: 3600}
    for failures, seconds in expected.items():
        for factor in (1.0, 1.2):
            gap = windows.next_start(prev, prev, rng=FixedRng(factor), failures=failures) - prev
            assert gap == timedelta(seconds=seconds)
    assert [backoff_seconds(n) for n in (0, 1, 2, 3, 4, 9)] == [300, 600, 1200, 2400, 3600, 3600]


def test_failure_backoff_is_never_shorter_than_the_outside_tier(
    windows: RegistrationWindows,
) -> None:
    prev = utc(2026, 10, 10, 12)
    for failures in (1, 3, 8):
        gap = windows.next_start(prev, prev, rng=FixedRng(1.0), failures=failures) - prev
        assert gap == timedelta(seconds=3600)


def test_gap_never_below_the_later_sweeps_floor_in_a_randomized_sweep(
    windows: RegistrationWindows,
) -> None:
    generator = random.Random(20260929)
    start, end = utc(2026, 10, 1), utc(2027, 2, 15)
    span = int((end - start).total_seconds())
    boundaries = [
        instant
        for window in windows.windows
        for instant in (
            windows._local_midnight_utc(window.start),
            windows._local_midnight_utc(window.end + timedelta(days=1)),
        )
    ]
    checked = 0
    for index in range(2000):
        if index % 2:
            prev = generator.choice(boundaries) + timedelta(seconds=generator.randint(-7200, 7200))
        else:
            prev = start + timedelta(seconds=generator.randrange(span))
        late = generator.choice((0, 0, generator.randint(1, 7200)))
        now = prev + timedelta(seconds=late)
        failures = generator.choice((0, 0, 1, 2, 3, 5))
        target = windows.next_start(prev, now, rng=generator, failures=failures)
        gap = (target - prev).total_seconds()
        floor = IN_WINDOW_INTERVAL if windows.contains(target) else OUTSIDE_WINDOW_INTERVAL
        assert target >= now
        assert gap >= floor, (prev, now, failures, target)
        if failures == 0 and late == 0:
            tier = max(windows.interval_for(prev), windows.interval_for(target))
            assert gap <= tier * JITTER_MAX + 1e-6, (prev, target)
        checked += 1
    assert checked == 2000


# -- freshness thresholds ------------------------------------------------------------------


def test_stale_after_and_thresholds_inside_outside_and_across_boundaries(
    windows: RegistrationWindows,
) -> None:
    inside = utc(2026, 11, 10, 12)
    outside = utc(2026, 10, 10, 12)
    cases = [
        (inside, inside, 600, (375, 600)),
        (outside, outside, 7200, (4500, 7200)),
        (outside, inside, 7200, (4500, 7200)),
        (inside, outside, 7200, (4500, 7200)),
        # Across the window start: verified at 04:30Z (outside), now 05:00Z (inside).
        (utc(2026, 11, 2, 4, 30), utc(2026, 11, 2, 5, 0), 7200, (4500, 7200)),
        # Across the window end: verified in the last minute, now just after.
        (utc(2026, 12, 1, 4, 59, 59), utc(2026, 12, 1, 5, 0), 7200, (4500, 7200)),
        # Both inside, one second before the end.
        (utc(2026, 12, 1, 4, 0), utc(2026, 12, 1, 4, 59, 59), 600, (375, 600)),
    ]
    for verified_at, now, stale, thresholds in cases:
        assert windows.stale_after_seconds(verified_at, now) == stale
        result = windows.seat_thresholds(verified_at, now)
        assert result == SeatThresholds(*thresholds)
        assert (result.fresh_seconds, result.stale_seconds) == thresholds


# -- shared vocabulary and tz self-check ---------------------------------------------------


def test_sync_source_is_per_term_and_validates_the_term() -> None:
    assert SYNC_SOURCE_PREFIX == "usf_schedule_sync"
    assert sync_source("202701") == "usf_schedule_sync:202701"
    assert sync_source(202701) == "usf_schedule_sync:202701"
    with pytest.raises(ValueError):
        sync_source("2027")


def test_sync_error_kinds_vocabulary() -> None:
    assert set(SYNC_ERROR_KINDS) == {
        "usf_http",
        "usf_timeout",
        "usf_response",
        "parse",
        "scope",
        "gate",
        "database",
        "schema",
        "unexpected",
    }


def test_assert_timezone_available_passes_here_and_fails_clearly_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert_timezone_available()

    def missing(_name: str) -> ZoneInfo:
        raise ZoneInfoNotFoundError("No time zone found with key America/New_York")

    monkeypatch.setattr(windows_module, "ZoneInfo", missing)
    with pytest.raises(RuntimeError, match="tzdata"):
        assert_timezone_available()
