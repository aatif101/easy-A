# Roadmap: Easy-A

## Overview

Easy-A is a working course-intelligence application for USF Tampa students: FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, configurable course coverage, and seat freshness classification.

This roadmap describes the sequence forward from that baseline. It is **not** a greenfield MVP
plan, and it does not restart the project.

**Current baseline: `origin/main` = `d72f8f3d77a11f301f2b74f56088a217226feefa`**
(verified by fetch on 2026-09-14).

**Current position: Phase 2 — Tampa-only data correction — is complete and verified on PR #18.
Review/merge is the current gate; Phase 3 historical grade coverage follows.**

### How to read this roadmap

| Section | Meaning |
|---------|---------|
| Sprint 5 | **Complete.** Merged. Not scope. |
| Phase 1 — Real-data expansion validation | **Complete.** Executed; results recorded below. |
| Phase 2 — Tampa-only data correction | **Complete on PR #18.** Live data verified; merge pending. |
| Phase 3 — Historical grade coverage | Next after PR #18 and approved exports. |
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
fixed the cause. The rows were preserved at that time; Phase 2 removed them on 2026-09-14.

**Not sufficiently measured:** search performance at the widened coverage. Split into
REQ-PERF-01 under Phase 4 rather than being falsely marked complete.

**Requirements:** REQ-COVERAGE-02 ✓ complete (search performance carved out to REQ-PERF-01)

---

## Phase 2: Tampa-Only Data Correction — COMPLETE ON PR #18

**Goal**: Stored, API and coverage-endpoint counts reflect Tampa-only reality, with the
contaminated rows removed and nothing legitimate lost.

**Depends on**: PR #16 (merged)

**Status**: Executed and verified 2026-09-14. PR #18 awaits review and merge.

**Why it exists**: the first expansion pass inserted 47 non-Tampa Spring 2027 sections. PR #16's
merged description is explicit that it "does not delete the 47 other-campus sections inserted by
the initial validation pass… They remain visible in stored coverage/API counts until a separately
reviewed cleanup."

**Scope**

1. A targeted, dry-run-first removal of the 47 non-Tampa Spring 2027 sections
2. A clean Tampa refresh afterwards
3. API and coverage-endpoint verification against the corrected data
4. An independent quality error for any future stored section outside Tampa

**Success criteria** (what must be TRUE, each with a real measured number)

1. ✓ Exact cleanup result: 47 sections selected from term `202701`, configured targets only,
   nonblank campus other than Tampa after stripping and case-folding
2. ✓ Removed 47 linked seat snapshots, 47 instructor observations, 0 syllabi and 0 grade rows
3. ✓ Clean refresh: MAC 5, ENC 41, AMH 19, PSY 10, BSC 2 = **77 Tampa / 0 other-campus**
4. ✓ Rankings API and coverage endpoint reported the same per-course counts and total of 77
5. ✓ Preserved all 237 grade rows, all 263 historical sections and every pre-cleanup Tampa section
6. ✓ Post-refresh quality: 0 errors, 31 warnings, 31 info; post-cleanup dry run: 0 eligible rows

The current total is 77 because AMH 2020 gained two legitimate Tampa sections after the dated
2026-09-09 validation. The historical 75-section result remains valid for that earlier pass.

**Requirements**: REQ-DATA-02

---

## Phase 3: Historical Grade Coverage for AMH / PSY / BSC

**Goal**: The three newly validated courses have real historical grade data instead of a global
fallback.

**Depends on**: Phase 2

**Status**: Next after PR #18 merges and approved exports are supplied

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
3. **Search performance measurement and improvement at the widened coverage** — an initial local
   request returning all 77 corrected sections took about 10.1 seconds on 2026-09-14
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
| 2 — Tampa-only data correction | ✓ Complete on PR #18; merge pending | 100% |
| 3 — Historical grade coverage | ◆ Next after merge/exports | 0% |
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
| REQ-DATA-02 | 2 | ✓ Complete on PR #18; merge pending |
| REQ-GRADES-01 | 3 | ○ Next |
| REQ-PERF-01 | 4 | ◐ Initial local measurement recorded; hosted work remains |
| REQ-OPS-01 | 4 | ○ Later |

Backlog requirements (`REQ-ALERT-*`, `REQ-RMP-01`) are deliberately unmapped — they belong to
candidate later phases.

---
*Last updated: 2026-09-14 — Phase 2 removed 47 contaminated sections and verified 77 current
Tampa sections across storage and APIs; PR #18 awaits merge.*
