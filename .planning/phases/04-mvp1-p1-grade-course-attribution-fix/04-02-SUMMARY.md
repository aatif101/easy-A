---
phase: 04-mvp1-p1-grade-course-attribution-fix
plan: 02
subsystem: database
tags: [pandas, openpyxl, sqlalchemy, grade-parser, data-quality]

# Dependency graph
requires:
  - phase: 04-mvp1-p1-grade-course-attribution-fix
    provides: "04-01: GradeDistribution.course_id resolved and persisted via resolve_course_id(), atomic all-keys preflight, same-key null-row repair"
provides:
  - "_cell_to_int() rejects blank/empty canonical grade-bucket and Total Grades cells with a row/column-specific, unverified-semantics ValueError instead of silently coercing to zero"
  - "Explicit numeric integer zero remains a valid canonical count in every bucket and in Total Grades"
  - "unattributed_grade_row error QualityFinding emitted from _check_grades() for every stored GradeDistribution whose course_id is null"
affects: [04-mvp1-p2-grade-data-sourcing]

# Actuals (#2632)
actuals:
  tokens: 1705
  tasks: 2
  commits: 2
  plan_head_before: 2ff78a87808fc259f08482159d84642f981d6293

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-closed blank-cell policy: _cell_to_int() raises on _is_empty_cell() and stripped-empty text instead of returning 0, reusing the existing per-row GradeWorkbookValidationError aggregation so failures still report every offending row/column together."
    - "Quality finding sits inside the existing _check_grades() distribution loop rather than as a new top-level check, matching the grade_total_mismatch/orphan_grade_row placement convention."

key-files:
  created: []
  modified:
    - src/easy_a/grades/parser.py
    - tests/grades/test_parser.py
    - src/easy_a/quality/checks.py
    - tests/quality/test_checks.py

key-decisions:
  - "Kept the blank-rejection message intentionally two-sided ('cannot distinguish zero from unavailable or suppressed') rather than asserting suppression as fact, per D-06/D-07 and the plan's explicit non-suppression-claim requirement."
  - "Percentage columns (% A, % B, ...) were left completely untouched — they are never routed through _cell_to_int(), so no percentage-blank case needed a test or a behavior change."
  - "unattributed_grade_row is additive inside the existing distribution loop in _check_grades(); it does not replace or alter orphan_grade_row (term/CRN-vs-Section) or grade_total_mismatch, which diagnose different invariants and can co-occur on the same row."

requirements-completed: [REQ-GRADES-01]

coverage:
  - id: D1
    description: "A blank canonical A/B/C/D/F/I/S/U/W/O or Total Grades cell rejects the workbook with row, column, and unverified-semantics context; explicit numeric zero remains valid."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/grades/test_parser.py#test_blank_bucket_count_fails_closed"
        status: pass
      - kind: unit
        ref: "tests/grades/test_parser.py#test_blank_total_fails_closed"
        status: pass
      - kind: unit
        ref: "tests/grades/test_parser.py#test_explicit_zero_count_succeeds"
        status: pass
    human_judgment: false
  - id: D2
    description: "The parser never labels a blank as suppressed and never manufactures a zero where the source supplied no canonical count."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/grades/test_parser.py#test_blank_bucket_count_fails_closed"
        status: pass
      - kind: unit
        ref: "tests/grades/test_parser.py#test_blank_total_fails_closed"
        status: pass
    human_judgment: false
  - id: D3
    description: "Data quality emits one deterministic unattributed_grade_row error for each stored GradeDistribution whose course_id is null, while attributed rows do not receive that finding."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "tests/quality/test_checks.py#test_unattributed_grade_row_is_an_error"
        status: pass
      - kind: unit
        ref: "tests/quality/test_checks.py#test_attributed_grade_row_has_no_unattributed_finding"
        status: pass
    human_judgment: false
  - id: D4
    description: "Parser and quality hardening do not alter scoring, term/CRN/source identity, provenance, the analytics fallback, or the rankings API."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: unit
        ref: "uv run pytest -q (261 passed / 3 skipped, up from the 257/3 baseline after 04-01)"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-09-21
status: complete
---

# Phase 04 Plan 02: Blank Grade-Cell Fail-Closed Policy + Quality Guard Summary

**Blank canonical grade-count and Total Grades cells now fail closed with row/column/unverified-semantics context instead of being silently coerced to zero, and every stored `GradeDistribution` with a null `course_id` now surfaces as a deterministic `unattributed_grade_row` data-quality error.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-21 (session start)
- **Completed:** 2026-09-21T07:26:54Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Closed the last unsupported-evidence seam in the parser: `_cell_to_int()` (`src/easy_a/grades/parser.py`) previously returned `0` for both `pandas`-missing values and stripped-empty text in every canonical grade bucket and `Total Grades`. It now raises a row/column-specific `ValueError` — aggregated into the existing `GradeWorkbookValidationError` path — whenever a canonical count cell is blank, with a message stating the semantics are unverified rather than claiming the source suppressed the value (D-06, D-07, OQ-04). Explicit numeric zero (integer, numeric string, or numeric type) remains fully valid in every bucket. Percentage columns are unaffected — they are never routed through `_cell_to_int()`.
- Replaced `test_empty_count_cells_are_zero` (the old blank-as-zero expectation) with `test_blank_bucket_count_fails_closed` and `test_blank_total_fails_closed`, and added `test_explicit_zero_count_succeeds` as a positive control proving zero and blank are treated as materially different inputs.
- Added an `unattributed_grade_row` error finding inside the existing `_check_grades()` distribution loop (`src/easy_a/quality/checks.py`): every persisted `GradeDistribution` with `course_id is None` now produces one deterministic finding carrying its term, CRN, and `grade_distribution:{id}` source record, stating the row cannot supply course historical analytics until attributed — with no inference of course identity from CRN. The existing `grade_total_mismatch` and `orphan_grade_row` checks are untouched and remain independent; a row can trigger any combination of the three.
- Extended `_grade()` in `tests/quality/test_checks.py` with `course_id: int | None = 10` and added `test_unattributed_grade_row_is_an_error` plus a positive control `test_attributed_grade_row_has_no_unattributed_finding` proving a correctly attributed row receives no `unattributed_grade_row` finding.

## Task Commits

Each task was committed atomically:

1. **Task 1: Reject ambiguous blank canonical counts while accepting explicit zero** - `d45fda9` (test)
2. **Task 2: Surface persisted null course attribution as a data-quality error** - `1dac70d` (test)

**Plan metadata:** commit created below (docs: complete plan)

_Note: both tasks are `tdd="true"`. For each, the new/replacement tests were written and run first to confirm RED against the unmodified production code, then the minimal production change was made and the same tests re-run to confirm GREEN — both within the same task commit, matching the 04-01 TDD/commit-scope contract._

## Files Created/Modified

- `src/easy_a/grades/parser.py` - `_cell_to_int()` no longer coerces blank/empty canonical count cells to `0`; it raises a new `_blank_count_cell_message()`-formatted `ValueError` with row, column, and unverified-semantics language. Explicit-zero and all other existing validation branches (boolean, non-numeric, non-integer) are unchanged.
- `tests/grades/test_parser.py` - Replaced the blank-as-zero test with `test_blank_bucket_count_fails_closed`, `test_blank_total_fails_closed`, and `test_explicit_zero_count_succeeds`.
- `src/easy_a/quality/checks.py` - `_check_grades()` gains a second finding branch inside its existing distribution loop, appending an `unattributed_grade_row` error for every `GradeDistribution` row with `course_id is None`.
- `tests/quality/test_checks.py` - `_grade()` gains `course_id: int | None = 10`; added `test_unattributed_grade_row_is_an_error` and `test_attributed_grade_row_has_no_unattributed_finding`.
- `.planning/phases/04-mvp1-p1-grade-course-attribution-fix/deferred-items.md` - Appended a second logged pre-existing, unrelated finding (out of scope for this plan — see Issues Encountered).

## Decisions Made

- Wrote the blank-rejection message as "cannot distinguish zero from unavailable or suppressed" (a stated ambiguity) rather than any wording that asserts suppression as the actual cause — this satisfies the plan's explicit "does not assert that the cell is suppressed" acceptance criterion while still being maximally informative to an operator (D-06, D-07).
- Left `unattributed_grade_row` additive and independent of `orphan_grade_row` / `grade_total_mismatch` rather than merging or replacing any existing check — they diagnose distinct invariants (null attribution vs. no matching Section vs. bucket-sum mismatch) and a single row can legitimately trigger more than one.
- Did not touch `src/easy_a/grades/ingest.py`, `src/easy_a/analytics/`, `src/easy_a/rankings/`, or the rankings API — this plan's scope is strictly the parser's blank-cell eligibility policy and one additive quality finding, per the plan's `files_modified` and the PATTERNS.md guardrails.

## Deviations from Plan

None - plan executed exactly as written. Both tasks matched their `<action>`/`<behavior>`/`<acceptance_criteria>` blocks with no Rule 1-4 auto-fixes required.

## Issues Encountered

- Running the full-repo `uv run ruff check .` gate (per this plan's `<verification>`) surfaced one pre-existing `E501` (line too long) in `src/easy_a/refresh/cleanup.py:494`. Confirmed via `git log -1 -- src/easy_a/refresh/cleanup.py` (last touched at commit `0c0f0c9`, 2026-09-20, predating both of this plan's commits) that the file is untouched by 04-02 and not in `04-02-PLAN.md`'s `files_modified`. Logged to `deferred-items.md` per the scope-boundary rule rather than fixed here. `uv run ruff check` on this plan's four changed files passes clean, and the full pytest suite (261 passed / 3 skipped) is unaffected.
- Running the full-repo `uv run mypy src migrations scripts tests` gate reproduced the same pre-existing, unrelated `tests/test_database_config.py` strict-mypy failures already logged against 04-01 (untouched by 04-02; no new entry needed).
- `EASY_A_TEST_POSTGRES_URL` was unset in this environment, so the PostgreSQL-configured integration path was not run (per the plan's `<environment_gate>` and D-12, this is reported honestly rather than claimed as passing).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The blank-cell fail-closed policy and the `unattributed_grade_row` quality guard planned for `04-02` are both now in place, completing the MVP1-P1 safety envelope described in `04-01-SUMMARY.md`'s "Next Phase Readiness": MVP1-P2 (Codex-owned grade data sourcing) can now import real USF InfoCenter exports and expect (a) rows to attach directly to current-term sections via `resolve_course_id()`, (b) any row containing a blank canonical count to be rejected with an honest, non-suppression-asserting reason rather than silently zeroed, and (c) any legacy or future null-attributed row to be visible as an explicit `unattributed_grade_row` quality error rather than silently absent from analytics.
- OQ-04 (real InfoCenter blank-cell/suppression semantics) remains genuinely unresolved — this plan deliberately rejects blanks rather than guessing their meaning, exactly as `04-RESEARCH.md` recommended; Phase 05 (or whichever phase inspects a real/sample export) must establish source-backed semantics before any blank-containing row can be accepted.
- Full pytest suite green (261 passed / 3 skipped, up from 257/3 after 04-01), ruff and strict mypy clean on all four files this plan modified. No raw or synthetic `.xlsx`/`.xls` file is tracked in Git (`git ls-files` verified empty for that pattern). PostgreSQL-configured path not run in this environment (D-12) — must be run in an authorized environment before the phase gate is fully closed.

## Self-Check: PASSED

- `src/easy_a/grades/parser.py` — FOUND
- `tests/grades/test_parser.py` — FOUND
- `src/easy_a/quality/checks.py` — FOUND
- `tests/quality/test_checks.py` — FOUND
- `.planning/phases/04-mvp1-p1-grade-course-attribution-fix/deferred-items.md` — FOUND
- Commit `d45fda9` — FOUND in `git log --oneline --all`
- Commit `1dac70d` — FOUND in `git log --oneline --all`

---
*Phase: 04-mvp1-p1-grade-course-attribution-fix*
*Completed: 2026-09-21*
