# Roadmap: Easy-A

## Overview

Easy-A is a working course-intelligence application for USF Tampa students. It has a FastAPI
backend, a React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real
historical grade imports, configurable course coverage, and seat freshness classification.

This roadmap describes the sequence forward from that baseline. It is **not** a greenfield MVP
plan, and it does not restart the project.

**Current baseline: `origin/main` = `62fb2f189c8cac67a1500863f080e0f638469df1`** (Sprint 5 merged via PR #14 and
PR #15; Tampa scope restriction via PR #16).

**Current position: Sprint 5 is complete. Next activity is real-data expansion validation.**

### How to read this roadmap

| Section | Meaning |
|---------|---------|
| Sprint 5 | **Complete.** Merged to main. Not scope. |
| Phase 1 — Real-data expansion validation | Current activity. |
| Phase 2 — Hosted beta | Next, after validation. |
| Backlog | Candidate later phases. Not scheduled, not committed. |

Coverage numbers and launch breadth throughout this document are **coverage expansion targets
subject to validation**, not declared support. Configuring a course target is not the same as
having validated coverage for it.

---

## Sprint 5 — COMPLETE

Merged to `main` via PR #14, PR #15 and PR #16. Verified present in the code at `62fb2f1`.

**PR #14 — configurable coverage and seat refresh**

- Configurable course targets — `src/easy_a/refresh/targets.py`, `target_cli.py`,
  config at `config/course_targets.toml`
- One-pass coverage refresh and seat-only refresh — `src/easy_a/refresh/coverage.py`,
  `scripts/refresh_seats.py`
- Seat freshness classification — `src/easy_a/schedule/freshness.py` (`SeatFreshness`,
  `classify_observation`, `snapshot_freshness`)
- Freshness fields exposed through the API
- Coverage metadata endpoint — `GET /api/v1/metadata/coverage`
- PostgreSQL integration coverage — `tests/refresh/test_postgres_coverage.py`

**PR #15 — frontend hardening and freshness UX**

- Explicit mock opt-in via `VITE_USE_MOCK_DATA`; unset `VITE_API_BASE_URL` now raises instead of
  silently serving fixtures — `web/src/api/rankings.ts`
- Scalable broader-course UX and server-backed pagination hardening
- Seat freshness UI and relative observation timestamps — `web/src/components/SeatBadge.tsx`,
  `web/src/utils/time.ts`
- Coverage UX — `web/src/components/CoverageNotice.tsx`

**PR #16 — Tampa scope restriction**

- Coverage refresh now pins `campus="T"` in the schedule query and rejects any returned row whose
  campus is not Tampa — `src/easy_a/refresh/coverage.py`. Tightens the bounded-request guarantee
  so a widened course list cannot silently pull non-Tampa sections.

**Requirements delivered:** REQ-COVERAGE-01, REQ-SEAT-01, REQ-SEAT-02, REQ-CONFIG-01.
REQ-TEST-01 is partially delivered — see `.planning/REQUIREMENTS.md` for its exact status.

---

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | Real-Data Expansion Validation | Current |
| 2 | Hosted Beta — Deployment, CI, Observability | Next |

---

## Phase Details

### Phase 1: Real-Data Expansion Validation

**Goal**: Know what the five configured course targets actually resolve to in real Spring 2027
data — counts, availability, quality and cost — so coverage can be claimed on evidence rather
than on configuration.

**Depends on**: Sprint 5 (complete)

**Status**: Current

**Configured targets** (`config/course_targets.toml`, catalog edition 2026-2027):

| Subject | Number |
|---------|--------|
| MAC | 1105 |
| ENC | 1101 |
| AMH | 2020 |
| PSY | 2012 |
| BSC | 1005 |

`MAC 1105` and `ENC 1101` are the previously validated beta pair. `AMH 2020`, `PSY 2012` and
`BSC 1005` are **configured but not yet validated** — configuration is not coverage.

**What the validation pass must determine**

For the configured Spring 2027 (`202701`) Tampa targets, by running real ingestion:

1. Actual section counts per course
2. Catalog availability — whether each target resolves in the 2026-2027 catalog
3. GenEd attribute coverage
4. Seat freshness behavior across a real refresh cycle
5. Instructor coverage — how many sections carry a named instructor rather than `Staff`
6. Historical grade coverage — which terms actually have imported grade data per course
7. Quality findings surfaced by the data-quality pipeline
8. Search performance implications at the widened coverage

**Success criteria** (what must be TRUE)

1. Every figure reported is measured from a real ingestion run, with the run's date and scope
   recorded. No count, term or percentage is stated without a source.
2. Courses that fail to resolve, or that have no historical grade data, are reported as such
   rather than omitted.
3. Search performance is measured at the widened coverage, not extrapolated from two courses.
4. The result states plainly which of the five targets are validated and which are not.

**Requirements**: REQ-COVERAGE-02

**Constraints**: requests to USF public sources stay narrow and bounded — no broad crawling. Do
not commit raw grade export files.

---

### Phase 2: Hosted Beta — Deployment, CI, Observability

**Goal**: The validated application runs as a hosted beta with enough automation and measurement
to keep it running.

**Depends on**: Phase 1

**Status**: Next

**Scope**

1. Deployment — minimal and portable, no provider-specific infrastructure
2. CI for Python and frontend checks (net-new; there is no `.github/` directory today)
3. Performance measurement at validated coverage
4. Observability — refresh success/failure, search latency
5. Operator runbook — refreshing data, recovering from a failed refresh

**Success criteria** (what must be TRUE)

1. The hosted beta is reachable and serves real data.
2. CI runs Python and frontend checks on push.
3. Search latency at validated coverage is measured and recorded.
4. An operator can follow the runbook to refresh data and recover from a failed refresh.

**Requirements**: REQ-OPS-01

---

## Backlog — candidate later phases

Not scheduled. Not committed. None is required for the hosted beta, and none should be pulled
into the current execution sequence.

### Phase 999.1: Seat alerts and notifications (candidate later phase)

**Not current scope.** A candidate later phase, appropriate only after the hosted beta is stable.
Do not add subscriber, watch, outbox or email-provider work to the current sequence.

Design considerations preserved as **future / optional only**: alerting would need a durable
worker independent of any browser session, polling shared across subscribers, a persisted outbox
with idempotency and bounded retries, verified email ownership before any send, and honest
language distinguishing provider acceptance from inbox receipt.

### Phase 999.2: Verified RMP profile links (candidate later phase)

**Not current scope.** Deferred until after hosted beta and core data stability. Not a blocker.
Constraints that hold whenever it is picked up: no scraping, no bulk crawler, and no imported
ratings, review counts, review text, tags or summaries — a verified link only.

### Phase 999.3: Deeper professor-specific coverage (candidate later phase)

Depends on named-instructor coverage in the source data, which Phase 1 will measure for the first
time across more than two courses.

### Phase 999.4: Additional UX features (candidate later phase)

Deep links, a methodology page, and expanded accessibility work.

### Phase 999.5: Methodology review (optional research item)

The current scoring model is the baseline and stays. An evidence-backed review of how it behaves
with little or no grade history is an **optional research item, not active implementation scope**.
Any change would require documented evidence plus matching methodology and test updates. No
rewrite is planned or approved.

---

## Progress

| Phase | Status | Plans | Progress |
|-------|--------|-------|----------|
| Sprint 5 | ✓ Complete (merged, PR #14 + #15) | — | 100% |
| 1 | ◆ Current | 0 | 0% |
| 2 | ○ Pending | 0 | 0% |

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-COVERAGE-01 | Sprint 5 | ✓ Complete |
| REQ-SEAT-01 | Sprint 5 | ✓ Complete |
| REQ-SEAT-02 | Sprint 5 | ✓ Complete |
| REQ-CONFIG-01 | Sprint 5 | ✓ Complete |
| REQ-TEST-01 | Sprint 5 | ◐ Partial — PostgreSQL integration exists and skips without config |
| REQ-COVERAGE-02 | 1 | ○ Current |
| REQ-OPS-01 | 2 | ○ Pending |

Backlog requirements (`REQ-ALERT-*`, `REQ-RMP-01`) are deliberately unmapped — they belong to
candidate later phases and are not part of the current sequence.

---
*Last updated: 2026-09-08 — Sprint 5 recorded complete against merged code at `62fb2f1`; next
activity is real-data expansion validation for the five configured targets.*
