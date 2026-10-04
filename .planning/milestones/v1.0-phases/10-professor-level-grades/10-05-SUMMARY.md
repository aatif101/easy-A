---
phase: 10-professor-level-grades
plan: 05
subsystem: api
tags: [instructor-breakdown, rankings-cache, pydantic, sqlalchemy, parity, d-20, no-migration]

requires:
  - phase: 10-professor-level-grades
    provides: plan 10-01 retuned instructor_course scoring, lab rule and _instructor_course_stats; plan 10-04 TypeScript contract field names
provides:
  - build_instructor_breakdown and the InstructorHistory/InstructorBreakdownResult dataclasses in analytics/queries.py
  - Per-instructor observation grouping in both the per-course and whole-term batch paths, sharing one _instructor_course_stats
  - InstructorHistoryRow and InstructorBreakdown API models; HistoricalAnalyticsSummary.instructor_breakdown (optional, last field)
  - historical_analytics.instructor_breakdown embedded in the cached JSON column and served by /search, /section and /course
affects: [10-06, 10-07, 10-08, 10-09, web]

requirements-completed: [REQ-PROF-01]

status: complete
plan_head_before: bda561cd3bc2dc06cbc17f6ca4046bbf167b6f78
plan_head_after: ee7156fb10801ec9d9d7842df195703cdc5f9116

actuals:
  tokens: 16500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Breakdown embedded in the historical_analytics JSON column: no migration, old cache rows load as null"
    - "One shared _instructor_course_stats feeds both the scoring decision and the displayed rows, so the pinned row and the section score cannot disagree"
    - "Breakdown result memoised per (current instructor, is_lab) within a course, so builder cost is bounded by distinct instructors"
    - "Batch path groups instructor observations from already-loaded rows via the course index: no new statement"

key-files:
  created:
    - tests/rankings/test_instructor_breakdown.py
  modified:
    - src/easy_a/analytics/queries.py
    - src/easy_a/rankings/models.py
    - src/easy_a/rankings/service.py
    - src/easy_a/rankings/cache.py
    - tests/analytics/test_queries.py
    - tests/rankings/test_cache_parity.py
    - tests/rankings/test_cli.py
    - tests/api/test_rankings_api.py

key-decisions:
  - "Transport is embedded, not lazy: the breakdown rides in historical_analytics, so there is no schema change, no deploy-ordering hazard and no loading or error state in the UI."
  - "Collapse cutoff is 15 effective grades (INSTRUCTOR_BREAKDOWN_COLLAPSE_MIN_EFFECTIVE_N); the current instructor is pinned at any n > 0."
  - "Rows are keyed by exact name_raw, the same identity the scoring path already uses, which is what keeps the iff invariant exact."
  - "A current laboratory section reports current_instructor when usable but current_instructor_has_history false and no rows."

patterns-established:
  - "Cache-vs-on-demand parity now includes instructor_breakdown, checked under unweighted and recency configs"
  - "Contract key sets are pinned literally in tests against web/src/types/rankings.ts"

coverage:
  - id: D1
    description: "Breakdown flows from both query paths through the cache to GET /api/v1/rankings/search with the exact contract keys, and /section returns an equal block"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_search_serves_cached_breakdown_that_matches_the_on_demand_endpoint"
        status: pass
      - kind: integration
        ref: "tests/api/test_rankings_api.py#test_search_embeds_instructor_breakdown_with_exact_contract_keys"
        status: pass
    human_judgment: false
  - id: D2
    description: "No instructor claim without course-level history and mapped instructors (D-20): subject, global, no letter grades and pre-backfill all carry null"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_breakdown_is_null_where_an_instructor_claim_is_unsupported"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_instructor_breakdown.py#test_builder_returns_none_for_fallback_empty_and_unmapped_course_stats"
        status: pass
    human_judgment: false
  - id: D3
    description: "Lab, no-history, Staff-current, below-cutoff pin, tie order, per-course name identity and config-driven thresholds behave as D-08..D-14 specify"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_current_laboratory_section_gets_no_rows_and_a_course_level_score"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_staff_current_section_lists_rows_display_only_and_keeps_course_score"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_current_instructor_below_cutoff_is_pinned_and_other_small_instructors_only_counted"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_ties_sort_by_name_and_other_courses_never_leak_into_a_row"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_breakdown_thresholds_follow_the_active_score_config"
        status: pass
    human_judgment: false
  - id: D4
    description: "Consistency invariant: score_source is instructor_course exactly when a scored current row exists on a non-lab section, with equal score and effective_n"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_instructor_breakdown.py#test_section_scores_from_instructor_course_exactly_when_the_pinned_row_is_scored"
        status: pass
    human_judgment: false
  - id: D5
    description: "Batch, per-course and cache paths produce identical breakdowns at bounded statement cost"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/analytics/test_queries.py#test_breakdown_is_identical_in_batch_and_per_course_paths"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_cache_parity.py#test_cached_rankings_match_on_demand_including_instructor_breakdown"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_queries.py#test_term_batch_statement_count_does_not_grow_with_sections"
        status: pass
    human_judgment: false
  - id: D6
    description: "Hosted search p95 and ENC 1101 page size impact of the embedded payload"
    requirement: REQ-PROF-01
    verification: []
    human_judgment: true
    rationale: "Measured against the 1.5 s bar after rollout in plan 10-08; no hosted data exists in tests."

duration: 35min
completed: 2026-10-01
---

# Phase 10 Plan 05: Instructor Breakdown API Summary

**Per-instructor grade history computed in both ranking paths from the same stats helper that scores sections, embedded in the cached historical_analytics JSON (no migration) and served contract-exact by search, section and course, null wherever the evidence does not support an instructor claim.**

## Performance

- **Duration:** about 35 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 1 created, 8 modified (9 in the diff)

## Accomplishments

- `build_instructor_breakdown` in `analytics/queries.py` returns `None` unless the course's own stats are `score_source=course` with `effective_n > 0` and `mapped_instructor_section_count > 0` (D-20), returns `lab_section` with no rows for a current lab (D-13), and otherwise lists every usable instructor at or above 15 effective grades plus the current instructor at any n > 0, sorted current first, effective_n descending, then name. Smaller instructors are only counted in `other_instructor_count`.
- Scoring and display share `_instructor_course_stats`. The per-course path now builds one `{name: observations}` map per call (two statements) and the whole-term path builds it from rows already loaded (no new statement); `_TermGradeEvidence.for_instructor` was replaced by `instructor_observations`, which uses the course index instead of scanning every row.
- API models `InstructorHistoryRow` and `InstructorBreakdown` match the 10-04 TypeScript contract exactly; `HistoricalAnalyticsSummary.instructor_breakdown` is the last, optional field, so legacy cache rows hydrate as null. `_historical_summary` takes the breakdown and `rank_section` and `refresh_section_rankings` both pass it.
- Tracer gate: verify re-run after Task 1 (ruff, mypy, 784 passed, 4 skipped); logged "Tracer verified end-to-end, expanding".
- Final checks: `uv run ruff check .` clean, `uv run mypy src` clean (92 files), `uv run pytest -q` 807 passed, 4 skipped (783 passed before this plan added its 24 tests). No Alembic migration (`git diff --name-only origin/main -- migrations` prints nothing).

## Task Commits

1. **Task 1: Tracer, breakdown through both paths and the cache to /search** - `3a89f34` (feat)
2. **Task 2: Batch, per-course and cache parity on a seven-branch seed** - `eb52fb6` (test)
3. **Task 3: Edge states, D-20 gating, invariant and API contract keys** - `ee7156f` (test)

## Decisions Made

- Embedded transport and cutoff 15, as the plan recorded; plan 10-08 measures hosted p95 and ENC 1101 page bytes.
- Instructor rows are keyed by exact `name_raw` (the scoring identity), not a re-cleaned name, so a whitespace variant cannot make the pinned row and the section score disagree.
- The breakdown is memoised per `(current instructor, is_lab)` within each course in both loops; sections sharing an instructor share one frozen result.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pinned CLI snapshot did not include the new historical_analytics key**
- **Found during:** Task 1 (full-suite run)
- **Issue:** `tests/rankings/test_cli.py::test_rank_section_cli_outputs_synthetic_spring_2027_fixture` compares the full JSON output of `rank_section`; the new `instructor_breakdown` key is a deliberate contract addition, not a regression.
- **Fix:** Extended the expected output with the exact breakdown block for that section (single scored current row, I. Rothstein, a_share 0.6, n 100). No existing line was changed or weakened.
- **Files modified:** `tests/rankings/test_cli.py`
- **Commit:** `3a89f34`

**Total deviations:** 1 auto-fixed (1 bug-in-test-snapshot). **Impact:** none on scope.

### Notes

- Task 2 and Task 3 listed `src/easy_a/analytics/queries.py` as a possible fix target; neither task exposed a parity or edge gap, so it was not modified after Task 1.
- Commits are one per task (test and implementation together), matching how plan 10-01 handled `tdd="true"` tasks, rather than separate RED and GREEN commits.

## Issues Encountered

- `gsd_run` is not defined in this shell, so the `git.base-branch --is-protected` helper was unavailable; HEAD was manually confirmed to be `phase-10-prof-grades` before each commit.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or schema; the breakdown rides existing endpoints. T-10-14 (iff invariant and parity tests), T-10-15 (null tests for subject, global, effective_n 0, mapped 0) and T-10-16 (only rows at or above 15 plus the pinned current instructor are serialized) are mitigated; T-10-SC: no package added.

## Next Phase Readiness

- Hosted breakdowns are null until the instructor backfill (plan 10-06/10-07) populates `section_instructors` for past terms; this is intended pre-backfill behavior.
- Plan 10-08 should record hosted search p95 and the ENC 1101 response size with the embedded payload.
- Deferred non-blocking observation: mypy on `tests/` has pre-existing errors noted in the 10-01 summary; `uv run mypy src` is clean.

## Self-Check: PASSED

- Created file exists: `tests/rankings/test_instructor_breakdown.py`; this SUMMARY.
- Commits `3a89f34`, `eb52fb6`, `ee7156f` exist on `phase-10-prof-grades`; `git rev-list --count bda561c..HEAD` was 3 before this SUMMARY.
- Acceptance greps pass: `def build_instructor_breakdown` (queries.py:88), `instructor_breakdown: InstructorBreakdown | None = None` (models.py:110), `instructor_breakdown=` (cache.py:173); no migration diff.

---
*Phase: 10-professor-level-grades*
*Completed: 2026-10-01*
