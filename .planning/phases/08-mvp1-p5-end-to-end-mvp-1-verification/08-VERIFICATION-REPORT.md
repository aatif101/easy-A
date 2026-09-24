# Phase 8 (MVP1-P5) — End-to-End Verification Report

Dated hosted-Supabase evidence for REQ-COVERAGE-03, REQ-GRADES-01 and REQ-PERF-01, and the
Phase 8 / MVP-1 (D-21) verdicts. All commands below ran against hosted Supabase, term `202701`,
inside the same UTC window recorded below. No cache rebuild, import, or hosted-data mutation
occurred anywhere in this phase.

## Snapshot

| Field | Value |
|---|---|
| UTC window start | 2026-09-24T18:29:44Z |
| UTC window end (Task 3 close) | see "## Verdicts" |
| `git rev-parse HEAD` (start) | `c55dfdcc0d538b7d5497a41f6e7b1a1c1c88d877` |
| Branch | `codex/phase8-replan` |
| `origin/main` (fetched, D-10) | `c063c27727f9cb87bb55da7b8f2ea76175abab67` |
| Term | `202701` |
| Environment (sanitized) | Supabase (from `inventory_tampa_grades.py`'s `_environment_label`, which reports only `SQLite` / `Supabase` / `Postgres (other host)` / dialect name — never a hostname or credential) |
| Inventory `observed_at_utc` | 2026-09-24T18:29:52.520931+00:00 |

Totals are verified against persisted aggregates (the live inventory CLI and the dated import
ledger), not re-read from raw workbooks — workbooks are outside Git (D-19) and no external source
is re-queried in this phase.

## Gates

| Gate | Status | Evidence command | UTC time | Denominator | Reason |
|---|---|---|---|---|---|
| REQ-COVERAGE-03 validator (suffix-exact + reconciliation) | PASS | `uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` | 2026-09-24T18:31:32Z–18:34:10Z | 3,783 sections / 1,402-entry target list | `PASS suffix-exact`, `PASS reconciliation` printed; stored/coverage/rankings counts agree; every stored course is a configured target |
| REQ-COVERAGE-03 API identity | PASS | `uv run python scripts/verify_rankings_pages.py --term 202701 --http-base-url http://127.0.0.1:8000` | 2026-09-24T18:36:21Z | 3,783 stored sections | `verdict: PASS`; stored_count=cache_count=api_total=3,783; 19 pages; 0 missing/extra/duplicate/non-Tampa; `api_score_source_split` matches the inventory's per-score_source split exactly |
| REQ-GRADES-01 D-21 inventory | PASS | `uv run python scripts/inventory_tampa_grades.py --term 202701 --exceptions-md .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md` | 2026-09-24T18:29:52Z | 3,783 sections | `verdicts.integrity`=PASS, `verdicts.d21_grade_coverage`=PASS; 3,122 evidence-backed, 661 listed exceptions |
| REQ-GRADES-01 validator honest-coverage | PASS | `uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` | 2026-09-24T18:31:32Z–18:34:10Z | 3,422 `course`-sourced cache rows | `PASS honest-coverage (verified non-letter-grade exceptions: 300)`; 300 == inventory's `exception_non_letter_grade` (300) exactly |
| REQ-GRADES-01 evidence wording | pending Task 3 | `npm --prefix web test` (08-03 `RankingEvidence.test.tsx`, 8 tests) | — | 8 component tests across 4 evidence scopes × 2 layouts | 08-03-SUMMARY.md already recorded all 8 passing; Task 3 reconfirms in the full regression run. Browser-viewport observation NOT MEASURED (no Chromium in this environment; logged in `.planning/WINDOWS.md` entry 8) |
| Grade provenance by term | PASS | see "## Provenance by term" | 2026-09-24T18:29:52Z | 5 historical terms, 8,662 rows | Live per-term counts equal the ledger's "Final result" table and 05-IMPORT-RECORD.md exactly, 0 deltas |
| Quality (202701) | PASS | `uv run python scripts/check_data_quality.py --term 202701 --json` | 2026-09-24T18:36:29Z–18:36:33Z | 3,783 sections | 0 errors, 1,058 warnings (`low_confidence_ranking`), 50 info (`no_historical_analytics`) — reproduces the ledger's final quality baseline exactly |
| REQ-PERF-01 p95 | PASS | `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50` | 2026-09-24T18:36:44Z–18:36:59Z | 50 calls, 5 warmups, single client | p50 220.15 ms, p95 277.25 ms, max 340.29 ms, dataset 3,783 sections, loopback HTTP over hosted Supabase (transaction pooler). p95 < 1,500 ms |
| D-02 invariance | pending Task 3 | `git fetch origin main && git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api src/easy_a/models migrations web/src/types web/src/api` | — | 7 paths | — |
| D-19 hygiene | pending Task 3 | `test -z "$(git ls-files -- '*.xlsx' '*.xls' '*.csv')"` | — | repo-tracked files | — |

## D-21 grade coverage

Live inventory (`scripts/inventory_tampa_grades.py --term 202701`), observed
2026-09-24T18:29:52.520931+00:00 against hosted Supabase:

| Metric | Value |
|---|---|
| Sections (snapshot) | 3,783 |
| Represented courses | 1,401 |
| Cache rows | 3,783 (refreshed_at min=max 2026-09-23T21:51:28.116181+00:00) |
| Grade rows | 8,662 (ingested_at max 2026-09-23T21:36:34.907224+00:00) |
| Non-Tampa sections | 0 |
| **Evidence-backed sections** | **3,122** (courses: 1,117) |
| **Exception sections** | **661** total — `no_rows` 361 (courses: 232), `non_letter_grade` 300 (courses: 52) |
| Integrity counters | `unattributed_grade_rows`=0, `bucket_sum_mismatch_rows`=0, `rows_at_or_after_term`=0, `stale_cache`=false, `non_tampa_section_count`=0 |
| Verdicts | `integrity`=PASS, `d21_grade_coverage`=PASS |

Exception list: `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md`
(machine-generated by `--exceptions-md`, never hand-transcribed; 661 rows sorted by
subject/course/CRN; counts-by-reason header: `no_rows: 361`, `non_letter_grade: 300`, matching
the inventory JSON exactly). Every exception carries one of two fixed, non-inventive reason
notes:

- `no_rows`: "No stored grade rows exist for the exact course key in the imported range (USF
  InfoCenter, Spring 2025 - Spring 2026; Summer 2026 checked empty). Stored data cannot
  distinguish InfoCenter's under-five-student omission, a new course, or a course not offered in
  the window — no narrower cause is assigned (D-06, D-07)."
- `non_letter_grade`: "Stored own-course grade rows exist for this course key with zero A-F
  (letter-grade) weight — the course reports only non-letter outcomes (e.g. S/U or pass/fail).
  The prior fallback is presented honestly, never as own-course letter-grade evidence (D-20,
  D-21)."

**D-21 source basis:** the source-side check (USF InfoCenter, Spring 2025 through Spring 2026;
Summer 2026 returned no rows) is documented in `.planning/grade-coverage-import-2026-09-23.md`.
The stored-data side is this inventory run: `window.window_terms` = `{202501: 2096, 202505: 465,
202508: 2887, 202601: 3035}`, `window.checked_empty_terms` = `{202605: 0}`, and
`window.outside_window_rows` = 179 (the 202408 Fall 2024 pilot rows, correctly reported outside
the D-21 window rather than silently dropped).

**Validator cross-check:** `scripts/validate_tampa_ingest.py`'s honest-coverage check reports
`PASS honest-coverage (verified non-letter-grade exceptions: 300)`. This count (300) equals the
inventory's `exception_non_letter_grade` section count (300) exactly, satisfying the plan's
cross-script key_links contract — a mismatch here would have been REQ-GRADES-01 FAIL.

**Fallbacks and course rows with effective_n = 0 are not counted as course history.**

## Provenance by term

Live per-term grade-row counts from the inventory run, compared against the dated import ledger
(`.planning/grade-coverage-import-2026-09-23.md`, "Final result") and, for the 202408 pilot term,
against `05-IMPORT-RECORD.md`'s all-course coverage table:

| Term | Inventory rows | Inventory total_grades_sum | Ledger rows | Ledger source | Delta |
|---|---:|---:|---:|---|---:|
| 202408 (outside D-21 window; Fall 2024 pilot) | 179 | 7,544 | 179 rows / 7,544 raw grades | `05-IMPORT-RECORD.md` all-course table (sum of DB `total_grade_count` column) | 0 |
| 202501 | 2,096 | 82,029 | 2,096 | `grade-coverage-import-2026-09-23.md` "Final result" | 0 |
| 202505 | 465 | 18,388 | 465 | `grade-coverage-import-2026-09-23.md` "Final result" | 0 |
| 202508 | 2,887 | 117,629 | 2,887 | `grade-coverage-import-2026-09-23.md` "Final result" | 0 |
| 202601 | 3,035 | 119,243 | 3,035 | `grade-coverage-import-2026-09-23.md` "Final result" | 0 |
| **Total** | **8,662** | — | **8,662** | — | **0** |

**Provenance verdict: PASS.** Every per-term row count matches its dated ledger source exactly;
no delta requires an explanation. 202408's raw total (7,544) also matches
`05-IMPORT-RECORD.md`'s sum of the DB `total_grade_count` column (554+482+1,037+227+500+652+
1,715+1,138+490+749 = 7,544) exactly.

**Sanity check against this plan's expected baseline (2026-09-23 live read, objective section —
not a pass condition):** the live 2026-09-24 read reproduces the baseline exactly: 3,783 sections
/ 1,401 courses; 3,122 evidence-backed; 661 exceptions = 361 no_rows + 300 non_letter_grade;
grade rows by term 202408 179 / 202501 2,096 / 202505 465 / 202508 2,887 / 202601 3,035 (8,662).
Zero deltas from the baseline.

## Identity, quality and performance (Task 2)

All three commands below ran against a local `uvicorn easy_a.api.app:app --host 127.0.0.1 --port
8000 --no-access-log` process using the same `DATABASE_URL` (hosted Supabase) as Task 1's
inventory run. The server was confirmed ready with a 200 from
`GET /api/v1/rankings/search?term=202701&limit=1` on the first attempt, and was stopped
immediately after the benchmark completed (verified: no stray `uvicorn` process remained).

### REQ-COVERAGE-03 API identity

`scripts/verify_rankings_pages.py --term 202701 --http-base-url http://127.0.0.1:8000`, observed
2026-09-24T18:36:21.918589+00:00:

| Field | Value |
|---|---|
| verdict | PASS |
| stored_count / cache_count / api_total | 3,783 / 3,783 / 3,783 |
| pages_fetched | 19 (page_size 200) |
| missing_count / extra_count / duplicate_count | 0 / 0 / 0 |
| non_tampa_count / order_violations | 0 / 0 |

`api_score_source_split` (from the live page walk) vs. the Task 1 inventory's per-score_source
section counts:

| score_source | API split (count / effective_n=0) | Inventory (evidence_backed + non_letter_grade / no_rows) | Match |
|---|---|---|---|
| course | 3,422 / 300 | 3,122 evidence_backed + 300 exception_non_letter_grade = 3,422 total, 300 at effective_n=0 | Exact |
| subject | 311 / 0 | 311 of the 361 `exception_no_rows` sections | Exact |
| global | 50 / 50 | 50 of the 361 `exception_no_rows` sections (311 subject + 50 global = 361) | Exact |

No difference between the API's exposed score-source split and the inventory's cached-state
split — the API is exposing the same evidence state the inventory classified, confirming
REQ-GRADES-01's cross-check.

### Quality (202701)

`scripts/check_data_quality.py --term 202701 --json`, run 2026-09-24T18:36:29Z–18:36:33Z:

| Field | Value |
|---|---|
| section_count | 3,783 |
| error_count | 0 |
| warning_count | 1,058 (`low_confidence_ranking`: 1,058) |
| info_count | 50 (`no_historical_analytics`: 50) |

This reproduces the dated import ledger's final quality baseline exactly (0 errors, 1,058
low-confidence warnings, 50 no-history info items). **Scope note:** `_check_grades` in
`src/easy_a/quality/checks.py` filters `GradeDistribution.term_id == term.id` — it inspects only
grade rows stamped with the *current* term (202701), which has none (all historical grade rows
carry a historical term). It therefore cannot see `unattributed_grade_row` or
`grade_total_mismatch` findings for the historical 202408/202501/202505/202508/202601 rows this
report's D-21 gate depends on. That is why the D-21 inventory's own integrity counters
(`unattributed_grade_rows`=0, `bucket_sum_mismatch_rows`=0 — see "## D-21 grade coverage") are the
authoritative check for historical-row integrity, not this term-scoped quality pass.

### REQ-PERF-01 p95

`scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701
--iterations 50`, run 2026-09-24T18:36:44Z–18:36:59Z (5 warmups, 50 measured calls, single
client, loopback HTTP over hosted Supabase transaction pooler):

| Metric | Value |
|---|---|
| Dataset size | 3,783 sections (stored term) |
| Iterations | 50 |
| p50 | 220.15 ms |
| p95 | **277.25 ms** |
| max | 340.29 ms |

**REQ-PERF-01 gate: p95 = 277.25 ms < 1,500 ms. PASS.** The run was not interrupted; all 50
calls completed. **Concurrent-user, deployed-host and browser latency: NOT MEASURED** — this
gate is single-client, serial, loopback HTTP only.

### Before/after snapshot comparison

Re-ran `scripts/inventory_tampa_grades.py --term 202701` (no `--exceptions-md`) after Task 2's
gates and the server shutdown, observed 2026-09-24T18:37:14Z. Compared against Task 1's snapshot
(observed 2026-09-24T18:29:52Z):

| Snapshot field | Task 1 | Task 2 (after) | Changed? |
|---|---|---|---|
| section_count | 3,783 | 3,783 | No |
| cache_row_count | 3,783 | 3,783 | No |
| cache_refreshed_at_max | 2026-09-23T21:51:28.116181+00:00 | 2026-09-23T21:51:28.116181+00:00 | No |
| grade_row_count | 8,662 | 8,662 | No |
| grade_ingested_at_max | 2026-09-23T21:36:34.907224+00:00 | 2026-09-23T21:36:34.907224+00:00 | No |

**No change.** The snapshot held across all live gates in this report — none needed to be
repeated or marked NOT MEASURED for drift. No hosted data was mutated, no cache rebuild or
import ran at any point in this phase.

## Regression and invariance

Filled in Task 3.

## Verdicts

Filled in Task 3.
