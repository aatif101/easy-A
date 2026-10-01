---
phase: 10-professor-level-grades
plan: 04
subsystem: web
tags: [react, typescript, tailwind, vitest, instructor-breakdown, ui-spec, d-11, d-13, d-20]

requires:
  - phase: 10-professor-level-grades
    provides: UI-SPEC and CONTEXT D-09..D-15 design contract; API contract field names (implemented server-side by plan 10-05)
provides:
  - web InstructorBreakdown block inside RankingDetails (named, Staff, lab, empty, no-history states)
  - InstructorBreakdownStatus, InstructorHistoryRow, InstructorBreakdown types and optional HistoricalAnalytics.instructor_breakdown
  - formatTermShort, formatTermRange, formatGradeCount, formatTermCount, isNamedInstructor utilities
  - synthetic mock-mode breakdowns (named, Staff, named without history)
affects: [10-05, 10-09, web]

status: complete
plan_head_before: c8c7cf676bc008c8541213cb7f9fc12069f35a6a
plan_head_after: ddae01614a69024ecf759bc8b2ac8811b1960bc5

actuals:
  tokens: 22000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Block gated twice: describeEvidence scope course_history AND a non-null breakdown, so fallback scores never show instructor figures (D-20)"
    - "Section ids derive from the RankingDetails id prop so desktop and mobile instances never duplicate ids"
    - "Thresholds (scoring minimum, collapse cutoff) are read from the breakdown object; the component hard-codes neither"
    - "Staff, ambiguous and unknown sections ignore any is_current flag: no pin, no highlight, no score claim (D-11)"

key-files:
  created:
    - web/src/components/InstructorBreakdown.tsx
    - web/src/components/InstructorBreakdown.test.tsx
    - web/src/utils/rankings.test.ts
  modified:
    - web/src/types/rankings.ts
    - web/src/utils/rankings.ts
    - web/src/components/RankingDetails.tsx
    - web/src/fixtures/rankings.ts
    - web/src/components/SeatBadge.test.tsx

key-decisions:
  - "Dashed notes use font-bold, not the existing font-semibold, because the UI-SPEC two-weight rule and the plan acceptance grep forbid font-semibold in the new component"
  - "Disclosure summary uses default list-item display (py-3 plus min-h-11) so the native marker stays visible"
  - "Empty state (unnamed, no instructors) keeps the heading and the single InfoTip but drops the source line and explainer, since no figure is shown"
  - "A named section whose breakdown claims history but carries no is_current row falls back to the no-history pinned row rather than pinning nothing"
  - "Rows flagged is_current are dropped from the list body in named sections so the pinned row appears exactly once"

requirements-completed: [REQ-PROF-01]

duration: 8 min
completed: 2026-10-01
---

# Phase 10 Plan 04: Instructor Breakdown UI Summary

**Per-instructor grade history block in the expanded ranking panel, with the pinned current instructor, Staff/lab/empty honesty states, API-sourced thresholds, and synthetic mock data.**

## Performance

- **Duration:** about 8 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files:** 3 created, 5 modified

## Accomplishments

- Tracer: a named-instructor breakdown renders from the ranking JSON through the real `RankingTable` on both desktop and mobile layouts, with a unique-id assertion. The tracer `<verify>` (targeted test, lint, typecheck, full suite) passed end to end before expansion.
- Every UI-SPEC state with locked copy: named heading with pinned "This section" row, Staff heading "Historically taught by" with the explainer and no pin or highlight, lab dashed note with no heading/tip/rows, dashed empty note, pinned "No recorded grade history" row, scored and "Not scored / Under {N} grades" slots, "Used in this section's score" only for an `instructor_course` ranking, "Based on 1 term" and "Limited sample" chips, 5-row cap with native `<details>` "Show all {N} instructors", singular/plural Others line.
- Utilities `formatTermShort` (fails closed to the raw code), `formatTermRange`, `formatGradeCount`, `formatTermCount`, `isNamedInstructor`, with their own unit tests.
- Synthetic fixtures: ENC 1101 (named instructor pinned, 6 others, shows the disclosure), MAC 1105 (Staff, no current instructor), BSC 1005 (named, no history). All names invented.
- Test hooks 1-7 are covered by 17 tests in `InstructorBreakdown.test.tsx`. Hook 8 holds: `RankingEvidence.test.tsx` is unmodified and passes.

## Task Commits

1. **Task 1: tracer** - `9413601` (feat)
2. **Task 2: all states, rules, copy, tests** - `7340ade` (feat)
3. **Task 3: synthetic breakdowns and production build** - `ddae016` (feat)

## Verification

- `npm --prefix web run lint && typecheck && test`: clean, 118 frontend tests passed (was 96 per STATE.md baseline; this plan added 22).
- `VITE_USE_MOCK_DATA=false VITE_API_BASE_URL=https://example.onrender.com npm --prefix web run build`: built.
- Acceptance greps: no `text-[11px]`, no `font-semibold`/`font-extrabold`, no `30`/`15` literals in the component; all five locked strings present verbatim; `git diff --quiet -- web/src/components/RankingEvidence.test.tsx` clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing SeatBadge test collided with the new fixture**
- **Found during:** Task 3
- **Issue:** `SeatBadge.test.tsx` ("expanded details show seat data separately from historical analytics") renders `syntheticRankings[0]` (the MAC Staff entry) and asserted `getByText("Easiness")`. Once that entry carried a breakdown, each scored instructor row's "Easiness" caption matched too, so the query found multiple elements.
- **Fix:** Scoped the query to the course-wide `<dt>` with `{ selector: "dt" }`, which is what the assertion always meant. No assertion was weakened. The plan's collision warning named only specific number strings, so this one was not anticipated.
- **Files modified:** `web/src/components/SeatBadge.test.tsx`
- **Commit:** `ddae016`

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none on scope; one test selector made more precise.

## Issues Encountered

None beyond the deviation above.

## Known Stubs

None. The synthetic breakdowns are mock-mode demonstration data only (`VITE_USE_MOCK_DATA=true`), labelled by the file's existing "do not describe real students or sections" note, and the production build sends `instructor_breakdown` straight from the API. The real API field is plan 10-05's job; until it ships, hosted rankings carry no `instructor_breakdown` and the block does not render.

## Threat Flags

None. No new endpoints, auth paths or file access. Instructor names render as React text children only (T-10-12); the block is gated on `course_history` scope (T-10-13); Staff lists carry no pin and no "Used in" line (T-10-11). No packages were added (T-10-SC).

## Deferred to a later plan

- Held-out visual backstops (40-character name at 320 px, InfoTip tooltip clipping at 320 px) are deferred to the hosted visual check in plan 10-09, per the plan's verification section.
- Field names mirror the 10-05 API contract (`collapse_min_effective_n` link); 10-05 must emit exactly these names.

## Next Phase Readiness

Ready for 10-05 (API contract) to emit `historical_analytics.instructor_breakdown`; the UI renders it with no further change.

## Self-Check: PASSED

- Files exist: `InstructorBreakdown.tsx`, `InstructorBreakdown.test.tsx`, `utils/rankings.test.ts` (created); `types/rankings.ts`, `utils/rankings.ts`, `RankingDetails.tsx`, `fixtures/rankings.ts`, `SeatBadge.test.tsx` (modified).
- Commits `9413601`, `7340ade`, `ddae016` found in `git log`.
