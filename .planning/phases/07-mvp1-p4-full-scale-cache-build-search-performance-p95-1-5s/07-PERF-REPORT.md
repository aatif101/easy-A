# Phase 07 live performance evidence

## Baseline — 2026-09-22 UTC

Source: committed term `202701` in hosted Supabase, PostgreSQL via transaction pooler.
The loopback uvicorn process and benchmark resolve the same project `.env` through
`get_settings()`; neither was given a URL override. No database URLs, hostnames,
credentials or raw grade exports are included here.

Live read-only reconciliation: **3,783 sections and cache rows, 1,401 represented
courses, 212 subjects, 179 grade rows, zero non-Tampa sections**. The 1,402-entry
target configuration is not the number of courses currently represented by sections.
Cache evidence groups are 132 sections / 10 courses with `score_source=course`,
563 / 104 with `score_source=subject`, and 3,088 / 1,287 with
`score_source=global`. Subject fallback is not course-specific history. Global
fallback is unevidenced. These live counts correct the older STATE.md assertion
that all newly added courses use global fallback.

Commands (same working directory and settings):

```powershell
uv run uvicorn easy_a.api.app:app --host 127.0.0.1 --port 8000 --no-access-log
uv run python scripts/benchmark_rankings_search.py --live --term 202701 --iterations 50
uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50
```

Each mode performs five warmups and 50 measured calls. HTTP additionally checks
an unfiltered response total against stored section/cache counts before warmup.
HTTP timing includes routing, complete response-body receipt, JSON parsing and
response validation. Direct timings invoke the route with a reused database
session. HTTP creates its session through the application's existing dependency.
This measures a locally served API over hosted Supabase, not deployed-host or
browser latency.

| Mode | Completed UTC | p50 ms | p95 ms | max ms |
|---|---|---:|---:|---:|
| Direct route diagnostic | 19:59:13 | 169.25 | 231.68 | 244.86 |
| Loopback HTTP | 20:01:02 | 1023.67 | 1110.28 | 1127.79 |

The baseline HTTP run is below 1,500 ms. Phase acceptance still requires final
rebuild, parity, quality and HTTP checks after implementation. The older synthetic
2.40-second result is not reused as live evidence.

### Deterministic workload

For zero-based measured iteration `i=0..49`, `term=202701`, `limit=50`,
`offset=(i % 5)*50`; cycle the enum order `easiness_desc`, `easiness_asc`,
`withdrawal_asc`, `seats_desc`, `course`. Set `seats_open=(i % 4 == 0)`;
set `min_easiness=3.0` only when `i % 6 == 0`. Set a subject only when
`i % 3 == 0`, selecting `[MAC, ENC, AMH, PSY, BSC, CHM][i % 6]` (therefore
the actual subject-filtered calls alternate MAC and PSY). All other filters are
omitted. Warmup replays iterations 0..4. The CLI prints every measured query
and its elapsed milliseconds, plus aggregate and per-sort statistics.

### SQL and hydration diagnosis

Captured exact bound SQL emitted by the unchanged route, then ran
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on its count and page statements.
Both representative pages use limit 50, offset 0, no subject/min-easiness filter.

| Query | PostgreSQL execution ms | Root | Output rows | Shared hit blocks |
|---|---:|---|---:|---:|
| Broad easiness-desc count | 17.074 | Aggregate | 1 | 867 |
| Broad easiness-desc page | 177.756 | Limit | 50 | 672 |
| Seats-open/seats-desc count | 15.247 | Aggregate | 1 | 891 |
| Seats-open/seats-desc page | 26.062 | Limit | 50 | 891 |

Separate warmed-session stage sample (wall time includes database network):

| Query | Route ms | Count SQL ms | Page SQL ms | Hydration ms | Other route ms |
|---|---:|---:|---:|---:|---:|
| Broad easiness-desc | 336.50 | 86.32 | 227.56 | 1.96 | 20.66 |
| Seats-open/seats-desc | 186.41 | 59.72 | 116.40 | 2.03 | 8.26 |

The API dependency currently creates a new engine/session factory per request;
the direct benchmark reuses one engine/session. Thus direct and HTTP figures
are intentionally distinct. A page-query sample is slower than the other SQL
stages, but the end-to-end acceptance result already passes. An index or SQL
change still needs measured benefit, not an assumption from the old fixture.

### Whole-term build and quality baseline

Measured with `scripts/measure_term_build.py --term 202701`: `refresh_section_rankings`
runs inside its caller-owned transaction, flushes, then rolls back (the stored cache is
not changed); the whole-term `run_quality_checks` pass is read-only. Statement counts come
from SQLAlchemy `before_cursor_execute` events.

- **Cache rebuild, pre-batching code (2026-09-23, WSL client):** did **not** complete.
  Started ~00:34 UTC; at ~01:04 UTC, about 30 minutes in, while processing subject EEE (the
  468th of 1,401 represented courses in subject/number order), the hosted pooler closed the
  connection (`psycopg.OperationalError: server closed the connection unexpectedly`). No
  completion time or statement total exists; none is extrapolated.
- **Quality pass, pre-batching code:** ~35 minutes for the whole term (Phase 06-03,
  2026-09-22, `check_data_quality.py --term 202701`).

## Final — 2026-09-23 UTC

Same hosted term, same pooler, client in WSL on the operator machine. Live counts unchanged:
3,783 sections and cache rows. The Phase 6 scale validator
(`validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml`) passes
suffix-exact, reconciliation and honest-coverage after all changes.

### Changes adopted

| Change | Commit | Why (measured) |
|---|---|---|
| Whole-term grade evidence read once (07-02) | `77f510f` | per-course global/subject grade scans grew with course count |
| Instructor, GenEd and syllabus reads batched; one `now()` for `refreshed_at` (07-02) | `8855633` | after grade batching, ~6 round trips per section (~78 ms each over the pooler) remained: ≈22k round trips per rebuild |
| One engine per API process (07-03) | `006353f` | the dependency built a new engine, and so a new TLS connection, per request: the ~900 ms HTTP-vs-direct gap |
| Search pages narrow keys, then hydrates latest seats for that page only (07-03) | `ed5c751` | default-sort page plan rescanned the materialized latest-seat window per candidate row (175 ms) |
| Page keys as a CTE (07-03) | `2757674` | page-key subquery was evaluated twice on seat-filtered pages |

No index migration was added. The tables hold ~4k rows. The slow page came from a join
strategy, not a missing index, and every tuned plan below runs in under 20 ms without a new
index. Alembic head stays `0003_create_section_rankings`.

### Whole-term build and quality — after

| Operation | Rows | Wall s | Statements | Grade reads | Completed UTC |
|---|---:|---:|---:|---:|---|
| Cache rebuild (rolled back) | 3,783 | 4.77 | 15 | 1 | 06:20:00 |
| Quality pass | — | 2.45 | 12 | 3 | 06:28:00 |

Quality findings are unchanged: `info:no_historical_analytics` 3,088 and
`warning:low_confidence_ranking` 3,088; 0 errors. A run with the 07-02 grade batching
alone (before per-section batching) was started but stopped after the per-section cost
was diagnosed on a single-course profile; it has no result.

### EXPLAIN (ANALYZE, BUFFERS) — before vs after

Same bound parameters as the baseline (limit 50, offset 0, no subject/min-easiness filter).

| Query | Before ms | After ms | After plan |
|---|---:|---:|---|
| Broad easiness-desc count | 17.07 | 2.07 | Aggregate over a narrow seq scan; no seat window |
| Broad easiness-desc page | 177.76 | 3.47 | Index scan + incremental sort for 50 keys; seat window over those 50 only |
| Seats-open/seats-desc count | 15.25 | 14.01 | unchanged shape (seats filter needs every latest seat) |
| Seats-open/seats-desc page | 26.06 | 18.24 | top-N key sort once (CTE); seat window for page rows only |

### Search latency — WSL client, identical deterministic workload

Five warmups, 50 measured calls per run, same query mix as the baseline. HTTP is a local
`uvicorn easy_a.api.app:app` on 127.0.0.1:8000 over hosted Supabase; timing covers the
request, the full body and JSON validation. It does not measure a deployed host or a browser.

| Variant | Run UTC | Direct p50 / p95 / max ms | HTTP p50 / p95 / max ms |
|---|---|---|---|
| Original serve path | 06:28–06:29 | 173.63 / 233.74 / 246.76 | 1089.04 / 1202.28 / 1370.92 |
| Engine reuse only (run 1) | 06:30 | 198.29 / 309.43 / 358.38 | 315.51 / 398.64 / 429.83 |
| Engine reuse only (run 2) | 06:31 | 172.26 / 259.25 / 274.71 | 299.25 / 408.36 / 454.63 |
| Engine reuse + key paging, no CTE (run 1) | 06:30 | 116.45 / 279.27 / 309.45 | 221.94 / 402.58 / 455.84 |
| Engine reuse + key paging, no CTE (run 2) | 06:31 | 116.38 / 283.10 / 383.42 | 222.27 / 399.84 / 402.21 |
| **Final (engine reuse + key paging + CTE)** | **06:36** | **112.14 / 212.57 / 253.25** | **217.02 / 309.91 / 334.02** |

Final HTTP per sort (10 calls each, p50 / p95 ms): easiness_desc 233.74 / 323.88,
easiness_asc 212.65 / 260.14, withdrawal_asc 216.65 / 280.84, seats_desc 230.73 / 244.22,
course 214.71 / 306.19.

**REQ-PERF-01 gate: loopback HTTP p95 = 309.91 ms < 1,500 ms at 3,783 stored sections on
hosted Supabase (transaction pooler), 50 measured GETs after 5 warmups. PASS.**
Direct-call figures are diagnostics only.

### Residual risks

- The client-to-pooler round trip (~75–80 ms from this machine) dominates what remains.
  A deployed API near the database region will see different, probably lower, latency.
  That is not measured here, and neither is browser latency.
- `seats_open` counts still compute every section's latest seat (14 ms). That is fine at
  ~4k snapshots but grows with snapshot history. An index on `seat_snapshots(section_id,
  observed_at DESC, id DESC)` is the candidate if snapshot volume grows. It is not added
  now because no measurement justifies it.
- PostgreSQL integration tests still skip without `EASY_A_TEST_POSTGRES_URL`. SQL behaviour
  was checked on SQLite tests plus live hosted EXPLAIN and benchmark runs.

## Verification

- Full Python suite: 323 passed, 3 skipped. mypy clean on `src/easy_a`. Ruff is clean on
  all touched files. Two pre-existing E501 lines remain in untouched files
  (`scripts/refresh_all_tampa.py`, `src/easy_a/refresh/cleanup.py`).
- Cache parity: byte-for-byte cached vs on-demand across course/subject/global/
  instructor-course evidence and current-syllabus, schedule-note, same-instructor and
  same-course history, GenEd and ambiguous-instructor branches.
- Statement budgets: cache rebuild and quality pass statement counts do not grow with
  section count (tests).
- Phase 6 scale validator: PASS suffix-exact, PASS reconciliation, PASS honest-coverage.
