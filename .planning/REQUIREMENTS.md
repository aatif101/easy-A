# Requirements: Easy-A

Requirements for the sequence forward from the current working baseline. Easy-A is an existing
application with real ingestion, configurable course coverage and seat freshness — not a
greenfield build.

**Current baseline: `origin/main` = `180afe0`.** Sprint 5 is merged and complete.
**Current activity: real-data expansion validation.**

## How requirements are classified

| Class | Meaning |
|-------|---------|
| Current baseline | Already working. Preserved, not rebuilt. |
| Complete | Delivered and merged. Kept for traceability. |
| Current | Active scope now. |
| Next | Hosted beta scope. |
| Later / optional | Candidate later phases. Not committed. |

Coverage figures are **coverage expansion targets subject to validation**. Configuring a course
target is not the same as having validated coverage for it.

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

Measured on the merged branch at `180afe0` on 2026-09-08:

| Suite | Result | Notes |
|-------|--------|-------|
| Python (`uv run pytest -q`) | **191 passed, 1 skipped** | The skip is the PostgreSQL integration test, which skips when `EASY_A_TEST_POSTGRES_URL` is unset |
| Python with PostgreSQL configured | 192 passed (reported in PR #14) | Requires `EASY_A_TEST_POSTGRES_URL` |
| Frontend (`npm test` in `web/`) | **78 passed** | 5 test files |
| Quality gates | ruff, mypy `strict = true`, ESLint, `tsc -b`, build — all passing | |

**Do not describe the whole Python suite as running on PostgreSQL.** Most tests still use
SQLite; PostgreSQL integration coverage exists for the behavior most exposed to the dialect gap
and skips silently when the environment variable is absent.

---

## Complete — Sprint 5 (merged, PR #14 + PR #15)

Kept for traceability. Verified present in code at `180afe0`.

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

## Current — real-data expansion validation

- [ ] **REQ-COVERAGE-02**: Configured coverage is validated against real data before it is claimed.
  *Acceptance*: Run real ingestion for the configured Spring 2027 (`202701`) Tampa targets —
  `MAC 1105`, `ENC 1101`, `AMH 2020`, `PSY 2012`, `BSC 1005` — and record, from that run:
  actual section counts per course; catalog availability per target; GenEd attribute coverage;
  seat freshness behavior across a refresh cycle; named-instructor coverage versus `Staff`;
  historical grade coverage by term per course; quality-pipeline findings; and measured search
  performance at the widened coverage.
  Every figure must carry the run date and scope. Targets that fail to resolve, or that have no
  historical grade data, are reported as such rather than omitted. The result states plainly
  which targets are validated and which are not. `MAC 1105` and `ENC 1101` are the previously
  validated pair; the other three are configured but unvalidated.
  Requests to USF public sources stay narrow and bounded. Do not commit raw grade export files.

---

## Next — hosted beta

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

### Fixed in Sprint 5 (historical — do not re-plan these)

| Observation | Status |
|-------------|--------|
| Frontend silently served fixtures when `VITE_API_BASE_URL` was unset | **Fixed in Sprint 5** — explicit `VITE_USE_MOCK_DATA` opt-in; unset config now throws |
| No seat freshness contract | **Fixed in Sprint 5** — `src/easy_a/schedule/freshness.py` plus API fields and UI |
| No PostgreSQL-specific integration coverage | **Fixed in Sprint 5 (partially)** — exists, skips without `EASY_A_TEST_POSTGRES_URL` |
| Frontend hard-coded a Spring 2027 term preference | **Fixed in Sprint 5** — term selection is configuration-driven |

### Still open

| Observation | Evidence | Where it lands |
|-------------|----------|----------------|
| Ranking search may be expensive at broader coverage | `GET /api/v1/rankings/search` ranks sections before slicing pagination | Measure in Phase 1 (REQ-COVERAGE-02) |
| Blank grade-cell / suppression semantics unresolved | `src/easy_a/grades/parser.py` converts every blank cell to `0` with no suppression path | Needs a real or sample InfoCenter export; owner holds ODS/registrar access |
| Broader real-data coverage is not yet validated | Three of five configured targets have never been ingested | Phase 1 is exactly this |
| `course_id` null on grade import; term/CRN/**source** dedup | Grade import behavior | Watch during expansion (BASE-04) |
| Named-instructor coverage is unmeasured beyond two courses | Two-course sample showed all `Staff` | Measured in Phase 1 |

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
*Last updated: 2026-09-08 — Sprint 5 marked complete against merged code at `180afe0`; test
baseline re-measured; current activity is real-data expansion validation.*
