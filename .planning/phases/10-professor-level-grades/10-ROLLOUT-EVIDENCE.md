# Phase 10 Rollout Evidence (plan 10-07)

Dated evidence for the pre-merge half of the Phase 10 rollout. No connection strings, hostnames or credentials appear in this file. Every hosted database statement below ran inside a READ ONLY transaction (`SET TRANSACTION READ ONLY`; `transaction_read_only` confirmed `on`). No USF request had been made when Task 1 closed; Task 2 sections are appended below as they are run.

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
