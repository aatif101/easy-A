---
gsd_state_version: "1.0"
current_phase: "03.5"
current_phase_name: Ranking Search Performance at Full Coverage
status: verifying
stopped_at: Completed 03.5-05-PLAN.md
last_updated: "2026-09-20T23:00:09.830Z"
last_activity: 2026-09-20
last_activity_desc: Phase 03.5 execution started
state_head: 2bb984a6019127ebe67735223f63ce5615231615
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 5
  completed_plans: 5
  percent: 40
---

# Project State

## Current update — 2026-09-20 Tampa coverage pilot

This update supersedes the older **Current Position**, **Current gate**, and **Next Action**
sections below; those sections retain the dated local-database history.

- Fetched `origin/main`: `a70a85346796d886f5f04741b5fd2330b660e2cc`. PR #18 (Tampa guard)
  and PR #19 (Supabase wiring) are merged. Working branch: `dev1/tampa-coverage-pilot`.
- User explicitly authorized Spring 2027 (`202701`) undergraduate Tampa coverage expansion,
  with a stop after pilot verification. Grades, syllabi, scoring, frontend, and deletions are
  excluded. This takes precedence over the earlier deferred coverage-breadth decision.
- Enumerated all 265 public undergraduate catalog prefixes sequentially: **1,402 courses /
  3,782 Tampa sections** across 212 subjects; 53 subjects had no undergraduate Tampa offerings.
  `courses.csv` is Git-ignored. No unresolved schedule searches; non-pilot catalog lookups pending.
- Hosted Supabase started empty. Existing coverage refresh populated **10 courses / 132 Tampa
  sections / 132 seat snapshots**, including five new targets contributing 55 sections:
  ACG 2021 (17), ACG 2071 (15), ANT 2000 (5), ECO 2013 (3), MAC 2311 (15).
- Independent quality CLI: **0 errors, 132 low-confidence warnings, 132 no-history info**.
  Coverage and rankings APIs returned 200; both matched SQL at 132 sections and per course.
  Coverage took 1.88 seconds; rankings took **600.61 seconds** against Supabase. Seat freshness
  during that request: 97 fresh / 35 aging; all 132 have complete seat fields and snapshots.
  Grades and syllabi remain **0 before / 0 after**, with unchanged full-row hashes.
- First pilot attempt rolled back completely: USF's CHM 2045 query also returns CHM 2045L,
  which the exact-course guard correctly rejects. ACG 2071 replaced CHM 2045 in the pilot.
  The full CSV has 33 base courses with suffix variants; their query behavior needs attention
  before scaling. Do not weaken the guard or blindly run the full list.
- Audit: `phase1_report.md`; ignored evidence: `data/coverage-pilot-2026-09-20/`.
- **Stopped at the user's pilot checkpoint.** Await confirmation before scaling. Resolve the
  confirmed suffix-query incompatibility using existing tooling and account for rankings
  latency before a full run. Full-scale ingestion/verification remain pending; no grade import.

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-14)

**Core value:** Every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking result.

**Current baseline:** `origin/main` = `d72f8f3d77a11f301f2b74f56088a217226feefa`
(verified by fetch on 2026-09-14)

## Current Position

| | |
|---|---|
| Sprint 5 | ✓ **Complete** — merged via PR #14, PR #15; Tampa scope fix in PR #16 |
| Phase 1 — Real-data expansion validation | ✓ **Complete** — executed; results below |
| Phase 2 — Tampa-only data correction | ✓ **Complete and verified on PR #18; merge pending** |
| Phase 3 — Historical grade coverage (AMH/PSY/BSC) | ◆ Next after merge and approved exports |
| Phase 4 — Hosted beta | ○ After that |

Phase: 03.5 (Ranking Search Performance at Full Coverage) — EXECUTING
Plan: 5 of 5
Status: Phase complete — ready for verification

Progress: [████░░░░░░] 40%

Last activity: 2026-09-20 — Phase 03.5 execution started
the five configured targets, verified stored/API/coverage agreement at 77 Tampa sections, and
added an independent campus-contamination quality guard.

## Current gate

**PR #18 must be reviewed and merged before Phase 2 is present on `main`.**

The live correction and its verification are complete. PR #18 contains the bounded cleanup
tooling, audit output, preservation checks, and an `unsupported_campus_section` quality error.
PR #17 overlaps with that work; consolidate on PR #18 and close the duplicate only after review.
Do not repeat the original destructive command with `--expect-removed 47`: the post-cleanup dry
run reports zero eligible rows.

## Next Action

1. Review and merge PR #18 into the verified current `origin/main`.
2. Close overlapping PR #17 after confirming PR #18 contains the desired quality guard.
3. Obtain approved historical grade exports for AMH 2020, then PSY 2012, then BSC 1005.
4. Plan and execute Phase 3 without committing raw export files.

The approved grade exports are the next external dependency. Until supplied, the three courses
remain global-prior fallbacks with `effective_n = 0`.

## Accumulated Context

### Phase 2 — Tampa-only data correction results (executed 2026-09-14)

The dry run identified exactly 47 eligible sections and zero ambiguous-campus rows. Selection
was limited to Spring 2027 (`202701`) sections belonging to configured target courses whose
nonblank campus was not Tampa after stripping and case-folding. Null/blank campus values,
unrelated terms and non-target courses were excluded.

| Result | Measured value |
|--------|----------------|
| Sections removed | 47 |
| Linked seat snapshots removed | 47 |
| Linked instructor observations removed | 47 |
| Linked syllabi removed | 0 |
| Grade rows removed | 0 |
| Tampa sections removed | 0 |
| Historical sections removed | 0 |
| Grade rows after cleanup | 237 |
| Historical sections after cleanup | 263 |

After the required course-coverage and seat refreshes, the database, rankings API and
`GET /api/v1/metadata/coverage` all agreed:

| Course | Current Tampa sections | Other-campus sections |
|--------|------------------------|-----------------------|
| MAC 1105 | 5 | 0 |
| ENC 1101 | 41 | 0 |
| AMH 2020 | 19 | 0 |
| PSY 2012 | 10 | 0 |
| BSC 1005 | 2 | 0 |
| **Current total** | **77** | **0** |

AMH 2020 gained two legitimate Tampa sections since the 2026-09-09 validation, so the current
source-backed total is 77 rather than the historical 75. Post-refresh quality reported **0
errors, 31 warnings and 31 info** for Spring 2027. A search request returning all 77 sections
took about **10.1 seconds** locally; this is an initial REQ-PERF-01 measurement and remains a
hosted-beta performance concern.

### Phase 1 — real-data expansion validation results (executed)

All five configured Spring 2027 (`202701`) targets were verified present in the catalog.

| Course | Catalog | Verified Tampa sections |
|--------|---------|-------------------------|
| MAC 1105 | present | 5 |
| ENC 1101 | present | 41 |
| AMH 2020 | present | 17 |
| PSY 2012 | present | 10 |
| BSC 1005 | present | 2 |
| **Verified Tampa total** | | **75** |

These 75 remain the dated 2026-09-09 validation result. The later clean refresh found 77 because
AMH 2020 increased from 17 to 19; see the Phase 2 result above.

**Seat refresh during the Tampa validation pass:** appended 75 snapshots; preserved previous
snapshots; preserved section identity; left all 237 grade rows unchanged; syllabi remained empty;
all observed Tampa seats were fresh immediately after refresh.

**Frontend / API verification:** required endpoints returned 200; desktop and mobile search
worked; server pagination worked; freshness UX worked; GenEd rendering worked; details worked;
no browser console errors.

**Not sufficiently measured:** search performance at the widened coverage. That concern moved to
hosted-beta performance work (REQ-PERF-01) rather than being marked complete here.

### Historical analytics — real state

| Course | Historical grade data | Analytics |
|--------|----------------------|-----------|
| MAC 1105 | Real imported data | High-confidence course-level analytics |
| ENC 1101 | Real imported data | High-confidence course-level analytics |
| AMH 2020 | **None imported** | Global fallback, `effective_n = 0` |
| PSY 2012 | **None imported** | Global fallback, `effective_n = 0` |
| BSC 1005 | **None imported** | Global fallback, `effective_n = 0` |

**Do not describe the AMH / PSY / BSC fallback scores as evidence-backed course history.** They
are global-prior fallbacks with zero observed outcomes for the course.

Historical grade import priority: **AMH 2020 → PSY 2012 → BSC 1005**.

### Data quality — validation run

| Term | Errors | Warnings | Info |
|------|--------|----------|------|
| 202408 | 0 | 103 | 103 |
| 202501 | 0 | 6 | 0 |
| 202508 | 0 | 11 | 0 |
| 202701 | 0 | 49 | 49 |

Zero errors across all four terms. Historical generic quality reports were **not** polluted by
Sprint 5 target/freshness checks.

### Test baseline

Measured 2026-09-09 on this branch (merged with `origin/main` = `62fb2f1`):

| Condition | Result |
|-----------|--------|
| `uv run pytest -q`, no `EASY_A_TEST_POSTGRES_URL` | **192 passed, 1 skipped** (193 collected) |
| Backend with PostgreSQL configured | **193 passed** (measured on the validation branch) |
| Frontend `npm test` in `web/` | **78 passed** |
| Quality gates | ruff, mypy, ESLint, typecheck, build — all passing |

The single skip is the PostgreSQL integration test. **A default run does not use PostgreSQL** —
most of the suite runs on SQLite, and the PostgreSQL integration test skips unless
`EASY_A_TEST_POSTGRES_URL` is set. Both facts are true; do not state only one.

Phase 2 branch verification measured 2026-09-14:

| Condition | Result |
|-----------|--------|
| Backend without PostgreSQL configured | **216 passed, 2 skipped** |
| Backend with PostgreSQL configured | **218 passed** |
| Quality gates | ruff and strict mypy passed |

The frontend was not changed or re-measured in Phase 2; its latest recorded baseline remains the
78-test result above.

### Sprint 5 — what landed

**PR #14:** configurable course targets (`src/easy_a/refresh/targets.py`, `target_cli.py`,
`config/course_targets.toml`), one-pass coverage refresh (`src/easy_a/refresh/coverage.py`),
seat-only refresh (`scripts/refresh_seats.py`), seat freshness classification
(`src/easy_a/schedule/freshness.py`), freshness API fields, coverage metadata endpoint
(`GET /api/v1/metadata/coverage`), PostgreSQL integration coverage.

**PR #15:** explicit mock opt-in via `VITE_USE_MOCK_DATA` with no silent production fixture
fallback, scalable broader-course UX, server-backed pagination hardening, seat freshness UI,
coverage UX, relative seat observation timestamps.

**PR #16:** coverage refresh pins `campus="T"` and rejects any returned row whose campus is not
Tampa, before ingestion (`src/easy_a/refresh/coverage.py`). Fixes the cause of the contamination;
does not remove the already-inserted rows.

### Decisions

Constraints live in the PROJECT.md `<decisions>` block (`D-01`..`D-19`). Load-bearing now:

- D-02: the existing scoring model is preserved — **no rewrite without explicit approval**
- D-06: no fabricated data, including no invented coverage figures
- D-09: bounded, narrow requests to USF public sources; no broad crawling
- D-10: verify current `origin/main` by fetch; do not check out or merge an unverified local `main`
- D-16 / D-17 / D-18: alerts, RMP and broader launch coverage stay deferred
- D-19: never commit raw grade export files
- [Phase 03.5]: Cache every non-seat ranking field and hydrate live seat state at read time.
- [Phase 03.5]: Batch historical analytics once per course while reusing ranking service helpers.
- [Phase 03.5]: Use one portable window-function latest-seat join for SQLite and PostgreSQL.
- [Phase 03.5]: Keep ranking search cache-only and hydrate explicitly joined seat state without per-row queries.
- [Phase 03.5]: [Phase 03.5]: Refresh configured target cache rows inside the caller-owned ingest transaction.
- [Phase 03.5]: [Phase 03.5]: Rebuild whole-term ranking cache as a wrapped refresh_data stage after syllabi.
- [Phase 03.5]: [Phase 03.5]: Filter non-exact schedule rows from the ingestion payload before strict Tampa and CRN validation.
- [Phase 03.5]: Extended cleanup.py's explicit-delete + identity-verification cascade to cover section_rankings as a fourth dependent table, closing the orphaned/stale-cache regression a future non-Tampa cleanup would reintroduce

### Fixed — do not re-plan

Silent frontend fixture fallback; missing seat freshness contract; absent PostgreSQL integration
coverage; hard-coded Spring 2027 term preference (all Sprint 5). Campus-scope bug in configured
refresh (PR #16); stored cross-campus contamination (Phase 2 / PR #18).

### Still open

- **PR #18 pending review/merge** — Phase 2 is verified on its branch but not yet on `main`
- **Search performance at widened coverage** — initial local measurement was about 10.1 seconds
  for 77 sections; hosted measurement and improvement remain REQ-PERF-01
- **No historical grades for AMH / PSY / BSC** — global fallback, `effective_n = 0`
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Needs a real or sample InfoCenter export.
- **Deployment host and domain** not yet supplied

### Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links, a scoring methodology rewrite, and campus-wide launch
coverage claims. All remain candidate later phases or optional research unless explicitly
approved later.

## Session Continuity

Last session: 2026-09-20T23:00:09.805Z
Stopped at: Completed 03.5-05-PLAN.md
contains 77 configured Tampa sections, zero other-campus target sections, and 237 grade rows.
Resume file: None
Next action: review and merge PR #18, then obtain the approved AMH 2020 grade export for Phase 3.

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 03.5 P01 | 15min | 2 tasks | 7 files |
| Phase 03.5 P02 | 7min | 2 tasks | 5 files |
| Phase 03.5 P03 | 8min | 3 tasks | 8 files |
| Phase 03.5 P04 | 20min | 2 tasks | 2 files |
