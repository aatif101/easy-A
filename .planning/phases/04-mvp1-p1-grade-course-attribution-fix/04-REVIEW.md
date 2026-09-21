---
phase: 04-mvp1-p1-grade-course-attribution-fix
reviewed: 2026-09-21T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/easy_a/grades/ingest.py
  - src/easy_a/grades/parser.py
  - src/easy_a/quality/checks.py
  - tests/grades/test_ingest.py
  - tests/grades/test_parser.py
  - tests/quality/test_checks.py
  - tests/test_grade_course_attribution.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-09-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the grade-course-attribution fix: `GradeDistribution.course_id` is now resolved via
`resolve_course_id` and written on both insert and update, course resolution happens atomically
for the whole workbook before any `GradeDistribution` mutation (`GradeCourseResolutionError`),
blank grade/total count cells in the workbook now fail closed instead of silently defaulting to
`0`, and a new `unattributed_grade_row` quality finding flags any stored row with a null
`course_id`.

Traced the full path: `parser.parse_grade_dataframe` → `ingest._resolve_grade_course_ids` →
`ingest.upsert_grade_distributions` → `_new_grade_distribution` / `_apply_grade_distribution` /
`_grade_distribution_differs`, and the new `quality.checks._check_grades` finding. The
all-or-nothing resolution is staged strictly before any `session.add()`/mutation of
`GradeDistribution`, so a `GradeCourseResolutionError` cannot leave partial writes (verified no
`GradeDistribution` objects are added prior to `_resolve_grade_course_ids` running to completion).
`_grade_distribution_differs` correctly includes `course_id` in its diff, which is what makes the
"same content, re-import backfills a previously-null course_id" case (tested explicitly) actually
update instead of silently no-op forever — this was the root cause the phase set out to fix, and
it is fixed correctly for both the insert and backfill-on-reimport paths.

Ran `pytest`, `ruff check`, and `mypy` against the three source files under review; all pass
(32/32 relevant tests green, no lint/type errors). Traced exception handling in `ingest_grade_file`
across all four except branches (`GradeWorkbookValidationError`, `GradeCourseResolutionError`,
`(GradeWorkbookSchemaError, TermParseError)`) and confirmed `records_seen`/`records_failed`
bookkeeping is correct in each case, including the case where `records` was never assigned before
the exception fired.

No critical or warning-level defects found in the diff itself. Two minor, non-blocking
observations below.

## Info

### IN-01: Unused module-level constant `GRADE_COUNT_FIELDS`

**File:** `src/easy_a/grades/parser.py:13-24`
**Issue:** `GRADE_COUNT_FIELDS` (a bucket-letter → model-field-name mapping) is defined but never
referenced anywhere in `src/` or `tests/` (confirmed via repo-wide grep). It predates this phase
but sits directly inside a file this phase modified twice (blank-cell fail-closed change), and is
easy to miss as dead weight since it looks like it should back `GRADE_BUCKETS` iteration in
`parse_grade_dataframe` — it doesn't; that function inlines its own count assembly instead.
**Fix:** Remove `GRADE_COUNT_FIELDS`, or if it's meant to replace the ad hoc `counts["A"]` /
`counts["B"]` ... wiring in `parse_grade_dataframe`'s record construction, wire it in and add a
regression test that would fail if the two ever drift.

### IN-02: Malformed section identifiers are silently dropped with no quality-check counterpart

**File:** `src/easy_a/grades/parser.py:160-163`
**Issue:** In `parse_grade_dataframe`, any row whose `course` cell isn't a campus-header row and
doesn't match `_SECTION_IDENTIFIER_RE` is silently skipped (`except SectionIdentifierParseError:
continue`) — it is never counted in `records_seen`, never surfaces as a `GradeRowValidationError`,
and produces no trace in the resulting `IngestRun`. This is pre-existing and by design for known
non-data rows (subtotal/total rows, confirmed by
`test_grade_workbook_ignores_hierarchy_and_total_rows`), but it sits right next to the phase's new
fail-closed philosophy for blank count cells (`_cell_to_int` now raises rather than silently
defaulting to `0`, specifically to avoid an "unverified assumption" per D-06/D-07). A genuine data
row with an unexpected/malformed section-identifier format (e.g. a InfoCenter export variant this
regex doesn't anticipate) would be dropped just as silently as an intentional total row, with zero
signal that a row was lost — the opposite of the fail-closed posture just adopted for blank counts
in the same function.
**Fix:** Not required for this phase (unchanged code, not the phase's stated scope), but worth a
follow-up: emit a low-severity finding/count (e.g. `rows_skipped_unrecognized`) distinguishing
"recognized non-data row" (campus header) from "row failed to parse as either a campus header or a
section identifier," so an unexpected format degrades visibly instead of silently.

---

_Reviewed: 2026-09-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
