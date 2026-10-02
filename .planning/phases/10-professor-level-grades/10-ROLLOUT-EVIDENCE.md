# Phase 10 Rollout Evidence (plan 10-07)

Dated evidence for the pre-merge half of the Phase 10 rollout. No connection strings, hostnames or credentials appear in this file. Every hosted database statement below ran inside a READ ONLY transaction (`SET TRANSACTION READ ONLY`; `transaction_read_only` confirmed `on`). No USF request had been made when Task 1 closed; Task 2 sections are appended below as they are run.

**FINAL STATUS (2026-10-01T21:23:24Z): the operator chose `approve` at the D-04 decision (see "D-04 decision" at the end); plan 10-07 is complete. The status lines below are earlier ones, kept for the record.**

**LATEST STATUS (2026-10-01, after dry run 4): the fourth five-term dry run (all-campus request with the campus gate before normalising, the one the user authorised after 10-GAP-06) COMPLETED: exit 0, `status` succeeded, `guard_failures` empty in all five terms, `row_normalisation_failures` 0, would-insert 8,535, nothing written (row counts identical). `pairs_match_reference` is still FAIL (pairs_total 3,297 against 3,216; n >= 60/30/15 are 1,314 / 2,153 / 2,785 against 1,329 / 2,178 / 2,829); `course_level_violations` is 0. It was not rerun. The D-04 decision is awaiting the operator; see "Five-term dry run 4 (D-07)" at the end. The statuses below are earlier ones, kept for the record.**

**STATUS (2026-10-01, after dry run 3): the third five-term dry run (all-campus request, the one the user authorised after 10-GAP-05) FAILED to complete: `error_kind` `parse` at term 202601, a schedule time cell holding two to-be-announced components that the row normaliser rejects (2 rows, both on a campus the backfill excludes). No what-if, no per-term report and no guard result was produced; nothing was written (row counts identical). It was not rerun and no code was changed (D-22e). See "Five-term dry run 3 (D-07)" at the end. The D-04 decision cannot be taken on dry run 3 evidence. The status below is the earlier one, kept for the record.**

**EARLIER STATUS (2026-10-01, after dry run 2): the second five-term dry run (the one the user authorised) completed all five requests and the full what-if, but exited 1 with guard `unmatched_fraction` in all five terms (10.1% to 38.9% of graded CRNs missing from USF against a 2% limit), and `pairs_match_reference` FAIL (2,788 pairs against 3,216). Nothing was written (row counts identical). It was not rerun and no narrower query was tried (D-22e). The D-04 decision is awaiting the operator; see "Five-term dry run 2 (D-07)" and "D-04 what-if diff". Earlier status, kept for the record: Task 1 parity gate RESOLVED (exit 0 after the 1e-9 tolerance, commit cef0d5c); dry run 1 failed at 202505 with a parse guard and was repaired (commit 7e29a8c).**

## Pre-merge gates

| Item | Value |
|------|-------|
| Start (UTC) | 2026-10-01T06:29:06Z |
| Branch | `phase-10-prof-grades` |
| HEAD at start | `0bb86e49c36747ac327830e366da7d9d0e123882` |
| D-10 check | `git fetch origin` then `git merge-base --is-ancestor origin/main HEAD` exits 0; branch is not `main` |
| origin/main | `8789ffd8775761acbe9f02bda791afcb02fecd00` |
| Plans 10-01..10-06 | all have SUMMARY files |

Local gate summary lines (all passed on the first run, nothing needed fixing):

| Gate | Result |
|------|--------|
| `uv run ruff check .` | All checks passed! |
| `uv run mypy src` | Success: no issues found in 92 source files |
| `uv run pytest -q` | 843 passed, 4 skipped, 1 warning |
| `npm --prefix web run lint` | clean |
| `npm --prefix web run typecheck` | clean |
| `npm --prefix web test` | 9 test files, 118 tests passed |
| `VITE_USE_MOCK_DATA=false VITE_API_BASE_URL=https://example.onrender.com npm --prefix web run build` | built (index JS 242.92 kB, gzip 74.19 kB) |

Workstation interpreter for the gates: CPython 3.14.4 (the `.venv`). The Docker image and the Render worker use `python:3.12-slim-trixie`.

## Hosted read-only baseline

Observed 2026-10-01T06:30:54Z, READ ONLY transaction.

| Check | Result |
|-------|--------|
| Alembic version | `0004_sync_removed_at` (head; this phase adds no migration) |
| Active 202701 sections | 3,703 |
| Sections in 202408 / 202501 / 202505 / 202508 / 202601 | 0 / 0 / 0 / 0 / 0 (as expected before the backfill) |

202701 `section_rankings.score_source` split (matches STATE.md as of 2026-09-30):

| score_source | rows |
|--------------|------|
| course | 3,332 |
| subject | 322 |
| global | 49 |

202701 active `delivery_method` values (for the Task 2 comparison with historical terms): `CL` 3,476; NULL 104; `HB` 85; `PD` 24; `AD` 14.

## Code-only parity (D-03)

First run (exact comparison, before the tolerance). Command: `uv run python scripts/report_ranking_diff.py --term 202701`, run from the workstation at 2026-10-01T06:31:00Z to 06:31:04Z. **Exit code 1 (differences). The required result was exit 0 (identical). The plan's instruction on exit 1 is to stop and present this evidence, so Task 2 was not run.**

| Field | Value |
|-------|-------|
| total_before / total_after | 3,703 / 3,703 |
| missing_in_after / extra_in_after | none / none |
| changed (any score field differs) | 3,667 of 3,703 |
| transitions (score_source changes) | none |
| abs easiness delta | max 5.33e-15, mean 2.35e-15, median 1.78e-15, p90 5.33e-15 |
| delta buckets | exactly 0: 745; (0, 0.25]: 2,958; every larger bucket: 0 |
| rank_shift | max 0, median 0 |
| effective_n and confidence_label changes | none |
| informational_changes | 0 |
| verdicts | identical FAIL; course_level_invariant FAIL (see below) |

Every difference is at the size of a single floating-point unit in the last place (1 ULP; the largest is 5.33e-15 on scores near 8 to 10). Fields that differ: `easiness_score` on 2,958 CRNs and `smoothed_withdrawal_rate` on 3,440 CRNs. No score_source, effective_n, confidence label or rank changed. The `course_level_invariant` verdict fails only because the comparison is exact: it counts these 1-ULP differences on course-level sections as violations.

### Re-run after tolerance (D-03)

The user decided "revise-with-tolerance". Commit `cef0d5c` added a shared `SCORE_TOLERANCE = 1e-9` (see `10-GAP-01-TOLERANCE.md`). The first run above is kept as the original BLOCKED record. Re-run: `uv run python scripts/report_ranking_diff.py --term 202701`, read-only, 2026-10-01T16:56:43Z to 16:56:49Z, no USF request. **Exit code 0 (identical).**

| Field | Value |
|-------|-------|
| verdicts | identical PASS; course_level_invariant PASS |
| total_before / total_after | 3,705 / 3,705 (active 202701 sections grew from 3,703 to 3,705 through the normal sync between the two runs; no missing or extra CRN) |
| changed (beyond tolerance) | 0 |
| transitions | none |
| rank_shift | max 0, median 0 |
| course_level_violations / informational_changes | 0 / 0 |
| float_noise | tolerance 1e-9, count 3,669, max_abs_delta 5.33e-15 |
| abs easiness delta | max 5.33e-15, mean 2.35e-15, median 1.78e-15; exactly 0: 745; (0, 0.25]: 2,960; every larger bucket: 0 |

Within-tolerance float noise remains visible under `float_noise` (3,669 sections, largest 5.33e-15, about 1 ULP), the same pre-existing cache gap diagnosed below. No score_source, effective_n, confidence label or rank differs.

### Diagnosis (read-only, local recompute against the same hosted data)

Two follow-up checks were run to find where the 1-ULP gap comes from. Both only read hosted data (READ ONLY transaction, rolled back).

| Check | Result |
|-------|--------|
| Recompute 202701 with origin/main code (`git archive origin/main src`, used from a scratch directory) vs recompute with this branch's code | 0 of 3,703 CRNs differ. The new code is exactly inert on live data. |
| Stored cache vs origin/main-code recompute | 3,667 of 3,703 differ, max 5.33e-15. The same gap exists without any Phase 10 code. |
| Stored cache vs this branch's recompute | 3,667 of 3,703 differ, max 5.33e-15 (identical to the previous row). |
| `report_ranking_diff.py` rerun under CPython 3.12.14 (scratch venv from the frozen lockfile; no package added, repo untouched) | Same result: exit 1, 3,667 changed, same deltas. The Python minor version is not the cause. |

Conclusion: this branch's code changes nothing by itself (the substance of D-03 holds: recomputation with and without the Phase 10 code is identical for all 3,703 sections, with no score, source, n, label or rank change). The gap is between the stored cache and any local recomputation, and it pre-exists this phase. The stored values are `Float` (double precision), so it is not a column-rounding effect. The likely cause is the runtime that last wrote the cache (the Render worker: different CPU or libm or an earlier code revision), but that is NOT confirmed. `report_ranking_diff.py` compares exactly, so it cannot return exit 0 against this cache from this workstation.

Note on request count: `report_ranking_diff.py` was run twice (once per interpreter) instead of once. Both runs are read-only and make no USF request.

## Laboratory vocabulary (D-13)

Active 202701 `section_type` values on hosted Supabase (READ ONLY, 2026-10-01T06:30:54Z):

| section_type | active sections |
|--------------|-----------------|
| Class Lecture | 2,340 |
| Laboratory | 555 |
| Directed Individual Study | 210 |
| Individual Performance | 141 |
| Internship | 131 |
| Discussion | 98 |
| Supervised Research | 86 |
| Other | 78 |
| Supervised Teaching | 64 |
| Total | 3,703 |

`LABORATORY_SECTION_TYPES` is `frozenset({"laboratory"})` (unchanged). The only laboratory value on hosted 202701 is `Laboratory`, which normalizes to `laboratory` and matches. There is no bare "Lab" value and no combined lecture-and-lab type among the nine values, so no code or test change was needed and none was committed. The historical-term section_type histogram is only available from the Task 2 dry run, so this vocabulary check remains open for the five historical terms.

## Five-term dry run 1 (D-07, parse failure at 202505)

**FAILED. Exit code 1, nothing written. The what-if (D-04), the per-term counts, N for `--expect-inserted`, the historical section_type histogram and the join re-measure were NOT produced.**

Command (run exactly once): `uv run python scripts/backfill_historical_sections.py --dry-run --report-json .planning/phases/10-professor-level-grades/10-WHATIF-DIFF.json`. Start 2026-10-01T16:57:32Z, end 2026-10-01T16:59:13Z (101 s). No USF request had been made from this workstation in this plan before it (the 60-minute precondition holds).

Sanitized outcome (stdout, identical to the report file):

| Field | Value |
|-------|-------|
| status / mode / written | failed / dry_run / false |
| error_kind | `parse` |
| failed_term | `202505` |
| error | Parsed 2174 rows from 2175 data rows; refusing a response that silently lost rows. |

Request count: the CLI fetches the terms in order and stops at the first failure, so three whole-term USF requests were made (`202408`, `202501`, `202505`, the last two 30 s apart); `202508` and `202601` were never requested. `202408` and `202501` fetched and parsed without a guard failure, but their counts were not reported because the run stops before any database step.

Meaning: `parse_whole_term` found 2,175 `<tr>` blocks containing a `<td>` in the 202505 response but the row parser produced 2,174 rows, one fewer. The guard refuses the whole term by design (it is the same fail-closed guard the live sync uses). The cause (which row is dropped and why) cannot be seen from the sanitized output, and the response HTML is not kept. Diagnosing it needs either a code change that reports the dropped row's position (counts only) plus a new request, or an explicit decision about the parser. Per D-22(e) there was no retry and no narrower-query fallback, and the dry run was not rerun.

`10-WHATIF-DIFF.json` holds only this failure object (no `what_if`, no changes list, no "://").

## Row counts before/after (dry run 1)

Read-only transactions (`SET TRANSACTION READ ONLY`, confirmed `on`). Counts are identical, so nothing was written (T-10-21).

| Table | Before (2026-10-01T16:57:24Z) | After (2026-10-01T16:59:17Z) |
|-------|------------------------------|------------------------------|
| sections (all terms; all are 202701) | 3,814 | 3,814 |
| section_instructors | 4,426 | 4,426 |
| seat_snapshots | 4,370 | 4,370 |
| section_rankings (all rows; all 202701) | 3,705 | 3,705 |
| ingest_runs | 133 | 133 |

Note: `sections` includes removed rows (3,814 total vs 3,705 active/ranked 202701 sections).

## Dry run 1 diagnosis and fix

The diagnostic dry run for term 202505 (with the saved-response option from 10-GAP-02) named the dropped row: data row `#486` of 2,175, a legitimate 24-cell section that parsed as `8/24` cells. Cause: its notes cell holds a hand-typed anchor with a non-breaking space in the start tag and a closing `</a` that never reaches its `>`, which left an anchor open and nested the remaining 16 cells inside it. The saved page is local only (git-ignored, mode 0600) and is not quoted here.

Decision "repair-anchor": a narrow, offline repair of cut-off anchor tags inside each row block before the guard counts and parses rows (commit `7e29a8c`, see `10-GAP-03-ANCHOR-REPAIR.md`). The guard condition is unchanged and every other lost-row shape is still refused.

Offline validation against the saved page (no USF request, no database connection): 2175 of 2175 rows parsed with the guard passing, at three chunkings; the 2174 rows that parsed before are identical after; one row newly parsed. 34 row blocks were touched by the repair (one failing row, 33 harmless cut-off closes). Gates after the change: `uv run pytest -q` 941 passed, 4 skipped, 1 xfailed; ruff and mypy clean.

The five-term dry run has NOT been rerun; it needs an explicit go-ahead, and this note does not authorise it. The Task 1 and Task 2 statuses above are unchanged until it is rerun.

## Five-term dry run (D-07)

Dry run 2, the single run the user authorised after the anchor repair (7e29a8c). Command, run exactly once and not rerun: `uv run python scripts/backfill_historical_sections.py --dry-run --report-json .planning/phases/10-professor-level-grades/10-WHATIF-DIFF.json --save-failed-response .planning/phases/10-professor-level-grades/failed-responses/dry-run-2.html`. Start 2026-10-01T19:39:42Z, end 2026-10-01T19:44:40Z (298 s, five whole-term USF requests 30 s apart). No parse failure occurred, so `dry-run-2.html` was not written (the git-ignored directory holds only the dry run 1 page).

**Exit code 1. `status` failed, `error_kind` `guard`, `written` false (always rolled back). `guard_failures` is `["unmatched_fraction"]` for ALL FIVE terms; the limit is 2% (`DEFAULT_MAX_UNMATCHED_FRACTION`, runbook section 1). All five terms fetched and parsed, the lost-rows guard no longer trips (202505 now parses 2,175 rows), and the what-if below was still computed, but a real `--apply` with these defaults would stop at the guard.**

Per term (fetched and graded, 202701 what-if computed once after all terms). `data_row_count`, `tail_error`, `bytes` and `elapsed` are reported only on a parse failure and were not emitted.

| Term | fetched_rows | grade_crns | to_write (would insert) | unmatched_grade_crns | unmatched_fraction | guard_failures | staff_or_blank | non_tampa | grade_course_unattributed | course_key_mismatch | uncataloged |
|------|-------------:|-----------:|------------------------:|---------------------:|-------------------:|----------------|---------------:|----------:|--------------------------:|--------------------:|------------:|
| 202408 | 6,672 | 179 | 161 | 18 | 0.1006 | unmatched_fraction | 0 | 0 | 0 | 0 | 0 |
| 202501 | 6,498 | 2,096 | 1,844 | 252 | 0.1202 | unmatched_fraction | 1 | 0 | 0 | 0 | 0 |
| 202505 | 2,175 | 465 | 284 | 181 | 0.3892 | unmatched_fraction | 0 | 0 | 0 | 0 | 0 |
| 202508 | 7,043 | 2,887 | 2,361 | 526 | 0.1822 | unmatched_fraction | 0 | 0 | 0 | 0 | 0 |
| 202601 | 6,703 | 3,035 | 2,512 | 523 | 0.1723 | unmatched_fraction | 0 | 0 | 0 | 0 | 0 |
| Total | 29,091 | 8,662 | **7,162** | 1,500 | 0.1732 | | 1 | 0 | 0 | 0 | 0 |

Total would-insert **N = 7,162** (the `--expect-inserted` value for plan 10-08, valid only for a run whose guards pass). Per term: 161 + 1,844 + 284 + 2,361 + 2,512. Every term reports `unchanged` 0, `updated` 0, `refreshed_last_seen` 0, `instructor_changes` 0, and `instructor_rows_added` equal to `inserted`. The 1,500 unmatched graded CRNs equal exactly the 1,500 grade rows with no section in the join re-measure below (8,662 total, 7,162 with a section). The cause is NOT established (USF no longer listing those CRNs in a whole-term response is the guard's own definition; why 10% to 39% of past graded CRNs are absent is unexplained). Raising `--max-unmatched-fraction` is not recommended without understanding it (runbook).

Historical `section_type` histogram per term (all five terms, 7,162 sections):

| section_type | 202408 | 202501 | 202505 | 202508 | 202601 | Total |
|--------------|-------:|-------:|-------:|-------:|-------:|------:|
| Class Lecture | 161 | 1,251 | 157 | 1,664 | 1,720 | 4,953 |
| Laboratory | 0 | 474 | 93 | 489 | 509 | 1,565 |
| Discussion | 0 | 37 | 7 | 47 | 75 | 166 |
| Other | 0 | 45 | 4 | 50 | 59 | 158 |
| Internship | 0 | 12 | 11 | 25 | 56 | 104 |
| Individual Performance | 0 | 0 | 0 | 43 | 46 | 89 |
| Directed Individual Study | 0 | 15 | 6 | 28 | 28 | 77 |
| Supervised Research | 0 | 7 | 3 | 8 | 9 | 27 |
| Supervised Teaching | 0 | 3 | 3 | 7 | 10 | 23 |

D-13 check: every historical value is one of the nine already seen on hosted 202701. The only laboratory value is `Laboratory`; there is no bare "Lab" and no combined lecture-and-lab type. `LABORATORY_SECTION_TYPES` stays `frozenset({"laboratory"})`; no code or test change. This closes the historical half of the vocabulary check opened in Task 1.

`delivery_method` per historical term (202408: CL 159, HB 2; 202501: CL 1,774, HB 41, None 10, PD 18, AD 1; 202505: CL 269, HB 3, None 5, PD 3, AD 4; 202508: CL 2,291, HB 40, None 9, PD 17, AD 4; 202601: CL 2,379, HB 57, None 47, PD 23, AD 6). All of AD, CL, HB, PD and NULL already occur in 202701; no new delivery method.

Pre-run read-only check at 2026-10-01T19:39:37Z: `uv run python scripts/report_ranking_diff.py --term 202701` exit 0 (identical PASS, course_level_invariant PASS, 3,706 of 3,706 sections, changed 0, float_noise count 3,670 with max 5.33e-15, no USF request).

## Row counts before/after

Read-only transactions (`SET TRANSACTION READ ONLY`, confirmed `on`). Identical, so nothing was written (T-10-21).

| Table | Before (2026-10-01T19:39:31Z) | After (2026-10-01T19:44:58Z) |
|-------|------------------------------|------------------------------|
| sections (all terms; all are 202701) | 3,815 | 3,815 |
| section_instructors | 4,436 | 4,436 |
| seat_snapshots | 4,376 | 4,376 |
| section_rankings (all rows; all 202701) | 3,706 | 3,706 |
| ingest_runs | 136 | 136 |

The counts moved slightly from the dry run 1 snapshots (3,814 / 4,426 / 4,370 / 3,705 / 133) through the normal sync between the two plan runs, not through the dry run.

## Join re-measure vs 2026-09-28

`what_if.pairs` of the dry run compared with the 2026-09-28 reference. `matches_reference` **false** (verdict `pairs_match_reference` FAIL). This blocks the go-live review until explained (runbook section 1).

| Measure | Dry run 2 | Reference | Delta |
|---------|----------:|----------:|------:|
| pairs | 2,788 | 3,216 | -428 |
| n >= 60 | 1,014 | 1,329 | -315 |
| n >= 30 | 1,743 | 2,178 | -435 |
| n >= 15 | 2,326 | 2,829 | -503 |
| n >= 5 | 2,671 | 3,208 | -537 |
| n >= 1 | 2,679 | 3,216 | -537 |
| n >= 30 and multi-term | 1,039 | 1,308 | -269 |
| instructors | 1,550 | 1,796 | -246 |
| courses | 1,119 | 1,117 | +2 |
| multi-term pairs | 1,208 | 1,439 | -231 |
| term span 1 / 2 / 3 / 4 / 5 | 1,580 / 831 / 302 / 74 / 1 | 1,777 / 965 / 359 / 110 / 5 | -197 / -134 / -57 / -36 / -4 |
| grade rows total | 8,662 | 8,662 | 0 |
| grade rows with a section | 7,162 | not in reference | |
| grade rows named | 7,161 | 8,661 | -1,500 |
| grade rows Staff or blank | 1 | not in reference | |

Reading: the grade-row total matches exactly; the shortfall of 1,500 named rows is exactly the 1,500 unmatched graded CRNs above. Every join number is lower than the reference, consistently with those rows being unattributable; courses is +2. The dry run cannot attribute instructors to graded CRNs that USF does not list, which is the likeliest source of the gap to the reference; this is not confirmed.

## D-04 what-if diff

**GUARD FAILURE: `unmatched_fraction` in all five terms (1,500 of 8,662 graded CRNs, 17.3%, limit 2%); `pairs_match_reference` FAIL (2,788 against 3,216; n >= 60/30/15 are 1,014 / 1,743 / 2,326 against 1,329 / 2,178 / 2,829). course_level_violations is 0.**

What-if term 202701 (3,706 sections), computed on the in-transaction state as if the 7,162 sections had been written, then rolled back.

| Item | Value |
|------|-------|
| code_only_parity | PASS (identical true; changed 0; float_noise count 3,670 at tolerance 1e-9, max 5.33e-15, on the stored cache against recomputation before any change) |
| course_level_invariant | PASS |
| course_level_violations | **0** |
| changed sections (score fields differ beyond tolerance) | 616 of 3,706 |
| transitions | course -> instructor_course: 616 (no other transition; no section leaves or enters) |
| missing_in_after / extra_in_after | none / none |
| informational_changes (mapped instructor section count changed, scores unchanged) | 2,989 |
| float_noise | count 3,061, max 5.33e-15 |
| changed fields | 272 with easiness, withdrawal, effective_n, confidence_label and source; 188 with easiness, withdrawal, effective_n and source; 140 with easiness, withdrawal and source; 16 other combinations |
| direction of easiness change | 333 up, 283 down |
| effective_n of the 616 after | 441 at n >= 60, 175 at 30 to 59, none below 30 |

Absolute easiness delta, all 3,706 sections: max 2.619, mean 0.0457, median 3.6e-15, p90 0.1386; buckets: exactly 0: 650; (0, 0.25]: 2,797; (0.25, 0.5]: 166; (0.5, 1]: 80; (1, 2]: 11; > 2: 2.

Absolute delta over the 616 changed sections only: max 2.619, mean 0.275, median 0.196, p90 0.589; 13 sections move by more than 1.0.

Rank shift (absolute): all 3,706 sections max 2,137, median 35; over the 616 changed sections median 266.5, mean 385, p90 940, max 2,137.

Top 25 changes by absolute delta (all are `course` -> `instructor_course`; CRN, subject and course number, easiness before and after, delta, rank before and after, effective_n before and after):

| CRN | Course | Before | After | Delta | Rank before | Rank after | n before | n after |
|-----|--------|-------:|------:|------:|------------:|-----------:|---------:|--------:|
| 13417 | AMH 2020 | 8.568 | 5.949 | -2.619 | 2686 | 3703 | 4049 | 296 |
| 20578 | AMH 2020 | 8.568 | 5.949 | -2.619 | 2700 | 3704 | 4049 | 296 |
| 12059 | ECO 3101 | 6.502 | 7.933 | +1.430 | 3701 | 3395 | 469 | 56 |
| 12060 | ECO 3101 | 6.502 | 7.933 | +1.430 | 3702 | 3396 | 469 | 56 |
| 13155 | HUM 1020 | 8.598 | 7.197 | -1.401 | 2605 | 3657 | 3384 | 77 |
| 13819 | EGN 3343 | 7.599 | 8.930 | +1.331 | 3585 | 1871 | 727 | 142 |
| 16940 | FIN 4504 | 8.911 | 7.609 | -1.303 | 1859 | 3553 | 426 | 56 |
| 14092 | EGN 3311 | 6.862 | 5.608 | -1.254 | 3684 | 3705 | 929 | 181 |
| 18402 | EGN 2615 | 7.222 | 5.982 | -1.240 | 3655 | 3701 | 496 | 53 |
| 18405 | EGN 2615 | 7.222 | 5.982 | -1.240 | 3658 | 3702 | 496 | 53 |
| 13523 | BSC 2011 | 7.658 | 8.745 | +1.088 | 3579 | 2247 | 2829 | 490 |
| 18637 | ANT 4930 | 8.745 | 7.741 | -1.004 | 2242 | 3525 | 227 | 32 |
| 18716 | ANT 4930 | 8.745 | 7.741 | -1.004 | 2245 | 3526 | 227 | 32 |
| 14499 | CEG 4850 | 8.609 | 9.595 | +0.986 | 2561 | 471 | 78 | 78 |
| 18408 | EGN 2440 | 7.213 | 8.195 | +0.983 | 3661 | 3171 | 827 | 148 |
| 18411 | EGN 2440 | 7.213 | 8.195 | +0.983 | 3664 | 3172 | 827 | 148 |
| 13804 | EGN 3365 | 7.976 | 8.953 | +0.978 | 3396 | 1814 | 722 | 84 |
| 15987 | AMH 2020 | 8.568 | 9.530 | +0.962 | 2690 | 559 | 4049 | 494 |
| 20509 | AMH 2020 | 8.568 | 9.530 | +0.962 | 2697 | 560 | 4049 | 494 |
| 12151 | POT 3003 | 8.403 | 7.461 | -0.942 | 3027 | 3586 | 362 | 79 |
| 19095 | HUM 1020 | 8.598 | 7.661 | -0.937 | 2611 | 3547 | 3384 | 261 |
| 11590 | MAR 3023 | 8.189 | 9.116 | +0.927 | 3205 | 1515 | 2772 | 919 |
| 14798 | GEB 3033 | 9.399 | 8.482 | -0.918 | 794 | 2809 | 2320 | 159 |
| 17151 | STA 2122 | 8.286 | 9.194 | +0.908 | 3119 | 1295 | 1247 | 192 |
| 17152 | STA 2122 | 8.286 | 9.194 | +0.908 | 3120 | 1296 | 1247 | 192 |

Resulting 202701 `instructor_course` sections: **616** (none before the backfill). Sanity against the research's 751 sections at n >= 30 including 131 labs (as of 2026-09-28): 751 less 131 labs is 620, and 616 is close; labs stay at course level (9 of the 616 carry an L suffix in the course number). The lower count is consistent with the shortfall in joined pairs above.

`10-WHATIF-DIFF.json` holds the full object plus the `changes` list (616 entries, derived numbers only, no instructor names, no "://"). It is the dry run 2 object: dry run 3 overwrote it with its short failure payload and that overwrite was reverted (`git checkout` of that one file), so the committed file stays the last complete what-if (computed with the superseded campus=T request).

## Five-term dry run 3 (D-07), all-campus request

The single run the user authorised after the campus fix (commits `a49e33a`, `097c95a`; notes 10-GAP-04, 10-GAP-05). Command, run exactly once and not rerun: `uv run python scripts/backfill_historical_sections.py --dry-run --report-json .planning/phases/10-professor-level-grades/10-WHATIF-DIFF.json --save-failed-response .planning/phases/10-professor-level-grades/failed-responses/dry-run-3.html`. Start 2026-10-01T20:24:07Z, end 2026-10-01T20:27:37Z (210 s wall clock for the requests that ran, with the 30 s inter-term pause). Pre-run read-only check at 2026-10-01T20:24:02Z: `report_ranking_diff.py --term 202701` exit 0 (identical true, course_level_invariant true, changed 0, 3,706 of 3,706, no USF request).

**Exit code 1. `status` failed, `error_kind` `parse`, `failed_term` `202601`, `written` false.** Diagnostics fingerprint (the whole payload, sanitized): error text `Invalid schedule time range` on a time cell consisting of two to-be-announced placeholders separated by a space (the shape `TBA TBA`, a row with two meeting components both unscheduled); `data_row_count`, `tail_error` and lost-rows diagnostics were not emitted because this is a normalisation error, not the lost-rows guard. `saved_response`: saved, 10,756,455 bytes, written to the git-ignored `failed-responses/dry-run-3.html` (mode 0600; never committed or quoted). The report carries no per-term section, no `fetch_seconds`, no `response_bytes` for the terms that came before, no what-if and no `guard_failures`: a parse failure aborts the run before any of them is built. The terms run in ascending order, so 202408, 202501, 202505 and 202508 were fetched and parsed before 202601 failed (inferred from the failure term; not reported). The only size figure available is the 202601 page: **10.76 MB for the all-campus response, under the 25 MB `WHOLE_TERM_MAX_BYTES` cap, no fetch size or timeout error.** The GAP-05 estimate (3 to 14 MB per page) held for this page.

Offline read of the saved 202601 page only (the repo's own parser, no USF request, no database connection; counts only):

| Measure | Value |
|---------|------:|
| data rows / rows parsed by the row parser | 9,969 / 9,969 (lost-rows guard would pass) |
| `Tampa` | 6,703 (the same count as the earlier `campus=T` request) |
| `Off-campus - Tampa` | 1,958 |
| `St. Petersburg` | 646 |
| `Off-campus - Sarasota-Manatee` | 253 |
| `Sarasota-Manatee` | 195 |
| `Off-campus - St. Petersburg` | 175 |
| `Off Campus Special Programs` | 39 (not on the allow-list, not one of the four known labels: would be listed under `unknown_campus_labels` if graded) |
| rows whose time cell the normaliser rejects | 2, both `Sarasota-Manatee`, both the two-placeholder shape |
| USF error tail marker present | yes (the usual one, as in the 202505 page) |

Reading: the all-campus request itself worked (the page parses to 9,969 rows, 1,958 of them `Off-campus - Tampa`). The failure is a separate, new defect: `parse_whole_term` normalises every fetched row before the campus allow-list is applied, so a row on an excluded campus can abort the run, and `_parse_time_range` accepts a lone `TBA` or `ARR` but not two components that are both unscheduled. The two rows would be dropped by the campus gate anyway. Other terms' pages may contain the same shape or others (the four earlier terms did not fail, and no saved copy of them exists). No code was changed and nothing was retried (D-22e); a fix needs a decision and then a fourth dry run needs its own authorisation.

### Row counts before/after (dry run 3)

Read-only transactions (`SET TRANSACTION READ ONLY`, `on`). Identical, so nothing was written (T-10-21).

| Table | Before (2026-10-01T20:23:55Z) | After (2026-10-01T20:28:38Z) |
|-------|------------------------------|------------------------------|
| sections (all terms; all are 202701) | 3,815 | 3,815 |
| section_instructors | 4,436 | 4,436 |
| seat_snapshots | 4,376 | 4,376 |
| section_rankings (all rows; all 202701) | 3,706 | 3,706 |
| ingest_runs | 136 | 136 |

### D-04 and the join re-measure

Not available from dry run 3: no what-if was computed, no pairs figure exists, no `would-insert` value, no `rows_by_campus` per term (other than the offline 202601 counts above), and the 633 non-"Other" previously unmatched CRNs were not checked. The dry run 2 figures above remain the last complete ones and are superseded by the request change. There is no `--expect-inserted` proposal. D-04 is not decided and nothing here approves a go-live.

## Five-term dry run 4 (D-07), campus gate before normalising

The single run the user authorised after the GAP-06 fix (commits `88a1f93`, `6501f3b`; notes 10-GAP-05, 10-GAP-06). Command, run exactly once and not rerun: `uv run python scripts/backfill_historical_sections.py --dry-run --report-json .planning/phases/10-professor-level-grades/10-WHATIF-DIFF.json --save-responses .planning/phases/10-professor-level-grades/failed-responses/dry-run-4`. Start 2026-10-01T21:08:44Z, end 2026-10-01T21:14:04Z (320 s wall clock: five all-campus whole-term USF requests 30 s apart). Pre-run read-only check at 2026-10-01T21:08:40Z: `report_ranking_diff.py --term 202701` exit 0 (identical true, course_level_invariant true, changed 0, 3,707 of 3,707, float_noise count 3,671 with max 5.33e-15, no USF request).

**Exit code 0. `status` succeeded, `mode` dry_run, `written` false (always rolled back), `guard_failures` `[]` for every term, `row_normalisation_failures` 0 for every term, `row_failures` empty.** Stderr empty. Request: whole-term campus blank (all campuses), selection allow-list `tampa` and `off-campus - tampa`. The five saved pages (`failed-responses/dry-run-4/<term>.html`, mode 0600, 47,483,086 bytes in all) are git-ignored and are not quoted or committed. In `10-WHATIF-DIFF.json` the saved-response paths were shortened from an absolute path to `<repo>/...` (no other change); the file contains no "://" and no home path.

Per term (the grade table holds 8,662 CRNs; every figure is a count).

| Term | fetched_rows | grade_crns | matched | unmatched | unmatched_fraction | kept (to_write = inserted) | non_tampa (grade CRN on another campus) | unknown_campus_labels (graded) | row_normalisation_failures | response_bytes | fetch_seconds |
|------|-------------:|-----------:|--------:|----------:|-------------------:|---------------------------:|----------------------------------------:|-------------------------------:|---------------------------:|---------------:|--------------:|
| 202408 | 9,776 | 179 | 179 | 0 | 0.0000 | 179 | 0 | none | 0 | 10,502,779 | 13.52 |
| 202501 | 9,620 | 2,096 | 2,096 | 0 | 0.0000 | 2,090 | 6 | Off Campus Special Programs 3 | 0 | 10,349,520 | 13.265 |
| 202505 | 4,445 | 465 | 465 | 0 | 0.0000 | 448 | 17 | Off Campus Special Programs 17 | 0 | 4,782,960 | 7.452 |
| 202508 | 10,298 | 2,887 | 2,863 | 24 | 0.0083 | 2,840 | 23 | Off Campus Special Programs 1 | 0 | 11,091,372 | 14.457 |
| 202601 | 9,969 | 3,035 | 3,001 | 34 | 0.0112 | 2,978 | 23 | Off Campus Special Programs 5 | 0 | 10,756,455 | 13.705 |
| Total | 44,108 | 8,662 | 8,604 | 58 | 0.0067 | **8,535** | 69 | 26 | 0 | 47,483,086 | 62.4 |

Total would-insert **N = 8,535** (179 + 2,090 + 448 + 2,840 + 2,978); this is the proposed `--expect-inserted` value for plan 10-08, valid only for a run whose guards pass. 8,662 grade CRNs = 8,535 kept + 69 on a non-allow-listed campus + 58 absent from the response. Every term reports `unchanged` 0, `updated` 0, `refreshed_last_seen` 0, `instructor_changes` 0, `course_key_mismatch` 0, `grade_course_unattributed` 0, `uncataloged` 0 and `instructor_rows_added` equal to `inserted`; `staff_or_blank` 1 (202501). The largest page is 11.09 MB (202508), under the 25 MB `WHOLE_TERM_MAX_BYTES` cap; no fetch size or timeout error.

`rows_by_campus` per term (all fetched rows; Tampa / Off-campus - Tampa / St. Petersburg / Off-campus - St. Petersburg / Sarasota-Manatee / Off-campus - Sarasota-Manatee / Off Campus Special Programs):

| Term | Tampa | Off-campus - Tampa | St. Petersburg | Off-campus - St. Petersburg | Sarasota-Manatee | Off-campus - Sarasota-Manatee | Off Campus Special Programs |
|------|------:|-------------------:|---------------:|----------------------------:|-----------------:|------------------------------:|----------------------------:|
| 202408 | 6,672 | 1,857 | 604 | 178 | 190 | 237 | 38 |
| 202501 | 6,498 | 1,858 | 599 | 161 | 189 | 254 | 61 |
| 202505 | 2,175 | 1,370 | 194 | 139 | 40 | 228 | 299 |
| 202508 | 7,043 | 1,936 | 646 | 181 | 210 | 253 | 29 |
| 202601 | 6,703 | 1,958 | 646 | 175 | 195 | 253 | 39 |

`non_tampa_by_label` (graded CRNs whose schedule campus is not on the allow-list; skipped, never written): 202501: Off Campus Special Programs 3, Sarasota-Manatee 1, St. Petersburg 2. 202505: Off Campus Special Programs 17. 202508: Off Campus Special Programs 1, Off-campus - Sarasota-Manatee 4, Off-campus - St. Petersburg 8, Sarasota-Manatee 2, St. Petersburg 8. 202601: Off Campus Special Programs 5, Off-campus - Sarasota-Manatee 2, Off-campus - St. Petersburg 2, Sarasota-Manatee 6, St. Petersburg 8. Totals: Off Campus Special Programs 26 (the only label that is neither allow-listed nor one of the four known non-Tampa labels, reported as `unknown_campus_labels`), St. Petersburg 18, Off-campus - St. Petersburg 10, Sarasota-Manatee 9, Off-campus - Sarasota-Manatee 6 (69 in all). These are Tampa-credited in the grade file (`0001 - Tampa Campus`) but scheduled on another campus by USF, so the allow-list excludes them; that policy is part of the D-04 decision.

### Unmatched graded CRNs, and the earlier non-"Other" gap

Unmatched fell from 1,500 (dry run 2, `campus=T`) to 58 (0.67% of 8,662; the limit is 2%), and the two terms that have any are 0.83% (202508) and 1.12% (202601). Offline read of the saved pages (the repo's own parser, the grade keys captured earlier, no USF request): the 58 still-unmatched grade CRNs by grade suffix are C 36, L 10, D 8, S 3, O 1 (202508: C 14, L 5, D 4, S 1; 202601: C 22, L 5, D 4, S 2, O 1). So at most 57 non-"Other" CRNs remain unmatched, against 633 non-"Other" before: at least 576 of the 633 now match (assuming the 57 are among the earlier 633, which holds when a campus=T row is also in the all-campus response), and only 1 `O` CRN remains unmatched against the 867 lower bound before. The 202505 term, where the earlier campus=T page survives, is exact: all 181 CRNs unmatched in dry run 2 (68 non-"Other", 113 `O`) are now matched and 202505 has 0 unmatched. The remaining 58 are not explained here (no label check of those CRNs was made).

### Historical `section_type` histogram and delivery methods (D-13)

| section_type | 202408 | 202501 | 202505 | 202508 | 202601 | Total |
|--------------|-------:|-------:|-------:|-------:|-------:|------:|
| Class Lecture | 168 | 1,299 | 186 | 1,806 | 1,850 | 5,309 |
| Laboratory | 0 | 482 | 115 | 503 | 517 | 1,617 |
| Other | 11 | 233 | 116 | 315 | 342 | 1,017 |
| Discussion | 0 | 38 | 7 | 53 | 81 | 179 |
| Internship | 0 | 12 | 12 | 57 | 81 | 162 |
| Individual Performance | 0 | 0 | 0 | 43 | 46 | 89 |
| Directed Individual Study | 0 | 16 | 6 | 31 | 30 | 83 |
| Supervised Teaching | 0 | 3 | 3 | 24 | 22 | 52 |
| Supervised Research | 0 | 7 | 3 | 8 | 9 | 27 |

D-13 check: every historical value is one of the nine values already seen on hosted 202701. The only laboratory value is `Laboratory` (no bare "Lab"); there is no combined lecture-and-lab type and no pure-lab type outside `LABORATORY_SECTION_TYPES = frozenset({"laboratory"})`. No code or test change. The `Other` count rises from 158 (campus=T) to 1,017 as expected: the Tampa-credited online block is mostly `Other`.

`delivery_method` per term: 202408: CL 159, AD 18, HB 2; 202501: CL 1,775, AD 242, HB 41, PD 22, None 10; 202505: CL 269, AD 167, PD 4, HB 3, None 5; 202508: CL 2,293, AD 448, HB 42, None 39, PD 18; 202601: CL 2,386, AD 440, HB 59, None 68, PD 25. Totals CL 6,882, AD 1,315, HB 147, None 122, PD 69. All of AD, CL, HB, PD and NULL already occur in 202701; no new delivery method.

### Row counts before/after (dry run 4)

Read-only transactions (`SET TRANSACTION READ ONLY`, `on`). Identical, so nothing was written (T-10-21).

| Table | Before (2026-10-01T21:08:35Z) | After (2026-10-01T21:14:09Z) |
|-------|------------------------------|------------------------------|
| sections (all terms; all are 202701) | 3,816 | 3,816 |
| section_instructors | 4,438 | 4,438 |
| seat_snapshots | 4,377 | 4,377 |
| section_rankings (all rows; all 202701) | 3,707 | 3,707 |
| ingest_runs | 137 | 137 |

The counts moved slightly from the dry run 3 snapshots (3,815 / 4,436 / 4,376 / 3,706 / 136) through the normal sync between the two plan runs, not through the dry run.

### Join re-measure vs 2026-09-28

`what_if.pairs.matches_reference` **false** (verdict `pairs_match_reference` FAIL; it requires pairs, n >= 60, n >= 30 and n >= 15 to match exactly). This blocks the go-live review until every delta is explained and accepted in writing (runbook section 1).

| Measure | Dry run 4 | Reference | Delta | Dry run 2 (campus=T) |
|---------|----------:|----------:|------:|---------------------:|
| pairs (`pairs_total`, includes pairs with n = 0) | 3,297 | 3,216 | +81 | 2,788 |
| n >= 60 | 1,314 | 1,329 | -15 | 1,014 |
| n >= 30 | 2,153 | 2,178 | -25 | 1,743 |
| n >= 15 | 2,785 | 2,829 | -44 | 2,326 |
| n >= 5 | 3,145 | 3,208 | -63 | 2,671 |
| n >= 1 | 3,153 | 3,216 | -63 | 2,679 |
| n >= 30 and multi-term | 1,292 | 1,308 | -16 | 1,039 |
| instructors | 1,790 | 1,796 | -6 | 1,550 |
| courses | 1,148 | 1,117 | +31 | 1,119 |
| multi-term pairs | 1,484 | 1,439 | +45 | 1,208 |
| term span 1 / 2 / 3 / 4 / 5 | 1,813 / 992 / 372 / 115 / 5 | 1,777 / 965 / 359 / 110 / 5 | +36 / +27 / +13 / +5 / 0 | 1,580 / 831 / 302 / 74 / 1 |
| grade rows total | 8,662 | 8,662 | 0 | 8,662 |
| grade rows with a section | 8,535 | not in reference | | 7,162 |
| grade rows named | 8,534 | 8,661 | -127 | 7,161 |
| grade rows Staff or blank | 1 | not in reference | | 1 |

Reading (observations; the cause of the remaining differences is not established): the join is now within 0.5% to 1.5% of the reference on the n-threshold counts (the dry run 2 gap was 21% to 24%) and the `named` shortfall fell from 1,500 to 127. The 127 named rows missing equal the 58 unmatched CRNs plus the 69 grade CRNs on a non-allow-listed campus (58 + 69 = 127). The headline `pairs` figure is +81 because `pairs_total` includes 144 pairs with no graded students (n = 0); the reference `pairs` (3,216) equals its own `n >= 1`, and on that like-for-like measure the delta is -63. `matches_reference` compares exactly, so it stays FAIL until the deltas are accepted or explained. `section_type_histogram` of the join: Class Lecture 5,309, Laboratory 1,617, Other 1,017, Discussion 179, Internship 162, Individual Performance 89, Directed Individual Study 83, Supervised Teaching 52, Supervised Research 27 (sums to 8,535).

### D-04 what-if diff

What-if term 202701 (3,707 sections), computed on the in-transaction state as if the 8,535 sections had been written, then rolled back. `guard_failures` is empty in every term; the only failing verdict is `pairs_match_reference`.

| Item | Value |
|------|-------|
| code_only_parity | PASS (identical true; changed 0; float_noise count 3,671 at tolerance 1e-9, max 5.33e-15, stored cache against recomputation before any change) |
| course_level_invariant | PASS |
| course_level_violations | **0** |
| changed sections (score fields differ beyond tolerance) | 637 of 3,707 |
| transitions | course -> instructor_course: 637 (no other transition; no section leaves or enters) |
| missing_in_after / extra_in_after | none / none |
| informational_changes (mapped instructor section count changed, scores unchanged) | 3,019 |
| float_noise | count 3,041, max 5.33e-15 |
| changed fields | 270 with easiness, withdrawal, effective_n, confidence_label and source; 195 with easiness, withdrawal, effective_n and source; 156 with easiness, withdrawal and source; 16 other combinations |
| direction of easiness change | 343 up, 294 down |
| effective_n of the 637 after | 469 at n >= 60, 168 at 30 to 59, none below 30 |

Absolute easiness delta, all 3,707 sections: max 2.619, mean 0.0461, median 3.6e-15, p90 0.1476; buckets: exactly 0: 650; (0, 0.25]: 2,801; (0.25, 0.5]: 164; (0.5, 1]: 79; (1, 2]: 11; > 2: 2.

Absolute delta over the 637 changed sections only: max 2.619, mean 0.268, median 0.189, p90 0.575; 13 sections move by more than 1.0.

Rank shift (absolute): all 3,707 sections max 2,135, median 36; over the 637 changed sections median 266, mean 378, p90 931, max 2,135.

Top 15 changes by absolute delta (all `course` -> `instructor_course`; CRN, subject and course number, easiness before and after, delta, rank before and after, effective_n before and after):

| CRN | Course | Before | After | Delta | Rank before | Rank after | n before | n after |
|-----|--------|-------:|------:|------:|------------:|-----------:|---------:|--------:|
| 13417 | AMH 2020 | 8.568 | 5.949 | -2.619 | 2686 | 3704 | 4049 | 296 |
| 20578 | AMH 2020 | 8.568 | 5.949 | -2.619 | 2700 | 3705 | 4049 | 296 |
| 12059 | ECO 3101 | 6.502 | 7.933 | +1.430 | 3702 | 3396 | 469 | 56 |
| 12060 | ECO 3101 | 6.502 | 7.933 | +1.430 | 3703 | 3397 | 469 | 56 |
| 13155 | HUM 1020 | 8.598 | 7.197 | -1.401 | 2605 | 3659 | 3384 | 77 |
| 13819 | EGN 3343 | 7.599 | 8.930 | +1.331 | 3586 | 1868 | 727 | 142 |
| 16940 | FIN 4504 | 8.911 | 7.609 | -1.303 | 1859 | 3557 | 426 | 56 |
| 14092 | EGN 3311 | 6.862 | 5.608 | -1.254 | 3685 | 3706 | 929 | 181 |
| 18402 | EGN 2615 | 7.222 | 5.982 | -1.240 | 3656 | 3702 | 496 | 53 |
| 18405 | EGN 2615 | 7.222 | 5.982 | -1.240 | 3659 | 3703 | 496 | 53 |
| 13523 | BSC 2011 | 7.658 | 8.745 | +1.088 | 3580 | 2246 | 2829 | 490 |
| 18637 | ANT 4930 | 8.745 | 7.741 | -1.004 | 2242 | 3529 | 227 | 32 |
| 18716 | ANT 4930 | 8.745 | 7.741 | -1.004 | 2245 | 3530 | 227 | 32 |
| 14499 | CEG 4850 | 8.609 | 9.595 | +0.986 | 2561 | 476 | 78 | 78 |
| 18408 | EGN 2440 | 7.213 | 8.195 | +0.983 | 3662 | 3170 | 827 | 148 |

Resulting 202701 `instructor_course` sections: **637** (none before the backfill); 9 of the 637 carry an L suffix in the course number (labs stay at course level by rule and no course-level, subject-level or global score moved: `course_level_violations` 0). Against the 2026-09-28 research's 751 sections at n >= 30 including 131 labs (751 less 131 is 620), 637 is in the same range.

`10-WHATIF-DIFF.json` now holds the full dry run 4 object, including the `changes` list (637 entries, derived numbers only: no instructor names, no "://", no home path). It replaces the dry run 2 object that was committed earlier; the dry run 2 figures above stay in this file for the record.

### D-04 and the plan 10-08 hand-off

No decision is recorded here and nothing in this section approves a go-live or `--apply`: D-04 is a `blocking-human` decision that the operator takes. The evidence it rests on is the two tables above (guards all clear; `pairs_match_reference` FAIL with the deltas listed; 637 sections change, all `course` -> `instructor_course`; no course-level movement). Proposed `--expect-inserted 8535`, valid only for a rerun that again has empty `guard_failures` on current data; a real `--apply` would make its own five USF requests.

## D-04 decision

| Item | Value |
|------|-------|
| Decision | `approve` |
| Recorded (UTC) | 2026-10-01T21:23:24Z |
| Decided by | the user (operator), in the orchestrator session, from the dry run 4 evidence summary |
| Options offered | approve (accept the reference deltas in writing, keep the allow-list); revise-widen-allow-list; reject |
| Reason given | None in the user's own words. The user replied only "approve"; no written reason was given and none is inferred here. |

What the approval accepts, in writing, from the "Five-term dry run 4" evidence above (dry run 4: exit 0, `guard_failures` empty in all five terms, `row_normalisation_failures` 0, would-insert 8,535, `course_level_violations` 0, `pairs_match_reference` FAIL):

- The `pairs_match_reference` FAIL stays as measured; it is accepted, not re-run. Deltas against the 2026-09-28 reference: pairs with n >= 1 -63; n >= 60 -15; n >= 30 -25; n >= 15 -44; named grade rows -127.
- The -127 named grade rows are fully accounted for: 58 graded CRNs absent from the whole-term responses plus 69 graded CRNs scheduled on a non-allow-listed campus (58 + 69 = 127).
- The courses delta (+31) and the multi-term pairs delta (+45) are unexplained. They are accepted as unexplained, not as understood. (The headline `pairs` +81 is the `pairs_total` definition including 144 pairs with n = 0; the like-for-like figure is the n >= 1 delta above.)
- The allow-list stays `{Tampa, Off-campus - Tampa}`. The 69 graded CRNs on other campuses stay excluded: 26 Off Campus Special Programs, 18 St. Petersburg, 10 Off-campus - St. Petersburg, 9 Sarasota-Manatee, 6 Off-campus - Sarasota-Manatee. The option to widen the allow-list was offered and not chosen.
- The proposed `--expect-inserted 8535` is valid only for a rerun that again has empty `guard_failures` on current data. A real `--apply` makes its own five USF requests and must be judged against its own dry run figures; if the guards or N differ, this approval does not cover that run without a new look.

Scope of the approval: it lets plan 10-08 start (merge with green CI, then the operator-run apply, each with its own gates and its own authorisations). It does NOT itself authorise the apply, a merge, a push, a deploy or any live USF request or hosted database write.

Open follow-ups (none resolved by this decision):

1. The 58 unmatched graded CRNs (0.67% of 8,662; 202508: 24, 202601: 34) are unexplained.
2. The courses (+31) and multi-term pairs (+45) deltas are unexplained.
3. Live-term blind spot: the live sync's `campus=T` request still cannot see Tampa-credited rows scheduled under another label for Spring 2027 (see 10-GAP-05, "Follow-up: the live term has the same blind spot").
4. The shared-normaliser change from 10-GAP-06 (a time cell of only `TBA`/`ARR` placeholders now reads as no time range, not a parse error) is a live-visible change to the live sync's normaliser (see 10-GAP-06, "Shared-code call-outs").
5. The Phase 9 carry-overs WR-03 and NEB 0001 are untouched by this plan.

## CI, merge and deploy

Recorded 2026-10-01 by the plan 10-08 continuation executor (Task 1 verification half), read-only, from branch `phase-10-post-merge` (created at origin/main). The merge, the push and the Render deploy were operator actions; nothing here pushed, merged or deployed.

Verdict: PASS on every item below. One item is not independently verifiable and is stated as such (the Render deploy rows).

| Item | Result |
|------|--------|
| PR | #37 (`phase-10-prof-grades` into `main`), https://github.com/aatif101/easy-A/pull/37, state MERGED |
| Merge commit | `bcf1dbbace2a16dc8d03d18880f6bcba89f4afe7`, merged 2026-10-01T21:33:06Z |
| `git fetch origin && git rev-parse origin/main` | `bcf1dbbace2a16dc8d03d18880f6bcba89f4afe7`, equal to the merge commit |
| `gh pr checks 37` | python, web and docker all `pass` on both PR runs (below) |
| PR run, event `push`, head `144e07d` | https://github.com/aatif101/easy-A/actions/runs/36929153363 (python 1m25s, web 27s, docker 40s), conclusion success |
| PR run, event `pull_request`, head `144e07d` | https://github.com/aatif101/easy-A/actions/runs/36929155977 (python 1m24s, web 32s, docker 28s), conclusion success |
| Post-merge run on main, event `push`, head `bcf1dbb` | https://github.com/aatif101/easy-A/actions/runs/36929434892, conclusion success |
| Check-runs on the merge commit | `python`, `web`, `docker` all `success` (GitHub API) |

Render deploy of the merge commit:

| Item | Result |
|------|--------|
| Operator statement | The user states Render shows easy-a-api, easy-a-worker and easy-a-web live on the merge commit. |
| Independent evidence | GitHub deployments created by Render for sha `bcf1dbbace2a16dc8d03d18880f6bcba89f4afe7` (environments `main - easy-a-api`, `main - easy-a-worker`, `main - easy-a-web`, created 2026-10-01T21:34:52Z to 21:34:53Z). Each has status `in_progress` then `success`: web 21:35:08Z, worker 21:35:21Z, api 21:35:34Z. This is Render's own report to GitHub, read through the GitHub API; it corroborates the operator statement but is not a read of the running containers. |
| What could NOT be verified | The commit actually running inside each container. `/health` returns only `{"status":"ok"}` and `/api/v1/metadata/sync-status` has no version or commit field; the runbook documents none. The worker (no HTTP surface) was not inspected beyond the Render deployment status above. |

Live health at 2026-10-01T21:40Z:

| Check | Result |
|-------|--------|
| `GET /health` | HTTP 200, `{"status":"ok"}` (served by uvicorn behind Cloudflare) |
| `GET /api/v1/metadata/sync-status?term=202701` | `is_stale` false; `last_status` succeeded; `last_success_at` 2026-10-01T20:42:05Z; `last_run_at` 2026-10-01T20:41:29Z; `last_error_kind` null; `failures_last_24h` 0; `in_registration_window` false; `cadence_seconds` 3600; `stale_after_seconds` 7200; `as_of` 2026-10-01T21:40:42Z |
| Observation | `last_records_failed` is 1 for the latest sweep. The runbook's healthy definition (succeeded, not stale, 0 failures in 24h) is met; the one unapplied row per sweep is noted, not investigated here. No sweep ran after the merge deploy yet at the time of the check (last run 20:41Z, cadence 3600 s), so this status predates the deployed code's first sweep. |

## Pre-apply live baseline

Observed 2026-10-01T21:41Z to 21:43Z, after the deploy of `bcf1dbb`, before any apply. All database reads in READ ONLY transactions; all API calls were public GETs. No USF request, no write.

Verdict: PASS. `report_ranking_diff` exit 0, inventory PASS/PASS, search items carry no instructor history.

### Deployed code changes no live score

`uv run python scripts/report_ranking_diff.py --term 202701`: exit 0 at 2026-10-01T21:41:03Z, verdicts `identical` PASS and `course_level_invariant` PASS.

| Field | Value |
|-------|-------|
| total_before / total_after | 3,707 / 3,707 |
| missing_in_after / extra_in_after | none / none |
| changed (beyond 1e-9) | 0 |
| float noise | 3,671 rows with delta at or below 1e-9; max abs delta 5.33e-15 (tolerance 1e-9) |
| course_level_violations | none |

### Inventory baseline (D-21)

`uv run python scripts/inventory_tampa_grades.py --term 202701`: exit 0 at 2026-10-01T21:41:05Z, verdicts `integrity` PASS and `d21_grade_coverage` PASS.

| Field | Value |
|-------|-------|
| 202701 sections / cache rows / represented courses | 3,707 / 3,707 / 1,374 |
| non_tampa_section_count | 0 |
| stale_cache | false (cache refreshed 2026-10-01T20:41:29Z) |
| evidence_backed sections | 3,049 |
| exception sections | 658 = no_rows 374 + non_letter_grade 284 |
| courses by state | evidence_backed 1,081; exception_no_rows 244; exception_non_letter_grade 49 |
| grade rows | 8,662 (202408 179, 202501 2,096, 202505 465, 202508 2,887, 202601 3,035); latest ingest 2026-09-23T21:36:34Z |
| integrity | unattributed_grade_rows 0; bucket_sum_mismatch_rows 0; rows_at_or_after_term 0 |

Note: active 202701 sections are 3,707 now against 3,703 at the 2026-10-01T06:30Z baseline above; the difference is live sweep drift (the worker ran at 20:41Z), not a change from this plan.

### Cache and metadata baselines (counts only)

| Item | Value |
|------|-------|
| Alembic version | `0004_sync_removed_at` (unchanged; no migration in this phase) |
| 202701 `section_rankings` rows | 3,707 |
| score_source split | course 3,333; subject 325; global 49 (no `instructor_course` yet) |
| delivery_method split | CL 3,480; NULL 104; HB 85; PD 24; AD 14 |
| Rows with a non-null `instructor_breakdown` | 0 of 3,707 (0 rows have a null `historical_analytics`) |

### API payload baselines

Public GETs against `https://easy-a-api.onrender.com`, HTTP 200 each. Bytes are the response body size; the SHA-256 is of the exact body saved at that moment (the search pages depend on live sweep data, so a later difference is expected to be explained, not assumed a regression).

| Request | Bytes | Items | SHA-256 |
|---------|-------|-------|---------|
| `/api/v1/rankings/search?term=202701&subject=ENC&course_number=1101&limit=50` | 84,210 | 41 (envelope total 41; limit 50, offset 0) | `f1255729d31617b55b2ef491e80dab06d77db1271a11a36d8b7a902239870351` |
| `/api/v1/rankings/search?term=202701&limit=50` (default page) | 99,363 | 50 (envelope total 3,707) | `873b63cd332913a0fe17de56fadafe1705e33fc1bffecd6153a5d93f98e3c7b4` |
| `/api/v1/metadata/delivery-methods` | 175 | 4 codes | `870eed9100ddfbd460599f5cf53918fc0dcdf4f35ab36c7b1c81e6062c50d4a3` |

`/api/v1/metadata/delivery-methods` body, verbatim (it carries no personal data):

```json
[{"code":"AD","label":"All Online 100%"},{"code":"CL","label":"Classroom 1–49%"},{"code":"HB","label":"Hybrid Blend 50–79%"},{"code":"PD","label":"Primarily DL 80–99%"}]
```

### No instructor history yet

Every sampled search item (41 on the ENC 1101 page and 50 on the default page, 91 items in all) has `historical_analytics.instructor_breakdown` present with the value `null`, so the key exists in the deployed response schema and carries no history. All 91 items have `score_source` `course`. The `historical_analytics` object keys on the deployed API are: completed_grade_count, confidence_label, easiness_score, effective_n, instructor_breakdown, mapped_instructor_section_count, prior_level, provenance, score_source, section_count, smoothed_withdrawal_rate, term_count, total_grade_count, withdrawal_count.

### Baseline conclusion

The deployed code changes no live score (ranking diff identical), D-21 inventory passes with 3,049 evidence-backed sections and 658 exceptions, the API serves no instructor history, and the payload sizes and delivery-method list are recorded for the post-apply comparison. Task 2 (the operator-run apply) was not prepared or run.

## Apply (D-05)

The operator ran the single apply from their own shell at merge commit `bcf1dbb`: `--apply --rebuild-term 202701 --expect-inserted 8535` with `--report-json .planning/phases/10-professor-level-grades/10-APPLY-REPORT.json`. The executor did not run it and made no USF request and no hosted write. Everything below was read from that report or from READ ONLY hosted transactions (`SET TRANSACTION READ ONLY`, `transaction_read_only` = on) taken 2026-10-02T01:56Z (UTC; the apply itself ran 2026-10-02 01:35:48Z to about 01:42:21Z by the ingest-run timestamps, cache rebuilt 01:40:22Z). The user pasted the same JSON summary; the executor re-read the file.

Verdict: **PASS on every Task 2 item.**

### Report file

| Check | Result |
|-------|--------|
| `10-APPLY-REPORT.json` | exists, 427,464 bytes, valid JSON (keys applied, fetch_seconds, mode, request, status, terms, written) |
| Leak scan | 0 occurrences of "://" and 0 of "pooler" (untracked; committed on this branch with the evidence, see below) |
| status / mode / written | `succeeded` / `apply` / `true` |
| `expect_inserted` | expected 8,535, actual 8,535, matched true |
| gate | gated true, `gate_failures` empty, `course_level_invariant` PASS, `course_level_violations` 0 |
| rows_rebuilt | 3,707 (total_before 3,707, total_after 3,707, missing_in_after none, extra_in_after none) |
| fetch_seconds | 202408 19.567, 202501 16.674, 202505 28.590, 202508 31.782, 202601 41.266 (137.9 s in all); five whole-term requests, no retry |

### Hosted counts against the reviewed dry run 4

| Term | Dry run 4 `to_write` | Hosted sections | Match | section_instructors rows | distinct section_id | Per-term report `inserted` / `instructor_rows_added` / `unmatched_grade_crns` |
|------|---------------------:|----------------:|-------|-------------------------:|--------------------:|--------------------------------------------|
| 202408 | 179 | 179 | yes | 179 | 179 | 179 / 179 / 0 |
| 202501 | 2,090 | 2,090 | yes | 2,090 | 2,090 | 2,090 / 2,090 / 0 |
| 202505 | 448 | 448 | yes | 448 | 448 | 448 / 448 / 0 |
| 202508 | 2,840 | 2,840 | yes | 2,840 | 2,840 | 2,840 / 2,840 / 24 |
| 202601 | 2,978 | 2,978 | yes | 2,978 | 2,978 | 2,978 / 2,978 / 34 |
| Total | 8,535 | 8,535 | yes | 8,535 | 8,535 | 8,535 / 8,535 / 58 |

Every per-term field of the apply report (fetched_rows, rows_by_campus, campus_allowed_rows, non_tampa and its labels, histograms, response_bytes, unmatched, staff_or_blank, all guard counters) is identical to dry run 4's `10-WHATIF-DIFF.json`, including `response_bytes` per term, so the USF responses did not change between the two runs; `guard_failures` is empty and `row_normalisation_failures` is 0 in every term.

| Check | Result |
|-------|--------|
| SectionInstructor rows on the 8,535 historical sections | 8,535 rows, 8,535 distinct section_id (no duplicates), 0 historical sections without an instructor row |
| Source of those rows | exactly one distinct value, `usf_schedule_backfill` |
| seat_snapshots on historical sections | **0** |
| non-null `removed_at` on historical sections | **0** |
| section_rankings rows for historical terms | 0 (the cache holds 202701 only) |
| IngestRun | one `succeeded` row per term, source `usf_schedule_backfill:202408` ... `:202601`, `error_message` null; records_seen / inserted / updated / failed: 179 / 179 / 0 / 0; 2,096 / 2,090 / 0 / 6; 465 / 448 / 0 / 17; 2,863 / 2,840 / 0 / 23; 3,001 / 2,978 / 0 / 23 (records_seen is the matched graded CRNs, records_failed the graded CRNs on a non-allow-listed campus: 6, 17, 23, 23 match `non_tampa`); all five rows carry one `started_at` (2026-10-02 01:35:48Z, one transaction) |
| Whole-table totals | sections 12,351 (= 3,816 + 8,535); section_instructors 12,973 (= 4,438 + 8,535, so the apply touched no 202701 instructor row); seat_snapshots 4,377 (unchanged); section_rankings 3,707 (unchanged); ingest_runs 146 (137 at dry run 4 + 5 backfill rows + 4 live sweeps since; the rows are history); alembic `0004_sync_removed_at` (unchanged) |
| 202701 sections | 3,816 in all (unchanged from dry run 4), of which 3,707 active and 109 with `removed_at` set (all removal marks pre-date this plan) |

### 202701 section_rankings score_source split

| score_source | Pre-apply baseline (2026-10-01T21:41Z) | Post-apply (2026-10-02T01:56Z) | Change |
|--------------|---------------------------------------:|-------------------------------:|-------:|
| course | 3,333 | 2,696 | -637 |
| subject | 325 | 325 | 0 |
| global | 49 | 49 | 0 |
| instructor_course | 0 | **637** | +637 |
| total | 3,707 | 3,707 | 0 |

The 637 expected by the what-if are exactly the 637 now served; every row left `course` for `instructor_course` and nothing else moved. All 3,707 cache rows carry one `refreshed_at` (2026-10-02 01:40:22Z, the apply's rebuild).

### Applied diff against the reviewed what-if (D-04)

The applied diff compares the stored cache before and after the rebuild; the what-if compared the stored cache with an in-transaction recomputation. Both are over the same 3,707 sections.

| Item | Reviewed what-if (dry run 4) | Applied (report) | Difference |
|------|------------------------------|------------------|------------|
| changed | 637 | 637 | none |
| transitions | course -> instructor_course 637 | course -> instructor_course 637 | none |
| course_level_violations | 0 | 0 | none |
| course_level_invariant | PASS | PASS | none |
| informational_changes | 3,019 | 3,019 | none |
| rank_shift | max 2,135, median 36 | max 2,135, median 36 | none |
| abs_delta max / p90 | 2.619 / 0.1476 | 2.619 / 0.1476 | none (max identical; p90 differs by 2e-15) |
| abs_delta mean | 0.046054672537338595 | 0.046054672537336694 | 1.9e-15 (float noise) |
| abs_delta median | 3.55e-15 | 0.0 | float noise |
| abs_delta buckets: 0 / (0, 0.25] / (0.25, 0.5] / (0.5, 1] / (1, 2] / > 2 | 650 / 2,801 / 164 / 79 / 11 / 2 | 3,070 / 381 / 164 / 79 / 11 / 2 | 2,420 sections move from "(0, 0.25]" to "0" (3,070 - 650 = 2,801 - 381 = 2,420); every bucket above 0.25 identical |
| float_noise | count 3,041, max 5.33e-15 | count 0, max 0.0 | see below |
| top 50 changes | list | same 50 CRNs, same order | none |
| the 637 `changes` entries | list | same 637 CRNs; every field equal (floats within 1e-9, none outside) | none |

Explanation of the only differences. The 637 changed sections, their transitions, deltas, ranks, effective_n values and the 50 top changes are the same as reviewed, so the sweep drift the brief asked about did not move any figure: the live term's section set was 3,707 active sections (3,816 in all) at both measurements and no 202701 instructor row was added in between. The only differences are in the sub-1e-9 float representation: the what-if saw 3,041 sections whose stored (worker-computed) score differs from the recomputation by up to 5.33e-15 (noise that predates this phase and that the runbook documents), while the applied before/after diff sees none. The buckets and median differ solely because of that 2,420-section noise population. The report does not say why the applied before/after diff reports zero noise while a later independent recomputation still sees some (Post-apply verification, item 2, finds 3,666 noise rows at max 5.33e-15); it is recorded as an observation, not explained, and has no effect on any score, rank or label beyond 1e-9.

## Post-apply verification

Recorded 2026-10-02 (UTC) by the plan 10-08 continuation executor, 01:56Z to 02:03Z. Every database access was a READ ONLY transaction, every API call a public GET, and no USF request was made. No file under `failed-responses/` was touched.

**Summary of verdicts: all required checks PASS (items 2, 3, 4, 5, 8; item 7 and 6 recorded). One recorded check does not match its reference and is carried as a finding, not a failure of a required gate: item 1 (success criterion 1) is UNMET as measured, with exactly the deltas that D-04 accepted in writing on 2026-10-01T21:23:24Z. The payload of the two search pages grew 2.5x and 7.0x (item 7), p95 rose from 212.56 to 273.10 ms and stays far below 1,500 ms (item 8). No rollback is indicated. For reference only, the runbook's rollback commands are `uv run python scripts/backfill_historical_sections.py --rollback --rebuild-term 202701 --yes` (data) and a constants revert plus `--rebuild-only --rebuild-term 202701` (scores); nothing was run.**

| # | Check | Verdict |
|---|-------|---------|
| 1 | `measure_instructor_pairs.py --before-term 202701` against the 2026-09-28 reference | exit 1, `pairs_match_reference` FAIL: success criterion 1 UNMET, deltas as accepted at D-04 (finding) |
| 2 | `report_ranking_diff.py --term 202701` | PASS, exit 0 |
| 3 | `inventory_tampa_grades.py` and `validate_tampa_ingest.py` | PASS, exit 0 both; evidence_backed 3,049 equals the baseline |
| 4 | `check_data_quality.py --term 202701` | PASS, 0 errors |
| 5 | historical_analytics breakdown counts and invariant | PASS, 0 violations |
| 6 | public API probes CNT 4419, PSY 2012, a lab section | recorded, consistent |
| 7 | payload bytes and delivery methods | delivery-methods identical; search pages 2.5x and 7.0x larger (finding) |
| 8 | `benchmark_rankings_search.py` remote, 50 iterations | PASS, p95 273.10 ms (< 1,500 ms) |

### 1. Join re-measure vs 2026-09-28 (D-06)

`uv run python scripts/measure_instructor_pairs.py --before-term 202701` at 2026-10-02T01:56:28Z: exit 1, `verdict` FAIL, `matches_reference` false. The numbers are identical, field by field, to dry run 4's in-transaction re-measure (the backfill wrote what the dry run said it would), and the deltas are the ones the D-04 decision accepted.

| Measure | Post-apply | Reference | Delta |
|---------|-----------:|----------:|------:|
| pairs (`pairs_total`, includes n = 0) | 3,297 | 3,216 | +81 |
| pairs, n >= 1 | 3,153 | 3,216 | -63 |
| n >= 60 | 1,314 | 1,329 | -15 |
| n >= 30 | 2,153 | 2,178 | -25 |
| n >= 15 | 2,785 | 2,829 | -44 |
| n >= 5 | 3,145 | 3,208 | -63 |
| instructors | 1,790 | 1,796 | -6 |
| courses | 1,148 | 1,117 | +31 |
| multi-term pairs | 1,484 | 1,439 | +45 |
| n >= 30 and multi-term | 1,292 | 1,308 | -16 |
| term span 1 / 2 / 3 / 4 / 5 | 1,813 / 992 / 372 / 115 / 5 | 1,777 / 965 / 359 / 110 / 5 | +36 / +27 / +13 / +5 / 0 |
| grade rows total / with a section / named / Staff or blank | 8,662 / 8,535 / 8,534 / 1 | 8,662 / not given / 8,661 / not given | 0 / n.a. / -127 / n.a. |

**Success criterion 1 (the re-measure matching 3,216 / 1,329 / 2,178 / 2,829) is UNMET.** Measured 3,297 / 1,314 / 2,153 / 2,785 (deltas +81 / -15 / -25 / -44).

Causes, each stated as a finding:

- **-127 named grade rows: established.** 58 graded CRNs are absent from the whole-term responses (202508: 24, 202601: 34) and 69 graded CRNs are scheduled on a non-allow-listed campus (Off Campus Special Programs 26, St. Petersburg 18, Off-campus - St. Petersburg 10, Sarasota-Manatee 9, Off-campus - Sarasota-Manatee 6); 58 + 69 = 127. Why the 58 are absent is still unexplained (D-04 open follow-up 1).
- **n >= 60 / 30 / 15 / 5 / 1 shortfalls (-15 / -25 / -44 / -63 / -63) and the instructor, multi-term and term-span shortfalls: consistent with, not proven to come from, those 127 missing rows.** Every like-for-like figure is below the reference and the direction is uniform; the executor did not re-run the join without the 127 rows to attribute each pair.
- **Headline +81 pairs, +31 courses, +45 multi-term pairs, -6 instructors: largely a definition artifact (new finding, an inference).** `pairs_total` includes 144 pairs whose students number zero (n = 0, for example sections graded only with non-letter grades); the reference's 3,216 equals its own n >= 1, which suggests it excluded them. A read-only recount on the same hosted data, restricted to pairs with n >= 1, gives pairs 3,153 (-63), instructors 1,756 (-40), courses 1,099 (-18) and multi-term pairs 1,422 (-17): all shortfalls, none a surplus. The 144 n = 0 pairs add 49 courses that no n >= 1 pair has and 62 multi-term pairs. This turns D-04 open follow-ups 2 (courses +31, multi-term +45) from "unexplained" into "explained by the n = 0 pairs, if the reference counted n >= 1 only"; the reference's own basis for instructors, courses and multi-term was not re-checked against the 2026-09-28 report's code, so this stays an inference.
- Section types of the join: Class Lecture 5,309, Laboratory 1,617, Other 1,017, Discussion 179, Internship 162, Individual Performance 89, Directed Individual Study 83, Supervised Teaching 52, Supervised Research 27 (sums to 8,535), the same as dry run 4.

The apply was accepted with these deltas at D-04, so this is a recorded gap, not a regression introduced by the apply.

### 2. Cache equals recomputation

`uv run python scripts/report_ranking_diff.py --term 202701` at 2026-10-02T01:57:17Z: **exit 0**; verdicts `identical` PASS and `course_level_invariant` PASS. total_before = total_after = 3,707; missing_in_after and extra_in_after none; changed 0 (beyond 1e-9); transitions none; rank_shift 0; course_level_violations none; informational_changes 0; float_noise count 3,666, max abs delta 5.33e-15 (baseline before the apply: 3,671 rows, same max). The worker's recomputation and the apply's rebuilt cache agree.

### 3. D-21 and ingest totals

- `uv run python scripts/inventory_tampa_grades.py --term 202701`: exit 0, `integrity` PASS and `d21_grade_coverage` PASS, observed 2026-10-02T01:57:35Z. **evidence_backed sections 3,049, equal to the Task 1 baseline (3,049)**, exceptions 658 (no_rows 374 + non_letter_grade 284), courses evidence_backed 1,081 / exception_no_rows 244 / exception_non_letter_grade 49, 3,707 sections and 3,707 cache rows, 1,374 courses, grade rows 8,662 (202408 179, 202501 2,096, 202505 465, 202508 2,887, 202601 3,035), `stale_cache` false, non_tampa_section_count 0, unattributed_grade_rows 0, bucket_sum_mismatch_rows 0, rows_at_or_after_term 0. Every figure equals the baseline; no sweep drift to explain.
- `uv run python scripts/validate_tampa_ingest.py --term 202701`: exit 0; `PASS suffix-exact`, `PASS reconciliation`, `PASS honest-coverage (verified non-letter-grade exceptions: 284)`; INFO auto-added (D-05) 16 courses (AML 4111, ARH 4301, ART 3781C, ART 4930, DIG 4972, ECH 4535, FIL 4839, FIN 4934, FRE 2201, HUM 4368, HUM 4391, HUM 4434, HUM 4890, LDR 3363, LDR 4204, POT 4936).

### 4. Data quality

`uv run python scripts/check_data_quality.py --term 202701`: exit 0, 3,707 sections, **Errors 0**, Warnings 1,140 (all `low_confidence_ranking`), Info 49 (all `no_historical_analytics`). No pre-apply count of these warnings was recorded, so no before/after comparison is claimed.

### 5. historical_analytics breakdown (202701 section_rankings, 3,707 rows)

| instructor_breakdown | Pre-apply baseline | Post-apply |
|----------------------|-------------------:|-----------:|
| null | 3,707 | **658** |
| `ready` | 0 | **2,506** |
| `lab_section` | 0 | **540** |
| `no_instructor_history` | 0 | **3** |
| total with a breakdown | 0 | 3,049 |

The 3,049 sections with a breakdown equal the 3,049 evidence-backed sections of the inventory, and the 658 null breakdowns equal the 658 D-21 exception sections (no_rows 374 + non_letter_grade 284).

Invariant, over the 637 `instructor_course` rows: 637 of 637 have status `ready`, exactly one `is_current` row, that row `scored` true, its `easiness_score` equal to the row's `easiness_score` (maximum absolute difference 5.33e-15, inside the 1e-9 tolerance; 525 rows are not bit-identical, the rest are) and its `effective_n` equal (maximum absolute difference 0.0). **Violations: 0** (no blocker). The 2,412 breakdown-carrying rows that are not `instructor_course` are all `course` rows; 1,869 of them are `ready` (the course-level figure is served and the instructors are listed), which is the designed behaviour.

### 6. Public API probes

Public GETs at 2026-10-02T01:59Z to 02:00Z, HTTP 200. Names are not recorded.

| Probe | Items | score_source | Breakdown status / rows | Notes |
|-------|------:|--------------|-------------------------|-------|
| `search?term=202701&subject=CNT&course_number=4419` (6,334 bytes) | 2 (CRN 14250, 14251) | both `course` | `ready`, 4 instructor rows each, 4 scored | current instructor has no history (`current_instructor_has_history` false, no `is_current` row, so no pinned row); the four rows have effective_n 203 / 175 / 109 / 44, term_count 2 / 2 / 1 / 1, first_term 202501 / 202501 / 202508 / 202508, last_term 202601 / 202601 / 202508 / 202508; item effective_n 531.0, easiness 8.068, term_count 3, section_count 6 |
| `search?term=202701&subject=PSY&course_number=2012` (52,219 bytes) | 10 | 5 `instructor_course` (CRN 12188, 12189, 12193, 12194, 12195), 5 `course` (11224, 12197, 12198, 12200, 12202) | all `ready`, 14 instructor rows each, 14 scored | `instructor_course` items: pinned (`is_current`) row effective_n 351.0, term_count 1, first_term and last_term 202508, scored true, easiness_score 8.9426; item easiness 8.943 and effective_n 351.0 equal it; `course` items: item effective_n 2,793.0, easiness 8.792, term_count 5, section_count 63, current instructor has no history |
| `search?term=202701&subject=CHM&course_number=2045L` (96,724 bytes) | 40 | all `course` | all 40 `lab_section`, 0 instructor rows, no current instructor | lab rule: labs stay at course level and carry no instructor history |

Provenance on every breakdown: `source` `grade_distributions+section_instructors`, `freshness` `historical`, `source_term` null, detail "instructor-level history from terms before 202701; laboratory sections excluded; USF lists one instructor per section". The item-level `historical_analytics.provenance` source is `grade_distributions` and the item's `instructor_provenance` source is `section_instructors` (freshness `current`, source_term 202701).

### 7. Payload sizes and delivery methods

Body bytes as received without compression, same method as the baseline.

| Request | Baseline (pre-apply) | Post-apply | Ratio | SHA-256 now |
|---------|---------------------:|-----------:|------:|-------------|
| `search?term=202701&subject=ENC&course_number=1101&limit=50` | 84,210 | **591,198** | 7.02x | `71264cdd76ba5605c5770814c6af660bc22c32e83b800f7dfdc013e0311a088b` |
| `search?term=202701&limit=50` (default page) | 99,363 | **247,681** | 2.49x | `e22c9aa116dafa6db660d56af52588455ec24524e656c39f9a49aaab60aeb628` |
| `/api/v1/metadata/delivery-methods` | 175 | 175 | 1.00x | `870eed9100ddfbd460599f5cf53918fc0dcdf4f35ab36c7b1c81e6062c50d4a3` (same as baseline) |

**Findings.** (a) `delivery-methods` is byte-identical to the baseline (AD, CL, HB, PD, same labels): **no new delivery code**, and none of the 8,535 new sections' delivery methods (CL, AD, HB, PD, NULL) added one. (b) The search pages grew because `instructor_breakdown` is no longer null. On the ENC 1101 page all 41 items carry a 62-row breakdown of about 13,500 bytes each (2,542 rows in all, 41 items 15,703 bytes on average against 2,054 before); on the default page the 50 items carry 1 to 22 rows each (698 rows in all, breakdown about 3,239 bytes on average, 5,368 bytes per item against 1,987 before). The non-breakdown part of an item is unchanged in size (about 2,100 to 2,200 bytes). Score mix on the two pages: ENC 1101 16 `instructor_course` and 25 `course`; default page 7 and 43. (c) With `Accept-Encoding: gzip` the same pages are 8,398 bytes (ENC 1101) and 5,228 bytes (default page) on the wire, so the practical transfer cost is small; no pre-apply compressed size was recorded to compare. (d) The growth is a consequence of the reviewed design (every section lists all instructors of its course) and has no plan threshold; it is recorded for the owner, not treated as a failure. The browser-side cost of a 591 KB uncompressed JSON for a 41-section course was not measured.

### 8. Hosted search benchmark

`uv run python scripts/benchmark_rankings_search.py --remote-url https://easy-a-api.onrender.com --iterations 50` at 2026-10-02T02:01:00Z: exit 0, 3,707 sections (hosted API total), 5 warmups, single client over public HTTPS.

| | Baseline (2026-09-30T18:30Z, 3,698 sections) | Post-apply | Change |
|--|---------------------------------------------:|-----------:|-------:|
| p50 | 131.53 ms | 129.98 ms | -1.55 ms |
| p95 | 212.56 ms | **273.10 ms** | +60.54 ms (+28%) |
| max | 371.92 ms | 435.95 ms | +64.03 ms |

**p95 273.10 ms is under the 1,500 ms bar: PASS.** The p95 and max rose while the median is flat, consistent with the larger bodies (item 7) but not attributed: one 50-call run from one workstation cannot separate payload growth from network variance. Browser and concurrent-user latency: not measured.

### Live sweep after the apply (runbook section 4, last bullet)

Not yet observable at the time of writing. `sync-status?term=202701` at 2026-10-02T02:01Z: `last_status` succeeded, `is_stale` false, `last_run_at` 01:08:46Z, `last_success_at` 01:09:10Z, `failures_last_24h` 0, `last_records_failed` 1 (the one unapplied row per sweep noted before the apply). That run pre-dates the apply (01:35Z to 01:42Z) and the cadence is 3,600 s, so the first sweep after the apply was still due and its result is **not** recorded here. What is verified now is the state it will find: 0 historical sections with `removed_at` set, `report_ranking_diff` exit 0, 202701 sections 3,816 unchanged. Open check for the operator or the next session: after the first post-apply sweep, `sync-status` must read succeeded and not stale, `report_ranking_diff.py --term 202701` must still exit 0, and the `instructor_course` count must still be 637 (a worker rebuild must keep the instructor-level scores because it runs the deployed code).

## Deployed UI

Recorded 2026-10-02T02:09Z (UTC) by the plan 10-09 executor. Public GETs only: the static site (`https://easy-a-web.onrender.com/`, its index and one JavaScript asset) and the public search API (`https://easy-a-api.onrender.com/api/v1/rankings/search`, 20 pages of 200 items to read all 202701 items; about 13 MB in all, 1 s apart). No USF request, no database connection, no write. Instructor names are not recorded here: only CRN, course and the name's character length. No browser was driven, so nothing in this section is a visual check.

Verdict: **PASS for the bundle-copy check (all three required strings are in the deployed bundle).** The six visual checks below are **queued for end-of-phase UAT and none is marked passed**. Two findings change how UAT must run two of them (the 40-character name does not exist in live data; ENC 1101 has no Others line).

### Deployed bundle

| Item | Value |
|------|-------|
| `GET /` | HTTP 200, 600 bytes; `index.html` references `/assets/index-sH87Oudy.js` (module script) and `/assets/index-DEXpzv9k.css` |
| JavaScript asset | `/assets/index-sH87Oudy.js`, HTTP 200, 242,919 bytes (the pre-merge local build in this file reported index JS 242.92 kB; the same size) |
| SHA-256 of the asset as fetched | `792d26992987c3524247f781dab1f4068f1fa37e70e55c405c18d26319079e8e` |
| API base compiled in | `easy-a-api.onrender.com`; the placeholder host used by the local gate build (`example.onrender.com`) occurs 0 times |

Copy strings searched with a fixed-string grep (each count is the number of matching lines in the minified bundle):

| String | Found |
|--------|------:|
| `Instructors for this course` | 1 |
| `Historically taught by` | 1 |
| `USF lists one instructor per section; co-taught courses are attributed to the listed instructor.` (verbatim D-15 caveat) | 1 |
| `Instructor history is not shown for lab sections. The figures above are course-wide.` | 1 (checked as a fragment, the text is in the bundle) |
| `Show all` | 1 |
| `Used in this section's score` and `Not used in this section's score.` | present (the Staff check expects the first not to appear in a Staff block; that is a rendering condition, not something a bundle grep can show) |
| `Not scored` | 1 |
| `break-words` | 9 occurrences |

What this establishes: the deployed web build contains the instructor block's copy and points at the live API. What it does not establish: that the block renders, wraps or lays out correctly in a browser; that is the queued UAT below.

### What the live API serves (the data the UI will render)

All 202701 items read from the public search API: 3,707 items, 3,707 distinct CRNs. Status split of `historical_analytics.instructor_breakdown`: `ready` 2,506 (637 `instructor_course` plus 1,869 `course`), `lab_section` 540, `no_instructor_history` 3, null 658 (284 `course` with no breakdown, 325 `subject`, 49 `global`). These equal the counts under "Post-apply verification" item 5 (null 658, ready 2,506, lab_section 540, no_instructor_history 3). No fallback-scored (`subject` or `global`) item has a breakdown. 623 `ready` sections have `other_instructor_count` above 0.

### UAT targets (for the queued human checks)

Open `https://easy-a-web.onrender.com`, search the course code (and pick the CRN), term Spring 2027 (202701).

| Human check | Target | Subject, course | CRN | What the live API says about it |
|-------------|--------|-----------------|-----|---------------------------------|
| 1. Named-instructor section | Primary | PSY 2012 | 12188 (also 12189, 12193, 12194, 12195) | `instructor_course`; breakdown `ready`, 14 rows; the current instructor has history and is the first row (`is_current`, `scored`, `effective_n` 351.0, 1 term, 202508 to 202508); all 14 rows scored; 10 rows have a single term; `other_instructor_count` 0 |
| 1. Named-instructor section | Secondary, no pinned row | CNT 4419 | 14250 (also 14251) | `course`; `ready`, 4 rows; the current instructor has no history, so there is no highlighted "This section" row (this is the designed no-pinned-row state, not a defect) |
| 1. Single-term instructor row | Same page as above | PSY 2012 | 12188 | the pinned row has `term_count` 1 (reads "1 term"); ADV 3101 CRN 13127 is a single-row, three-term course for the one-row, no-"Show all" case |
| 2. Staff section with a ready breakdown | Primary | IDH 4950 | 12497 (also 12498 to 12503, 12505) | `course`; the section's instructor is Staff; `ready`, 14 rows, `other_instructor_count` 1, `current_instructor_has_history` false, no `is_current` row |
| 3. Lab section | Primary | CHM 2045L | 11528 (also 11529, 11530) | breakdown `lab_section`, 0 rows (CHM 2211L CRN 11287 is another) |
| 3. Fallback-scored section (no instructor block) | `subject` source | SYG 3235 | 20075 | `score_source` `subject`, no breakdown |
| 3. Fallback-scored section (no instructor block) | `global` source | CHD 4537 | 13112 | `score_source` `global`, no breakdown (CLT 3511 CRN 20322 is another) |
| 4. More than five instructors | Primary | ENC 1101 | 14045 (41 sections; others 14114, 14124) | `instructor_course`; `ready`, 62 rows (12 unscored, 26 with a single term), current instructor has history; **`other_instructor_count` 0 on all 41 ENC 1101 sections, so no Others line can appear there** (see finding A) |
| 4. Others line with counts only | Substitute for the ENC 1101 Others expectation | ANT 4930 | 10805 | `instructor_course`; 6 rows (so "Show all 6 instructors" holds one row), `other_instructor_count` 4 (cutoff 15 grades) |
| 4. Others line, many rows | Alternative | BSC 4933 | 18286 (also 13615, 18288, 20246) | `instructor_course`; 10 rows, `other_instructor_count` 9 |
| 5. Long instructor name (backstop 1) | Longest name in live data, visible without expanding | CRW 3312 | 13723 | `course`; `ready`, 4 rows; the section's own instructor is the highlighted first row and its name is **18 characters** (the longest in the data) |
| 5. Long instructor name, hidden behind "Show all" | Same length, a row inside the disclosure | IDH 4950 | 12497 | the 18-character name is row 13 of 14 (inside the "Show all 14 instructors" disclosure) |
| 6. InfoTip clipping at 320 px (backstop 2) | Any block with a right-aligned InfoTip | PSY 2012 | 12188 | the block has exactly the one InfoTip |

Longest listed instructor name across every breakdown row of all 3,707 items: **18 characters** (appears in IDH 4950, IDH 4200 CRN 12477, CRW 3312, ENC 1102 CRN 19230, CRW 3112 CRN 13909 and CRW 3111 CRN 13907 among others). The longest `instructor` value on any search item is also 18 characters.

Findings that affect UAT:

- **A. ENC 1101 shows no Others line.** The plan's fourth human check expects "the Others line shows counts only" on an ENC 1101 section, but every ENC 1101 section has `other_instructor_count` 0 (all 62 rows listed qualify). The Others line is exercised on ANT 4930 CRN 10805 or BSC 4933 CRN 18286 instead. On ENC 1101 the check is limited to "at most five rows visible", the "Show all 62 instructors" disclosure, keyboard operation (Enter and Space) and the focus ring.
- **B. The 40-character-name backstop cannot be run with real data.** UI-SPEC long-text row 1 calls for a held-out check at 320 px with a 40-character name. The longest listed name is 18 characters. UAT can run the 320 px wrap check with the 18-character names above (real data, short of the spec length), and a 40-character case needs the text edited in the browser's developer tools or a mock-data build. The backstop is therefore only partly coverable live, and passing it with an 18-character name must not be recorded as the 40-character result.
- **C. CNT 4419 is not a named-instructor-with-history target.** Its two sections are `course`-sourced with no pinned row (the current instructor has no history), so it does not show the highlighted "This section" row. PSY 2012 CRN 12188 is used for that.

### Queued human checks (end-of-phase UAT; NOT passed)

These are the six `<human-check>` items of plan 10-09 Task 1, carried to `/gsd-verify-work 10`. None has been observed by anyone; the status of each is **queued**.

1. **Named-instructor block (desktop and 320 px).** On the site, search PSY 2012 and expand CRN 12188 (CNT 4419 CRN 14250 for the no-pinned-row state). Expect the "Instructors for this course" block directly under the course-wide figures; the current instructor first, highlighted, labelled "This section"; rows reading "{pct}% A · {n} grades · {k} terms ({first}–{last})"; and the Easiness score, or "Not scored" with "Under N grades". Status: queued.
2. **Staff section.** Expand IDH 4950 CRN 12497: heading "Historically taught by", the explainer saying the instructors do not affect this section's score, no highlighted row, nothing saying "Used in this section's score". Status: queued.
3. **Lab and fallback sections.** Expand CHM 2045L CRN 11528: only the note "Instructor history is not shown for lab sections. The figures above are course-wide." Expand SYG 3235 CRN 20075 and CHD 4537 CRN 13112: no instructor block at all. Status: queued.
4. **More than five instructors.** Expand ENC 1101 CRN 14045: at most five rows visible; "Show all 62 instructors" opens with Enter or Space and is focus-visible. Expand ANT 4930 CRN 10805 (and BSC 4933 CRN 18286) for the Others line, which shows counts only (finding A). Status: queued.
5. **Backstop, UI-SPEC long-text 1.** At 320 px, CRW 3312 CRN 13723 (18-character name, visible) and IDH 4950 CRN 12497 (18-character name inside the disclosure): the name wraps onto further lines with no ellipsis, clipping or horizontal scroll. The 40-character case needs an edited text node (finding B). Status: queued, partly coverable.
6. **Backstop, UI-SPEC long-text 2.** At 320 px, focus or hover the "i" InfoTip in the block (PSY 2012 CRN 12188): the full co-teaching caveat appears without clipping off-screen. Status: queued.
