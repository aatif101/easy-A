---
phase: 09-hosted-beta-deployment-ci-observability
plan: 12
subsystem: database
tags: [sync, catalog, auto-add, pacing, negative-cache, tomllib, sqlalchemy]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-08 run_sweep, build_sweep_plan, DbState.course_ids, dry-run contract"
provides:
  - "easy_a.sync.courses: CourseAdder (2 s pacing, 10/sweep cap, 6 h negative cache), AutoAddResult, CourseAdderLike, default_course_adder(), load_catalog_settings(), CatalogSettingsError"
  - "run_sweep auto-adds new in-scope courses after the gate and before build_sweep_plan; SweepOutcome.auto_added and .unapplied"
  - "plan.new_course_keys: the in-scope courses only new CRNs reference that Easy-A lacks"
affects: [09-13, 09-14, 09-15, sync-worker]

actuals:
  tokens: 7000
  tasks: 2
  commits: 2
plan_head_before: afd4ac54dbc23dd9a408cc3880dce6e06aa48b7d
plan_head_after: ff4b648fc387571d13a8ca52939c4ecc56a358bb

tech-stack:
  added: []
  patterns:
    - "Catalog settings read with tomllib in easy_a.sync.courses so the worker never imports easy_a.refresh (pandas)"
    - "Adder injected into run_sweep through a small Protocol; default is a lazily created process singleton so the negative cache outlives one sweep"
    - "tests/sync autouse fixture swaps the default adder for an offline one so no test can reach USF"

key-files:
  created:
    - src/easy_a/sync/courses.py
    - tests/sync/test_courses.py
  modified:
    - src/easy_a/sync/sweep.py
    - src/easy_a/sync/plan.py
    - src/easy_a/sync/cli.py
    - tests/sync/conftest.py
    - tests/sync/test_dry_run.py

key-decisions:
  - "Auto-add is a paced catalog fetch per new course, never a schedule-derived stand-in row (a made-up edition could outrank the real one in resolve_course_id and split a course; RESEARCH Pattern 10)."
  - "Only courses referenced by CRNs not already in the database are looked up (new_course_keys), so an existing section's course is never re-fetched."
  - "Failed and deferred courses stay unknown: their rows count in records_failed and are named with reasons in IngestRun.error_message, capped at 2,000 characters; the sweep still succeeds."
  - "Deferred (cap) courses are not negative-cached, so the next sweep retries them immediately; only fetch/parse failures wait 6 hours."
  - "A missing or malformed catalog settings file raises CatalogSettingsError (a ValueError), which the sweep maps to a failed run of kind unexpected with nothing written."

patterns-established:
  - "Sweeps without an explicit adder use the worker singleton; tests must monkeypatch it (autouse in tests/sync/conftest.py)"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "A course USF lists but Easy-A lacks is added in the same sweep with its sections, one instructor row and one snapshot each, exactly one catalog URL requested, and its section_rankings rows carry score_source subject/global with effective_n 0"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/sync/test_courses.py#test_unknown_course_is_added_in_the_same_sweep_with_the_honest_fallback_label"
        status: pass
    human_judgment: false
  - id: D2
    description: "Catalog requests are paced (sleeps [2.0, 2.0], none before the first), capped at 10 per sweep with the eleventh deferred and fetched on a later sweep, and never made for out-of-scope (graduate) courses"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_courses.py#test_requests_are_paced_two_seconds_apart_with_no_initial_delay"
        status: pass
      - kind: unit
        ref: "tests/sync/test_courses.py#test_per_sweep_cap_defers_the_eleventh_course_to_a_later_sweep"
        status: pass
    human_judgment: false
  - id: D3
    description: "Fetch errors, no-heading pages and pages describing a different course are named with reasons in the outcome and IngestRun.error_message and counted in records_failed while the sweep succeeds; failures are negative-cached for 6 hours"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_courses.py#test_failed_courses_are_named_and_the_sweep_still_succeeds"
        status: pass
      - kind: unit
        ref: "tests/sync/test_courses.py#test_failed_course_is_negative_cached_for_six_hours"
        status: pass
    human_judgment: false
  - id: D4
    description: "Dry run never fetches and lists the would-add keys; the default adder singleton is reused across sweeps; a settings file without catalog_url_template fails the sweep as unexpected with no partial writes; the worker import graph stays free of pandas and easy_a.refresh"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_courses.py#test_dry_run_never_fetches_and_lists_the_would_add_keys"
        status: pass
      - kind: unit
        ref: "tests/sync/test_courses.py#test_default_adder_singleton_is_reused_across_sweeps"
        status: pass
      - kind: unit
        ref: "tests/sync/test_courses.py#test_bad_catalog_settings_fail_the_sweep_with_no_partial_writes"
        status: pass
      - kind: command
        ref: "uv run python -c 'import easy_a.sync.courses; assert no pandas / easy_a.refresh'"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live behavior against cloud.usf.edu (real page shapes for the 11 measured missing courses, request politeness) is not exercised: every test uses a fake fetch"
    requirement: REQ-SYNC-01
    verification: []
    human_judgment: true
    rationale: "No live USF request is permitted in tests; the first hosted sweep should be observed to confirm the real catalog pages parse."

duration: 20min
completed: 2026-09-29
---

# Phase 09 Plan 12: Auto-add of new courses Summary

**The sync worker now auto-adds any undergraduate Tampa course it sees but Easy-A lacks, through one paced (2 s), capped (10 per sweep) catalog fetch per course with a 6-hour negative cache, inserting the course and its sections in the same sweep transaction with the honest no-history fallback label and naming every course it could not add.**

## Performance

- **Duration:** about 20 min
- **Started:** 2026-09-29T17:35:00Z (approx.)
- **Completed:** 2026-09-29T17:55:08Z
- **Tasks:** 2
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments
- `easy_a.sync.courses` with `CourseAdder`, `AutoAddResult`, `default_course_adder()` and a tomllib `load_catalog_settings()` that reads only `catalog_edition` and `catalog_url_template` (no pandas import).
- `run_sweep` calls the adder after the gate and before `build_sweep_plan` (never on a dry run), re-resolves course ids for added keys with one select (highest edition), and inserts the new sections in the same transaction; auto-added rankings come out as `subject`/`global` with `effective_n 0`.
- Unapplied courses (fetch failure, no heading, wrong course, cap deferral, negative cache) are reported by name with a reason in `SweepOutcome.unapplied` and `IngestRun.error_message` ("unapplied courses: NEB 0001 (no catalog heading); ..."), truncated to 2,000 characters, and counted in `records_failed`. The CLI log line gained `auto_added` and `unapplied_courses`.
- Nine tests in `tests/sync/test_courses.py`; `tests/sync/conftest.py` now gives the default adder an offline fetch so no existing or future sync test can reach USF.

## Task Commits

1. **Task 1: Tracer, unknown course added in the same sweep with honest fallback** - `cbe3386` (feat)
2. **Task 2: Pacing, cap, negative cache, failure reporting, dry-run** - `ff4b648` (test)

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## Files Created/Modified
- `src/easy_a/sync/courses.py` - CourseAdder, AutoAddResult, CourseAdderLike protocol, catalog settings reader, default singleton
- `src/easy_a/sync/sweep.py` - auto-add wiring, `auto_added`/`unapplied` on SweepOutcome, reason-bearing unapplied message
- `src/easy_a/sync/plan.py` - `new_course_keys` helper
- `src/easy_a/sync/cli.py` - log line fields for auto-added and unapplied courses
- `tests/sync/test_courses.py` - tracer plus pacing, cap, failure, negative cache, dry-run, singleton and settings cases
- `tests/sync/conftest.py` - autouse offline default adder
- `tests/sync/test_dry_run.py` - the dry-run adder is now a recording object with `add_missing` instead of a lambda

## Decisions Made
See `key-decisions` above. `config/course_targets.toml` is unchanged (git diff empty) and no package was added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing sweeps with unknown courses would have fetched live USF pages**
- **Found during:** Task 1 (wiring the default adder)
- **Issue:** Once `run_sweep` falls back to the default adder, existing tests with unknown courses (for example PSY 1012) would make real catalog requests, which the execution rules forbid.
- **Fix:** Autouse fixture in `tests/sync/conftest.py` replaces the singleton with an adder whose fetch raises `httpx.ConnectError`; those tests keep their assertions (course named, rows counted as failed).
- **Files modified:** tests/sync/conftest.py
- **Verification:** full suite passes (673 passed, 4 skipped)
- **Committed in:** cbe3386

**2. [Rule 1 - Bug] Old `CourseAdder = Callable[..., object]` alias and lambda adder in test_dry_run.py**
- **Found during:** Task 1
- **Issue:** The 09-08 placeholder alias clashed by name with the new `CourseAdder` class and could not express `add_missing`.
- **Fix:** Replaced by the `CourseAdderLike` protocol; the dry-run test uses a recording fake.
- **Files modified:** src/easy_a/sync/sweep.py, tests/sync/test_dry_run.py
- **Committed in:** cbe3386

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both necessary for hermetic tests and a clean adder interface. No scope creep.

## Issues Encountered
- `ruff format src` reformatted 15 unrelated pre-existing files (the repo is not fully ruff-format clean). Those changes were reverted with `git checkout` on the exact paths before committing; only files this plan touches were committed.

## Known Stubs

None. (Grade history for auto-added courses is intentionally not imported; it is a deferred idea per CONTEXT and the courses are labelled `subject`/`global` with `effective_n 0`.)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 09-13 to 09-15 can rely on the worker adding new courses on its own; the first hosted sweep should be watched once to confirm real catalog pages parse (D5 in coverage).
- `uv run pytest -q` (673 passed, 4 skipped), `uv run mypy src` and `uv run ruff check .` are clean.

## Self-Check: PASSED

Created files exist (`src/easy_a/sync/courses.py`, `tests/sync/test_courses.py`); commits `cbe3386` and `ff4b648` are on `codex/render-setup`.

---
*Phase: 09-hosted-beta-deployment-ci-observability*
*Completed: 2026-09-29*
