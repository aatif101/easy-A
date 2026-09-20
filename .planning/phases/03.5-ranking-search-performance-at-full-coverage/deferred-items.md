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
