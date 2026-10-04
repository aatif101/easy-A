---
phase: 10-professor-level-grades
plan: 06
subsystem: schedule
tags: [backfill, d-04-gate, what-if, sweep-lock, rollback, rebuild-only, runbook, sqlalchemy, pytest]

requires:
  - phase: 10-professor-level-grades
    provides: plan 10-02 backfill CLI and write path; plan 10-03 ranking diff and instructor-pair re-measure
provides:
  - "--dry-run what-if (code-only parity, ranking diff, pairs re-measure) inside an always-rolled-back transaction"
  - "--apply with required --rebuild-term, sweep lock first, same-transaction cache rebuild and a verdict-gated commit (--expect-inserted, course-level invariant)"
  - "--rollback [--yes] and --rebuild-only undo modes (no USF request, sweep lock first)"
  - "select_rollback_sections and delete_backfilled_sections in easy_a.schedule.backfill"
  - "docs/runbooks/historical-instructor-backfill.md and section 14 in hosted-beta-operations.md"
affects: [10-07, 10-08, instructor-backfill, rankings-cache]

plan_head_before: e3030a73a948b5f18d829e5faa2f986914b03f93
plan_head_after: 4a6bf9472535c31d4ac1809465f6601a71e336ba

actuals:
  tokens: 15960
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "The what-if reuses the real write path inside a transaction that is always rolled back, so the reviewed numbers come from the code that will commit"
    - "One transaction owns lock, write, cache rebuild and diff; a failed gate rolls the whole thing back"
    - "Undo modes report the same applied diff but are ungated (applied.gated false), so a diff verdict can never block an undo"
    - "Child-first chunked Core deletes (instructors, cache rows, then sections) behave the same where ON DELETE CASCADE is and is not enforced"

key-files:
  created:
    - tests/schedule/test_backfill_cli.py
    - docs/runbooks/historical-instructor-backfill.md
  modified:
    - src/easy_a/schedule/backfill_cli.py
    - src/easy_a/schedule/backfill.py
    - tests/schedule/test_backfill.py
    - docs/runbooks/hosted-beta-operations.md

key-decisions:
  - "Undo modes (--rollback --yes, --rebuild-only) report the stored-before versus stored-after diff and its verdict but never gate on it (applied.gated false): blocking an undo because a diff looks odd is worse than the odd diff. Only --apply gates (course-level invariant, --expect-inserted)."
  - "--rollback without --yes does the real deletion and cache rebuild inside a transaction it always rolls back, so the preview counts and the applied diff are exactly what --yes would commit; it also takes the sweep lock."
  - "A rollback-eligible section needs at least one instructor row and only backfill-sourced rows, so a section with no instructor rows (not provably ours) is kept."
  - "delete_backfilled_sections restricts the section delete to the five historical terms, so even a live-term id handed to it deletes nothing."
  - "--rebuild-term and --what-if-term share one validator: six digits and not a historical backfill term."
  - "The pairs verdict is reported, never an exit-code gate; the runbook makes an unexplained pairs delta a human blocker in the D-04 review."

requirements-completed: [REQ-PROF-01]

coverage:
  - id: C1
    description: "A dry run reports the full D-04 what-if from the real write path (code-only parity, ranking diff with the course->instructor_course transition, pairs re-measure, three verdicts) and leaves table counts and stored scores identical"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_tracer_dry_run_reports_the_full_what_if_and_commits_nothing"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_report_json_carries_the_per_section_changes_list"
        status: pass
    human_judgment: false
  - id: C2
    description: "A tampered stored cache row fails code-only parity and exits 1; --what-if-term must be a live six-digit term"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_a_tampered_stored_cache_row_fails_code_only_parity"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_what_if_term_must_be_a_live_six_digit_term"
        status: pass
    human_judgment: false
  - id: C3
    description: "Apply requires --rebuild-term, takes the sweep lock before any statement, commits the backfill and the rebuilt cache row (score_source instructor_course) in one transaction, and reports the applied diff"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_apply_commits_the_backfill_and_the_rebuilt_cache_together"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_apply_takes_the_sweep_lock_before_any_statement"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_apply_without_rebuild_term_is_a_usage_error_and_makes_no_request"
        status: pass
    human_judgment: false
  - id: C4
    description: "Apply refuses safely: busy lock exits 2 with nothing written; --expect-inserted mismatch and a course-level violation roll back with exit 1 and the JSON names the counts; a failed guard writes nothing"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_busy_sweep_lock_exits_2_with_nothing_written"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_expect_inserted_mismatch_rolls_back_and_names_both_counts"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_a_course_level_violation_rolls_the_apply_back"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_a_failed_guard_in_apply_takes_no_lock_and_writes_nothing"
        status: pass
    human_judgment: false
  - id: C5
    description: "Rollback previews by default and writes nothing; --yes deletes exactly the backfilled sections and restores pre-apply counts (except ingest_runs) and course-level scores"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_rollback_without_yes_previews_and_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_rollback_yes_restores_the_pre_apply_state_except_the_ingest_run"
        status: pass
    human_judgment: false
  - id: C6
    description: "Historical sections with a seat snapshot, a syllabus link, a non-backfill instructor row or no instructor row are ineligible and kept; live-term sections are never eligible or deletable"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_a_historical_section_with_other_data_is_ineligible_and_kept"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_live_term_sections_are_never_eligible"
        status: pass
    human_judgment: false
  - id: C7
    description: "--rebuild-only rebuilds a stale cache with no request and no data write; busy lock stops rollback and rebuild-only with exit 2; modes are mutually exclusive and undo modes need --rebuild-term"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_rebuild_only_rebuilds_the_cache_with_no_request_and_no_data_write"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_busy_sweep_lock_stops_rollback_and_rebuild_only"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_modes_are_mutually_exclusive"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill_cli.py#test_undo_modes_need_rebuild_term_and_yes_needs_rollback"
        status: pass
    human_judgment: false
  - id: C8
    description: "The runbook has the six required headings, documents --expect-inserted, the exit codes and the rollback, and hosted-beta-operations.md links it from section 14"
    requirement: REQ-PROF-01
    verification:
      - kind: command
        ref: "grep -qF for each of the six runbook headings in docs/runbooks/historical-instructor-backfill.md, then grep -q historical-instructor-backfill.md docs/runbooks/hosted-beta-operations.md"
        status: pass
    human_judgment: false
  - id: C9
    description: "Nothing here was run against hosted Supabase or live USF; the PostgreSQL behavior of the advisory lock and of the child-first deletes, the real what-if numbers and the D-04 review belong to plans 10-07 and 10-08"
    requirement: REQ-PROF-01
    human_judgment: true
    rationale: "Tests run on SQLite, where try_sweep_lock is a no-op returning True and ON DELETE CASCADE is not enforced; the real diff, the real pairs verdict and the owner's go/no-go can only be observed against the hosted database"

duration: ~10 min
completed: 2026-10-01
status: complete
---

# Phase 10 Plan 06: Backfill Rollout Instrument Summary

**The backfill CLI is now the D-04 rollout instrument: a dry run shows the stored-versus-after ranking diff and the join re-measure from the real write path with nothing committed, an apply goes live atomically under the sweep lock behind an `--expect-inserted` and course-level-invariant gate, and `--rollback` and `--rebuild-only` undo the data and the scoring change.**

## Performance

- **Duration:** ~10 min (the shell did not capture a start time; derived from commit timestamps 02:17 to 02:26 local)
- **Completed:** 2026-10-01
- **Tasks:** 3
- **Files:** 6 (2 created, 4 modified)

## Accomplishments

- `--dry-run`: before any backfill write it reads the stored cache and the new code's recomputation for `--what-if-term` (default `202701`), writes the backfill, recomputes, measures the instructor pairs and rolls back. `what_if` carries `code_only_parity`, `ranking_diff`, `pairs` and `verdicts` (`code_only_parity`, `course_level_invariant`, `pairs_match_reference`). Exit 0 needs no guard failure, identical code-only parity and the course-level invariant; the pairs verdict never changes the exit code. `--report-json` adds the per-section `changes` lists.
- `--apply` needs `--rebuild-term`. One transaction: `try_sweep_lock` (exit 2, nothing written, when busy), read stored cache, write backfill and `IngestRun` rows, `refresh_section_rankings`, diff stored before/after, then commit only when the course-level invariant holds and any `--expect-inserted N` matches; otherwise roll back and exit 1. The `applied` object reports the diff, `verdicts`, `gate_failures` and the expected/actual counts.
- `--rollback` (preview by default, `--yes` commits) and `--rebuild-only`: no USF request, sweep lock first, cache rebuild, `applied` diff. `select_rollback_sections` and `delete_backfilled_sections` in `backfill.py` pick and remove only historical-term sections with no seat snapshot, no syllabus link and only backfill-sourced instructor rows.
- `docs/runbooks/historical-instructor-backfill.md` (all six required headings, commands, how to read each verdict, the 3,216 / 1,329 / 2,178 / 2,829 comparison, exit codes, rollback and scoring revert) and a linked section 14 in `hosted-beta-operations.md`.
- 36 new tests in `tests/schedule/test_backfill_cli.py`. Full suite 843 passed, 4 skipped; `ruff check .` and `mypy src` clean (the new test file is mypy-clean too).

## Task Commits

1. **Task 1 (tracer): the D-04 what-if in the dry run** - `8e179ed` (feat)
2. **Task 2: atomic apply under the sweep lock** - `67b3f59` (feat)
3. **Task 3: rollback, rebuild-only and the runbook** - `4a6bf94` (feat)

Tracer gate: the tracer `<verify>` (pytest on `tests/schedule/test_backfill_cli.py`, `ruff check .`, `mypy src`) passed end to end before the commit and again before expansion.

## Files Created/Modified

- `src/easy_a/schedule/backfill_cli.py` - what-if, apply gate, undo modes, report and emit changes
- `src/easy_a/schedule/backfill.py` - `RollbackSelection`, `select_rollback_sections`, `delete_backfilled_sections`
- `tests/schedule/test_backfill_cli.py` - new: what-if, apply, lock, expect-inserted, invariant, rollback, rebuild-only, mode tests
- `tests/schedule/test_backfill.py` - 10-02 apply tests pass `--rebuild-term 202701`; `test_report_json_matches_stdout` strips the file-only `changes` lists before comparing
- `docs/runbooks/historical-instructor-backfill.md` - new operator runbook
- `docs/runbooks/hosted-beta-operations.md` - section 14 with the link

## Decisions Made

- Undo modes report the diff but are never gated on it (`applied.gated` false); only `--apply` gates.
- A rollback preview performs the real deletion and rebuild inside a transaction it rolls back, and takes the sweep lock, so preview and commit cannot differ.
- Rollback eligibility requires at least one instructor row and only backfill-sourced rows.
- The delete itself is restricted to the five historical terms, independent of the selection.
- `--rebuild-term` and `--what-if-term` share one validator (six digits, not a historical term).
- The pairs verdict is informational for the exit code; the runbook makes an unexplained delta a human blocker.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A plan 10-02 test asserted the report file equals stdout**
- **Found during:** Task 1
- **Issue:** `test_report_json_matches_stdout` compared the `--report-json` file with the stdout object. The plan requires the file to also carry the per-section `changes` lists, so the equality could no longer hold.
- **Fix:** The test removes the file-only `changes` keys from the file's `what_if` diffs, then still asserts the whole object equals stdout. Nothing else in the assertion was weakened.
- **Files modified:** `tests/schedule/test_backfill.py`
- **Commit:** `8e179ed`

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none on scope.

Notes (not deviations): the 10-02 apply tests were updated to pass `--rebuild-term 202701`, as the plan directed, and the two tests that expect exit 2 (`--apply` with a refused term or a pause below the floor) now also pass it, so they still fail for their own reason and not for the missing flag. The ineligible-section behavior is tested for four reasons (seat snapshot, syllabus, other-source instructor, no instructor row), one more than the plan listed.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The destructive rollback path is the one in the plan's threat model (T-10-20): preview by default, `--yes` required, historical terms and backfill-only rows only. T-10-17 (dry run always rolls back), T-10-18 (sweep lock first in apply, rollback and rebuild-only) and T-10-19 (`--expect-inserted` plus the course-level invariant) are mitigated as planned and covered by tests. No package was added (T-10-SC).

## User Setup Required

None. The live run (dry run, owner review, apply, verification) is plans 10-07 and 10-08, following the new runbook.

## Next Phase Readiness

Plan 10-07 can run the dry run against hosted Supabase and take the D-04 review to the owner; plan 10-08 does the apply. Carry-forward points:

- The PostgreSQL paths are unproven here: `try_sweep_lock` is a no-op on SQLite, and SQLite does not enforce `ON DELETE CASCADE`. The explicit child-first deletes were chosen to behave identically on both, but the first real `--rollback --yes` is the first PostgreSQL execution.
- Exit code 2 now means both an argparse usage error and "sweep lock busy" (the plan's choice); the JSON `status` `busy` tells them apart.
- A dry run followed by an apply is two whole-term requests per term (each invocation fetches). The runbook states this against D-22(e); say so if the owner reads "one request per term" as covering the whole procedure.

## Self-Check: PASSED

- Created files exist: `tests/schedule/test_backfill_cli.py`, `docs/runbooks/historical-instructor-backfill.md`.
- Commits exist: `8e179ed`, `67b3f59`, `4a6bf94` (`git log` shows all three on `phase-10-prof-grades`); `git rev-list --count e3030a7..HEAD` is 3.
- Acceptance criteria: `grep` shows `measure_instructor_pairs` and `diff_score_rows` in the dry-run path, and `try_sweep_lock` and `refresh_section_rankings` in `backfill_cli.py`; all six runbook headings and the `hosted-beta-operations.md` link are present.
- Plan verification: `uv run pytest -q -x` 843 passed, 4 skipped; `uv run ruff check .` and `uv run mypy src` clean.
