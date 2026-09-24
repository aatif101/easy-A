---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
plan: 01
subsystem: testing
tags: [rankings-api, verification, sqlalchemy, httpx, fastapi, req-coverage-03]

requires:
  - phase: 07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
    provides: full-scale rankings cache at 3,783 sections and the search route's
      key-first paging that this scanner walks
provides:
  - "scripts/verify_rankings_pages.py: a read-only, loopback-only CLI proving exact
    full-page identity-set equality between stored Section rows and
    GET /api/v1/rankings/search for a term, not merely a matching aggregate total"
  - "A real 202701 PASS verdict against hosted Supabase, recorded verbatim below, for
    the 08-04 REQ-COVERAGE-03 verification report to consume"
affects: [08-04-end-to-end-verification]

actuals:
  tokens: 8095
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Bounded page walk: stop after ceil(first_total/page_size) pages (or 1 page when
      total is 0), never trusting an unbounded loop to terminate correctly"
    - "Named FAIL reasons per structural anomaly (short_page, duplicate_identity,
      identity_mismatch, snapshot_changed, order_violation, http_status,
      invalid_response, non_tampa_section, page_overrun, count_mismatch) instead of a
      single boolean pass/fail"
    - "score_source split is reporting-only: tallied for every returned section but
      never folded into a coverage verdict (D-20/D-21)"

key-files:
  created:
    - scripts/verify_rankings_pages.py
    - tests/api/test_verify_rankings_pages.py
  modified: []

key-decisions:
  - "Task 2's boundary/ordering/empty-term/unstable-snapshot tests all passed against
    the Task 1 implementation with zero production-code changes: scan_pages()'s
    bounded walk, per-page/adjacency ordering check and collected-vs-total overrun
    check, plus reconcile()'s duplicate/identity/non-Tampa checks, were designed as
    one complete algorithm in Task 1 rather than incrementally. Verified directly via
    pytest's own per-test evidence (workflow.tdd_mode is false for this project, same
    precedent as Phase 06-03's SUMMARY)."
  - "--http-base-url reuses scripts/benchmark_rankings_search.py's plain-loopback-origin
    validation semantics by duplicating the small check in this script, not by
    importing across scripts/ (each script is a standalone CLI, matching the existing
    convention where tests load them via importlib file-location, not package import)."
  - "The API route reads from SectionRankingCache, not raw Section rows, so a stored
    Section that was never refreshed into the cache surfaces as a missing CRN
    (identity_mismatch), not a silent count_mismatch -- more informative for the
    08-04 report."

requirements-completed: [REQ-COVERAGE-03]

coverage:
  - id: D1
    description: "scripts/verify_rankings_pages.py walks every page of
      GET /api/v1/rankings/search (sort=course) and proves exact identity-set
      equality against stored Section rows, failing loudly on any omission,
      substitution, duplication or unstable total instead of trusting a matching
      count alone"
    requirement: REQ-COVERAGE-03
    verification:
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_seeded_three_section_walk_at_page_size_two_yields_pass"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_omitted_stored_crn_yields_identity_mismatch"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_substituted_crn_same_count_yields_identity_mismatch"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_exactly_page_size_rows_scans_one_page_with_no_overlap"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_one_row_past_page_size_yields_second_page_of_exactly_one"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_empty_term_yields_pass_with_zero_stored_and_one_page"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_short_non_final_page_fails_with_short_page_reason"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_duplicate_crn_across_adjacent_pages_fails_with_duplicate_identity"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_total_changing_between_pages_fails_with_snapshot_changed"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_out_of_order_items_fail_with_order_violation"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_http_500_fails_with_http_status_reason"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_malformed_json_body_fails_with_invalid_response_reason"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_collecting_more_items_than_total_fails_with_page_overrun"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_stored_non_tampa_section_fails_with_non_tampa_section_reason"
        status: pass
      - kind: e2e
        ref: "uv run python scripts/verify_rankings_pages.py --term 202701 --http-base-url http://127.0.0.1:8000"
        status: pass
    human_judgment: false
  - id: D2
    description: "api_score_source_split reports course/instructor_course/subject/global
      counts (with effective_n=0 sub-counts) without ever treating any split as grade
      coverage (D-20/D-21)"
    requirement: REQ-COVERAGE-03
    verification:
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_score_source_split_counts_every_returned_section_without_claiming_coverage"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-24
status: complete
---

# Phase 08 Plan 01: Rankings Page Identity Scanner Summary

**Read-only, loopback-only CLI that walks every page of GET /api/v1/rankings/search
(sort=course) and proves exact identity-set equality against stored Section rows for a
term, replacing the "matching first-page total" benchmark with a real PASS/FAIL/NOT
MEASURED verdict; the live run against hosted Supabase term 202701 returned PASS with
3,783/3,783 sections reconciled and zero missing, extra, duplicate or non-Tampa
identities.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-23T23:15:00Z (approx, first file read)
- **Completed:** 2026-09-24T00:10:00Z
- **Tasks:** 2 completed
- **Files modified:** 2 (both new)

## Accomplishments

- `scripts/verify_rankings_pages.py`: `build_parser()`, `main(argv) -> int`,
  `StoredSnapshot`, `PageScan`, `IdentityVerdict`, `stored_identities(session, term)`,
  `scan_pages(client, term, page_size)`, `reconcile(stored, scan)`. CLI flags `--term`
  (default 202701), `--http-base-url` (required, loopback-only), `--page-size`
  (1..200, default 200). Exit codes 0 PASS / 1 FAIL / 3 NOT MEASURED.
- Bounded page walk: stops after `ceil(first_total / page_size)` pages (or 1 page when
  the first-observed total is 0), never fetching an unnecessary probe page — the
  200-row boundary case ends in exactly 1 page, the 201-row case in exactly 2, with no
  empty-page overlap.
- Ten named FAIL reasons, each with a dedicated regression test: `identity_mismatch`,
  `count_mismatch`, `short_page`, `duplicate_identity`, `snapshot_changed`,
  `order_violation`, `http_status`, `invalid_response`, `non_tampa_section`,
  `page_overrun`.
- `api_score_source_split` tallies `course` / `instructor_course` / `subject` /
  `global` counts (with an `effective_n_zero` sub-count) for every returned section,
  documented as reporting-only — never folded into the PASS/FAIL verdict, honoring
  D-20/D-21.
- Real live run against hosted Supabase, term 202701 (recorded verbatim, sanitized):
  `{"gate": "api_identity", "verdict": "PASS", "reason": null, "term": "202701",
  "observed_at_utc": "2026-09-23T23:57:06.003338+00:00", "environment": "Supabase",
  "stored_count": 3783, "cache_count": 3783, "api_total": 3783, "pages_fetched": 19,
  "page_size": 200, "missing_count": 0, "extra_count": 0, "duplicate_count": 0,
  "non_tampa_count": 0, "order_violations": 0, "sample_missing": [], "sample_extra":
  [], "sample_duplicates": [], "api_score_source_split": {"course": {"count": 3422,
  "effective_n_zero": 300}, "global": {"count": 50, "effective_n_zero": 50}, "subject":
  {"count": 311, "effective_n_zero": 0}}}`. This matches STATE.md's D-21 inventory
  exactly (3,122 evidence-backed = 3,422 course − 300 effective_n=0; 311 subject; 50
  global) and confirms every stored Tampa section is searchable through the complete
  page walk, not just a matching count.

## Task Commits

Each task was committed atomically (Task 1 as RED then GREEN; Task 2 as an additional
RED-equivalent commit whose tests all passed against the Task 1 implementation with no
GREEN/production-code commit needed — see Deviations below):

1. **Task 1 RED** — `f014ffc` `test(08-01): add failing tests for rankings page
   identity scanner` (test)
2. **Task 1 GREEN** — `8dc19ac` `feat(08-01): implement rankings page identity
   scanner` (feat)
3. **Task 2** — `bd25186` `test(08-01): cover page-boundary, empty-term, ordering and
   unstable-snapshot cases` (test; no feat/refactor commit — see Deviations)

**Plan metadata:** commit pending below (this SUMMARY + STATE/ROADMAP/REQUIREMENTS).

## Files Created/Modified

- `scripts/verify_rankings_pages.py` — the identity scanner CLI (new)
- `tests/api/test_verify_rankings_pages.py` — 16 tests covering the PASS path, every
  named FAIL reason, the NOT MEASURED connection-error path, and the score-source
  split reporting contract (new)

## Decisions Made

- Reused `benchmark_rankings_search.py`'s plain-loopback-origin validation semantics
  by duplicating the small `_http_base_url` check locally rather than importing across
  `scripts/` modules, consistent with the existing convention (each script is a
  standalone CLI; tests load them via `importlib` file-location, not package import).
- Chose exact-tuple-equality (not just strict-inequality) as the boundary between
  `duplicate_identity` and `order_violation` during the per-page/adjacency ordering
  check: an adjacent repeated `(subject, course_number, crn)` key is reported as
  `duplicate_identity`, a genuinely decreasing key as `order_violation`. Because
  `crn` is unique within a term (`uq_sections_term_crn`), a correctly-ordered walk can
  only ever produce a duplicate adjacently — a non-adjacent duplicate would require an
  intervening ordering violation, which the walk already catches first.
- `count_mismatch` is implemented as a defensive fallback reason (all three counts must
  agree once identities, duplicates and non-Tampa rows are all clean) but has no
  dedicated test, matching the plan's acceptance criteria which does not require one —
  the route reads from `SectionRankingCache`, so a Section without a cache row
  surfaces as `identity_mismatch` (a missing CRN), not silently as `count_mismatch`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] Removed two unused imports flagged by ruff**
- **Found during:** Task 1 (post-implementation `ruff check`)
- **Issue:** `import sys` and `from easy_a.models import Course` were left over from
  early drafting and were never referenced.
- **Fix:** Removed both (`F401`).
- **Files modified:** `scripts/verify_rankings_pages.py`
- **Verification:** `uv run ruff check scripts/verify_rankings_pages.py
  tests/api/test_verify_rankings_pages.py` exits 0; `uv run mypy
  scripts/verify_rankings_pages.py` exits 0.
- **Committed in:** `8dc19ac` (folded into the Task 1 GREEN commit before it was made
  — no separate commit needed since the fix landed before the GREEN commit).

---

**Total deviations:** 1 auto-fixed (1 lint). **Impact:** cosmetic only, no behavior
change.

### Process note (not a Rule 1-4 deviation)

Task 2's `<action>` describes implementation work ("Bound the walk...", "Check every
page's total...", "Check ordering...") as if it were still to be done. In practice the
Task 1 implementation was designed as one complete algorithm covering every case in
both tasks' `<behavior>` blocks (the bounded-walk termination condition, the
per-page/adjacency ordering check, and the collected-vs-total overrun check are all a
single cohesive design that can't be meaningfully split in half). All 16 tests written
across Task 1 and Task 2 — including every Task-2-only boundary/ordering/empty-term/
unstable-snapshot case — passed against the Task 1 GREEN implementation with **zero**
additional production-code changes; Task 2 therefore produced only a `test(08-01)`
commit with no matching `feat`/`refactor` commit. This is documented per the TDD
`error_handling` guidance ("Test doesn't fail in RED phase: feature may already exist —
investigate" — investigated, confirmed by design, not a false green) and matches the
precedent set in Phase 06-03's SUMMARY, which likewise notes `workflow.tdd_mode` is
false for this project so the automated RED/GREEN gate isn't enforced; RED/GREEN
discipline was verified directly via pytest's own per-test evidence instead.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `scripts/verify_rankings_pages.py` and its live 202701 PASS verdict (recorded above,
  verbatim JSON) are ready for `08-04` to consume for the REQ-COVERAGE-03 row of
  `08-VERIFICATION-REPORT.md`; its `api_score_source_split` is ready to be
  cross-checked there against the `08-02` inventory's cache split.
- No blockers. `src/easy_a/api`, `src/easy_a/rankings` and `src/easy_a/analytics` are
  untouched (`git diff --quiet origin/main` on those paths exits 0) — no ranking
  calculation, cache row or response contract changed (D-02).
- Full suite: 340 passed / 3 skipped (was 324 passed / 3 skipped at plan start; +16 new
  tests, 0 regressions).

---
*Phase: 08-mvp1-p5-end-to-end-mvp-1-verification*
*Completed: 2026-09-24*

## Self-Check: PASSED

- FOUND: scripts/verify_rankings_pages.py
- FOUND: tests/api/test_verify_rankings_pages.py
- FOUND: .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-01-SUMMARY.md
- FOUND: f014ffc (test RED)
- FOUND: 8dc19ac (feat GREEN)
- FOUND: bd25186 (test, Task 2 coverage)
