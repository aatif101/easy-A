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

**Current baseline:** `origin/main` = `d72f8f3d77a11f301f2b74f56088a217226feefa`
(verified by fetch 2026-09-09; `62fb2f1` is an ancestor and was the pre-onboarding baseline —
every commit since is planning/docs only, no application code)

## Current Position

| | |
|---|---|
| Sprint 5 | ✓ **Complete** — merged via PR #14, PR #15; Tampa scope fix in PR #16 |
| Phase 1 — Real-data expansion validation | ✓ **Complete** — executed; results below |
| Phase 2 — Tampa-only data correction | ◆ **Current — BLOCKED WORK ITEM** |
| Phase 3 — Historical grade coverage (AMH/PSY/BSC) | ○ Next |
| Phase 4 — Hosted beta | ○ After that |

Phase: 2 of 4 (Tampa-Only Data Correction)
Plan: 1 of 3 — removal tooling written and tested; execution and verification outstanding
Status: Blocked — 47 contaminated rows are still stored; the cleanup has not been run

Progress: [██░░░░░░░░] 25%

Last activity: 2026-09-09 — Wrote and tested the section-removal tooling
(`src/easy_a/refresh/cleanup.py`, `cleanup_cli.py`, `scripts/cleanup_non_tampa_sections.py`,
`tests/refresh/test_cleanup.py`). **The tooling has not been run against the beta database** —
no database is reachable from the environment it was written in.

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

**Removal tooling now exists but has not been run.** `scripts/cleanup_non_tampa_sections.py`
performs a targeted, reviewable removal: it reports without writing unless `--apply` is given,
selects sections by term and stored campus, deletes by explicit primary key, and aborts the
transaction if stored grade rows change, if a kept-campus section is lost, if the number removed
differs from the number matched, or if any other-campus section remains. `--expect-removed N`
refuses to proceed unless exactly `N` sections match.

Writing it did not fix anything on its own: **the 47 rows are still in the beta database, and
every count above is still contaminated.** The remaining work is running it, then a clean Tampa
refresh, then recording the verified counts.

## Next Action

**Run the cleanup against the beta database, then a clean Tampa refresh and API verification.**

This needs an operator with access to the beta database — it cannot be done from an environment
with no database. The commands are:

```
uv run python scripts/cleanup_non_tampa_sections.py --term 202701
uv run python scripts/cleanup_non_tampa_sections.py --term 202701 --apply --expect-removed 47 --json
uv run python scripts/refresh_course_coverage.py --term 202701
```

Run the first without `--apply` and review the matched CRNs before applying. If the dry run
matches a number other than 47, stop and investigate rather than lowering the guard. Keep the
`--json` output as the cleanup record.

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

Re-measured 2026-09-09 at `d72f8f3` plus the cleanup tooling:

| Condition | Result |
|-----------|--------|
| `uv run pytest -q`, no `EASY_A_TEST_POSTGRES_URL` | **208 passed, 1 skipped** (209 collected) |
| Backend with PostgreSQL configured | **not re-measured** — no PostgreSQL in this environment |
| Frontend `npm test` in `web/` | **78 passed** |
| Quality gates | `ruff check .`, `mypy src migrations scripts tests` — passing |

The suite was 192 passed / 1 skipped before this work; the 16 added tests cover the cleanup
tooling. The PostgreSQL-configured figure was **193 passed** when last measured on the validation
branch; it should now be 209, but nobody has run it — do not quote 209 as measured.

The single skip is the PostgreSQL integration test. **A default run does not use PostgreSQL** —
most of the suite runs on SQLite, and the PostgreSQL integration test skips unless
`EASY_A_TEST_POSTGRES_URL` is set. Both facts are true; do not state only one.

### Phase 2 — removal tooling (written 2026-09-09, not yet run)

`scripts/cleanup_non_tampa_sections.py` → `src/easy_a/refresh/cleanup.py` and `cleanup_cli.py`,
with 16 tests in `tests/refresh/test_cleanup.py` and a README section.

Behaviour: reports without writing unless `--apply` is given; selects sections in the requested
term whose stored `campus` is not `--keep-campus` (default `Tampa`), compared case-insensitively
after stripping; deletes by explicit primary key, never a broad `WHERE`; `--expect-removed N`
refuses to proceed unless exactly `N` sections match; refuses any matched section carrying a
stored syllabus; `--json` emits a machine-readable record. Deleting a section cascades to that
section's own seat snapshots and instructor observations and cannot touch `grade_distributions`,
which joins to sections by `(term, CRN)` and holds no section foreign key. After applying, it
re-measures and aborts the transaction if stored grade rows changed, if a kept-campus section was
lost, if the number removed differs from the number matched, or if any other-campus section
remains. Both modes print stored counts before and after — sections per campus, seat snapshots,
instructor observations, syllabi, grade rows for the term, grade rows across all terms.

**Rehearsal only, on synthetic data:** against a throwaway SQLite database seeded to the reported
shape (75 Tampa + 47 other-campus sections, 237 grade rows), the dry run matched 47, `--apply
--expect-removed 47` took stored sections 122 → 75 with 0 Tampa sections and 0 grade rows removed,
a second run was a no-op, and `coverage_metadata` then read 5 / 41 / 17 / 10 / 2 = 75. **Those
rows were invented for the rehearsal and are not evidence about the beta database.**

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

- **47 non-Tampa sections stored** — the current blocker, above. Removal tooling now exists;
  running it against the beta database is the outstanding step.
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
Stopped at: Section-removal tooling written, tested (16 tests) and documented in `README.md`.
Rehearsed end to end against a throwaway SQLite database seeded to the reported shape — 122
stored sections went to 75, 47 removed, 0 Tampa sections removed, 237 grade rows preserved, and
`coverage_metadata` then read 5 / 41 / 17 / 10 / 2 = 75. **That rehearsal used synthetic rows and
is not evidence about the beta database.** Cleanup of the 47 contaminated rows has **not** been
performed.
Resume file: None
Next action: run the cleanup against the beta database as described under "Next Action" above.
