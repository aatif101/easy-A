---
phase: 04-mvp1-p1-grade-course-attribution-fix
verified: 2026-09-21T00:00:00Z
status: passed
score: 8/8 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-01-PLAN.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-01-SUMMARY.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-02-PLAN.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-02-SUMMARY.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-VALIDATION.md"
  - ".planning/phases/04-mvp1-p1-grade-course-attribution-fix/deferred-items.md"
  - "src/easy_a/grades/ingest.py"
  - "src/easy_a/grades/parser.py"
  - "src/easy_a/quality/checks.py"
  - "tests/grades/test_ingest.py"
  - "tests/grades/test_parser.py"
  - "tests/quality/test_checks.py"
  - "tests/test_grade_course_attribution.py"
covered_digest: "v1:sha256:8415abcd96e9f47ba1d53125048ad7a8641348d685f64e3978993a3cfc359368"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 04: MVP1-P1 — Grade→Course Attribution Fix Verification Report

**Phase Goal:** imported historical grade distributions attach to current-term sections so
easiness is computed from real data (`effective_n > 0`), not the global fallback.
**Verified:** 2026-09-21
**Status:** passed
**Re-verification:** No — initial verification

**Note on REQ-GRADES-01:** REQUIREMENTS.md correctly marks REQ-GRADES-01 partial (◐) — full
acceptance also requires MVP1-P2 (grade data sourcing, a separate later phase). This is expected
and was verified to be honestly recorded, not overclaimed. This report verifies phase 04's own
delivered scope: the attribution mechanism, fail-closed blank-cell validation, and the
`unattributed_grade_row` quality finding.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | (Roadmap SC1) A section whose course has imported grade history reports `effective_n > 0` and a grade-derived easiness score; sections without history stay an honest `effective_n = 0` fallback | ✓ VERIFIED | `tests/test_grade_course_attribution.py::test_generated_xlsx_attribution_reaches_cached_search_without_historical_section` — ran directly, passes. Asserts `with_history_rank.effective_n > 0`, `score_source == "course"`; `no_history_rank.effective_n == 0`, `score_source == "global"` across direct rank, cache row, hydrated cache, and `GET /api/v1/rankings/search` JSON. |
| 2 | (Roadmap SC2) Term/CRN/source dedup preserved; no raw export files committed; scoring model unchanged | ✓ VERIFIED | `git ls-files -- '*.xlsx' '*.xls'` returns empty (no tracked export). `tests/grades/test_ingest.py::test_duplicate_grade_ingestion_is_idempotent` and `test_same_key_reimport_backfills_null_course_id_without_duplicate` ran and pass. `src/easy_a/analytics/`, rankings scoring, and API routes are untouched by this phase's diffs (confirmed by `files_modified` in both PLANs and by source read). |
| 3 | A generated historical XLSX row resolves to the canonical `Course.id` and contributes real evidence to a 202701 section even when no matching historical Section exists (D-04, D-20) | ✓ VERIFIED | `tests/test_grade_course_attribution.py` deliberately omits a 202408 `Section` for CRN 89033; test asserts `grade.course_id == mac.id` via `resolve_course_id()`. Ran and passes. |
| 4 | Every distinct parsed course key is resolved before any `GradeDistribution` mutation; unresolved keys fail the workbook atomically and are all named in the failure (D-04, D-06, D-07) | ✓ VERIFIED | `src/easy_a/grades/ingest.py::_resolve_grade_course_ids()` resolves all distinct keys before the mutation loop in `upsert_grade_distributions()`; `tests/grades/test_ingest.py::test_missing_courses_fail_atomically_and_report_all_keys` ran and passes, asserting zero persisted `GradeDistribution` rows and all unresolved keys reported. |
| 5 | A same-term/CRN/source re-import repairs a null `course_id` in place, updates the row once, preserves `source_hash`, and never creates a duplicate (D-04) | ✓ VERIFIED | `tests/grades/test_ingest.py::test_same_key_reimport_backfills_null_course_id_without_duplicate` ran and passes: `records_inserted == 0`, `records_updated == 1`, one persisted row, `course_id` repaired, `source_hash` preserved. `_grade_distribution_differs()` includes `course_id` in its diff. |
| 6 | A blank canonical A/B/C/D/F/I/S/U/W/O or Total Grades cell rejects the workbook with row, column, and unverified-semantics context; explicit numeric zero remains valid (D-06, D-07) | ✓ VERIFIED | `src/easy_a/grades/parser.py::_cell_to_int()` raises via `_blank_count_cell_message()` on `_is_empty_cell()`/stripped-empty text. `tests/grades/test_parser.py::test_blank_bucket_count_fails_closed`, `test_blank_total_fails_closed`, `test_explicit_zero_count_succeeds` ran and pass; message contains row, column name, "unverified", and explicitly does not assert "suppressed the value". |
| 7 | Data quality emits one deterministic error finding for each stored `GradeDistribution` whose `course_id` is null, while attributed rows do not receive that finding (D-04, D-07) | ✓ VERIFIED | `src/easy_a/quality/checks.py::_check_grades()` appends an `unattributed_grade_row` error `QualityFinding` for every row with `course_id is None`. `tests/quality/test_checks.py::test_unattributed_grade_row_is_an_error` and `test_attributed_grade_row_has_no_unattributed_finding` ran and pass. |
| 8 | Parser and quality hardening, and grade-course attribution, do not alter scoring, term/CRN/source identity, provenance, the analytics fallback, or the rankings API (D-02, D-04) | ✓ VERIFIED | `(term_id, crn, source)` unique identity unchanged in `src/easy_a/models/core.py` (not modified by either plan). `src/easy_a/analytics/`, `src/easy_a/rankings/`, and `src/easy_a/api/routes/rankings.py` are absent from both plans' `files_modified` and unmodified per source read. Full suite (261 passed / 3 skipped) confirms no regression. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/easy_a/grades/ingest.py` | Canonical course preflight and course_id-aware term/CRN/source upsert | ✓ VERIFIED | `GradeCourseResolutionError`, `_resolve_grade_course_ids()` present; `_new_grade_distribution`, `_apply_grade_distribution`, `_grade_distribution_differs` all take/propagate `course_id`. |
| `tests/test_grade_course_attribution.py` | Generated-XLSX → ingest → analytics → 202701 cache → search vertical proof | ✓ VERIFIED | Present, substantive (215 lines), exercises full path incl. FastAPI TestClient; ran and passes. |
| `tests/grades/test_ingest.py` | Attribution, backfill, atomic failure, deduplication, provenance regression coverage | ✓ VERIFIED | Contains all named tests; ran and passes (7 tests incl. CLI). |
| `src/easy_a/grades/parser.py` | Fail-closed canonical grade-count cell validation | ✓ VERIFIED | `_cell_to_int()` raises on blank; `_blank_count_cell_message()` present. |
| `tests/grades/test_parser.py` | Blank bucket/total rejection and explicit-zero acceptance coverage | ✓ VERIFIED | All 3 new tests present and passing; old blank-as-zero test removed as planned. |
| `src/easy_a/quality/checks.py` | `unattributed_grade_row` quality invariant | ✓ VERIFIED | Present inside `_check_grades()` distribution loop. |
| `tests/quality/test_checks.py` | Attributed/null-attributed quality finding controls | ✓ VERIFIED | Both tests present and passing. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `src/easy_a/grades/ingest.py` | `src/easy_a/common/lookups.py` | `resolve_course_id()` for every distinct parsed key before upsert | ✓ WIRED | `_resolve_grade_course_ids()` imports and calls `resolve_course_id` per distinct `(subject, course_number)` key, before the mutation loop. |
| `src/easy_a/grades/ingest.py` | `src/easy_a/models/core.py` | resolved `Course.id` persisted on `GradeDistribution.course_id` | ✓ WIRED | `course_id` set on insert (`_new_grade_distribution`) and update (`_apply_grade_distribution`); `(term_id, crn, source)` identity untouched. |
| `tests/test_grade_course_attribution.py` | `src/easy_a/rankings/cache.py` | `refresh_section_rankings(session, term="202701")` after import | ✓ WIRED | Called directly in test; cache rows verified with correct `effective_n`/`score_source`. |
| `tests/test_grade_course_attribution.py` | `src/easy_a/api/routes/rankings.py` | `GET /api/v1/rankings/search` reads rebuilt cache | ✓ WIRED | `TestClient` call in test; response JSON asserted for both CRNs. |
| `src/easy_a/grades/parser.py` | `src/easy_a/grades/ingest.py` | `GradeWorkbookValidationError` aborts before attribution preflight/upsert | ✓ WIRED | `ingest_grade_file()` catches `GradeWorkbookValidationError` and marks the run failed before `upsert_grade_distributions()` runs. |
| `src/easy_a/quality/checks.py` | `src/easy_a/models/core.py` | `_check_grades` inspects `GradeDistribution.course_id` without inferring from CRN | ✓ WIRED | `if distribution.course_id is None:` — no CRN-based inference present. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `effective_n` / `score_source` in `/api/v1/rankings/search` | ranking cache row | `GradeDistribution.course_id.in_(course_ids)` real SQL query in `src/easy_a/analytics/queries.py` (`_fetch_course_grade_observations`) | Yes | ✓ FLOWING |
| `GradeDistribution.course_id` | ORM field | `resolve_course_id()` → real `SELECT Course.id ... WHERE subject/number` query in `src/easy_a/common/lookups.py` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks / Test Execution

Ran the phase's own pytest targets directly (not trusting SUMMARY claims):

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase-focused targeted tests | `uv run pytest -q tests/test_grade_course_attribution.py tests/grades/test_ingest.py tests/grades/test_parser.py tests/quality/test_checks.py` | 32 passed | ✓ PASS |
| Full suite (once) | `uv run pytest -q` | 261 passed, 3 skipped | ✓ PASS (matches SUMMARY claim) |
| No tracked raw/generated exports (D-19) | `git ls-files -- '*.xlsx' '*.xls'` | empty output | ✓ PASS |
| Ruff on phase-modified files | `uv run ruff check .` | 1 pre-existing violation in `src/easy_a/refresh/cleanup.py:494` (unmodified by this phase, confirmed via `git log`, documented in `deferred-items.md`) | ✓ PASS (no violation in phase files) |
| Strict mypy on phase-modified files | `uv run mypy src/easy_a/grades/ingest.py src/easy_a/grades/parser.py src/easy_a/quality/checks.py tests/grades/test_ingest.py tests/grades/test_parser.py tests/quality/test_checks.py tests/test_grade_course_attribution.py` | Success: no issues found in 7 source files | ✓ PASS |

`EASY_A_TEST_POSTGRES_URL` is not set in this environment; the PostgreSQL-configured path was not
run, consistent with D-12 and the phase's own honest reporting in both SUMMARYs and
`04-VALIDATION.md`'s Manual-Only Verifications table. This is not a phase-04 gap — it is an
environment-gated check the phase explicitly could not run and did not claim to have run.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| REQ-GRADES-01 | 04-01, 04-02 | Ingested Tampa courses have real historical grade data; easiness computed from it | ◐ PARTIAL (expected, correctly recorded) | Phase 04's own scope (attribution mechanism, fail-closed blank-cell validation, `unattributed_grade_row` finding) is fully delivered and verified above. REQUIREMENTS.md explicitly and correctly still marks this ◐ pending MVP1-P2 (grade data sourcing) — no overclaiming found. |

No orphaned requirements: REQ-GRADES-01 is the only requirement mapped to Phase 04 in
REQUIREMENTS.md, and both plans declare it.

### Anti-Patterns Found

None in phase-modified files. Grepped `src/easy_a/grades/ingest.py`, `src/easy_a/grades/parser.py`,
and `src/easy_a/quality/checks.py` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and
placeholder/stub language — zero matches.

One pre-existing, out-of-scope issue noted for completeness (not a phase-04 blocker):

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/easy_a/refresh/cleanup.py` | 494 | Ruff `E501` line-too-long | ℹ️ Info | Pre-existing, predates both phase-04 commits (`git log` confirms last touch at `0c0f0c9`, before `d45fda9`/`1dac70d`), not in either plan's `files_modified`, correctly logged in `deferred-items.md`. Does not affect phase goal. |

Code review (`04-REVIEW.md`) independently found 0 critical/warning findings and 2 info-level
observations (unused `GRADE_COUNT_FIELDS` constant; pre-existing silent-drop of malformed section
identifiers) — both explicitly out of this phase's scope and non-blocking.

### Human Verification Required

None. All must-haves are verified by direct source inspection and by pytest runs executed in this
verification pass (not merely SUMMARY claims).

### Gaps Summary

No gaps found. All 8 merged must-haves (2 roadmap success criteria + 6 PLAN-frontmatter truths
after dedup) are verified against source code and passing test runs executed directly by this
verifier. Term/CRN/source dedup, atomic preflight, null-row backfill, blank-cell fail-closed
policy, and the `unattributed_grade_row` quality finding are all present, wired, and behaviorally
proven. No raw/generated grade export files are tracked in Git. Scoring model, analytics fallback,
and rankings API are unmodified by this phase. REQ-GRADES-01 is honestly and correctly recorded as
partial in REQUIREMENTS.md, consistent with D-06/D-07/D-20 (no unsupported completion claim) — this
is expected given the phase's declared scope, not a gap.

---

_Verified: 2026-09-21_
_Verifier: Claude (gsd-verifier)_
