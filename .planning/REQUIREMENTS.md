# Requirements: Easy-A

Requirements for the sequence forward from the current working baseline. Easy-A is an existing
application with real ingestion, configurable course coverage and seat freshness — not a
greenfield build.

**Current baseline: `origin/main` = `62fb2f1`.** Sprint 5 and real-data expansion validation are
both complete.
**Current activity: Tampa-only data correction (Phase 2) — blocking.**

## How requirements are classified

| Class | Meaning |
|-------|---------|
| Current baseline | Already working. Preserved, not rebuilt. |
| Complete | Delivered and merged. Kept for traceability. |
| Current | Active scope now. |
| Next | Hosted beta scope. |
| Later / optional | Candidate later phases. Not committed. |

Coverage figures below are **measured**, from the real-data validation pass of 2026-09-09. Where
a figure is not measured, it says so. Note that *verified* Tampa counts and *currently stored*
counts differ until the Phase 2 cleanup runs — see REQ-DATA-02.

---

## Current baseline (preserved, not rebuilt)

- **BASE-01 — Existing scoring model.** The historical easiness score stays as-is: current
  grade/withdrawal composition, Bayesian shrinkage, confidence labels, and course /
  instructor-course fallback behavior. **No rewrite without explicit approval.**
- **BASE-02 — Score isolation.** Seats, modality, GenEd and syllabus signals do not influence the
  score. Changing seat data must not change a historical score.
- **BASE-03 — Ingestion pipelines.** Catalog, schedule, syllabi and grades, each shaped
  `client.py → parser.py → ingest.py → cli.py`, orchestrated by `src/easy_a/refresh/service.py`.
- **BASE-04 — Grade provenance and deduplication.** Grade rows carry source hashes and are unique
  by term/CRN/source. Explicit source selection prevents duplicate exports from double-counting.
  Must remain intact through coverage expansion. **Never commit raw grade export files.**
- **BASE-05 — Deterministic signal extraction.** Nine supported syllabus policy categories with
  provenance and short evidence quotes. Rules-based, no model calls.
- **BASE-06 — Test and quality baseline.** See "Current test baseline" below.
- **BASE-07 — Existing stack.** Python 3.12 / FastAPI / SQLAlchemy / Alembic / PostgreSQL 16 and
  React / TypeScript / Vite / Tailwind, in this repository. No rewrite, no separate product.

### Current test baseline

Re-measured 2026-09-10 at `origin/main` = `d72f8f3` plus the Phase 2 cleanup tooling and
campus-scope quality check:

| Condition | Result |
|-----------|--------|
| `uv run pytest -q`, no `EASY_A_TEST_POSTGRES_URL` | **215 passed, 1 skipped** (216 collected) |
| Backend with PostgreSQL configured | **not re-measured** — was 193 passed at `62fb2f1` |
| Frontend `npm test` in `web/` | **78 passed** |
| Quality gates | `ruff check .`, `mypy src migrations scripts tests` — passing |

The suite was 192 passed / 1 skipped before this work; the 23 added tests cover the cleanup
tooling (16) and the campus-scope quality check (7).

Both facts are true and both matter: **a default run does not use PostgreSQL** — most of the
suite runs on SQLite and the PostgreSQL integration test skips unless `EASY_A_TEST_POSTGRES_URL`
is set; with it set, that test also runs. Do not state only one of these. The
PostgreSQL-configured total has not been re-measured since the tooling landed — quote
193-at-`62fb2f1` as the last measurement rather than a current number.

---

## Complete — Sprint 5 (merged, PR #14 + PR #15)

Kept for traceability. Verified present in code at `62fb2f1`.

- [x] **REQ-COVERAGE-01**: Course coverage is configurable rather than hard-coded. ✓ **Complete.**
  `src/easy_a/refresh/targets.py` loads validated targets from `config/course_targets.toml`;
  `target_cli.py` and `src/easy_a/refresh/coverage.py` drive one-pass coverage refresh. Five
  targets are configured. *Configuration is not validated coverage — see REQ-COVERAGE-02.*

- [x] **REQ-SEAT-01**: Seat information carries visible observation age. ✓ **Complete.**
  `src/easy_a/schedule/freshness.py` provides `SeatFreshness`, `classify_observation` and
  `snapshot_freshness`; freshness fields are exposed through the API; the frontend renders seat
  freshness with relative observation timestamps (`web/src/components/SeatBadge.tsx`,
  `web/src/utils/time.ts`).

- [x] **REQ-SEAT-02**: A seat-only refresh workflow exists. ✓ **Complete.**
  `scripts/refresh_seats.py` refreshes seat availability without re-running full ingestion.
  *Refresh and freshness only — notifying anyone about a seat change remains a candidate later
  phase.*

- [x] **REQ-CONFIG-01**: Production configuration cannot silently serve synthetic data.
  ✓ **Complete.** `web/src/api/rankings.ts` now requires an explicit opt-in: with
  `VITE_API_BASE_URL` unset and `VITE_USE_MOCK_DATA` not `"true"`, it throws
  *"API configuration unavailable: set VITE_API_BASE_URL or explicitly enable
  VITE_USE_MOCK_DATA=true for synthetic development data."* A non-absolute URL is also rejected.

- [◐] **REQ-TEST-01**: PostgreSQL integration coverage where practical. **Partially complete.**
  `tests/refresh/test_postgres_coverage.py` provides PostgreSQL-specific integration coverage and
  calls `pytest.skip("Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration")` when the
  environment variable is absent. So: PostgreSQL integration coverage **exists**, is **not**
  exercised by default, and the bulk of the suite still runs on SQLite. Widening it is
  worthwhile but not currently scheduled work.

---

## Complete — Phase 1 real-data expansion validation (executed 2026-09-09)

- [x] **REQ-COVERAGE-02**: Configured coverage is validated against real data before it is claimed.
  ✓ **Complete**, with one carve-out. All five configured Spring 2027 (`202701`) targets were
  verified present in the catalog and their Tampa sections counted:

  | Course | Catalog | Verified Tampa sections |
  |--------|---------|-------------------------|
  | MAC 1105 | present | 5 |
  | ENC 1101 | present | 41 |
  | AMH 2020 | present | 17 |
  | PSY 2012 | present | 10 |
  | BSC 1005 | present | 2 |
  | **Verified Tampa total** | | **75** |

  Seat refresh appended 75 snapshots, preserved previous snapshots and section identity, left all
  237 grade rows unchanged, and left syllabi empty; all observed Tampa seats were fresh
  immediately after refresh. Data quality reported **zero errors** across 202408, 202501, 202508
  and 202701, and historical generic quality reports were not polluted by Sprint 5
  target/freshness checks. Frontend and API verification passed: required endpoints returned 200,
  desktop and mobile search worked, server pagination worked, freshness UX worked, GenEd
  rendering worked, details worked, and there were no browser console errors.

  **Carve-out:** search performance at the widened coverage was **not** sufficiently measured.
  That concern is REQ-PERF-01 under the hosted beta, not a satisfied criterion here.

  **Caveat:** the 75 figure is *verified Tampa sections*, not *currently stored* sections. The
  database still holds 47 contaminated non-Tampa rows until REQ-DATA-02 completes.

---

## Current — Tampa-only data correction (blocking)

- [◐] **REQ-DATA-02**: Stored, API and coverage counts reflect Tampa-only reality.
  *Context*: the first expansion pass ran before the campus-scope bug was found — configured
  refresh queried all campuses, and **47 non-Tampa Spring 2027 sections were inserted into the
  existing beta database**. PR #16 fixed the cause by pinning `campus="T"` and rejecting non-Tampa
  rows before ingestion, but its merged description states plainly that it "does not delete the 47
  other-campus sections inserted by the initial validation pass… They remain visible in stored
  coverage/API counts until a separately reviewed cleanup."
  *Acceptance*: perform a targeted, reviewable removal of those 47 rows, then a clean Tampa
  refresh and API verification. Record, as measured numbers: the exact cleanup result (rows
  removed and the selection criteria); final Tampa-only stored counts; final API counts; final
  coverage-endpoint counts; and explicit confirmation that **no historical grades and no Tampa
  sections were deleted** — the 237 grade rows and all 75 verified Tampa sections must survive
  intact. Stored, API and coverage counts must agree with each other.
  *Progress (2026-09-09)*: the removal tooling is written, tested and documented —
  `scripts/cleanup_non_tampa_sections.py`, `src/easy_a/refresh/cleanup.py`,
  `src/easy_a/refresh/cleanup_cli.py`, 16 tests in `tests/refresh/test_cleanup.py`, and a README
  section. It reports without writing unless `--apply` is given, selects by term and stored
  campus, deletes by explicit primary key, refuses sections carrying a stored syllabus, and
  aborts the transaction if stored grade rows change, a kept-campus section is lost, the number
  removed differs from the number matched, or any other-campus section remains.
  `--expect-removed N` refuses to proceed unless exactly `N` sections match.
  *Progress (2026-09-10)*: added `unsupported_campus_section`, an error-severity quality check
  reporting one finding per stored section outside the supported campus. It runs in the generic
  check path, so `scripts/check_data_quality.py --term 202701` reports it and exits nonzero with
  no target configuration. The supported campus and its comparison live in
  `src/easy_a/common/campus.py`, shared with the cleanup command. This is an independently
  implemented confirmation of the cleanup — cleanup selects by campus group-by and verifies
  counts; the check iterates stored sections and names each offender — and it catches a
  recurrence from any code path, not just coverage refresh.
  *Outstanding*: **neither the cleanup nor the check has been run against the beta database** — that needs an
  operator with database access. None of the acceptance numbers above has been measured, so this
  requirement stays open and the blocker stands.

---

## Next — historical grade coverage

- [ ] **REQ-GRADES-01**: The three newly validated courses have real historical grade data.
  *Context*: `AMH 2020`, `PSY 2012` and `BSC 1005` currently have **no imported historical grade
  data**. Each falls back to a global prior with `effective_n = 0`. **These fallback scores are
  not evidence-backed course history and must not be described as such** — in the product, the
  API, or these documents.
  *Acceptance*: obtain and import approved historical grade exports in priority order
  **AMH 2020 → PSY 2012 → BSC 1005**; validate the resulting course-level analytics against the
  source aggregate per course; record which terms actually have data per course and which do not.
  A course that still lacks data after the pass is recorded as lacking it, not quietly omitted.
  Approved exports are an external input with a named owner. **Never commit raw export files.**

---

## Later — hosted beta

- [ ] **REQ-PERF-01**: Search performance is measured at the widened coverage.
  *Context*: carried over from Phase 1, which did not measure it sufficiently.
  `GET /api/v1/rankings/search` ranks sections before slicing pagination.
  *Acceptance*: measure and record search latency against the corrected, widened dataset. Report
  real numbers with the dataset size they were measured at. Extrapolation from the two-course
  beta does not satisfy this.

- [ ] **REQ-OPS-01**: The hosted beta is deployable, observable and reproducible.
  *Acceptance*: Minimal, portable deployment configuration — no provider-specific infrastructure.
  CI runs Python and frontend checks (net-new; no `.github/` directory exists today). Basic
  observability covers refresh success/failure and search latency. An operator runbook covers
  refreshing data and recovering from a failed refresh.

---

## Later / optional — candidate later phases

Not committed. Not required for the hosted beta.

- **REQ-ALERT-01 (candidate later phase)**: Seat availability notifications. Appropriate only
  after the hosted beta is stable. Would need verified email ownership, a durable worker
  independent of any browser session, polling shared across subscribers, and a persisted outbox
  with idempotency and bounded retries. **Do not add subscriber, watch, outbox or email-provider
  work to the current execution sequence.**

- **REQ-RMP-01 (candidate later phase)**: A verified "View on Rate My Professors" profile link.
  Deferred until after hosted beta and core data stability; not a blocker. Whenever picked up:
  no scraping, no bulk crawler, no imported ratings, review counts, review text, tags or
  summaries — a verified link only.

- **Methodology review (optional research item)**: An evidence-backed review of how the existing
  score behaves with little or no grade history. Not active implementation scope. Any change
  needs documented evidence and matching methodology and test updates.

---

## Observations

### Fixed (historical — do not re-plan)

| Observation | Status |
|-------------|--------|
| Frontend silently served fixtures when `VITE_API_BASE_URL` was unset | **Fixed in Sprint 5** — explicit `VITE_USE_MOCK_DATA` opt-in; unset config throws |
| No seat freshness contract | **Fixed in Sprint 5** — `src/easy_a/schedule/freshness.py` plus API fields and UI |
| No PostgreSQL-specific integration coverage | **Fixed in Sprint 5 (partially)** — exists, skips without `EASY_A_TEST_POSTGRES_URL` |
| Frontend hard-coded a Spring 2027 term preference | **Fixed in Sprint 5** — configuration-driven |
| Configured refresh queried all campuses | **Cause fixed in PR #16** — `campus="T"` pinned, non-Tampa rows rejected before ingestion. **The 47 rows already inserted were not removed** — see REQ-DATA-02. |

### Still open

| Observation | Evidence | Where it lands |
|-------------|----------|----------------|
| 47 non-Tampa Spring 2027 sections stored in the beta database | PR #16 merged description | REQ-DATA-02 — **current blocker** |
| Search performance unmeasured at widened coverage | Phase 1 did not measure it; search ranks sections before slicing pagination | REQ-PERF-01 (hosted beta) |
| AMH 2020, PSY 2012, BSC 1005 have no historical grade data | Validation run: global fallback, `effective_n = 0` for each | REQ-GRADES-01 |
| Blank grade-cell / suppression semantics unresolved | `src/easy_a/grades/parser.py` converts every blank cell to `0` with no suppression path | Needs a real or sample InfoCenter export; owner holds ODS/registrar access |
| Deployment host and domain not supplied | — | Before hosted beta |
| `course_id` null on grade import; term/CRN/**source** dedup | Grade import behavior | BASE-04; watch during grade imports |

### Confirmed healthy by the validation run

- Zero data-quality errors across 202408, 202501, 202508 and 202701
- Historical generic quality reports were not polluted by Sprint 5 target/freshness checks
- Seat refresh preserved previous snapshots and section identity, and left all 237 grade rows
  unchanged
- Frontend and API verification passed with no browser console errors

---

## Out of scope

- LLM or AI features of any kind
- Scraping any source, or importing RMP review content
- Auth, accounts, or a user-profile product
- Payments, SMS, browser push, native apps
- Automatic registration
- Multi-university expansion
- Provider-specific deployment infrastructure
- A scoring methodology rewrite without explicit approval
- Committing raw grade export files

---
*Last updated: 2026-09-09 — real-data expansion validation recorded with measured results;
REQ-DATA-02 (47-section cleanup) is the current blocking requirement; search performance carved
out to REQ-PERF-01.*
