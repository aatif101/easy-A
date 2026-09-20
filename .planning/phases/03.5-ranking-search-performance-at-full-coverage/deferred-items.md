# Phase 03.5 Deferred Items

## Plan 03.5-01 verification environment

- The repository-wide default test run cannot complete in this Python 3.14 environment because
  Starlette's deprecated `httpx` `TestClient` hangs while entering its AnyIO portal, before the
  first API test body runs. A 15-second isolated run of
  `tests/api/test_rankings_api.py::test_health_endpoint` timed out at fixture setup. Direct API
  import-order probes pass after the cache import-cycle fix.
- Running the non-API suite completed with 205 passed and 2 skipped, plus 5 failures in
  `tests/refresh/test_targets.py`. Those tests expect the committed five-target baseline while the
  user-owned `config/course_targets.toml` workspace change currently contains ten targets.
- Repository-wide strict mypy reports five existing errors in `tests/test_database_config.py`.
  Plan-owned files pass strict mypy.

These items predate or are independent of the cached-ranking implementation and were not changed
under the executor's scope boundary.

## Plan 03.5-03 verification environment

- The repository-wide suite now completes in this environment: 242 passed and 2 skipped. Its six
  failures all assume the committed five-target baseline while the preserved user-owned
  `config/course_targets.toml` contains ten targets; one is the coverage API length assertion and
  five are refresh target/count assertions. The remaining refresh suite passes with 43 passed,
  2 skipped, and those 5 target-count cases deselected.
- Repository-wide strict mypy still reports the five existing
  `tests/test_database_config.py` errors recorded above. All Plan 03.5-03 files pass strict mypy.
- `scripts/check_data_quality.py --term 202701` is blocked before database access by a pre-existing
  import cycle: `analytics.queries -> common.instructors -> easy_a.models -> rankings.cache ->
  rankings.service -> analytics.queries`. Plan 03.5-01 introduced the cache registration seam;
  Plan 03.5-03 does not alter that model/package import graph.

## Plan 03.5-05 (resolutions and deferrals)

- **RESOLVED:** the import cycle recorded above is fixed in commit `2bb984a` (`fix(03.5)`):
  `rankings/__init__` defers its service exports via a PEP 562 `__getattr__`, and the
  `analytics.queries` / `signals.resolver` imports in `cache.py` and `service.py` are now
  function-local at their single call sites. `check_data_quality.py --term 202701` runs (0 errors).
- **DEFERRED (accepted deviation, tracked in WINDOWS.md):** rankings-search p95 ~2.40s at the
  3,782-section synthetic scale exceeds the ~1.5s REQ-PERF-01 target. Deferred to a post-pilot
  tuning pass (additive index/query tuning). Not user-facing-blocked at the ~132-section pilot.
- **FOLLOW-UP:** `benchmark_rankings_search.py` labels environment/pooler only from `--url`; a
  `DATABASE_URL`-driven run cannot be certified as Supabase. Derive the label from the resolved
  engine URL.
