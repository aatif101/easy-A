# Roadmap: Easy-A

## Overview

Easy-A is a working course-intelligence application for USF Tampa students: FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, configurable course coverage, and seat freshness classification.

This roadmap describes the sequence forward from that baseline. It is **not** a greenfield MVP
plan, and it does not restart the project.

**Current baseline: `origin/main` = `d72f8f3d77a11f301f2b74f56088a217226feefa`**
(verified by fetch 2026-09-09; Sprint 5 via PR #14 + #15, Tampa scope fix via PR #16, all at
ancestor `62fb2f1` — everything since is planning/docs only).

**Current position: Sprint 5 and real-data validation are complete. Phase 2 — Tampa-only data
correction — is the current work and is blocking.**

### How to read this roadmap

| Section | Meaning |
|---------|---------|
| Sprint 5 | **Complete.** Merged. Not scope. |
| Phase 1 — Real-data expansion validation | **Complete.** Executed; results recorded below. |
| Phase 2 — Tampa-only data correction | **Current.** Blocks trustworthy coverage numbers. |
| Phase 3 — Historical grade coverage | Next. |
| Phase 4 — Hosted beta | After that. |
| Backlog | Candidate later phases. Not scheduled, not committed. |

---

## Sprint 5 — COMPLETE

Merged via PR #14, PR #15 and PR #16. Verified present in code at `62fb2f1`.

- **PR #14** — configurable course targets (`src/easy_a/refresh/targets.py`, `target_cli.py`,
  `config/course_targets.toml`), one-pass coverage refresh (`src/easy_a/refresh/coverage.py`),
  seat-only refresh (`scripts/refresh_seats.py`), seat freshness classification
  (`src/easy_a/schedule/freshness.py`), freshness API fields, coverage metadata endpoint
  (`GET /api/v1/metadata/coverage`), PostgreSQL integration coverage
- **PR #15** — explicit mock opt-in via `VITE_USE_MOCK_DATA` with no silent production fixture
  fallback, scalable broader-course UX, server-backed pagination hardening, seat freshness UI,
  coverage UX, relative seat observation timestamps
- **PR #16** — coverage refresh pins `campus="T"` and rejects non-Tampa rows before ingestion

**Requirements delivered:** REQ-COVERAGE-01, REQ-SEAT-01, REQ-SEAT-02, REQ-CONFIG-01.
REQ-TEST-01 is partial — PostgreSQL integration exists but skips without configuration.

---

## Phase 1: Real-Data Expansion Validation — COMPLETE

**Executed.** All five configured Spring 2027 (`202701`) targets verified present in the catalog.

| Course | Catalog | Verified Tampa sections |
|--------|---------|-------------------------|
| MAC 1105 | present | 5 |
| ENC 1101 | present | 41 |
| AMH 2020 | present | 17 |
| PSY 2012 | present | 10 |
| BSC 1005 | present | 2 |
| **Verified Tampa total** | | **75** |

**Seat refresh:** appended 75 snapshots; preserved previous snapshots and section identity; left
all 237 grade rows unchanged; syllabi remained empty; all observed Tampa seats fresh immediately
after refresh.

**Data quality:** zero errors across all four terms.

| Term | Errors | Warnings | Info |
|------|--------|----------|------|
| 202408 | 0 | 103 | 103 |
| 202501 | 0 | 6 | 0 |
| 202508 | 0 | 11 | 0 |
| 202701 | 0 | 49 | 49 |

Historical generic quality reports were not polluted by Sprint 5 target/freshness checks.

**Frontend / API:** required endpoints returned 200; desktop and mobile search worked; server
pagination worked; freshness UX worked; GenEd rendering worked; details worked; no browser
console errors.

**What the pass exposed:** a campus-scope bug — configured refresh queried all campuses, and the
first pass inserted **47 non-Tampa Spring 2027 sections** into the existing beta database. PR #16
fixed the cause. The rows were preserved, not removed. That is Phase 2.

**Not sufficiently measured:** search performance at the widened coverage. Split into
REQ-PERF-01 under Phase 4 rather than being falsely marked complete.

**Requirements:** REQ-COVERAGE-02 ✓ complete (search performance carved out to REQ-PERF-01)

---

## Phase 2: Tampa-Only Data Correction — CURRENT

**Goal**: Stored, API and coverage-endpoint counts reflect Tampa-only reality, with the
contaminated rows removed and nothing legitimate lost.

**Depends on**: PR #16 (merged)

**Status**: Current — blocking. Any coverage figure read from the running database is wrong
until this completes.

**Why it exists**: the first expansion pass inserted 47 non-Tampa Spring 2027 sections. PR #16's
merged description is explicit that it "does not delete the 47 other-campus sections inserted by
the initial validation pass… They remain visible in stored coverage/API counts until a separately
reviewed cleanup."

**Scope**

1. ✓ A targeted, reviewable removal step. Written 2026-09-09:
   `scripts/cleanup_non_tampa_sections.py` → `src/easy_a/refresh/cleanup.py` and
   `cleanup_cli.py`, with 16 tests in `tests/refresh/test_cleanup.py` and a README section.
   Reports without writing unless `--apply` is given; selects by term and stored campus;
   deletes by explicit primary key; `--expect-removed N` refuses to proceed unless exactly `N`
   sections match; refuses sections carrying a stored syllabus; and aborts the transaction if
   stored grade rows change, a kept-campus section is lost, the number removed differs from the
   number matched, or any other-campus section remains.
2. ○ **Running it against the beta database.** Not done — needs an operator with database
   access. Writing the tooling did not remove the rows.
3. ○ A clean Tampa refresh afterwards
4. ○ API and coverage-endpoint verification against the corrected data

**Success criteria** (what must be TRUE, each with a real measured number)

1. Exact cleanup result recorded — rows removed, and the criteria used to select them
2. Final Tampa-only stored counts recorded
3. Final API counts recorded
4. Final coverage-endpoint counts recorded
5. **No historical grades and no Tampa sections deleted** — the 237 grade rows and all 75
   verified Tampa sections survive intact, confirmed by count
6. Stored, API and coverage counts agree with each other

**Requirements**: REQ-DATA-02

---

## Phase 3: Historical Grade Coverage for AMH / PSY / BSC

**Goal**: The three newly validated courses have real historical grade data instead of a global
fallback.

**Depends on**: Phase 2

**Status**: Next

Currently `AMH 2020`, `PSY 2012` and `BSC 1005` have **no imported historical grade data**. They
fall back to a global prior with `effective_n = 0`. Those fallback scores are not evidence-backed
course history and must not be described as such anywhere in the product or the docs.

**Import priority: AMH 2020 → PSY 2012 → BSC 1005.**

**Scope**

1. Obtain and import approved historical grade exports, in priority order
2. Validate the resulting course-level analytics per course
3. Record which terms actually have data per course, and which do not

**Success criteria**

1. Each imported course reports real observed outcomes with a non-zero effective N, or is
   explicitly recorded as still lacking data
2. Analytics for each imported course are validated against the source aggregate
3. No course presents a global fallback as if it were course history

**Requirements**: REQ-GRADES-01

**Dependency**: approved historical grade exports are an external input. Never commit raw export
files.

---

## Phase 4: Hosted Beta — Deployment, CI, Performance, Observability

**Goal**: The corrected application runs as a hosted beta with enough automation and measurement
to keep it running.

**Depends on**: Phase 2 (and Phase 3 for meaningful coverage)

**Status**: Later

**Scope**

1. Deployment — minimal and portable, no provider-specific infrastructure
2. CI for Python and frontend checks (net-new; there is no `.github/` directory today)
3. **Search performance measurement at the widened coverage** — carried over from Phase 1, which
   did not measure it sufficiently
4. Observability — refresh success/failure, search latency
5. Operator runbook — refreshing data, recovering from a failed refresh

**Success criteria**

1. The hosted beta is reachable and serves real data
2. CI runs Python and frontend checks on push
3. Search latency at validated coverage is measured and recorded
4. An operator can follow the runbook to refresh data and recover from a failed refresh

**Requirements**: REQ-PERF-01, REQ-OPS-01

---

## Backlog — candidate later phases

Not scheduled. Not committed. None is required for the hosted beta, and none should be pulled
into the current execution sequence.

### Phase 999.1: Seat alerts and notifications (candidate later phase)

**Not current scope.** Appropriate only after the hosted beta is stable. Do not add subscriber,
watch, outbox or email-provider work to the current sequence.

Design considerations preserved as **future / optional only**: a durable worker independent of
any browser session, polling shared across subscribers, a persisted outbox with idempotency and
bounded retries, verified email ownership before any send, and honest language distinguishing
provider acceptance from inbox receipt.

### Phase 999.2: Verified RMP profile links (candidate later phase)

**Not current scope.** Deferred until after hosted beta and core data stability. Not a blocker.
Whenever picked up: no scraping, no bulk crawler, and no imported ratings, review counts, review
text, tags or summaries — a verified link only.

### Phase 999.3: Deeper professor-specific coverage (candidate later phase)

Depends on named-instructor coverage in the source data.

### Phase 999.4: Additional UX features (candidate later phase)

Deep links, a methodology page, and expanded accessibility work.

### Phase 999.5: Methodology review (optional research item)

The current scoring model is the baseline and stays. An evidence-backed review of how it behaves
with little or no grade history is an **optional research item, not active implementation scope**.
Any change would require documented evidence plus matching methodology and test updates. No
rewrite is planned or approved.

---

## Progress

| Phase | Status | Progress |
|-------|--------|----------|
| Sprint 5 | ✓ Complete (PR #14, #15, #16) | 100% |
| 1 — Real-data expansion validation | ✓ Complete | 100% |
| 2 — Tampa-only data correction | ◆ Current (blocking) — tooling written, not yet run | 25% |
| 3 — Historical grade coverage | ○ Next | 0% |
| 4 — Hosted beta | ○ Later | 0% |

---

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-COVERAGE-01 | Sprint 5 | ✓ Complete |
| REQ-SEAT-01 | Sprint 5 | ✓ Complete |
| REQ-SEAT-02 | Sprint 5 | ✓ Complete |
| REQ-CONFIG-01 | Sprint 5 | ✓ Complete |
| REQ-TEST-01 | Sprint 5 | ◐ Partial — PostgreSQL integration exists, skips without config |
| REQ-COVERAGE-02 | 1 | ✓ Complete — search performance carved out to REQ-PERF-01 |
| REQ-DATA-02 | 2 | ◆ Current |
| REQ-GRADES-01 | 3 | ○ Next |
| REQ-PERF-01 | 4 | ○ Later |
| REQ-OPS-01 | 4 | ○ Later |

Backlog requirements (`REQ-ALERT-*`, `REQ-RMP-01`) are deliberately unmapped — they belong to
candidate later phases.

---
*Last updated: 2026-09-09 — Phase 2 removal tooling written and tested; execution against the
beta database, the clean refresh and the verification counts remain outstanding.*
