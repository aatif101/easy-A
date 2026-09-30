from __future__ import annotations

import random
import signal
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from easy_a.sync.runner import (
    MAX_WAIT_SLICE_SECONDS,
    SweepStatus,
    install_stop_signal_handlers,
    run_loop,
)
from easy_a.sync.windows import (
    IN_WINDOW_INTERVAL,
    JITTER_MAX,
    OUTSIDE_WINDOW_INTERVAL,
    RegistrationWindows,
    load_windows,
)

REAL_CONFIG = Path(__file__).resolve().parents[2] / "config" / "registration_windows.toml"

IN_WINDOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
OUTSIDE = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


class FixedRng:
    def __init__(self, value: float) -> None:
        self.value = value

    def uniform(self, a: float, b: float) -> float:
        return self.value


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


class FakeStopEvent(threading.Event):
    """A stop event whose wait() advances the fake clock instead of sleeping."""

    def __init__(self, clock: FakeClock) -> None:
        super().__init__()
        self.clock = clock
        self.timeouts: list[float] = []

    def wait(self, timeout: float | None = None) -> bool:
        assert timeout is not None
        self.timeouts.append(timeout)
        self.clock.advance(timeout)
        return self.is_set()


@dataclass(frozen=True)
class Outcome:
    status: SweepStatus
    started_at: datetime


class ScriptedSweep:
    """Returns scripted statuses (repeating the last one) and records the clock at each call."""

    def __init__(
        self,
        clock: FakeClock,
        statuses: list[SweepStatus] | None = None,
        duration: float = 0.0,
        on_call: Callable[[int], None] | None = None,
    ) -> None:
        self.clock = clock
        self.statuses = statuses or [SweepStatus.succeeded]
        self.duration = duration
        self.on_call = on_call
        self.starts: list[datetime] = []

    def __call__(self) -> Outcome:
        index = len(self.starts)
        started = self.clock.now
        self.starts.append(started)
        if self.on_call is not None:
            self.on_call(index)
        self.clock.advance(self.duration)
        return Outcome(self.statuses[min(index, len(self.statuses) - 1)], started)

    def gaps(self) -> list[float]:
        return [(b - a).total_seconds() for a, b in zip(self.starts, self.starts[1:], strict=False)]


@pytest.fixture(scope="module")
def windows() -> RegistrationWindows:
    return load_windows(REAL_CONFIG)


def _run(
    windows: RegistrationWindows,
    sweep: ScriptedSweep,
    clock: FakeClock,
    *,
    initial: datetime | None,
    rng: object,
    max_sweeps: int,
    stop: FakeStopEvent | None = None,
    on_wait: Callable[[datetime], None] | None = None,
) -> int:
    return run_loop(
        sweep,
        windows=windows,
        stop_event=stop or FakeStopEvent(clock),
        now_fn=clock,
        rng=rng,  # type: ignore[arg-type]
        initial_last_start=initial,
        max_sweeps=max_sweeps,
        on_wait=on_wait,
    )


# -- floor across restarts -----------------------------------------------------------------


@pytest.mark.parametrize("factor", [1.0, 1.2])
@pytest.mark.parametrize(
    ("initial", "floor"), [(IN_WINDOW, IN_WINDOW_INTERVAL), (OUTSIDE, OUTSIDE_WINDOW_INTERVAL)]
)
@pytest.mark.parametrize("restart_after", [0, 1, 120, 290])
def test_first_sweep_waits_until_initial_last_start_plus_the_floor(
    windows: RegistrationWindows,
    initial: datetime,
    floor: int,
    factor: float,
    restart_after: int,
) -> None:
    clock = FakeClock(initial + timedelta(seconds=restart_after))
    sweep = ScriptedSweep(clock)
    _run(windows, sweep, clock, initial=initial, rng=FixedRng(factor), max_sweeps=1)
    assert len(sweep.starts) == 1
    assert sweep.starts[0] >= initial + timedelta(seconds=floor)
    assert sweep.starts[0] == initial + timedelta(seconds=floor * factor)


def test_a_restart_long_after_the_last_sweep_runs_immediately(
    windows: RegistrationWindows,
) -> None:
    clock = FakeClock(OUTSIDE + timedelta(days=2))
    sweep = ScriptedSweep(clock)
    stop = FakeStopEvent(clock)
    _run(windows, sweep, clock, initial=OUTSIDE, rng=FixedRng(1.0), max_sweeps=1, stop=stop)
    assert sweep.starts == [OUTSIDE + timedelta(days=2)]
    assert stop.timeouts == []


def test_with_no_previous_sweep_the_first_one_runs_immediately(
    windows: RegistrationWindows,
) -> None:
    clock = FakeClock(OUTSIDE)
    sweep = ScriptedSweep(clock)
    stop = FakeStopEvent(clock)
    _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=1, stop=stop)
    assert sweep.starts == [OUTSIDE]
    assert stop.timeouts == []


def test_on_wait_receives_the_target_instant(windows: RegistrationWindows) -> None:
    clock = FakeClock(IN_WINDOW)
    sweep = ScriptedSweep(clock)
    targets: list[datetime] = []
    _run(
        windows,
        sweep,
        clock,
        initial=IN_WINDOW,
        rng=FixedRng(1.0),
        max_sweeps=1,
        on_wait=targets.append,
    )
    assert targets == [IN_WINDOW + timedelta(seconds=IN_WINDOW_INTERVAL)]


def test_sleeps_are_sliced_to_at_most_sixty_seconds(windows: RegistrationWindows) -> None:
    clock = FakeClock(OUTSIDE)
    stop = FakeStopEvent(clock)
    sweep = ScriptedSweep(clock)
    _run(windows, sweep, clock, initial=OUTSIDE, rng=FixedRng(1.0), max_sweeps=1, stop=stop)
    assert stop.timeouts
    assert max(stop.timeouts) == MAX_WAIT_SLICE_SECONDS
    assert sum(stop.timeouts) == pytest.approx(OUTSIDE_WINDOW_INTERVAL)


# -- spacing --------------------------------------------------------------------------------


def test_successive_sweeps_are_spaced_by_the_tier_floor(windows: RegistrationWindows) -> None:
    for start, floor in ((IN_WINDOW, IN_WINDOW_INTERVAL), (OUTSIDE, OUTSIDE_WINDOW_INTERVAL)):
        clock = FakeClock(start)
        sweep = ScriptedSweep(clock, duration=12.0)
        _run(windows, sweep, clock, initial=None, rng=random.Random(7), max_sweeps=25)
        assert len(sweep.starts) == 25
        assert all(gap >= floor for gap in sweep.gaps())
        assert all(gap <= floor * JITTER_MAX + 1e-6 for gap in sweep.gaps())


def test_spacing_holds_across_a_window_end_and_a_window_start(
    windows: RegistrationWindows,
) -> None:
    # End of the Nov 2-30 window (Dec 1 05:00Z) and the run-up to the Jan 7 window.
    for begin, count in (
        (datetime(2026, 12, 1, 2, 0, tzinfo=UTC), 30),
        (datetime(2027, 1, 7, 1, 0, tzinfo=UTC), 40),
    ):
        clock = FakeClock(begin)
        sweep = ScriptedSweep(clock, duration=15.0)
        _run(windows, sweep, clock, initial=None, rng=random.Random(11), max_sweeps=count)
        for previous, later in zip(sweep.starts, sweep.starts[1:], strict=False):
            floor = IN_WINDOW_INTERVAL if windows.contains(later) else OUTSIDE_WINDOW_INTERVAL
            assert (later - previous).total_seconds() >= floor


def test_the_first_sweep_of_a_window_fires_at_local_midnight(
    windows: RegistrationWindows,
) -> None:
    clock = FakeClock(datetime(2026, 11, 2, 3, 30, tzinfo=UTC))
    sweep = ScriptedSweep(clock)
    _run(
        windows,
        sweep,
        clock,
        initial=datetime(2026, 11, 2, 3, 20, tzinfo=UTC),
        rng=FixedRng(1.0),
        max_sweeps=2,
    )
    assert sweep.starts[0] == datetime(2026, 11, 2, 4, 20, tzinfo=UTC)
    assert sweep.starts[1] == datetime(2026, 11, 2, 5, 0, tzinfo=UTC)


# -- outcomes -------------------------------------------------------------------------------


def test_failures_back_off_and_a_success_resets_them(windows: RegistrationWindows) -> None:
    clock = FakeClock(IN_WINDOW)
    statuses = [
        SweepStatus.failed,
        SweepStatus.failed,
        SweepStatus.failed,
        SweepStatus.succeeded,
        SweepStatus.succeeded,
    ]
    sweep = ScriptedSweep(clock, statuses)
    _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=5)
    assert sweep.gaps() == [600.0, 1200.0, 2400.0, 300.0]


def test_backoff_is_capped_at_the_hourly_floor(windows: RegistrationWindows) -> None:
    clock = FakeClock(IN_WINDOW)
    sweep = ScriptedSweep(clock, [SweepStatus.failed])
    _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=8)
    assert sweep.gaps() == [600.0, 1200.0, 2400.0, 3600.0, 3600.0, 3600.0, 3600.0]


def test_busy_waits_one_full_tier_interval_and_is_not_a_failure(
    windows: RegistrationWindows,
) -> None:
    for start, floor in ((IN_WINDOW, IN_WINDOW_INTERVAL), (OUTSIDE, OUTSIDE_WINDOW_INTERVAL)):
        clock = FakeClock(start)
        sweep = ScriptedSweep(clock, [SweepStatus.busy, SweepStatus.busy, SweepStatus.succeeded])
        _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=3)
        assert sweep.gaps() == [float(floor), float(floor)]


def test_a_dry_run_outcome_is_paced_like_a_success(windows: RegistrationWindows) -> None:
    clock = FakeClock(IN_WINDOW)
    sweep = ScriptedSweep(clock, [SweepStatus.failed, SweepStatus.dry_run, SweepStatus.succeeded])
    _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=3)
    assert sweep.gaps() == [600.0, 300.0]


# -- stopping -------------------------------------------------------------------------------


def test_stop_event_set_mid_wait_returns_quickly_without_another_sweep(
    windows: RegistrationWindows,
) -> None:
    stop = threading.Event()
    calls: list[int] = []

    def sweep() -> Outcome:
        calls.append(1)
        raise AssertionError("no sweep may run once the stop event is set")

    now = datetime.now(UTC)
    threading.Timer(0.1, stop.set).start()
    started = time.monotonic()
    result = run_loop(
        sweep,
        windows=windows,
        stop_event=stop,
        now_fn=lambda: datetime.now(UTC),
        rng=random.Random(1),
        initial_last_start=now,
    )
    elapsed = time.monotonic() - started
    assert result == 0
    assert elapsed < 1.0
    assert calls == []


def test_stop_event_already_set_runs_no_sweep(windows: RegistrationWindows) -> None:
    clock = FakeClock(OUTSIDE)
    stop = FakeStopEvent(clock)
    stop.set()
    sweep = ScriptedSweep(clock)
    assert (
        _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=5, stop=stop) == 0
    )
    assert sweep.starts == []


def test_stop_during_a_sweep_lets_it_finish_and_starts_no_more(
    windows: RegistrationWindows,
) -> None:
    clock = FakeClock(OUTSIDE)
    stop = FakeStopEvent(clock)
    finished: list[int] = []

    class Sweep(ScriptedSweep):
        def __call__(self) -> Outcome:
            outcome = super().__call__()
            stop.set()  # SIGTERM arrives while the sweep is running
            finished.append(1)
            return outcome

    sweep = Sweep(clock)
    assert (
        _run(windows, sweep, clock, initial=None, rng=FixedRng(1.0), max_sweeps=5, stop=stop) == 0
    )
    assert len(sweep.starts) == 1
    assert finished == [1]


def test_stop_set_while_waiting_on_the_fake_clock_ends_the_loop(
    windows: RegistrationWindows,
) -> None:
    clock = FakeClock(OUTSIDE)
    stop = FakeStopEvent(clock)
    original = stop.wait
    waits: list[int] = []

    def wait_then_stop(timeout: float | None = None) -> bool:
        waits.append(1)
        result = original(timeout)
        if len(waits) == 3:
            stop.set()
            return True
        return result

    stop.wait = wait_then_stop  # type: ignore[method-assign]
    sweep = ScriptedSweep(clock)
    assert (
        _run(windows, sweep, clock, initial=OUTSIDE, rng=FixedRng(1.0), max_sweeps=5, stop=stop)
        == 0
    )
    assert sweep.starts == []


# -- signals --------------------------------------------------------------------------------


@pytest.fixture
def restore_signal_handlers() -> Iterator[None]:
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


@pytest.mark.skipif(not hasattr(signal, "SIGTERM"), reason="platform has no SIGTERM")
@pytest.mark.parametrize("name", ["SIGTERM", "SIGINT"])
def test_signal_handlers_only_set_the_stop_event(restore_signal_handlers: None, name: str) -> None:
    stop = threading.Event()
    install_stop_signal_handlers(stop)
    assert not stop.is_set()
    signal.raise_signal(getattr(signal, name))
    assert stop.is_set()
