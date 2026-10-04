---
phase: 10-professor-level-grades
verified: 2026-10-02T02:29:35Z
status: gaps_found
score: 11/15 must-haves verified
covered_files:
  - .planning/phases/10-professor-level-grades/10-01-PLAN.md
  - .planning/phases/10-professor-level-grades/10-01-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-02-PLAN.md
  - .planning/phases/10-professor-level-grades/10-02-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-03-PLAN.md
  - .planning/phases/10-professor-level-grades/10-03-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-04-PLAN.md
  - .planning/phases/10-professor-level-grades/10-04-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-05-PLAN.md
  - .planning/phases/10-professor-level-grades/10-05-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-06-PLAN.md
  - .planning/phases/10-professor-level-grades/10-06-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-07-PLAN.md
  - .planning/phases/10-professor-level-grades/10-07-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-08-PLAN.md
  - .planning/phases/10-professor-level-grades/10-08-SUMMARY.md
  - .planning/phases/10-professor-level-grades/10-09-PLAN.md
  - .planning/phases/10-professor-level-grades/10-09-SUMMARY.md
  - src/easy_a/analytics/pair_coverage.py
  - src/easy_a/analytics/queries.py
  - src/easy_a/analytics/scoring.py
  - src/easy_a/common/section_types.py
  - src/easy_a/rankings/cache.py
  - src/easy_a/rankings/diff.py
  - src/easy_a/rankings/models.py
  - src/easy_a/rankings/service.py
  - src/easy_a/schedule/backfill.py
  - src/easy_a/schedule/backfill_cli.py
  - src/easy_a/sync/fetch.py
  - web/src/components/InstructorBreakdown.tsx
  - web/src/components/RankingDetails.tsx
  - web/src/types/rankings.ts
  - web/src/utils/rankings.ts
covered_digest: "v2:sha256:5198a9a66b384c6f435c9fda5a23c67d9ad68533a927e5e8308b6381aef57b62"
behavior_unverified: 1
overrides_applied: 0
# Evidence note (sourced from 10-ROLLOUT-EVIDENCE.md "Unmatched graded CRNs"; not part of the owner's reason):
# the 58 graded CRNs absent from USF's whole-term responses are, by grade suffix, C 36, L 10, D 8, S 3, O 1 (not all labs).
# accepted_at below: the owner's reply was dated 2026-10-03; the time of day was not recorded, 00:00:00Z is a format placeholder.
overrides:
  - must_have: "ROADMAP success criterion 1: historical join coverage re-measured against the DB matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829 at n >= 60 / 30 / 15)"
    reason: "i don't think this really is a problem at all. labs are really hard to get the distritbution out of and i get the other supervised teaching types as well. i think we can clsoe the phase then? cause honeslty i dont see a problem."
    accepted_by: "aatif101"
    accepted_at: "2026-10-03T00:00:00Z"
gaps:
  - truth: "ROADMAP success criterion 1: historical join coverage re-measured against the DB matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829 at n >= 60 / 30 / 15)"
    status: failed
    reason: "Measured 3,297 / 1,314 / 2,153 / 2,785 (pairs_match_reference FAIL, verified in 10-WHATIF-DIFF.json what_if.pairs.matches_reference = false and in the post-apply re-measure). The D-04 'approve' accepted the deltas to authorise the apply; it did not change the criterion text, was not recorded as an override, and carried no reason in the operator's own words. Three of the deltas (58 absent graded CRNs, courses +31, multi-term +45) were accepted as unexplained."
    artifacts:
      - path: ".planning/ROADMAP.md"
        issue: "Phase 10 success criterion 1 still states exact-match numbers that the live data does not meet"
      - path: "src/easy_a/analytics/pair_coverage.py"
        issue: "matches_reference requires pairs_total, n_ge_60, n_ge_30 and n_ge_15 to equal the reference exactly; pairs_total includes 144 n = 0 pairs while the reference 3,216 equals its own n >= 1"
    missing:
      - "Either an explicit owner override of criterion 1 in this file's frontmatter (accepted_by / accepted_at, with a reason), or an amendment of the ROADMAP criterion to a basis the phase scope can meet (Tampa + Off-campus - Tampa allow-list; n >= 1 like-for-like; stated tolerance)"
      - "Explanation or explicit non-explanation of the 58 graded CRNs absent from the whole-term responses (202508: 24, 202601: 34)"
  - truth: "The instructor panel never states that instructor-level history is absent when history is recorded (core value; D-06/D-07 explicit-state honesty)"
    status: partial
    reason: "P10-WR-01 confirmed in source: web/src/components/InstructorBreakdown.tsx line 135 computes isEmpty = !named && breakdown.instructors.length === 0, ignoring other_instructor_count. The backend (queries.py lines 150-173) returns status ready with instructors=() and other_instructor_count=N when every instructor with history is under the 15-grade collapse cutoff and no current instructor is pinned. The UI then renders 'No instructor-level grade history is recorded for this course.' directly above 'N other instructors with under 15 grades each'. No test covers this state (the only empty-state test uses no_instructor_history with other_instructor_count 0). This is in the deployed bundle (bcf1dbb). How many live Staff sections are in this state was not recorded anywhere and could not be measured here (read-only, no live requests)."
    artifacts:
      - path: "web/src/components/InstructorBreakdown.tsx"
        issue: "isEmpty ignores other_instructor_count; EMPTY_NOTE can render beside the Others line"
      - path: "web/src/components/InstructorBreakdown.test.tsx"
        issue: "No test for !named && instructors=[] && other_instructor_count > 0"
    missing:
      - "Gate the empty note on other_instructor_count === 0 (or use different wording), render the Others line under the 'Historically taught by' heading in that state, and add the test"
      - "Count the live sections in this state from the public search API"
deferred: []
behavior_unverified_items:
  - truth: "A live worker sweep after the apply keeps the 8,535 backfilled historical sections, their instructor rows and removed_at untouched, and a worker cache rebuild keeps the 637 instructor_course scores"
    test: "After the first worker sweep that runs after 2026-10-02T01:42Z (cadence 3,600 s), read GET /api/v1/metadata/sync-status?term=202701, run report_ranking_diff.py --term 202701, and count 202701 section_rankings rows with score_source instructor_course"
    expected: "sync-status last_status succeeded and not stale; report_ranking_diff exit 0; instructor_course count still 637 (plus or minus normal sweep drift, explained); 0 historical sections with removed_at set"
    why_human: "The last recorded sweep (01:08Z) pre-dates the apply (01:35Z to 01:42Z). The invariant is covered by a unit test (tests/schedule/test_backfill.py::test_backfilled_history_survives_a_live_sweep_untouched) but has never been observed on the live worker, and the evidence cannot show the running worker container's commit (neither /health nor sync-status exposes it)."
coincidental_reliance_items: []
human_verification:
  - test: "UAT 1: named-instructor block, desktop and 320 px. Open https://easy-a-web.onrender.com, term Spring 2027, search PSY 2012, expand CRN 12188 (also 12189, 12193, 12194, 12195). Then CNT 4419 CRN 14250 (also 14251)."
    expected: "'Instructors for this course' directly under the course-wide figures; the current instructor first, highlighted, labelled 'This section', with 'Used in this section's score'; rows read '{pct}% A, {n} grades, {k} terms ({first}-{last})' and Easiness or 'Not scored' over 'Under 30 grades'; the PSY 2012 pinned row shows the 'Based on 1 term' chip (term_count 1, 202508 only). CNT 4419 shows no highlighted row (current instructor has no history; designed state)."
    why_human: "Layout, highlight and copy placement in a real browser; never observed (queued, not passed)."
  - test: "UAT 2: Staff section. Expand IDH 4950 CRN 12497 (also 12498 to 12503, 12505)."
    expected: "Heading 'Historically taught by', the Staff explainer saying the instructors do not affect this section's score, no highlighted row, nothing saying 'Used in this section's score', 14 rows plus a 1-instructor Others line."
    why_human: "Visual and copy check; never observed."
  - test: "UAT 3: lab and fallback sections. Expand CHM 2045L CRN 11528 (also 11529, 11530; CHM 2211L CRN 11287). Expand SYG 3235 CRN 20075 (subject source) and CHD 4537 CRN 13112 (global source; CLT 3511 CRN 20322 is another)."
    expected: "Lab: only the dashed note 'Instructor history is not shown for lab sections. The figures above are course-wide.' with no heading and no rows. Fallback sections: no instructor block at all."
    why_human: "Visual check; never observed."
  - test: "UAT 4: more than five instructors. Expand ENC 1101 CRN 14045 (41 sections; also 14114, 14124). Expand ANT 4930 CRN 10805 and BSC 4933 CRN 18286 for the Others line."
    expected: "ENC 1101: at most five rows visible, 'Show all 62 instructors' opens with Enter and Space and shows a focus ring (no Others line can appear: other_instructor_count is 0 on all 41 ENC 1101 sections, finding A). ANT 4930 (6 rows, others 4) and BSC 4933 (10 rows, others 9): the Others line shows counts only ('N other instructors with under 15 grades each')."
    why_human: "Keyboard operation, focus ring and disclosure behaviour in a browser; never observed. The plan's original ENC 1101 Others-line expectation cannot be met, so the check was moved to ANT 4930 and BSC 4933."
  - test: "UAT 5 (backstop, UI-SPEC long-text 1): at 320 px open CRW 3312 CRN 13723 (18-character name, visible as the pinned row) and IDH 4950 CRN 12497 (18-character name, row 13 of 14, inside 'Show all 14 instructors'). For the 40-character case, edit a name text node in the browser developer tools or use a mock-data build."
    expected: "The name wraps onto further lines with no ellipsis, clipping or horizontal scroll (break-words is on the name span in source and appears 9 times in the deployed bundle)."
    why_human: "The 40-character held-out check CANNOT be run with live data: the longest listed instructor name across all 3,707 live items is 18 characters. A pass with an 18-character name must not be recorded as the 40-character result; only an edited text node or a mock build exercises it. This backstop is only partly coverable live."
  - test: "UAT 6 (backstop, UI-SPEC long-text 2): at 320 px focus or hover the 'i' InfoTip in the block on PSY 2012 CRN 12188."
    expected: "The full co-teaching caveat ('USF lists one instructor per section; co-taught courses are attributed to the listed instructor.') appears without clipping off-screen. Source shows the tooltip is w-64 and right-anchored (InfoTip.tsx), so a 256 px tooltip must fit left of the icon inside a 320 px viewport."
    why_human: "Clipping depends on rendered geometry; never observed."
  - test: "UAT 7 (new, from P10-WR-01): scan the public search API for 202701 items with instructor_breakdown.status ready, instructors empty, other_instructor_count > 0 and a Staff or unnamed section; open one in the UI."
    expected: "Count recorded. If any exist, the page currently shows 'No instructor-level grade history is recorded for this course.' above 'N other instructors with under 15 grades each' (a contradictory statement on the live site until WR-01 is fixed)."
    why_human: "Needs live requests, which this verification was forbidden to make; the count is the missing fact that sets the severity."
  - test: "Post-apply live sweep (see behavior_unverified_items): after the first worker sweep following the apply, repeat sync-status, report_ranking_diff and the instructor_course count."
    expected: "succeeded and not stale; exit 0; instructor_course 637 (drift explained); 0 removed historical sections."
    why_human: "Not observed; needs the live worker and hosted DB."
  - test: "Owner decision on ROADMAP success criterion 1: record an override in this file's frontmatter, or amend the criterion, or close the gap by other means."
    expected: "A written decision with accepted_by, accepted_at and a reason in the owner's own words (the D-04 approval recorded none)."
    why_human: "Only the owner can accept a deviation from the roadmap contract."
---

# Phase 10: Professor-level grades - Verification Report

**Phase Goal:** Show a named instructor's own grade history for a course, next to the course-wide history, wherever the evidence supports it.
**Verified:** 2026-10-02T02:29:35Z
**Status:** gaps_found
**Re-verification:** No - initial verification (no prior 10-VERIFICATION.md)

## Verdict in one paragraph

The mechanism works and is live: the D-24 retune is in source, 8,535 historical sections were backfilled exactly as dry run 4 predicted, 637 sections of 202701 now score `instructor_course`, the breakdown is served for 3,049 sections, no course-level, subject-level or global score moved, and search p95 is 273.10 ms against the 1,500 ms bar. The goal is substantially achieved. It is not fully achieved on the roadmap's own terms, for two reasons. First, ROADMAP success criterion 1 is FAILED as measured and no override exists; the D-04 approval authorised the rollout but did not make the criterion true (see "Success criterion 1" below). Second, one live-UI defect (P10-WR-01) makes the instructor panel state a falsehood in a reachable state, which breaks the project's core value. Everything visual is unobserved. Status is therefore `gaps_found`, with a human_verification section that still has to be worked.

I made no live requests and no database connection. DB-side figures below come from `10-ROLLOUT-EVIDENCE.md` (read-only transactions recorded by the executors) and from the two tracked JSON files, which I parsed locally. Where a number could only come from the evidence file, I say so.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1: join re-measure matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829) | ✗ FAILED | `10-WHATIF-DIFF.json` `what_if.pairs`: pairs_total 3,297, n_ge_60 1,314, n_ge_30 2,153, n_ge_15 2,785, `matches_reference` false, `verdicts.pairs_match_reference` "FAIL". Post-apply re-measure in the evidence file is identical field by field. No override in frontmatter. |
| 2 | SC2: every instructor-level figure shows its denominator, term count and source (D-06, D-07) | ✓ VERIFIED | `InstructorBreakdown.tsx`: each row renders `{pct}% A`, `formatGradeCount(effective_n)`, `formatTermCount` and `formatTermRange`; unscored rows show "Not scored / Under N grades" with N from the API; a block-level SOURCE_LINE names the source; API provenance is `grade_distributions+section_instructors`, freshness `historical`. `RecencyConfig.enabled` is False, so `effective_n` equals the raw grade count (live CNT 4419 values 203 / 175 / 109 / 44 match the research's raw n). Caveats: source is stated once per block, not per figure, and carries no date (the term range per row stands in for it); rendering is covered by jsdom tests and bundle strings, not a browser. |
| 3 | Goal: a named instructor's own history appears next to course-wide history where evidence supports it | ✓ VERIFIED | `RankingDetails.tsx` imports and renders `InstructorBreakdown` from `historical_analytics.instructor_breakdown`; live API serves 2,506 `ready`, 540 `lab_section`, 3 `no_instructor_history`, 658 null (= the 658 D-21 exceptions); PSY 2012 probe shows a pinned current-instructor row with n, terms and score equal to the section's; the deployed bundle contains the three required copy strings. |
| 4 | D-24 retune: min effective_n 30, `instructor_prior_strength` 30, withdrawal prior unchanged, single-term flag label-only | ✓ VERIFIED | `scoring.py`: `DEFAULT_INSTRUCTOR_PRIOR_STRENGTH = 30.0`, `DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N = 30.0`, `DEFAULT_GRADE_PRIOR_STRENGTH` still 60; instructor strength applies only when `score_source is ScoreSource.instructor_course`; withdrawal strength unchanged. PROJECT.md D-24 reads approved 2026-09-30; README "Instructor-course history" documents it. I ran `pytest tests/analytics/test_instructor_retune.py tests/rankings` (112 passed). 637 sections now `instructor_course` (apply report: transitions `course->instructor_course` 637). |
| 5 | Course, subject and global scores are unchanged by the retune and the backfill (D-03) | ✓ VERIFIED | `10-APPLY-REPORT.json` `applied`: `course_level_invariant` true, `course_level_violations` [], changed 637 all `course->instructor_course`, `subject` 325 and `global` 49 unchanged. Code-only parity: origin/main-code and branch-code recomputations differ for 0 of 3,703 CRNs. Note: stored cache vs any local recompute differs by up to 5.33e-15 (1 ULP) on ~3,670 rows; this pre-dates the phase (shown with origin/main code), is covered by the declared 1e-9 `SCORE_TOLERANCE`, and its cause is NOT established. So "identical" holds within tolerance against the live cache and exactly between code versions. |
| 6 | Laboratory sections are excluded from instructor stats and labelled (D-13) | ✓ VERIFIED | `queries.py` applies `is_laboratory_section_type` at lines 320, 442, 560, 586-589 and 800-822 (both the per-course and whole-term paths); `LABORATORY_SECTION_TYPES = frozenset({"laboratory"})`, confirmed against hosted vocabulary in the evidence (only value `Laboratory`). Live: 540 `lab_section` breakdowns; CHM 2045L probe returns 40 items, all `course` with 0 instructor rows. 9 of the 637 `instructor_course` rows carry an L suffix in the course number, which is not a contradiction (suffix is not section_type) but was not individually checked. |
| 7 | Backfill landed exactly as reviewed (D-05, D-06, D-07) | ✓ VERIFIED | `10-APPLY-REPORT.json`: status succeeded, mode apply, written true, `expect_inserted` 8,535 = 8,535 matched, gate_failures [], `guard_failures` [] and `row_normalisation_failures` 0 in all five terms; per-term inserted 179 / 2,090 / 448 / 2,840 / 2,978 (sum 8,535) equal dry run 4. Hosted post-apply counts (8,535 sections, 8,535 instructor rows, one distinct source `usf_schedule_backfill`) are from the evidence file only; I could not re-read the DB. Idempotent re-run was unit-tested only (fake client, SQLite), never run live. |
| 8 | Historical rows are inert: no seat snapshots, no `removed_at`, not in the cache | ✓ VERIFIED | Evidence file (read-only hosted queries): 0 seat_snapshots and 0 non-null `removed_at` on historical sections; `section_rankings` for historical terms 0; whole-table totals reconcile (12,351 = 3,816 + 8,535; seat_snapshots unchanged 4,377). Not independently re-read by me. |
| 9 | Breakdown and section score cannot disagree (shared `_instructor_course_stats`) | ✓ VERIFIED | Source: `build_instructor_breakdown` calls the same `_instructor_course_stats` that scores a section. Live (evidence): over the 637 `instructor_course` rows, 637/637 `ready` with one `is_current` row, scored, easiness equal within 5.33e-15 (inside 1e-9) and effective_n equal; 0 violations. |
| 10 | Staff, blank and ambiguous sections: list is display-only and never feeds the score (D-08, D-11) | ✓ VERIFIED | Source: `current = current_instructor if is_usable_instructor(...) else None`; UI shows "Historically taught by", the Staff explainer and no pinned row when not named; vitest "Staff section: ... no score claim" passes. Live IDH 4950 CRN 12497 is `course`-scored with 14 rows and no `is_current` row. Rendering not observed in a browser. |
| 11 | The panel never says history is absent when history is recorded | ✗ FAILED (partial) | P10-WR-01, confirmed in source (see gap above). Reachable, deployed, untested; live prevalence unknown. |
| 12 | Cache equals a fresh recomputation after the apply | ✓ VERIFIED | Evidence: `report_ranking_diff.py --term 202701` exit 0 at 2026-10-02T01:57:17Z, identical PASS, course_level_invariant PASS, changed 0 beyond 1e-9. The applied diff matches the reviewed what-if for all 637 changes, ranks, effective_n and top 50 (I checked `changed` 637, transitions, `expect_inserted`, `rows_rebuilt` 3,707 in the JSON). Unexplained observation carried: the applied before/after diff reports float_noise 0 while a later recompute reports 3,666 noise rows (max 5.33e-15); no score, rank or label beyond 1e-9 is affected. |
| 13 | REQ-PERF-01 not regressed (search p95 under ~1.5 s at full coverage) | ✓ VERIFIED (with caveats) | Evidence: hosted single-client benchmark, 50 calls after 5 warmups, p50 129.98 ms, **p95 273.10 ms**, max 435.95 ms at 3,707 sections; baseline p95 212.56 ms (+28%). Under the bar by 5.5x. See "Performance and payload" below for what is and is not covered. |
| 14 | A live sweep after the apply leaves the backfill and the 637 scores intact | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Unit test exists and passes in the suite (`test_backfilled_history_survives_a_live_sweep_untouched`); the live worker has not run since the apply; the running worker's commit is not independently readable. Routed to human verification. |
| 15 | UI-SPEC visual checks, including both held-out backstops, pass on the deployed UI | ? UNCERTAIN | Six checks queued, none observed. The 40-character backstop cannot be exercised by live data (longest live name 18 characters). |

**Score:** 11/15 truths verified (1 present, behavior-unverified; 1 uncertain; 2 failed)

### Success criterion 1: unmet as measured, and what the D-04 acceptance does and does not do

Numbers (from `10-WHATIF-DIFF.json`, re-confirmed after the apply in the evidence file):

| Measure | Measured | Reference | Delta |
|---------|---------:|----------:|------:|
| pairs (`pairs_total`, includes 144 pairs with n = 0) | 3,297 | 3,216 | +81 |
| pairs, n >= 1 (like-for-like with the reference's own n >= 1) | 3,153 | 3,216 | -63 |
| n >= 60 | 1,314 | 1,329 | -15 |
| n >= 30 | 2,153 | 2,178 | -25 |
| n >= 15 | 2,785 | 2,829 | -44 |
| grade rows named | 8,534 | 8,661 | -127 |

Every criterion number misses on a like-for-like basis, so the criterion is not met under either reading of "pairs". It is not a near-match that rounding or definition could rescue.

What is established: the -127 named rows are exactly 58 graded CRNs absent from the whole-term USF responses plus 69 graded CRNs scheduled on a campus outside the allow-list `{Tampa, Off-campus - Tampa}` (58 + 69 = 127; both are in the per-term fields of the JSON). The reference was built from an unfiltered pull (research doc: 27,273 sections, 8,661 of 8,662 grade rows matched) while the phase deliberately writes only allow-listed campuses, so the phase's own scope choice guarantees a shortfall against that reference.

What is not established: why 58 graded CRNs are absent; the cause of the n-threshold shortfalls beyond "consistent with the 127 missing rows" (no re-join without them was run); and the +31 courses / +45 multi-term deltas, which D-04 accepted as unexplained. The later n >= 1 recount (instructors 1,756, courses 1,099, multi-term 1,422) that would explain them is in the evidence file only; I could not reproduce it without the DB, and it is an inference that depends on the reference's counting basis, which was not re-checked.

Does acceptance in writing satisfy the criterion? **No, it leaves a gap.** Reasons:

1. The D-04 decision was a go/no-go on the apply, scoped by its own text ("it lets plan 10-08 start"); it never states that criterion 1 is satisfied or amended. The ROADMAP criterion text is unchanged and still demands an exact match.
2. The record shows the operator replied only "approve"; "no written reason was given and none is inferred". The listed deltas were written up by the executor.
3. The acceptance explicitly covered only the dry run 4 numbers. The post-apply numbers are identical, so that scope held, but the approval says a different run would need a new look.
4. The GSD override mechanism requires `accepted_by` / `accepted_at` / a reason against a named must-have; none exists.

What acceptance does establish: the shortfall is a known, documented, owner-reviewed deviation introduced by a scope decision, not a regression or an undetected defect, and the apply it authorised was correct to run. This looks intentional, so the owner can close it in one of two ways.

**Suggested override (not applied; only the owner can accept):**

```yaml
overrides:
  - must_have: "Historical join coverage re-measured against the DB matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829 at n >= 60 / 30 / 15)"
    reason: "Allow-list {Tampa, Off-campus - Tampa} excludes 69 graded CRNs by design and 58 graded CRNs are absent from USF's whole-term responses; measured 3,153 (n>=1) / 1,314 / 2,153 / 2,785, n-thresholds within 1.6% of reference; course-level scores unchanged"
    accepted_by: "<owner>"
    accepted_at: "<ISO timestamp>"
```

The alternative is to amend the ROADMAP criterion to a tolerance or a Tampa-scoped, n >= 1 basis. Either way, the 58 absent CRNs should be recorded as an explicit open item rather than left as "unexplained".

### Performance and payload (REQ-PERF-01)

REQ-PERF-01 (already ticked from Phase 07) requires p95 under about 1.5 s against Supabase at full coverage with scoring and API contract unchanged. Phase 10 evidence: p95 273.10 ms (single client, 50 calls, public HTTPS from one workstation). That clears the bar with margin, so the requirement is not regressed.

What the number does not cover, stated plainly:

- **Payload growth is real and has no threshold.** ENC 1101 search page 84,210 to 591,198 bytes (7.02x; 41 items, each carrying a 62-row breakdown of about 13,500 bytes); default page (limit 50, which is the UI's `PAGE_SIZE`) 99,363 to 247,681 bytes (2.49x). With gzip the same pages are 8,398 and 5,228 bytes, so transfer cost is small, but no pre-apply compressed size was recorded. Browser parse and render cost of a 591 KB JSON for a 41-section course was not measured. The API allows `limit` up to 200 (`rankings.py`), so a worst-case page can be several times larger than the measured ones; the evidence read 20 pages of 200 items totalling about 13 MB, about 650 KB per page on average.
- **p95 rose 28% and max rose 64 ms while the median is flat.** The evidence attributes this to nothing; one run cannot separate payload from network variance.
- **The acceptance clause "API contract unchanged" no longer holds literally.** `historical_analytics` gained an additive `instructor_breakdown` key (null for 658 sections). It is additive and the old cache rows load as null, so I treat it as a deliberate, documented extension, not a regression.
- **Browser and concurrent-user latency remain unmeasured**, as they were for Phase 07 and Phase 09.

Verdict: no gap against REQ-PERF-01 as written; a measurement gap and a design decision (every section lists every instructor of its course) is recorded for the owner. If search pages ever feel slow in the UI, the breakdown payload is the first suspect.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/easy_a/analytics/scoring.py` | D-24 constants and instructor prior | ✓ VERIFIED | Defaults and branch on `ScoreSource.instructor_course` read directly |
| `src/easy_a/common/section_types.py` | Single home of the Laboratory rule | ✓ VERIFIED | Imported in `queries.py` at 3 call sites plus helper paths |
| `src/easy_a/analytics/queries.py` | Breakdown builder, lab rule in both paths | ✓ VERIFIED | `build_instructor_breakdown` lines ~95-190; shared stats |
| `src/easy_a/rankings/{models,service,cache}.py` | Breakdown embedded in `historical_analytics`, no migration | ✓ VERIFIED | `InstructorBreakdown` model, service and cache pass `instructor_breakdown`; Alembic head unchanged `0004_sync_removed_at` (evidence) |
| `src/easy_a/schedule/backfill.py`, `backfill_cli.py`, `scripts/backfill_historical_sections.py` | One-off backfill with dry-run, apply, rollback, rebuild-only | ✓ VERIFIED | Ran live once (apply report), dry runs recorded; see WR-02..WR-04 below |
| `src/easy_a/rankings/diff.py`, `scripts/report_ranking_diff.py`, `scripts/measure_instructor_pairs.py`, `src/easy_a/analytics/pair_coverage.py` | D-04 diff and join re-measure | ✓ VERIFIED | Ran; the re-measure produced the SC1 FAIL |
| `web/src/components/InstructorBreakdown.tsx` | All states, locked copy | ⚠️ DEFECT | Wired into `RankingDetails` and deployed; WR-01 empty-state defect |
| `web/src/{types,utils}/rankings.ts` | Types and formatters | ✓ VERIFIED | `formatGradeCount`, `formatTermCount`, `formatTermRange`, `isNamedInstructor` read |
| `docs/runbooks/historical-instructor-backfill.md` | Operator runbook | ✓ EXISTS | Used for the real apply; WR-04 notes it contradicts the tracked reports |
| `10-APPLY-REPORT.json`, `10-WHATIF-DIFF.json` | Evidence | ✓ VERIFIED | Valid JSON; 0 hits for `://`, `supabase`, `pooler`, `postgres` or `/home/`; no instructor-name keys |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `RankingDetails.tsx` | `InstructorBreakdown.tsx` | import and render with `ranking.historical_analytics.instructor_breakdown` | WIRED | lines 11, 17, 42 |
| `rankings/service.py`, `cache.py` | `analytics/queries.py` | `analytics_row.instructor_breakdown` passed into the model | WIRED | service.py line 83, cache.py line 173 |
| `queries.py` breakdown | `scoring.py` stats | shared `_instructor_course_stats` | WIRED | invariant 637/637 live |
| backfill apply | cache rebuild | same transaction under the sweep lock, `--rebuild-term` | WIRED | apply report `rows_rebuilt` 3,707 = `total_before` |
| deployed web bundle | live API | compiled-in `easy-a-api.onrender.com` | WIRED | placeholder host count 0 (evidence) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `InstructorBreakdown.tsx` rows | `breakdown.instructors` | `section_rankings.historical_analytics` JSON from `build_instructor_breakdown` over backfilled `section_instructors` + `grade_distributions` | Yes: 2,506 ready breakdowns with real counts (PSY 2012 14 rows, CNT 4419 4 rows) | ✓ FLOWING |
| Others line | `other_instructor_count` | same builder | Yes (623 ready sections have > 0) | ✓ FLOWING (but see WR-01) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frontend suite incl. InstructorBreakdown tests | `npm --prefix web test -- --run` | 9 files, 118 tests passed | ✓ PASS |
| Retune and rankings tests | `uv run --offline pytest -q tests/analytics/test_instructor_retune.py tests/rankings` | 112 passed | ✓ PASS |
| Sync, schedule and analytics regression (Phase 9 shared code) | `uv run --offline pytest -q tests/sync tests/schedule tests/analytics` | 546 passed, 1 skipped, 1 xfailed | ✓ PASS |
| Empty-state defect reproduced by reading source | `InstructorBreakdown.tsx` line 135 vs `queries.py` lines 150-173 and absence of a covering test | defect present | ✗ FAIL (WR-01) |
| Live API probes, DB queries, sweep | not run | read-only verification, no live requests | ? SKIP (human) |

I did not run `mypy`, `ruff` or the full workspace suite; the evidence file records ruff, mypy, 843 then 1,043 Python tests and the web gates passing before merge, and CI green on PR #37 and on main.

### Probe Execution

No `scripts/*/tests/probe-*.sh` and no probe declared by any PLAN or SUMMARY. SKIPPED (none declared).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-PROF-01 | 10-01 through 10-09 (all nine declare it) | A named instructor's own grade history for a course is shown next to the course-wide history wherever evidence supports it; backfill for five terms; denominator, term count and source on every figure; labs and co-teaching labelled; scoring change only via D-24 | ⚠️ PARTIAL, not satisfied yet | Backfill 8,535 / five terms done; figures show denominator, term count, source (SC2); labs labelled (540); co-teaching InfoTip text in bundle; D-24 approved and applied. Blocked by SC1 FAILED (no override), WR-01, and unobserved UI. REQUIREMENTS.md correctly leaves the checkbox unticked; it must stay unticked until the gaps close. |

Orphan check: REQUIREMENTS.md maps only REQ-PROF-01 to Phase 10 (line 234 section); no orphaned IDs. REQ-PERF-01 is a regression constraint, not a Phase 10 requirement (see above).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (phase-modified source files) | - | `TBD` / `FIXME` / `XXX` | none found | Grep over all 21 source files returned no matches. The only `PLACEHOLDER` hits are `PLACEHOLDER_TIME_TOKENS` and `SHAPE_PLACEHOLDER` in `normalize.py`, which are legitimate identifiers. |
| `web/src/components/InstructorBreakdown.tsx` | 135, 157-158, 187-193 | Empty-state ignores `other_instructor_count` (P10-WR-01) | 🛑 Blocker-class defect (counted in the gaps), live | False statement beside contradicting line |
| `src/easy_a/schedule/backfill_cli.py` | 396-398, 520, 608, 836, 1071-1074 | DB error text echoed to stdout and `--report-json` (P10-WR-02) | ⚠️ Warning | Did not bite: tracked reports and the evidence file contain no host, role or URL (grep above). Latent for the next operator run. |
| `src/easy_a/schedule/backfill_cli.py` | 154-163, 579, 594-600, 743-749 | `--apply` gate vacuous for a wrong `--rebuild-term` (P10-WR-03) | ⚠️ Warning | Did not bite in the one live apply: `rows_rebuilt` 3,707 equals `total_before` 3,707. Latent for any re-run, `--rollback` or `--rebuild-only`. |
| `src/easy_a/schedule/backfill_cli.py` | 1061-1075 | `--report-json` written unguarded after commit, no path rule (P10-WR-04) | ⚠️ Warning | The two reports are tracked in git (about 430 KB each, per-CRN numbers, no names) while the runbook says never to commit reports; doc/behaviour mismatch. Verified derived-only. |
| `scripts/report_ranking_diff.py`, `scripts/measure_instructor_pairs.py` | 147-155, 114-129 | Any `SQLAlchemyError` reported as "NOT MEASURED"; config errors exit 1 (P10-WR-05) | ⚠️ Warning | Exit 1 means "difference found" for the diff tool, so a crash is indistinguishable by exit code. Did not bite in recorded runs. |

### Open review warnings (10-REVIEW.md, 10-REVIEW-DISPOSITION.md)

All 12 findings are still `open`; none has been triaged, fixed or dismissed. Five are Warnings; zero Critical. I read each against source or evidence:

- **P10-WR-01 (live UI, user-visible): confirmed, counted as a gap above.** It is the only one that contradicts the product's core value on the live site today. It is a small fix with a test. I recommend closing it before UAT item 2 and 7, because UAT on a Staff section could otherwise record a pass over a defective state.
- **P10-WR-02, WR-03, WR-04, WR-05: confirmed as latent operator-tooling defects, none triggered by the recorded live runs.** They matter if the backfill CLI is ever re-run (rollback, a second apply, or a new term). They do not affect the served data. Recommended triage: fix WR-03 and WR-02 before any re-run; WR-04 and WR-05 can be documented.
- Info items IN-01 to IN-07 are doc/robustness notes. IN-05 (unbounded `IN (...)` lists, about 13% of the psycopg3 parameter limit at 8,662 grade rows) is a scaling hazard as more terms are imported.

### Items I could not close and the honest limits of this verification

- **The 40-character name-wrap backstop** (UI-SPEC long-text row 1) cannot be exercised by live data. The longest listed name across all 3,707 live items is 18 characters. `break-words` is on the name span in source and in the bundle (9 occurrences), but that is presence, not behaviour. It needs an edited text node or a mock-data build, and the verifier will not accept a pass on an 18-character name as the 40-character result. Counted inside truth 15.
- **No browser was driven by anyone.** The evidence "Deployed UI" check is a bundle grep plus API reads; it proves the copy is shipped and the data exists, not that anything lays out correctly.
- **The first live sweep after the apply was not observed** (truth 14).
- **Render deploy of `bcf1dbb`** is corroborated by GitHub deployment status, not by reading the running containers (neither `/health` nor sync-status exposes a commit).
- **Dating note:** the evidence timestamps the apply and post-apply checks as 2026-10-02 UTC while the PR merge is 2026-10-01T21:33Z; consistent. ROADMAP says "Live 2026-10-02"; that is UTC.
- **Live-term blind spot (Info, outside this phase's scope):** the live sync still requests `campus=T`, so Spring 2027 sections scheduled under `Off-campus - Tampa` are not in search and can never display instructor history, although their historical rows are now in the DB. Recorded in 10-GAP-05 and D-04 follow-up 3; not resolved.
- **Request volume:** D-22(e) names a one-time five-term backfill. The record shows four dry runs (3 + 5 + 5 + 5 whole-term requests, per the evidence) plus the five-request apply, each authorised by the user and spaced 30 s apart. This is documented and consented to, not hidden, but it is well above five; flagging it because AGENTS.md treats D-22 as a narrow exception.

### Gaps Summary

Two gaps block a `passed` verdict.

1. **SC1 is failed, accepted for rollout but not for the criterion.** The honest state is: the apply was reviewed and authorised, the shortfall is small (within 1.6% on the n-thresholds) and fully accounted for in 127 of its rows, but the roadmap contract is unmatched and nobody has recorded that the contract itself is changed. Close it with an owner override or an amended criterion, and record the 58 absent CRNs as an open item.
2. **P10-WR-01 puts a false statement on the live site** in a reachable, untested state. The fix is one condition plus one test; live prevalence needs one API scan.

Beyond the gaps, status cannot become `passed` until the human_verification section is worked: six queued visual checks (none observed, one of which cannot be run at spec length on live data), the unobserved first post-apply sweep, the WR-01 prevalence scan, and the owner decision on SC1. Suggested next step: `/gsd-plan-phase 10 --gaps` for the WR-01 fix (and optionally WR-02/WR-03 triage), then `/gsd-verify-work 10` for the UAT, with the owner's SC1 decision recorded first so the UAT is not carrying an open contract question.

---

_Verified: 2026-10-02T02:29:35Z_
_Verifier: Claude (gsd-verifier)_
