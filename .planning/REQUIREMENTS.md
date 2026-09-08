# Requirements: Easy-A

Requirements for the sequence forward from the current working baseline. Easy-A is an existing
application with a validated real-data beta, not a greenfield build.

**Current planning phase: Sprint 5.**

## How requirements are classified

| Class | Meaning |
|-------|---------|
| Current baseline | Already working. Preserved, not rebuilt. |
| Sprint 5 | Active scope now. |
| Next | Hosted beta scope, after Sprint 5. |
| Later / optional | Candidate later phases. Not committed, not required for beta. |

Coverage figures are **coverage expansion targets subject to validation**. No requirement here
claims coverage that has not been ingested and verified.

---

## Current baseline (preserved, not rebuilt)

These describe what already works. They are the platform, not scope. Changing them is out of
scope unless a requirement below says otherwise.

- **BASE-01 — Existing scoring model.** The historical easiness score stays as-is: the current
  grade/withdrawal composition, Bayesian shrinkage, confidence labels, and course /
  instructor-course fallback behavior. No rewrite is planned or approved. See the optional
  methodology review in the backlog.
- **BASE-02 — Score isolation.** Seats, modality, GenEd and syllabus signals do not influence the
  score. Changing seat data must not change a historical score. This property already holds and
  must be preserved.
- **BASE-03 — Ingestion pipelines.** Catalog, schedule, syllabi and grades, each shaped
  `client.py → parser.py → ingest.py → cli.py`, orchestrated by `src/easy_a/refresh/service.py`.
- **BASE-04 — Grade provenance and deduplication.** Grade rows carry source hashes and are unique
  by term/CRN/source. Explicit source selection prevents duplicate exports from double-counting.
  This safety property must remain intact through any coverage expansion.
- **BASE-05 — Deterministic signal extraction.** Nine supported syllabus policy categories with
  provenance and short evidence quotes. Rules-based, no model calls.
- **BASE-06 — Test and quality baseline.** 166 Python tests and 19 frontend tests passing
  (measured 2026-09-08). ruff, mypy `strict = true`, ESLint and `tsc -b` all clean. Preserve this
  passing baseline; update tests when semantics genuinely change.
- **BASE-07 — Existing stack.** Python 3.12 / FastAPI / SQLAlchemy / Alembic / PostgreSQL 16 and
  React / TypeScript / Vite / Tailwind, in this repository. No rewrite, no separate product.

---

## Sprint 5 requirements (current scope)

- [ ] **REQ-COVERAGE-01**: Course coverage is configurable rather than hard-coded.
  *Acceptance*: A target-course mechanism drives which courses are ingested and served. Widening
  coverage beyond the validated `MAC 1105` + `ENC 1101` beta requires a configuration change, not
  a code change. Coverage actually achieved is recorded with real counts and named terms after
  ingestion — never claimed in advance. Sections whose grade history, instructor name or syllabus
  is unavailable are still listed, with the unavailability stated explicitly.

- [ ] **REQ-SEAT-01**: Seat information carries visible observation age.
  *Acceptance*: Each section exposes its latest known seat count, availability state, and the
  time of the last **successful** observation, distinguishable from the last attempt. A failed or
  partial request must not advance the success timestamp, must not fabricate a zero count, and
  must not present stale data as current. Waitlist capacity stays separate from available seats.
  Negative remaining-seat values from the source are handled as over-capacity, not as a negative
  "available" badge — upstream genuinely emits these (CRN `19410` published `190/207/-17`).
  Frontend surfaces observation age with a text label, not color alone.

- [ ] **REQ-SEAT-02**: A seat-only refresh workflow exists.
  *Acceptance*: Seat availability can be refreshed without re-running the full ingestion
  pipeline. Refresh cadence is configurable. Requests to USF public sources stay bounded and
  narrow, consistent with existing practice — no broad crawling. Failure to refresh is visible
  rather than silent.
  *Note*: This requirement covers refresh and freshness only. Notifying anyone about a seat
  change is a candidate later phase, not part of this requirement.

- [ ] **REQ-CONFIG-01**: Production configuration cannot silently serve synthetic data.
  *Acceptance*: `web/src/api/rankings.ts` currently returns synthetic fixtures when
  `VITE_API_BASE_URL` is unset, so a misconfigured production deploy renders plausible fake course
  data. A production build with no configured API base URL must fail visibly instead. Fixtures
  remain available but explicitly opt-in for development and tests. The hard-coded Spring 2027
  term preference is replaced by explicit configuration.

- [ ] **REQ-TEST-01**: PostgreSQL integration coverage where practical.
  *Acceptance*: All 166 Python tests currently run on `sqlite+pysqlite:///:memory:` while the
  deployment target is PostgreSQL 16, and Alembic migrations are never applied in tests
  (`Base.metadata.create_all` is used instead). Add integration coverage that runs against
  PostgreSQL 16 for the behavior most at risk from the dialect gap — queries, migrations, and
  concurrent access. Partial progress is acceptable; the existing baseline must still pass.

---

## Next — hosted beta

- [ ] **REQ-COVERAGE-02**: Broader real-data coverage is validated before it is claimed.
  *Acceptance*: Report actual ingested coverage with real counts, named historical grade terms,
  and stated exclusions. Search performance is measured at the broader coverage level rather than
  extrapolated from the two-course beta — `GET /api/v1/rankings/search` currently ranks every
  section in the term before slicing pagination, issuing roughly six queries per section, so
  broader coverage needs measurement rather than assumption.

- [ ] **REQ-OPS-01**: The hosted beta is deployable, observable and reproducible.
  *Acceptance*: Minimal, portable deployment configuration — no provider-specific infrastructure.
  CI runs Python and frontend checks (net-new; no `.github/` directory exists today). Basic
  observability covers refresh success/failure and search latency. An operator runbook covers
  refreshing data and recovering from a failed refresh.

---

## Later / optional — candidate later phases

Not committed. Not required for the hosted beta. Recorded so the thinking is not lost.

- **REQ-ALERT-01 (candidate later phase)**: Seat availability notifications. Appropriate only
  after near-live seat refresh works and the hosted beta is stable. Would require verified email
  ownership, a durable worker independent of any browser session, polling shared across
  subscribers, and a persisted outbox with idempotency and bounded retries. Provider acceptance
  is not inbox receipt. **Do not add subscriber, watch, outbox or email-provider work to the
  current execution sequence.**

- **REQ-RMP-01 (candidate later phase)**: A verified "View on Rate My Professors" profile link.
  Deferred until after hosted beta and core data stability; not a blocker for the beta. Whenever
  it is picked up: no scraping, no bulk crawler, and no imported ratings, review counts, review
  text, tags or summaries — a verified link only.

- **Methodology review (optional research item)**: An evidence-backed review of how the existing
  score behaves with little or no grade history, and whether confidence labelling communicates
  that honestly. Not active implementation scope. Any change would need documented evidence and
  matching methodology and test updates.

---

## Evidence-backed observations to respect

These came out of codebase mapping and Phase 1 research. They are findings worth honoring, not
product requirements on their own.

| Observation | Evidence | Why it matters |
|-------------|----------|----------------|
| Production must not silently fall back to synthetic fixtures | `web/src/api/rankings.ts` serves 287 lines of fixtures when `VITE_API_BASE_URL` is unset | Covered by REQ-CONFIG-01 |
| PostgreSQL integration tests are valuable | `.planning/codebase/TESTING.md`: SQLite-only, migrations never applied | Covered by REQ-TEST-01 |
| Search performance must be measured at broader coverage | `GET /api/v1/rankings/search` ranks all sections before pagination, ~6 queries per section | Covered by REQ-COVERAGE-02 |
| Seat observation timestamps and freshness should be explicit | Two seat sources of truth — canonical `Section` columns (`src/easy_a/schedule/ingest.py`) and `SeatSnapshot` rows — with a fallback in `src/easy_a/rankings/service.py` that can make a stale column look current | Covered by REQ-SEAT-01 |
| Grade source deduplication and provenance must stay safe | Grade rows unique by term/CRN/**source**; `course_id` initialized to null on import | BASE-04; watch during coverage expansion |
| No fabricated data | Project-wide principle | Applies to coverage claims, seat states and scores alike |
| The existing stack should be preserved | BASE-07 | No rewrite |
| Untracked local work must be protected | `refs/heads/main` is at `d880d3c` with untracked `web/` (verified to contain only `dist/` and `node_modules/`, no source); `origin/main` is at `06634490` | Work from branches or worktrees descended from `origin/main` |

---

## Out of scope

- LLM or AI features of any kind — no AI summaries, AI scoring, or predicted personal grades
- Scraping any source, or importing RMP review content
- Auth, accounts, or a user-profile product
- Payments, SMS, browser push, native apps
- Automatic registration — the product links to official USF registration and never automates it
- Multi-university expansion
- Provider-specific deployment infrastructure beyond minimal, portable preparation
- A scoring methodology rewrite

---
*Last updated: 2026-09-08 — re-scoped to the actual Sprint 5 sequence. Alerts, RMP and a scoring
rewrite were previously recorded as required scope; they are candidate later phases or optional
research, and the existing scoring model is preserved as the baseline.*
