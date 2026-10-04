---
phase: 10-professor-level-grades
plan: 09
subsystem: rollout-closeout
tags: [deployed-ui, bundle-check, uat-targets, state-facts, roadmap, requirements, rollout-evidence]

requires:
  - phase: 10-professor-level-grades
    provides: "10-08 live apply and post-apply verification (10-ROLLOUT-EVIDENCE.md), 10-04 InstructorBreakdown UI, 10-UI-SPEC.md visual-check rows"
provides:
  - "Deployed bundle check: the live web build index-sH87Oudy.js contains the instructor block copy and the verbatim D-15 caveat"
  - "Concrete CRN targets for the six queued UI visual checks (UAT), none marked passed"
  - "STATE.md, ROADMAP.md and REQUIREMENTS.md carry Phase 10's dated live facts with evidence citations; next action is /gsd-verify-work 10"
affects: [phase-10-verification, phase-10-uat, REQ-PROF-01]

actuals:
  tokens: 5300   # chars/4 over the 21,158 characters added in the two work commits (evidence section, STATE, ROADMAP, REQUIREMENTS); excludes this SUMMARY
  tasks: 2
  commits: 2     # MEASURED: git rev-list --count 650d5c2..HEAD before this close-out commit

plan_head_before: 650d5c212678473572c1ea0be08b4330f5c726e2
plan_head_after: 1b21447339a95f62c8281ac87e11ce67e53da017   # last work commit before the close-out metadata commit

tech-stack:
  added: []
  patterns:
    - "Closeout evidence from public GETs only: static bundle grep and a full read of the public search API; counts, CRNs and name lengths, never names"

key-files:
  created: []
  modified:
    - .planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "No visual check is recorded as passed: the six human checks are queued for end-of-phase UAT with exact CRN targets; the bundle grep proves the copy is deployed, not that it renders correctly"
  - "REQ-PROF-01 is left unticked (live, pending phase verification); ROADMAP Coverage row is the half-filled style Phase 9 used, and success criterion 1 stays recorded as unmet as measured"
  - "The 40-character-name backstop is recorded as only partly coverable live (longest listed name is 18 characters) rather than substituting an 18-character pass for it"

requirements-completed: []  # plan frontmatter declares REQ-PROF-01; deliberately NOT marked complete, see 'Requirement status'

coverage:
  - id: D1
    description: "The deployed web bundle contains 'Instructors for this course', 'Historically taught by' and the verbatim D-15 co-teaching caveat, and points at the live API"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "curl GET https://easy-a-web.onrender.com/ then the hashed asset /assets/index-sH87Oudy.js (HTTP 200, 242,919 bytes), fixed-string grep for each copy string (1 match each); plan Task 1 automated check passes"
        status: pass
    human_judgment: false
  - id: D2
    description: "The instructor block renders and lays out as the UI-SPEC requires on desktop and at 320 px (named-instructor, Staff, lab, fallback and more-than-five-instructor sections; Others line; 40-character name wrap; InfoTip clipping)"
    requirement: "REQ-PROF-01"
    verification: []
    human_judgment: true
    rationale: "Visual and responsive behaviour that no test here asserts; six checks queued for end-of-phase UAT with CRN targets in 10-ROLLOUT-EVIDENCE.md '## Deployed UI'. Not observed by anyone."
  - id: D3
    description: "STATE.md, ROADMAP.md and REQUIREMENTS.md state the live Phase 10 facts using only numbers present in 10-ROLLOUT-EVIDENCE.md, with REQ-PROF-01 live and pending verification"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "plan Task 2 automated check (STATE cites evidence and gsd-verify-work 10; ROADMAP Phase 10 live; REQUIREMENTS REQ-PROF-01 cites evidence) plus a grep that each copied figure occurs in 10-ROLLOUT-EVIDENCE.md"
        status: pass
    human_judgment: false

duration: "about 12 min wall clock (public GETs and document edits)"
completed: 2026-10-02
status: complete
---

# Phase 10 Plan 09: Deployed-UI check and planning facts Summary

**The deployed web bundle carries the instructor block and the verbatim D-15 caveat, six UI-SPEC visual checks are queued with concrete CRN targets (none observed), and STATE, ROADMAP and REQUIREMENTS now record Phase 10 as live and pending verification with evidence-sourced numbers.**

## Performance

- **Duration:** about 12 min wall clock
- **Completed:** 2026-10-02T02:12Z
- **Tasks:** 2 (one tracer, one auto)
- **Files modified:** 4 (the evidence file, STATE.md, ROADMAP.md, REQUIREMENTS.md), plus this SUMMARY

## Accomplishments

- **Deployed bundle (Task 1, tracer).** `GET /` on `https://easy-a-web.onrender.com` references `/assets/index-sH87Oudy.js` (242,919 bytes, the same size the pre-merge local build reported). A fixed-string search found "Instructors for this course", "Historically taught by", the verbatim co-teaching caveat, the lab-section note, "Show all", "Not scored" and the Staff-section strings once each; the placeholder API host of the local gate build occurs 0 times and `easy-a-api.onrender.com` is compiled in. Recorded under `## Deployed UI`.
- **Live data read.** All 3,707 public search items were read (20 pages of 200). The status split equals the post-apply record: `ready` 2,506, `lab_section` 540, `no_instructor_history` 3, null 658.
- **UAT targets (Task 1).** PSY 2012 CRN 12188 (highlighted current row, a single-term row), CNT 4419 CRN 14250 (no-pinned-row state), IDH 4950 CRN 12497 (Staff section, ready breakdown), CHM 2045L CRN 11528 (lab), SYG 3235 CRN 20075 and CHD 4537 CRN 13112 (subject and global fallback, no block), ENC 1101 CRN 14045 (62 rows), ANT 4930 CRN 10805 and BSC 4933 CRN 18286 (Others line), CRW 3312 CRN 13723 and IDH 4950 CRN 12497 (longest name, 18 characters, visible and inside the disclosure). Six checks queued; none marked passed.
- **Planning facts (Task 2).** STATE.md gained a dated Phase 10 block (sections per term and total, backfill rows, `score_source` split including `instructor_course` 637, breakdown counts, D-21 3,049, join re-measure verdict and deltas, p95 273.10 ms, payload growth, deployed UI, open items), updated repo facts, the D-24 lines ("approved 2026-09-30, live 2026-10-02") and a new Next action (`/gsd-verify-work 10`) that keeps WR-03, NEB 0001, the gate-recovery rehearsal and the 30 s sweep-duration gap open. ROADMAP.md: Phase 10 status live and pending verification, plans 9/9 with every box checked, Coverage row half-filled. REQUIREMENTS.md: REQ-PROF-01 evidence note, checkbox unticked.

## Task Commits

1. **Task 1: deployed bundle check, targets, queued checks** - `6cf0d3f` (docs)
2. **Task 2: Phase 10 facts in STATE, ROADMAP, REQUIREMENTS** - `1b21447` (docs)

**Plan metadata:** the close-out commit (this SUMMARY, STATE, ROADMAP, REQUIREMENTS) follows.

## Files Created/Modified

- `.planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md` - gained `## Deployed UI`
- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` - Phase 10 live facts via scoped replacements

## Decisions Made

- Nothing is marked passed that was not observed. The bundle grep establishes that the copy is deployed; it does not establish that the block renders, wraps or lays out correctly.
- REQ-PROF-01 stays unticked and success criterion 1 stays "unmet as measured, accepted at D-04", as instructed.

## Deviations from Plan

None - plan executed as written. Two observations that the plan did not anticipate, recorded in the evidence file as findings for UAT rather than fixed:

1. **No 40-character instructor name exists in live data.** The longest listed name is 18 characters, so UI-SPEC long-text row 1 (a 40-character name at 320 px) can be exercised live only with 18-character names; the 40-character case needs an edited text node or a mock-data build. An 18-character pass must not be recorded as the 40-character result.
2. **ENC 1101 has no Others line.** All 41 sections have `other_instructor_count` 0, so the plan's fourth check ("Others line shows counts only" on ENC 1101) cannot be seen there; ANT 4930 CRN 10805 and BSC 4933 CRN 18286 are the substitute targets. CNT 4419 is also not a highlighted-row target (no pinned row); PSY 2012 is.

Also noted: the plan's Task 2 ROADMAP check (`grep -A6 "## Phase 10" | grep -i live`) is satisfied by the word "live" in the "Depends on" line; the new Status line sits one line outside that window. The Status line does say Live. The REQUIREMENTS check needed the evidence filename within 12 lines of the REQ-PROF-01 line, so the citation sits at the start of the evidence note.

## Authentication Gates

None.

## Issues Encountered

None in execution. Open items carried, none resolved or hidden by this plan: the first live worker sweep after the apply has not been observed; success criterion 1 (`pairs_match_reference`) is unmet as measured, accepted at D-04; the search payload growth (7.0x ENC 1101, 2.5x default page, browser cost unmeasured); the 58 absent graded CRNs; WR-03, NEB 0001, the optional gate-recovery rehearsal and the 30 s sweep-duration gap from Phase 9.

## User Setup Required

None.

## Known Stubs

None.

## Threat Flags

None - no code, endpoint, auth path or schema change; the only access was public GETs. No instructor name, connection string or pooler host is written in the evidence section (a grep for the one name that appeared in a tool output returned 0).

## Requirement status

REQ-PROF-01 is declared by this plan and by 10-08 but is NOT marked complete: the checkbox is unticked, `requirements-completed` is empty and no `requirements mark-complete` was run. Verification has not run, the six visual checks are unobserved, and ROADMAP success criterion 1 is unmet as measured.

## Next Phase Readiness

- **Next:** `/gsd-verify-work 10` (verification and UAT). The UAT items are the six checks in `10-ROLLOUT-EVIDENCE.md` "Deployed UI" with their CRN targets.
- **Before or at verification:** observe the first post-apply worker sweep (`sync-status?term=202701` succeeded and not stale, `report_ranking_diff.py --term 202701` exit 0, `instructor_course` still 637); the verifier must treat criterion 1 as unmet, accepted at D-04.

## Self-Check: PASSED

- `10-ROLLOUT-EVIDENCE.md` contains `## Deployed UI` and the string "Instructors for this course" (Task 1 automated check passed); STATE.md, ROADMAP.md and REQUIREMENTS.md pass the Task 2 automated check.
- Work commits `6cf0d3f` and `1b21447` exist on `phase-10-post-merge`; neither deleted any file.
- Acceptance: all nine Phase 10 plans are checked in ROADMAP.md; REQ-PROF-01 is unticked; every Phase 10 figure copied into the planning documents occurs in `10-ROLLOUT-EVIDENCE.md`.

---
*Phase: 10-professor-level-grades*
*Completed: 2026-10-02*
