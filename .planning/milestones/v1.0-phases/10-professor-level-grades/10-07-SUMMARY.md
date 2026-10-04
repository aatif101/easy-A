---
phase: 10-professor-level-grades
plan: 07
subsystem: rollout
tags: [backfill, dry-run, d-04, campus-gate, parse-guard, ranking-diff, rollout-evidence]

requires:
  - phase: 10-professor-level-grades
    provides: "10-02 backfill CLI, 10-03 ranking diff and pair re-measure, 10-06 dry-run what-if, apply, rollback and rebuild-only modes"
provides:
  - "10-ROLLOUT-EVIDENCE.md: pre-merge gates, hosted baseline, code-only parity PASS, lab vocabulary, dry runs 1 to 4, join re-measure, D-04 what-if diff, recorded D-04 decision"
  - "10-WHATIF-DIFF.json: the full dry run 4 what-if (637 changed sections, derived numbers only)"
  - "D-04 decision recorded: approve, with the reference deltas accepted in writing and the campus allow-list kept"
  - "Proposed --expect-inserted 8535 for plan 10-08 (valid only for a rerun with empty guard failures)"
  - "Gap fixes found by running on real data: ranking-diff float tolerance, lost-rows diagnostics, anchor repair, all-campus request with allow-list gate, campus gate before normalising, TBA TBA time cells, row quarantine, response save and replay"
affects: [10-08, 10-09, live-sync-normaliser, historical-instructor-backfill-runbook]

actuals:
  tokens: 69000   # chars/4 over the added lines of src, scripts, tests, docs and phase notes (excludes the 14k-line what-if JSON)
  tasks: 3
  commits: 17     # MEASURED: git rev-list --count 0bb86e4..0819965 (before this close-out commit)

plan_head_before: 0bb86e49c36747ac327830e366da7d9d0e123882
plan_head_after: 0819965   # last work commit before the close-out metadata commit

tech-stack:
  added: []
  patterns:
    - "Opt-in, backfill-only parser parameters (row_gate, quarantine_row_failures) so the live sync keeps its exact behavior"
    - "Fail-closed guards with sanitized, counts-only diagnostics"
    - "Raw responses saved to a git-ignored directory (mode 0600) and replayed offline"

key-files:
  created:
    - .planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md
    - .planning/phases/10-professor-level-grades/10-WHATIF-DIFF.json
    - .planning/phases/10-professor-level-grades/10-GAP-01-TOLERANCE.md
    - .planning/phases/10-professor-level-grades/10-GAP-02-PARSE-DIAGNOSTICS.md
    - .planning/phases/10-professor-level-grades/10-GAP-03-ANCHOR-REPAIR.md
    - .planning/phases/10-professor-level-grades/10-GAP-04-UNMATCHED-CRNS.md
    - .planning/phases/10-professor-level-grades/10-GAP-05-CAMPUS-FIX.md
    - .planning/phases/10-professor-level-grades/10-GAP-06-PARSE-ORDER-TBA.md
    - src/easy_a/sync/parse_diagnostics.py
    - tests/schedule/test_backfill_gap06.py
    - tests/sync/test_anchor_repair.py
    - tests/sync/test_parse_diagnostics.py
    - tests/sync/test_row_gate.py
    - tests/schedule/test_normalize_time.py
  modified:
    - src/easy_a/rankings/diff.py
    - scripts/report_ranking_diff.py
    - src/easy_a/schedule/backfill.py
    - src/easy_a/schedule/backfill_cli.py
    - src/easy_a/schedule/client.py
    - src/easy_a/schedule/normalize.py
    - src/easy_a/sync/fetch.py
    - docs/runbooks/historical-instructor-backfill.md
    - .gitignore

key-decisions:
  - "D-04: approve, with the pairs_match_reference deltas accepted in writing and the allow-list {Tampa, Off-campus - Tampa} kept; the user gave no reason beyond 'approve'"
  - "Approval covers proceeding to plan 10-08 only; it does not authorise the apply, a merge, a push or any live request"
  - "Ranking diff compares scores within SCORE_TOLERANCE 1e-9 (user decision revise-with-tolerance); the stored cache differs from any local recomputation by about 1 ULP, pre-existing and not caused by Phase 10"
  - "The backfill requests every campus (blank P_CAMPUS) and keeps the allow-list {Tampa, Off-campus - Tampa}; the live sync keeps campus=T (D-22(a))"

requirements-completed: [REQ-PROF-01]  # copied from the plan frontmatter; NOT marked complete in REQUIREMENTS.md here (the apply is plan 10-08)

coverage:
  - id: D1
    description: "Code-only parity on hosted data: recomputing 202701 with this branch equals the stored section_rankings within 1e-9 (report_ranking_diff exit 0, course_level_invariant PASS), and the recompute with origin/main code is identical to the branch's for all sections"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "uv run python scripts/report_ranking_diff.py --term 202701 (read-only; exit 0 observed 2026-10-01T16:56:49Z and again before dry runs 2, 3 and 4)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Laboratory vocabulary read from hosted 202701 and from the dry run 4 historical histogram: the only laboratory value is 'Laboratory'; LABORATORY_SECTION_TYPES unchanged, no code or test change"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "10-ROLLOUT-EVIDENCE.md section 'Laboratory vocabulary (D-13)' and dry run 4 'Historical section_type histogram'"
        status: pass
    human_judgment: false
  - id: D3
    description: "A five-term dry run on real USF and hosted data that completes with all guards clear and nothing written (dry run 4: exit 0, guard_failures empty in all terms, before/after row counts identical, would-insert 8,535, course_level_violations 0)"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "uv run python scripts/backfill_historical_sections.py --dry-run --report-json 10-WHATIF-DIFF.json --save-responses <dir> (run once on 2026-10-01T21:08:44Z; exit 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Join re-measure against the 2026-09-28 reference: pairs_match_reference FAILS (n >= 1 -63, n >= 60 -15, n >= 30 -25, n >= 15 -44, named -127; courses +31 and multi-term +45 unexplained); accepted in writing by the operator, not explained"
    requirement: "REQ-PROF-01"
    verification:
      - kind: other
        ref: "10-WHATIF-DIFF.json what_if.pairs.matches_reference = false"
        status: fail
    human_judgment: true
    rationale: "The verdict is a FAIL by definition; the operator accepted the deltas as a D-04 judgment and the unexplained ones stay open follow-ups"
  - id: D5
    description: "Recorded D-04 operator decision (approve) with scope, accepted deltas, kept allow-list, no-authorisation statement and open follow-ups"
    requirement: "REQ-PROF-01"
    verification: []
    human_judgment: true
    rationale: "A blocking-human decision; the evidence is the written record in 10-ROLLOUT-EVIDENCE.md, not an automated check"
  - id: D6
    description: "Offline code fixes found by the live runs (tolerance, diagnostics, anchor repair, all-campus request and gate, campus gate before normalising, TBA TBA, quarantine, save and replay) with unit tests"
    verification:
      - kind: unit
        ref: "uv run pytest -q (1043 passed, 4 skipped, 1 xfailed); ruff check and mypy src clean"
        status: pass
    human_judgment: false

duration: "about 15 h wall clock, mostly waiting on decisions between dry runs (2026-10-01T06:29:06Z to 21:23:24Z)"
completed: 2026-10-01
status: complete
---

# Phase 10 Plan 07: Rollout 1 Summary

**Four five-term dry runs on real USF and hosted data, six gap fixes found along the way, a clean dry run 4 (all guards clear, would-insert 8,535, 637 sections move course to instructor_course, no course-level movement), and the operator's recorded D-04 approval with the reference deltas accepted in writing.**

## Performance

- **Duration:** about 15 h wall clock (waiting on the user between dry runs); active work is a small fraction
- **Started:** 2026-10-01T06:29:06Z
- **Completed:** 2026-10-01T21:23:24Z (D-04 decision recorded)
- **Tasks:** 3 (tracer, dry run, blocking-human decision)
- **Files modified:** 28 in the plan range (about 19,200 lines added, 14,358 of them the what-if JSON)

## Accomplishments

- Task 1 (tracer): local gates green, hosted read-only baseline taken, code-only parity proven (the new code recomputes 202701 exactly as origin/main code does; the 1-ULP gap to the stored cache pre-exists the phase) and the lab vocabulary confirmed. The first exact comparison exited 1, which is how the tolerance gap was found.
- Task 2: the dry run needed four attempts. Dry run 4 completed (exit 0, five all-campus requests, `guard_failures` empty, nothing written, before/after row counts identical): fetched 44,108 rows, 8,662 graded CRNs, 8,604 matched, 58 unmatched (0.67% against a 2% limit), 8,535 would be inserted, 69 graded CRNs excluded because they are scheduled on another campus.
- D-04 what-if on dry run 4: 637 of 3,707 sections change, all `course` to `instructor_course`; `course_level_violations` 0; direction 343 up, 294 down; median absolute delta over the changed sections 0.189; 13 sections move by more than 1.0; largest -2.619 (AMH 2020).
- Task 3: the user chose `approve`; the decision, scope, accepted deltas and open follow-ups are written under "D-04 decision" in 10-ROLLOUT-EVIDENCE.md.

## USF requests made by this plan (whole-term pages and one probe)

| Run | Requests | Result |
|-----|---------:|--------|
| Dry run 1 | 3 | Failed at 202505 with the lost-rows guard |
| Dry run 2 | 5 | `campus=T`; guard `unmatched_fraction` in all five terms; would-insert 7,162 |
| 202505 diagnostic | 1 | Named the dropped row (unterminated anchor) |
| ENC probe | 1 | All-campus request; confirmed the missing CRNs are Tampa-credited rows scheduled under another label |
| Dry run 3 | 5 | All-campus; failed at 202601 on a `TBA TBA` time cell |
| Dry run 4 | 5 | Succeeded |
| **Total** | **20** | Nothing was written to the hosted database in any of them |

The plan's own bound was five requests with a rerun only on "revise"; the user authorised each extra request after a decision. See Deviations.

## Task Commits

1. **Task 1: tracer (gates, baseline, parity, lab vocabulary)** - `2199e03` (docs); parity re-run after the tolerance fix - `9188c6c` (docs)
2. **Task 2: five-term dry run** - evidence commits `6cf0770` (dry run 1), `7c68e04` (dry run 2), `a9eaa4c` (dry run 3), `8967ab1` (dry run 4)
3. **Task 3: D-04 decision** - `0819965` (docs)

Gap fixes and gap notes (each decided by the user before it was made): `cef0d5c` (float tolerance), `967d06c` (lost-rows diagnostics), `7e29a8c` (anchor repair), `2e27db3` (anchor repair and dry run 1 diagnosis note), `0a02903` (unmatched-CRN diagnosis, GAP-04), `0cd1bd1` (ENC probe record), `a49e33a` (all-campus request and allow-list), `097c95a` (campus fix note, GAP-05), `88a1f93` (campus gate before normalising, quarantine, save and replay), `6501f3b` (GAP-06 note and runbook).

**Plan metadata:** the close-out commit (SUMMARY, STATE, ROADMAP) follows this file.

## Files Created/Modified

See the frontmatter `key-files`. Production code changed only in the backfill path, the shared whole-term parse and fetch helpers, the ranking diff and the shared time-range normaliser. `.gitignore` gained the git-ignored `failed-responses/` directory (saved raw pages, mode 0600, never committed).

## Decisions Made

- D-04 approve with the deltas accepted (see the evidence file). The approval covers proceeding to plan 10-08 (merge and operator apply, each with its own gates) and does not itself authorise the apply, a merge, a push or any live request. The user gave no written reason beyond "approve".
- `--expect-inserted 8535` is proposed for plan 10-08 and is valid only for a rerun with empty `guard_failures` on current data.

## Deviations from Plan

Each fix below was made only after a user decision, outside the plan's literal scope (the plan expected one dry run and no code change beyond the lab constant).

**1. [Rule 1 - Bug] Ranking diff compared floats exactly**
- **Found during:** Task 1 (parity). Exit 1 with 3,667 of 3,703 sections differing by at most 5.33e-15, no score source, n, label or rank change.
- **Issue:** the stored cache differs from any local recomputation by about 1 ULP; the exact comparison could never return exit 0. Diagnosis: recompute with origin/main code equals recompute with this branch's code for all 3,703 CRNs, so the gap pre-exists the phase. Its cause (likely the runtime that wrote the cache) is not confirmed.
- **Fix:** user decision "revise-with-tolerance": shared `SCORE_TOLERANCE = 1e-9`, within-tolerance noise reported as `float_noise`.
- **Files:** `src/easy_a/rankings/diff.py`, `scripts/report_ranking_diff.py`, `tests/rankings/test_diff.py`. **Commit:** `cef0d5c`. Note: 10-GAP-01.

**2. [Rule 3 - Blocking] Dry run 1 failed the lost-rows guard at 202505, and the guard was not diagnosable**
- **Issue:** "Parsed 2174 rows from 2175 data rows"; the sanitized output could not name the row. Fix 1: counts-only parse diagnostics plus an opt-in saved response (`967d06c`, note 10-GAP-02). Fix 2: a narrow, offline repair of cut-off anchor tags inside each row block before the guard counts rows (`7e29a8c`, note 10-GAP-03); a 202505 diagnostic request showed the cause (a hand-typed anchor with a non-breaking space and a `</a` that never closes). The guard condition itself is unchanged.
- **Verification:** the saved page parses 2,175 of 2,175 offline; the 2,174 rows that parsed before are identical after. **Commits:** `967d06c`, `7e29a8c`, `2e27db3`.

**3. [Rule 1 - Bug, found by data] Dry run 2: 1,500 graded CRNs absent from the `campus=T` responses (guard `unmatched_fraction` in all five terms)**
- **Issue:** 10% to 39% of graded CRNs missing against a 2% limit; join re-measure 2,788 pairs against 3,216. Diagnosis (10-GAP-04, plus one all-campus ENC probe request): the grade file credits those rows to Tampa, but USF schedules them under other labels (largely `Off-campus - Tampa` and `Off Campus Special Programs`), which a `campus=T` request never returns.
- **Fix:** user decision "implement-campus-fix": the backfill (only) now requests every campus and keeps `{Tampa, Off-campus - Tampa}` via an exact allow-list; the live sync keeps `campus=T`. **Commits:** `0a02903`, `0cd1bd1`, `a49e33a`, `097c95a` (notes 10-GAP-04, 10-GAP-05).

**4. [Rule 1 - Bug] Dry run 3 failed at 202601 on a `TBA TBA` time cell, in a row on an excluded campus**
- **Issue:** the parse normalised every row before the campus gate, and `_parse_time_range` rejected two unscheduled components. Two `Sarasota-Manatee` rows aborted the run before any report existed.
- **Fix:** user decision "fix-both": the campus gate runs before normalisation (opt-in `row_gate`, backfill only); a time cell made only of `TBA`/`ARR` placeholders reads as no time range (SHARED normaliser, so it is live-visible; see follow-ups); rows that fail on an allowed campus are quarantined and make a `row_normalisation_failures` guard fail instead of aborting; `--save-responses` and an offline `--from-saved` replay. **Commits:** `88a1f93`, `6501f3b` (note 10-GAP-06, runbook update).

**5. Request budget exceeded the plan**
- The plan allowed one five-request dry run and no rerun without "revise". The actual total was 20 whole-term and probe requests (table above), each extra run explicitly authorised by the user after a decision. No narrower-query fallback was used (D-22(e)); no run wrote to the hosted database.

**Total deviations:** 5 (6 fixes: tolerance, diagnostics, anchor repair, campus request and gate, gate before normalising with TBA and quarantine, save and replay), all user-decided.
**Impact on plan:** the plan's gates were kept (parity, one-way dry run, rollback to the read-only state, D-04 human decision). Scope grew in the backfill and parser code, with unit tests; no migration and no live write.

## Issues Encountered

- `pairs_match_reference` still FAILS on dry run 4 and was not rerun. The remaining deltas are the operator-accepted ones: n >= 1 -63, n >= 60 -15, n >= 30 -25, n >= 15 -44, named -127 (58 unmatched plus 69 non-allow-listed campus CRNs = 127). Courses +31 and multi-term pairs +45 are unexplained.
- 58 graded CRNs remain unmatched (0.67%); the cause was not established.
- Evidence limits: the `data_row_count`, `tail_error`, bytes and elapsed figures were reported only for failed parses; dry run 4 reports `response_bytes` and `fetch_seconds` per term.

## Open follow-ups (carried, none resolved here)

1. 58 unmatched graded CRNs are unexplained.
2. The courses (+31) and multi-term (+45) deltas are unexplained.
3. Live-term blind spot: the live sync's `campus=T` request cannot see Tampa-credited rows scheduled under another label for Spring 2027 (10-GAP-05 follow-up); needs its own decision.
4. The shared-normaliser `TBA TBA` change (10-GAP-06) is a live-visible change to the live sync; call-out recorded in the gap note.
5. Phase 9 carry-overs WR-03 (cadence-floor race) and NEB 0001 (fails every sweep) are untouched.

## Known Stubs

None. No placeholder data or UI in this plan's changes.

## Threat Flags

None. No new network endpoint, auth path or schema change. The new `--save-responses` option writes raw USF pages to a local git-ignored directory with mode 0600 and never commits or quotes them; it is opt-in and off by default. No connection string or hostname appears in the evidence or the what-if JSON (checked).

## Self-check against 10-07-PLAN.md (non-live checks)

- Evidence headings present: Pre-merge gates, Hosted read-only baseline, Code-only parity (D-03), Laboratory vocabulary (D-13), Five-term dry run (D-07), Row counts before/after, Join re-measure vs 2026-09-28, D-04 what-if diff, D-04 decision: all found.
- No connection string or pooler hostname in 10-ROLLOUT-EVIDENCE.md (0 matches). The only `://` occurrences are the build placeholder (an example URL in the web build command) and prose saying the JSON has no `://`.
- 10-WHATIF-DIFF.json: has `what_if`, `ranking_diff` and `pairs`; 0 occurrences of `://` or the pooler host.
- Gates on the branch after all changes: `uv run ruff check .` passed; `uv run mypy src` no issues in 93 source files; `uv run pytest -q` 1043 passed, 4 skipped, 1 xfailed, 1 warning.
- Hosted row counts identical before and after every dry run (T-10-21).

## User Setup Required

None - no external service configuration required beyond the DATABASE_URL already used from the operator's shell.

## Next Phase Readiness

- Plan 10-08 may start: D-04 is approved. It must merge with green CI, then the operator runs the apply with its own gates. The apply must be preceded by a fresh dry run on current data with empty `guard_failures`; only then is `--expect-inserted 8535` valid. The 58 unmatched, the unexplained deltas and the live-term blind spot stay open.
- REQ-PROF-01 is not complete: the apply and the post-apply verification are plan 10-08, and the UI check is plan 10-09.

## Self-Check: PASSED

- `10-ROLLOUT-EVIDENCE.md`, `10-WHATIF-DIFF.json`, `10-GAP-01` through `10-GAP-06`, `parse_diagnostics.py`, and the new test files exist.
- Commits `cef0d5c`, `967d06c`, `7e29a8c`, `2e27db3`, `0a02903`, `0cd1bd1`, `a49e33a`, `097c95a`, `88a1f93`, `6501f3b`, `8967ab1` and `0819965` are present in the log.

---
*Phase: 10-professor-level-grades*
*Completed: 2026-10-01*
