---
phase: 09-hosted-beta-deployment-ci-observability
reviewed: 2026-09-30T20:30:00Z
depth: standard
files_reviewed: 88
files_reviewed_list:
  - .dockerignore
  - .github/workflows/ci.yml
  - Dockerfile
  - README.md
  - config/registration_windows.toml
  - docs/runbooks/hosted-beta-operations.md
  - migrations/versions/0004_sync_removed_at.py
  - render.yaml
  - scripts/benchmark_rankings_search.py
  - scripts/inventory_tampa_grades.py
  - scripts/refresh_all_tampa.py
  - scripts/validate_tampa_ingest.py
  - scripts/verify_rankings_pages.py
  - src/easy_a/analytics/queries.py
  - src/easy_a/api/app.py
  - src/easy_a/api/routes/metadata.py
  - src/easy_a/api/schemas.py
  - src/easy_a/config.py
  - src/easy_a/models/sections.py
  - src/easy_a/quality/checks.py
  - src/easy_a/quality/coverage.py
  - src/easy_a/rankings/cache.py
  - src/easy_a/rankings/service.py
  - src/easy_a/refresh/cleanup.py
  - src/easy_a/refresh/coverage.py
  - src/easy_a/refresh/service.py
  - src/easy_a/schedule/client.py
  - src/easy_a/schedule/freshness.py
  - src/easy_a/schedule/ingest.py
  - src/easy_a/schema_guard.py
  - src/easy_a/sync/__init__.py
  - src/easy_a/sync/__main__.py
  - src/easy_a/sync/apply.py
  - src/easy_a/sync/cli.py
  - src/easy_a/sync/courses.py
  - src/easy_a/sync/fetch.py
  - src/easy_a/sync/gate.py
  - src/easy_a/sync/lock.py
  - src/easy_a/sync/plan.py
  - src/easy_a/sync/runner.py
  - src/easy_a/sync/scope.py
  - src/easy_a/sync/sweep.py
  - src/easy_a/sync/windows.py
  - tests/analytics/test_removed_sections.py
  - tests/api/test_benchmark_rankings_search.py
  - tests/api/test_rankings_api.py
  - tests/api/test_request_logging.py
  - tests/api/test_sync_status.py
  - tests/api/test_verify_rankings_pages.py
  - tests/quality/test_removed_section_consumers.py
  - tests/rankings/test_cache_parity.py
  - tests/rankings/test_removed_sections.py
  - tests/rankings/test_verified_freshness.py
  - tests/refresh/test_inventory_tampa_grades.py
  - tests/refresh/test_postgres_coverage.py
  - tests/refresh/test_removed_section_consumers.py
  - tests/refresh/test_targets.py
  - tests/refresh/test_validate_tampa_ingest.py
  - tests/schedule/test_freshness.py
  - tests/schedule/test_ingest.py
  - tests/sync/__init__.py
  - tests/sync/conftest.py
  - tests/sync/sweep_support.py
  - tests/sync/test_cli.py
  - tests/sync/test_courses.py
  - tests/sync/test_diff_apply.py
  - tests/sync/test_dry_run.py
  - tests/sync/test_fetch.py
  - tests/sync/test_gate.py
  - tests/sync/test_import_hygiene.py
  - tests/sync/test_lock_postgres.py
  - tests/sync/test_runner.py
  - tests/sync/test_sweep.py
  - tests/sync/test_sweep_failures.py
  - tests/sync/test_windows.py
  - tests/sync/wholeterm_html.py
  - tests/test_ci_workflow.py
  - tests/test_database_config.py
  - tests/test_deploy_config.py
  - tests/test_schema_guard.py
  - web/src/App.test.tsx
  - web/src/App.tsx
  - web/src/api/rankings.test.ts
  - web/src/api/rankings.ts
  - web/src/components/SyncStatus.test.tsx
  - web/src/components/SyncStatus.tsx
  - web/src/fixtures/rankings.ts
  - web/src/types/rankings.ts
findings:
  critical: 1
  warning: 8
  info: 4
  total: 13
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-09-30T20:30:00Z
**Depth:** standard
**Files Reviewed:** 88
**Status:** issues_found

## Summary

The sync worker's core design holds up. The sweep runs in one transaction under `pg_try_advisory_xact_lock`, with a fixed-vocabulary error surface. All SQL is parameterized, so I found no injection path. The scoring code in `src/easy_a/analytics` changed only by the added `removed_at IS NULL` filters, so scoring behaviour is unchanged. I found no path that leaks a DB password, and the public API never serializes raw `error_message`. The `removed_at` filter is applied consistently across analytics, quality, refresh, rankings service/cache and the scripts I diffed. The public search route still depends on a cache-deletion invariant (WR-07).

The defects below are operational rather than data-corrupting. The most serious is that the documented gate override cannot actually unblock a legitimate mass removal once a prior successful sweep exists (CR-01). The rest are:
- A log-formatting bug that corrupts the JSON line of the most common failure kind (WR-01).
- Three places where the D-22 cadence and lock guarantees are weaker than documented (WR-02, WR-03, WR-04).
- A misleading startup diagnosis (WR-05).
- A single bad course that can fail every sweep (WR-06).
- Two `removed_at` restore/consistency gaps (WR-07, WR-08).

Several claims below were reproduced by running the actual code, not only read.

## Critical Issues

### CR-01: `--max-missing-fraction` cannot override the gate once a prior sweep has succeeded, so the documented mass-removal recovery path does not work

**File:** `src/easy_a/sync/gate.py:60-66` (and `src/easy_a/sync/sweep.py:257-267`, `docs/runbooks/hosted-beta-operations.md:71`)
**Issue:** The CLI help and the runbook's `gate` playbook say a legitimate mass removal is applied with `--once --max-missing-fraction X`. `run_sweep` forwards only `max_missing_fraction` to `evaluate_gate`. The other two rules, `row_floor` (in-scope rows below 90% of `last_success_records_seen`) and `subjects_absent`, always use their hard-coded defaults.

A sweep that legitimately loses more than 10% of sections therefore also trips `row_floor`, because `last_success_records_seen` is the previous succeeded run. Reproduced:

```
evaluate_gate(GateInput(500, 1000, 500, 1000, S, S), max_missing_fraction=0.9)
-> GateResult(passed=False, reasons=('row_floor 500 below 90% of 1000',))
```

A failed sweep never advances `last_success_records_seen`. So after the first real mass drop, every later sweep, automatic or manual, fails the same way. The only exits are hand-inserting a succeeded `IngestRun` or a code change. The hosted worker has had prior successful sweeps, so this is the live configuration.

`tests/sync/test_cli.py:538` passes only because `seed_from_rows` (tests/sync/sweep_support.py:81-92) never writes a succeeded `sync_source` `IngestRun`. `last_success_records_seen` is therefore `None` in that test and `row_floor` is never evaluated. The override is untested on the production path.

**Fix:** Make the override cover every rule tied to the expected size of the term, and add a test with a prior succeeded `IngestRun`. For example, pass an explicit override through `GateInput` or `evaluate_gate`:

```python
# gate.py
def evaluate_gate(inp, *, max_missing_fraction=0.10, min_row_ratio=0.90, ...):
    ...
# sweep.py: derive min_row_ratio from the operator's override
min_row_ratio = min(0.90, 1.0 - max_missing_fraction)
evaluate_gate(GateInput(...), max_missing_fraction=max_missing_fraction, min_row_ratio=min_row_ratio)
```

Also relax or scale `subjects_absent` when the override is used. Then seed a succeeded `IngestRun` in the override test.

## Warnings

### WR-01: `_JsonLineFormatter` URL scrub corrupts the JSON of failed-sweep log lines

**File:** `src/easy_a/sync/cli.py:64,91` (with `src/easy_a/sync/sweep.py:116-119`)
**Issue:** The formatter runs `_URL_RE = [a-z][a-z0-9+.-]*://\S*` over the already-serialized JSON string. `\S*` swallows the closing quote, the comma and any following non-space characters up to the next space.

`sanitize_error_detail` only redacts `postgres://` URLs, so an `httpx` status error passes through with its URLs. That message ends with the MDN URL:

```
"Server error '502 Bad Gateway' for url '...'\nFor more information check: https://developer.mozilla.org/.../502"
```

Reproduced with `sweep_failed` / `usf_http`. The emitted line is:

```
..., "error_detail": "Server error '502 Bad Gateway' for url '[redacted-url] more information check: [redacted-url] "peak_rss_mb": 72.3, "next_start_at": null}
```

`json.loads` fails on it ("Expecting ',' delimiter"). `usf_http` is the most likely hosted failure, so those lines lose `peak_rss_mb` and `next_start_at` and break any JSON log parsing on Render. No secret leaks, but the observability contract is broken.

**Fix:** Scrub string values before serializing, not the serialized text. Also redact any `scheme://` URL inside `sanitize_error_detail`, or stop echoing httpx messages and use `type(exc).__name__` plus the status code.

```python
def _scrub(value):
    if isinstance(value, str):
        return _URL_RE.sub("[redacted-url]", value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    return value

return json.dumps(_scrub(payload), default=str)
```

### WR-02: Whole-term fetch has no wall-clock deadline while holding the advisory lock and an open transaction

**File:** `src/easy_a/schedule/client.py:88-111` (called from `src/easy_a/sync/sweep.py:249`)
**Issue:** `WHOLE_TERM_READ_TIMEOUT_SECONDS = 120` is an httpx per-read timeout, meaning the gap between received bytes. It is not a total cap. `elapsed_seconds` is only measured after the body is complete. A slow-drip response, up to the 25 MB limit, can keep the sweep transaction and `pg_try_advisory_xact_lock` held indefinitely.

The transaction sits idle on the Supabase pooler the whole time. Every other worker, `--once` and `--restore-crn` then returns `busy`. A SIGTERM cannot interrupt a running sweep, and Render SIGKILLs it after `maxShutdownDelaySeconds: 90`. The transaction is rolled back, so there is no corruption, but one bad response stalls sync.

**Fix:** Enforce a total deadline inside the `iter_bytes` loop:

```python
if clock() - started > WHOLE_TERM_MAX_SECONDS:  # e.g. 180
    raise WholeTermResponseError("Whole-term response exceeded the wall-clock limit.")
```

Map it to `usf_timeout`. Consider fetching before opening the DB transaction, then taking the lock only for diff and apply. That is the larger change, but it removes the long idle-in-transaction window.

### WR-03: Cadence floor is checked outside the lock and from in-memory state, so overlapping workers can breach D-22(b)

**File:** `src/easy_a/sync/cli.py:377-382, 438-445`; `src/easy_a/sync/runner.py:66-98`; `src/easy_a/sync/sweep.py:204`
**Issue:** The floor is enforced two ways. `_run_single_sweep` reads the last run once, before `run_sweep`. The loop uses its own in-memory `last_start`. Neither re-reads `max(IngestRun.started_at)` after the lock is acquired.

The module docstring itself notes that Render runs old and new workers side by side for 60-90 s on every deploy. Suppose worker A finishes and commits at T, and worker B, whose own timer expires at T+x with x below the floor, had been waiting on the lock or had a stale `last_start`. B then gets the lock and sweeps immediately. That produces two whole-term USF requests closer together than 300 s in-window. The same applies to a manual `--once` that passed the floor check before a concurrent sweep committed.

**Fix:** Inside the locked transaction, right after `try_sweep_lock`, re-read the latest `IngestRun.started_at` for the source. If it is inside the floor, return a `busy`-like outcome without fetching:

```python
latest = session.scalar(select(func.max(IngestRun.started_at)).where(IngestRun.source == sync_source(term)))
if latest is not None and now_fn() < earliest_next_start(windows, _as_utc(latest)):
    return SweepOutcome(status=SweepStatus.busy, ...)
```

### WR-04: `--dry-run` makes a full whole-term USF request but is never recorded, so the cadence floor does not constrain it

**File:** `src/easy_a/sync/sweep.py:302-308, 356`; `src/easy_a/sync/cli.py:377-382`
**Issue:** The floor check compares against the latest recorded `IngestRun`. A dry run writes no `IngestRun`: it returns before the insert, and `_record_failure` skips recording when `dry_run`. Back-to-back `--dry-run` invocations therefore each pass the floor check and each fetch about 7 MB from USF.

A dry run also does not reset the worker's spacing, so USF sees requests closer together than the tiered floor. AGENTS.md D-22 scopes the exception to a single whole-term request per sweep on the tiered cadence. The runbook says "No option starts a sweep sooner than the cadence floor", which is not true for `--dry-run`.

**Fix:** Either record dry runs in a way the floor reads (for example a `dry_run` status that `latest_sweep_start` includes), or document and cap them explicitly. A minimal guard is a short lock-file or DB marker with its own floor.

### WR-05: `require_sync_schema` reports any database error as "migration 0004 not applied"

**File:** `src/easy_a/schema_guard.py:26-34` (callers `src/easy_a/api/app.py:35-37`, `src/easy_a/sync/cli.py:338-343`)
**Issue:** It catches every `SQLAlchemyError` from `SELECT removed_at FROM sections LIMIT 0`. That includes connection refused, auth failure, pooler errors and timeouts, and the fixed message blames the schema. A transient Supabase or pooler blip at deploy time makes the API crash-loop and the worker exit 4 with "migration 0004 has not been applied". An operator following the runbook may then look at migrations instead of connectivity.

**Fix:** Only map the undefined-column case, and let operational errors propagate as a connection problem:

```python
except sqlalchemy.exc.ProgrammingError as exc:   # psycopg UndefinedColumn / UndefinedTable
    raise SchemaNotCurrentError(SCHEMA_NOT_CURRENT_MESSAGE) from exc
# OperationalError / InterfaceError: re-raise, or raise a distinct DatabaseUnavailable with a fixed message
```

The worker's startup path should map connection errors to a separate fixed message (`_startup_failure`), still without echoing driver text.

### WR-06: One failing course auto-add aborts and repeats the whole sweep; only two exception types are isolated

**File:** `src/easy_a/sync/courses.py:166-180`; `src/easy_a/sync/sweep.py:277-280`
**Issue:** `_try_add` catches only `CatalogParseError` and `httpx.HTTPError`. Anything else escapes `add_missing` and aborts the entire sweep as `unexpected` or `database`. Examples:
- `httpx.InvalidURL`, which is not an `HTTPError`.
- Any other exception from `parse_catalog_html`.
- An `IntegrityError` inside `upsert_catalog_courses`, which also poisons the Postgres transaction.

The failing course is never negative-cached, because the exception never reaches `_failed_at`. Each retry, at backoff of at most an hour, fails the same way, so the entire term's sync goes stale because of one new course number.

**Fix:** Wrap each course in a SAVEPOINT and treat any `Exception` as a per-course failure:

```python
try:
    html = self.fetch(...); parsed = parse_catalog_html(...)
    ...
    with session.begin_nested():
        upsert_catalog_courses(session, matching)
except (CatalogParseError, httpx.HTTPError) as exc: ...
except Exception as exc:
    return f"add failed: {type(exc).__name__}"
```

### WR-07: Public search relies solely on "cache row deleted" to hide removed sections; the query has no `removed_at` guard

**File:** `src/easy_a/api/routes/rankings.py:79-85, 131-145` (not in the diff, but it is the consumer this phase depends on)
**Issue:** The removed-section filter was added to analytics, quality, refresh, rankings service/cache and the scripts. The search route reads `SectionRankingCache` joined to `Section` with no `Section.removed_at.is_(None)` condition. Correctness depends on every writer that sets `removed_at` also deleting the cache row in the same transaction. That is true today for `apply_sweep_plan`, but it is an unenforced invariant. `_restore_crns`, the legacy ingest and a future writer can each break it, and any drift shows removed sections in public results.

**Fix:** Add `Section.removed_at.is_(None)` to the key query and the page query. The join to `Section` already exists at line 87, and the filter is cheap. It also makes the `validate_tampa_ingest`/`verify_rankings_pages` reconciliation a real cross-check rather than a tautology.

### WR-08: Legacy narrow ingest clears `removed_at` without rebuilding the cache and without the sweep lock

**File:** `src/easy_a/schedule/ingest.py:146`; `src/easy_a/schedule/cli.py:32-33`
**Issue:** `_update_section` now sets `removed_at = None` (restore). `python -m easy_a.schedule.cli` calls `ingest_schedule_html` and does not call `refresh_section_rankings` (unlike `refresh/service.py` and `refresh/coverage.py`). A section restored this way has no cache row. The worker's next sweep then sees it as active and unchanged, so it plans no restore and no structural change. It stays absent from search until some unrelated structural change triggers a full rebuild.

The legacy ingest also takes no advisory lock, so it can interleave with a sweep's bulk `removed_at` writes.

**Fix:** Have the CLI rebuild the affected scope after ingest (as `refresh` does), and optionally take `try_sweep_lock` first. Alternatively, have the sweep treat "active section with no cache row" as a structural change.

## Info

### IN-01: `sanitize_error_detail` only redacts `postgres[ql]://` URLs

**File:** `src/easy_a/sync/sweep.py:58,116-119`
**Issue:** No secret leak was found. Driver errors can still carry the Supabase host, pooler user and project ref, for example `FATAL: password authentication failed for user "postgres.<ref>"`. Libpq-style `host=… user=… password=…` conninfo text is also not matched. These strings land in Render logs and `IngestRun.error_message`. The API never exposes them, because `_error_kind` maps only the kind token.
**Fix:** Also redact `password=\S+` and `user=\S+`, and consider storing only `kind: ExceptionClassName` for `database` failures.

### IN-02: Legacy freshness fallback logs a warning with traceback per call

**File:** `src/easy_a/schedule/freshness.py:119-145`
**Issue:** `get_registration_windows` is `lru_cache`d, but exceptions are not cached. If the windows file is unreadable, `_verified_thresholds` re-reads it and logs a `warning` with `exc_info=True` for every seat snapshot of every search result, roughly 50 per request. That will flood hosted logs during the exact incident it reports.
**Fix:** Log once (as done for the partial override), or cache the fallback for N seconds.

### IN-03: String-munging class names in `SyncStatus`

**File:** `web/src/components/SyncStatus.tsx:61`
**Issue:** `AMBER_PANEL.replace("mb-4 ", "")` derives a class string by editing another constant. A reorder or rename of the Tailwind classes silently breaks the spacing, and Tailwind's class scanner may not see the derived literal.
**Fix:** Define `AMBER_BASE` and compose `${AMBER_BASE} mb-4` and `${AMBER_BASE} mt-2` explicitly.

### IN-04: CI and deploy config minor hardening

**File:** `.github/workflows/ci.yml:48-51,95-98`; `render.yaml:48`
**Issue:**
- Third-party actions (`astral-sh/setup-uv`, and the others) are pinned by tag, not commit SHA. `permissions: contents: read` keeps the blast radius small.
- The `push: "**"` plus `pull_request` triggers run duplicate pipelines for same-repo PR branches.
- `--term 202701` is hard-coded in `render.yaml`, while `config/registration_windows.toml` also carries the term. A term change needs two edits, and a mismatch fails startup with exit 4, which is safe.

**Fix:** SHA-pin the actions, scope `push` to `main` or add a concurrency group that dedupes by ref, and note the two-place term in the runbook.

---

_Reviewed: 2026-09-30T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
