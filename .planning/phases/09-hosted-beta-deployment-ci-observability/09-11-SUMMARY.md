---
phase: 09-hosted-beta-deployment-ci-observability
plan: 11
subsystem: infra
tags: [sync, worker, cli, cadence-floor, sigterm, json-logging, restore, import-hygiene]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-02 require_sync_schema and sections.removed_at"
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-03 registration windows, next_start, assert_timezone_available"
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-08 run_sweep and SweepOutcome; runner.run_loop and install_stop_signal_handlers"
provides:
  - "python -m easy_a.sync --term T: always-on loop, --once, --dry-run, --restore-crn (repeatable), --log-level, --max-missing-fraction"
  - "easy_a.sync.cli: build_parser, main(argv, *, session_factory, client_factory, now_fn, windows, stop_event) -> exit code; outcome_log_dict/log_outcome"
  - "Database-backed cadence floor (latest IngestRun start, any status) for every mode; exit codes 0/1/2/3/4"
  - "One JSON line per sweep on logger easy_a.sync (stdout), URL-scrubbed"
affects: [09-12, 09-13, 09-14, runbook, render-worker]

actuals:
  tokens: 9900
  tasks: 2
  commits: 2
plan_head_before: 82095892af621096a2d073f6858184cdf52a02fc
plan_head_after: 9b96fe8b9bf4f8739eb5c14620bb7395ae16f74a

tech-stack:
  added: []
  patterns:
    - "Injectable main(): session_factory, client_factory, now_fn, windows and stop_event keywords keep the CLI testable without patching"
    - "JSON-only stdout: a formatter emits dict messages verbatim and wraps every other record (for example easy_a.sync.sweep warnings) as an event=log JSON object, then scrubs any URL"
    - "Signal handlers are installed only in the main thread when no stop event is injected, and the previous handlers are restored on exit"

key-files:
  created:
    - src/easy_a/sync/cli.py
    - src/easy_a/sync/__main__.py
    - tests/sync/test_cli.py
    - tests/sync/test_import_hygiene.py
  modified:
    - src/easy_a/sync/sweep.py

key-decisions:
  - "Floor = windows.next_start(last_start, last_start, rng=_NoJitter(), failures=0) with last_start the latest IngestRun.started_at for sync_source(term) in any status, normalized to UTC; applied to --once and --dry-run; no bypass flag exists."
  - "SweepOutcome.extra (unused until now) carries removed, restored, instructor_changes and seat_changes from the SweepPlan; the CLI JSON line reads them. instructor_changes and seat_changes count changes to existing sections; a new section's first instructor row and first snapshot belong to its insert."
  - "Startup also refuses (exit 4) when config/registration_windows.toml is for a different term than --term, so the cadence can never silently belong to another term."
  - "--restore-crn takes the sweep advisory lock (exit 2 if a sweep holds it) so it cannot interleave with a running sweep, and exits 1 when no requested CRN was restorable."
  - "--max-missing-fraction defaults to None at parse time so an explicit use can be detected and rejected in loop and restore modes (usage error, exit 2)."

patterns-established:
  - "Argparse usage errors are converted to a returned exit code inside main(), so tests assert an int and __main__ stays raise SystemExit(main())"

requirements-completed: [REQ-SYNC-01, REQ-OPS-01]

coverage:
  - id: D1
    description: "--once runs one real sweep and logs exactly one JSON line (event sweep_succeeded, counts, scope, removed, instructor and seat changes, peak_rss_mb, next_start_at); an immediate second --once is refused with exit 3 and an ISO UTC time; --dry-run exits 0 with sweep_dry_run and leaves every table count unchanged and is also floor-refused"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/sync/test_cli.py#test_once_runs_one_sweep_and_logs_one_json_line"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_second_once_is_refused_by_the_floor_with_an_iso_time"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_dry_run_reports_and_leaves_tables_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "Startup guards exit 4 with one sanitized line before any USF request: missing removed_at names 0004_sync_removed_at; an engine failure carrying a postgresql URL never leaks it; a failed sweep never logs a connection URL"
    requirement: REQ-OPS-01
    verification:
      - kind: integration
        ref: "tests/sync/test_cli.py#test_missing_removed_at_exits_4_naming_the_migration"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_engine_failure_exits_4_without_leaking_the_url"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_failed_sweep_exits_1_and_logs_no_connection_url"
        status: pass
    human_judgment: false
  - id: D3
    description: "Loop mode makes exactly one request then stops cleanly on the stop event (worker_stopped, exit 0); a restart with a recent IngestRun waits and makes zero requests; a real SIGTERM to a sleeping worker process exits 0 in under 5 s"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/sync/test_cli.py#test_loop_sweeps_once_then_stops_cleanly_on_the_stop_event"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_loop_restart_with_a_recent_ingest_run_waits_instead_of_sweeping"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_sigterm_stops_a_sleeping_worker_process_with_exit_0"
        status: pass
    human_judgment: false
  - id: D4
    description: "--restore-crn clears removed_at, puts the CRN back in section_rankings, reports not_found and not_removed, makes no USF client call, and exits 1 when nothing is restorable; --max-missing-fraction is a usage error outside --once/--dry-run and lets the operator apply a mass removal inside them"
    requirement: REQ-OPS-01
    verification:
      - kind: integration
        ref: "tests/sync/test_cli.py#test_restore_crn_clears_removed_at_and_restores_the_cache_row_without_http"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_max_missing_fraction_requires_once_or_dry_run"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_max_missing_fraction_override_lets_the_operator_apply_a_mass_removal"
        status: pass
    human_judgment: false
  - id: D5
    description: "The worker import graph (cli, sweep and the lazily loaded ranking service and models) contains neither pandas nor any easy_a.refresh module, proven in a fresh interpreter; python -m easy_a.sync --help lists every option"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/sync/test_import_hygiene.py#test_worker_import_graph_excludes_pandas_and_easy_a_refresh"
        status: pass
      - kind: integration
        ref: "tests/sync/test_cli.py#test_help_lists_every_option_in_a_subprocess"
        status: pass
      - kind: command
        ref: "uv run pytest -q && uv run mypy src && uv run ruff check ."
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-29
---

# Phase 09 Plan 11: Sync worker CLI Summary

**`python -m easy_a.sync` ships the worker binary: an always-on loop plus `--once`, `--dry-run` and `--restore-crn`, startup guards (exit 4), a database-seeded cadence floor no flag can bypass, SIGTERM-clean shutdown and one URL-scrubbed JSON outcome line per sweep.**

## Performance

- **Duration:** about 30 min
- **Completed:** 2026-09-29
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 4 created (2 source, 2 test), 1 modified (`sweep.py`, +6 lines)

## Accomplishments

- Tracer: `--once` against a seeded SQLite term with a MockTransport client runs the full path (startup checks, floor, one request, single transaction) and prints one `sweep_succeeded` line with inserted 1, updated 2, removed 1, restored 0, instructor_changes 1, seat_changes 1 and the scope breakdown. An immediate second `--once` returns 3 and prints `refused: next sweep allowed at 2026-09-29T13:00:01+00:00`. Verified end to end before expansion.
- The floor comes from the database for every mode, so restart and manual runs respect D-22(b); a recorded failed sweep counts too. A restart with a recent IngestRun sleeps and makes zero requests.
- Real-process proof: a subprocess worker on a SQLite file database with a fresh IngestRun goes to sleep, receives SIGTERM, logs `worker_stopped` and exits 0 in under 5 s. The test never touches the hosted database (it sets `DATABASE_URL` to the SQLite file and runs from a temp directory).
- `--restore-crn` runs under the sweep advisory lock, clears `removed_at`, rebuilds `section_rankings` and never builds a USF client (the test's client factory raises if called).
- Verification: `uv run pytest -q` 664 passed, 4 skipped (`tests/sync`: 171 passed, 1 skipped); `mypy src` "Success: no issues found in 86 source files"; `ruff check .` clean; `python -m easy_a.sync --help` lists all six options.

## Task Commits

1. **Task 1: `--once` and `--dry-run` with startup guards, DB-backed floor and outcome logging (tracer)** - `258d2b9` (feat)
2. **Task 2: Always-on loop with SIGTERM, restore-CRN tool and import-hygiene proof** - `9b96fe8` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] SweepOutcome did not carry the removed/restored/instructor/seat counts the log line requires**
- **Found during:** Task 1
- **Issue:** must_haves list `removed`, `restored`, `instructor_changes` and `seat_changes` in the JSON line, but `SweepOutcome` only had `records_*` counts; the `extra` field added in 09-08 was never populated.
- **Fix:** `_sweep_in_transaction` now fills `extra` from the plan (`len(plan.removals)`, `restores`, `instructor_appends`, `snapshot_appends`) for both real and dry-run outcomes. No existing field or test changed.
- **Files modified:** `src/easy_a/sync/sweep.py`
- **Commit:** 258d2b9

**2. [Rule 2 - Missing critical] Non-outcome log records would break the one-JSON-line-per-sweep contract**
- **Found during:** Task 1
- **Issue:** `easy_a.sync.sweep` logs a plain-text warning on failure; as a child of `easy_a.sync` it would reach the JSON stdout handler as a non-JSON line.
- **Fix:** the handler's formatter wraps any non-dict record as `{"event":"log",...}` with URL scrubbing, and the failure-path test confirms exactly one `sweep_failed` outcome line beside the wrapped warning.
- **Files modified:** `src/easy_a/sync/cli.py`
- **Commit:** 258d2b9

**3. [Rule 2 - Missing critical] Windows-file term mismatch guard**
- **Found during:** Task 1
- **Issue:** the plan loads the windows but never checks they belong to `--term`; the wrong term would silently drive the cadence.
- **Fix:** startup exits 4 when `windows.term != --term`.
- **Files modified:** `src/easy_a/sync/cli.py`
- **Commit:** 258d2b9

**Total deviations:** 3 auto-fixed (1 Rule 3, 2 Rule 2). **Impact:** additive only; no plan interface changed.

## Known Limitations (for the runbook, plan 09-14)

- **Repeated `--dry-run` is not floor-limited by itself.** The floor reads recorded IngestRuns and a dry run records none (09-08 design: read-only), so back-to-back dry runs after the same real sweep each make one USF request. A dry run is refused inside the floor of the last real or failed sweep, which satisfies the plan's prohibition ("after the last recorded sweep"), but the runbook should tell operators not to loop dry runs. Closing this fully would need persisted dry-run evidence, which is a schema or IngestRun decision outside this plan.
- `next_start_at` in the outcome line is the earliest allowed start (pure floor, no jitter); the loop's real wait adds up to 20% jitter and failure backoff.
- Pre-existing, out of scope: `ruff format --check .` reports unformatted files (for example `tests/sync/test_diff_apply.py`); `ruff check .` is clean and is the plan's gate.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The new surface (worker CLI, `--restore-crn`) is covered by T-09-30..T-09-33; the restore writes only `sections.removed_at` and the derived cache.

## Next Phase Readiness

Ready for 09-12 (course auto-add plugs into `run_sweep`'s `course_adder`) and 09-13 (`render.yaml` worker `dockerCommand: python -m easy_a.sync --term 202701`, exec form so SIGTERM reaches PID 1). The operator's hosted `--dry-run` remains plan 09-14's step; nothing here was run against hosted Supabase.

## Self-Check: PASSED

- FOUND: src/easy_a/sync/cli.py, src/easy_a/sync/__main__.py, tests/sync/test_cli.py, tests/sync/test_import_hygiene.py
- FOUND commits: 258d2b9, 9b96fe8 (`git rev-list --count 82095892..HEAD` = 2)
- Acceptance criteria re-run: `--help` lists all six options; `--once` returns 0 with one JSON line and the immediate repeat returns 3; missing `removed_at` returns 4 naming `0004_sync_removed_at`; loop stop, restart-floor and restore tests pass; hygiene test passes in a fresh interpreter.
