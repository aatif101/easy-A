# Easy-A

## What This Is

Easy-A is a course-intelligence website for USF Tampa students. A student finds a real section and
sees what the historical grade distribution actually looked like, how strong that evidence is,
which syllabus policies are supported by a quotable source, and how many seats were available the
last time the section was successfully checked.

It is an existing, working application — not a greenfield build and not a prototype. Python 3.12 /
FastAPI / SQLAlchemy / Alembic / PostgreSQL 16 on the backend, React / TypeScript / Vite / Tailwind
on the frontend. It has real Spring 2027 schedule ingestion, real historical grade imports, and a
validated real-data beta covering `MAC 1105` and `ENC 1101` with high-confidence historical
analytics, GenEd metadata, seat snapshots and a data-quality pipeline. The API and frontend have
been smoke-tested end to end.

**Current planning phase: Sprint 5.**

## Core Value

Every number a student sees is a real observed outcome with a visible denominator, a named source
and a timestamp — and when the evidence does not exist, the product says so instead of producing a
plausible-looking result.

## Requirements

### Current baseline (working today)

<!-- Verified at commit 06634490 against .planning/codebase/ (map date 2026-09-05) and the
     measured test baseline of 2026-09-08. This is the platform, not scope. -->

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
- ✓ **166 Python tests and 19 frontend tests passing** (measured 2026-09-08 in this worktree)
- ✓ Strict quality gates: ruff (`B,C4,E,F,I,SIM,UP`), mypy `strict = true`, ESLint + `tsc -b`

### Sprint 5 (active scope)

<!-- Full text and acceptance criteria in .planning/REQUIREMENTS.md. -->

- [ ] **REQ-COVERAGE-01** — Configurable course coverage beyond the two-course beta
- [ ] **REQ-SEAT-01** — Seat information with visible observation age
- [ ] **REQ-SEAT-02** — Seat-only refresh workflow
- [ ] **REQ-CONFIG-01** — Production configuration cannot silently serve synthetic data
- [ ] **REQ-TEST-01** — PostgreSQL integration coverage where practical

### Next — hosted beta

- [ ] **REQ-COVERAGE-02** — Broader real-data coverage validated before it is claimed
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

## Context

**Repository state.** Brownfield repo with a mapped codebase (`.planning/codebase/`, map date
2026-09-05) and an ingested handoff document set (`.planning/intel/`). See "Handoff document
status" below — those documents are proposals, and several of their claims are not adopted.

**What exists vs what Sprint 5 adds:**

| Area | Already exists | Sprint 5 work |
|------|----------------|---------------|
| Backend platform | FastAPI app factory, DI, schemas, domain services, ORM, Alembic | Deployment-safe configuration |
| Course coverage | Validated `MAC 1105` + `ENC 1101` beta | Configurable target-course mechanism |
| Scoring | Historical easiness score, shrinkage, confidence labels, fallback behavior | **Unchanged — preserved as baseline** |
| Grade import | XLSX parser, ten buckets, totals, source hashes | Watch dedup/provenance safety during expansion |
| Seats | Schedule client, `Section` columns, `SeatSnapshot` rows, open-seat filter | Freshness classification, explicit timestamps, seat-only refresh |
| Frontend | Responsive table/cards, filters, pagination, details | Freshness UX; remove silent fixture fallback |
| Tests | 166 Python + 19 frontend, all on SQLite | PostgreSQL integration coverage where practical |
| CI | Nothing — no `.github/` directory | Net-new, in Phase 2 |
| Deployment | `docker-compose.yml` provisions PostgreSQL only | Minimal, portable preparation |

**Evidence-backed observations to respect** (findings, not product requirements):

- `web/src/api/rankings.ts` silently serves 287 lines of synthetic fixtures when
  `VITE_API_BASE_URL` is unset — a misconfigured deploy renders plausible fake course data
- Two parallel seat sources of truth — canonical `Section` columns written by
  `src/easy_a/schedule/ingest.py` and `SeatSnapshot` rows — with a fallback in
  `src/easy_a/rankings/service.py` that can make a stale column look current
- Grade import initializes `course_id` to null; grade rows are unique by term/CRN/**source**, so
  duplicate exports double-count without explicit source selection
- `GET /api/v1/rankings/search` ranks every section in the term before slicing pagination, issuing
  roughly six queries per section — needs measurement at broader coverage
- The frontend hard-codes a Spring 2027 term preference
- Python tests run on `sqlite+pysqlite:///:memory:` while deployment targets PostgreSQL 16, and
  Alembic migrations are never applied in tests

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

- **Coverage expansion target, subject to validation**: Current validated beta coverage is
  `MAC 1105` + `ENC 1101`. Sprint 5 broadens coverage through a configurable target-course
  mechanism, and expansion may move toward broader Spring 2027 Tampa coverage. Final launch
  coverage depends on data availability, data quality, refresh sustainability and measured
  performance. Do not claim campus-wide support before it is ingested and validated.
- **Preserve the existing scoring model**: the historical easiness score, its grade/withdrawal
  composition, Bayesian shrinkage, confidence labels, and course / instructor-course fallback
  behavior all stay. Seats, modality, GenEd and syllabus signals must not influence the score.
- **Baseline and branch safety**: `origin/main` is `06634490de5c765bdc7b55e4f439476b0e4fa0f7`.
  Local `refs/heads/main` is still `d880d3c2bd31158c2392725e5c203ac92b2088fa` and the primary
  checkout at `C:/Users/smati/VS Code Projects/easy-A` is on it with untracked files present.
  Work from branches or worktrees descended from `origin/main`; **leave local `main` and its
  untracked files alone.** The untracked `web/` there was verified on 2026-09-08 to contain only
  `dist/` and `node_modules/` — build artifacts, no source — but the directory is still not this
  session's to clean up.
- **Tech stack**: preserve Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and
  React/TypeScript/Vite/Tailwind, in this repository. No rewrite, no separate product.
- **No fabricated data**: no synthetic fallback in production, no invented coverage figures, no
  unsupported policy assertion, no guessed source link, no silent scope expansion.
- **Bounded source access**: requests to USF public sources stay narrow and bounded, consistent
  with existing practice. No broad crawling.
- **Grade provenance safety**: source hashes and term/CRN/source uniqueness must remain intact
  through coverage expansion; duplicate exports must not double-count.
- **Deployment**: minimal and portable. No provider-specific infrastructure in Sprint 5.
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
- **D-10 [locked]:** Work from branches or worktrees descended from `origin/main`. Preserve untracked local work; do not check out, merge or fast-forward local `main`.
- **D-11 [locked]:** Use GSD Core's `.planning/` structure, not GSD2 `.gsd/` conventions.
- **D-12 [locked]:** Preserve the passing test baseline (166 Python / 19 frontend, measured 2026-09-08) and update tests when semantics genuinely change. PostgreSQL integration coverage is valuable because the current suite is SQLite-only and never applies Alembic migrations.
- **D-13 [locked]:** Never invent data coverage, source permissions, credential access or deployment completion. Identify missing external dependencies early and name an owner. Do not purchase services.

### Current sprint scope

- **D-14 [current-scope]:** Sprint 5 covers configurable broader course coverage, a seat-only refresh workflow, seat freshness classification and timestamps, frontend freshness UX, production-safe frontend/backend configuration, deployment preparation, and PostgreSQL integration coverage where practical.
- **D-15 [current-scope]:** Sprint 5 explicitly excludes a scoring methodology rewrite, email seat alerts, auth/accounts, RMP integration, LLM features, and provider-specific deployment infrastructure.

### Deferred — candidate later phases, not committed

- **D-16 [deferred]:** Seat alerts and notifications. Appropriate only after near-live seat refresh works and the hosted beta is stable. Do not add subscriber, watch, outbox or email-provider work to the current execution sequence. Architecture notes are retained in the ROADMAP backlog as future / optional design considerations only.
- **D-17 [deferred]:** Verified RMP profile links. Deferred until after hosted beta and core data stability; not a beta blocker. D-08's prohibitions apply whenever it is picked up.
- **D-18 [deferred]:** Broader launch coverage breadth. Expansion is a coverage target subject to data availability, quality, refresh sustainability and performance — not a declared commitment.

</decisions>

## Open Questions

| ID | Question | Blocks | Resolve by |
|----|----------|--------|------------|
| OQ-01 (resolved) | Where does implementation happen? Resolved 2026-09-08: branches and worktrees descended from `origin/main` (`06634490`); leave local `main` and its untracked files alone. | Nothing | Resolved |
| OQ-02 (resolved) | Exact baseline test counts. Resolved 2026-09-08 by direct measurement in this worktree: **166 Python and 19 frontend tests passing**. This confirms the handoff PRD's figure and supersedes `.planning/codebase/TESTING.md`'s approximate "~154". All 166 run on SQLite. | Nothing | Resolved |
| OQ-03 | How broadly can coverage expand while keeping refresh sustainable and search performance acceptable? Search currently ranks every section in a term before pagination. | Phase 2 coverage claims | Sprint 5 / Phase 2, by measurement |
| OQ-04 | Do real USF InfoCenter grade exports contain suppression markers, or is blank genuinely zero? `src/easy_a/grades/parser.py` currently converts every blank cell to `0` unconditionally, with no suppression path. Answering needs a real or sample export. | Grade-import correctness at broader coverage | Needs a real export file; owner is whoever holds ODS/registrar access |
| OQ-05 | External dependencies not yet supplied: deployment host and domain. | Phase 2 deployment | Before hosted beta |

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Restructure from eight greenfield phases to the actual Sprint 5 sequence | The earlier roadmap described a greenfield MVP build and did not reflect a working application with a validated real-data beta. It also sequenced alerts and RMP as required scope. | Applied 2026-09-08 |
| Treat the handoff documents as proposals, not confirmed decisions | Alerts, RMP, a scoring rewrite and campus-wide launch scope were recorded as "locked" and "user-confirmed" without that confirmation. | Applied 2026-09-08 |
| Preserve the existing scoring model | The current model works and is the validated baseline for the beta. Replacing it is a large change with no approval behind it. | Applied 2026-09-08 |
| Keep evidence-backed observations, drop the requirements built on top of them | Findings like the silent fixture fallback and the SQLite/PostgreSQL gap are real and verified; the product requirements the handoff derived from them were not confirmed. | Applied 2026-09-08 |

---
*Last updated: 2026-09-08 — corrected to reflect the actual project baseline and Sprint 5 scope.*
