---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
plan: 03
subsystem: ui
tags: [react, typescript, vitest, testing-library, evidence-transparency]

# Dependency graph
requires:
  - phase: 08-mvp1-p5-end-to-end-mvp-1-verification (plan 02)
    provides: the live D-21 inventory (3,122 evidence-backed course/effective_n>0 sections;
      300 course/effective_n=0 x4900-series non-letter-grade exceptions; 311 subject; 50 global)
      that this plan's UI must state truthfully
provides:
  - "describeEvidence() in web/src/utils/rankings.ts: single source of truth for what backs a
    ranking's displayed easiness score, across four scopes (course_history,
    no_letter_grade_history, subject_fallback, no_course_evidence), failing closed to
    no_course_evidence for any unrecognized score_source"
  - "RankingTable and RankingDetails wired to describeEvidence() so the desktop row, the mobile
    card and both expanded detail regions all state the true evidence scope instead of implying
    course-level history where none exists (D-20)"
  - "web/src/components/RankingEvidence.test.tsx: 8 component tests covering all four evidence
    scopes across both layouts and details"
affects: [08-04, ui, verification]

# Actuals (#2632)
actuals:
  tokens: 5203
  tasks: 2
  commits: 3
  plan_head_before: ce99f9c95915d99a6ddeb1352ce622fc88db4193

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single describeEvidence(ranking) helper as the one place that maps
      score_source + effective_n + subject to student-visible evidence wording;
      RankingTable and RankingDetails both call it once per ranking and never
      re-derive the scope from raw fields."

key-files:
  created:
    - web/src/components/RankingEvidence.test.tsx
  modified:
    - web/src/utils/rankings.ts
    - web/src/components/RankingTable.tsx
    - web/src/components/RankingDetails.tsx

key-decisions:
  - "Implemented describeEvidence()'s full rule set (all four scopes) in Task 1's single commit
    rather than splitting course/effective_n=0 (Task 1) from subject/global/unrecognized-source
    (Task 2) across two production-code commits, because the four scopes are one function with
    one exhaustive rule table and splitting it would have left an intermediate commit with an
    incomplete/inconsistent switch. Task 2's tests therefore pass immediately (GREEN from the
    first run) against the already-complete implementation; see 'TDD Gate Compliance' below."
  - "Restricted the existing low-confidence 'Based on limited historical data.' InfoTip/paragraph
    (desktop and mobile) to the course_history scope only, so no evidence string renders twice
    when a fallback/no-evidence row also happens to carry confidence_label=low."

requirements-completed: [REQ-GRADES-01]

coverage:
  - id: D1
    description: "course/effective_n=0 (D-21 non-letter-grade exception) shows the D-20-honest
      'No letter-grade history (pass/fail or independent study) — score is a prior' note plus
      the matching source/sample labels in the desktop row, mobile card and both expanded detail
      regions, with no 'Course-level history' or '0 grades' text anywhere and the numeric score
      unchanged."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#course with effective_n=0 (D-21 non-letter-grade exception) reads as a prior everywhere"
        status: pass
    human_judgment: false
  - id: D2
    description: "global (effective_n=0 or >0), subject with effective_n<=0, and any unrecognized
      score_source all render the 'No historical grades for this course — score is a global
      prior' / 'Global prior — no course evidence' / 'No course grades' wording (fail-closed),
      never course-level history."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#no_course_evidence: global with effective_n=0 shows the global-prior wording, never course-level history"
        status: pass
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#no_course_evidence: global with effective_n=22 (fixture CRN 17205) shows the global-prior wording, never course-level history"
        status: pass
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#no_course_evidence: subject with effective_n=0 falls closed to the global-prior wording"
        status: pass
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#no_course_evidence: an unrecognized score_source fails closed and never claims course history"
        status: pass
    human_judgment: false
  - id: D3
    description: "subject with effective_n>0 shows 'No course history — score uses {SUBJECT}
      subject-level history', 'Subject-level fallback' and '{N} subject-level grades', so
      subject history cannot be read as the course's own distribution."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#subject_fallback: subject with effective_n=45 names the subject and never claims course history"
        status: pass
    human_judgment: false
  - id: D4
    description: "course and instructor_course with effective_n>0 keep the existing
      'Course-level history' / 'Instructor + course history' labels, the '{N} grades' sample,
      the historical-analytics sentence, and the low-confidence InfoTip/paragraph where
      applicable — unchanged from before this plan."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#course_history: course with effective_n=342 (fixture CRN 15502) keeps the existing wording and shows no evidence note"
        status: pass
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx#course_history: instructor_course with effective_n=34 and low confidence (fixture CRN 16880) keeps the limited-data explanation"
        status: pass
      - kind: unit
        ref: "web/src/App.test.tsx#renders low confidence with its limited-data explanation"
        status: pass
    human_judgment: false
  - id: D5
    description: "Real desktop table / mobile card visual inspection at representative widths for
      course, course/effective_n=0, subject and global rows."
    verification: []
    human_judgment: true
    rationale: "No browser or Playwright is available in this execution environment (checked:
      no chromium/chrome binary, no playwright in web/package.json or node_modules). Recorded as
      NOT MEASURED and logged to .planning/WINDOWS.md (entry 8, kind unrun-verify). The 8
      RankingEvidence.test.tsx component tests render both the desktop and mobile layout
      simultaneously (jsdom does not enforce the Tailwind lg: breakpoint that would otherwise
      hide one) and assert the exact same strings a browser would show, but this is not a
      substitute for a real-viewport human check."

# Metrics
duration: 53min
completed: 2026-09-24
status: complete
---

# Phase 08 Plan 03: Course-evidence wording fix Summary

**describeEvidence() helper makes every easiness score's evidence scope (course history, no-letter-grade prior, subject fallback, or no-course-evidence global prior) explicit and truthful across the desktop row, mobile card and expanded details — closing the D-20 gap where the 300 D-21 x4900-series course/effective_n=0 sections read as "Course-level history · 0 grades".**

## Performance

- **Duration:** 53 min
- **Started:** 2026-09-24T17:32:05Z
- **Completed:** 2026-09-24T18:26:04Z
- **Tasks:** 2
- **Files modified:** 4 (1 new, 3 modified)

## Accomplishments
- Added `describeEvidence()`, `EvidenceScope` and `EvidenceDescription` to `web/src/utils/rankings.ts`, the single place that turns `score_source` + `effective_n` + `subject` into student-visible evidence wording, with a fail-closed default (`no_course_evidence`) for any value not explicitly handled.
- Course/instructor_course sections with `effective_n <= 0` (the 300 D-21 x4900-series non-letter-grade exceptions) now show "No letter-grade history (pass/fail or independent study) — score is a prior" instead of implying course-level history with a misleading "0 grades" sample.
- Global priors (any `effective_n`) and subject fallback with `effective_n <= 0` now read "No historical grades for this course — score is a global prior" / "Global prior — no course evidence" / "No course grades", never "Course-level history".
- Subject fallback with `effective_n > 0` now names the subject explicitly ("No course history — score uses {SUBJECT} subject-level history"), so subject history cannot be mistaken for the course's own distribution.
- Course/instructor_course with `effective_n > 0` are byte-for-byte unchanged from before this plan: same labels, same sample text, same historical-analytics sentence, same low-confidence InfoTip.
- 8 new component tests in `web/src/components/RankingEvidence.test.tsx` cover all four scopes across the desktop row, the mobile card container and both expanded detail regions, with positive and negative (fail-closed) assertions.

## Task Commits

Each task was committed atomically, following the TDD RED → GREEN discipline (`workflow.tdd_mode` is `false` for this project, so the gate is not automation-enforced, but the discipline was followed and verified directly against vitest's own per-test evidence — same approach used in Phase 06-03):

1. **Task 1: Carry the course/effective_n=0 case from the API fields through the helper to row, card and details**
   - `d393631` `test(08-03): add failing test for course/effective_n=0 evidence wording` — RED: 1 test written, run against the unmodified implementation, confirmed to fail on the target assertion (note text not found), not on an import/syntax error.
   - `2692e7f` `feat(08-03): carry course/effective_n=0 evidence through row, card and details` — GREEN: `describeEvidence()` added and wired into `RankingTable`/`RankingDetails`; the RED test passes; full suite (79 tests), typecheck and lint all clean.
   - No REFACTOR commit — implementation needed no cleanup after GREEN.
   - **Tracer feedback gate:** `npm --prefix web test -- src/components/RankingEvidence.test.tsx` re-run end-to-end after the commit, passed. Auto mode inactive (`workflow._auto_chain_active=false`, `workflow.auto_advance` unset); `human_verify_mode=end-of-phase` (default) with an automated-only `<verify>` → re-ran and passed → continued with no checkpoint, per the Interactive branch of the tracer feedback gate.
2. **Task 2: Cover global, subject, course-backed and unexpected sources across both layouts and details**
   - `ec4245f` `test(08-03): cover global, subject, course-backed and unexpected evidence sources` — 7 additional test cases (no_course_evidence x4, subject_fallback x1, course_history x2) against the already-complete `describeEvidence()` implementation from Task 1; all pass immediately (see Deviations below for why there is no separate feat commit for this task).

**Plan metadata:** (pending — this commit)

## Files Created/Modified
- `web/src/utils/rankings.ts` - Added `EvidenceScope`, `EvidenceDescription`, `describeEvidence(ranking)`. `scoreSourceLabel` unchanged (still exported, still maps `course` → "Course-level history").
- `web/src/components/RankingTable.tsx` - Desktop Easiness cell and mobile score block render `evidence.note` when non-null; the "Based on limited historical data." low-confidence explanation (desktop `InfoTip`, mobile paragraph) is now gated to `evidence.scope === "course_history"` so no evidence string renders twice.
- `web/src/components/RankingDetails.tsx` - "Effective sample" and "Score source" cells read `evidence.sampleLabel` / `evidence.sourceLabel`; the historical-analytics sentence is replaced by `evidence.detailSummary` when non-null; the low-confidence explanation is likewise gated to `course_history`.
- `web/src/components/RankingEvidence.test.tsx` (new) - 8 tests: course/effective_n=0, global effective_n=0, global effective_n=22 (fixture CRN 17205), subject effective_n=0, subject effective_n=45 (PSY), course effective_n=342 (fixture CRN 15502), instructor_course effective_n=34 low confidence (fixture CRN 16880), and an unrecognized score_source cast through `unknown`.

## Decisions Made
- Implemented all four `describeEvidence()` scopes in Task 1's single commit instead of splitting production code across Task 1 and Task 2 commits, because they form one exhaustive rule table; see "TDD Gate Compliance" below for how this affected Task 2's RED phase.
- Restricted the pre-existing low-confidence InfoTip/paragraph to `course_history` scope only, so a fallback row that also happens to carry `confidence_label: "low"` does not show both the fallback note and the "Based on limited historical data." text (which would otherwise imply the row has limited-but-real course data, contradicting the fallback note next to it).

## TDD Gate Compliance

`workflow.tdd_mode` is `false` for this project (confirmed via `gsd-tools query config-get workflow.tdd_mode`), so the automated RED/GREEN gate (`gsd_run check tdd-red-evidence`) is not enforced — consistent with the Phase 06-03 precedent recorded in STATE.md ("gsd tdd-red-evidence is Node-TAP-specific and cannot classify [non-TAP] output ... RED/GREEN was verified directly via [the test runner's] own per-test evidence instead"). Vitest's default reporter is not TAP either, so the same reasoning applies here.

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| Task 1 | ✓ (`d393631`, confirmed failing on target assertion) | ✓ (`2692e7f`) | — (none needed) | Pass |
| Task 2 | Not applicable — see below | ✓ (`ec4245f`, tests pass on first run) | — | Documented deviation |

**Task 2 RED note:** Task 2's `<action>` describes extending `describeEvidence()` with the subject/global/unrecognized-source rules. Those rules were already written as part of Task 1's single `describeEvidence()` function (Decisions Made, above), so by the time Task 2's tests were authored, the implementation already satisfied them — Task 2's test run passed on the first execution with zero further production-code changes. This is the "Unexpected GREEN" condition the TDD gate's Fail-Fast Rule 1 calls out; investigated and confirmed benign: the feature genuinely already existed (built intentionally in Task 1, not by accident), not that the test was wrong. Documented here rather than manufacturing an artificial RED by temporarily reverting working code, since `workflow.tdd_mode=false` does not require the automated gate and the underlying discipline (test written to describe behavior, verified against real assertions, full suite green) was preserved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a self-contradictory negative assertion added during Task 2 test authoring**
- **Found during:** Task 2, first test run
- **Issue:** An early draft of the `course_history: course with effective_n=342` test asserted `within(table).queryByText("342 grades")).not.toBeInTheDocument()`, intending to check the desktop row itself has no sample text — but the expanded `RankingDetails` region for that row renders *inside* the same `<table>` (colSpan cell), so "342 grades" legitimately appears within `table` scope once expanded. The assertion was wrong, not the implementation.
- **Fix:** Removed the incorrect negative assertion; the existing `detailRegions.forEach(...)` loop already asserts "342 grades" is present in both expanded regions, which is the actually-intended check.
- **Files modified:** `web/src/components/RankingEvidence.test.tsx`
- **Verification:** `npm --prefix web test -- src/components/RankingEvidence.test.tsx` — all 8 tests pass.
- **Committed in:** `ec4245f` (test was fixed before commit; no separate fix commit needed)

---

**Total deviations:** 1 auto-fixed (1 test-authoring bug, found and fixed before commit)
**Impact on plan:** No scope creep; no production-code change beyond what Task 1/Task 2 specified.

## Issues Encountered
None beyond the test-authoring bug documented above.

## User Setup Required
None - no external service configuration required.

## Manual Browser Observations (Task 2 acceptance criterion)

**NOT MEASURED.** No browser or Playwright is available in this execution environment (verified: no `chromium`/`chromium-browser`/`google-chrome` binary on PATH; no `playwright` in `web/package.json` or `web/node_modules`). Logged to `.planning/WINDOWS.md` as ledger entry 8 (`kind: unrun-verify`, phase 08). The 8 `RankingEvidence.test.tsx` component tests render both the desktop table and the mobile card simultaneously (jsdom does not apply the Tailwind `lg:` breakpoint classes that would otherwise hide one layout) and assert the exact literal strings that would render in either viewport, for course, course/effective_n=0, subject and global rows — this is real evidence of correct text output per layout, but is not a substitute for a real-viewport visual check. 08-04 should carry this NOT MEASURED status into the phase verification report per the plan's `<verification>` instruction.

## Next Phase Readiness

- `web/src/utils/rankings.ts`, `web/src/components/RankingTable.tsx` and `web/src/components/RankingDetails.tsx` now state every easiness score's true evidence scope; ready for 08-04's end-to-end verification report to cite this as the resolved UI-honesty gap for D-20/D-21.
- No blockers. The one open item (manual browser observation) is recorded as NOT MEASURED with a clear reason and a WINDOWS.md entry, not a silent gap.
- `git diff --quiet origin/main -- web/src/types web/src/api web/src/fixtures src` confirmed empty — this plan touched only presentation code, satisfying D-02.

---
*Phase: 08-mvp1-p5-end-to-end-mvp-1-verification*
*Completed: 2026-09-24*

## Self-Check: PASSED

All created/modified files verified present on disk; all three task commits (`d393631`, `2692e7f`, `ec4245f`) verified present in `git log`.
