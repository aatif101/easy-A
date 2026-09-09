# Easy-A

## What This Is

Easy-A is a course-intelligence website for USF Tampa students. A student finds a real section and
sees what the historical grade distribution actually looked like, how strong that evidence is,
which syllabus policies are supported by a quotable source, and how many seats were available the
last time the section was successfully checked.

It is an existing, working application — not a greenfield build and not a prototype. Python 3.12 /
FastAPI / SQLAlchemy / Alembic / PostgreSQL 16 on the backend, React / TypeScript / Vite / Tailwind
on the frontend. It has real Spring 2027 schedule ingestion, real historical grade imports,
configurable course coverage, seat freshness classification, GenEd metadata and a data-quality
pipeline. The API and frontend have been smoke-tested end to end.

**Current baseline: `origin/main` = `d72f8f3d77a11f301f2b74f56088a217226feefa`** (verified by
fetch 2026-09-09; Sprint 5 merged via PR #14 and PR #15 and the Tampa scope restriction via
PR #16, all at ancestor `62fb2f1` — every commit since is planning/docs only).

**Sprint 5 and real-data expansion validation are both complete.**
**Current activity: Tampa-only data correction — blocking. See "Current blocker" below.**

## Core Value

Every number a student sees is a real observed outcome with a visible denominator, a named source
and a timestamp — and when the evidence does not exist, the product says so instead of producing a
plausible-looking result.

## Requirements

### Current baseline (working today)

<!-- Verified against merged code at origin/main = 62fb2f1 and the test baseline measured
     2026-09-08. The codebase map (.planning/codebase/) dates from 2026-09-05 at commit
     06634490 — historical baseline evidence, predating Sprint 5. This is the platform, not
     scope. -->

- ✓ Layered FastAPI backend with read-only `/api/v1/rankings/{section,course,search}` and
  `/api/v1/metadata` routes — `src/easy_a/api/`
- ✓ Ingest pipelines for catalog, schedule, syllabi and grades, orchestrated by
  `src/easy_a/refresh/service.py`
- ✓ XLSX grade-distribution import covering all ten grade buckets, totals, source hashes and
  term/CRN joins — `src/easy_a/grades/`
- ✓ Historical easiness score with Bayesian shrinkage, confidence labels, and course /
  instructor-course fallback — `src/easy_a/analytics/`
- ✓ Deterministic syllabus policy extraction for nine categories with provenance and evidence
  quotes — `src/easy_a/signals/`
- ✓ Ranking service joining analytics, section facts, GenEd attributes, seats, modality and
  signals — `src/easy_a/rankings/`
- ✓ React SPA with responsive table/cards, metadata-backed filters, pagination, expandable details
  and error/loading/empty states — `web/src/`
- ✓ Real Spring 2027 schedule ingestion, real historical grade imports, seat snapshots and a
  data-quality pipeline
- ✓ Validated `MAC 1105` + `ENC 1101` real-data beta
- ✓ Configurable course targets — `src/easy_a/refresh/targets.py`, `config/course_targets.toml`
- ✓ Seat freshness classification and seat-only refresh — `src/easy_a/schedule/freshness.py`,
  `scripts/refresh_seats.py`
- ✓ Coverage metadata endpoint — `GET /api/v1/metadata/coverage`
- ✓ Explicit mock opt-in — unset `VITE_API_BASE_URL` throws rather than serving fixtures
- ✓ Tampa-only scope enforcement in coverage refresh — `campus="T"` pinned in the schedule query,
  non-Tampa rows rejected (PR #16)
- ✓ Reviewable removal of stored sections outside the supported campus —
  `scripts/cleanup_non_tampa_sections.py`, `src/easy_a/refresh/cleanup.py` (tooling only; not yet
  run against the beta database)
- ✓ **208 Python passed / 1 skipped and 78 frontend passed** (measured 2026-09-09 at `d72f8f3`
  plus the cleanup tooling; was 192 / 1 at `62fb2f1`. The skip is the PostgreSQL integration
  test, which needs `EASY_A_TEST_POSTGRES_URL`)
- ✓ Strict quality gates: ruff (`B,C4,E,F,I,SIM,UP`), mypy `strict = true`, ESLint + `tsc -b`

### Sprint 5 — COMPLETE (merged, PR #14 + PR #15)

<!-- Full text and evidence in .planning/REQUIREMENTS.md. -->

- [x] **REQ-COVERAGE-01** — Configurable course targets
- [x] **REQ-SEAT-01** — Seat information with visible observation age
- [x] **REQ-SEAT-02** — Seat-only refresh workflow
- [x] **REQ-CONFIG-01** — Explicit mock opt-in; no silent production fixture fallback
- [◐] **REQ-TEST-01** — PostgreSQL integration coverage **exists but skips** without
  `EASY_A_TEST_POSTGRES_URL`; the bulk of the suite still runs on SQLite

### Phase 1 — real-data expansion validation — COMPLETE (2026-09-09)

- [x] **REQ-COVERAGE-02** — All five configured Spring 2027 targets verified in the catalog;
  **75 verified Tampa sections** total. Search performance was not sufficiently measured and is
  carved out to REQ-PERF-01.

### Current — Tampa-only data correction (blocking)

- [◐] **REQ-DATA-02** — Remove the 47 non-Tampa Spring 2027 sections inserted by the first
  expansion pass; clean Tampa refresh; verify API and coverage counts. **Partial:** the removal
  tooling is written and tested (`scripts/cleanup_non_tampa_sections.py`); it has not been run
  against the beta database, so no count has changed yet.

### Next — historical grade coverage

- [ ] **REQ-GRADES-01** — Import approved historical grade exports for AMH 2020 → PSY 2012 →
  BSC 1005 and validate the resulting analytics

### Later — hosted beta

- [ ] **REQ-PERF-01** — Measure search performance at the widened coverage
- [ ] **REQ-OPS-01** — Deployable, observable, reproducible hosted beta

### Later / optional

Candidate later phases. Not committed, not required for the beta. See `.planning/ROADMAP.md`
backlog for detail.

- Seat alerts and notifications
- Verified RMP profile links
- Deeper professor-specific coverage
- Additional UX features
- Methodology review (optional research item)

### Out of Scope

- LLM or AI features — no AI summaries, AI scoring, or predicted personal grades
- Scraping any source; importing RMP ratings, review counts, review text, tags or summaries
- Auth, accounts, or a user-profile product
- Payments, SMS, browser push, native apps
- Automatic registration — the product links to official USF registration, never automates it
- Multi-university expansion
- Provider-specific deployment infrastructure beyond minimal, portable preparation
- A scoring methodology rewrite

## Current blocker

**47 non-Tampa Spring 2027 sections are still stored in the beta database.**

The first expansion pass ran before the campus-scope bug was found: configured refresh queried all
campuses and inserted 47 non-Tampa Spring 2027 sections into the existing beta database. PR #16
fixed the cause — it pins `campus="T"` and rejects non-Tampa rows before ingestion — but its
merged description states plainly that it "does not delete the 47 other-campus sections inserted
by the initial validation pass… They remain visible in stored coverage/API counts until a
separately reviewed cleanup."

**Until REQ-DATA-02 completes, stored counts, `/api/v1/rankings/*` counts and
`GET /api/v1/metadata/coverage` counts all still include the contaminated rows and do not equal
the verified Tampa total of 75.** Any coverage figure read from the running database today is
wrong.

The removal tooling was written on 2026-09-09 — `scripts/cleanup_non_tampa_sections.py`, backed
by `src/easy_a/refresh/cleanup.py` and covered by `tests/refresh/test_cleanup.py`. It reports
without writing unless `--apply` is given, deletes by explicit primary key, and verifies after
applying that no grade row and no kept-campus section was lost. **It has not been run against the
beta database**, so the contaminated counts above are unchanged.

## Context

**Real-data expansion validation (executed 2026-09-09).** All five configured Spring 2027
(`202701`) targets verified present in the catalog:

| Course | Catalog | Verified Tampa sections | Historical grade data |
|--------|---------|-------------------------|-----------------------|
| MAC 1105 | present | 5 | Real data; high-confidence course analytics |
| ENC 1101 | present | 41 | Real data; high-confidence course analytics |
| AMH 2020 | present | 17 | **None** — global fallback, `effective_n = 0` |
| PSY 2012 | present | 10 | **None** — global fallback, `effective_n = 0` |
| BSC 1005 | present | 2 | **None** — global fallback, `effective_n = 0` |
| **Verified Tampa total** | | **75** | |

**The AMH / PSY / BSC fallback scores are not evidence-backed course history.** They are global
priors with zero observed outcomes for the course. Grade import priority: AMH 2020 → PSY 2012 →
BSC 1005.

Seat refresh appended 75 snapshots, preserved previous snapshots and section identity, left all
237 grade rows unchanged, and left syllabi empty; all observed Tampa seats were fresh immediately
after refresh. Data quality reported **zero errors** across all four terms (202408: 103 warnings /
103 info; 202501: 6 / 0; 202508: 11 / 0; 202701: 49 / 49), and historical generic quality reports
were not polluted by Sprint 5 target/freshness checks. Frontend and API verification passed —
endpoints 200, desktop and mobile search, server pagination, freshness UX, GenEd rendering and
details all worked, with no browser console errors.

Search performance at the widened coverage was **not** sufficiently measured; that is REQ-PERF-01.

**Repository state.** Brownfield repo with a mapped codebase (`.planning/codebase/`, map date
2026-09-05) and an ingested handoff document set (`.planning/intel/`). See "Handoff document
status" below — those documents are proposals, and several of their claims are not adopted.

**What exists now vs what comes next:**

| Area | Exists at `62fb2f1` | Next |
|------|---------------------|------|
| Backend platform | FastAPI app factory, DI, schemas, domain services, ORM, Alembic | Deployment config (Phase 2) |
| Course coverage | Configurable targets; 5 courses configured | **Validate 3 unvalidated targets against real data (Phase 1)** |
| Scoring | Historical easiness score, shrinkage, confidence labels, fallback | **Unchanged — preserved as baseline** |
| Seats | Freshness classification, seat-only refresh, API fields, freshness UI | — |
| Frontend | Explicit mock opt-in, pagination hardening, coverage UX, relative timestamps | — |
| Tests | 208 passed / 1 skipped Python, 78 frontend; PostgreSQL integration present but skippable | Widen PostgreSQL coverage (unscheduled) |
| CI | Nothing — no `.github/` directory | Net-new, Phase 2 |
| Deployment | `docker-compose.yml` provisions PostgreSQL only | Minimal, portable (Phase 2) |

**Fixed in Sprint 5** (historical — do not re-plan):

- Frontend silently served fixtures when `VITE_API_BASE_URL` was unset — now requires an explicit
  `VITE_USE_MOCK_DATA=true` opt-in and throws otherwise
- No seat freshness contract — now `src/easy_a/schedule/freshness.py` plus API fields and UI
- No PostgreSQL-specific integration coverage — now present, though it skips without config
- Frontend hard-coded a Spring 2027 term preference — now configuration-driven

**Still open** (evidence-backed observations, not product requirements):

- `GET /api/v1/rankings/search` ranks sections before slicing pagination — needs measurement at
  the widened coverage rather than extrapolation from two courses
- `src/easy_a/grades/parser.py` converts every blank cell to `0` with no suppression path.
  Unresolved: answering it needs a real or sample InfoCenter export.
- 47 non-Tampa Spring 2027 sections remain stored — the current blocker (REQ-DATA-02). Removal
  tooling now exists but has not been run against the beta database.
- AMH 2020, PSY 2012 and BSC 1005 have no imported historical grade data; each falls back to a
  global prior with `effective_n = 0` (REQ-GRADES-01)
- Grade import initializes `course_id` to null; grade rows are unique by term/CRN/**source**, so
  duplicate exports double-count without explicit source selection. Watch during expansion.
- Two seat sources of truth — canonical `Section` columns and `SeatSnapshot` rows. Sprint 5 added
  an authoritative freshness contract on top; the underlying duality is worth watching.

**Live-source reality** (`docs/live-source-drift-2026-09-01.md`, observational, two courses
sampled): every observed Spring 2027 Tampa section in the sample listed instructor `Staff`; no
current-term syllabus was found for either sampled course; CRN `19410` published `190/207/-17`,
confirming upstream genuinely emits negative seats-remaining. **Point-in-time observations from a
two-course sample, not campus-wide facts.**

## Handoff document status

`docs/final-mvp-plan.md`, `docs/final-mvp-ui-spec.md` and `docs/gsd-core-mvp-prompt.md` are
**proposal documents from an earlier planning conversation**. They are useful design thinking and
are retained, but they are **not** a record of confirmed product decisions, and several of their
claims are explicitly not adopted:

| Handoff claim | Actual status |
|---------------|---------------|
| Email seat alerts are required MVP scope | **Not adopted.** Candidate later phase after near-live seat refresh and hosted beta stability. |
| Verified RMP links are required MVP scope | **Not adopted.** Deferred until after hosted beta and core data stability. Not a beta blocker. |
| Replace the score with a grade-only v2 formula | **Not adopted.** The existing scoring model is the baseline. A methodology review is an optional research item only. |
| All offered USF Tampa sections are the launch scope | **Not adopted.** Validated coverage is `MAC 1105` + `ENC 1101`. Broader coverage is an expansion target subject to validation. |
| Eight sequential delivery phases | **Not adopted.** Superseded by the Sprint 5 → hosted beta sequence in `.planning/ROADMAP.md`. |

Design detail in those documents may still inform later work when a feature is actually picked up.
Treat it as input, never as an approved requirement.

## Constraints

- **Validated coverage**: all five configured targets in `config/course_targets.toml` were
  validated against real Spring 2027 data on 2026-09-09 — **75 verified Tampa sections**. Section
  presence is validated for all five; *historical grade coverage* is not — AMH 2020, PSY 2012 and
  BSC 1005 have none. Distinguish the two when reporting coverage. Do not claim campus-wide
  support: five courses is the declared scope, and stored counts remain contaminated until
  REQ-DATA-02 completes.
- **Preserve the existing scoring model**: the historical easiness score, its grade/withdrawal
  composition, Bayesian shrinkage, confidence labels, and course / instructor-course fallback
  behavior all stay. Seats, modality, GenEd and syllabus signals must not influence the score.
- **Baseline and branch safety**: `origin/main` is
  `62fb2f189c8cac67a1500863f080e0f638469df1`. Fetch and verify current `origin/main` before
  planning rather than trusting a recorded SHA. Work from branches or worktrees descended from it.
  A local checkout may lag behind `origin/main` and may hold untracked work — **do not check out,
  merge or fast-forward a local `main` you did not verify.**
  *(Historical baseline evidence: `06634490` was `origin/main` before Sprint 5 and is the commit
  the codebase map was taken at; `d880d3c` was an older local `main`.)*
- **Tech stack**: preserve Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and
  React/TypeScript/Vite/Tailwind, in this repository. No rewrite, no separate product.
- **No fabricated data**: no synthetic fallback in production, no invented coverage figures, no
  unsupported policy assertion, no guessed source link, no silent scope expansion.
- **Bounded source access**: requests to USF public sources stay narrow and bounded, consistent
  with existing practice. No broad crawling.
- **Grade provenance safety**: source hashes and term/CRN/source uniqueness must remain intact
  through coverage expansion; duplicate exports must not double-count.
- **Deployment**: minimal and portable. No provider-specific infrastructure.
- **Never commit raw grade export files.** Grade exports are source data with access conditions;
  the repository stores derived aggregates and provenance, not the exports themselves.
- **Planning system**: GSD Core `.planning/` structure, not GSD2 `.gsd/`.

## Decisions

<!-- Constraints that genuinely govern the work. Items the handoff documents asserted as locked
     but which were never confirmed have been removed — see "Handoff document status" above. -->

<decisions>

### Current baseline constraints

- **D-01 [locked]:** Preserve the existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vite/Tailwind architecture. Work in the existing repository; do not rewrite the application or create a separate product.
- **D-02 [locked]:** Preserve the existing scoring model as the current baseline — historical easiness score, current grade/withdrawal composition, Bayesian shrinkage, confidence labels, and course / instructor-course fallback behavior. A scoring rewrite is not approved scope. A methodology review is an optional research item only.
- **D-03 [locked]:** Seats, modality, GenEd and syllabus signals must not influence the grade score. Changing seat data must not change a historical score.
- **D-04 [locked]:** Respect term/CRN identity, real grade-file terms, source provenance and deduplication. Duplicate exports must not double-count. Conservative professor attribution.
- **D-05 [locked]:** Seat observation age must be visible. Failed requests must not advance the success timestamp, fabricate zero seats, or present stale data as current. Waitlist capacity is separate from available seats.
- **D-06 [locked]:** No fabricated data. No production synthetic fallback, no invented coverage figures, no unsupported policy assertion, no guessed source link, no silent scope expansion, no auto-registration, no LLM or AI features.
- **D-07 [locked]:** Explicit unavailable / insufficient / suppressed / invalid states with reasons. Absent evidence is reported as absent.
- **D-08 [locked]:** No scraping of any source, and no imported RMP ratings, review counts, review text, tags or summaries. This prohibition holds regardless of whether verified RMP links are ever implemented.
- **D-09 [locked]:** Bounded, narrow requests to USF public sources. No broad crawling.
- **D-10 [locked]:** Fetch and verify current `origin/main` before planning; work from branches or worktrees descended from it. Preserve untracked local work; do not check out, merge or fast-forward a local `main` you did not verify.
- **D-11 [locked]:** Use GSD Core's `.planning/` structure, not GSD2 `.gsd/` conventions.
- **D-12 [locked]:** Preserve the passing test baseline and update tests when semantics genuinely change. Measured 2026-09-09 at `d72f8f3` plus the cleanup tooling: 208 passed / 1 skipped without `EASY_A_TEST_POSTGRES_URL` (209 collected); 78 frontend passed. A default run does not use PostgreSQL — state both facts, not one. The PostgreSQL-configured total was 193 at `62fb2f1` and has not been re-measured since; do not quote a current number for it.
- **D-13 [locked]:** Never invent data coverage, source permissions, credential access or deployment completion. Identify missing external dependencies early and name an owner. Do not purchase services.

### Current sprint scope

- **D-14 [complete]:** Sprint 5 delivered configurable course targets, one-pass coverage refresh, seat-only refresh, seat freshness classification and API fields, a coverage metadata endpoint, explicit frontend mock opt-in, pagination hardening, freshness UX and PostgreSQL integration coverage. Merged via PR #14 and PR #15 at `62fb2f1`.
- **D-15 [current-scope]:** Real-data expansion validation is complete (2026-09-09). Current activity is Tampa-only data correction (REQ-DATA-02), then historical grade coverage for AMH/PSY/BSC, then hosted beta. Still excludes a scoring rewrite, email alerts, auth/accounts, RMP, LLM features, and provider-specific deployment infrastructure.
- **D-21 [locked]:** Section deletion is an explicit, reviewable operator step. Any command that removes stored sections reports without writing by default, selects rows by stated criteria, deletes by explicit primary key rather than a broad `WHERE`, and verifies afterwards that historical grade rows and in-scope sections survived — aborting the transaction if they did not. No pipeline stage deletes sections implicitly.
- **D-20 [locked]:** A global-prior fallback score is not course history. Never present a course with `effective_n = 0` as having evidence-backed historical analytics.
- **D-19 [locked]:** Never commit raw grade export files.

### Deferred — candidate later phases, not committed

- **D-16 [deferred]:** Seat alerts and notifications. Appropriate only after near-live seat refresh works and the hosted beta is stable. Do not add subscriber, watch, outbox or email-provider work to the current execution sequence. Architecture notes are retained in the ROADMAP backlog as future / optional design considerations only.
- **D-17 [deferred]:** Verified RMP profile links. Deferred until after hosted beta and core data stability; not a beta blocker. D-08's prohibitions apply whenever it is picked up.
- **D-18 [deferred]:** Broader launch coverage breadth. Expansion is a coverage target subject to data availability, quality, refresh sustainability and performance — not a declared commitment.

</decisions>

## Open Questions

| ID | Question | Blocks | Resolve by |
|----|----------|--------|------------|
| OQ-01 (resolved) | Where does implementation happen? Resolved 2026-09-08: branches and worktrees descended from current `origin/main`, verified by fetch rather than a recorded SHA. Do not check out, merge or fast-forward an unverified local `main`. | Nothing | Resolved |
| OQ-02 (resolved) | Exact test baseline. Re-measured 2026-09-08 at `62fb2f1`: **192 Python passed / 1 skipped, 78 frontend passed**. The skip is the PostgreSQL integration test, which needs `EASY_A_TEST_POSTGRES_URL`. Supersedes the pre-Sprint-5 figure of 166/19 and `.planning/codebase/TESTING.md`'s "~154". | Nothing | Resolved |
| OQ-03 | How does search perform at the widened coverage? Phase 1 did not measure it sufficiently. Search still ranks sections before slicing pagination. | Hosted beta sizing | REQ-PERF-01, by measurement against the corrected dataset |
| OQ-04 | Do real USF InfoCenter grade exports contain suppression markers, or is blank genuinely zero? `src/easy_a/grades/parser.py` currently converts every blank cell to `0` unconditionally, with no suppression path. Answering needs a real or sample export. | Grade-import correctness at broader coverage | Needs a real export file; owner is whoever holds ODS/registrar access |
| OQ-05 | External dependencies not yet supplied: deployment host and domain. | Phase 2 deployment | Before hosted beta |
| OQ-06 (resolved) | Do `AMH 2020`, `PSY 2012` and `BSC 1005` resolve in the catalog, and what coverage do they have? Resolved 2026-09-09: all three present, with 17 / 10 / 2 verified Tampa sections. **None has imported historical grade data** — all three use a global fallback with `effective_n = 0`. | Nothing | Resolved |
| OQ-07 | Are approved historical grade exports available for AMH 2020, PSY 2012 and BSC 1005? External input with a named owner. | REQ-GRADES-01 | Before Phase 3 |

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Restructure from eight greenfield phases to the actual Sprint 5 sequence | The earlier roadmap described a greenfield MVP build and did not reflect a working application with a validated real-data beta. It also sequenced alerts and RMP as required scope. | Applied 2026-09-08 |
| Treat the handoff documents as proposals, not confirmed decisions | Alerts, RMP, a scoring rewrite and campus-wide launch scope were recorded as "locked" and "user-confirmed" without that confirmation. | Applied 2026-09-08 |
| Preserve the existing scoring model | The current model works and is the validated baseline for the beta. Replacing it is a large change with no approval behind it. | Applied 2026-09-08 |
| Keep evidence-backed observations, drop the requirements built on top of them | Findings like the silent fixture fallback and the SQLite/PostgreSQL gap are real and verified; the product requirements the handoff derived from them were not confirmed. | Applied 2026-09-08 |
| Record Sprint 5 complete against merged code rather than against the PR description | Each delivered item was verified present in the tree at `62fb2f1` before its requirement was ticked; the test baseline was re-measured rather than quoted. | Applied 2026-09-08 |
| Demote the handoff docs to low-precedence archival inputs in the ingest manifest | Leaving `gsd-core-mvp-prompt.md` as a precedence-0 ADR meant any future `/gsd-ingest-docs` run could re-promote alerts, RMP, a scoring rewrite and campus-wide scope over current planning. | Applied 2026-09-08 |

---
*Last updated: 2026-09-09 — Phase 2 removal tooling written and tested; the 47 rows are still stored and the blocker stands until the cleanup is run against the beta database.*
