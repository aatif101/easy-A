---
gsd_state_version: '1.0'
status: active
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 0
  completed_plans: 0
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-15)

**Core value:** Every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking result.

**Current baseline:** `origin/main` = `9d686c01bca44b3bbf79a2277a4a1b2618df00a9`
(verified by fetch on 2026-09-15)

## Current Position

| | |
|---|---|
| Sprint 5 | ✓ **Complete** — merged via PR #14, PR #15; Tampa scope fix in PR #16 |
| Phase 1 — Real-data expansion validation | ✓ **Complete** — executed; results below |
| Phase 2 — Tampa-only data correction | ✓ **Complete and merged via PR #18; PR #17 superseded** |
| Phase 3 — Historical grade coverage (AMH/PSY/BSC) | ◆ Current — preparation; approved exports pending, starting with AMH 2020 |
| Phase 4 — Hosted beta | ○ After that |

Phase: 3 of 4 (Historical Grade Coverage; preparation)
Plan: 0 of TBD
Status: Phase 2 merged via PR #18; Phase 3 preparation and approved grade exports are next

Progress: [█████░░░░░] 50%

Last activity: 2026-09-15 — Phase 2 merged through PR #18 at
`9d686c01bca44b3bbf79a2277a4a1b2618df00a9`; PR #17 was closed as superseded.

## Current gate

**Phase 2 is present on `main` through PR #18; PR #17 is closed as superseded.**

The live correction and its verification are complete. PR #18 merged the bounded cleanup
tooling, audit output, preservation checks, and an `unsupported_campus_section` quality error.
The next gate is Phase 3 preparation and obtaining approved historical grade exports, starting
with AMH 2020.
Do not repeat the original destructive command with `--expect-removed 47`: the post-cleanup dry
run reports zero eligible rows.

## Next Action

1. Prepare Phase 3.
2. Obtain approved historical grade exports for AMH 2020, then PSY 2012, then BSC 1005.
3. Plan and execute Phase 3 without committing raw export files.

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

### Fixed — do not re-plan

Silent frontend fixture fallback; missing seat freshness contract; absent PostgreSQL integration
coverage; hard-coded Spring 2027 term preference (all Sprint 5). Campus-scope bug in configured
refresh (PR #16); stored cross-campus contamination (Phase 2 / PR #18).

### Still open

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

Last session: 2026-09-15
Stopped at: Phase 2 merged through PR #18 at
`9d686c01bca44b3bbf79a2277a4a1b2618df00a9`; PR #17 closed as superseded. The live database
contains 77 configured Tampa sections, zero other-campus target sections, and 237 grade rows.
Resume file: None
Next action: prepare Phase 3 and obtain the approved AMH 2020 historical grade export.
