# Phase 10 Rollout Evidence (plan 10-07)

Dated evidence for the pre-merge half of the Phase 10 rollout. No connection strings, hostnames or credentials appear in this file. Every hosted database statement below ran inside a READ ONLY transaction (`SET TRANSACTION READ ONLY`; `transaction_read_only` confirmed `on`). No USF request has been made in this plan so far, and the dry run (Task 2) has NOT been run.

**STATUS: BLOCKED at Task 1. The code-only parity gate (D-03) returned exit 1, not the required exit 0. Task 2 (dry run) was not run, per the plan. See "Code-only parity (D-03)".**

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

Command: `uv run python scripts/report_ranking_diff.py --term 202701`, run from the workstation at 2026-10-01T06:31:00Z to 06:31:04Z. **Exit code 1 (differences). The required result was exit 0 (identical). The plan's instruction on exit 1 is to stop and present this evidence, so Task 2 was not run.**

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
