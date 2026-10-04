---
phase: 10-professor-level-grades
plan: 02
subsystem: schedule
tags: [backfill, historical-sections, section-instructors, usf-whole-term, idempotent, cli, sqlalchemy, pytest]

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: fetch_whole_term (chunked fail-closed whole-term parse), StaffScheduleClient.search_term, sections.removed_at
  - phase: 10-professor-level-grades
    provides: plan 10-01 instructor-course retune read through get_instructor_course_historical_outcome_stats
provides:
  - easy_a.schedule.backfill (HISTORICAL_GRADE_TERMS, BACKFILL_SOURCE, grade-key loading, batch course resolution, pure row selection, change-only bulk write)
  - easy_a.schedule.backfill_cli (argparse one-off CLI, main(argv, *, session_factory, client_factory, now_fn, sleep) -> int)
  - scripts/backfill_historical_sections.py wrapper
  - RowSpec.section_type in tests/sync/wholeterm_html.py
affects: [10-06, 10-07, 10-08, instructor-backfill, rankings-cache]

plan_head_before: a3f92985ae68914da143f94c2bb380aaa9181be1
plan_head_after: a433f0661dbc41961dbed81e43d322d00f204bab

actuals:
  tokens: 13750
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Pure selection (select_backfill_rows) separated from bulk DB reads and executemany writes"
    - "Statement count independent of row count: Core insert(Section) executemany plus one id read, not per-row unit-of-work INSERTs"
    - "CLI emits exactly one JSON line of counts; error text scrubbed of URL-shaped strings"

key-files:
  created:
    - src/easy_a/schedule/backfill.py
    - src/easy_a/schedule/backfill_cli.py
    - scripts/backfill_historical_sections.py
    - tests/schedule/test_backfill.py
  modified:
    - tests/sync/wholeterm_html.py

key-decisions:
  - "The write path is a dedicated change-only bulk writer, not _upsert_sections: it appends no seat snapshots, never sets removed_at, and appends an instructor row only when the whitespace/case-cleaned name differs from the current resolved name."
  - "Sections are inserted with Core executemany plus one id read because the ORM unit of work issued one INSERT per row on SQLite (81 vs 21 statements for 40 vs 10 rows); the bounded-statement test pins this."
  - "A failed guard never writes in --apply. --dry-run still runs the rolled-back write path for what-if counts, except when a duplicate CRN makes the write unsafe."
  - "All terms are fetched before any transaction opens, so a failure on a later term leaves nothing written for earlier terms."

requirements-completed: [REQ-PROF-01]

coverage:
  - id: C1
    description: "One whole-term request per term (empty subject, campus T) becomes grade-backed Section and SectionInstructor rows with no seat snapshot, an IngestRun, a JSON count report and an activated instructor-course join"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_tracer_one_term_goes_from_whole_term_response_to_joined_rows"
        status: pass
    human_judgment: false
  - id: C2
    description: "Writes are idempotent and change-only: a re-run inserts, updates and appends nothing; a changed instructor appends exactly one row; a changed field counts as one update"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_rerun_over_identical_data_changes_nothing"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_changed_instructor_appends_one_row_and_changed_field_counts_as_update"
        status: pass
    human_judgment: false
  - id: C3
    description: "Dry run reports the same per-term counts as apply and leaves every table unchanged"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_dry_run_reports_apply_counts_and_changes_nothing"
        status: pass
    human_judgment: false
  - id: C4
    description: "Only the five D-22(e) terms are accepted; 202701 and other terms exit 2 with no request; pause below 10 s is rejected"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_terms_outside_the_allowlist_are_refused_without_a_request"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_pause_below_the_floor_is_rejected"
        status: pass
    human_judgment: false
  - id: C5
    description: "Request policy: no retry, stop at the first failed term with a coarse URL-free kind and nothing written, pacing between terms only"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_http_500_on_second_term_stops_with_nothing_written"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_sleep_runs_between_terms_and_never_after_the_last"
        status: pass
    human_judgment: false
  - id: C6
    description: "Fail-closed guards: zero parsed rows, unmatched grade CRN fraction above the limit and duplicate CRNs among rows to write abort before any write"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_zero_parsed_rows_fail_the_guard_in_apply_and_dry_run"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_unmatched_grade_fraction_above_the_limit_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_duplicate_crn_among_rows_to_write_aborts_before_any_write"
        status: pass
    human_judgment: false
  - id: C7
    description: "Non-Tampa, unattributed-grade and course-key-mismatch rows are skipped and counted; Laboratory sections are stored and histogrammed"
    requirement: REQ-PROF-01
    verification:
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_non_tampa_unattributed_and_mismatched_rows_are_skipped_and_counted"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_laboratory_sections_are_stored_and_listed_in_the_histogram"
        status: pass
    human_judgment: false
  - id: C8
    description: "Batch course resolution matches resolve_course_id; write statements do not grow with row count; a live 202701 sweep leaves backfilled history untouched; the backfill imports no sync change-only logic and is absent from render.yaml and the Dockerfile"
    requirement: REQ-PROF-01
    verification:
      - kind: unit
        ref: "tests/schedule/test_backfill.py#test_batch_course_resolution_matches_resolve_course_id"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_statements_do_not_grow_with_the_number_of_rows"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_backfilled_history_survives_a_live_sweep_untouched"
        status: pass
      - kind: integration
        ref: "tests/schedule/test_backfill.py#test_backfill_is_isolated_from_the_live_sync_and_the_worker"
        status: pass
    human_judgment: false
  - id: C9
    description: "No LIVE run against hosted Supabase or USF was made in this plan; real-data counts and the post-run join re-measure belong to the operator step in plan 10-08"
    requirement: REQ-PROF-01
    human_judgment: true
    rationale: "Hosted counts, real USF response shape and the 2026-09-28 join-coverage re-measure can only be observed by the operator run; tests use a synthetic MockTransport response"

duration: ~20 min
completed: 2026-10-01
status: complete
---

# Phase 10 Plan 02: Historical Section Backfill Summary

**One-off five-term backfill CLI: one whole-term USF request per term, grade-backed Section and SectionInstructor rows written in bulk and change-only, with a rolled-back dry run and fail-closed guards.**

## Performance

- **Duration:** ~20 min (start time was not captured; estimate)
- **Completed:** 2026-10-01
- **Tasks:** 2
- **Files:** 5 (4 created, 1 modified)

## Accomplishments

- `src/easy_a/schedule/backfill.py`: `HISTORICAL_GRADE_TERMS`, `BACKFILL_SOURCE`, `backfill_ingest_source`, `load_grade_keys` (one query), `resolve_course_ids` (one query, highest `catalog_edition`, same rule as `resolve_course_id`), pure `select_backfill_rows` with the ordered skip counts (not_graded, non_tampa, grade_course_unattributed, course_key_mismatch, uncataloged), `validate_selection`, and `write_term_backfill` (bulk inserts, change-only updates, bulk `last_seen_at` refresh in chunks of 500, instructor append only on a changed name, never a seat snapshot, never `removed_at`).
- `src/easy_a/schedule/backfill_cli.py`: `--terms` (allowlist via argparse `choices`), required `--dry-run | --apply`, `--pause-seconds` (floor 10, default 30), `--max-unmatched-fraction` (0.02), `--report-json`; exit codes 0/1/2; stdout is one JSON object; error text scrubbed of URL-shaped strings.
- `scripts/backfill_historical_sections.py` is the two-line wrapper; `--help` lists every documented flag.
- 22 tests in `tests/schedule/test_backfill.py`; full suite 742 passed, 4 skipped (baseline was 720 passed); `ruff check .` and `mypy src` clean; the new test file is mypy-clean.

## Task Commits

1. **Task 1 (tracer): whole-term response to joined Section and SectionInstructor rows** - `c1eb60a` (feat)
2. **Task 2: idempotence, request policy and fail-closed guards** - `a433f06` (feat)

Tracer gate: the tracer `<verify>` (pytest on the backfill tests, ruff, mypy) was re-run end to end after the commit and passed before expansion.

## Files Created/Modified

- `src/easy_a/schedule/backfill.py` - selection, bulk read and change-only bulk write
- `src/easy_a/schedule/backfill_cli.py` - argparse CLI, fetch loop, guards, dry-run rollback, JSON report
- `scripts/backfill_historical_sections.py` - wrapper calling `backfill_cli.main`
- `tests/schedule/test_backfill.py` - end-to-end and guard tests over a fake USF client
- `tests/sync/wholeterm_html.py` - `RowSpec.section_type` (default "Class Lecture"; existing sync tests unchanged)

## Decisions Made

- Dedicated bulk writer instead of reusing `_upsert_sections` (which appends an instructor and seat snapshot on every run and does one SELECT per row); only `_section_values` is imported from `schedule.ingest`.
- Core `insert(Section)` executemany plus one id read, because the ORM unit of work issued one INSERT per row (81 vs 21 statements for 40 vs 10 rows).
- Apply never writes past a failed guard; dry run still shows the rolled-back what-if counts unless a duplicate CRN is present.
- Everything is fetched before any transaction opens, so a later-term failure leaves earlier terms unwritten.
- An ambiguous or missing current instructor state counts as "differs", so a section with two observations at the same instant gets a resolving row on the next run; real runs have distinct `fetched_at` times.

## Deviations from Plan

None - plan executed exactly as written.

Notes (not deviations): the bulk-insert approach in Task 2 replaced the ORM `session.add` insert from the Task 1 tracer once the bounded-statement test showed per-row INSERTs; the plan's behavior block required exactly that bound. `tests/sync/test_import_hygiene.py` is unchanged, so the worker import graph is unaffected (the new isolation test covers the backfill's own import graph).

## Issues Encountered

- `parse_qs` drops blank values by default, so the first tracer run could not see the empty `P_SUBJ`; fixed in the test with `keep_blank_values=True`.
- Reusing one constant clock across runs made two instructor observations tie on `observed_at` (ambiguous state); tests now use distinct run times, matching real runs.

## Known Stubs

None.

## Threat Flags

None. The only new surface is the operator-run CLI writing to the production database, which the plan's threat model (T-10-03 to T-10-07) already covers: term allowlist, one request per term with a 10 s floor and no retry, change-only instructor append, count-only URL-free output, and skip counts for unattributed or mismatched grade rows.

## User Setup Required

None. The live run against hosted Supabase (dry run first, then apply) is the operator step in plan 10-08; it needs `DATABASE_URL` and migration 0004 applied, which hosted Supabase already has.

## Next Phase Readiness

Ready for the remaining Phase 10 plans. Plan 10-06 adds the D-04 what-if diff to `--dry-run`, the cache rebuild to `--apply` and a rollback mode on top of these functions. Nothing has been run against real USF or hosted data; the real response shape, the Laboratory vocabulary and the join-coverage re-measure against the 2026-09-28 report (3,216 pairs) are still to be confirmed by the operator run.

## Self-Check: PASSED
