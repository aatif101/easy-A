---
phase: 09-hosted-beta-deployment-ci-observability
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, sync, rankings-cache, schema-guard]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-01 CI gates (ruff, mypy, pytest) this work passes under
provides:
  - "sections.removed_at (nullable timestamptz) on the Section model"
  - "Alembic 0004_sync_removed_at: removed_at column + ix_seat_snapshots_section_id_observed_at (authored, NOT applied to hosted Supabase)"
  - "refresh_section_rankings excludes removed sections and deletes their cache rows"
  - "/section 404s and /course omits removed sections; /search drops them after a rebuild"
  - "require_sync_schema / SchemaNotCurrentError startup guard for the API lifespan (09-06) and worker (09-11)"
affects: [09-03, 09-06, 09-11, 09-14, sync-worker]

actuals:
  tokens: 4133
  tasks: 2
  commits: 2
plan_head_before: 8516ef10deb56c4021589845700d78e63f9b810f
plan_head_after: ba6b1bd7b02c81add1a05c7af2784674a567f1a4

tech-stack:
  added: []
  patterns:
    - "Removal is a reversible mark (removed_at), never a row delete (D-23)"
    - "Cache rebuild deletes derived rows of removed sections via one bulk DELETE with a subquery"
    - "Schema guard raises a fixed, URL-free message and chains the driver error"

key-files:
  created:
    - migrations/versions/0004_sync_removed_at.py
    - src/easy_a/schema_guard.py
    - tests/rankings/test_removed_sections.py
    - tests/test_schema_guard.py
  modified:
    - src/easy_a/models/sections.py
    - src/easy_a/rankings/cache.py
    - src/easy_a/rankings/service.py
    - tests/api/test_rankings_api.py

key-decisions:
  - "Migration 0004 is authored and verified only via offline --sql generation and SQLite tests; hosted apply stays a manual, operator-approved step in plan 09-14"
  - "Cache cleanup deletes only section_rankings rows (synchronize_session=fetch); Section, SectionInstructor and SeatSnapshot rows are untouched"
  - "Schema guard on a Connection probes inside begin_nested() so a failed probe does not poison an outer PostgreSQL transaction"

patterns-established:
  - "Removed-section filter: Section.removed_at.is_(None) on every serving-path section selection"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "A section marked removed leaves /search after a cache rebuild and returns when unmarked; history rows retained"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/rankings/test_removed_sections.py#test_removed_section_leaves_search_and_returns_when_restored"
        status: pass
    human_judgment: false
  - id: D2
    description: "Scoped rebuild deletes removed cache rows only within its subject/course scope"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/rankings/test_removed_sections.py#test_scoped_rebuild_only_drops_removed_rows_in_scope"
        status: pass
    human_judgment: false
  - id: D3
    description: "/section returns 404 for a removed CRN, /course and /search omit it, and clearing the mark restores all three"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/api/test_rankings_api.py#test_removed_section_leaves_all_ranking_routes_and_returns_when_restored"
        status: pass
    human_judgment: false
  - id: D4
    description: "Migration 0004 offline SQL contains the column and index, single alembic head, downgrade reverses both"
    requirement: REQ-SYNC-01
    verification:
      - kind: other
        ref: "alembic upgrade 0003_create_section_rankings:0004_sync_removed_at --sql | grep -cE 'ADD COLUMN removed_at|CREATE INDEX ix_seat_snapshots_section_id_observed_at' -> 2"
        status: pass
    human_judgment: false
  - id: D5
    description: "require_sync_schema raises SchemaNotCurrentError naming 0004_sync_removed_at with no connection URL; accepts Engine and Connection"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/test_schema_guard.py"
        status: pass
    human_judgment: false
---

# Phase 9 Plan 02: removed_at end to end Summary

**`sections.removed_at` with migration 0004, cache rebuild exclusion and stale-row deletion, `/section` and `/course` filters, and a URL-free `require_sync_schema` startup guard; scoring untouched.**

## Performance

- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 4 created, 4 modified
- **Completed:** 2026-09-29

## Accomplishments

- Added nullable timezone-aware `Section.removed_at` and the `ix_seat_snapshots_section_id_observed_at` index (section_id, observed_at DESC, id DESC) to the models, so SQLite test schemas match the migration.
- Authored `0004_sync_removed_at` (down_revision `0003_create_section_rankings`); offline SQL shows `ADD COLUMN removed_at` and `CREATE INDEX ...`, the downgrade drops both, `alembic heads` reports one head. It has **not** been applied to any hosted database.
- `refresh_section_rankings` selects only `removed_at IS NULL` sections and, after the upsert loop, bulk-deletes `section_rankings` rows of removed sections in the rebuilt scope (whole term, or the given subject/course). It still does not commit.
- `rank_course_sections` and `_get_section_course_term` exclude removed sections, so the existing 404 mapping handles `/section` for a removed CRN and `/course` omits it.
- `require_sync_schema(bind)` probes `SELECT removed_at FROM sections LIMIT 0` on an Engine or Connection and raises `SchemaNotCurrentError` with a fixed message naming migration `0004_sync_removed_at`; no URL or driver text is interpolated.

## Task Commits

1. **Task 1 (tracer): model, migration 0004, guard, cache** - `34a4099` (feat)
2. **Task 2: route-level removal test and schema guard tests** - `ba6b1bd` (test)

## Verification

- `uv run pytest -q`: 393 passed, 3 skipped (tests/rankings/test_cache_parity.py unchanged and green).
- `uv run mypy src`: Success, no issues found in 74 source files.
- `uv run ruff check src tests migrations`: clean.
- Offline alembic SQL grep count: 2. `git diff --quiet origin/main -- src/easy_a/analytics`: exit 0 (no scoring change, D-02).
- Tracer feedback gate: the tracer `<verify>` was automated-only; it passed end to end before Task 2 began.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Sequencing] service.py filters landed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** The tracer test exercises `search_rankings` and the removal-then-restore contract; the `service.py` predicates (Task 2's file list) were small and made in the same edit pass as the cache change.
- **Fix:** Committed them with Task 1 (`34a4099`). Task 2's commit carries the route-level and schema guard tests that prove them.
- **Files modified:** src/easy_a/rankings/service.py
- **Commit:** 34a4099

**2. [Rule 2 - Correctness] Connection probe wrapped in a savepoint**
- **Found during:** Task 1
- **Issue:** On PostgreSQL a failed probe statement inside a caller's transaction would abort that transaction.
- **Fix:** For a `Connection`, the probe runs inside `begin_nested()`; an `Engine` gets its own short-lived connection. Test confirms the connection stays usable after a passing probe.
- **Files modified:** src/easy_a/schema_guard.py
- **Commit:** 34a4099

**Total deviations:** 2 (1 sequencing, 1 correctness hardening). **Impact:** none on scope or behavior.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The schema guard's fixed message covers T-09-06; cache-row deletion covers T-09-04; T-09-05 is covered by not applying the migration (manual apply in 09-14).

## Issues Encountered

None. The PostgreSQL `begin_nested` path of the schema guard on a stale schema is exercised only on SQLite here; the PostgreSQL integration tests still skip without `EASY_A_TEST_POSTGRES_URL`.

## Next Phase Readiness

Ready for the next Phase 9 plan. Plans 09-06 (API lifespan) and 09-11 (worker) can import `require_sync_schema`. Plan 09-14 must apply `0004_sync_removed_at` manually to hosted Supabase (with the operator's go-ahead) before any process running this code with the guard enabled starts against it. Note the hosted database currently lacks `sections.removed_at`, so deploying this code before the migration is applied would break the `/section`, `/course` and cache-rebuild queries.

## Self-Check: PASSED

- FOUND: migrations/versions/0004_sync_removed_at.py, src/easy_a/schema_guard.py, tests/rankings/test_removed_sections.py, tests/test_schema_guard.py
- FOUND commits: 34a4099, ba6b1bd
