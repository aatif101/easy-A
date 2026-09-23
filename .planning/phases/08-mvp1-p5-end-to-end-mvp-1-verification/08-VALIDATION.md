---
phase: "08"
slug: "mvp1-p5-end-to-end-mvp-1-verification"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-23"
---

# Phase 8 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest and Vitest |
| Config | `pyproject.toml`, `web/vite.config.ts` |
| Quick run | `uv run pytest tests/refresh/test_validate_tampa_ingest.py tests/refresh/test_inventory_tampa_grades.py tests/api/test_verify_rankings_pages.py -q`; `npm --prefix web test -- src/components/RankingEvidence.test.tsx` |
| Full run | `uv run pytest -q`; `npm --prefix web test`; `npm --prefix web run typecheck`; `npm --prefix web run lint`; `npm --prefix web run build` |
| Planning-time baseline (2026-09-23) | Python 324 passed / 3 skipped (6.2 s); frontend 78 passed (11.3 s); frontend lint, typecheck and build clean. Repo-wide `ruff check .` (2) and `mypy src migrations scripts tests` (30 in 9 files) already fail on files Phase 8 does not touch, so Phase 8 scopes ruff/mypy to the files it adds or changes. |
| Feedback latency | Record measured duration during execution |

## Grade-coverage criterion (PROJECT.md D-21, locked 2026-09-23)

Every Spring 2027 Tampa section is either **evidence-backed** (`score_source` `course`/`instructor_course`, `effective_n > 0`, attributed own-course rows with letter-grade weight and reconciled raw totals) or a **listed source-limited exception** (`no_rows` or `non_letter_grade`) that keeps its honest subject/global fallback with D-20 labeling. Fallbacks and `course` rows with `effective_n = 0` are never counted as course history; no data is invented; no grade sourcing or import happens in Phase 8. The 2026-09-23 live read (3,783 sections; 3,122 evidence-backed; 661 exceptions = 311 subject + 50 global + 300 `course`/`effective_n = 0`) is a sanity baseline to re-measure, not a pass condition.

## Sampling Rate

- After a source change, run its focused test and record the result.
- After each wave, run the relevant Python or frontend suite.
- Before Phase 8 sign-off, run the full suites and live hosted gates against one dated term snapshot.
- A PostgreSQL integration skip is reported as a skip, not as a pass.

## Per-Task Verification Map

| Requirement | Plan | Behavior | Automated command | Existing? |
|---|---|---|---|---|
| REQ-COVERAGE-03 | 08-04 | Tampa target/cache count and suffix ownership | `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q`; live `uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` | Yes |
| REQ-COVERAGE-03 | 08-01 | All stored term/CRN identities appear exactly once over API pages (200/201 boundaries, empty term, total order, unstable snapshot) | `uv run pytest tests/api/test_verify_rankings_pages.py tests/api/test_rankings_search_sql.py -q`; live `uv run python scripts/verify_rankings_pages.py --term 202701 --http-base-url http://127.0.0.1:8000` | Wave 0 gap |
| REQ-GRADES-01 | 08-02 | Every section is evidence-backed or a listed D-21 exception (`no_rows`, `non_letter_grade`); integrity failures named; provenance by term; atomic exception list | `uv run pytest tests/refresh/test_inventory_tampa_grades.py -q`; live `uv run python scripts/inventory_tampa_grades.py --term 202701 --exceptions-md .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md` | Wave 0 gap |
| REQ-GRADES-01 | 08-02 | Validator honest-coverage accepts `course`/`effective_n = 0` only with stored letter-grade-free history; every other zero-sample course claim still fails | `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q` | Wave 0 gap (new cases) |
| REQ-GRADES-01 | 08-03 | Desktop row, mobile card and expanded details state the evidence scope for `course`/`effective_n = 0`, `global`, `subject` and `course`/`effective_n > 0`; no "Course-level history" or "0 grades" on evidence-free rows | `npm --prefix web test -- src/components/RankingEvidence.test.tsx` | Wave 0 gap |
| REQ-PERF-01 | 08-04 | Full-scale single-client loopback search p95 below 1.5 s | `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50` | Yes |
| D-02 | 08-04 | Scoring, cache, API and frontend API contract unchanged | `git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api src/easy_a/models migrations web/src/types web/src/api`; `uv run pytest tests/api/test_benchmark_rankings_search.py tests/api/test_rankings_search_sql.py tests/rankings/test_cache_parity.py -q` | Yes |

## Wave 0 Requirements

- [ ] Add focused tests for the complete API page identity scan (08-01).
- [ ] Add focused tests for the D-21 grade inventory and the validator's non-letter-grade exception (08-02).
- [ ] Add focused frontend tests for `course`/`effective_n = 0`, `global`, `subject` and course-backed evidence wording in both layouts and details (08-03).

## Manual-Only Verifications

| Behavior | Why manual | Instructions |
|---|---|---|
| Browser display at desktop and mobile sizes | Existing component tests cannot prove layout | Inspect representative course, `course`/`effective_n = 0`, subject and global rows; record screenshots or observations, or NOT MEASURED, without claiming a deployed-host latency. |
| Hosted Supabase evidence | Credentials and service availability are environment-specific | Run existing live commands, record UTC time, denominators, and explicit PASS/FAIL/NOT MEASURED verdicts. |

## Validation Sign-Off

- [ ] All new tasks have focused tests or a documented live gate.
- [ ] Live result issues separate Phase 8 and MVP-1 (D-21) verdicts, with evidence-backed and exception counts reported separately.
- [ ] Full suite, quality, grade inventory, D-21 exception list, coverage, and p95 results recorded.
- [ ] `nyquist_compliant: true` only after required tests and live gates pass.

**Approval:** pending
