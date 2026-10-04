---
phase: 09-hosted-beta-deployment-ci-observability
plan: 05
subsystem: api
tags: [seat-freshness, verified-at, cadence-thresholds, registration-windows, rankings]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-03 easy_a.sync.windows seat_thresholds and shared registration-windows config
provides:
  - "snapshot_freshness(..., verified_at=None): cadence-aware thresholds from the later of Section.last_seen_at and the snapshot time"
  - "Optional EASY_A_SEAT_FRESH_SECONDS / EASY_A_SEAT_STALE_SECONDS overrides (default unset), applied only when both are set"
  - "LEGACY_FRESH_SECONDS / LEGACY_STALE_SECONDS (600/1800) as the unchanged fallback for the legacy path"
  - "verified_at wired through hydrate_ranking (search, section, course routes) and rank_section"
affects: [09-07, 09-08, quality-coverage, frontend-seat-freshness]

actuals:
  tokens: 6662
  tasks: 2
  commits: 2
plan_head_before: b6a6ad64536ead5dd3242831d938a0cf7dceaa4e
plan_head_after: d481293b7345d1342fdec2d63a3ec6edca852fb8

tech-stack:
  added: []
  patterns:
    - "Freshness stays read-time only: derived per request, never cached, never touches scoring (D-02, D-03)"
    - "Lazy import of easy_a.sync.windows inside the function keeps the freshness module import light"
    - "Unreadable registration-windows file falls back to the stricter legacy 600/1800 s, never to a looser tier"

key-files:
  created:
    - tests/rankings/test_verified_freshness.py
    - tests/schedule/test_freshness.py
  modified:
    - src/easy_a/schedule/freshness.py
    - src/easy_a/config.py
    - src/easy_a/rankings/cache.py
    - src/easy_a/rankings/service.py
    - tests/rankings/test_cache_parity.py
    - README.md

key-decisions:
  - "Partial overrides (only one of the two env vars set) are ignored and logged once at warning level; the cadence rule applies"
  - "If the registration-windows file cannot be read, verified-time freshness uses the legacy 600/1800 s thresholds (never optimistic) and logs a warning instead of failing public search"
  - "classify_observation keeps its public signature and per-threshold fallback: explicit argument, then settings override, then legacy constant"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "A sweep-verified section reads fresh through the search route and rank_section even when its snapshot is days old; seat counts still come from the snapshot"
    requirement: "REQ-SYNC-01"
    verification:
      - kind: integration
        ref: "tests/rankings/test_verified_freshness.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Thresholds follow the cadence (375/600 in a window, 4500/7200 outside, larger tier at a boundary); both overrides win; partial override ignored and warned once"
    requirement: "REQ-SYNC-01"
    verification:
      - kind: unit
        ref: "tests/schedule/test_freshness.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Legacy freshness contract and cache parity unchanged (600/1800 s without verified_at; scoring untouched)"
    requirement: "REQ-SYNC-01"
    verification:
      - kind: unit
        ref: "tests/refresh/test_targets.py#test_freshness_boundaries"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_cache_parity.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "No optimistic freshness: a section neither snapshotted nor verified recently is labelled stale"
    requirement: "REQ-SYNC-01"
    verification:
      - kind: unit
        ref: "tests/rankings/test_verified_freshness.py#test_old_verification_is_never_labelled_fresh"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-09-29
---

# Phase 09 Plan 05: Verified-time seat freshness Summary

**Seat freshness on the search, section and course routes is now judged from the later of `Section.last_seen_at` and the latest snapshot, against cadence-derived thresholds (375/600 s in a registration window, 4500/7200 s outside), with optional explicit overrides and the legacy 600/1800 s path frozen.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-09-29T17:15:00Z (approx)
- **Completed:** 2026-09-29T17:23:28Z
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files modified:** 8

## Accomplishments

- `snapshot_freshness` accepts `verified_at`; the observation time is the later of `verified_at` and `snapshot.observed_at` (both normalised with `as_utc`). Thresholds come from `get_registration_windows().seat_thresholds(observation_time, as_of)`, so the larger tier applies at a window boundary. The all-seat-values-None branch still returns unavailable, carrying the verified time.
- `hydrate_ranking` (used by the search, section and course routes) and `_seat_info_for` (used by `rank_section`) pass `verified_at=section.last_seen_at`. Seat counts are untouched and still come from the latest `SeatSnapshot`.
- `EASY_A_SEAT_FRESH_SECONDS` / `EASY_A_SEAT_STALE_SECONDS` are now optional (default `None`, `ge=0`). They replace the cadence thresholds only when both are set; a partial override is ignored with a one-time warning.
- The legacy path is unchanged: `classify_observation` without explicit thresholds and `snapshot_freshness` without `verified_at` still use 600/1800 s (now named `LEGACY_FRESH_SECONDS` / `LEGACY_STALE_SECONDS`). `tests/refresh/test_targets.py` is unmodified and passes.
- README seat-freshness section rewritten to document the verified-time rule, the cadence table, boundary behaviour and overrides.

## Task Commits

1. **Task 1: Sweep-verified section reads fresh through the search route (tracer)** - `753d141` (feat)
2. **Task 2: Override semantics, boundary thresholds and legacy behaviour locked by tests** - `d481293` (test)

**Tracer gate:** interactive, `human_verify_mode` end-of-phase, tracer `<verify>` automated-only. Re-ran `pytest tests/rankings/test_verified_freshness.py tests/refresh/test_targets.py tests/rankings tests/api` (126 passed) and `mypy src` (clean) after the parity-fixture fix below. Tracer verified end-to-end; expansion proceeded.

## Files Created/Modified

- `src/easy_a/schedule/freshness.py` - `verified_at`, cadence thresholds, override precedence, legacy constants, windows-unreadable fallback
- `src/easy_a/config.py` - the two seat threshold settings become optional overrides
- `src/easy_a/rankings/cache.py`, `src/easy_a/rankings/service.py` - one-line `verified_at` wiring each
- `tests/rankings/test_verified_freshness.py` - tracer: fresh, stale, in-window aging and in-window stale via `search_rankings` and `rank_section`, plus no-optimistic-freshness and snapshot-newer-than-verification cases
- `tests/schedule/test_freshness.py` - thresholds at exact edges, window start/end boundary, overrides, partial override warning, skew, naive timestamps, all-None, legacy, windows fallback
- `tests/rankings/test_cache_parity.py` - one test fixture adjusted (see deviations)
- `README.md` - seat-freshness documentation

## Decisions Made

- Partial overrides ignored with a one-time warning (documented in the `snapshot_freshness` docstring and README).
- Windows-file failure degrades to the stricter legacy thresholds rather than a 500 on public search.
- `quality/coverage.py` (third `snapshot_freshness` caller) intentionally not edited; plan 09-07 owns moving it to `verified_at`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan acceptance criterion "test_cache_parity.py passes unmodified" conflicts with the required behaviour**
- **Found during:** Task 1
- **Issue:** `test_newer_seat_snapshot_is_live_without_mutating_cached_analytics` seeds its section with `last_seen_at == AS_OF` and a newer snapshot at `AS_OF - 1 min`, then asserts `hydrated.seats.observed_at == newest_at`. Under the plan's own rule (observation time is the later of verified time and snapshot time) the observation time is correctly `AS_OF`. Cached versus on-demand parity itself still held.
- **Fix:** In that one test, set `section.last_seen_at = OBSERVED_AT` (AS_OF minus 5 min) before adding the newer snapshot, so the snapshot is the latest signal and the test's intent (a newer snapshot is live, analytics not mutated) is preserved. Four added lines including a comment; no assertion changed.
- **Files modified:** `tests/rankings/test_cache_parity.py`
- **Verification:** `tests/rankings` passes; full suite green.
- **Commit:** `753d141`

**2. [Rule 2 - Missing critical functionality] Unreadable registration-windows file must not break public search**
- **Found during:** Task 1
- **Issue:** `get_registration_windows()` reads a relative TOML path on first use. A missing or invalid file would raise inside the search route and 500 every request.
- **Fix:** `_verified_thresholds` catches `OSError` / `ValueError`, logs a warning and uses the legacy 600/1800 s thresholds, which are stricter than the cadence tiers, so freshness can never become optimistic. Covered by `test_unreadable_windows_fall_back_to_legacy_thresholds_never_optimistic`.
- **Files modified:** `src/easy_a/schedule/freshness.py`, `tests/schedule/test_freshness.py`
- **Commit:** `753d141`, `d481293`

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 2). **Impact:** no scope creep; the first corrects a plan-authoring inconsistency, the second preserves the "no optimistic freshness" prohibition under a failure mode.

## Issues Encountered

- `ruff format --check` reports pre-existing formatting drift in 28 files across the repo (including pre-existing parts of `tests/rankings/test_cache_parity.py`). Out of scope; not touched. Files created or rewritten by this plan are formatted and `ruff check` is clean.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or trust-boundary schema change. T-09-14 (misleading fresh label) and T-09-15 (env overrides) are mitigated as planned; T-09-SC: no package added.

## Verification

- `uv run pytest tests/rankings/test_verified_freshness.py tests/refresh/test_targets.py tests/rankings tests/api -q`: 126 passed
- `uv run pytest tests/schedule/test_freshness.py tests/refresh/test_targets.py -q`: 47 passed
- `uv run pytest -q`: 539 passed, 4 skipped
- `uv run mypy src`: Success: no issues found in 81 source files
- `tests/refresh/test_targets.py` unmodified (empty diff)

## Next Phase Readiness

Ready for the next Wave 2 plan. Plan 09-07 should move the `quality/coverage.py` stale-seat check to `verified_at` using the same `snapshot_freshness(..., verified_at=...)` call. The frontend can rely on the `seats.observed_at` field now meaning the verified time when a sweep is more recent than the snapshot.

## Self-Check: PASSED

- FOUND: src/easy_a/schedule/freshness.py, tests/rankings/test_verified_freshness.py, tests/schedule/test_freshness.py
- FOUND commits: 753d141, d481293
