"""Worker loop: cadence-paced sweeps that survive restarts and stop cleanly on SIGTERM.

The loop enforces the D-22 spacing rules by asking ``RegistrationWindows.next_start`` for every
wait. A restart never sweeps early because the caller seeds ``initial_last_start`` from the latest
persisted IngestRun. The only sleep primitive is ``stop_event.wait``, so setting the event wakes
the loop at once; a sweep that is already running is never interrupted.

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from types import FrameType
from typing import Protocol

from easy_a.sync.windows import RegistrationWindows, SupportsUniform

MAX_WAIT_SLICE_SECONDS = 60.0
"""Longest single sleep, so wall-clock changes are re-evaluated at least this often."""


class SweepStatus(StrEnum):
    succeeded = "succeeded"
    failed = "failed"
    busy = "busy"
    dry_run = "dry_run"


class SweepResult(Protocol):
    """What run_loop needs to know about a finished sweep attempt."""

    @property
    def status(self) -> SweepStatus: ...

    @property
    def started_at(self) -> datetime: ...


SweepFunction = Callable[[], SweepResult]


def run_loop(
    sweep: SweepFunction,
    *,
    windows: RegistrationWindows,
    stop_event: threading.Event,
    now_fn: Callable[[], datetime],
    rng: SupportsUniform,
    initial_last_start: datetime | None,
    max_sweeps: int | None = None,
    on_wait: Callable[[datetime], None] | None = None,
) -> int:
    """Run sweeps until ``stop_event`` is set (or ``max_sweeps``, which exists for tests).

    ``initial_last_start`` is the start of the latest persisted sweep for this term, in any
    status; ``None`` means there is none and the first sweep runs immediately. Returns 0.
    Exceptions raised by ``sweep`` propagate: the sweep function reports expected failures as a
    ``failed`` result, and the supervisor restarts the process after an unexpected crash (the
    persisted start time keeps the restart from sweeping early).
    """
    last_start = initial_last_start
    failures = 0
    completed = 0

    while not stop_event.is_set():
        if max_sweeps is not None and completed >= max_sweeps:
            return 0

        now = now_fn()
        if last_start is None:
            target = now
        else:
            target = windows.next_start(last_start, now, rng=rng, failures=failures)

        if target > now and on_wait is not None:
            on_wait(target)
        if _wait_until(target, stop_event, now_fn):
            return 0
        if stop_event.is_set():
            return 0

        attempt_at = now_fn()
        result = sweep()
        completed += 1

        if result.status is SweepStatus.busy:
            last_start = attempt_at
        elif result.status is SweepStatus.failed:
            last_start = result.started_at
            failures += 1
        else:
            last_start = result.started_at
            failures = 0

    return 0


def _wait_until(
    target: datetime, stop_event: threading.Event, now_fn: Callable[[], datetime]
) -> bool:
    """Sleep until ``target`` in short slices. Returns True when the stop event fired."""
    while True:
        if stop_event.is_set():
            return True
        remaining = (target - now_fn()).total_seconds()
        if remaining <= 0:
            return False
        if stop_event.wait(timeout=min(remaining, MAX_WAIT_SLICE_SECONDS)):
            return True


def install_stop_signal_handlers(stop_event: threading.Event) -> None:
    """Make SIGTERM and SIGINT set ``stop_event`` and nothing else. Main thread only."""

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
