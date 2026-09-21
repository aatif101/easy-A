# Requirements: Easy-A

Requirements for the sequence forward from the current working baseline. Easy-A is an existing
application with real ingestion, configurable course coverage and seat freshness — not a
greenfield build.

**Live facts (baseline SHA, counts) live in `.planning/STATE.md`.** Sprint 5, real-data validation
and the Tampa-only correction (PR #18) are merged; Phase 3.5 is delivered.
**Current milestone: MVP 1** — full Tampa coverage + historical grades + performance (see below).

## How requirements are classified

| Class | Meaning |
|-------|---------|
| Current baseline | Already working. Preserved, not rebuilt. |
| Complete | Delivered and merged. Kept for traceability. |
| Current | Active scope now. |
| Next | Hosted beta scope. |
| Later / optional | Candidate later phases. Not committed. |

Coverage figures below are **measured** and dated. The 75-section table is the real-data validation
pass of 2026-09-09; the clean refresh of 2026-09-14 found 77 Tampa sections after two legitimate
AMH 2020 sections appeared. Where a figure is not measured, it says so.

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

Measured 2026-09-09 on this branch (merged with `origin/main` = `62fb2f1`):

| Condition | Result |
|-----------|--------|
| `uv run pytest -q`, no `EASY_A_TEST_POSTGRES_URL` | **192 passed, 1 skipped** (193 collected) |
| Backend with PostgreSQL configured | **193 passed** (measured on the validation branch) |
| Frontend `npm test` in `web/` | **78 passed** |
| Quality gates | ruff, mypy, ESLint, typecheck, build — all passing |

Both facts are true and both matter: **a default run does not use PostgreSQL** — most of the
suite runs on SQLite and the PostgreSQL integration test skips unless `EASY_A_TEST_POSTGRES_URL`
is set; with it set, all 193 pass. Do not state only one of these.

Phase 2 branch verification on 2026-09-14 measured **216 passed, 2 skipped** without PostgreSQL
and **218 passed** with PostgreSQL configured. Ruff and strict mypy also passed. The frontend was
not changed or re-measured in Phase 2; its latest recorded result remains 78 passed above.

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

  **Dated result:** the 75 figure is the verified Tampa count from 2026-09-09. Phase 2 later
  removed the 47 contaminated rows, and the clean 2026-09-14 refresh found 77 current Tampa
  sections because AMH 2020 increased from 17 to 19.

---

## Complete on PR #18 — Tampa-only data correction

- [x] **REQ-DATA-02**: Stored, API and coverage counts reflect Tampa-only reality.
  *Context*: the first expansion pass ran before the campus-scope bug was found — configured
  refresh queried all campuses, and **47 non-Tampa Spring 2027 sections were inserted into the
  existing beta database**. PR #16 fixed the cause by pinning `campus="T"` and rejecting non-Tampa
  rows before ingestion, but its merged description states plainly that it "does not delete the 47
  other-campus sections inserted by the initial validation pass… They remain visible in stored
  coverage/API counts until a separately reviewed cleanup."
  *Measured result, 2026-09-14*: the dry run found exactly 47 eligible sections and zero ambiguous
  rows. Eligibility was limited to term `202701`, configured target courses, and a nonblank
  stored campus other than Tampa after stripping and case-folding. Null/blank campuses, other
  terms and non-target courses were excluded. Apply removed 47 sections, 47 seat snapshots and
  47 instructor observations; it removed 0 syllabi, 0 grade rows, 0 Tampa sections, 0 historical
  sections and 0 unrelated-term sections.

  The required clean course-coverage and seat refreshes produced MAC 1105 = 5, ENC 1101 = 41,
  AMH 2020 = 19, PSY 2012 = 10 and BSC 1005 = 2: **77 Tampa sections and zero other-campus
  sections**. The database, rankings API and `GET /api/v1/metadata/coverage` agreed. All 237
  grade rows and all 263 historical sections remained. A post-cleanup dry run found zero eligible
  rows, and Spring 2027 quality reported 0 errors, 31 warnings and 31 info.

  *Delivery*: PR #18 contains the cleanup tooling, preservation checks, tests and independent
  `unsupported_campus_section` quality guard. Verified and merged.

---

## MVP 1 — full Tampa coverage + historical grades

- [ ] **REQ-COVERAGE-03**: All ~3,782 USF Tampa Spring 2027 sections are ingested and searchable.
  *Context*: the current DB holds only 132 sections / 10 courses, and there is **no "all Tampa"
  ingest path** yet — ingestion is target-driven off `config/course_targets.toml`.
  *Acceptance*: catalog + schedule ingestion covers the full Tampa Spring 2027 set; the
  CHM 2045/2045L suffix-course guard is resolved without weakening it; config and stored data are
  reconciled. (MVP1-P3.)

- [x] **REQ-GRADES-01**: Ingested Tampa courses have real historical grade data, and easiness is
  computed from it. *Current verified scope*: hosted Supabase has **179 Fall 2024 aggregate rows**
  for all 10 currently ingested courses, totaling 7,544 raw grades. All 132 Spring 2027 sections
  report `effective_n > 0` and `score_source=course` after the separate live cache rebuild.
  **A global-prior fallback is not evidence-backed course history and must not be described as such.**
  *Acceptance*: import historical grade distributions (data sourcing is Codex-owned, MVP1-P2),
  attribution fixed so current-term sections resolve their course history, per-course analytics
  validated against the source aggregate, and courses still lacking data recorded as lacking it —
  never quietly omitted. **Never commit raw export files.**
  **MVP1-P1 done (2026-09-21, `04-01-SUMMARY.md` + `04-02-SUMMARY.md`):** `GradeDistribution.course_id`
  is now resolved via `resolve_course_id()` on insert and update, with an atomic all-keys preflight
  and same-key null-row repair; proved end-to-end on a generated workbook through a rebuilt 202701
  cache to `GET /api/v1/rankings/search` (effective_n > 0 / score_source=course vs. an honest
  effective_n = 0 / score_source=global control). Blank canonical grade-count and Total Grades
  cells now fail closed with a row/column-specific, non-suppression-asserting reason instead of
  being silently coerced to zero (explicit numeric zero remains valid), and every stored
  `GradeDistribution` with a null `course_id` now surfaces as a deterministic
  `unattributed_grade_row` data-quality error.
  **MVP1-P2 done (2026-09-21, `05-01-SUMMARY.md` + `05-02-SUMMARY.md`):** every per-course raw
  database total exactly matches its authenticated InfoCenter source total; the operator approved
  the all-ten record; repeat import proved idempotent; no raw workbook is tracked. OQ-04 remains
  genuinely unresolved because none of the 179 real rows contained a blank canonical cell. Phase 6
  must extend this requirement to every newly ingested Tampa course, explicitly retaining a global
  fallback for any course whose source data is unavailable.

---

## MVP 1 — performance

- [◐] **REQ-PERF-01** (MVP-1 blocking): Ranking search is fast at full Tampa coverage.
  *Context*: Phase 3.5 delivered the SQL rewrite that removed the per-section N+1 (which measured
  ~600s at 132 sections over Supabase). Measured **~2.40s p95** at a 3,782-section synthetic fixture
  over Supabase — still above target. The rewrite kept cached rankings byte-for-byte identical to
  the on-demand results (automated parity test).
  *Acceptance*: search page p95 **< ~1.5s** against Supabase at full ~3,782-section coverage,
  scoring model and API contract unchanged, with real numbers, dataset size and environment (MVP1-P4).

## After MVP 1 — hosted beta

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
| Configured refresh queried all campuses | **Cause fixed in PR #16** — `campus="T"` pinned, non-Tampa rows rejected before ingestion. Stored contamination was removed and verified in Phase 2 / PR #18. |

### Still open

| Observation | Evidence | Where it lands |
|-------------|----------|----------------|
| Historical grade coverage for future all-Tampa expansion | Current 10-course pilot is fully course-backed; newly added Phase 6 courses still require the same sourced-data or explicit-fallback treatment | REQ-GRADES-01 / MVP1-P3 |
| Grade→course attribution broken | **Fixed in MVP1-P1 (04-01, 2026-09-21)** — `resolve_course_id()` now resolves and persists `course_id` on insert/update, with an atomic preflight and null-row repair | Closed |
| No "all Tampa" ingest path; suffix-course guard | ingestion is target-driven; USF's CHM 2045 query also returns CHM 2045L (33 base courses affected) | REQ-COVERAGE-03 / MVP1-P3 |
| Search p95 above target at full scale | ~2.40s p95 at a 3,782-section synthetic fixture over Supabase | REQ-PERF-01 / MVP1-P4 |
| Blank grade-cell / suppression semantics unresolved | **Fail-closed rejection added in MVP1-P1 (04-02, 2026-09-21)** — blank canonical counts are now rejected rather than coerced to zero; the underlying real-export semantics (OQ-04) are still unresolved | Needs a real/sample InfoCenter export |
| Deployment host and domain not supplied | — | After MVP 1 (hosted beta) |

### Confirmed healthy by the validation run

- Zero data-quality errors across 202408, 202501, 202508 and 202701
- Historical generic quality reports were not polluted by Sprint 5 target/freshness checks
- Seat refresh preserved previous snapshots and section identity, and left all 237 grade rows
  unchanged
- Frontend and API verification passed with no browser console errors
- Phase 2 cleanup (old local beta DB) preserved all 237 grade rows and 263 historical sections and
  reached 77 Tampa / 0 other-campus configured sections — **dated history**, superseded by the
  current hosted Supabase DB (132 sections / 10 courses / 179 Fall 2024 grade rows; see STATE.md)

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
*Last updated: 2026-09-21 — MVP1-P2 imported and reconciled real Fall 2024 history for all 10
currently ingested courses (179 rows / 7,544 grades); all 132 live sections are course-backed and
the operator approved the all-course record. REQ-GRADES-01 is complete for current coverage and
must be extended as Phase 6 adds courses. OQ-04 remains open. Previously updated 2026-09-20 —
reclassified REQ-GRADES-01/REQ-PERF-01 and added REQ-COVERAGE-03 under the MVP-1 milestone; dated
beta-DB figures moved to `.planning/ARCHIVE.md`.*
