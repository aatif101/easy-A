---
phase: 7
slug: mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-22
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for REQ-PERF-01 and the three verified plans.

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/rankings/test_cache_parity.py tests/api/test_rankings_search_sql.py tests/refresh/test_rankings_cache_refresh.py -q` |
| Full suite command | `uv run pytest -q` |
| Estimated runtime | Measure during execution; the hosted integration path depends on network latency. |

## Sampling Rate

- After each code task: run the affected targeted tests.
- After each wave: run the quick command and relevant PostgreSQL integration tests when `EASY_A_TEST_POSTGRES_URL` is configured.
- Before Phase 7 verification: run the full suite, cache parity checks, and the live read-only Supabase benchmark.
- Record actual test and benchmark duration; do not assert a feedback-latency target before measuring it.

## Per-Task Verification Map

| Task | Wave | Requirement | Test or evidence |
|------|------|-------------|------------------|
| 07-01-01 — live benchmark tracer | 1 | REQ-PERF-01 | `uv run pytest tests/api/test_benchmark_rankings_search.py tests/api/test_rankings_search_sql.py -q` |
| 07-01-02 — full-scale baseline | 1 | REQ-PERF-01 | `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50`; dated baseline report |
| 07-02-01 — batched historical evidence | 2 | REQ-PERF-01 | `uv run pytest tests/analytics/test_queries.py -q` |
| 07-02-02 — full-term cache and quality paths | 2 | REQ-PERF-01 | `uv run pytest tests/rankings/test_cache_parity.py tests/refresh/test_rankings_cache_refresh.py tests/analytics/test_queries.py -q` |
| 07-03-01 — measured search query tuning | 3 | REQ-PERF-01 | `uv run pytest tests/api/test_rankings_search_sql.py tests/rankings/test_cache_parity.py -q` |
| 07-03-02 — index decision and hosted p95 gate | 3 | REQ-PERF-01 | Full suite, live loopback HTTP benchmark, Phase 6 scale validator, and dated 07-PERF-REPORT.md |

## Wave 0 Requirements

- [x] Add failing parity/query-count coverage for any new batch analytics path before changing cache behavior.
- [x] Add focused environment-label tests before fixing `DATABASE_URL` resolution.
- [x] Add regression cases before any split count/page search query or seat lookup rewrite.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale hosted latency | REQ-PERF-01 | Requires reachable hosted Supabase and its real live data. | Run the read-only loopback HTTP benchmark against the hosted engine, record dated actual section count and p95 from at least 50 measured complete responses, and check it is below 1.5 seconds. |
| Query plan diagnosis | REQ-PERF-01 | Plans depend on live PostgreSQL statistics. | Run `EXPLAIN (ANALYZE, BUFFERS)` for the representative count and page statements before and after tuning; redact credentials and raw grade rows. |

## Validation Sign-Off

- [x] All tasks have automated verification or explicit Wave 0 dependencies.
- [x] No three consecutive code tasks lack automated checks.
- [~] Full suite passes (323 passed, 3 skipped). The PostgreSQL integration path still skips
  because `EASY_A_TEST_POSTGRES_URL` is not configured. Live hosted EXPLAIN and benchmark runs
  cover the SQL instead.
- [x] Cache parity and honest `effective_n=0` semantics pass (parity tests; live split
  unchanged at 132 course / 563 subject / 3,088 global; scale validator honest-coverage PASS).
- [x] Live hosted search p95 is below 1.5 seconds: loopback HTTP p95 309.91 ms, 3,783 sections,
  hosted Supabase transaction pooler, 50 measured after 5 warmups, 2026-09-23 06:36 UTC.
- [x] `nyquist_compliant: true` set after validation.

## Measured results (2026-09-23)

| Task | Evidence |
|------|----------|
| 07-01-01 | benchmark tests pass (`2336d69`, `4985b80`) |
| 07-01-02 | baseline HTTP p95 1,110 ms (Windows) / 1,202 ms (WSL); pre-batch rebuild did not complete (connection dropped after ~30 min) |
| 07-02-01 | `tests/analytics/test_queries.py` batch-vs-public parity pass (`77f510f`) |
| 07-02-02 | rebuild 4.77 s / 15 statements; quality 2.45 s / 12 statements; parity and statement-budget tests pass (`8855633`) |
| 07-03-01 | search contract tests pass; page SQL 177.8 → 3.5 ms (`ed5c751`, `2757674`) |
| 07-03-02 | HTTP p95 309.91 ms; no index needed; scale validator PASS (`006353f`) |

**Approval:** validated 2026-09-23 (see `07-PERF-REPORT.md`)
