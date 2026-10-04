---
phase: 09-hosted-beta-deployment-ci-observability
plan: 07
subsystem: database
tags: [sqlalchemy, sync, removed-sections, quality, coverage, analytics]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-02 sections.removed_at and the serving-path filters"
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-05 snapshot_freshness(verified_at=...) cadence-derived thresholds"
provides:
  - "Legacy ingest (_update_section) clears removed_at, so a section seen again is live"
  - "coverage_metadata and refresh_data report active sections only"
  - "Analytics current-term section listings exclude removed sections; historical evidence untouched"
  - "Quality section/seat scans and quality coverage ignore removed sections"
  - "stale_seat_observation judged from Section.last_seen_at with cadence thresholds"
affects: [09-08, 09-11, 09-14, sync-worker, quality]

actuals:
  tokens: 3400
  tasks: 3
  commits: 3
plan_head_before: 449a8ccc5ff648a80d9aca714f93bbbf18a48e3c
plan_head_after: 534a831fa86c35d8171239e10e0dd4b127f8458d

tech-stack:
  added: []
  patterns:
    - "Every current-term Section enumeration carries Section.removed_at.is_(None)"
    - "Narrow-refresh CRN lookup stays unfiltered so an operator can restore a removed CRN"

key-files:
  created:
    - tests/refresh/test_removed_section_consumers.py
    - tests/analytics/test_removed_sections.py
    - tests/quality/test_removed_section_consumers.py
  modified:
    - src/easy_a/schedule/ingest.py
    - src/easy_a/refresh/coverage.py
    - src/easy_a/refresh/service.py
    - src/easy_a/analytics/queries.py
    - src/easy_a/quality/checks.py
    - src/easy_a/quality/coverage.py
    - tests/schedule/test_ingest.py
    - tests/refresh/test_targets.py
    - README.md

key-decisions:
  - "signals/resolver.py left unfiltered by design: it resolves one given CRN and is reached only through callers that already exclude removed sections"
  - "Exactly two predicates added in analytics/queries.py, both on current-term Section listings; no grade-evidence join changed (D-02)"

patterns-established:
  - "Removed-section consumer audit: filter enumerations, never point lookups used for restore"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "Removing a section drops it from /coverage counts and a legacy re-ingest restores it (removed_at cleared)"
    requirement: REQ-SYNC-01
    verification:
      - kind: integration
        ref: "tests/refresh/test_removed_section_consumers.py#test_removed_section_leaves_coverage_and_legacy_reingest_restores_it"
        status: pass
      - kind: unit
        ref: "tests/schedule/test_ingest.py#test_reingest_clears_removed_at_for_sections_seen_again"
        status: pass
    human_judgment: false
  - id: D2
    description: "Analytics current-term listings and refresh_data counts exclude removed sections while the historical course aggregate is unchanged"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/analytics/test_removed_sections.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Quality scans ignore removed sections and stale_seat_observation uses verified time (fresh verification not flagged, stale verification flagged)"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/quality/test_removed_section_consumers.py"
        status: pass
      - kind: command
        ref: "uv run pytest -q && uv run mypy src"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-09-29
---

# Phase 09 Plan 07: Removed-section consumer audit Summary

**removed_at is now honoured by every non-serving current-term consumer (coverage, refresh counts, analytics listings, quality scans), the legacy ingest restores any section it sees again, and seat staleness is judged from the verified time so change-only snapshots cannot flood quality with false warnings.**

## Performance

- **Duration:** about 4 min of executor time (start time not recorded precisely)
- **Completed:** 2026-09-29T17:30Z
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files modified:** 12 (3 created, 9 modified)

## Accomplishments

- Tracer: ingest fixture, mark CRN 13173 removed, `coverage_metadata` drops 2 to 1, legacy `ingest_schedule_html` restores it (count back to 2, `removed_at` None). Verified end to end before expansion.
- `refresh_data` course and section counts use active sections only; analytics current-term listings (`get_current_section_historical_analytics`, `get_term_section_historical_analytics`) exclude removed sections, with an equality test proving the historical course aggregate is identical before and after a removal.
- Quality checks (section scan, seat snapshot scan) and quality coverage ignore removed sections; `stale_seat_observation` now calls `snapshot_freshness(..., verified_at=section.last_seen_at)` and the message reads "Seat data has not been verified within the cadence-derived stale threshold."
- Scoring files (`scoring.py`, `confidence.py`, `grades.py`) unchanged versus origin/main (D-02). Full suite 566 passed, 4 skipped; `mypy src` clean; `ruff check` clean.

## Task Commits

1. **Task 1: Coverage counts drop removed sections; legacy re-ingest restores** - `98414a5` (feat)
2. **Task 2: Refresh counts and analytics current-term listings ignore removed sections** - `3d9a555` (feat)
3. **Task 3: Quality checks skip removed sections and judge staleness by verification time** - `534a831` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `src/easy_a/schedule/ingest.py` - `_update_section` sets `removed_at = None`
- `src/easy_a/refresh/coverage.py` - count/max query filtered to active sections; CRN lookup unfiltered with explanatory comment
- `src/easy_a/refresh/service.py` - course/section counts over active sections
- `src/easy_a/analytics/queries.py` - two current-term Section listings filtered
- `src/easy_a/quality/checks.py` - section scan and seat snapshot scan filtered
- `src/easy_a/quality/coverage.py` - active-section selection; verified-time staleness and reworded message
- `tests/refresh/test_removed_section_consumers.py`, `tests/analytics/test_removed_sections.py`, `tests/quality/test_removed_section_consumers.py` - new
- `tests/schedule/test_ingest.py` - restore-on-reingest test
- `tests/refresh/test_targets.py` - existing stale-seat expectation adjusted (see deviations)
- `README.md` - quality-check description updated to the new staleness basis

## Decisions Made

- `signals/resolver.py` intentionally not filtered (plan truth); callers already exclude removed sections.
- The refresh_data count test runs a second, term-only `RefreshConfig` so no ingest stage restores the removed section before the counts are read.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing stale-seat test assumed legacy 1800 s threshold**
- **Found during:** Task 3 (full-suite run)
- **Issue:** `tests/refresh/test_targets.py::test_seats_append_preserve_identity_grades_syllabus_and_score` asserted a stale warning one hour after the last ingest. With verification-time judgement and the cadence threshold (7200 s outside a registration window) that section is correctly not stale yet, so the assertion encoded the old basis, not a defect.
- **Fix:** Moved `as_of` from `NOW + 1h` to `NOW + 3h` with a comment; the intent (a stale seat produces the warning) is preserved. The plan's "keep every other expectation" instruction covered message text only, so this is recorded as a deviation.
- **Files modified:** tests/refresh/test_targets.py
- **Verification:** full suite green
- **Commit:** 534a831

**2. [Rule 2 - Missing critical] README described the old stale-seat basis**
- **Found during:** Task 3
- **Issue:** README stated seat snapshots older than the configured threshold are flagged, which no longer matches the check.
- **Fix:** Reworded to "seat data not verified within the cadence-derived stale threshold (judged from last-seen time; removed sections ignored)".
- **Files modified:** README.md
- **Commit:** 534a831

**Total deviations:** 2 auto-fixed (1 bug-in-test-assumption, 1 doc accuracy). **Impact:** none on scope; no production behaviour beyond the plan.

## Issues Encountered

None. `ruff format --check` reports 29 pre-existing unformatted files across the repo; that is unrelated to this plan and was not touched (`ruff check`, the CI gate, is clean).

## Threat Flags

None. No new endpoints, auth paths or schema changes.

## Known Stubs

None.

## Next Phase Readiness

Ready for 09-08. The sync worker (09-11) can rely on legacy ingest, coverage, refresh counts, analytics and quality all treating `removed_at` consistently.

## Self-Check: PASSED

- Created files exist: tests/refresh/test_removed_section_consumers.py, tests/analytics/test_removed_sections.py, tests/quality/test_removed_section_consumers.py
- Commits 98414a5, 3d9a555, 534a831 present in git log; `commits: 3` measured from the plan ledger.
- Plan verification: `uv run pytest -q` (566 passed, 4 skipped), `uv run mypy src` (Success: no issues found), scoring files unchanged versus origin/main.
