---
phase: 09-hosted-beta-deployment-ci-observability
plan: 06
subsystem: api
tags: [sync-status, observability, request-logging, schema-guard, ingest-runs]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-02 require_sync_schema and Section.removed_at (migration 0004)
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-03 sync_source, SYNC_ERROR_KINDS and registration-window cadence rules
provides:
  - "GET /api/v1/metadata/sync-status?term=... with SyncStatusResponse (D-07)"
  - "One JSON log line per HTTP request on logger easy_a.request (D-08)"
  - "API lifespan refuses to start when migration 0004 is missing (Pitfall 8)"
  - "delivery-methods lists only methods of active (not removed) sections"
affects: [09-08, 09-09, 09-10, runbook]

actuals:
  tokens: 6950
  tasks: 2
  commits: 2
plan_head_before: e83c5f0593a050d8d47163cfeee5c92964f72fd2
plan_head_after: a3ae9460356e88714ba0b18dba431d3931de6b36

tech-stack:
  added: []
  patterns:
    - "Public status endpoints expose a fixed vocabulary (SYNC_ERROR_KINDS), never raw error text"
    - "Module-level _now() clock in the route module so tests pin the instant"
    - "Startup probe reuses the API's cached engine (get_api_session_factory().kw['bind']) via _startup_engine, so it shares the request pool"

key-files:
  created:
    - tests/api/test_sync_status.py
    - tests/api/test_request_logging.py
  modified:
    - src/easy_a/api/schemas.py
    - src/easy_a/api/routes/metadata.py
    - src/easy_a/api/app.py

key-decisions:
  - "D-07 (sync-status endpoint separate from /coverage) and D-08 (structured request logs, no metrics vendor) are Claude's lean, implemented as the working decisions and flagged for the user's later review"
  - "last_status is limited to succeeded/failed; any other IngestRun.status (for example a future running state) reports null rather than leaking an unvetted value"
  - "last_success_at uses finished_at of the latest succeeded run; succeeded rows with no finished_at are ignored"
  - "Unhandled exceptions log status 500 and re-raise, so the middleware never swallows an error"

requirements-completed: [REQ-OPS-01, REQ-SYNC-01]

coverage:
  - id: D1
    description: "sync-status returns all SyncStatusResponse fields from IngestRun rows of sync_source(term), with staleness = 2 x max cadence inside and outside a window"
    requirement: "REQ-SYNC-01"
    verification:
      - kind: integration
        ref: "tests/api/test_sync_status.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "sync-status never returns error_message text; unknown prefixes map to 'unexpected' (host and port asserted absent)"
    requirement: "REQ-OPS-01"
    verification:
      - kind: integration
        ref: "tests/api/test_sync_status.py#test_failed_run_reports_kind_without_leaking_error_text"
        status: pass
      - kind: integration
        ref: "tests/api/test_sync_status.py#test_unknown_error_prefix_maps_to_unexpected"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every request emits exactly one JSON line with event, method, route template (or 'unmatched'), status and duration_ms; query strings never logged"
    requirement: "REQ-OPS-01"
    verification:
      - kind: integration
        ref: "tests/api/test_request_logging.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Startup fails with SchemaNotCurrentError on a schema without sections.removed_at; skipped with the dependency override; /health stays DB-free"
    requirement: "REQ-OPS-01"
    verification:
      - kind: integration
        ref: "tests/api/test_request_logging.py#test_startup_refuses_a_schema_without_removed_at"
        status: pass
      - kind: integration
        ref: "tests/api/test_request_logging.py#test_startup_with_dependency_override_never_touches_the_engine"
        status: pass
    human_judgment: false
  - id: D5
    description: "No metrics vendor, APM agent or paid monitoring dependency added (stdlib logging only)"
    requirement: "REQ-OPS-01"
    verification: []
    human_judgment: true
    rationale: "A prohibition (D-08) verified by inspecting that pyproject.toml and uv.lock are unchanged; no test asserts the absence of a dependency"

duration: 12min
completed: 2026-09-29
---

# Phase 09 Plan 06: Sync status endpoint, request logging and schema guard Summary

**An unauthenticated `GET /api/v1/metadata/sync-status` reports last success, last status and coarse error kind, 24 h failures, cadence and staleness from IngestRun rows without leaking error text, every request now logs one JSON duration line by route template, and the API refuses to start on a database missing migration 0004.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-09-29T17:27Z
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files modified:** 5 (3 source, 2 new test files)

## Accomplishments

- `SyncStatusResponse` (schemas.py) and `GET /sync-status` (metadata.py). Three bounded queries per call: latest succeeded run (by `finished_at`, then `id`), latest run of any status (by `started_at`, then `id`), and a count of failed runs started in the last 24 h, all filtered by `source == sync_source(term)`. Term uses the same pattern as `/coverage` (shared `TERM_PATTERN`; 422 on bad input). `/coverage` and its tests are untouched.
- Staleness: `stale_after_seconds = windows.stale_after_seconds(last_success_at or now, now)`; `is_stale` when there is no success or the age exceeds that value. Verified at 3 min (fresh, cadence 3600, stale_after 7200), 3 h (stale) and inside the November window (11 min old is stale, cadence 300, stale_after 600).
- `last_error_kind` is only set when the latest run failed and is the text before the first colon when it is in `easy_a.sync.SYNC_ERROR_KINDS` (imported, not redefined), else `unexpected`. `error_message` is never serialized (T-09-16); the test asserts `6543` and `db.example.internal` are absent from the body.
- `app.py`: `logging.basicConfig(level=INFO, format="%(message)s")` plus an explicit INFO level on `easy_a.request`, and an `http` middleware (registered after CORS, so outermost) emitting `{"event","method","route","status","duration_ms"}` as JSON. `route` is the matched route template or `unmatched`; the raw path, query string and headers are never logged (T-09-17). A raising handler logs 500 and re-raises.
- `_lifespan` keeps `require_database_url()` and then calls `require_sync_schema(_startup_engine())` unless `get_db_session` is overridden. `_startup_engine()` returns the bound engine of the cached API session factory, so the probe shares the request pool. `/health` remains DB-free.
- `list_delivery_methods` filters `Section.removed_at.is_(None)`.

## Task Commits

1. **Task 1: IngestRun rows become an honest sync-status payload (tracer)** - `579a7f4` (feat)
2. **Task 2: Request-duration log line, schema guard at startup, removed-aware delivery methods** - `a3ae946` (feat)

**Tracer gate:** interactive, `human_verify_mode` end-of-phase, tracer `<verify>` automated-only. Re-ran `pytest tests/api/test_sync_status.py` (9 passed), `mypy src` (clean) and `pytest tests/api` (78 passed); tracer verified end-to-end, expansion proceeded.

## Files Created/Modified

- `src/easy_a/api/schemas.py` - `SyncStatusResponse`
- `src/easy_a/api/routes/metadata.py` - `/sync-status`, `_now`, `_error_kind`, removed-aware delivery methods
- `src/easy_a/api/app.py` - logging configuration, request middleware, `_startup_engine`, schema guard in the lifespan
- `tests/api/test_sync_status.py` - 9 tests
- `tests/api/test_request_logging.py` - 9 tests (logging, unmatched, 500 re-raise, lifespan guard, override bypass, /health, delivery methods)

## Decisions Made

- **D-07 and D-08 are Claude's lean**, implemented as working decisions and flagged for the user's later review: `/sync-status` is a separate endpoint (not folded into `/coverage`, which stays "configured targets"), and latency observability is structured logs plus the benchmark, with no metrics vendor.
- Non-`succeeded`/`failed` run statuses report `last_status: null` (the Literal is closed).
- Startup probe reuses the API's cached engine rather than building a second pool.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Delivery-methods filter landed in the Task 1 commit**
- **Found during:** Task 2
- **Issue:** The `Section.removed_at.is_(None)` edit to `metadata.py` was made together with the sync-status edits, so it is committed in Task 1 (`579a7f4`); Task 2 (`a3ae946`) carries only its test.
- **Fix:** None needed; both files' final content matches the plan. Recorded for traceability.
- **Files modified:** src/easy_a/api/routes/metadata.py
- **Commit:** 579a7f4

**Total deviations:** 1 (commit-attribution only). **Impact:** none on behaviour.

## Issues Encountered

- `ruff format --check` reports two pre-existing unformatted files under `tests/api` (`test_rankings_search_sql.py`, `test_verify_rankings_pages.py`); out of scope, untouched. The plan's verification (`ruff check`) is clean.
- The first "current schema" lifespan test used a non-shared in-memory SQLite engine and failed because the TestClient runs the lifespan on another thread; fixed with `StaticPool` and `check_same_thread=False`.

## Verification

- `uv run pytest -q`: 557 passed, 4 skipped
- `uv run mypy src`: Success, no issues found in 81 source files
- `uv run ruff check .`: All checks passed

## Known Stubs

None.

## Threat Flags

None. The new public surface (`/sync-status`, request log line) is exactly the one in the plan's threat model (T-09-16 to T-09-19); mitigations are implemented and tested. T-09-SC: no package added.

## Next Phase Readiness

09-08 (worker) must write `"<kind>: <detail>"` messages using `SYNC_ERROR_KINDS` so `last_error_kind` is informative; 09-09 can consume `/sync-status` (`fetchSyncStatus`). The runbook should add the daily sync-status check and the p95-from-logs one-liner over `easy_a.request` lines.

## Self-Check: PASSED

- FOUND: tests/api/test_sync_status.py, tests/api/test_request_logging.py
- FOUND commits: 579a7f4, a3ae946
