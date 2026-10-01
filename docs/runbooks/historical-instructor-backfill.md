# Historical Instructor Backfill Runbook

Use this runbook to run the one-off historical instructor backfill (Phase 10): fetch the five historical grade terms from USF, store the graded sections and their instructors, rebuild the live term's ranking cache, and check that the instructor-level scores are what you reviewed. It also covers undoing the data write and undoing a scoring change.

## Purpose and policy

Production holds grade rows for five historical terms but no `sections` or `section_instructors` rows for them, so the instructor-course join can never match. The backfill creates those rows, and only for CRNs that already have a stored grade row (D-06). After it commits, the live term's `section_rankings` cache is rebuilt in the same transaction, so the new instructor-level scores go live atomically.

- **Request policy (D-22(e)):** five terms only (`202408`, `202501`, `202505`, `202508`, `202601`), one whole-term request per term per invocation, at least 10 s between terms (default 30 s), no retries. A `--dry-run` and an `--apply` are separate invocations, so a dry run followed by an apply is two requests per term. Do not repeat either without a reason; if one fails, read the report before running it again.
- **Operator-run only (D-05):** run it from a workstation. It is never added to the Render worker, `render.yaml` or the Docker image, and it never touches the live sync's change-only or removal logic.
- **Same lock as the worker (D-22(c)):** `--apply`, `--rollback` and `--rebuild-only` take the sweep advisory lock before anything else. If a live sweep holds it, they exit `2` with nothing written; wait a minute and retry.
- **Nothing is committed by a dry run.** The what-if runs inside a transaction that is always rolled back.
- **No requests in undo modes.** `--rollback` and `--rebuild-only` never contact USF.
- Output is counts only: no URLs, no instructor names.

## Preconditions

- You are on a checkout at the merged `origin/main` (verify with `git fetch origin` and `git merge-base --is-ancestor origin/main HEAD`).
- `DATABASE_URL` is set to the Supabase **transaction pooler** (host ends in `.pooler.supabase.com`, port `6543`). Check this without printing the URL, user or password.
- The worker is healthy: `curl -fsS https://easy-a-api.onrender.com/api/v1/metadata/sync-status?term=202701` shows `last_status` `succeeded` and `is_stale` `false` (Hosted Beta Operations, section 1). Do not start the backfill while a sweep is failing.
- Migration 0004 is applied (hosted Supabase already has it).
- Pick a directory outside the repository for the report files. Never commit them.

## 1. Dry run

```bash
uv run python scripts/backfill_historical_sections.py --dry-run --report-json <path>
```

By default all five terms are fetched, 30 s apart, and the what-if is computed for `202701` (`--what-if-term`). The command prints one JSON object and exits `0` only when no guard failed, the new code reproduces the stored cache (`code_only_parity` PASS) and the course-level invariant holds. `<path>` receives the same object with the per-section `changes` lists added.

Read, in this order:

1. **Per-term counts** under `terms.<term>`: `fetched_rows` (rows USF returned), `grade_crns` (graded CRNs stored for the term), `to_write` (graded sections that will be stored), `inserted` and `updated` (what apply would do), `instructor_rows_added`. `to_write` plus the skipped counts (`non_tampa`, `grade_course_unattributed`, `course_key_mismatch`, `uncataloged`) accounts for every graded row; `not_graded` rows are ignored on purpose.
2. **`unmatched_grade_crns` and `unmatched_fraction`**: graded CRNs USF no longer lists. Above 2 % the run stops with `guard_failures: ["unmatched_fraction"]` and exit 1. Do not raise `--max-unmatched-fraction` to get past it without understanding why the CRNs are missing.
3. **`guard_failures`**: `zero_rows` (USF returned no rows), `unmatched_fraction`, `duplicate_crn`. Any entry means exit 1 and a stop. A failed apply writes nothing.
4. **`section_type_histogram` and `delivery_method_histogram`**: expect mostly `Class Lecture`. Check that `Laboratory` appears with the exact spelling the lab rule matches. A new or unfamiliar type name is a finding to report before applying, because only the exact normalized value `laboratory` is treated as a lab (D-13).
5. **`staff_or_blank`**: sections whose instructor is "Staff" or blank. They are stored but make no instructor pair.
6. **`what_if.verdicts`**:
   - `code_only_parity` must be `PASS`: the new scoring code, run on today's data, reproduces the stored cache (float scores equal within the 1e-9 tolerance below; everything else exactly). `FAIL` means the cache is stale or was edited, so any later diff would mix two causes. Rebuild (section 5, `--rebuild-only`) or investigate first.
   - `course_level_invariant` must be `PASS`: after the backfill, no course-level, subject-level or global score moved. A violation names the CRNs in `what_if.ranking_diff.course_level_violations`.
   - `pairs_match_reference` should be `PASS`; see below.

   **Float tolerance.** The two float score fields (`easiness_score`, `smoothed_withdrawal_rate`) are compared with an absolute tolerance of `1e-9` (`SCORE_TOLERANCE` in `src/easy_a/rankings/diff.py`), in the dry-run gates, the `--apply` gate and `scripts/report_ranking_diff.py` alike. The stored cache and a workstation recomputation differ by a few units in the last place (live 202701 check on 2026-10-01: at most 5.33e-15, no source, label, count or rank change; the same gap exists with the pre-Phase-10 code), so an exact comparison could never return PASS. Anything larger than the tolerance still fails. `effective_n`, `confidence_label`, `score_source`, CRN identity and rank are compared exactly. The noise is reported, not hidden: each diff object carries `float_noise` (`tolerance`, `count` of sections with a within-tolerance float difference, and `max_abs_delta`). Expect a large `count` and a `max_abs_delta` around 1e-14; a `max_abs_delta` near 1e-9 is worth investigating.
7. **`what_if.ranking_diff`**: `changed` (sections whose score fields changed), `transitions` (expected: `course->instructor_course` only), `abs_delta` and `abs_delta_buckets` (how far scores moved), `rank_shift`, and `top_changes` (the largest movers). The full per-section list is in the report file under `what_if.ranking_diff.changes`.

**Pairs comparison.** `what_if.pairs` is the join re-measure inside the rolled-back transaction. It compares the number of (instructor, course) pairs with the 2026-09-28 feasibility report:

| Measure | Reference |
|---|---|
| Pairs | 3,216 |
| Pairs with effective n >= 60 | 1,329 |
| Pairs with effective n >= 30 | 2,178 |
| Pairs with effective n >= 15 | 2,829 |

`pairs_match_reference` is `PASS` only when all four match; `what_if.pairs.deltas` shows measured minus reference for every number. A `FAIL` does not change the exit code, but it blocks the go-live review (section 2) until the difference is explained.

## 2. D-04 review

The project owner approves the diff; the agent or operator who ran the dry run does not. Review the report against D-04: which sections change score and rank and by how much, and confirmation that course-level scores are unchanged.

Approve only when all of these hold:

- Exit code `0`, `guard_failures` empty for every term, and `unmatched_fraction` small and explained.
- `code_only_parity` `PASS` and `course_level_invariant` `PASS`.
- Every transition is `course->instructor_course`, and the size of `abs_delta` and the `top_changes` are acceptable to the owner.
- `pairs_match_reference` `PASS`, or every delta in `what_if.pairs.deltas` is explained and accepted in writing.
- The histograms contain no surprise section types.

Any of these blocks the apply: a failed guard, a `FAIL` verdict, a non-`instructor_course` transition, or an unexplained pairs delta. Write the decision, the date and the `inserted` total in the Run Log. That total is the value for `--expect-inserted` in the next step.

## 3. Apply

```bash
uv run python scripts/backfill_historical_sections.py --apply --rebuild-term 202701 --expect-inserted <N from the dry run> --report-json <path>
```

`<N>` is the sum of `terms.<term>.inserted` over the five terms in the reviewed dry run.

In one transaction, in this order, the command: takes the sweep lock; reads the stored cache for `202701`; writes the sections, instructor rows and one `ingest_runs` row per term; rebuilds `section_rankings` for `202701`; and diffs the stored cache before and after. It commits only when the course-level invariant holds and the inserted total equals `--expect-inserted`. The printed `applied` object is that stored-before versus stored-after diff.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Committed. Sections, instructors, ingest rows and the rebuilt cache are live together. |
| `1` | Nothing was written. A fetch or guard failed (`error_kind` `usf_http`, `usf_timeout`, `usf_response`, `parse`, `guard`, `database`), the course-level invariant failed (`error_kind` `course_level_invariant`), or the inserted count differed from `--expect-inserted` (`error_kind` `expect_inserted`; `applied.expect_inserted` shows the expected and actual numbers). |
| `2` | Nothing was written. Either a usage error (for example `--rebuild-term` missing), or `status` `busy`: a live sweep holds the sweep lock. |

A count mismatch means the data changed since the review. Do not edit `--expect-inserted` to match: run a new dry run and review it again.

## 4. Verify

Run these against the hosted database after exit `0`. All are read-only.

```bash
uv run python scripts/measure_instructor_pairs.py --report-json <path>
uv run python scripts/report_ranking_diff.py --term 202701 --report-json <path>
uv run python scripts/inventory_tampa_grades.py
uv run python scripts/validate_tampa_ingest.py --term 202701
uv run python scripts/benchmark_rankings_search.py --remote-url https://easy-a-api.onrender.com --iterations 50
```

- `measure_instructor_pairs.py` exits `0` when the pairs, n >= 60, n >= 30 and n >= 15 numbers equal the 2026-09-28 report (3,216 / 1,329 / 2,178 / 2,829).
- `report_ranking_diff.py --term 202701` exits `0` when the stored cache equals a fresh recomputation. It should, because the apply rebuilt it.
- `inventory_tampa_grades.py` and `validate_tampa_ingest.py` must still report their existing PASS verdicts: the backfill must not change grade coverage or the Tampa ingest totals.
- The hosted benchmark checks search latency. The MVP-1 target is p95 under about 1.5 s (Hosted Beta Operations, section 7). Read the whole distribution, because the first request after idle can be slow.
- Check the worker log or `sync-status`: the next sweep must succeed and must not mark any historical section removed (historical rows are never touched by a live sweep).

Record the numbers in the Run Log.

## 5. Roll back

Two separate undo paths exist. Neither contacts USF.

**Undo the data write.** Preview first:

```bash
uv run python scripts/backfill_historical_sections.py --rollback --rebuild-term 202701
```

The preview does the deletion and the cache rebuild inside a transaction it always rolls back, and prints `terms.<term>.eligible_sections` and `ineligible_sections`, `deleted_sections` (what the commit would delete) and the `applied` diff (the expected transition is `instructor_course->course`). A section is eligible only when it belongs to one of the five historical terms, has no seat snapshot, has no syllabus linked to it, and every instructor row on it came from the backfill. Anything else is kept and counted as ineligible; `202701` sections are never eligible. Then commit:

```bash
uv run python scripts/backfill_historical_sections.py --rollback --rebuild-term 202701 --yes
```

This deletes the eligible sections and their instructor rows and rebuilds the `202701` cache in one transaction under the sweep lock. `ingest_runs` rows are history and are kept. After it, `report_ranking_diff.py --term 202701` should exit `0` and the instructor-level scores return to course level.

**Undo a scoring change only.** If the backfill is fine but the scoring constants need to go back, revert the constants in code, deploy, then rebuild the cache from the reverted code with no data write:

```bash
uv run python scripts/backfill_historical_sections.py --rebuild-only --rebuild-term 202701
```

Run it from a checkout at the reverted code. It rebuilds the `202701` cache under the sweep lock, makes no request and writes nothing but the cache, and prints the `applied` diff. The live worker also rebuilds the cache after every changed sweep, so deploy the reverted code first or the next sweep will publish the old scoring again.

For all three modes `--rebuild-term` is required and must be a six-digit term that is not one of the five historical terms. Exit `2` with `status` `busy` means a live sweep holds the lock; nothing was changed, so retry shortly. The `applied` diff of the undo modes is reported but never blocks the undo.

## Run Log

| Date (UTC) | Operator | Action | Command / setting | Result | Justification |
|---|---|---|---|---|---|
| | | | | | |
