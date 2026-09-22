---
phase: 05-mvp1-p2-grade-data-sourcing-import-to-supabase
plan: 01
subsystem: database
tags: [supabase, infocenter, grades, rankings-cache, provenance]
requires:
  - phase: 04-mvp1-p1-grade-course-attribution-fix
    provides: canonical course attribution, fail-closed workbook parsing, and live rankings cache integration
provides:
  - real Fall 2024 MAC 1105 aggregate grade history in hosted Supabase
  - a verified historical-import plus live-cache-rebuild operator procedure
  - aggregate-only provenance for the tracer import
affects: [05-02-grade-data-scaling, historical-analytics, data-quality]
actuals:
  tokens: 1611
  tasks: 3
  commits: 2
tech-stack:
  added: []
  patterns: [historical-term import followed by separate live-term cache rebuild, raw-to-raw aggregate reconciliation]
key-files:
  created:
    - docs/runbooks/grade-import.md
    - .planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md
  modified: []
key-decisions:
  - "Used MAC 1105 Fall 2024 as the bounded tracer and reconciled the source Total Grades sum against the database raw total_grade_count, never the smoothed score."
  - "Applied the checked-in 0003_create_section_rankings migration because hosted Supabase was at 0002 and could not rebuild the required cache."
patterns-established:
  - "Import each workbook under its confirmed historical Banner term, then rebuild term 202701 separately."
  - "Retain only per-course aggregates and provenance in Git; keep raw InfoCenter exports outside repository history."
requirements-completed: [REQ-GRADES-01]
coverage:
  - id: D1
    description: "MAC 1105 has real historical grade evidence in hosted Supabase and all five live sections use course-backed scoring."
    requirement: REQ-GRADES-01
    verification:
      - kind: integration
        ref: "scripts/analyze_course.py --term 202701 --subject MAC --course 1105"
        status: pass
      - kind: manual_procedural
        ref: "Operator approval: InfoCenter Total Grades 1,138 equals DB raw total_grade_count 1,138 and score_source=course"
        status: pass
    human_judgment: true
    rationale: "The authenticated source report and hosted database aggregate required operator comparison; approved 2026-09-21."
  - id: D2
    description: "The reusable runbook documents scoped historical import, the separate 202701 rebuild, and honesty checks."
    requirement: REQ-GRADES-01
    verification:
      - kind: other
        ref: "Runbook contract checks for --grade-file and --term 202701"
        status: pass
    human_judgment: false
  - id: D3
    description: "No raw XLS/XLSX export or row-level derivative entered Git history."
    requirement: REQ-GRADES-01
    verification:
      - kind: other
        ref: "git ls-files -- '*.xlsx' '*.xls'"
        status: pass
    human_judgment: false
duration: 54min
completed: 2026-09-21
status: complete
---

# Phase 05 Plan 01: Tracer Grade Import Summary

**A bounded Fall 2024 MAC 1105 InfoCenter export now supplies verified course-backed history to the Spring 2027 rankings cache, with exact aggregate reconciliation and a reusable operator runbook.**

## Performance

- **Duration:** 54 min
- **Started:** 2026-09-21T13:50:00-04:00
- **Completed:** 2026-09-21T14:44:20-04:00
- **Tasks:** 3
- **Files modified:** 2 operational artifacts plus this summary

## Accomplishments

- Imported six approved aggregate rows for MAC 1105 under their confirmed Fall 2024 Banner term; database raw `total_grade_count` 1,138 exactly matches the InfoCenter `Total Grades` sum.
- Rebuilt the Spring 2027 rankings cache so all five live MAC 1105 sections changed from `effective_n=0` / `score_source=global` to `effective_n=1102.0` / `score_source=course`.
- Added a reusable import runbook and aggregate-only provenance record while keeping the raw workbook outside Git.

## Task Commits

1. **Tasks 1-2: Source, import, rebuild, validate, and document the tracer** - `fd4c83d` (docs)
2. **Task 3: Human verification** - approved by the operator on 2026-09-21; captured in this plan metadata commit

## Files Created/Modified

- `docs/runbooks/grade-import.md` - Historical import, separate live cache rebuild, validation, deduplication, and data-handling procedure.
- `.planning/phases/05-mvp1-p2-grade-data-sourcing-import-to-supabase/05-IMPORT-RECORD.md` - Aggregate tracer result and provenance without raw rows.

## Decisions Made

- Chose the narrow MAC 1105 / Fall 2024 / Tampa report as the Phase 5-1 tracer rather than broad scraping.
- Treated `total_grade_count` as the exact source-reconciliation contract; `effective_n` and easiness remain intentionally derived/smoothed values.
- Applied existing migration `0003_create_section_rankings` to the hosted database after the first import exposed schema drift at revision 0002.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Hosted database lacked the rankings cache table**
- **Found during:** Task 2 historical refresh
- **Issue:** The grade stage committed successfully, but the cache stage failed because hosted Supabase was at migration 0002 and `section_rankings` did not exist.
- **Fix:** Applied the checked-in `0003_create_section_rankings` migration, repeated the import to prove idempotency, and rebuilt the live cache.
- **Files modified:** None; database schema advanced using the existing migration.
- **Verification:** Alembic reported head at 0003; repeat ingest inserted 0 and updated 0; the 202701 cache rebuild completed with 0 quality errors.
- **Committed in:** No code commit required; operational result recorded in `fd4c83d`.

---

**Total deviations:** 1 auto-fixed blocking environment issue
**Impact on plan:** Required for the planned cache rebuild; no scope or scoring changes.

## Issues Encountered

- The historical-term refresh reports six quality errors because no Fall 2024 schedule sections are loaded. The supported analytics query uses canonical `course_id` attribution and the live 202701 quality report has 0 errors.

## User Setup Required

None - the operator completed authenticated InfoCenter access and approved the tracer comparison.

## Next Phase Readiness

- Phase 5-1 is approved and ready to checkpoint.
- Plan 05-02 may scale the same bounded, term-explicit import procedure to the remaining ingested Tampa courses.
- The raw export remains local and must not be committed or pushed.

---
*Phase: 05-mvp1-p2-grade-data-sourcing-import-to-supabase*
*Completed: 2026-09-21*
