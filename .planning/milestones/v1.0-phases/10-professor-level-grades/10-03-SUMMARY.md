---
phase: 10-professor-level-grades
plan: 03
subsystem: analytics
tags: [ranking-diff, d-04-gate, instructor-pairs, join-coverage, read-only, measurement, sqlalchemy, pytest]

requires:
  - phase: 10-professor-level-grades
    provides: plan 10-01 retune and laboratory rule inside get_term_section_historical_analytics (the recomputation this diff reads)
provides:
  - easy_a.rankings.diff (ScoreRow, SCORE_FIELDS, stored_score_rows, computed_score_rows, rank_rows, diff_score_rows, RankingDiff)
  - scripts/report_ranking_diff.py (read-only stored-vs-computed diff CLI, exit 0/1/3)
  - easy_a.analytics.pair_coverage (REFERENCE_2026_09_28, measure_instructor_pairs, PairCoverage)
  - scripts/measure_instructor_pairs.py (read-only pair re-measure CLI, exit 0/1/3)
affects: [10-06, 10-07, 10-08, rankings-cache, instructor-backfill]

plan_head_before: c4f16d7e99c55f2181a70375aa08bf644f4f33c6
plan_head_after: 4fcbc73848e00a7aabafa7f0591ce16b88b3a39a

actuals:
  tokens: 17000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Verdicts derived from the same fields the report prints, so a reported anomaly cannot read PASS (T-10-10)"
    - "Read-only scripts open REPEATABLE READ READ ONLY on PostgreSQL and exit 0/1/3 like inventory_tampa_grades.py"
    - "Independent cross-check: pair_coverage reads grade rows and section instructors directly and does not reuse analytics.queries"

key-files:
  created:
    - src/easy_a/rankings/diff.py
    - scripts/report_ranking_diff.py
    - tests/rankings/test_diff.py
    - src/easy_a/analytics/pair_coverage.py
    - scripts/measure_instructor_pairs.py
    - tests/analytics/test_pair_coverage.py
  modified: []

key-decisions:
  - "Absolute-delta statistics and buckets cover every section present on both sides, with bucket 0 holding the unchanged ones; `changed` and `transitions` count only sections whose score fields differ"
  - "transitions list only sections whose score_source changed, so unchanged course->course rows never appear"
  - "A mapped_instructor_section_count change with no score-field change is informational only; the backfill raises that count on course-level rows without moving any score"
  - "Pair effective_n is min(sum of A-F, sum of total_grades) per pair, recency off, matching the research definition; instructor names are matched on whitespace-collapsed, case-folded text"
  - "PairCoverage carries the reference it was measured against, read from the module at call time, so a test or a re-baselined report can substitute it"

requirements-completed: [REQ-PROF-01]

coverage:
  - id: C1
    description: "Stored section_rankings score fields equal a fresh recomputation after a cache rebuild: identical and course_level_invariant true, script exit 0"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_diff.py#test_stored_and_computed_rows_match_after_refresh"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_diff.py#test_script_exit_0_on_fresh_cache_then_1_after_mutation"
        status: pass
    human_judgment: false
  - id: C2
    description: "Any difference fails: an edited course-level row is named in course_level_violations and exits 1; CRNs on one side only fail both verdicts"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_diff.py#test_editing_a_stored_course_level_row_is_reported"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_crn_present_on_one_side_only_fails_both_verdicts"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_every_score_field_change_is_a_course_level_violation"
        status: pass
    human_judgment: false
  - id: C3
    description: "The diff quantifies changes: source transitions, absolute-delta stats and buckets, rank shift, top changes with before/after rank and effective_n; a course to instructor_course move is a transition and not a violation"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_course_to_instructor_course_move_is_a_transition_not_a_violation"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_abs_delta_stats_and_buckets"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_rank_shift_and_top_changes_ordering"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_ranks_use_easiness_desc_with_course_and_crn_tiebreak"
        status: pass
    human_judgment: false
  - id: C4
    description: "A mapped-instructor-count change alone is informational and does not make the diff non-identical"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_mapped_count_change_alone_is_informational"
        status: pass
    human_judgment: false
  - id: C5
    description: "Diff script is read-only, emits no URL, exits 3 NOT MEASURED when the database errors, and lists --term, --top, --report-json"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/rankings/test_diff.py#test_script_never_writes"
        status: pass
      - kind: integration
        ref: "tests/rankings/test_diff.py#test_script_exit_3_when_database_unreachable"
        status: pass
      - kind: unit
        ref: "tests/rankings/test_diff.py#test_script_help_lists_options"
        status: pass
    human_judgment: false
  - id: C6
    description: "Pair re-measure reproduces the seeded behavior table: Staff and blank excluded, per-course pair key, min(A-F, total) rule, before-term cutoff, term-span and section-type histograms, grade-row accounting"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_seeded_example_matches_the_behavior_table"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_same_name_in_two_courses_is_two_pairs_one_instructor"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_effective_n_is_min_of_letter_grades_and_total"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_rows_of_terms_at_or_after_before_term_are_excluded"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_blank_and_staff_names_are_excluded_case_insensitively"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_section_type_histogram_counts_grade_rows_with_a_section"
        status: pass
    human_judgment: false
  - id: C7
    description: "matches_reference requires pairs, n>=60, n>=30 and n>=15 to equal the 2026-09-28 report; deltas are measured minus reference for every reference key; exit 0 only on a match, 1 otherwise, 3 NOT MEASURED"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/analytics/test_pair_coverage.py#test_matches_reference_requires_four_headline_numbers"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_script_exit_0_when_numbers_match_a_patched_reference"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_script_exit_1_when_the_database_differs_from_the_report"
        status: pass
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_script_exit_3_when_database_unreachable"
        status: pass
    human_judgment: false
  - id: C8
    description: "Pair tool output carries no instructor names and no URL (T-10-08, D-19)"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/analytics/test_pair_coverage.py#test_script_exit_1_when_the_database_differs_from_the_report"
        status: pass
    human_judgment: false
  - id: C9
    description: "Neither tool was run against hosted Supabase in this plan; the real before/after diff and the real join re-measure are produced by plans 10-07 and 10-08"
    requirement: REQ-PROF-01
    human_judgment: true
    rationale: "Real-data verdicts (whether 3,216 pairs reproduce, which sections move) can only be observed against the hosted database; tests use small seeded SQLite data"

duration: ~12 min
completed: 2026-10-01
status: complete
---

# Phase 10 Plan 03: Ranking Diff and Instructor-Pair Re-measure Summary

**Two read-only measurement tools gate Phase 10: a D-04 stored-versus-recomputed ranking diff (exit 0 only when every section is identical) and a re-measure of the historical (instructor, course) join compared number for number with the 2026-09-28 report.**

## Performance

- **Duration:** ~12 min (start time was not captured; estimate)
- **Completed:** 2026-10-01
- **Tasks:** 2
- **Files:** 6 (all created)

## Accomplishments

- `src/easy_a/rankings/diff.py`: `stored_score_rows` reads the cache score columns plus `mapped_instructor_section_count` from the stored `historical_analytics`; `computed_score_rows` selects active sections the way `refresh_section_rankings` does and calls `get_term_section_historical_analytics`; `diff_score_rows` returns a frozen `RankingDiff` with changed count, transitions, absolute-delta stats (max, mean, median, p90) and buckets, rank-shift stats, top changes, `course_level_violations`, informational changes, and the `identical` and `course_level_invariant` verdicts.
- `scripts/report_ranking_diff.py`: `--term` (required), `--top`, `--report-json` (full per-CRN changes); one JSON object with a `verdicts` block; exit 0 identical, 1 any difference, 3 NOT MEASURED; REPEATABLE READ READ ONLY on PostgreSQL; never prints the URL.
- `src/easy_a/analytics/pair_coverage.py`: `REFERENCE_2026_09_28` with the report numbers, and `measure_instructor_pairs`, an independent two-query measurement (grade rows outer-joined to Section and Course, then section instructor names) that does not reuse the scoring code.
- `scripts/measure_instructor_pairs.py`: `--before-term` (default 202701) and `--report-json`; same read-only session and exit-code pattern.
- 41 new tests (24 diff, 17 pair coverage). Full suite 783 passed, 4 skipped (baseline 742 passed); `ruff check .` and `mypy src` clean.

## Task Commits

1. **Task 1 (tracer): stored-vs-computed ranking diff from the cache table to a JSON verdict** - `a97e885` (feat)
2. **Task 2: historical instructor-pair re-measure against the 2026-09-28 report** - `4fcbc73` (feat)

Tracer gate: the tracer `<verify>` (pytest on `tests/rankings/test_diff.py`, `ruff check .`, `mypy src`) was re-run end to end after the commit and passed before the expansion task.

## Files Created/Modified

- `src/easy_a/rankings/diff.py` - score rows, rank computation, diff and verdict logic
- `scripts/report_ranking_diff.py` - read-only diff CLI
- `tests/rankings/test_diff.py` - unit tests per behavior, end-to-end tests over a file-backed SQLite engine
- `src/easy_a/analytics/pair_coverage.py` - reference numbers and the independent pair measurement
- `scripts/measure_instructor_pairs.py` - read-only pair re-measure CLI
- `tests/analytics/test_pair_coverage.py` - seeded-history tests and script exit-code tests

## Decisions Made

- Delta statistics and buckets span every section present on both sides (bucket `0` holds unchanged sections), while `changed`, `transitions` and `top_changes` cover only sections whose score fields differ.
- `transitions` counts only real `score_source` changes; a section that is `course` on both sides never appears there.
- A change confined to `mapped_instructor_section_count` is informational: the backfill raises that count on course-level rows without moving any score, so it must not fail the D-04 gate.
- A pair's `effective_n` is `min(sum of A-F, sum of total_grades)` with recency off, as the research defined it. Instructor names are matched after whitespace collapse and case folding, the same cleaning `get_current_instructor_states` applies.
- `PairCoverage` stores the reference it was compared with, read from the module at measurement time, so a test or a later re-baseline can replace it.

## Deviations from Plan

None - plan executed exactly as written.

Notes (not deviations): the plan's pair tool compares with the report using `pairs`, `n_ge_60`, `n_ge_30` and `n_ge_15` as the match gate; the other reference numbers (instructors, courses, multi-term pairs, grade-row totals, term span) appear as deltas only, per the behavior block. One test expectation (the median in the bucket test) was wrong on first run and corrected to 0.275; the code was right.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. Both tools read only, open no new network surface, and emit CRNs, course keys and counts. T-10-08 (no names, no URLs), T-10-09 (read-only transactions, no writes; `test_script_never_writes` in both files) and T-10-10 (verdicts derived from the reported fields) are mitigated as planned.

## Next Phase Readiness

Plan 10-06 can embed both tools in the backfill's dry run, and plans 10-07 and 10-08 can run them against hosted Supabase. The first real signal is 10-07's pair re-measure against 3,216 pairs; until then no real-data claim is made.

## Self-Check: PASSED

- Created files exist: all six listed under key-files.created.
- Commits exist: `a97e885`, `4fcbc73` (`git log` shows both on `phase-10-prof-grades`).
- Acceptance criteria: `grep` for `def diff_score_rows`, `course_level_violations` and `REFERENCE_2026_09_28` match; the file contains 3216, 1329, 2178 and 2829; both scripts' `--help` exit 0 and list their flags.
- Plan verification: `uv run pytest -q -x` 783 passed, 4 skipped; `uv run ruff check .` and `uv run mypy src` clean.
