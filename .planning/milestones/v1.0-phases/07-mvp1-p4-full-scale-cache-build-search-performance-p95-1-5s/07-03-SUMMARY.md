---
phase: 07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
plan: 03
subsystem: api
tags: [search, sql, connection-pool, supabase, explain]

requires:
  - phase: 07-02
    provides: batched cache/quality paths
provides:
  - REQ-PERF-01 met: loopback HTTP search p95 309.91 ms at 3,783 sections on hosted Supabase
affects: [08]

key-files:
  created:
    - tests/api/test_dependencies.py
  modified:
    - src/easy_a/api/dependencies.py
    - src/easy_a/api/routes/rankings.py
    - tests/api/test_rankings_search_sql.py
    - tests/api/test_benchmark_rankings_search.py
    - .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md

key-decisions:
  - "Engine reuse is the dominant fix (HTTP p95 1,202 → ~400 ms). Key-first paging lowers median latency and server time (page 175 → 3.5 ms). A CTE removes a double-evaluated page-key subquery (seat page 36 → 18 ms)."
  - "No index migration: the tables are ~4k rows and the bad plan was a join strategy. Alembic head stays 0003. A seat_snapshots(section_id, observed_at DESC, id DESC) index is noted as the candidate if snapshot history grows."
  - "The count query joins latest seats only when seats_open filters on them; seat sort alone adds the join only to the page-key query."

requirements-completed: [REQ-PERF-01]

duration: ~45min
completed: 2026-09-23
status: complete
---

# Phase 7 Plan 3: Search tuning and the hosted p95 gate

**REQ-PERF-01 passes. Loopback HTTP GET /api/v1/rankings/search over hosted Supabase at 3,783
stored sections measures p50 217 ms, p95 309.91 ms, max 334 ms over 50 measured calls after 5
warmups (2026-09-23 06:36 UTC), down from a p95 of 1,202 ms. The API contract, scores and
seat semantics are unchanged.**

## Accomplishments

- The API dependency caches one session factory and engine per process. Previously every request
  created an engine, so each paid a new TLS connection to the pooler and leaked the engine.
- The search route counts and pages narrow cache keys, and joins latest seats only where seats
  filter or order results. It then hydrates full rows and latest seats for the 50-row page only.
  Totals, order, ties, paging, filters, escaping, GenEd EXISTS, seat fallbacks and the
  (observed_at DESC, id DESC) latest-snapshot tie-break are preserved.
- New contract tests:
  - Count reads seat snapshots only for `seats_open`.
  - Paged results concatenate to the unpaged order for seat and withdrawal sorts.
  - Equal-time snapshot tie-break.
  - One engine per process.

## Task Commits

1. Engine reuse: `006353f`
2. Key-first paging: `ed5c751`
3. CTE page keys: `2757674`

## Verification

- Full suite 323 passed, 3 skipped. mypy clean. Ruff clean on touched files.
- Phase 6 scale validator: PASS suffix-exact / reconciliation / honest-coverage.
- Before/after EXPLAIN and all variant runs, including engine-only and no-CTE runs, are in
  `07-PERF-REPORT.md`.

## Deviations

- Tests that select read statements by a leading `SELECT` now also accept `WITH`. The live
  benchmark's no-write test still rejects any INSERT, UPDATE or DELETE.
- The p95 gate was measured from a local API over hosted Supabase, as the plan defines. Deployed
  and browser latency are not measured (hosted beta, Phase 9).

---
*Completed: 2026-09-23*
