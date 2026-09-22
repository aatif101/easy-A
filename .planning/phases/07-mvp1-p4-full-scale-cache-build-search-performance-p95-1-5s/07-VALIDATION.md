---
phase: 7
slug: mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
status: draft
nyquist_compliant: false
wave_0_complete: false
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

- [ ] Add failing parity/query-count coverage for any new batch analytics path before changing cache behavior.
- [ ] Add focused environment-label tests before fixing `DATABASE_URL` resolution.
- [ ] Add regression cases before any split count/page search query or seat lookup rewrite.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale hosted latency | REQ-PERF-01 | Requires reachable hosted Supabase and its real live data. | Run the read-only loopback HTTP benchmark against the hosted engine, record dated actual section count and p95 from at least 50 measured complete responses, and check it is below 1.5 seconds. |
| Query plan diagnosis | REQ-PERF-01 | Plans depend on live PostgreSQL statistics. | Run `EXPLAIN (ANALYZE, BUFFERS)` for the representative count and page statements before and after tuning; redact credentials and raw grade rows. |

## Validation Sign-Off

- [ ] All tasks have automated verification or explicit Wave 0 dependencies.
- [ ] No three consecutive code tasks lack automated checks.
- [ ] Full suite and PostgreSQL integration path pass.
- [ ] Cache parity and honest `effective_n=0` semantics pass at live scale.
- [ ] Live hosted search p95 is below 1.5 seconds with dataset size and environment recorded.
- [ ] `nyquist_compliant: true` set after validation.

**Approval:** pending
