# Roadmap: Easy-A

## Overview

Easy-A is a working course-intelligence application for USF Tampa students: FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, configurable course coverage, and seat freshness classification.

This roadmap describes the sequence forward from that baseline. It is **not** a greenfield MVP
plan, and it does not restart the project.

**Live facts (baseline SHA, section/grade counts, next action) live in `.planning/STATE.md`.**

**Current milestone: MVP 1** — all ~3,782 USF Tampa Spring 2027 sections searchable on hosted
Supabase, with historical grade distributions imported and easiness computed from them, at search
p95 < ~1.5s. Sprint 5, real-data validation and the Tampa-only correction (PR #18) are merged;
Phase 3.5 is delivered. See **MVP 1** below.

### How to read this roadmap

| Section | Meaning |
|---------|---------|
| Sprint 5 / Phase 1 / Phase 2 | **Complete & merged.** Dated results in `.planning/ARCHIVE.md`. |
| Phase 3 — Historical grade coverage | Folded into **MVP 1** (generalized beyond AMH/PSY/BSC). |
| Phase 3.5 — Ranking search performance | **Delivered, not closed** — perf goal folded into MVP1-P4. |
| **MVP 1 (MVP1-P1..P5)** | **Active milestone.** Full Tampa coverage + grades + performance. |
| Phase 4 — Hosted beta | After MVP 1. |
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

**Status**: Complete — executed and verified 2026-09-14, merged via PR #18.

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

**Status**: Folded into **MVP 1** (generalized beyond AMH/PSY/BSC to all ingested Tampa courses).
Needs the grade→course attribution fix (MVP1-P1) and approved grade exports (MVP1-P2, Codex-owned).

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

**Plans:** 5/5 plans executed (tracer-first; Wave 1 → Wave 2 ×3 parallel → Wave 3)

Plans:

- [x] 03.5-01-PLAN.md — Tracer: `section_rankings` table + batch-by-course population + hydrate, proven by byte-for-byte parity (D-01/D-02/D-04/D-07/D-08)
- [x] 03.5-02-PLAN.md — Rewrite `/rankings/search` to SQL filter/sort/paginate + live seat join; remove the N+1 (D-03/D-06/D-08)
- [x] 03.5-03-PLAN.md — Refresh-pipeline wiring (atomic cache population) + CHM 2045/2045L suffix pre-filter (D-09/D-10)
- [x] 03.5-04-PLAN.md — Extend cleanup cascade + identity verification to `section_rankings` (no orphans)
- [x] 03.5-05-PLAN.md — Benchmark harness + real Supabase before/after p95 measurement + full Postgres-path suite (criteria 2/5)

**Status: NOT closed — delivered with the performance goal deferred.** All 5 plans are built and
committed; the circular-import regression they surfaced is fixed. Success criteria 3 (quality 0
errors) and 5 (full Postgres-path suite green, 256 passed) are met, and the scoring model + API
contract are unchanged. **Success criterion 2 (p95 < ~1.5s at full ~3,782-section scale) is NOT
met — measured ~2.40s** (recorded in `.planning/WINDOWS.md`, detail in `03.5-PERF-REPORT.md`).
Because MVP 1 targets hosted Supabase at full ~3,782-section scale, this goal is **folded into
MVP 1 as blocking phase MVP1-P4** (see below) — not a deferred backlog item. The residual work is
additive index/query tuning, not a rewrite. Phase 3.5 therefore stays open (goal partially met)
rather than being marked complete.

---

## MVP 1 — milestone overview

**Goal**: all ~3,782 USF Tampa Spring 2027 (`202701`) sections ingested and **searchable against
hosted Supabase**, each with **historical grade distributions imported** and **easiness computed
from that real data** (not the `effective_n = 0` fallback), with search **p95 < ~1.5s**. RMP
instructor links = MVP 2. "Every section" is judged by PROJECT.md D-21: source range exhausted,
remaining source-limited sections honestly labeled as fallbacks.

**Where we start**: 132 sections / 10 courses / **0 grade rows** on Supabase; the full Tampa
universe is ~1,402 courses / ~3,782 sections (see `.planning/STATE.md`).

**Hard constraints** (unchanged): scoring model frozen (D-02); no fabricated data / honest
`effective_n` (D-06/D-07/D-20); API response contract identical; term/CRN/source dedup and never
commit raw grade files (D-04/D-19); bounded USF requests (D-08/D-09).

MVP 1 is delivered as **Phases 4–8** below (sequenced: P4 first, P5 parallel-but-depends-on-P4,
P6 large & independent, P7 after P6). Phase 9 (hosted beta) follows MVP 1.

---

## Phase 4: MVP1-P1 — Grade→course attribution fix

**Goal**: imported historical grade distributions attach to current-term sections so easiness is
computed from real data (`effective_n > 0`), not the global fallback.

**Depends on**: Phase 3.5 (delivered). This is the MVP-1 engineering crux — do it first.

**Scope**

1. `GradeDistribution.course_id` is hard-coded `None` at ingest (`src/easy_a/grades/ingest.py:140`)
   and the parsed subject/number are discarded, so imported historical grades never attach to
   current-term sections. Backfill `course_id` from the parsed subject+number so a 202701 section's
   `course_id` matches the grade row (`src/easy_a/analytics/queries.py:294-300`).

2. Decide blank-cell suppression semantics (`src/easy_a/grades/parser.py:250` turns blanks into `0`).
3. Prove easiness-from-grades end-to-end on a sample export.

**Success criteria**

1. A section whose course has imported grade history reports `effective_n > 0` and a grade-derived
   easiness score; sections without history stay an honest `effective_n = 0` fallback.

2. Term/CRN/source dedup preserved; no raw export files committed; scoring model unchanged.

**Requirements**: REQ-GRADES-01

**Plans:** 2/2 plans complete

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Tracer: canonical course attribution from generated historical XLSX through 202701 cache-backed search, plus atomic backfill/dedup coverage

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Fail-closed blank-count semantics and explicit null-attribution quality findings

---

## Phase 5: MVP1-P2 — Grade data sourcing + import to Supabase

**Goal**: historical grade distributions for the ingested Tampa courses are present in Supabase.

**Depends on**: Phase 4 (grades loaded before the attribution fix will not count).

**Scope**

1. Source USF InfoCenter grade-distribution XLSX for the Tampa courses (**Codex-owned** task).
2. Load into Supabase via the existing import tooling (`grades/cli.py`, `--grade-file`).
3. Validate per-course analytics against the source aggregate; record courses still lacking data
   as lacking it, never quietly omitted.

**Success criteria**

1. Imported courses report real observed outcomes with non-zero effective N, validated per course.
2. Honest `effective_n`; no fabricated data; **no raw export files committed**.

**Requirements**: REQ-GRADES-01

**Status:** Complete — all 10 currently ingested courses are course-backed and operator-verified.

**Plans:** 2/2 plans executed (tracer-first; Wave 1 → Wave 2)

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Tracer: source + scope + import ONE course, rebuild the 202701 cache, validate raw-count vs source against hosted Supabase; author `docs/runbooks/grade-import.md` + `05-IMPORT-RECORD.md`

**Wave 2** *(blocked on Wave 1)*

- [x] 05-02-PLAN.md — Imported the remaining nine courses; completed and operator-approved the honest all-10-course coverage record; no real blank cells, so OQ-04 remains open and no conditional fixture was created

---

## Phase 6: MVP1-P3 — All-Tampa section ingestion (10 → ~3,782)

**Goal**: all ~3,782 USF Tampa Spring 2027 sections are ingested and searchable.

**Depends on**: independent of Phases 4/5; large lift.

**Scope**

1. No "all Tampa" path exists — ingestion is target-driven (`config/course_targets.toml` →
   `src/easy_a/refresh/coverage.py:74`). Catalog-ingest all ~1,402 Tampa courses (course rows must
   pre-exist for `resolve_course_id`, `src/easy_a/common/lookups.py:35`).

2. Add a subject-level Tampa ingest path (with the campus guard that today lives only in
   `coverage.py:141-155`) or a generated full target list.

3. Fix the exact-course suffix guard (CHM 2045 vs 2045L, `coverage.py:185`; 33 base courses
   affected) without weakening it. Reconcile config (5 courses) vs stored data (10).

**Success criteria**

1. Full Tampa Spring 2027 set ingested; stored/API/coverage counts agree; 0 non-Tampa rows.
2. Suffix-variant courses ingest correctly; quality 0 errors.

**Requirements**: REQ-COVERAGE-03

**Plans:** 3/3 plans executed (tracer-first; Wave 1 → Wave 2 → Wave 3)

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Tracer: target-list generator + committed full ~1,402-entry `config/course_targets.toml`, one-subject (CHM) end-to-end ingest with campus + suffix guards, quality 0 errors, honest coverage; generalized suffix-guard regression test

**Wave 2** *(blocked on Wave 1)*

- [x] 06-02-PLAN.md — Resumable, paced per-subject orchestrator + runbook, blocking-human go-live checkpoint, full-scale all-Tampa ingestion (~1,402 courses / ~3,782 sections) into hosted Supabase

**Wave 3** *(blocked on Wave 2)*

- [x] 06-03-PLAN.md — Scale validation: all 33 suffix-variant base courses exact-only, 0 non-Tampa, quality 0 errors, stored/coverage/API counts agree, config vs stored reconciled, honest-coverage (D-20) at scale

---

## Phase 7: MVP1-P4 — Full-scale cache build + search performance (p95 < ~1.5s)

**Goal**: rankings search p95 < ~1.5s against Supabase at full ~3,782-section scale. Folds in
Phase 3.5's open performance goal.

**Depends on**: Phase 6 (need full scale to measure and tune).

**Scope**

1. Populate `section_rankings` for all ~3,782 sections (`src/easy_a/rankings/cache.py:73` supports
   whole-term); address cache build-time latency at scale.

2. `EXPLAIN ANALYZE` the serve query; add index(es) on the `section_rankings` sort/filter columns;
   re-measure until p95 < ~1.5s on Supabase. No scoring or API-contract change.

3. Fix the benchmark env-label bug (label/pooler from the resolved engine URL, not only `--url`).

**Success criteria**

1. Measured search p95 < ~1.5s on Supabase at full scale, with dataset size + environment stated.
2. Cached rankings byte-for-byte identical to on-demand results (parity test still passes).

**Requirements**: REQ-PERF-01

**Plans:** 3/3 complete (2026-09-23). Loopback HTTP search p95 **309.91 ms** at 3,783 sections on hosted
Supabase; whole-term cache rebuild 4.77 s; quality pass 2.45 s. Evidence: `07-PERF-REPORT.md`.
**Wave 1**

- [x] 07-01-PLAN.md — Tracer: read-only live HTTP benchmark, resolved-engine label, and full-scale baseline

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 07-02-PLAN.md — Batch historical evidence for cache and quality rebuilds with exact score/fallback parity

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 07-03-PLAN.md — Tune measured search bottlenecks and indexes; verify hosted HTTP p95 < 1.5s

---

## Phase 8: MVP1-P5 — End-to-end MVP-1 verification

**Goal**: MVP 1 is demonstrably met end to end.

**Depends on**: Phases 4–7.

**Success criteria**

1. All ~3,782 Tampa sections searchable; easiness grade-derived wherever data exists.
2. Quality 0 errors; p95 < ~1.5s on Supabase; honest data semantics; API contract + scoring
   model unchanged.

**Requirements**: REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01

**Grade-coverage gate**: PROJECT.md D-21 — every section is evidence-backed or a listed
source-limited exception; fallbacks never count as course history; no grade sourcing in this phase.

**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Tracer: read-only full-page API identity scan (every stored term+CRN exactly once)
- [x] 08-02-PLAN.md — D-21 grade inventory with per-section exception list; validator accepts evidence-proven non-letter-grade exceptions
- [x] 08-03-PLAN.md — Presentation-only evidence wording for course/effective_n=0, global and subject rows (desktop, mobile, details)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-04-PLAN.md — Dated hosted verification report, committed D-21 exception list, Phase 8 and MVP-1 verdicts

**Gap closure** *(from 08-VERIFICATION.md / 08-REVIEW.md CR-01)*

- [x] 08-05-PLAN.md — Every reported D-21 integrity counter gates the verdict (CR-01), stale_cache from scoring-window rows (WR-01), suffix guard kept fail-closed and documented (WR-02), read-only live re-verification recorded in the report

---

## Phase 9: Hosted Beta — Deployment, CI, Observability

**Goal**: The corrected application runs as a hosted beta with enough automation and measurement
to keep it running.

**Depends on**: MVP 1

**Status**: After MVP 1

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

### Phase 999.6 — promoted to MVP1-P4 (no longer backlog)

Full-scale ranking search tuning (p95 < ~1.5s on Supabase, plus the benchmark env-label fix) was
briefly a deferred backlog item. Because MVP 1 targets hosted Supabase at full ~3,782-section
scale, it is now **blocking phase MVP1-P4** in the MVP 1 milestone above.

### Phase 999.5: Methodology review (optional research item)

The current scoring model is the baseline and stays. An evidence-backed review of how it behaves
with little or no grade history is an **optional research item, not active implementation scope**.
Any change would require documented evidence plus matching methodology and test updates. No
rewrite is planned or approved.

---

## Progress

| Phase | Status | Progress |
|-------|--------|----------|
| Sprint 5 / Phase 1 / Phase 2 | ✓ Complete & merged | 100% |
| 3 — Historical grades | ↳ Folded into MVP 1 (Phases 4–5) | — |
| 3.5 — Ranking search performance | ✓ Perf goal met via Phase 7 | — |
| 4 — MVP1-P1 grade→course attribution | Complete    | 100% |
| 5 — MVP1-P2 grade sourcing + import | Complete | 100% |
| 6 — MVP1-P3 all-Tampa ingestion | ✓ Complete | 100% |
| 7 — MVP1-P4 full-scale perf (p95 < 1.5s) | ✓ Complete | 100% |
| 8 — MVP1-P5 MVP-1 verification | Complete    | 100% |
| 9 — Hosted beta | ○ After MVP 1 | 0% |

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
| REQ-DATA-02 | 2 | ✓ Complete (PR #18 merged) |
| REQ-COVERAGE-03 | 6, 8 | ✓ Complete — live 3,783/3,783/3,783 identity reconciliation, 0 missing/extra/duplicate/non-Tampa (2026-09-24, Phase 8 verification) |
| REQ-GRADES-01 | 4–5, 8 | ✓ Complete under D-21 — 3,122 evidence-backed sections, 661 listed source-limited exceptions, honest fallback labeling verified end to end (2026-09-24, Phase 8 verification) |
| REQ-PERF-01 | 7, 8 | ✓ Complete — loopback HTTP p95 277.25 ms at 3,783 sections on hosted Supabase, re-confirmed in Phase 8 end-to-end verification (2026-09-24) |
| REQ-OPS-01 | 9 | ○ After MVP 1 |

Backlog requirements (`REQ-ALERT-*`, `REQ-RMP-01`) are deliberately unmapped — they belong to
candidate later phases.

---
*Last updated: 2026-09-20 — added the MVP-1 milestone (full Tampa coverage + grades + performance)
with phases MVP1-P1..P5; Phase 3.5's perf goal folded into MVP1-P4; dated history moved to
`.planning/ARCHIVE.md`.*
