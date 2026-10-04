---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
plan: 05
subsystem: testing
tags: [pytest, sqlalchemy, mypy, ruff, supabase, data-quality]

# Dependency graph
requires:
  - phase: 08-mvp1-p5-end-to-end-mvp-1-verification (08-02, 08-04)
    provides: scripts/inventory_tampa_grades.py, scripts/validate_tampa_ingest.py and their
      test suites, plus the Phase 8 verification report and validation strategy this plan
      re-verifies and amends
provides:
  - A D-21 grade-coverage inventory gate whose verdict is derived from every counter it
    reports under "integrity" (closes the CR-01 verification gap) instead of a subset
  - stale_cache computed from grade rows inside the scoring evidence window only, not
    every fetched row (WR-01)
  - A documented, behavior-preserving fail-closed contract for the Phase 06 suffix-leak
    guard's ambiguous zero-section case (WR-02)
  - A dated, read-only re-verification of both fixed gates against hosted Supabase,
    recorded in 08-VERIFICATION-REPORT.md and 08-VALIDATION.md
affects: [phase-09-hosted-beta, mvp-1-ship-gate]

# Actuals (#2632)
actuals:
  tokens: 10702
  tasks: 3
  commits: 3
plan_head_before: 915b3b7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A gate's JSON 'integrity' block and its PASS/FAIL derivation share one local mapping,
      so a reported counter cannot be silently excluded from the verdict (integrity_ok =
      failure_section_count == 0 and not any(integrity.values()))."
    - "stale_cache/staleness checks compare against a maximum computed only over rows that
      pass the same filter the scoring query applies, not every fetched row, to avoid both
      false positives (unrelated out-of-window data) and false negatives (WR-01)."

key-files:
  created: []
  modified:
    - scripts/inventory_tampa_grades.py
    - tests/refresh/test_inventory_tampa_grades.py
    - scripts/validate_tampa_ingest.py
    - tests/refresh/test_validate_tampa_ingest.py
    - .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md
    - .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md

key-decisions:
  - "CR-01 fixed: Inventory.to_dict now builds the 'integrity' JSON mapping once as a local
    and derives integrity_ok from that same mapping, so rows_at_or_after_term (and any future
    reported counter) can never print PASS while nonzero."
  - "WR-01 fixed: added a second running maximum (evidence_ingested_at_max) updated only for
    grade rows that pass the term_code < before_term filter, matching the scoring query's own
    filter; stale_cache now compares against it instead of the maximum over every fetched row."
  - "WR-02 kept, not narrowed: assert_suffix_exact_ingest's raise condition, queries and loop
    are byte-for-byte unchanged from HEAD a1f6d45. Scoping the suffix-course existence lookup
    to sections in the validated term would make the zero-section branch unreachable and
    silently delete the Phase 06 L-variant leak guard, so the ambiguous state still fails
    closed -- only the docstring, one comment and the AssertionError message changed to name
    both possibilities honestly."
  - "IN-01 and IN-02 deferred per the plan's pre-approved scope, with their unchanged-file
    status re-confirmed live in Task 3 (scripts/benchmark_rankings_search.py and web/src
    diff empty against a1f6d45)."

requirements-completed: [REQ-GRADES-01, REQ-COVERAGE-03]

coverage:
  - id: D1
    description: "Every counter reported under the D-21 inventory's 'integrity' JSON key
      gates both verdicts.integrity and verdicts.d21_grade_coverage (and the exit code):
      rows_at_or_after_term > 0 now fails the gate instead of being silently absorbed (CR-01)."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/refresh/test_inventory_tampa_grades.py::test_rows_at_or_after_term_gates_integrity_verdict"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_inventory_tampa_grades.py::test_every_reported_integrity_counter_gates_the_verdict"
        status: pass
      - kind: integration
        ref: "tests/refresh/test_inventory_tampa_grades.py::test_main_exits_nonzero_when_grade_row_at_or_after_term_exists"
        status: pass
    human_judgment: false
  - id: D2
    description: "stale_cache is derived only from grade rows inside the scoring evidence
      window (term_code < before_term), so an out-of-window ingest can no longer trip it
      while an in-window one (e.g. the 202408 pilot) still does (WR-01)."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: integration
        ref: "tests/refresh/test_inventory_tampa_grades.py::test_stale_cache_ignores_out_of_window_grade_ingest"
        status: pass
      - kind: integration
        ref: "tests/refresh/test_inventory_tampa_grades.py::test_stale_cache_trips_on_newer_in_window_grade_ingest"
        status: pass
    human_judgment: false
  - id: D3
    description: "assert_suffix_exact_ingest's leak guard fails closed on the ambiguous
      zero-section suffix-course case (ingested but with no sections in the validated term),
      with the raise condition unchanged and the ambiguity now documented (WR-02)."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: integration
        ref: "tests/refresh/test_validate_tampa_ingest.py::test_assert_suffix_exact_ingest_fails_closed_when_suffix_offered_only_in_another_term"
        status: pass
      - kind: integration
        ref: "tests/refresh/test_validate_tampa_ingest.py::test_assert_suffix_exact_ingest_passes_for_the_term_the_suffix_is_offered_in"
        status: pass
      - kind: integration
        ref: "tests/refresh/test_validate_tampa_ingest.py::test_assert_suffix_exact_ingest_raises_on_leaked_suffix_section"
        status: pass
    human_judgment: false
  - id: D4
    description: "The fixed D-21 inventory and validator were re-run read-only against
      hosted Supabase (term 202701) and reproduced the 08-04 baseline exactly: verdicts
      PASS/PASS, 3,122/361/300 sections, all five integrity counters clean, validator
      honest-coverage 300 matching the inventory exactly. Recorded in
      08-VERIFICATION-REPORT.md's new 'Gap closure re-verification (08-05)' section."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: other
        ref: "uv run python scripts/inventory_tampa_grades.py --term 202701 (live hosted Supabase, observed 2026-09-24T19:21:44Z)"
        status: pass
      - kind: other
        ref: "uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml (live hosted Supabase, observed window 2026-09-24T19:24:21Z)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-09-24
status: complete
---

# Phase 8 Plan 5: D-21 Integrity Gate Fix and Live Re-Verification Summary

**Closed the Phase 8 verification gap (CR-01: `rows_at_or_after_term` was reported but never gated the D-21 verdict) plus two review warnings (WR-01 `stale_cache` window, WR-02 suffix-guard documentation), then re-ran both fixed gates read-only against hosted Supabase and got the same PASS/PASS/3,122/361/300 result as 08-04.**

## Performance

- **Duration:** ~30 min (commits span 2026-09-24T19:17Z–19:27Z; RED/GREEN capture and doc edits included)
- **Started:** 2026-09-24 (session start, reading plan + review + context)
- **Completed:** 2026-09-24T19:27:05Z
- **Tasks:** 3/3
- **Files modified:** 6 (2 production scripts, 2 test files, 2 phase-record docs)

## Accomplishments

- **CR-01 closed:** `Inventory.to_dict` in `scripts/inventory_tampa_grades.py` now builds the
  `"integrity"` JSON mapping once as a local and derives `integrity_ok` from that same mapping
  (`failure_section_count == 0 and not any(integrity.values())`), so `rows_at_or_after_term`
  (or any future reported counter) can never print PASS while nonzero. Proven end to end: a real
  `GradeDistribution` row on the inventoried term, seeded through the database, travels through
  `collect_inventory` → `to_dict` → `main()` to `FAIL`/`FAIL`, exit 1.
- **WR-01 fixed:** `_aggregate_grade_rows` now tracks a second running maximum,
  `evidence_ingested_at_max`, updated only for grade rows that pass the same
  `term_code < before_term` filter the scoring queries in `src/easy_a/analytics/queries.py`
  apply. `stale_cache` compares the cache refresh time against this evidence-window maximum
  (exposed as the new `snapshot.evidence_grade_ingested_at_max` field) instead of the maximum
  over every fetched row, so an out-of-window ingest can no longer trip it while an in-window
  one (including the 202408 pilot, outside `D21_WINDOW_TERMS` but inside the scoring evidence
  window) still does.
- **WR-02 kept and documented:** `scripts/validate_tampa_ingest.py`'s `assert_suffix_exact_ingest`
  raise condition, every query, loop and `continue` are byte-for-byte unchanged from HEAD
  `a1f6d45`. Only the docstring, one comment and the `AssertionError` message changed, naming
  both possibilities ("leaked into" the base course, or "not offered in term" the validated
  term) instead of asserting only the leak. The reviewer's alternative fix (scoping the
  suffix-course existence lookup to courses with sections in the validated term) would make the
  zero-section branch unreachable and silently delete the Phase 06 L-variant leak guard, so it
  was not applied.
- **Touched-file mypy fix:** `test_write_atomic_leaves_target_absent_on_simulated_failure` now
  monkeypatches `os.replace` directly via a top-level `import os`, instead of `inv.os` (which
  mypy rejected as a non-exported attribute). This is the `test_inventory_tampa_grades.py`
  portion of `.planning/WINDOWS.md` entry 9; the `tests/api/test_verify_rankings_pages.py`
  portion is unchanged and stays open.
- **Live re-verification:** re-ran the fixed inventory and validator read-only against hosted
  Supabase (term 202701). Result reproduces the 08-04 baseline exactly: `verdicts.integrity` =
  `verdicts.d21_grade_coverage` = PASS, 3,122 evidence_backed / 361 exception_no_rows / 300
  exception_non_letter_grade, all five integrity counters 0/false,
  `evidence_grade_ingested_at_max` equal to `grade_ingested_at_max` (every stored grade row
  precedes 202701), validator `PASS suffix-exact` / `PASS reconciliation` /
  `PASS honest-coverage (verified non-letter-grade exceptions: 300)`. No hosted data was
  written; `08-D21-EXCEPTIONS.md` was not regenerated.

## RED/GREEN Evidence (Tasks 1 and 2)

**Task 1 (CR-01), RED** — before the fix, against the unfixed script:

```
FAILED tests/refresh/test_inventory_tampa_grades.py::test_rows_at_or_after_term_gates_integrity_verdict[3-FAIL]
FAILED tests/refresh/test_inventory_tampa_grades.py::test_every_reported_integrity_counter_gates_the_verdict
FAILED tests/refresh/test_inventory_tampa_grades.py::test_main_exits_nonzero_when_grade_row_at_or_after_term_exists
3 failed, 1 passed in 0.24s
```

**Task 1, GREEN** — after adding the shared `integrity` mapping and deriving `integrity_ok` from it:

```
4 passed in 0.10s   # the 3 named tests (parametrized to 4 cases)
26 passed in 0.19s  # full test_inventory_tampa_grades.py (22 existing + 4 new)
```

**Task 2 (WR-01), RED** — reverted `scripts/inventory_tampa_grades.py` to the Task 1 commit
(`b124e0a`, pre-WR-01) and re-ran the new stale_cache tests:

```
FAILED tests/refresh/test_inventory_tampa_grades.py::test_stale_cache_ignores_out_of_window_grade_ingest
  assert output["integrity"]["stale_cache"] is False
  E  assert True is False
1 failed, 1 passed in 0.22s
```

(`test_stale_cache_trips_on_newer_in_window_grade_ingest` legitimately passed against both old
and new logic — an in-window re-ingest trips `stale_cache` either way; only the out-of-window
case distinguishes the fix.)

**Task 2 (WR-02), RED** — reverted `scripts/validate_tampa_ingest.py` to `b124e0a` and re-ran
the new cross-term validator tests:

```
FAILED tests/refresh/test_validate_tampa_ingest.py::test_assert_suffix_exact_ingest_fails_closed_when_suffix_offered_only_in_another_term
  AssertionError: assert 'not offered in term' in 'CHM 2045L: suffix course is ingested but owns
  0 stored sections for term 202701 -- its sections were likely mis-attributed to (leaked into)
  CHM 2045.'
1 failed, 2 passed in 0.99s
```

**Task 2, GREEN** — after restoring both fixes:

```
5 passed in 0.60s   # the 5 named Task 2 tests
42 passed in 0.67s  # full test_inventory_tampa_grades.py + test_validate_tampa_ingest.py (34 baseline + 8 new)
```

`uv run ruff check` and `uv run mypy` on all four touched files: clean both times (mypy required
one additional fix beyond the plan's literal text — see Deviations).

## Task Commits

Each task was committed atomically:

1. **Task 1: Tracer — gate every reported integrity counter (CR-01)** - `b124e0a` (fix)
2. **Task 2: stale_cache from scoring-window rows only; suffix guard kept and documented (WR-01, WR-02)** - `0dc05aa` (fix)
3. **Task 3: Read-only live re-verification against hosted Supabase** - `2af00c1` (docs)

**Plan metadata:** recorded below (final commit made after this SUMMARY).

## Files Created/Modified

- `scripts/inventory_tampa_grades.py` - Shared `integrity` mapping gates both verdicts (CR-01);
  `evidence_ingested_at_max` drives `stale_cache` from scoring-window rows only (WR-01); new
  `Inventory.evidence_grade_ingested_at_max` field and snapshot key; docstring/comment updates.
- `tests/refresh/test_inventory_tampa_grades.py` - `_make_inventory` accepts field overrides via
  `dataclasses.replace`; `_add_grade` gained optional `ingested_at`; new `_pin_timestamps` helper
  and `T0` constant; 6 new tests (3 CR-01, 2 WR-01, plus the `inv.os`→`os` mypy fix on the
  existing `write_atomic` test).
- `scripts/validate_tampa_ingest.py` - `assert_suffix_exact_ingest`'s raise condition, queries
  and loop unchanged; docstring, one comment and the `AssertionError` message reworded to name
  the catalog-scoped-vs-term-scoped ambiguity honestly (WR-02).
- `tests/refresh/test_validate_tampa_ingest.py` - `_add_section` gained a `term_id` kwarg; 2 new
  cross-term tests proving the fail-closed behavior in one term and the pass in the other.
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md` - new
  "## Gap closure re-verification (08-05)" section; three Gates rows updated to reference the
  fixed gate and the live re-confirmation; one sentence added to "## Verdicts".
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md` - one new
  requirement-map row for 08-05.

## Decisions Made

See `key-decisions` in the frontmatter above (CR-01 fixed, WR-01 fixed, WR-02 kept and
documented not narrowed, IN-01/IN-02 deferred per the plan's pre-approved scope).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_make_inventory`'s `**overrides` typing failed mypy under `dataclasses.replace`**
- **Found during:** Task 2 verification (`uv run mypy` on the four touched files)
- **Issue:** Typing `_make_inventory(sections, **overrides: object)` and the invariant test's
  `dataclasses.replace(clean, **{key: dirty})` made mypy type-check the dict-splat against every
  individual `Inventory` field type, producing 13 `arg-type` errors not present in the plan's
  literal instructions or the 08-04 baseline.
- **Fix:** Changed the parameter to `**overrides: Any` (`typing.Any`) in `_make_inventory`, and
  built an explicit `overrides: dict[str, Any] = {key: dirty}` before splatting it in the
  invariant test, so mypy treats the values as compatible with any field type.
- **Files modified:** `tests/refresh/test_inventory_tampa_grades.py`
- **Verification:** `uv run mypy scripts/inventory_tampa_grades.py scripts/validate_tampa_ingest.py tests/refresh/test_inventory_tampa_grades.py tests/refresh/test_validate_tampa_ingest.py` → "Success: no issues found in 4 source files"
- **Committed in:** `0dc05aa` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/blocking — a mypy typing fix needed to meet the plan's
own "mypy clean on the four touched files" acceptance criterion)
**Impact on plan:** Necessary to satisfy the plan's own verification gate; no behavior change,
test-file typing only. No scope creep.

## Issues Encountered

None beyond the deviation above. RED capture for the WR-01/WR-02 fixes required temporarily
reverting the two production scripts to the Task 1 commit (`git checkout b124e0a -- <file>`,
never `git stash`) and restoring them from a scratchpad backup afterward — both files were
diffed against their pre-revert state to confirm an exact restore before the Task 2 commit.

## User Setup Required

None - no external service configuration required.

## `.planning/WINDOWS.md` entry 9

Partially addressed: the `tests/refresh/test_inventory_tampa_grades.py` portion (`inv.os`
re-export) is fixed by this plan's Task 2. The `tests/api/test_verify_rankings_pages.py`
portion (5 errors: missing return-type annotation, two untyped-function calls, an unused
`type: ignore`, an `int()` overload mismatch) is unchanged and out of this plan's declared file
scope — entry 9 stays open for that file. Repo-wide `mypy src migrations scripts tests` moved
from 36 errors / 11 files (08-04) to 35 errors / 10 files (08-05), a -1/-1 delta matching exactly
the one error this plan's touched-file fix resolved.

## Next Phase Readiness

- MVP-1's REQ-GRADES-01 verdict now rests on a D-21 inventory gate that enforces every integrity
  counter it reports, not a subset — the Phase 8 verification gap (CR-01) is closed.
- All three review-warning/info dispositions from `08-REVIEW.md` are recorded: WR-01 fixed,
  WR-02 kept and documented, IN-01/IN-02 deferred with reasons.
- No blockers. Phase 9 (Hosted Beta) and any ship/milestone-close workflow can proceed on the
  updated Phase 8 verification record.

---
*Phase: 08-mvp1-p5-end-to-end-mvp-1-verification*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 7 claimed files found on disk (4 code/test files, 2 phase-record docs, this SUMMARY). All 3
task commit hashes (`b124e0a`, `0dc05aa`, `2af00c1`) found in `git log --oneline --all`.
