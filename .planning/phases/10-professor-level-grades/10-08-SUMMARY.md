---
phase: 10-professor-level-grades
plan: 08
subsystem: rollout
tags: [merge, ci, render-deploy, backfill-apply, d-05, post-apply-verification, instructor_course, rollout-evidence]

requires:
  - phase: 10-professor-level-grades
    provides: "10-07 D-04 approve decision (pairs_match_reference deltas accepted in writing), dry run 4 what-if (would-insert 8,535, 637 sections to instructor_course), 10-06 apply/rollback/rebuild-only CLI, 10-03 ranking diff and pair re-measure"
provides:
  - "Phase 10 code on main: PR #37 merged as bcf1dbb with python, web and docker green; Render deployments success for api, worker and web"
  - "Pre-apply live baseline: report_ranking_diff exit 0, inventory PASS/PASS (3,049 evidence-backed), payload bytes and delivery-methods baselines, 0 of 3,707 breakdowns non-null"
  - "The single operator-run apply (D-05) live on hosted data: 8,535 historical sections and 8,535 backfill instructor rows, 637 sections now scored instructor_course"
  - "Post-apply verification of the Phase 10 criteria with dated, measured verdicts (10-ROLLOUT-EVIDENCE.md sections 'CI, merge and deploy', 'Pre-apply live baseline', 'Apply (D-05)', 'Post-apply verification')"
  - "10-APPLY-REPORT.json: the apply's own report (counts and diffs only, no connection strings)"
affects: [10-09, hosted-api-payload-size, historical-instructor-backfill-runbook, REQ-PROF-01]

actuals:
  tokens: 7500   # chars/4 over the 29,835 characters added to 10-ROLLOUT-EVIDENCE.md; excludes the operator-generated 10-APPLY-REPORT.json (427 KB) and this SUMMARY
  tasks: 3
  commits: 2     # MEASURED: git rev-list --count bcf1dbb..HEAD before this close-out commit (no per-plan ledger file exists for 10-08, so the base is the merge commit the continuation started from)

plan_head_before: bcf1dbbace2a16dc8d03d18880f6bcba89f4afe7
plan_head_after: b12cd3c   # last work commit before the close-out metadata commit

tech-stack:
  added: []
  patterns:
    - "Operator-run production write: the executor prepares and verifies read-only, the operator executes the apply from their own shell"
    - "Evidence from READ ONLY transactions and public GETs; counts and identifiers only, no names, no connection strings"

key-files:
  created:
    - .planning/phases/10-professor-level-grades/10-APPLY-REPORT.json
  modified:
    - .planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md

key-decisions:
  - "The apply was run by the operator, once, from their own shell at bcf1dbb with --apply --rebuild-term 202701 --expect-inserted 8535; the executor never ran it and made no USF request or hosted write"
  - "Success criterion 1 is recorded as UNMET as measured (3,297 / 1,314 / 2,153 / 2,785 against 3,216 / 1,329 / 2,178 / 2,829); it stands as accepted in writing in the D-04 decision, not as met"
  - "The search payload growth (ENC 1101 7.0x, default page 2.5x) is a finding for the owner, not a failure: the plan sets no threshold"
  - "No rollback is indicated; none was run"

requirements-completed: []  # plan frontmatter declares REQ-PROF-01; NOT marked complete, see 'Requirement status'

coverage:
  - id: D1
    description: "Phase 10 code merged to main only after green python, web and docker CI (PR #37, merge commit bcf1dbb) and deployed by Render"
    requirement: "REQ-PROF-01"
    verification:
      - kind: integration
        ref: "gh pr checks 37 and GitHub check-runs on bcf1dbb: python, web, docker success (runs 36929153363, 36929155977, 36929434892)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The deployed code alone changed no live score before the apply (report_ranking_diff exit 0, 3,707 rows, 0 changed beyond 1e-9) and the pre-apply baselines were recorded"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "uv run python scripts/report_ranking_diff.py --term 202701 (exit 0, 2026-10-01T21:41:03Z); inventory_tampa_grades.py PASS/PASS"
        status: pass
    human_judgment: false
  - id: D3
    description: "The operator-run apply: 8,535 sections inserted (179 / 2,090 / 448 / 2,840 / 2,978) with 8,535 backfill instructor rows, 0 seat snapshots, 0 removal marks, one succeeded IngestRun per term, 202701 split course 2,696 / subject 325 / global 49 / instructor_course 637, applied diff identical to the reviewed what-if"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "10-APPLY-REPORT.json (leak scan 0 for '://' and 'pooler') and READ ONLY hosted queries recorded under '## Apply (D-05)'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Post-apply consistency: report_ranking_diff exit 0, D-21 inventory PASS/PASS with evidence_backed 3,049 equal to the baseline, validate_tampa_ingest PASS, check_data_quality 0 errors, breakdown counts null 658 / ready 2,506 / lab_section 540 / no_instructor_history 3 with 0 invariant violations over 637 instructor_course rows"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "report_ranking_diff.py, inventory_tampa_grades.py, validate_tampa_ingest.py, check_data_quality.py --term 202701 (all exit 0, 2026-10-02T01:56Z to 02:03Z)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Public API probes and hosted search benchmark: CNT 4419, PSY 2012 (5 instructor_course items with a pinned row carrying effective_n, term_count and source) and a CHM 2045L lab section (lab_section) are served; delivery-methods unchanged; p95 273.10 ms against the 1,500 ms bar (baseline 212.56 ms)"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "public GETs recorded under 'Post-apply verification' item 6; benchmark_rankings_search.py --remote-url --iterations 50 (exit 0, 2026-10-02T02:01Z)"
        status: pass
    human_judgment: false
  - id: D6
    description: "ROADMAP success criterion 1: the join re-measure matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829 at n >= 60 / 30 / 15)"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "uv run python scripts/measure_instructor_pairs.py --before-term 202701 (exit 1, pairs_match_reference FAIL: 3,297 / 1,314 / 2,153 / 2,785)"
        status: fail
    human_judgment: true
    rationale: "FAIL as measured, by definition. The deltas were accepted in writing by the operator in the D-04 decision (2026-10-01T21:23:24Z), which is a judgment, not a re-measure that matches. The n >= 1 recount is an inference only."
  - id: D7
    description: "First live worker sweep after the apply leaves the instructor-level scores intact (sync-status succeeded and not stale, report_ranking_diff exit 0, instructor_course still 637)"
    requirement: "REQ-PROF-01"
    verification: []
    human_judgment: true
    rationale: "Not yet observed: the last sweep (01:08Z) pre-dates the apply (01:35Z to 01:42Z) and the cadence is 3,600 s. An open follow-up check, not a verified result."

duration: "about 4.7 h wall clock from the D-04 decision (2026-10-01T21:23Z) to the post-apply record (2026-10-02T02:03Z), almost all of it operator actions and waiting; executor work is a small fraction"
completed: 2026-10-02
status: complete
---

# Phase 10 Plan 08: Rollout 2 Summary

**Phase 10 is merged (PR #37, CI green), deployed, and the operator's single apply put 8,535 historical sections and instructor rows live and moved 637 sections to instructor_course exactly as reviewed; every required gate passes, but ROADMAP success criterion 1 (the join re-measure) is unmet as measured and stands only as accepted in writing at D-04.**

## Performance

- **Duration:** about 4.7 h wall clock, mostly operator actions and waiting (D-04 decision 2026-10-01T21:23Z; post-apply record 2026-10-02T02:03Z)
- **Started:** 2026-10-01T21:23Z (continuation from the D-04 approval)
- **Completed:** 2026-10-02T02:04Z
- **Tasks:** 3 (two operator checkpoints, one read-only verification)
- **Files modified:** 2 in the work commits (the evidence file and the operator-generated apply report), plus this SUMMARY, STATE.md and ROADMAP.md in the close-out

## Accomplishments

- **Merge and deploy (Task 1).** PR #37 (`phase-10-prof-grades` into `main`) merged as `bcf1dbb` at 2026-10-01T21:33:06Z. python, web and docker passed on both PR runs and on the post-merge run on main. Render's deployments for `easy-a-api`, `easy-a-worker` and `easy-a-web` reached `success` for that SHA (read from GitHub's deployments API; the running container's commit could not be read directly, because `/health` and `sync-status` carry no commit field).
- **Pre-apply baseline.** With the deployed code and no history yet: `report_ranking_diff` exit 0 (3,707 rows, 0 changed beyond 1e-9), inventory PASS/PASS with 3,049 evidence-backed and 658 exceptions, 0 of 3,707 breakdowns non-null, payload sizes recorded (ENC 1101 page 84,210 bytes, default page 99,363 bytes, delivery-methods 175 bytes).
- **The apply (Task 2, operator-run).** One transaction from the operator's own shell, `--apply --rebuild-term 202701 --expect-inserted 8535`: succeeded, 8,535 inserted against 8,535 expected. Per term 179 / 2,090 / 448 / 2,840 / 2,978 sections, each equal to dry run 4's `to_write`. 8,535 backfill instructor rows (one per section, source `usf_schedule_backfill`), 0 seat snapshots, 0 removal marks, one succeeded IngestRun per term, no 202701 instructor row touched. The `score_source` split for 202701 went from course 3,333 / subject 325 / global 49 / instructor_course 0 to course 2,696 / subject 325 / global 49 / instructor_course 637. The applied diff is identical to the reviewed what-if (637 changed, all course to instructor_course, `course_level_violations` 0, same top 50 changes).
- **Post-apply verification (Task 3).** `report_ranking_diff` exit 0; inventory PASS/PASS with `evidence_backed` 3,049 (equal to the baseline); `validate_tampa_ingest` PASS; `check_data_quality` 0 errors; breakdown counts null 658 (equal to the D-21 exception sections) / ready 2,506 / lab_section 540 / no_instructor_history 3, with 0 invariant violations over the 637 instructor_course rows; API probes show a ready breakdown with a pinned row carrying its effective_n, term_count and source (PSY 2012), and a lab section with status `lab_section` (CHM 2045L); delivery-methods byte-identical; hosted p95 273.10 ms (baseline 212.56 ms, bar 1,500 ms).

## Task Commits

1. **Task 1: merge, deploy, pre-apply baseline** - `a0ee139` (docs). The push, the PR and the merge were operator actions, not commits by this plan.
2. **Task 2: operator-run apply, then read-only confirmation** - `b12cd3c` (docs), together with Task 3. The apply itself is not a commit; it ran in the operator's shell.
3. **Task 3: post-apply verification** - `b12cd3c` (docs)

**Plan metadata:** the close-out commit (SUMMARY, STATE, ROADMAP) follows this file.

## Files Created/Modified

- `.planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md` - gained "CI, merge and deploy", "Pre-apply live baseline", "Apply (D-05)" and "Post-apply verification"
- `.planning/phases/10-professor-level-grades/10-APPLY-REPORT.json` - the apply's report written by the operator's run (427,464 bytes, counts and diffs only; 0 occurrences of `://` or `pooler`), committed with the evidence

## What Was Not Met or Not Observed

These are stated plainly; none is smoothed over.

1. **ROADMAP success criterion 1 is UNMET as measured.** `measure_instructor_pairs.py --before-term 202701` exits 1 with `pairs_match_reference` FAIL: 3,297 / 1,314 / 2,153 / 2,785 against the reference 3,216 / 1,329 / 2,178 / 2,829 (deltas +81 / -15 / -25 / -44). The numbers equal dry run 4's field by field, and the deltas are the ones the operator accepted in writing in the D-04 decision. That acceptance is a judgment recorded in the evidence; it does not make the re-measure match. What is established: the -127 named grade rows are 58 graded CRNs absent from the whole-term responses plus 69 on non-allow-listed campuses. What is only consistent-with or inferred: the n >= 60 / 30 / 15 shortfalls come from those rows (the join was not re-run without them), and the headline +81 pairs, +31 courses and +45 multi-term pairs look like a definition artifact of counting 144 n = 0 pairs (a read-only n >= 1 recount gives pairs 3,153 (-63), instructors 1,756 (-40), courses 1,099 (-18), multi-term 1,422 (-17), all shortfalls). That recount is a finding and an inference, not proof; the reference's own basis for courses and multi-term was not re-checked against the 2026-09-28 report's code. Why the 58 CRNs are absent from USF's responses remains unexplained.
2. **The first live worker sweep after the apply has not been observed.** The last recorded sweep (2026-10-02T01:08Z) pre-dates the apply (01:35Z to 01:42Z), and the cadence is 3,600 s. The check is open (see Next Phase Readiness). Nothing here shows that a worker rebuild keeps the 637 instructor_course rows; it is expected because the worker runs the deployed code, but that is not yet verified.
3. **Search payload growth, no threshold in the plan.** The ENC 1101 search page grew from 84,210 to 591,198 bytes (7.0x; 8,398 bytes gzipped) and the default page from 99,363 to 247,681 bytes (2.5x; 5,228 bytes gzipped). The growth is the instructor breakdown now being non-null (every section lists all instructors of its course; ENC 1101 items carry 62 rows each). Recorded for the owner; the browser-side cost of 591 KB uncompressed JSON was not measured, and no pre-apply gzip size exists to compare.
4. **Applied-diff `float_noise` was 0 in the applied before/after diff against the what-if's 3,041, unexplained.** Both are below 1e-9 and affect no score, rank or label beyond that tolerance. A later independent recomputation still sees 3,666 noise rows at max 5.33e-15. Observation only; not explained.
5. **The running commit in each Render container was not independently verified.** The deploy evidence is the operator's statement plus Render's own success reports through GitHub; neither `/health` nor `sync-status` exposes a commit.

## Decisions Made

- The apply was operator-run and executed once; the executor prepared and read back the result only.
- Success criterion 1 is carried as unmet-as-measured but accepted (D-04), not marked met.
- Payload growth is a finding for the owner. No code or threshold was changed.
- No rollback: every required gate passed, and the runbook's rollback commands (`--rollback --rebuild-term 202701 --yes`; a constants revert plus `--rebuild-only`) were recorded for reference only and not run.

## Deviations from Plan

None - plan executed as written. The two blocking-human checkpoints (merge and apply) were handled by the operator as designed, and the executor ran only read-only checks. The one departure worth stating is bookkeeping: no per-plan commit ledger file existed for 10-08, so `plan_head_before` is the merge commit `bcf1dbb` that the continuation started from, and the measured commit count is 2.

## Issues Encountered

- The two unmet or unobserved items above (success criterion 1; first post-apply sweep) are not problems that occurred during the work; they are results that must be read as they are.
- `last_records_failed` is 1 on every sweep (NEB 0001 unapplied, a Phase 9 carry-over); it was noted and left untouched.

## User Setup Required

None - no external service configuration beyond the operator's own actions already completed (push, merge, apply from their shell with their own `DATABASE_URL`).

## Threat Flags

None - no new endpoint, auth path or schema change was introduced by this plan. The only new surface is data already within the reviewed design (instructor-level figures embedded in the search payload). No connection string appears in the evidence, the apply report or this file (negative greps recorded).

## Requirement status

REQ-PROF-01 is declared by this plan but is NOT marked complete here. Plan 10-09 (the deployed-UI check and queued visual UAT) also declares it, so it is not ready to close at the end of this plan; and ROADMAP success criterion 1 is unmet as measured. The completion decision stays with plan 10-09 and the phase verification.

## Next Phase Readiness

- **Plan 10-09** (deployed-UI check with queued visual UAT) can start: the live API now serves ready breakdowns, pinned rows and `lab_section` states for the UI to render.
- **Follow-up to run after the first sweep following the apply** (operator or next session): `sync-status?term=202701` must read `last_status` succeeded and `is_stale` false; `uv run python scripts/report_ranking_diff.py --term 202701` must still exit 0; the `instructor_course` count must still be 637. If any of these fails, record it and stop for the operator; do not roll back unprompted.
- **Owner findings, not blockers:** the search payload growth (7.0x and 2.5x) with no plan threshold and unmeasured browser cost; the unexplained 58 absent graded CRNs; the unexplained `float_noise` difference; the Phase 9 carry-overs WR-03 and NEB 0001 still open.

## Self-Check: PASSED

- `10-ROLLOUT-EVIDENCE.md` and `10-APPLY-REPORT.json` exist; the evidence file carries "## CI, merge and deploy", "## Pre-apply live baseline", "## Apply (D-05)" and "## Post-apply verification" (the Task 1, 2 and 3 automated checks).
- Work commits `a0ee139` and `b12cd3c` exist on `phase-10-post-merge`.

---
*Phase: 10-professor-level-grades*
*Completed: 2026-10-02*
