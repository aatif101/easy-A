# Historical Instructor Backfill Runbook

Use this runbook to run the one-off historical instructor backfill (Phase 10): fetch the five historical grade terms from USF, store the graded sections and their instructors, rebuild the live term's ranking cache, and check that the instructor-level scores are what you reviewed. It also covers undoing the data write and undoing a scoring change.

## Purpose and policy

Production holds grade rows for five historical terms but no `sections` or `section_instructors` rows for them, so the instructor-course join can never match. The backfill creates those rows, and only for CRNs that already have a stored grade row (D-06). After it commits, the live term's `section_rankings` cache is rebuilt in the same transaction, so the new instructor-level scores go live atomically.

- **Request policy (D-22(e)):** five terms only (`202408`, `202501`, `202505`, `202508`, `202601`), one whole-term request per term per invocation, at least 10 s between terms (default 30 s), no retries. A `--dry-run` and an `--apply` are separate invocations, so a dry run followed by an apply is two requests per term. Do not repeat either without a reason; if one fails, read the report before running it again.
- **Campus-blank request, Tampa allow-list (Phase 10 gap 05):** the backfill's whole-term request is made with `P_CAMPUS` blank, which asks USF for every campus. The live sync's request stays `campus=T` (D-22(a)) and is not changed here. See "Campus request and the allow-list" below for why.
- **Operator-run only (D-05):** run it from a workstation. It is never added to the Render worker, `render.yaml` or the Docker image, and it never touches the live sync's change-only or removal logic.
- **Same lock as the worker (D-22(c)):** `--apply`, `--rollback` and `--rebuild-only` take the sweep advisory lock before anything else. If a live sweep holds it, they exit `2` with nothing written; wait a minute and retry.
- **Nothing is committed by a dry run.** The what-if runs inside a transaction that is always rolled back.
- **No requests in undo modes.** `--rollback` and `--rebuild-only` never contact USF.
- Output is counts only: no URLs, no instructor names. A parse failure adds structural diagnostics (section 1a), still without any cell text.

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

1. **Per-term counts** under `terms.<term>`: `fetched_rows` (rows USF returned), `rows_by_campus` (every fetched row by schedule campus label), `campus_allowed_rows` (fetched rows on the Tampa allow-list, graded or not), `grade_crns` (graded CRNs stored for the term), `to_write` (graded sections that will be stored), `inserted` and `updated` (what apply would do), `instructor_rows_added`, `response_bytes`. `to_write` plus the skipped counts (`non_tampa`, `grade_course_unattributed`, `course_key_mismatch`, `uncataloged`) accounts for every graded row; `not_graded` rows are ignored on purpose. `non_tampa_by_label` splits `non_tampa` by campus label and `unknown_campus_labels` lists the labels in it that are neither on the allow-list nor a known non-Tampa label; read both before approving (a label you do not recognise needs a decision, it is never silently kept). Top-level `request` shows the campus parameter and the allow-list used, and `fetch_seconds` the time per term request.
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

### 1a. When a term fails the parse guard

`error_kind` `parse` with `error` starting `Parsed N rows from M data rows; refusing a response that silently lost rows.` means the lost-rows guard (the same fail-closed guard the live sweep uses) found a different number of parsed rows than `<tr>` blocks holding `<td>` cells. Nothing was written, the run stopped at that term, and later terms were not requested (no retry, per D-22(e)). The guard itself is unchanged; the report now says where to look.

`parse_diagnostics` (also appended in short form to `error`):

| Field | Meaning |
|---|---|
| `expected_rows`, `parsed_rows`, `difference` | The two counts from the error message. `difference > 0`: rows dropped; `< 0`: a block swallowed a neighbour. |
| `suspect_total`, `suspect_rows_omitted` | Rows that did not parse to exactly one row when parsed alone, and how many fell past the cap (10 are listed). |
| `suspect_rows[].position` | 0-based among **data rows** (blocks with a `<td>`), the unit the guard counts. Row `#2174` is the 2,175th data row. |
| `suspect_rows[].block_index` | 0-based among **all** `<tr>` blocks after the header row; use it to find the row in a saved response. |
| `cell_count` | Direct `<td>` children, which must equal the 24 expected headers or the parser skips the row. |
| `td_tag_count` | Every `<td` tag in the block. More than `cell_count` means cells nested deeper (a nested table). |
| `nested_table`, `colspan_cells` | A `<table>` inside the block; cells with `colspan` or `rowspan`. |
| `isolated_rows` | Rows the parser returned for the block alone: `0` dropped, `2+` the block swallowed the next row (missing `</tr>`). |
| `cell_shape` | One character per direct cell: `.` empty, `d` digits only, `a` anything else (capped at 40, `+` marks truncation). Structure only. |
| `crn`, `crn_shape` | The CRN cell if it is purely digits; otherwise `null` with `absent`, `empty` or `non_numeric_<n>_chars`. |
| `fingerprint` | A one-line reading: for example `missing FEES` (23 cells), `1 spanning cells, crn absent` (a colspan placeholder or banner row), `nested table`, `block holds 2 rows`. |
| `mismatched_chunks[]` | The 250-row chunks whose data-row and parsed counts differ (`first_position`, `data_rows`, `parsed_rows`). If `suspect_rows` is empty the mismatch depends on chunk context; look in these windows. |
| `inspection_failed` | `true` if the diagnostic pass itself failed; the counts and chunks are still valid. |

Only counts, positions, fixed labels and a digits-only CRN are reported: no URLs, instructor names, titles or raw HTML.

**Keeping the raw response.** Add `--save-failed-response PATH` to the dry run or apply. It is off by default and the file is written only when a term's response fails the parse guard (the lost-rows guard, a missing header row, or an unparseable subject/course cell); a successful run and every other failure kind write nothing. The text is saved as decoded, with mode `0600`. The file names instructors, so it must never be committed: `PATH` must be outside the repository, or under `.planning/phases/10-professor-level-grades/failed-responses/`, which is git-ignored. Any other path inside the repository is refused with exit 2 before any request.

```bash
uv run python scripts/backfill_historical_sections.py --terms 202505 --dry-run --save-failed-response .planning/phases/10-professor-level-grades/failed-responses/202505.html --report-json <path>
```

The report then carries `saved_response` (`saved`, `path`, `bytes`; or `saved: false` and an exception name if the write failed, which never hides the parse failure). Inspect the suspect block locally, for example by counting `<tr` blocks to `block_index` after the header row. Each rerun is a new whole-term request per term, so only rerun with a reason.

**Known USF quirk: unterminated anchors in a note cell (Phase 10 gap 03).** The 202505 response held one legitimate 24-cell section whose note cell contained a hand-typed link: a non-breaking space inside the `<a` tag, a curly-quote `href`, and a closing `</a` that never reached its `>`. The HTML parser read that broken end tag as running on into `</td>`, left the anchor open, and nested the remaining cells inside it, so the row came back with 8 direct cells (`8/24 cells`, `24 td tags vs 8 direct cells` in the fingerprint) and the guard refused the term. `parse_whole_term` now repairs this before counting and parsing, for the live sync and the backfill alike: inside each row block it closes a `</a` and a `<a ...` that have no `>` before the next `<`, by inserting a `>` and changing nothing else. The guard condition is unchanged, so every other lost-row shape (23 or 25 cells, placeholder rows, a missing `</tr>`, a nested table) is still refused. If the fingerprint of a failing row still reads `td tags vs direct cells` with no nested table, look for another unterminated tag in its note cell.

### 1b. Campus request and the allow-list

**What changed and why.** Dry run 2 (2026-10-01) failed `unmatched_fraction` in all five terms: 1,500 of 8,662 graded CRNs (17.3%) were not in the responses. The cause (`10-GAP-04-UNMATCHED-CRNS.md`, confirmed by a one-request probe) is that USF lists a large block of Tampa-credited sections, mostly online or off-site "Other" types, under the schedule campus label `Off-campus - Tampa`, while the grade source files the same sections under `0001 - Tampa Campus`. A `campus=T` request never returns them. The backfill therefore requests each term with a blank campus (every campus) and decides itself which rows to keep; the fix is `10-GAP-05-CAMPUS-FIX.md`.

**Selection rule.** A fetched row is kept only if it has a stored grade row (D-06), its course key matches, and its campus label, with whitespace collapsed and case ignored, is on the allow-list `{Tampa, Off-campus - Tampa}`. Nothing else is tolerated: `Off-campus-Tampa` (no spaces) or `Tampa Campus` are not on the list. `St. Petersburg`, `Off-campus - St. Petersburg`, `Sarasota-Manatee`, `Off-campus - Sarasota-Manatee` and any other label are excluded, counted in `non_tampa` and broken out in `non_tampa_by_label`; a label that is not one of those four known ones also appears in `unknown_campus_labels`. Excluded rows never become `sections` rows.

**Unchanged.** The `unmatched_fraction` definition (graded CRNs absent from the whole response, over graded CRNs) and its 2% default, `--max-unmatched-fraction`, the lost-rows parse guard and the unterminated-anchor repair all apply to the all-campus response exactly as before. With the corrected request the expected unmatched fraction is near zero; if it is still above 2%, stop and diagnose, do not raise the limit.

**Payload.** An all-campus response is larger than `campus=T`. Offline parsing of a saved page, scaled up with repeated rows, showed linear, bounded cost (a 5.7 MB page: 2.5 s and about 170 MB process RSS; an 11.4 MB page: 4.5 s and about 240 MB); the 25 MB response cap and the 120 s read timeout were left unchanged. A dry run reports `response_bytes` per term so any growth is visible; if a term fails with `error_kind` `usf_response` ("exceeded N bytes") or `usf_timeout`, that is the signal to revisit those limits.

**Live term blind spot (separate follow-up, not changed here).** The live sync still requests `campus=T` and its scope filter keeps only the exact label `Tampa`, so it has the same blind spot for the live term. That is a product coverage question under D-22(a) and D-06/D-07, tracked in `10-GAP-05-CAMPUS-FIX.md`, and is not part of this runbook.

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
