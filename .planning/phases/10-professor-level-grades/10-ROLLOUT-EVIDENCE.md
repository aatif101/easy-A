# Phase 10 Rollout Evidence (plan 10-07)

Dated evidence for the pre-merge half of the Phase 10 rollout. No connection strings, hostnames or credentials appear in this file. Every hosted database statement below ran inside a READ ONLY transaction (`SET TRANSACTION READ ONLY`; `transaction_read_only` confirmed `on`). No USF request had been made when Task 1 closed; Task 2 sections are appended below as they are run.

**STATUS: Task 1 parity gate RESOLVED (exit 0). Task 2 dry run FAILED at term 202505 with a parse guard (exit 1, nothing written); the dry run was NOT rerun, per the plan. Awaiting a decision. See "Five-term dry run (D-07)". Original Task 1 note: parity gate RESOLVED (exit 0 after the user's "revise-with-tolerance" decision, commit cef0d5c). The first run was BLOCKED (exit 1, float noise only); that record is kept below. See "Code-only parity (D-03)" and "Re-run after tolerance (D-03)".**

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

## Five-term dry run (D-07)

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

## Row counts before/after

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
