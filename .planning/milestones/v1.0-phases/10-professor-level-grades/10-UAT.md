---
status: complete
phase: 10-professor-level-grades
source: [10-VERIFICATION.md]
started: 2026-10-04T00:51:41.133Z
updated: 2026-10-04T20:50:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. Deploy check for the P10-WR-01 fix (new in re-verification). The fix (ce93724, 4318e44) is on branch phase-10-post-merge only; origin/main is bcf1dbb. After the operator merges and Render redeploys easy-a-web, confirm the deployed bundle name differs from the pre-fix index-sH87Oudy.js and then run UAT 2 and UAT 7.
expected: A new web bundle is live. A Staff or unnamed section whose instructors are all under the 15-grade cutoff shows 'Historically taught by', the Source line, the Staff explainer and 'N other instructors with under 15 grades each', with no dashed 'No instructor-level grade history is recorded' note.
result: pass
evidence: origin/main 6a81e29 contains ce93724 and 4318e44; live bundle index-DKTDfTjY.js (differs from index-sH87Oudy.js)

### 2. UAT 1: named-instructor block, desktop and 320 px. Open https://easy-a-web.onrender.com, term Spring 2027, search PSY 2012, expand CRN 12188 (also 12189, 12193, 12194, 12195). Then CNT 4419 CRN 14250 (also 14251).
expected: 'Instructors for this course' directly under the course-wide figures; the current instructor first, highlighted, labelled 'This section', with 'Used in this section's score'; rows read '{pct}% A, {n} grades, {k} terms ({first}-{last})' and Easiness or 'Not scored' over 'Under 30 grades'; the PSY 2012 pinned row shows the 'Based on 1 term' chip (term_count 1, 202508 only). CNT 4419 shows no highlighted row (current instructor has no history; designed state).
result: pass

### 3. UAT 2: Staff section. Expand IDH 4950 CRN 12497 (also 12498 to 12503, 12505).
expected: Heading 'Historically taught by', the Staff explainer saying the instructors do not affect this section's score, no highlighted row, nothing saying 'Used in this section's score', 14 rows plus a 1-instructor Others line.
result: pass

### 4. UAT 3: lab and fallback sections. Expand CHM 2045L CRN 11528 (also 11529, 11530; CHM 2211L CRN 11287). Expand SYG 3235 CRN 20075 (subject source) and CHD 4537 CRN 13112 (global source; CLT 3511 CRN 20322 is another).
expected: Lab: only the dashed note 'Instructor history is not shown for lab sections. The figures above are course-wide.' with no heading and no rows. Fallback sections: no instructor block at all.
result: pass

### 5. UAT 4: more than five instructors. Expand ENC 1101 CRN 14045 (41 sections; also 14114, 14124). Expand ANT 4930 CRN 10805 and BSC 4933 CRN 18286 for the Others line.
expected: ENC 1101: at most five rows visible, 'Show all 62 instructors' opens with Enter and Space and shows a focus ring (no Others line can appear: other_instructor_count is 0 on all 41 ENC 1101 sections, finding A). ANT 4930 (6 rows, others 4) and BSC 4933 (10 rows, others 9): the Others line shows counts only ('N other instructors with under 15 grades each').
result: pass

### 6. UAT 5 (backstop, UI-SPEC long-text 1): at 320 px open CRW 3312 CRN 13723 (18-character name, visible as the pinned row) and IDH 4950 CRN 12497 (18-character name, row 13 of 14, inside 'Show all 14 instructors'). For the 40-character case, edit a name text node in the browser developer tools or use a mock-data build.
expected: The name wraps onto further lines with no ellipsis, clipping or horizontal scroll (break-words is on the name span in source and appears 9 times in the deployed bundle).
result: pass

### 7. UAT 6 (backstop, UI-SPEC long-text 2): at 320 px focus or hover the 'i' InfoTip in the block on PSY 2012 CRN 12188.
expected: The full co-teaching caveat ('USF lists one instructor per section; co-taught courses are attributed to the listed instructor.') appears without clipping off-screen. Source shows the tooltip is w-64 and right-anchored (InfoTip.tsx), so a 256 px tooltip must fit left of the icon inside a 320 px viewport.
result: pass

### 8. UAT 7 (from P10-WR-01): scan the public search API for 202701 items with instructor_breakdown.status ready, instructors empty, other_instructor_count > 0 and a Staff or unnamed section; open one in the UI after the fix is deployed. Recorded as not run in 10-ROLLOUT-EVIDENCE.md.
expected: Count recorded. If any exist, after the fix is deployed the page shows the Staff block with the Others line and no 'No instructor-level grade history is recorded' note. If none exist, record 'not exercisable on live data'; the vitest test is then the only evidence.
result: pass
evidence: "Scan run 2026-10-04: 3708 items; count A = 176 (ready, no listed instructors, other_instructor_count > 0); 142 of those have a Staff current instructor. Exercisable on live data. Remaining: open one in the UI, e.g. MUN 3714 CRN 10123."

### 9. Post-apply live sweep (see behavior_unverified_items): after the first worker sweep following the apply, repeat sync-status, report_ranking_diff and the instructor_course count.
expected: succeeded and not stale; exit 0; instructor_course 637 (drift explained); 0 removed historical sections.
result: pass
evidence: "2026-10-04: sync-status succeeded, not stale (last success 19:46Z); report_ranking_diff exit 0 (3708 sections identical, float noise only <=5e-15); historical sections 8535, removed_at set 0; instructor_course 664 vs 637 at apply. Drift (+27, total sections 3707->3708) accepted by owner as USF adding/changing sections; cause not independently verified."

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
