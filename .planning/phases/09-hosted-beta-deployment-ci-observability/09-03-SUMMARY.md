---
phase: 09-hosted-beta-deployment-ci-observability
plan: 03
subsystem: infra
tags: [cadence, jitter, backoff, zoneinfo, pydantic, sigterm, sync-worker]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-01 CI gates (ruff, mypy, pytest) this work passes under
provides:
  - "config/registration_windows.toml: the three D-02 Spring 2027 windows with cited usf.edu sources"
  - "easy_a.sync.windows: RegistrationWindows, load_windows, get_registration_windows, interval_for, contains, next_window_start_after, next_start, stale_after_seconds, seat_thresholds, assert_timezone_available"
  - "easy_a.sync.runner: run_loop, SweepStatus, install_stop_signal_handlers"
  - "easy_a.sync: SYNC_SOURCE_PREFIX, sync_source(term), SYNC_ERROR_KINDS"
  - "settings.registration_windows_path (EASY_A_REGISTRATION_WINDOWS_PATH)"
affects: [09-05, 09-06, 09-08, 09-11, 09-15, sync-worker]

actuals:
  tokens: 10990
  tasks: 2
  commits: 2
plan_head_before: bcc426d00b8dc6ac05e0573213561826cc0fd85d
plan_head_after: 122eefd8a76bf65f95a2a15b37d112a0de20d8c3

tech-stack:
  added: []
  patterns:
    - "Pure cadence functions with an injected clock and rng (SupportsUniform protocol)"
    - "Upward-only jitter so the D-22(b) floor holds for every gap"
    - "stop_event.wait as the only sleep primitive, in slices of at most 60 s"
    - "Light import graph for the worker: no pandas, nothing from easy_a.refresh"

key-files:
  created:
    - config/registration_windows.toml
    - src/easy_a/sync/__init__.py
    - src/easy_a/sync/windows.py
    - src/easy_a/sync/runner.py
    - tests/sync/__init__.py
    - tests/sync/test_windows.py
    - tests/sync/test_runner.py
  modified:
    - src/easy_a/config.py

key-decisions:
  - "Jitter factor is uniform in [1.0, 1.2], never negative, so no gap can fall under the 300 s / 3600 s floors (reconciles phase D-01 with PROJECT.md D-22(b))"
  - "Windows are whole local days in America/New_York; membership is decided by the local calendar date, which is correct across the 2026-11-01 DST end"
  - "The first sweep of a window fires at local midnight, or at previous start plus 300 s when the previous sweep began less than 300 s before midnight"
  - "A busy outcome is neither a failure nor a reset: it records the attempt time and waits a full tier interval"
  - "Exceptions from the sweep function propagate; expected failures are returned as SweepStatus.failed"

patterns-established:
  - "Cadence and freshness thresholds are methods on RegistrationWindows so the worker and API cannot disagree"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "Registration windows config holds exactly the three D-02 windows with usf.edu sources; the loader rejects unknown keys, overlap, disorder, reversed dates, bad timezones and non-usf https sources"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_windows.py (test_real_config_*, test_loader_rejects_*)"
        status: pass
    human_judgment: false
  - id: D2
    description: "interval_for and window membership are correct at every local-midnight boundary across the Nov 1 DST change"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_windows.py#test_contains_at_local_midnight_boundaries"
        status: pass
    human_judgment: false
  - id: D3
    description: "next_start never places a sweep closer to the previous one than the later sweep's tier floor, including window ends, window starts, late now and failure backoff"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_windows.py#test_gap_never_below_the_later_sweeps_floor_in_a_randomized_sweep"
        status: pass
    human_judgment: false
  - id: D4
    description: "stale_after_seconds and seat_thresholds give 375/600 s in a window and 4500/7200 s outside, using the larger tier across a boundary"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_windows.py#test_stale_after_and_thresholds_inside_outside_and_across_boundaries"
        status: pass
    human_judgment: false
  - id: D5
    description: "run_loop honours the floor across restarts, backs off on failure, treats busy as one tier interval, and stops within 1 s on SIGTERM without interrupting a sweep"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_runner.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "The registration dates are correct for Spring 2027 (they were read from usf.edu on 2026-09-29 and the Registrar marks them subject to change)"
    requirement: REQ-SYNC-01
    verification: []
    human_judgment: true
    rationale: "Dates come from an external page that can change; a person must re-check both usf.edu pages before 2026-11-02"

duration: 12min
completed: 2026-09-29
---

# Phase 9 Plan 03: Cadence Engine Summary

**Pure registration-window cadence engine (300 s in window, 3600 s outside, upward-only jitter, floor-safe backoff, DST-correct local-day windows) plus a SIGTERM-clean runner loop that cannot sweep early across restarts.**

## Performance

- **Duration:** about 12 min
- **Completed:** 2026-09-29
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 7 created, 1 modified

## Accomplishments

- `config/registration_windows.toml` encodes the three D-02 windows (Nov 2-30 2026, Jan 7 2027, Jan 11-15 2027) with their usf.edu source URLs. The header states the fetch date (2026-09-29) and that the registrar marks the dates as subject to change.
- `RegistrationWindows` is a frozen, `extra="forbid"` pydantic model. It rejects start after end, unsorted or overlapping windows, an unloadable timezone, a non-Banner term, an empty window list and any source that is not an https URL on usf.edu. An invalid file therefore fails at startup instead of silently defaulting to the 5-minute tier.
- `next_start` is the single place the D-22(b) floor is enforced: jitter is drawn once from [1.0, 1.2], the gap is measured from the previous start, backoff is `max(tier x jitter, min(3600, 300 x 2^failures))`, a target that lands outside every window is pushed to at least the hourly gap, and the wait is capped so a window's first sweep fires at local midnight.
- `stale_after_seconds` and `seat_thresholds` are methods on the same model, so 09-05 (freshness) and 09-06 (sync-status) will read exactly what the worker uses. `settings.registration_windows_path` lets both processes resolve the same file.
- `run_loop` seeds from `initial_last_start` (so a restart or deploy never sweeps early), sleeps only through `stop_event.wait` in slices of at most 60 s, never starts a sweep once the event is set and never interrupts a running one. `install_stop_signal_handlers` only sets the event.
- 72 tests in `tests/sync` (39 windows, 33 runner). A 2,000-instant seeded invariant test (half the instants placed within 2 h of a window boundary) checks that no gap is below the later sweep's floor and that jitter never stretches a gap beyond 1.2 x the larger of the two tiers.

## Task Commits

1. **Task 1: windows config, loader, tier and threshold functions** - `8997f3c` (feat)
2. **Task 2: runner loop and signal handlers** - `122eefd` (feat)

## Verification

- `uv run pytest tests/sync -q`: 72 passed. Full suite: 465 passed, 3 skipped (the 3 skips are the existing Postgres integration tests).
- Import check: `easy_a.sync.windows` and `easy_a.sync.runner` load the real config and the timezone with no `pandas` and nothing under `easy_a.refresh` in `sys.modules`.
- `uv run mypy src`: Success, no issues in 77 source files. `uv run ruff check .`: all checks passed.
- Tracer gate: the tracer's `<verify>` carried only automated checks, so it was re-run end to end (tests, import graph, mypy) after the Task 1 commit and passed before Task 2 started.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Window-start cap could delay the first in-window sweep by up to an hour**
- **Found during:** Task 1 design, checked against the plan's cap rule
- **Issue:** The plan caps the sleep to the next window start only when that start is later than `prev_start + 300 s`. If the previous sweep started less than 300 s before local midnight (roughly one hourly sweep in twelve), the cap does not apply and the first sweep of the window would wait the full hourly interval, leaving seat data stale at the start of registration.
- **Fix:** In that case the target becomes `prev_start + 300 s` (the in-window floor), never earlier. The floor still holds because a window lasts at least one whole day, so the later sweep is inside it. Covered by `test_previous_sweep_seconds_before_a_window_waits_for_the_in_window_floor`.
- **Files modified:** `src/easy_a/sync/windows.py`, `tests/sync/test_windows.py`
- **Commit:** `8997f3c`

**2. [Rule 1 - Bug] mypy `no-any-return` on the backoff expression**
- **Found during:** Task 1 verify (`uv run mypy src`)
- **Issue:** `min(..., 300 * 2 ** n)` is typed `Any` because `int ** int` can be a float.
- **Fix:** Use `300 * (1 << doublings)` with the exponent capped at 10.
- **Files modified:** `src/easy_a/sync/windows.py`
- **Commit:** `8997f3c`

**Total deviations:** 2 auto-fixed (2 bugs). **Impact:** none on scope; deviation 1 only shortens a wait that the plan's own text ("the first sweep of a window fires at the window's local midnight") intended to be short, and never below the D-22(b) floor.

## Flagged for user review

1. **Jitter interpretation (D-01 vs PROJECT.md D-22(b)).** The factor is uniform in [1.0, 1.2] and never negative. A -20 percent jitter would put in-window sweeps under 5 minutes and out-of-window sweeps under 60 minutes, breaking both D-22(b) floors. Please confirm this reading.
2. **Research Open Question 3.** D-02 keeps Jan 7 and Jan 11-15 as separate windows, so Jan 8-10 run hourly. If you prefer one contiguous Jan 7-15 window, only `config/registration_windows.toml` changes.
3. **Research Open Question 8.** The D-02 windows total 35 days. At 288 sweeps per day that is about 10,080 whole-term requests (about 7 MB each; 9-16 s of USF server time each). This is within D-22, but please confirm the volume. The worker will log bytes and Content-Encoding per sweep (09-11), so the first sweeps show whether responses are compressed.
4. **Dates can change.** The dates were read from usf.edu/registrar/calendars/index.aspx and usf.edu/registrar/register/registration_times.aspx on 2026-09-29. The registrar says they are subject to change, so re-check both pages before 2026-11-02.

## Authentication Gates

None.

## Known Stubs

None. No placeholder data, empty defaults flowing to UI, or TODO markers in the files created or modified.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change. The only file read is the local windows config (T-09-08 mitigations are in place: `extra="forbid"`, ordering and overlap validation, https usf.edu source required).

## Next Phase Readiness

- 09-05 can call `get_registration_windows().seat_thresholds(verified_at, now)`; 09-06 can call `interval_for` and `stale_after_seconds`.
- 09-08 and 09-11 can use `sync_source(term)`, `SYNC_ERROR_KINDS`, `SweepStatus` and `run_loop`. 09-11 must seed `initial_last_start` from the latest IngestRun for `sync_source(term)` (T-09-09), call `assert_timezone_available()` at startup and call `install_stop_signal_handlers` from the main thread.
- 09-13 (Docker image) must provide tz data (`apt-get install tzdata`); `assert_timezone_available` fails loudly if it is missing.

## Self-Check: PASSED

- Files present: `config/registration_windows.toml`, `src/easy_a/sync/__init__.py`, `src/easy_a/sync/windows.py`, `src/easy_a/sync/runner.py`, `tests/sync/__init__.py`, `tests/sync/test_windows.py`, `tests/sync/test_runner.py`, and the `registration_windows_path` setting in `src/easy_a/config.py`.
- Commits `8997f3c` and `122eefd` exist on `codex/render-setup`; `git rev-list --count` from the recorded base gives 2.
- Acceptance criteria re-run: exactly three `[[windows]]` entries, boundary tests at 2026-11-02T05:00Z and 2026-12-01T05:00Z, randomized floor test, light import graph, `ruff check .` exit 0.
