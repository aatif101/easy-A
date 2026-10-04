---
phase: 04-mvp1-p1-grade-course-attribution-fix
plan: 01
subsystem: database
tags: [sqlalchemy, grade-ingest, canonical-course-attribution, rankings-cache, fastapi]

# Dependency graph
requires: []
provides:
  - "GradeDistribution.course_id populated on insert and update via existing resolve_course_id()"
  - "GradeCourseResolutionError: atomic preflight that fails the whole workbook and reports every unresolved (subject, course_number) key before any GradeDistribution mutation"
  - "Same-key re-import repairs a null course_id in place without creating a duplicate row"
  - "Vertical proof that a historical grade row with no matching historical Section reaches 202701 cache-backed search as real course evidence (effective_n > 0, score_source=course), alongside an honest no-history control (effective_n = 0, score_source=global)"
affects: [04-02-blank-grade-cell-and-quality-guard]

# Actuals (#2632)
actuals:
  tokens: 5465
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Preflight-before-mutation: resolve every distinct parsed course key via resolve_course_id() before entering the term/CRN/source upsert loop; collect and report all unresolved keys in one deterministic error"
    - "Thread the resolved course_id through insert/apply/diff helpers so a same-key re-import backfills a previously-null attribution instead of leaving it stale"

key-files:
  created:
    - tests/test_grade_course_attribution.py
  modified:
    - src/easy_a/grades/ingest.py
    - tests/grades/test_ingest.py

key-decisions:
  - "Reused the existing common/lookups.resolve_course_id() rather than adding a grade-specific matcher, preserving identical normalization/catalog-edition selection across schedule, syllabus, and grade ingestion."
  - "records_failed on GradeCourseResolutionError counts ROWS whose course key is unresolved (not distinct unresolved keys), matching the plan's phrasing and the existing IngestRun.records_failed semantics used by GradeWorkbookValidationError."
  - "Did not add course_id to the (term_id, crn, source) unique identity; course attribution remains a mutable property of an already-identified row, per D-04."

patterns-established:
  - "Grade-domain preflight error pattern: GradeCourseResolutionError carries unresolved_keys (sorted, deterministic) and records_failed, caught in ingest_grade_file() alongside the existing GradeWorkbookValidationError handling to mark the IngestRun failed before any grade mutation."

requirements-completed: [REQ-GRADES-01]

coverage:
  - id: D1
    description: "Historical grade rows attach directly to their canonical Course.id on insert and update, without relying on a matching historical Section."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/grades/test_ingest.py#test_grade_ingest_assigns_canonical_course_id"
        status: pass
      - kind: integration
        ref: "tests/test_grade_course_attribution.py#test_generated_xlsx_attribution_reaches_cached_search_without_historical_section"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unresolved course keys fail the whole workbook atomically before any GradeDistribution mutation, reporting every unresolved (subject, number) key deterministically."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/grades/test_ingest.py#test_missing_courses_fail_atomically_and_report_all_keys"
        status: pass
    human_judgment: false
  - id: D3
    description: "Same term/CRN/source re-import repairs a null course_id in place (one row, one update, no duplicate), preserving source and source_hash provenance."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/grades/test_ingest.py#test_same_key_reimport_backfills_null_course_id_without_duplicate"
        status: pass
      - kind: unit
        ref: "tests/grades/test_ingest.py#test_duplicate_grade_ingestion_is_idempotent"
        status: pass
    human_judgment: false
  - id: D4
    description: "After rebuilding the 202701 rankings cache, cache-backed search reports effective_n > 0 / score_source=course for the section with imported history and effective_n = 0 / score_source=global for an otherwise valid no-history control — never presenting the global fallback as course history."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: integration
        ref: "tests/test_grade_course_attribution.py#test_generated_xlsx_attribution_reaches_cached_search_without_historical_section"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-21
status: complete
---

# Phase 04 Plan 01: Grade-Course Attribution Fix Summary

**Grade ingestion now resolves and persists `GradeDistribution.course_id` via the shared `resolve_course_id()` lookup, with an atomic all-keys preflight and null-row repair on re-import, proven end-to-end from a generated historical XLSX through a rebuilt 202701 rankings cache to `GET /api/v1/rankings/search`.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-21 (session start)
- **Completed:** 2026-09-21T07:19:20Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified) plus a deferred-items log

## Accomplishments

- Fixed the blocking attribution seam: `GradeDistribution.course_id` was hard-coded `None` at ingest (`src/easy_a/grades/ingest.py:139` before this plan); it is now resolved via the existing canonical `resolve_course_id()` lookup and threaded through insert, update, and diff.
- Added a deterministic, atomic preflight: `GradeCourseResolutionError` collects every distinct unresolved `(subject, course_number)` key across the whole workbook before any `GradeDistribution` row is touched, and `ingest_grade_file()` marks the `IngestRun` failed with the exact unresolved keys and affected row count.
- Made re-import self-healing: a same `(term_id, crn, source)` re-import now repairs a previously null `course_id` in place, reporting exactly one update and leaving exactly one row — no duplicate, no stale attribution.
- Proved the full vertical path with a new generated-XLSX integration test (`tests/test_grade_course_attribution.py`): a Fall 2024 grade row with **no** matching historical `Section` attaches directly to its canonical course, and after `refresh_section_rankings(session, term="202701")`, `rank_section()`, the `SectionRankingCache` row, `hydrate_ranking()`, and `GET /api/v1/rankings/search` all agree the section has `effective_n > 0` / `score_source == "course"`, while a no-history control section stays an explicit `effective_n == 0` / `score_source == "global"` (D-06, D-07, D-20).
- Strengthened `tests/grades/test_ingest.py` with canonical-attribution, null-row-backfill, and mixed-known/unknown-atomicity regression coverage, seeding the local fixture with the canonical `Course` row the new preflight requires.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end direct attribution — generated historical XLSX to 202701 cached search** - `3a7d3fc` (feat)
2. **Task 2: Harden attribution preflight, null-row repair, deduplication, and provenance** - `24999f8` (test)

**Plan metadata:** commit created below (docs: complete plan)

_Note: Task 1 is `tdd="true"` and `type="tracer"`; the test was written and run to confirm RED (grade.course_id asserted None) before the production fix, then re-run to confirm GREEN — both within the same task commit per the plan's TDD/tracer contract. Task 2's new tests passed on first run against Task 1's implementation with no further production refinement needed._

## Files Created/Modified

- `src/easy_a/grades/ingest.py` - Added `GradeCourseResolutionError` and `_resolve_grade_course_ids()`; `upsert_grade_distributions()` preflights all distinct course keys before the mutation loop; `_new_grade_distribution()`, `_apply_grade_distribution()`, and `_grade_distribution_differs()` now take and propagate `course_id`.
- `tests/test_grade_course_attribution.py` (new) - Generated-XLSX vertical proof: parser → preflighted ingest → analytics → 202701 cache rebuild → `GET /api/v1/rankings/search`, with an explicit no-history control.
- `tests/grades/test_ingest.py` - Seeded canonical `Course` in the local fixture; strengthened idempotency assertions; added canonical-attribution, null-row-backfill, and atomic-failure-with-all-keys-reported tests.
- `.planning/phases/04-mvp1-p1-grade-course-attribution-fix/deferred-items.md` (new) - Logged a pre-existing, unrelated strict-mypy finding in `tests/test_database_config.py` (out of scope for this plan).

## Decisions Made

- Reused `resolve_course_id()` unchanged rather than adding a grade-specific course matcher, so grade, schedule, and syllabus ingestion share identical subject/number normalization and catalog-edition selection.
- `GradeCourseResolutionError.records_failed` counts affected rows (not distinct unresolved keys), matching the plan's "number of rows whose course key is unresolved" phrasing and the existing `IngestRun.records_failed` convention used elsewhere in this file.
- Kept `(term_id, crn, source)` as the sole database identity; `course_id` is treated purely as an attributed, mutable property of an already-identified row (D-04) — no migration, no new unique-constraint dimension.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a ruff line-length violation in the new exception docstring**
- **Found during:** Task 1 (post-implementation `ruff check`)
- **Issue:** The `GradeCourseResolutionError` docstring exceeded the 100-character line limit.
- **Fix:** Rewrapped the docstring across four lines.
- **Files modified:** `src/easy_a/grades/ingest.py`
- **Verification:** `uv run ruff check src/easy_a/grades/ingest.py tests/test_grade_course_attribution.py` — all checks passed.
- **Committed in:** `3a7d3fc` (Task 1 commit)

**2. [Rule 1 - Bug] Narrowed `IngestRun.error_message` (`str | None`) before substring assertions**
- **Found during:** Task 2 (post-implementation `mypy`)
- **Issue:** `"PSY 2012" in ingest_run.error_message` failed strict mypy because `error_message` is `str | None`.
- **Fix:** Added `assert ingest_run.error_message is not None` before the substring checks.
- **Files modified:** `tests/grades/test_ingest.py`
- **Verification:** `uv run mypy tests/grades/test_ingest.py` — no issues found.
- **Committed in:** `24999f8` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — lint/type correctness in newly-written code, no behavior change).
**Impact on plan:** No scope creep; both fixes are mechanical correctness of code introduced in this plan.

## Issues Encountered

- Discovered a pre-existing, unrelated strict-mypy failure in `tests/test_database_config.py` while running the full `uv run mypy src migrations scripts tests` gate. Confirmed via `git diff`/`git log` that the file is untouched by this plan (last touched at commit `106a06d`, unrelated to Phase 04) and not in `04-01-PLAN.md`'s `files_modified`. Logged to `deferred-items.md` per the scope-boundary rule rather than fixed here. Ruff and the full pytest suite (`uv run pytest -q`, 257 passed / 3 skipped, up from the research baseline of 253 passed / 3 skipped) are unaffected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `GradeDistribution.course_id` is now populated on every new and repaired grade import; MVP1-P2 (grade data sourcing) can import real USF InfoCenter exports and expect them to attach to current-term sections without any historical `Section` dependency.
- The `unattributed_grade_row` quality-finding guard and the blank-canonical-count fail-closed policy remain scoped to `04-02` (not touched here); existing null-attributed rows in any live database still need a same-key re-import (or an explicit audited repair) to backfill `course_id` before MVP1-P2/P3 broaden coverage.
- Full pytest suite green (257 passed / 3 skipped), ruff clean on all changed files, strict mypy clean on all changed files. No raw or synthetic `.xlsx`/`.xls` file is tracked in Git (`git ls-files` verified empty for that pattern).

## Self-Check: PASSED

- `src/easy_a/grades/ingest.py` — FOUND
- `tests/test_grade_course_attribution.py` — FOUND
- `tests/grades/test_ingest.py` — FOUND
- `.planning/phases/04-mvp1-p1-grade-course-attribution-fix/deferred-items.md` — FOUND
- Commit `3a7d3fc` — FOUND in `git log --oneline --all`
- Commit `24999f8` — FOUND in `git log --oneline --all`

---
*Phase: 04-mvp1-p1-grade-course-attribution-fix*
*Completed: 2026-09-21*
