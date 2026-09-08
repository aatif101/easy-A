---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 2
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-08)

**Core value:** Every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking result.

**Current baseline:** `origin/main` = `180afe0b8faf72a70c297e4c3d4af40c8c3b15a0`

**Current focus:** Phase 1 — Real-data expansion validation

## Current Position

Sprint 5: **COMPLETE** — merged to main via PR #14 and PR #15. Do not re-plan or re-implement it.

Phase: 1 of 2 (Real-Data Expansion Validation)
Plan: 0 of TBD
Status: Ready — validation pass not yet run
Last activity: 2026-09-08 — Merged current main into the planning branch, verified each Sprint 5
deliverable present in code, re-measured the test baseline, and updated planning docs to match.
No application code changed by this planning work.

Progress: [░░░░░░░░░░] 0%

## Next Action

**Run the real-data expansion validation pass for the configured Spring 2027 targets, record
actual coverage / history / quality results, then plan hosted beta work.**

Configured targets (`config/course_targets.toml`, catalog edition 2026-2027):

| Subject | Number | Status |
|---------|--------|--------|
| MAC | 1105 | Previously validated |
| ENC | 1101 | Previously validated |
| AMH | 2020 | **Configured, not validated** |
| PSY | 2012 | **Configured, not validated** |
| BSC | 1005 | **Configured, not validated** |

The pass must determine, from real ingestion: actual section counts, catalog availability, GenEd
attributes, seat freshness behavior, named-instructor coverage, historical grade coverage,
quality-pipeline findings, and search performance implications at the widened coverage.

Record the run date and scope with every figure. Report targets that fail to resolve rather than
omitting them. **Configuration is not coverage — do not claim a target is covered until real
ingestion validates it.**

Requests to USF public sources stay narrow and bounded. Never commit raw grade export files.

## Accumulated Context

### Baseline

Easy-A is a working application. FastAPI backend, React/TypeScript frontend, PostgreSQL, real
Spring 2027 schedule ingestion, real historical grade imports, configurable course coverage, seat
freshness classification, GenEd metadata, and a data-quality pipeline.

**Measured test baseline (2026-09-08, merged branch at `180afe0`):**

| Suite | Result |
|-------|--------|
| Python `uv run pytest -q` | 191 passed, 1 skipped |
| Frontend `npm test` (in `web/`) | 78 passed |

The single skip is the PostgreSQL integration test, which skips when `EASY_A_TEST_POSTGRES_URL`
is unset. PR #14 reported 192 passed with PostgreSQL configured. **Most of the suite still runs on
SQLite** — do not describe it as a PostgreSQL suite.

### Sprint 5 — what landed

**PR #14:** configurable course targets (`src/easy_a/refresh/targets.py`, `target_cli.py`,
`config/course_targets.toml`), one-pass coverage refresh (`src/easy_a/refresh/coverage.py`),
seat-only refresh (`scripts/refresh_seats.py`), seat freshness classification
(`src/easy_a/schedule/freshness.py`), freshness API fields, coverage metadata endpoint
(`GET /api/v1/metadata/coverage`), PostgreSQL integration coverage
(`tests/refresh/test_postgres_coverage.py`).

**PR #15:** explicit mock opt-in via `VITE_USE_MOCK_DATA` with no silent production fixture
fallback (`web/src/api/rankings.ts`), scalable broader-course UX, server-backed pagination
hardening, seat freshness UI (`web/src/components/SeatBadge.tsx`), coverage UX
(`web/src/components/CoverageNotice.tsx`), relative seat observation timestamps
(`web/src/utils/time.ts`).

### Decisions

Constraints live in the PROJECT.md `<decisions>` block (`D-01`..`D-19`). Load-bearing now:

- D-02: the existing scoring model is preserved — **no rewrite without explicit approval**
- D-06: no fabricated data, including no invented coverage figures
- D-09: bounded, narrow requests to USF public sources; no broad crawling
- D-10: verify current `origin/main` by fetch; do not check out or merge an unverified local `main`
- D-15: current activity is real-data expansion validation
- D-16 / D-17 / D-18: alerts, RMP and broader launch coverage stay deferred
- D-19: never commit raw grade export files

### Fixed in Sprint 5 — do not re-plan

- Frontend silently serving fixtures when `VITE_API_BASE_URL` was unset
- Missing seat freshness contract
- No PostgreSQL-specific integration coverage (now present, skippable)
- Hard-coded Spring 2027 frontend term preference

### Still open

- **Ranking search cost at broader coverage** — `GET /api/v1/rankings/search` ranks sections
  before slicing pagination. Measure during Phase 1.
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Unresolved; needs a real or sample InfoCenter
  export, owned by whoever holds ODS/registrar access.
- **Broader real-data coverage is not yet validated** — three of five configured targets have
  never been ingested. This is Phase 1.
- **Deployment host and domain** not yet supplied (needed for Phase 2).

### Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links, a scoring methodology rewrite, and campus-wide launch
coverage claims. All remain candidate later phases or optional research unless explicitly
approved later.

## Session Continuity

Last session: 2026-09-08
Stopped at: Planning docs synchronized with merged Sprint 5 code at `180afe0`. No phase planned
under the current roadmap; no application code changed.
Resume file: None
Next action: run the real-data expansion validation pass described above. If you want GSD to
manage it as a planned phase, `/gsd-plan-phase 1` plans Phase 1 (Real-Data Expansion Validation)
— **not** Sprint 5, which is already implemented and merged.
