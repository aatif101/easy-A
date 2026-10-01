---
phase: 10-professor-level-grades
plan: 01
subsystem: analytics
tags: [scoring, bayesian-shrinkage, instructor-course, laboratory-rule, sqlalchemy, pytest]

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: live sync worker and removed_at filtering on current-term consumers
provides:
  - ScoreConfig.instructor_prior_strength (30.0) and instructor_course_min_effective_n 30.0 (D-24)
  - Per-source grade prior strength in compute_historical_outcome_stats
  - easy_a.common.section_types, the single home of the Laboratory rule (D-13)
  - Lab-aware instructor evidence in the per-course and whole-term batch query paths
  - D-24 recorded as approved in PROJECT.md and methodology in README
affects: [10-02, 10-07, rankings-cache, instructor-backfill]

plan_head_before: f5d7e90ebe9e1475f984d48102ecb920ac89501f
plan_head_after: 31694b9353dd41d5e7082d313d54c2bb15467735

actuals:
  tokens: 10973
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Per-ScoreSource shrinkage strength chosen inside compute_historical_outcome_stats"
    - "Section-type rules live in easy_a.common.section_types, imported by analytics"
    - "Lab flag carried on _EvidenceRow so the batch path adds no statements"

key-files:
  created:
    - src/easy_a/common/section_types.py
    - tests/analytics/test_instructor_retune.py
  modified:
    - src/easy_a/analytics/scoring.py
    - src/easy_a/analytics/queries.py
    - tests/analytics/test_queries.py
    - README.md
    - .planning/PROJECT.md

key-decisions:
  - "instructor_prior_strength applies to grade favorability only; withdrawal shrinkage stays at withdrawal_prior_strength 60 for every level (literal reading of D-24)."
  - "Laboratory matching is exact on the normalized value 'laboratory'; combined types and unknown types are not treated as labs. Vocabulary is confirmed against hosted data in plan 10-07."
  - "The single-term flag is label-only: term_count differs, easiness_score does not (D-02)."

patterns-established:
  - "Retune reproducibility: ScoreConfig(instructor_course_min_effective_n=60, instructor_prior_strength=60) reproduces the D-02 baseline, proven by test"
  - "Exact float equality over every non-instructor cache row under the new and baseline configs"

requirements-completed: [REQ-PROF-01]

coverage:
  - id: D1
    description: "Retuned instructor_course score (gate 30, instructor prior 30 for grades, withdrawal 60) flows from ScoreConfig through the refresh_section_rankings cache rebuild"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/analytics/test_instructor_retune.py#test_retuned_instructor_course_score_flows_through_cache_rebuild"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_instructor_retune.py#test_instructor_course_source_smooths_grades_with_instructor_prior_strength"
        status: pass
    human_judgment: false
  - id: D2
    description: "Course, subject and global stats are byte-identical under the new defaults and the 60/60 baseline config"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/analytics/test_instructor_retune.py#test_retuned_instructor_course_score_flows_through_cache_rebuild"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_instructor_retune.py#test_non_instructor_sources_keep_grade_prior_strength_60"
        status: pass
    human_judgment: false
  - id: D3
    description: "Laboratory sections never feed instructor-level stats and current lab sections score from course history, in both query paths, while course-level history keeps lab grades"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/analytics/test_queries.py#test_lab_only_history_gives_instructor_no_instructor_course_stats"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_queries.py#test_current_lab_section_is_scored_from_course_history_in_both_paths"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_queries.py#test_term_batch_matches_per_course_analytics_exactly"
        status: pass
    human_judgment: false
  - id: D4
    description: "Single-term label-only (D-02), Staff never matched (D-08) and per-course name identity (D-14) hold"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/analytics/test_instructor_retune.py#test_single_term_flag_is_label_only_and_adds_no_shrinkage"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_instructor_retune.py#test_staff_sections_feed_course_history_but_never_an_instructor"
        status: pass
      - kind: unit
        ref: "tests/analytics/test_instructor_retune.py#test_instructor_name_is_matched_within_one_course_never_pooled"
        status: pass
    human_judgment: false
  - id: D5
    description: "PROJECT.md D-24 approved 2026-09-30 with D-02 amendment note and Key Decisions row; README documents the methodology"
    requirement: REQ-PROF-01
    verification:
      - kind: other
        ref: "grep -q 'D-24 [locked, approved 2026-09-30]' .planning/PROJECT.md && grep -q instructor_prior_strength README.md"
        status: pass
    human_judgment: true
    rationale: "Wording accuracy of the methodology prose and the recorded approval is a judgment call no test asserts."

duration: 25min
completed: 2026-10-01
status: complete
---

# Phase 10 Plan 01: Instructor-course scoring retune and laboratory rule Summary

**D-24 instructor-course retune (gate 30, instructor grade prior 30, withdrawal prior unchanged at 60) plus the D-13 Laboratory exclusion in both instructor query paths, with exact-equality proof that course, subject and global scores are unchanged**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-01
- **Tasks:** 3
- **Files modified:** 7 (2 created)

## Accomplishments
- `ScoreConfig` gains `instructor_prior_strength` (30.0) and `instructor_course_min_effective_n` drops to 30.0. `compute_historical_outcome_stats` picks the grade prior strength per `ScoreSource`; withdrawal smoothing is untouched at 60 for all sources. No other constant changed.
- The retuned `instructor_course` score is proven end to end through `refresh_section_rankings` reading `SectionRankingCache` rows. Under `ScoreConfig(instructor_course_min_effective_n=60.0, instructor_prior_strength=60.0)` the same section scores from course history, and every non-instructor cache row is equal under both configs with exact float equality.
- `easy_a.common.section_types` is the single home of the Laboratory rule. `_instructor_section_ids` and `_TermGradeEvidence.for_instructor` drop lab rows, and both current-section loops score lab sections from course history. `Section.section_type` was added to the existing `_TermGradeEvidence.load` select, so statement counts did not grow. Course-level aggregation still includes lab grades.
- D-02 (single-term is label only), D-08 (Staff never matched, still feeds course history) and D-14 (name matched within one course, never pooled) are covered by tests. The term-batch parity test now runs over a seed containing lab sections and still passes with the statement-count tests unchanged.
- PROJECT.md D-24 reads approved 2026-09-30, D-02 carries the amendment note, the Key Decisions table has the D-24 row. README has an "Instructor-course history" subsection.

## Task Commits

1. **Task 1: Tracer, retuned score through the cache rebuild** - `b83e54a` (feat)
2. **Task 2: Laboratory rule in both query paths plus D-02/D-08/D-14 tests** - `f433d79` (feat)
3. **Task 3: D-24 approval and methodology docs** - `31694b9` (docs)

**Plan metadata:** the SUMMARY commit follows this file.

Tracer gate: verify re-run after Task 1 (5 passed, full suite 711 passed, 4 skipped), logged "Tracer verified end-to-end, expanding".

## Files Created/Modified
- `src/easy_a/analytics/scoring.py` - `DEFAULT_INSTRUCTOR_PRIOR_STRENGTH`, `instructor_prior_strength`, gate 30, per-source grade prior strength
- `src/easy_a/common/section_types.py` - `LABORATORY_SECTION_TYPES`, `normalize_section_type`, `is_laboratory_section_type`
- `src/easy_a/analytics/queries.py` - lab exclusion in `_instructor_section_ids`, `_TermGradeEvidence` (`section_is_lab`) and both current-section loops
- `tests/analytics/test_instructor_retune.py` - end-to-end retune, per-source strength, lab vocabulary, D-02/D-08/D-14
- `tests/analytics/test_queries.py` - `_add_section(section_type=...)`, lab tests for both paths, lab sections in the parity seed
- `README.md`, `.planning/PROJECT.md` - methodology and approval record

## Decisions Made
- Instructor prior strength applies to grade favorability only (plan's resolved open item), withdrawal stays 60 at every level.
- Exact-set lab matching on the normalized value; vocabulary to be confirmed against hosted data in plan 10-07.
- PROJECT.md D-24 text cross-references "Phase 10 D-08/D-13/D-14" explicitly to avoid confusion with the same-numbered PROJECT.md decisions.

## Deviations from Plan

None - plan executed exactly as written. The tracer expansion gate passed on its automated verify.

## Issues Encountered
- `gsd_run` was not defined in the bash environment, so the `git.base-branch --is-protected` check returned unavailable; the fallback was a manual check that HEAD is `phase-10-prof-grades`, not a protected name. State updates used the resolver block from `gsd-run-resolver.md`.
- Existing mypy errors in `tests/analytics/test_queries.py` (lines 505 and 584 area, `list` type-arg and an untyped helper) are pre-existing and out of scope; `uv run mypy src` is clean.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or schema surface; mitigations T-10-01 (invariance test) and T-10-02 (documented methodology) are in place.

## Next Phase Readiness
- Scoring and lab rules exist before any backfill makes `instructor_course` reachable in production.
- Plan 10-07 must confirm the `laboratory` vocabulary against hosted data and run the stored-versus-recomputed course-level proof.
- Final checks: `uv run pytest -q` 720 passed, 4 skipped (baseline 706); `uv run ruff check .` and `uv run mypy src` clean.

## Self-Check: PASSED

- Created files exist: `src/easy_a/common/section_types.py`, `tests/analytics/test_instructor_retune.py`, this SUMMARY.
- Commits `b83e54a`, `f433d79`, `31694b9` exist on `phase-10-prof-grades`; `git rev-list --count f5d7e90..HEAD` was 3 before this SUMMARY.
- All task acceptance criteria and plan-level verification commands re-run and passed.

---
*Phase: 10-professor-level-grades*
*Completed: 2026-10-01*
