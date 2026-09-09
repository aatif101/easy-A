---
gsd_state_version: '1.0'
status: blocked
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 0
  completed_plans: 0
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-09)

**Core value:** Every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking result.

**Current baseline:** `origin/main` = `62fb2f189c8cac67a1500863f080e0f638469df1`

## Current Position

| | |
|---|---|
| Sprint 5 | ✓ **Complete** — merged via PR #14, PR #15; Tampa scope fix in PR #16 |
| Phase 1 — Real-data expansion validation | ✓ **Complete** — executed; results below |
| Phase 2 — Tampa-only data correction | ◆ **Current — BLOCKED WORK ITEM** |
| Phase 3 — Historical grade coverage (AMH/PSY/BSC) | ○ Next |
| Phase 4 — Hosted beta | ○ After that |

Phase: 2 of 4 (Tampa-Only Data Correction)
Plan: 0 of TBD
Status: Blocked — 47 contaminated rows must be removed before coverage numbers can be trusted

Progress: [██░░░░░░░░] 25%

Last activity: 2026-09-09 — Recorded real-data expansion validation results. No application code
changed by this planning work.

## ⛔ Current blocker

**47 non-Tampa Spring 2027 sections are still stored in the beta database.**

The first expansion pass ran before the campus-scope bug was found: configured refresh queried
all campuses, and 47 non-Tampa Spring 2027 sections were inserted into the existing beta
database. **PR #16 fixed the cause but did not remove the rows** — its merged description states
plainly that it "does not delete the 47 other-campus sections inserted by the initial validation
pass… They remain visible in stored coverage/API counts until a separately reviewed cleanup."

Consequences right now:

- Stored section counts, `/api/v1/rankings/*` counts and `GET /api/v1/metadata/coverage` counts
  **all still include the 47 contaminated rows**. They do not equal the verified Tampa total of 75.
- Any coverage figure read from the running database today is wrong until cleanup completes.

**There is no section-deletion tooling in the repository.** `scripts/` contains ingest, refresh,
analysis and quality commands only, and no code path deletes sections. The cleanup needs a
targeted, reviewable removal step to be written.

## Next Action

**Targeted removal of the 47 preserved non-Tampa Spring 2027 sections, followed by a clean Tampa
refresh and API verification.**

Required outcome, all of which must be recorded with real measured numbers:

1. Exact cleanup result — how many rows were removed, and by what criteria
2. Final Tampa-only stored counts
3. Final API counts
4. Final coverage-endpoint counts
5. Explicit confirmation that **no historical grades and no Tampa sections were deleted** —
   the 237 grade rows and all 75 verified Tampa sections must survive intact

Do not claim cleanup is done until these are measured. Requests to USF public sources stay narrow
and bounded. Never commit raw grade export files.

After cleanup completes, the sequence is: import historical grades for AMH 2020 → PSY 2012 →
BSC 1005, validate the resulting course-level analytics, then prepare the hosted beta.

## Accumulated Context

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

These 75 are the verified Tampa sections. They are **not** the current stored counts — see the
blocker above.

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
refresh (PR #16 — cause fixed; stored rows still need cleanup).

### Still open

- **47 non-Tampa sections stored** — the current blocker, above
- **Search performance at widened coverage** — not sufficiently measured; moved to REQ-PERF-01
- **No historical grades for AMH / PSY / BSC** — global fallback, `effective_n = 0`
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Needs a real or sample InfoCenter export.
- **Deployment host and domain** not yet supplied

### Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links, a scoring methodology rewrite, and campus-wide launch
coverage claims. All remain candidate later phases or optional research unless explicitly
approved later.

## Session Continuity

Last session: 2026-09-09
Stopped at: Real-data expansion validation results recorded in the planning docs. Cleanup of the
47 contaminated rows has **not** been performed. No application code changed.
Resume file: None
Next action: the targeted cleanup described under "Next Action" above.
