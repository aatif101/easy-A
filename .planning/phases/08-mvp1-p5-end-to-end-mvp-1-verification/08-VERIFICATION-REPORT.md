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
| REQ-GRADES-01 evidence wording | PASS | `npm --prefix web test` (08-03 `RankingEvidence.test.tsx`, 8 tests) | 2026-09-24T18:39:45Z | 8 component tests across 4 evidence scopes × 2 layouts | All 8 pass (part of 86/86 frontend suite). Browser-viewport observation NOT MEASURED (no Chromium in this environment; logged in `.planning/WINDOWS.md` entry 8) |
| Grade provenance by term | PASS | see "## Provenance by term" | 2026-09-24T18:29:52Z | 5 historical terms, 8,662 rows | Live per-term counts equal the ledger's "Final result" table and 05-IMPORT-RECORD.md exactly, 0 deltas |
| Quality (202701) | PASS | `uv run python scripts/check_data_quality.py --term 202701 --json` | 2026-09-24T18:36:29Z–18:36:33Z | 3,783 sections | 0 errors, 1,058 warnings (`low_confidence_ranking`), 50 info (`no_historical_analytics`) — reproduces the ledger's final quality baseline exactly |
| REQ-PERF-01 p95 | PASS | `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50` | 2026-09-24T18:36:44Z–18:36:59Z | 50 calls, 5 warmups, single client | p50 220.15 ms, p95 277.25 ms, max 340.29 ms, dataset 3,783 sections, loopback HTTP over hosted Supabase (transaction pooler). p95 < 1,500 ms |
| D-02 invariance | PASS | `git fetch origin main && git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api src/easy_a/models migrations web/src/types web/src/api` | 2026-09-24T18:38:18Z | 7 paths | empty diff against `origin/main` (`c063c27`) |
| D-19 hygiene | PASS | `test -z "$(git ls-files -- '*.xlsx' '*.xls' '*.csv')"` | 2026-09-24T18:38:18Z | repo-tracked files | no spreadsheet/CSV export tracked |

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

`git fetch origin main` (D-10) confirmed `origin/main` = `c063c27727f9cb87bb55da7b8f2ea76175abab67`,
matching STATE.md's recorded value exactly (no drift since 2026-09-23).

### D-02 invariance

```
git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api \
  src/easy_a/models migrations web/src/types web/src/api
```

**PASS — empty diff.** None of the 7 scoring/cache/API/model/migration/frontend-contract paths
differ from `origin/main`. Scoring model and API response contract are unchanged by Phase 8.

### D-19 hygiene

```
test -z "$(git ls-files -- '*.xlsx' '*.xls' '*.csv')"
```

**PASS — empty.** No spreadsheet or CSV export is tracked in the repository.

### Full suite results

| Suite | Command | Result | Planning-time baseline (2026-09-23) |
|---|---|---|---|
| Python (full) | `uv run pytest -q` | **366 passed, 3 skipped** (9.48s) | 324 passed / 3 skipped |
| Python (scoped: benchmark, search-contract, cache-parity) | `uv run pytest tests/api/test_benchmark_rankings_search.py tests/api/test_rankings_search_sql.py tests/rankings/test_cache_parity.py -q` | **42 passed** | — |
| Frontend tests | `npm --prefix web test` | **86 passed** (6 files) | 78 passed |
| Frontend typecheck | `npm --prefix web run typecheck` | **clean** (`tsc -b`, no errors) | clean |
| Frontend lint | `npm --prefix web run lint` | **clean** (`eslint .`, no errors) | clean |
| Frontend build | `npm --prefix web run build` | **`✓ built in 1.59s`** | clean |

**PostgreSQL integration status:** `EASY_A_TEST_POSTGRES_URL` was **not set** in this environment.
The 3 skipped tests in the full Python run are the PostgreSQL-specific integration tests, reported
as **skipped**, not passed, per the plan's instruction.

The 366/3 Python figure and the 86 frontend figure both grew from the plan's stated baselines
(324/3 and 78) because 08-01, 08-02 and 08-03 added tests in this phase (+16 identity-scanner
tests, +22 D-21 inventory tests, +4 honest-coverage tests, +8 evidence-wording component tests) —
this is net new coverage, not a changed baseline; 0 regressions in either suite.

### Scoped quality gates (this phase's gate scripts)

```
uv run ruff check scripts/verify_rankings_pages.py scripts/inventory_tampa_grades.py \
  scripts/validate_tampa_ingest.py tests/api/test_verify_rankings_pages.py \
  tests/refresh/test_inventory_tampa_grades.py tests/refresh/test_validate_tampa_ingest.py
uv run mypy scripts/verify_rankings_pages.py scripts/inventory_tampa_grades.py \
  scripts/validate_tampa_ingest.py
```

**Both PASS — 0 issues.** `ruff check` (6 files, including both test files) reports "All checks
passed!"; `mypy` on the three production gate scripts reports "Success: no issues found in 3
source files".

### Repo-wide ruff / mypy (measured, not just re-quoted)

| Check | Planning-time baseline (2026-09-23) | Measured now (2026-09-24) | Delta |
|---|---|---|---|
| `ruff check .` | 2 errors | **2 errors** (unchanged) | 0 |
| `mypy src migrations scripts tests` | 30 errors in 9 files | **36 errors in 11 files** | +6 errors, +2 files |

The `ruff check .` count is unchanged and stays outside files Phase 8 touches. The `mypy` count is
**not** unchanged: the +6/+2 delta is entirely in `tests/api/test_verify_rankings_pages.py` (5
errors: a missing return-type annotation, two untyped-function calls, an unused `type: ignore`,
and an `int()` overload mismatch) and `tests/refresh/test_inventory_tampa_grades.py` (1 error: a
re-export of `scripts.inventory_tampa_grades.os`) — both test files added by 08-01 and 08-02.
This is honestly recorded rather than repeating the stale "pre-dates Phase 8" framing from
`08-VALIDATION.md`'s planning-time baseline, which no longer applies to these two files. Both
files sit outside 08-04's own declared file scope (`08-VERIFICATION-REPORT.md`,
`08-D21-EXCEPTIONS.md`, `08-VALIDATION.md` only), so this plan does not modify them. Logged to
`.planning/WINDOWS.md` as ledger entry 9 (`kind: lint-warning`, phase 08) for follow-up — a
type-annotation cleanup in test files, not a production-code, scoring, cache, API or D-02/D-19
issue, and not a REQ-COVERAGE-03 / REQ-GRADES-01 / REQ-PERF-01 blocker (their gate scripts remain
mypy-clean and every gate above is PASS).

## Verdicts

**Phase 8 verdict: PASS**

Against ROADMAP.md's Phase 8 success criteria:

1. **All ~3,782 Tampa sections searchable; easiness grade-derived wherever data exists.** PASS —
   `verify_rankings_pages.py` proves exact identity-set equality (3,783/3,783/3,783, 0
   missing/extra/duplicate/non-Tampa) through the complete API page walk, and the D-21 inventory
   shows 3,122 sections evidence-backed with 661 sections as listed, honestly-labeled exceptions
   (never counted as course history).
2. **Quality 0 errors; p95 < ~1.5s on Supabase; honest data semantics; API contract + scoring
   model unchanged.** PASS — quality 0 errors (1,058 warnings, 50 info); p95 277.25 ms < 1,500 ms
   (50 calls, 5 warmups, single client); the validator, inventory, API split and 08-03 UI wording
   all agree on the honest evidence state; D-02 diff against `origin/main` is empty.

**MVP-1 verdict (D-21): PASS**

Against `PROJECT.md`'s MVP-1 goal read through D-21 (locked 2026-09-23): every Spring 2027 Tampa
section either has sourced own-course history or is a listed source-limited exception with
D-20-honest fallback labeling.

| Requirement | Status | Evidence |
|---|---|---|
| REQ-COVERAGE-03 | PASS | validator (`PASS suffix-exact`, `PASS reconciliation`) + API identity scan (`verdict: PASS`, 3,783/3,783/3,783) |
| REQ-GRADES-01 | PASS | D-21 inventory (`d21_grade_coverage`=PASS, 3,122 evidence-backed / 661 listed exceptions), validator honest-coverage (`PASS`, 300 verified non-letter-grade exceptions == inventory's 300), API score-source split == cache split exactly, 08-03 evidence-wording tests (8/8 pass) |
| REQ-PERF-01 | PASS | p95 277.25 ms < 1,500 ms, 50 calls / 5 warmups, single-client loopback HTTP, hosted Supabase, full 3,783-section stored term |

**Every gate row in "## Gates" above is PASS.** `08-D21-EXCEPTIONS.md` is complete (661 rows,
machine-generated, matching the inventory's exception count exactly) and no section is unlisted
or in a failure state (`missing_cache_row`, `unbacked_course_claim`, `raw_total_mismatch`,
`history_not_used`, `global_nonzero_effective_n` and `unclassified` all report 0 — see
`sections_by_state` in "## D-21 grade coverage", which sums exactly to 3,783: 3,122 + 361 + 300).

**The 661 listed D-21 exceptions (361 `no_rows` + 300 `non_letter_grade`) are the honest end
state, not a gap.** They are source-limited by InfoCenter's own reporting boundaries (under-five
enrollment omission, new courses, courses not offered in the checked window, or courses whose
only history has zero letter-grade weight) and keep an explicit, correctly-labeled subject/global
or non-letter-grade-prior fallback rather than fabricated course history. No new grade sourcing or
import is proposed by this report, per D-21's explicit stop-here decision.

**Browser layout observation (08-03 Task 2 acceptance criterion): NOT MEASURED.** No Chromium or
Playwright is available in this execution environment (unchanged since 08-03; logged to
`.planning/WINDOWS.md` entry 8). The 8 `RankingEvidence.test.tsx` component tests render both the
desktop table and mobile card layouts in `jsdom` and assert the literal evidence-wording strings
for course, `course`/`effective_n=0`, subject and global rows — real evidence of correct text
output per layout, not a substitute for a real-viewport visual check. This does not block the
MVP-1 verdict: the 08-03 wording requirement is proven at the component level with 8/8 tests
passing, and D-21's grade-coverage criterion does not depend on a visual check.

**Concurrent-user, deployed-host and browser latency: NOT MEASURED**, per REQ-PERF-01's
single-client loopback scope (this plan's `<verification>` and D-21's concurrency edge
resolution). No claim is made beyond the measured single-client loopback HTTP p95.

No repair action is required: there is no FAIL row in this report. The one open item
(`.planning/WINDOWS.md` entry 9, the test-file mypy delta) is a follow-up type-annotation cleanup,
not a stale_cache, history_not_used, unbacked_course_claim or raw_total_mismatch state — it does
not name a cache rebuild (`docs/runbooks/grade-import.md` section 2) or a `/gsd-debug`
investigation, because no gate observed either failure signature.

**UTC window end:** 2026-09-24T18:41:00Z (approx, Task 3 close). No hosted-data mutation, cache
rebuild, or grade import occurred at any point across Tasks 1–3 of this plan.
