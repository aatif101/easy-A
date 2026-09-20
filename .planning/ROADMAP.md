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

## Phase 3.5: Ranking Search Performance at Full Coverage

**Goal**: Ranking search is fast enough to serve all ~3,782 Spring 2027 Tampa sections over the
hosted Supabase database — search-page latency well under ~1.5s p95 — with the easiness scoring
model and the API response contract both unchanged.

**Depends on**: Phase 2 (independent of Phase 3 grade imports; unblocked)

**Status**: Next — critical. Carved out of Phase 4 because REQ-PERF-01 is now a blocker, not a
deferred concern.

**Why it exists**: after the move to hosted Supabase and widened coverage, a 132-section pilot
measured ~600s for a single rankings search. Root cause (confirmed in
`src/easy_a/api/routes/rankings.py`, `_rank_candidate_sections`): the endpoint ranks the *whole*
term on every request — selecting every candidate section, then looping CRN-by-CRN through
`rank_section()`, which fires several per-section queries (course, instructor, seats, attributes,
analytics, signals) — and only sorts/paginates afterward. This N+1 was invisible on sub-ms local
Postgres and explodes over remote Supabase (a network round-trip per query).

**Scope**

1. Precompute rankings into a derived/cached table (e.g. `section_rankings`), refreshed as part of
   / right after the refresh pipeline. Alembic migration chained after
   `0002_create_section_syllabus_tables`.
2. Rewrite the search path to read from that table with sort, filter (subject/course/gened/
   delivery/open-seats/min-easiness/confidence) and pagination done in SQL — O(one page), not
   O(whole term). Eliminate the per-section N+1.
3. Keep seat freshness / "latest observed seats" semantics correct: cached ranking vs. live seat
   snapshot relationship decided and documented; stale seats must not corrupt scores.
4. Fix the CHM 2045 vs CHM 2045L (course-number suffix / lab-section) matching in ingest and the
   campus/target guard so full-scale runs stay clean.

**Hard constraints**

- **D-02**: easiness scoring model UNCHANGED. Cached values must be byte-for-byte identical to what
  the current on-demand `rank_section()` produces. No scoring rewrite.
- API response contract identical: `items`/`total`/`limit`/`offset`, and existing sort values
  (`easiness_desc`, `easiness_asc`, `withdrawal_asc`, `seats_desc`, `course`).
- Honest-data semantics preserved: unavailable stays unavailable; provenance / confidence /
  `effective_n` intact; no fabricated values.
- Do not touch grades or syllabi ingestion. No secrets in git.

**Success criteria**

1. Correctness parity: cached-table results match current on-demand rankings exactly (same order,
   scores, fields) for sampled sections and full-course searches — enforced by an automated parity
   test.
2. Performance: rankings search measured against Supabase before/after, at pilot size and against a
   larger seeded set; after ≈ search page < ~1.5s p95, with real numbers, dataset size, environment.
3. Quality unchanged: `check_data_quality.py` still 0 errors; Tampa-only guard clean.
4. Cache freshness: how/when `section_rankings` is refreshed is documented and tested so it cannot
   silently go stale after an ingestion.
5. Full test suite green, including the PostgreSQL integration path.

**Requirements**: REQ-PERF-01

**Plans:** 5 plans (tracer-first; Wave 1 → Wave 2 ×3 parallel → Wave 3)

Plans:
- [ ] 03.5-01-PLAN.md — Tracer: `section_rankings` table + batch-by-course population + hydrate, proven by byte-for-byte parity (D-01/D-02/D-04/D-07/D-08)
- [ ] 03.5-02-PLAN.md — Rewrite `/rankings/search` to SQL filter/sort/paginate + live seat join; remove the N+1 (D-03/D-06/D-08)
- [ ] 03.5-03-PLAN.md — Refresh-pipeline wiring (atomic cache population) + CHM 2045/2045L suffix pre-filter (D-09/D-10)
- [ ] 03.5-04-PLAN.md — Extend cleanup cascade + identity verification to `section_rankings` (no orphans)
- [ ] 03.5-05-PLAN.md — Benchmark harness + real Supabase before/after p95 measurement + full Postgres-path suite (criteria 2/5)

---

## Phase 4: Hosted Beta — Deployment, CI, Observability

**Goal**: The corrected application runs as a hosted beta with enough automation and measurement
to keep it running.

**Depends on**: Phase 2, Phase 3.5 (and Phase 3 for meaningful coverage)

**Status**: Later

**Scope**

1. Deployment — minimal and portable, no provider-specific infrastructure
2. CI for Python and frontend checks (net-new; there is no `.github/` directory today)
3. Observability — refresh success/failure, search latency
4. Operator runbook — refreshing data, recovering from a failed refresh

**Success criteria**

1. The hosted beta is reachable and serves real data
2. CI runs Python and frontend checks on push
3. An operator can follow the runbook to refresh data and recover from a failed refresh

**Requirements**: REQ-OPS-01

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
