# Archive — superseded dated history

Historical, dated results moved out of the live `STATE.md` so the current state stays legible.
**Everything here is history, not current fact.** The current database is a fresh hosted Supabase
instance (see `STATE.md`); the counts below describe the earlier local beta database and earlier
validation passes. Do not cite these as the present state.

---

## Phase 2 — Tampa-only data correction results (executed 2026-09-14, old local beta DB)

Dry run identified exactly 47 eligible sections (Spring 2027 configured-target sections whose
nonblank campus was not Tampa after stripping/case-folding; null/blank campuses, other terms and
non-target courses excluded).

| Result | Measured value |
|--------|----------------|
| Sections removed | 47 |
| Linked seat snapshots removed | 47 |
| Linked instructor observations removed | 47 |
| Linked syllabi / grade rows / Tampa sections / historical sections removed | 0 |
| Grade rows after cleanup | 237 |
| Historical sections after cleanup | 263 |

Post-cleanup counts (DB, rankings API and `GET /api/v1/metadata/coverage` agreed): MAC 1105 = 5,
ENC 1101 = 41, AMH 2020 = 19, PSY 2012 = 10, BSC 1005 = 2 — **77 Tampa / 0 other-campus**. AMH 2020
had gained two legitimate sections since the 2026-09-09 validation. Post-refresh quality: 0 errors,
31 warnings, 31 info. A search returning all 77 sections took ~10.1s locally (early REQ-PERF-01
signal). Delivered on PR #18 (since merged).

## Phase 1 — real-data expansion validation (executed 2026-09-09, old local beta DB)

Five configured Spring 2027 targets verified present: MAC 1105 = 5, ENC 1101 = 41, AMH 2020 = 17,
PSY 2012 = 10, BSC 1005 = 2 — **75 verified Tampa sections**. Seat refresh appended 75 snapshots,
preserved prior snapshots/identity, left all 237 grade rows unchanged, syllabi empty. Data quality
0 errors across 202408/202501/202508/202701. Frontend/API verification passed, no console errors.
Search performance at widened coverage not sufficiently measured → carved to REQ-PERF-01.

## Historical analytics — old local beta DB state

In the old local beta DB, MAC 1105 and ENC 1101 had real imported grade data (high-confidence
course analytics); AMH 2020 / PSY 2012 / BSC 1005 had none (global fallback, `effective_n = 0`).
**This grade data was never migrated to the current hosted Supabase DB, which has zero grade rows.**

## Data quality — 2026-09-09 validation run

| Term | Errors | Warnings | Info |
|------|--------|----------|------|
| 202408 | 0 | 103 | 103 |
| 202501 | 0 | 6 | 0 |
| 202508 | 0 | 11 | 0 |
| 202701 | 0 | 49 | 49 |

## Test baselines (dated)

- 2026-09-09 at `62fb2f1`: `uv run pytest -q` without `EASY_A_TEST_POSTGRES_URL` → **192 passed,
  1 skipped** (193 collected); with PostgreSQL configured → **193 passed**; frontend `npm test` →
  **78 passed**. A default run does not use PostgreSQL (SQLite; the integration test skips).
- 2026-09-14 Phase 2 branch: **216 passed, 2 skipped** without PostgreSQL; **218 passed** with it;
  ruff + strict mypy passed. Frontend not re-measured.
- 2026-09-20 (Phase 3.5, Supabase path): **256 passed** with `EASY_A_TEST_POSTGRES_URL` exported.

## Sprint 5 — what landed (merged; do not re-plan)

- **PR #14:** configurable course targets, one-pass coverage refresh, seat-only refresh, seat
  freshness classification + API fields, coverage metadata endpoint, PostgreSQL integration coverage.
- **PR #15:** explicit frontend mock opt-in (`VITE_USE_MOCK_DATA`), broader-course UX, server
  pagination hardening, seat freshness UI, coverage UX, relative seat timestamps.
- **PR #16:** coverage refresh pins `campus="T"` and rejects non-Tampa rows before ingestion.

## Fixed — do not re-plan

Silent frontend fixture fallback; missing seat-freshness contract; absent PostgreSQL integration
coverage; hard-coded Spring 2027 term preference (all Sprint 5). Campus-scope bug in configured
refresh (PR #16). Stored cross-campus contamination (Phase 2 / PR #18). Circular import
`analytics.queries → common.instructors → models → rankings.cache → rankings.service/queries`
(fixed 2026-09-20, commit `2bb984a`).
