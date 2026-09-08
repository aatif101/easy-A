# Roadmap: Easy-A

## Overview

Easy-A is a working course-intelligence application for USF Tampa students, already well beyond
prototype. It has a FastAPI backend, a React/TypeScript frontend, PostgreSQL, real Spring 2027
schedule ingestion, real historical grade imports, and a validated real-data beta covering
`MAC 1105` and `ENC 1101` with high-confidence historical analytics.

This roadmap describes the sequence forward from that baseline. It is **not** a greenfield MVP
plan, and it does not restart the project.

**Current planning phase: Sprint 5.**

### How to read this roadmap

| Section | Meaning |
|---------|---------|
| Already delivered | Working today; the platform the next work builds on. Not scope. |
| Phase 1 — Sprint 5 | Current active scope. |
| Phase 2 — Hosted beta | Next, after Sprint 5 lands. |
| Backlog | Candidate later phases. Not scheduled, not committed, not required for beta. |

Coverage numbers, launch breadth and refresh cadence throughout this document are **coverage
expansion targets subject to validation**, not declared support. Nothing here claims coverage
that has not actually been ingested and validated.

---

## Already delivered (current baseline)

Working and verified at baseline commit `06634490`. Evidence: `.planning/codebase/` (map date
2026-09-05) and the test baseline measured directly on 2026-09-08 (see
`.planning/phases/_superseded/01-baseline-scope-and-contracts/01-RESEARCH.md`).

- Foundational ingestion — catalog, schedule, syllabi and grades, each shaped
  `client.py → parser.py → ingest.py → cli.py`, orchestrated by `src/easy_a/refresh/service.py`
- Historical grade analytics and signals — XLSX import across all ten grade buckets with totals,
  source hashes and term/CRN joins (`src/easy_a/grades/`); deterministic syllabus policy
  extraction for nine categories with provenance and evidence quotes (`src/easy_a/signals/`)
- Ranking service — `src/easy_a/rankings/` joining analytics, section facts, GenEd attributes,
  seats, modality and deterministic signals
- API — read-only `/api/v1/rankings/{section,course,search}` and `/api/v1/metadata`
- Frontend — React SPA with responsive table/cards, metadata-backed filters, pagination,
  expandable details, and error/loading/empty states
- Real-data beta — real Spring 2027 schedule ingestion and real historical grade imports
- `MAC 1105` + `ENC 1101` historical integration with high-confidence analytics
- GenEd metadata, seat snapshots, and a data-quality pipeline
- Quality hardening — ruff (`B,C4,E,F,I,SIM,UP`), mypy `strict = true` across
  `src migrations scripts tests`, ESLint + `tsc -b`
- Measured test baseline: **166 Python tests and 19 frontend tests passing** (measured
  2026-09-08 in this worktree). All Python tests run on SQLite.
- API and frontend smoke-tested end to end

---

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | Sprint 5 — Coverage Expansion, Seat Freshness, Deployment-Safe Configuration | Current |
| 2 | Hosted Beta — Coverage Validation, Deployment, Observability, CI | Next |

Backlog items are listed after the phase details and are **not** numbered into this sequence.

---

## Phase Details

### Phase 1: Sprint 5 — Coverage Expansion, Seat Freshness, Deployment-Safe Configuration

**Goal**: Easy-A serves more than the two validated beta courses, shows seat information whose
age a student can actually see, and can be configured for a hosted deployment without silently
serving synthetic data.

**Depends on**: Nothing — builds directly on the current baseline

**Status**: Current

**Scope**

1. **Configurable broader course coverage.** Replace the two-course beta shape with a
   configurable target-course mechanism so coverage can be widened without code changes.
   Expansion may move toward broader Spring 2027 Tampa coverage; the eventual breadth is a
   coverage expansion target subject to data availability, data quality, refresh sustainability
   and measured performance.
2. **Seat-only refresh workflow.** A refresh path that updates seat availability without
   re-running the full ingestion pipeline.
3. **Seat freshness classification and timestamps.** Explicit last-successful-observation time,
   distinct from last attempt. A failed request must not advance the success timestamp, fabricate
   a zero seat count, or make stale data look current.
4. **Frontend freshness UX.** Surface observation age and staleness in the interface, with a text
   label for every state rather than color alone.
5. **Production-safe frontend/backend configuration.** `web/src/api/rankings.ts` currently serves
   synthetic fixtures when `VITE_API_BASE_URL` is unset — a misconfigured deploy renders plausible
   fake course data. Production must fail visibly instead. Fixtures stay explicitly opt-in for
   development and tests.
6. **Deployment preparation.** Minimal and portable. No provider-specific infrastructure.
7. **PostgreSQL integration coverage where practical.** All 166 Python tests currently run on
   SQLite while the deployment target is PostgreSQL 16, and Alembic migrations are never applied
   in tests. Close what is practical within this sprint rather than treating it as all-or-nothing.

**Explicitly out of scope for Sprint 5**

- Scoring methodology rewrite — the current model stays as the baseline
- Email seat alerts — see Backlog
- Auth or accounts
- RMP integration — see Backlog
- LLM features
- Provider-specific deployment infrastructure beyond minimal and portable preparation

**Success criteria** (what must be TRUE)

1. Course coverage is driven by configuration rather than hard-coded course selection, and
   widening coverage does not require a code change.
2. Seat data carries an explicit last-successful-observation timestamp, distinguishable from a
   failed attempt, and the frontend shows observation age with a text label.
3. A production build with no API base URL configured fails visibly and never renders synthetic
   fixture data.
4. Coverage actually ingested and validated is recorded with real counts — no coverage claim is
   made ahead of ingestion.
5. Whatever PostgreSQL integration coverage is added runs against PostgreSQL 16, and the existing
   166 Python / 19 frontend baseline still passes.

**Requirements**: REQ-COVERAGE-01, REQ-SEAT-01, REQ-SEAT-02, REQ-CONFIG-01, REQ-TEST-01

---

### Phase 2: Hosted Beta — Coverage Validation, Deployment, Observability, CI

**Goal**: The expanded application runs as a hosted beta on real data, with enough measurement and
automation to keep it running.

**Depends on**: Phase 1

**Status**: Next

**Scope**

1. Broader real-data coverage validation — verify what was actually ingested, with real counts
2. Deploy the hosted beta
3. Performance and observability hardening — measure search at broader coverage rather than at
   two courses
4. CI for Python and frontend checks (net-new; there is no `.github/` directory today)
5. Operator runbook

**Success criteria** (what must be TRUE)

1. Ingested coverage is reported with actual counts and named terms, with exclusions stated.
2. The hosted beta is reachable and serves real data.
3. Search performance is measured at the broader coverage level, not extrapolated from the
   two-course beta.
4. CI runs Python and frontend checks on push.
5. An operator can follow the runbook to refresh data and recover from a failed refresh.

**Requirements**: REQ-COVERAGE-02, REQ-OPS-01

---

## Backlog — candidate later phases

Not scheduled. Not committed. None of these is required for the hosted beta, and none should be
pulled into the Sprint 5 or Phase 2 execution sequence.

### Phase 999.1: Seat alerts and notifications (candidate later phase)

A student subscribes to a section and is notified when seats are reported available.

**Not current scope.** Seat alerting is a candidate later phase, appropriate only after near-live
seat refresh is working and the hosted beta is stable. Do not add subscriber, watch, outbox or
email-provider work to the current execution sequence.

Design considerations preserved from the handoff documents, **future / optional only**: alerting
would need a durable scheduled worker independent of any browser session, polling shared across
subscribers rather than per-subscriber, a persisted outbox with idempotency and bounded retries,
verified email ownership before any send, and honest language distinguishing provider acceptance
from inbox receipt. These are notes for whoever eventually designs the feature, not requirements.

### Phase 999.2: Verified RMP profile links (candidate later phase)

**Not current scope.** Deferred until after hosted beta and core data stability. Verified links
may be considered later. RMP is not a blocker for the beta.

Constraints that hold whenever this is picked up: no scraping, no bulk crawler, and no imported
ratings, review counts, review text, tags or summaries — a link only.

### Phase 999.3: Deeper professor-specific coverage (candidate later phase)

Professor-specific historical evidence depends on named-instructor coverage in the source data.
A two-course sample found every observed Spring 2027 Tampa section listed as instructor `Staff`;
campus-wide coverage is unmeasured. Worth revisiting once broader coverage is actually ingested
and the real rate is known.

### Phase 999.4: Additional UX features (candidate later phase)

Deep links, methodology page, expanded accessibility work, and interface refinements beyond the
freshness UX in Sprint 5.

### Phase 999.5: Methodology review (optional research item)

The current scoring model is the baseline and stays. This is an **optional research item, not
active implementation scope**: an evidence-backed review of how the existing historical easiness
score behaves when a course has little or no grade history, and whether the confidence labelling
communicates that honestly. Any change would require documented evidence plus matching
methodology and test updates. No rewrite is planned or approved.

---

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| 1 | ○ Planning | 0 | 0% |
| 2 | ○ Pending | 0 | 0% |

---

## Coverage

Every active requirement in `.planning/REQUIREMENTS.md` maps to a phase:

| Requirement | Phase |
|-------------|-------|
| REQ-COVERAGE-01 | 1 |
| REQ-SEAT-01 | 1 |
| REQ-SEAT-02 | 1 |
| REQ-CONFIG-01 | 1 |
| REQ-TEST-01 | 1 |
| REQ-COVERAGE-02 | 2 |
| REQ-OPS-01 | 2 |

Backlog requirements (`REQ-ALERT-*`, `REQ-RMP-01`) are deliberately unmapped — they belong to
candidate later phases and are not part of the current sequence.

---
*Last updated: 2026-09-08 — restructured to match the actual project sequence from the current
Sprint 5 baseline, replacing an earlier eight-phase greenfield MVP structure that did not reflect
the working application.*
