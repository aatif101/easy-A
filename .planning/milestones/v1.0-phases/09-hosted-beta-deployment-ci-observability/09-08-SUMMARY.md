---
phase: 09-hosted-beta-deployment-ci-observability
plan: 08
subsystem: database
tags: [sync, sweep, transaction, diff, change-only, dry-run, ingest-run, sqlalchemy]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-02 sections.removed_at and serving-path filters"
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-03 sync_source, SYNC_ERROR_KINDS, SweepStatus"
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-04 fetch_whole_term, apply_scope, evaluate_gate, try_sweep_lock"
provides:
  - "easy_a.sync.plan: pure build_sweep_plan diff (DbState, SweepPlan, SeatValues, ExistingSection, SECTION_FIELDS)"
  - "easy_a.sync.apply: load_db_state (three bulk reads) and apply_sweep_plan (change-only writes, chunked last_seen_at, structural-only cache rebuild)"
  - "easy_a.sync.sweep: run_sweep(...) -> SweepOutcome with succeeded, failed, busy and dry_run paths; sanitize_error_detail, classify_error, SweepGateError"
affects: [09-09, 09-10, 09-11, 09-12, sync-worker]

actuals:
  tokens: 17000
  tasks: 3
  commits: 3
plan_head_before: 495d473d52361ac220740168ab2f74e975434b96
plan_head_after: 1c8ab92529be41f977c79e39ba9e81c6e4f8134f

tech-stack:
  added: []
  patterns:
    - "Pure diff between a DbState snapshot and scoped rows; apply performs exactly what the plan lists"
    - "Column-tuple bulk reads (no ORM entities) so the identity map cannot serve stale values to refresh_section_rankings"
    - "Portable ROW_NUMBER latest-snapshot subquery kept local to the worker (no import of FastAPI routes)"
    - "Failure evidence in a second short transaction so it survives the rollback"

key-files:
  created:
    - src/easy_a/sync/plan.py
    - src/easy_a/sync/apply.py
    - src/easy_a/sync/sweep.py
    - tests/sync/conftest.py
    - tests/sync/sweep_support.py
    - tests/sync/test_sweep.py
    - tests/sync/test_diff_apply.py
    - tests/sync/test_sweep_failures.py
    - tests/sync/test_dry_run.py
  modified: []

key-decisions:
  - "Open Question 4 (recorded): IngestRun has no summary column and none is added. The full change summary lives in the returned SweepOutcome (as_log_dict, logged by the CLI in 09-11). records_seen = in-scope rows, records_inserted = new sections, records_updated = sections with any change (fields, instructor, seats, removed, restored), records_failed = unapplied in-scope sections (unknown course)."
  - "Existing sections keep their course_id: only new CRNs resolve a course (highest catalog_edition). Re-pointing an existing section to a newer edition on every sweep would break change-only writes."
  - "The sweep time written to first_seen_at, last_seen_at and history rows is FetchedTerm.fetched_at (now_fn after the fetch); IngestRun.started_at is now_fn at entry."
  - "A DB section counts as in scope for the gate and for removal only when its campus is Tampa and its course number is undergraduate (the same D-04 rule as apply_scope), so legacy or out-of-scope rows are never removed by a sweep."
  - "A dry run performs the same fetch, gate and diff, then rolls back; a gate failure in a dry run returns failed/gate and records no IngestRun."

patterns-established:
  - "Seat-only sweeps append snapshots and update seat columns but never rebuild section_rankings; only structural changes do"
  - "error_message for a failed IngestRun is '<kind>: <detail>' with kind in SYNC_ERROR_KINDS, postgres URLs replaced and a 500-character cap"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "One sweep applies USF's state in a single transaction: insert, instructor change, seat change, unchanged, removed and graduate-ignored in one pass, exactly one request, an IngestRun with the specified counts, removed CRN gone from section_rankings and from /rankings/search"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/sync/test_sweep.py#test_sweep_applies_usf_state_in_one_transaction"
        status: pass
    human_judgment: false
  - id: D2
    description: "The diff is change-only: an unchanged repeat sweep appends 0 instructor rows and 0 snapshots; whitespace/case name differences are not changes; no-observation, blank and ambiguous states append one row; seat-only changes append a snapshot without a cache rebuild; delivery_method change and restore rebuild"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_diff_apply.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Unknown-course rows are counted in records_failed and named in the outcome and IngestRun.error_message, never inserted or silently dropped; last_seen_at bulk update is chunked (2,500 CRNs, 3 statements)"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_diff_apply.py#test_unknown_course_rows_are_counted_and_named_never_dropped"
        status: pass
      - kind: unit
        ref: "tests/sync/test_diff_apply.py#test_last_seen_bulk_update_is_chunked_across_a_large_term"
        status: pass
    human_judgment: false
  - id: D4
    description: "HTTP 503, timeout, non-HTML, missing header, short row, duplicate CRN, gate trip, mid-apply database error, schema and unexpected errors all leave every table unchanged except one failed IngestRun with a kind prefix and no connection URL; busy makes no request and no write"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_sweep_failures.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Dry run writes nothing (no IngestRun, identical counts, marks and instructors), never calls a course adder, reports the ScopeReport with graduate rows and the same counts a real sweep then applies, and issues exactly one request"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_dry_run.py"
        status: pass
      - kind: command
        ref: "uv run pytest -q && uv run mypy src && uv run ruff check ."
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-29
---

# Phase 09 Plan 08: Change-only single-transaction sweep Summary

**run_sweep turns one scoped whole-term fetch into a change-only, single-transaction update of the term (instructor and seat rows only on change, reversible removals, restores, chunked last_seen_at, structural-only ranking rebuilds) with an IngestRun per sweep, sanitized failure evidence that survives rollback, a busy path and a read-only dry run.**

## Performance

- **Duration:** about 25 min of executor time
- **Completed:** 2026-09-29
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files modified:** 9 created (3 source, 6 test support and test files)

## Accomplishments

- Tracer (`tests/sync/test_sweep.py`): seeded MAC 1105 (13173, 19410, 20000) plus ten ENC sections; one sweep updates 13173 (instructor and seats), leaves 19410 alone, removes 20000, inserts 21111 and ignores a MAC 6000 graduate row. IngestRun records seen 13, inserted 1, updated 2, failed 0; 20000 leaves `section_rankings` and `/api/v1/rankings/search`; one HTTP request. Verified end to end before expansion.
- Change-only proof: two identical sweeps in a row leave `section_instructors` and `seat_snapshots` counts identical; a seat-only sweep appends one snapshot and never calls `refresh_section_rankings`; `delivery_method` changes and restores do.
- Failure safety: every failure kind (including an error raised after `apply_sweep_plan` has already written) leaves all tables and `removed_at` values unchanged and records exactly one failed IngestRun with a `SYNC_ERROR_KINDS` prefix; connection URLs (including driver-suffixed ones) are redacted and detail capped at 500 characters.
- Full suite 607 passed, 4 skipped; `mypy src` clean; `ruff check .` clean. No `easy_a.sync` module imports `easy_a.refresh` or `easy_a.api`, and importing `easy_a.sync.sweep` does not load pandas.

## Task Commits

1. **Task 1: One sweep applies USF's current state in one transaction and records an IngestRun** - `9c82643` (feat)
2. **Task 2: Change-only precision, restore, unknown-course reporting and structural-only rebuilds** - `0f11f08` (test)
3. **Task 3: Failure, busy and dry-run paths leave the database untouched and leave evidence** - `1c8ab92` (test)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `src/easy_a/sync/plan.py` - pure diff, `SECTION_FIELDS`, `structural_change`, `counts()`
- `src/easy_a/sync/apply.py` - `load_db_state`, `apply_sweep_plan`, portable latest-snapshot read
- `src/easy_a/sync/sweep.py` - `run_sweep`, `SweepOutcome`, `SweepGateError`, error classification and sanitizing
- `tests/sync/conftest.py`, `tests/sync/sweep_support.py` - SQLite engine, MockTransport client, seeding and count helpers
- `tests/sync/test_sweep.py`, `test_diff_apply.py`, `test_sweep_failures.py`, `test_dry_run.py` - new

## Decisions Made

See `key-decisions` above. The Open Question 4 decision (no summary column; counts mapped as specified) is recorded there; migration 0004 is untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Sequencing] Failure, busy and dry-run handling landed with Task 1's source commit**
- **Found during:** Task 1
- **Issue:** The gate raises `SweepGateError` and the whole transaction must roll back on any failure, so the exception handling, busy path and dry-run branch were written together with the happy path in `sweep.py`.
- **Fix:** Task 1's commit holds all three source modules; Tasks 2 and 3 are the tests that pin the change-only diff and the failure, busy and dry-run behaviour. No source change was needed after the tracer beyond a lint-only import cleanup.
- **Files modified:** src/easy_a/sync/sweep.py
- **Commit:** 9c82643

**2. [Rule 3 - Blocking] Test fixtures live in `tests/sync/conftest.py`**
- **Found during:** Task 1
- **Issue:** Importing pytest fixtures into each test module tripped ruff (F401/F811).
- **Fix:** `engine` and `session_factory` fixtures moved to `tests/sync/conftest.py`; shared helpers stay in `tests/sync/sweep_support.py`.
- **Commit:** 9c82643

Otherwise the plan executed as written.

## Auth Gates

None.

## Known Stubs

None. `course_adder` is accepted and deliberately unused until plan 09-12 (documented in the plan); unknown-course rows are reported, not dropped.

## Threat Flags

None. No new endpoint, auth path or schema change; the only new surface is the worker's writes already covered by T-09-22 to T-09-25.

## Self-Check: PASSED

- src/easy_a/sync/plan.py, apply.py, sweep.py found; tests/sync/test_sweep.py, test_diff_apply.py, test_sweep_failures.py, test_dry_run.py found.
- Commits 9c82643, 0f11f08, 1c8ab92 present in `git log`.
