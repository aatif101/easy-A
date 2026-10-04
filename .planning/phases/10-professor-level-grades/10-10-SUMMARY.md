---
phase: 10-professor-level-grades
plan: 10
subsystem: ui
tags: [react, vitest, instructor-breakdown, gap-closure, P10-WR-01]

requires:
  - phase: 10-professor-level-grades
    provides: InstructorBreakdown component, build_instructor_breakdown API payload (other_instructor_count)
provides:
  - InstructorBreakdown no longer states that instructor-level history is absent when instructors are collapsed into the Others line
  - Regression test for the collapsed-only Staff state in desktop and mobile regions
  - Dated condition-only UI-SPEC amendment for P10-WR-01
  - P10-WR-01 disposition (fixed in 10-10, live after merge and redeploy)
affects: [10-11, verify-work 10, operator merge and Render redeploy of easy-a-web]

actuals:
  tokens: 1580
  tasks: 2
  commits: 3

plan_head_before: 79062fc408118fd6cb16e4a80f37f7ff2c288836
plan_head_after: a00e9dc9b80d54ad761c9fd77142853898e7a4a7
commits: 3

tech-stack:
  added: []
  patterns:
    - "Empty-state note gated on every evidence signal in the payload (listed rows and collapsed count), never just one"

key-files:
  created: []
  modified:
    - web/src/components/InstructorBreakdown.tsx
    - web/src/components/InstructorBreakdown.test.tsx
    - .planning/phases/10-professor-level-grades/10-UI-SPEC.md
    - .planning/phases/10-professor-level-grades/10-REVIEW-DISPOSITION.md

key-decisions:
  - "isEmpty requires othersCount === 0 in addition to no named instructor and no rows, so collapsed history is never reported as absent"
  - "The row list is omitted when it would hold no rows, rather than rendering an empty ul"
  - "UI-SPEC amended by condition only; no locked copy string added, removed or reworded"

requirements-completed: [REQ-PROF-01]

duration: 3 min
completed: 2026-10-02
status: complete
---

# Phase 10 Plan 10: Collapsed-only Staff state renders truthfully (P10-WR-01) Summary

The instructor panel's dashed "no instructor-level grade history is recorded" note now renders only when the course has no instructor history at all; a Staff section whose instructors are all under the 15-grade cutoff shows the "Historically taught by" block (Source line, Staff explainer) followed by the Others line.

## Performance

- **Duration:** 3 min
- **Started:** 2026-10-02T07:44:42Z
- **Completed:** 2026-10-02T07:46:00Z (plus summary write)
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- RED then GREEN on the tracer slice: the new test failed on the unmodified component (empty note rendered, no Source line), then passed after a one-condition fix. Test commit contains only the new test.
- `InstructorBreakdown.tsx`: `othersCount` is computed before `isEmpty`, and `isEmpty` additionally requires `othersCount === 0`. The row `ul` renders only when at least one row exists (`hasRows`). No string constant, class constant, heading choice, InfoTip placement, disclosure logic or Others-line wording changed.
- `10-UI-SPEC.md`: condition cells of the Copywriting "Empty state body" row and the UI Considerations "empty" row narrowed; a dated "## Amendments" entry cites 10-VERIFICATION.md gap 2 and P10-WR-01. The locked empty-state copy remains verbatim in both places.
- `10-REVIEW-DISPOSITION.md`: `open: 11`, `fixed: 1`, P10-WR-01 row names plan 10-10 and fix commit 4318e44 and says it is live only after merge and Render redeploy; deferral sentence for the other eleven findings added.

## Task Commits

1. **Task 1 (tracer): RED test** - `ce93724` (test)
2. **Task 1 (tracer): GREEN fix** - `4318e44` (fix)
3. **Task 2: UI-SPEC amendment and disposition** - `a00e9dc` (docs)

Plan metadata (SUMMARY, STATE, ROADMAP) is committed separately.

## Verification

- `npm --prefix web test -- InstructorBreakdown`: 18 passed. New test alone: `Tests 1 passed`.
- Full gate chain: eslint 0, `tsc -b` 0, vitest 119 passed (9 files), production build (`VITE_USE_MOCK_DATA=false`) built `index-Cn8gBM45.js`.
- Acceptance criteria: `othersCount === 0` count 1; zero changed upper-case const lines versus origin/main; the test diff versus origin/main removes no lines (the existing no_instructor_history empty-note test is untouched); UI-SPEC has 4 P10-WR-01 mentions, one "## Amendments", the locked empty-state body twice; the only removed UI-SPEC lines are the two condition rows; disposition has 11 rows reading "open".
- Tracer feedback gate: auto-mode verification re-run passed end to end before expansion; no `blocking-human` gate on this plan.

## Deviations from Plan

None - plan executed exactly as written.

One housekeeping edit beyond the plan's literal list: the disposition ledger's intro sentence ("no finding has been fixed or dismissed yet") was made consistent with the new row; no finding row other than P10-WR-01 changed.

## Issues Encountered

None.

## Human-check outstanding (not an executor task)

Live visual check on https://easy-a-web.onrender.com (Spring 2027, desktop and 320 px) after the operator merges and Render redeploys easy-a-web: a Staff or unnamed section in the collapsed-only state should show the "Historically taught by" heading, Source line, Staff explainer and "N other instructors with under 15 grades each", with no dashed no-history note and no rows. Confirm the bundle name differs from the pre-fix `index-sH87Oudy.js`. If plan 10-11 Task 3's scan finds no section in this state, record "not exercisable on live data"; the vitest test is then the only evidence. Queued for `/gsd-verify-work 10`. Until the merge, the live site still shows the P10-WR-01 statement. This plan does not push, open a PR, merge or deploy (PROJECT.md D-10).

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file access or schema change. T-10-30 and T-10-31 mitigated as planned; T-10-SC: no package added, removed or upgraded.

## Next Phase Readiness

Gap 2 of 10-VERIFICATION.md is closed in source and tests. Gap 2's live-count item is plan 10-11 Task 3. Ready for 10-11.

## Self-Check: PASSED

- FOUND: web/src/components/InstructorBreakdown.tsx, web/src/components/InstructorBreakdown.test.tsx, 10-UI-SPEC.md, 10-REVIEW-DISPOSITION.md
- FOUND commits: ce93724, 4318e44, a00e9dc
