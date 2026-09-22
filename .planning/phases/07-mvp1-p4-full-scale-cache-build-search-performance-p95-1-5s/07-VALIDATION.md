---
phase: 7
slug: mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-22
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for REQ-PERF-01. Update the task map after plans are final.

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

The planner will assign task IDs and automated commands. Every cache or search behavior change must have a targeted parity/regression check. The final performance task requires a dated live measurement.

| Behavior | Requirement | Test or evidence |
|----------|-------------|------------------|
| Batched cache build preserves every non-seat ranking field, fallback source, confidence, and provenance | REQ-PERF-01 | `tests/rankings/test_cache_parity.py` and PostgreSQL integration path |
| SQL count, filters, sorts, ties, pagination, and live seats preserve the API contract | REQ-PERF-01 | `tests/api/test_rankings_search_sql.py` |
| Benchmark labels the resolved engine target and never prints credentials | REQ-PERF-01 | Focused benchmark unit tests and smoke run |
| Hosted search p95 is below 1.5 seconds over the full live Tampa term | REQ-PERF-01 | Dated read-only Supabase benchmark report with 3,783-section dataset, query mix, p50/p95/max, and environment |

## Wave 0 Requirements

- [ ] Add failing parity/query-count coverage for any new batch analytics path before changing cache behavior.
- [ ] Add focused environment-label tests before fixing `DATABASE_URL` resolution.
- [ ] Add regression cases before any split count/page search query or seat lookup rewrite.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full-scale hosted latency | REQ-PERF-01 | Requires reachable hosted Supabase and its real live data. | Run the read-only benchmark against the resolved hosted engine, record dated 3,783-section environment and p95, and check it is below 1.5 seconds. |
| Query plan diagnosis | REQ-PERF-01 | Plans depend on live PostgreSQL statistics. | Run `EXPLAIN (ANALYZE, BUFFERS)` for the representative count and page statements before and after tuning; redact credentials and raw grade rows. |

## Validation Sign-Off

- [ ] All tasks have automated verification or explicit Wave 0 dependencies.
- [ ] No three consecutive code tasks lack automated checks.
- [ ] Full suite and PostgreSQL integration path pass.
- [ ] Cache parity and honest `effective_n=0` semantics pass at live scale.
- [ ] Live hosted search p95 is below 1.5 seconds with dataset size and environment recorded.
- [ ] `nyquist_compliant: true` set after validation.

**Approval:** pending
