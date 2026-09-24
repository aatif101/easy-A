---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
plan: 02
subsystem: testing
tags: [d21, grade-coverage, sqlalchemy, honest-coverage, req-grades-01]

requires:
  - phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782
    provides: full-scale 3,783-section Tampa ingest and the existing
      scripts/validate_tampa_ingest.py suffix-exact/reconciliation/honest-coverage checks
      this plan extends
provides:
  - "scripts/inventory_tampa_grades.py: a read-only, full-term D-21 grade-coverage CLI
    that classifies every stored section into exactly one of nine named states
    (evidence_backed, exception_non_letter_grade, exception_no_rows, or a named
    integrity failure), emits a per-section exception list with a fixed non-inventive
    reason note, and a d21_grade_coverage PASS/FAIL verdict"
  - "scripts/validate_tampa_ingest.py's assert_honest_coverage() amended to accept a
    stored-evidence-proven non-letter-grade course/effective_n=0 row as a listed D-21
    exception (returns the verified count) while still failing every other zero-sample
    course-backed claim"
  - "A real PASS/PASS D-21 verdict against hosted Supabase term 202701, recorded
    verbatim below, for 08-04's REQ-GRADES-01 verification report to consume"
affects: [08-03-ui-presentation, 08-04-end-to-end-verification]

actuals:
  tokens: 16140
  tasks: 3
  commits: 3
plan_head_before: 7cbc24d965b124c341e60c53cfe4daa07737d655

tech-stack:
  added: []
  patterns:
    - "One-session, fixed-statement-count reads (sections+course, cache rows, grouped
      grade aggregates) grouped by course key exactly like _course_ids in
      analytics/queries.py, proven independent of course count by a 2-course-vs-6-course
      statement-count regression test"
    - "Cache rows built through the real refresh_section_rankings in every classification
      test, not hand-constructed, so the total_grade_count reconciliation invariant is
      proven against production code"
    - "write_atomic(path, text): temp file in the same directory + os.replace, so an
      interrupted --exceptions-md write leaves the previous file or none, never a
      truncated list"
    - "Fixed, non-inventive reason notes: no_rows and non_letter_grade each carry one
      constant string across every exception of that category (D-06/D-07) -- never a
      narrower or invented cause"

key-files:
  created:
    - scripts/inventory_tampa_grades.py
    - tests/refresh/test_inventory_tampa_grades.py
  modified:
    - scripts/validate_tampa_ingest.py
    - tests/refresh/test_validate_tampa_ingest.py

key-decisions:
  - "evidence_backed requires attributed A-F-weighted rows for the exact course key plus
    reconciliation of the cached historical_analytics.total_grade_count against the
    key's persisted total_grades sum (course: exact equality; instructor_course: in
    (0, key sum]) -- a numeric score alone is never treated as proof of own-course
    history (D-20, D-21)."
  - "assert_honest_coverage's exception is narrowly scoped: only score_source=course,
    effective_n=0, with stored rows proving A-F sum 0 and total_grades sum > 0 for that
    exact course key. Every other effective_n<=0 course/instructor_course claim, every
    subject row with effective_n=0, and every course row whose key actually has
    letter-grade history still raises the original D-20 AssertionError naming the CRN."
  - "The interrupted plan was resumed by verification only: re-ran every <verify> and
    <acceptance_criteria> command in 08-02-PLAN.md against the three already-committed
    task commits (4940b00, 55f8276, 87cd996) rather than redoing the work. No code
    change was needed -- every criterion passed on first re-run."

requirements-completed: [REQ-GRADES-01]

coverage:
  - id: D1
    description: "scripts/inventory_tampa_grades.py classifies every stored 202701
      section into exactly one D-21 state and reports a d21_grade_coverage verdict that
      is PASS only when there are zero integrity failures and every non-evidence-backed
      section is a listed exception"
    requirement: REQ-GRADES-01
    verification:
      - kind: unit
        ref: "tests/refresh/test_inventory_tampa_grades.py -q (22 passed)"
        status: pass
      - kind: e2e
        ref: "uv run python scripts/inventory_tampa_grades.py --term 202701"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every non-evidence-backed section carries a fixed, non-inventive
      reason_note (no_rows or non_letter_grade) identical across every exception of that
      category; --exceptions-md writes atomically"
    requirement: REQ-GRADES-01
    verification:
      - kind: unit
        ref: "tests/refresh/test_inventory_tampa_grades.py#test_no_rows_reason_note_identical_across_every_no_rows_exception"
        status: pass
    human_judgment: false
  - id: D3
    description: "scripts/validate_tampa_ingest.py's honest-coverage check agrees with
      D-21: a stored-evidence-proven non-letter-grade course/effective_n=0 row is a
      listed exception, but every other zero-sample course-backed claim still fails"
    requirement: REQ-GRADES-01
    verification:
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py -q (12 passed)"
        status: pass
      - kind: e2e
        ref: "uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml"
        status: pass
    human_judgment: false

duration: ~35min (this continuation session; prior session's task work not separately timed)
completed: 2026-09-24
status: complete
---

# Phase 08 Plan 02: D-21 Grade Coverage Inventory Summary

**Read-only D-21 inventory CLI (`scripts/inventory_tampa_grades.py`) that classifies all
3,783 Spring 2027 Tampa sections into evidence_backed / listed exception / named
integrity failure, plus a D-21-aligned `assert_honest_coverage()` in the Tampa
validator; live run against hosted Supabase term 202701 returned PASS/PASS with 3,122
evidence-backed sections and 661 listed exceptions (361 no_rows + 300
non_letter_grade), matching STATE.md's D-21 baseline exactly.**

## Continuation note

This plan was executed by a prior agent across three task commits
(`4940b00`, `55f8276`, `87cd996`), then the session was interrupted before the
plan-level verification pass, SUMMARY.md and STATE/ROADMAP tracking updates. This
continuation did **not** redo or rewrite any task. It re-ran every `<verify>` command
and `<acceptance_criteria>` check in `08-02-PLAN.md` against the already-committed code
(full suite, task-scoped pytest, ruff, mypy, `--help`, `git diff --quiet origin/main --
src/easy_a`, the JSON-shape/bucket-key/verdict-sum checks, and both live commands), and
found every criterion passing on first re-run. No fix commit was needed.

## Performance

- **Duration:** ~35 min for this verification-and-summary continuation session
- **Tasks:** 3 completed (by the prior session; verified, not redone, in this one)
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments

- `scripts/inventory_tampa_grades.py` (new, 847 lines added across the three commits):
  `build_parser()`, `main(argv) -> int`, `collect_inventory(session, term) -> Inventory`,
  `classify_section(...) -> SectionState`, `EvidenceState` enum, `write_atomic(path,
  text)`, module constants `D21_WINDOW_TERMS` / `D21_CHECKED_EMPTY_TERMS`. CLI flags
  `--term` (default 202701), `--exceptions-md PATH`. Exit codes: 0 both verdicts PASS, 1
  otherwise, 3 NOT MEASURED (connection failure).
- Every section maps to exactly one of nine states: `evidence_backed`,
  `exception_non_letter_grade`, `exception_no_rows`, `missing_cache_row`,
  `unbacked_course_claim`, `raw_total_mismatch`, `history_not_used`,
  `global_nonzero_effective_n`, `unclassified`. `evidence_backed` requires
  score_source course/instructor_course, effective_n > 0, attributed A-F-weighted rows
  for the exact course key, and reconciliation of the cached `total_grade_count`
  against the key's persisted `total_grades` sum -- proven against the real
  `refresh_section_rankings` in tests, not a hand-built cache row.
- Fixed, non-inventive reason notes: every `no_rows` exception and every
  `non_letter_grade` exception carries one constant note text (never a narrower or
  invented cause -- D-06, D-07), verified by a dedicated identity test.
- Term-level provenance and integrity: `grade_rows_by_term` (rows, courses,
  total_grades sum, sources, source_hash count, ingested_at range per historical
  term), a `window` block against `D21_WINDOW_TERMS`/`D21_CHECKED_EMPTY_TERMS`, and
  integrity counters (`unattributed_grade_rows`, `bucket_sum_mismatch_rows`,
  `stale_cache`, `non_tampa_section_count`).
- `--exceptions-md PATH` renders a deterministic Markdown table (sorted by subject,
  course_number, crn) through `write_atomic` (temp file + `os.replace`), so an
  interrupted write leaves the previous file or none.
- `scripts/validate_tampa_ingest.py`'s `assert_honest_coverage(session, term) -> int`
  now accepts a `score_source=course`, `effective_n=0` row as a verified D-21 exception
  only when the course key's stored rows prove A-F sum 0 and total_grades sum > 0; a
  new `_course_key_grade_totals()` issues one grouped query for this. Every other
  zero-sample course/instructor_course claim, and every subject row with
  `effective_n=0`, still raises the original D-20 `AssertionError` naming the CRN. `main`
  now prints `"PASS honest-coverage (verified non-letter-grade exceptions: N)"`.
- **Live run 1** -- `uv run python scripts/inventory_tampa_grades.py --term 202701`
  against hosted Supabase (exit 0, both verdicts PASS). Verbatim snapshot and verdict
  block:
  ```json
  {"gate": "d21_grade_coverage", "term": "202701",
   "observed_at_utc": "2026-09-24T17:20:12.065630+00:00", "environment": "Supabase",
   "snapshot": {"section_count": 3783, "represented_course_count": 1401,
     "cache_row_count": 3783,
     "cache_refreshed_at_min": "2026-09-23T21:51:28.116181+00:00",
     "cache_refreshed_at_max": "2026-09-23T21:51:28.116181+00:00",
     "grade_row_count": 8662,
     "grade_ingested_at_max": "2026-09-23T21:36:34.907224+00:00",
     "non_tampa_section_count": 0},
   "sections_by_state": {"evidence_backed": 3122, "exception_no_rows": 361,
     "exception_non_letter_grade": 300},
   "courses_by_state": {"evidence_backed": 1117, "exception_no_rows": 232,
     "exception_non_letter_grade": 52},
   "integrity": {"unattributed_grade_rows": 0, "bucket_sum_mismatch_rows": 0,
     "rows_at_or_after_term": 0, "stale_cache": false, "non_tampa_section_count": 0},
   "evidence_backed_sections": 3122,
   "exception_sections_by_reason": {"no_rows": 361, "non_letter_grade": 300},
   "verdicts": {"integrity": "PASS", "d21_grade_coverage": "PASS"}}
  ```
  (the `exceptions` array itself has 661 entries, sorted subject/course/crn, each
  carrying its fixed reason_note; `grade_rows_by_term` and `window` omitted here for
  length -- see the plan's must_haves for their shape.) This is an **exact match** to
  the plan's live baseline (3,122 evidence-backed; 661 = 311 subject + 50 global +
  300 course/effective_n=0) and to STATE.md's recorded D-21 figures. No bucket-letter
  keys (`a_count`..`w_count`) appear anywhere in the JSON output (the one substring
  hit on `w_count` is `cache_row_count`, verified by direct string-context inspection).
- **Live run 2** -- `uv run python scripts/validate_tampa_ingest.py --term 202701
  --targets config/course_targets.toml` against hosted Supabase (exit 0):
  ```
  PASS suffix-exact
  PASS reconciliation
  PASS honest-coverage (verified non-letter-grade exceptions: 300)
  ```
  The validator's verified count (300) equals the inventory's
  `exception_non_letter_grade` count (300) exactly, satisfying the plan's key_links
  contract between the two scripts.
- Full suite (re-run in this continuation): **366 passed, 3 skipped** (matches the
  prior session's reported 366/3; +26 tests since Phase 08-01's 340/3 baseline: 22 in
  `test_inventory_tampa_grades.py`, plus the 4 new honest-coverage tests folded into
  `test_validate_tampa_ingest.py`'s existing 12). `ruff check` and `mypy` clean on all
  four files. `git diff --quiet origin/main -- src/easy_a` exits 0 -- no production
  scoring/cache/API/schema code touched (D-02).

## Task Commits

Each task was committed atomically by the prior session:

1. **Task 1: Trace one course key from hosted rows to a classified JSON record** -
   `4940b00` (feat) -- `scripts/inventory_tampa_grades.py`,
   `tests/refresh/test_inventory_tampa_grades.py`
2. **Task 2: Classify every D-21 state and emit the exception list** - `55f8276`
   (feat) -- both files extended
3. **Task 3: Encode D-21's non-letter-grade exception in the validator's
   honest-coverage check** - `87cd996` (feat) -- `scripts/validate_tampa_ingest.py`,
   `tests/refresh/test_validate_tampa_ingest.py`

**Plan metadata:** commit pending below (this SUMMARY + STATE/ROADMAP/REQUIREMENTS).

## Files Created/Modified

- `scripts/inventory_tampa_grades.py` - the D-21 grade-coverage inventory CLI (new)
- `tests/refresh/test_inventory_tampa_grades.py` - 22 tests covering every named
  state, the verdict contract, the reason-note identity invariant, the
  fixed-statement-count regression, and the exceptions-md/atomic-write path (new)
- `scripts/validate_tampa_ingest.py` - `assert_honest_coverage` amended to accept the
  evidence-proven non-letter-grade exception; new `_course_key_grade_totals` (modified)
- `tests/refresh/test_validate_tampa_ingest.py` - 4 new tests for the verified
  exception, letter-grade-present rejection, subject-zero rejection and
  instructor_course-zero rejection (modified)

## Decisions Made

See `key-decisions` in frontmatter. In summary: evidence_backed requires both
attributed letter-grade weight and raw-total reconciliation against a cache built by
the real refresh path (not a numeric score alone); the honest-coverage exception is
scoped as narrowly as D-21 allows (course-only, effective_n exactly 0, stored A-F sum
0 with total > 0); and this session's own scope was verification-only, per the
orchestrator's explicit instruction not to redo committed task work.

## Deviations from Plan

None - all three tasks were executed exactly as planned by the prior session, and
every `<verify>` command and `<acceptance_criteria>` check in `08-02-PLAN.md` passed
on direct re-run in this continuation with no code changes required.

## Issues Encountered

The executing session was interrupted after Task 3's commit, before plan-level
verification, SUMMARY.md and STATE/ROADMAP updates. Resolved by this continuation:
independently re-ran every acceptance criterion and both live commands (inventory CLI
and validator) against the committed code, confirmed all pass, and completed the
plan's closing steps.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `scripts/inventory_tampa_grades.py`'s live PASS/PASS verdict and full JSON payload
  (snapshot, grade_rows_by_term, window, sections_by_state, courses_by_state,
  integrity, evidence_backed_sections, exception_sections_by_reason, exceptions,
  verdicts) are ready for 08-03 (UI presentation) and 08-04 (end-to-end verification
  report / `08-D21-EXCEPTIONS.md`) to consume.
- The validator's verified non-letter-grade exception count (300) is proven to equal
  the inventory's `exception_non_letter_grade` count (300), satisfying the plan's
  cross-script key_links contract ahead of 08-04.
- No blockers. `src/easy_a` untouched; no scoring, cache, API or schema change.
- Full suite: 366 passed / 3 skipped (was 340/3 at Phase 08-01's close; +26 net new
  tests this plan, 0 regressions).

---
*Phase: 08-mvp1-p5-end-to-end-mvp-1-verification*
*Completed: 2026-09-24*

## Self-Check: PASSED

- FOUND: scripts/inventory_tampa_grades.py
- FOUND: tests/refresh/test_inventory_tampa_grades.py
- FOUND: scripts/validate_tampa_ingest.py
- FOUND: tests/refresh/test_validate_tampa_ingest.py
- FOUND: .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-02-SUMMARY.md
- FOUND: 4940b00 (Task 1)
- FOUND: 55f8276 (Task 2)
- FOUND: 87cd996 (Task 3)
