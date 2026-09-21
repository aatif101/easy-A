---
phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782
plan: 01
subsystem: data-pipeline
tags: [pydantic, sqlalchemy, csv, toml, ingestion, tdd]

# Dependency graph
requires:
  - phase: 05-mvp1-p2-historical-grade-sourcing
    provides: 10 pilot courses with course-backed Fall 2024 grade history on hosted Supabase
provides:
  - scripts/generate_tampa_targets.py — reproducible courses.csv -> config/course_targets.toml generator
  - config/course_targets.toml regenerated to the full ~1,402-course Tampa universe (git-tracked)
  - Proven end-to-end ingestion path (catalog + schedule + suffix guard + honest-coverage contract)
    for one full subject (CHM, 23 courses / 295 sections) against live hosted Supabase
  - Suffix guard (_retain_exact_course_rows) proven generic across 4 base/suffix pairs, not CHM-specific
affects: [06-02-all-tampa-batch-ingestion, 06-03-validation]

# Actuals (#2632)
actuals:
  tokens: 21882
  tasks: 2
  commits: 7

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config-generator script mirrors catalog/cli.py's build_parser()/main(argv)->int shape and reuses CourseTarget/CourseTargets validation instead of hand-rolled regex/dedup."
    - "Composite tuple_(col_a, col_b).in_([...]) IN-clause instead of an OR-of-AND expression tree, for filters that must scale past ~1,000 configured targets on SQLite."
    - "Isolated small pilot-scale CourseTargets fixtures in tests, rather than depending on the ambient default config/course_targets.toml's cardinality."

key-files:
  created:
    - scripts/generate_tampa_targets.py
    - scripts/__init__.py
    - tests/refresh/test_generate_targets.py
  modified:
    - config/course_targets.toml
    - src/easy_a/refresh/cleanup.py
    - tests/refresh/test_targets.py
    - tests/refresh/test_coverage_suffix_guard.py
    - tests/api/test_rankings_api.py

key-decisions:
  - "Reconciled config/course_targets.toml to the full ~1,402-entry generated list (locked decision 1), replacing the 5-entry pilot config as the git-tracked source of truth."
  - "Fixed src/easy_a/refresh/cleanup.py's _target_filter to a single composite tuple_(...).in_(...) clause instead of an OR-of-AND tree, after the full-scale config tripped SQLite's expression-tree depth limit (1000) in an existing test."
  - "Decoupled pilot-scale tests (tests/refresh/test_targets.py, tests/api/test_rankings_api.py) from the ambient default config's cardinality via local 5-course CourseTargets fixtures, rather than editing the tests' original intent."

patterns-established:
  - "generate_tampa_targets.py: read CSV -> CourseTarget per row -> CourseTargets(...) -> let pydantic validation raise uncaught, matching load_targets' own surface-directly behavior."

requirements-completed: [REQ-COVERAGE-03]

coverage:
  - id: D1
    description: "scripts/generate_tampa_targets.py reproducibly builds config/course_targets.toml from courses.csv, validating every row against CourseTarget/CourseTargets before writing (count, base/suffix separation, malformed-row rejection, duplicate rejection, determinism)."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: unit
        ref: "tests/refresh/test_generate_targets.py (7 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "config/course_targets.toml is git-tracked, loads via load_targets() without error, and holds >=1400 targets with CHM 2045 and CHM 2045L as separate entries."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: unit
        ref: "uv run python -c \"from easy_a.refresh.targets import load_targets; ...\" -> 1402"
        status: pass
    human_judgment: false
  - id: D3
    description: "CHM ingested end-to-end into hosted Supabase (23 courses, 295 sections) via the unmodified refresh_course_coverage.py --subject CHM: catalog + schedule ingest, suffix guard, Tampa scope guard, ranking cache refresh, 0 quality errors, 0 non-Tampa rows."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: integration
        ref: "uv run python scripts/refresh_course_coverage.py --term 202701 --targets config/course_targets.toml --subject CHM (live hosted Supabase) -> Quality errors: 0"
        status: pass
      - kind: integration
        ref: "uv run python scripts/check_data_quality.py --term 202701 --json (live hosted Supabase) -> 590 findings, 0 errors"
        status: pass
    human_judgment: false
  - id: D4
    description: "CHM 2045 (5 sections) and CHM 2045L (40 sections) resolve to their own separate course_number with no cross-leak; newly ingested CHM courses report score_source=global/effective_n=0 (D-20 honest fallback), the 10 pilot courses keep score_source=course."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: integration
        ref: "ad hoc SELECT on Section/Course + rank_section() spot-check against live DB (documented in this SUMMARY's Accomplishments)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Suffix guard (_retain_exact_course_rows) generalizes beyond the single CHM 2045 fixture, proven at the unit level across 4 base/suffix pairs; src/easy_a/refresh/coverage.py has zero diff."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: unit
        ref: "tests/refresh/test_coverage_suffix_guard.py (8 parametrized tests)"
        status: pass
      - kind: unit
        ref: "git diff --exit-code -- src/easy_a/refresh/coverage.py"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-09-21
status: complete
---

# Phase 06 Plan 01: All-Tampa Ingestion Tracer Summary

**Generated the full ~1,402-course `config/course_targets.toml` from `courses.csv` and proved the unmodified catalog+schedule ingestion path, suffix guard, and honest-coverage contract end-to-end on CHM (23 courses / 295 sections) against live hosted Supabase, with 0 quality errors.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-09-21T21:14:33Z
- **Completed:** 2026-09-21T21:44:40Z
- **Tasks:** 2 completed
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- `scripts/generate_tampa_targets.py` reproducibly rebuilds `config/course_targets.toml` from `courses.csv`, reusing `CourseTarget`/`CourseTargets` Pydantic validation unmodified (no hand-rolled regex/dedup logic). TDD RED-then-GREEN: `tests/refresh/test_generate_targets.py` was committed failing first (generator didn't exist), then the generator was implemented to make it pass.
- `config/course_targets.toml` regenerated and committed with 1,402 targets (>= 1400), reconciling the prior 5-entry pilot config and the 10 stored pilot courses into the full Tampa universe (locked decision 1). CHM 2045 and CHM 2045L are separate entries, confirming no base/suffix collapsing.
- Live tracer: `refresh_course_coverage.py --term 202701 --targets config/course_targets.toml --subject CHM` ingested all 23 CHM courses / 295 Tampa sections against hosted Supabase — "Missing targets: 0", "Quality errors: 0". `check_data_quality.py --term 202701 --json` independently confirmed 590 findings, 0 errors, against a term total of 427 sections (132 pilot + 295 CHM), 0 non-Tampa.
- Suffix-guard spot-check: CHM 2045 resolved to exactly 5 sections and CHM 2045L to exactly 40 sections with no cross-leak (`_retain_exact_course_rows` proven correct at full CHM scale, unmodified).
- Honest-coverage spot-check: a fresh CHM 2045 section reports `score_source=global` / `effective_n=0.0` (D-20 compliant — no fabricated history), while pilot course MAC 1105 keeps `score_source=course` / `effective_n=1102.0` unchanged.
- Task 2 generalized the suffix-guard regression test beyond the single CHM fixture: parametrized over 4 representative base/suffix pairs (CHM 2045/2045L, BSC 2010/2010L, PHY 2049/2049L, APK 3125/3125L) drawn from the 33 base courses in `courses.csv` that have an L-variant. `src/easy_a/refresh/coverage.py` has zero diff throughout the plan.

## Task Commits

Each task was committed atomically (Task 1 used TDD, producing multiple commits per the plan's `tdd="true"` requirement):

1. **Task 1 (RED):** add failing tests for the Tampa target generator — `2020173` (test)
2. **Task 1 (GREEN):** implement the generator — `284e987` (feat)
3. **Task 1 (data):** regenerate and commit the full `config/course_targets.toml` — `572302e` (feat)
4. **Task 1 (deviation, Rule 1):** scale `cleanup.py`'s target filter for the full config — `b542896` (fix)
5. **Task 1 (deviation, Rule 3):** make `scripts/` an importable package for mypy — `ad5eaa4` (fix)
6. **Task 1 (deviation, Rule 1):** decouple pilot-scale tests from the full default config — `6838cda` (fix)
7. **Task 2:** generalize the suffix-guard regression test beyond CHM — `d27dbd0` (test)

**Plan metadata:** committed as part of this Summary + STATE.md update (see final commit below).

_Note: Task 1 (`tdd="true"`) has multiple commits per the RED -> GREEN -> deviation pattern; the live CHM ingestion itself (against hosted Supabase) is not a git-tracked artifact and has no separate commit — it is verified via the DB spot-checks and quality-CLI output documented above._

## Files Created/Modified

- `scripts/generate_tampa_targets.py` - Generator: `build_parser()`/`main(argv)->int`, `--csv`/`--out`/`--catalog-edition` flags, reuses `CourseTarget`/`CourseTargets` validation, deterministic TOML rendering.
- `scripts/__init__.py` - Empty; makes `scripts/` an importable package so mypy resolves `scripts.generate_tampa_targets` consistently with the test's dotted import (mypy's own suggested fix for a "found twice" module conflict).
- `tests/refresh/test_generate_targets.py` - 7 tests covering count/metadata preservation, base+suffix separation, malformed-row rejection (4 parametrized cases), duplicate rejection, determinism, and a `load_targets()` round-trip.
- `config/course_targets.toml` - Regenerated: 1,402 targets (was 5), CHM 2045/2045L present as separate entries, `catalog_edition`/`catalog_url_template` preserved exactly.
- `src/easy_a/refresh/cleanup.py` - `_target_filter` changed from an OR-of-AND expression tree to a single composite `tuple_(Course.subject, Course.number).in_(...)` clause, fixing a SQLite expression-tree depth-limit failure at 1,402 targets.
- `tests/refresh/test_targets.py` - Added `_pilot_config()`/`_write_pilot_targets_file()` helpers; several tests that called `load_targets()` (ambient default) now build/pass an isolated 5-course pilot config so their assertions stay meaningful at the new default cardinality.
- `tests/api/test_rankings_api.py` - `test_seat_freshness_and_coverage_api` now monkeypatches `easy_a.api.routes.metadata.load_targets` to a 5-course pilot config for its `/api/v1/metadata/coverage` assertions.
- `tests/refresh/test_coverage_suffix_guard.py` - Parametrized over 4 base/suffix pairs via generalized `_course_config`/`_mixed_response` helpers (was CHM-only `_chm_config`/`_mixed_chm_response`).

## Decisions Made

- Regenerated `config/course_targets.toml` in place as the full ~1,402-entry git-tracked source of truth, per the plan's locked decision 1, rather than keeping it pilot-sized with a separate `--targets` override file.
- Fixed the SQLite expression-tree depth-limit failure in `cleanup.py` with a composite `tuple_(...).in_(...)` IN-clause rather than working around it in the test — this is the correct scale-safe form of the same filter and works identically on PostgreSQL.
- Added `scripts/__init__.py` (mypy's own suggested resolution) rather than reconfiguring `[tool.mypy]` project-wide (`explicit_package_bases`), which surfaced unrelated pre-existing errors in `tests/test_database_config.py` when tried.
- Built isolated pilot-scale `CourseTargets` fixtures in tests rather than changing what those tests exercise, preserving each test's original intent and assertions unchanged in substance.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `cleanup.py`'s `_target_filter` broke at full config scale (SQLite expression-tree depth limit)**
- **Found during:** Task 1, running the plan-level `<verification>` suite (`uv run pytest tests/refresh/ tests/catalog/ tests/schedule/ -q`) after regenerating `config/course_targets.toml` to 1,402 entries.
- **Issue:** `_target_filter` built `or_(*(and_(...) for item in targets))` — one AND clause per configured target. At 1,402 targets this exceeded SQLite's expression-tree depth limit (1000), failing `tests/refresh/test_cleanup.py::test_cli_dry_run_json_does_not_write` with `sqlite3.OperationalError: Expression tree is too large`.
- **Fix:** Replaced with `tuple_(Course.subject, Course.number).in_([(item.subject, item.number) for item in targets])` — a single composite IN-clause, semantically identical, scales correctly on both SQLite and PostgreSQL.
- **Files modified:** `src/easy_a/refresh/cleanup.py`
- **Verification:** `uv run pytest tests/refresh/test_cleanup.py -q` (17 passed, 1 skipped); `uv run mypy src/easy_a/refresh/cleanup.py` clean.
- **Committed in:** `b542896`

**2. [Rule 3 - Blocking] mypy "Source file found twice" for `scripts/generate_tampa_targets.py`**
- **Found during:** Task 1, running `uv run mypy src migrations scripts tests` (README's documented invocation) after adding `tests/refresh/test_generate_targets.py`'s `from scripts.generate_tampa_targets import ...` dotted import.
- **Issue:** With no `__init__.py`, mypy resolved `scripts/generate_tampa_targets.py` under two different module identities (`generate_tampa_targets` from the `scripts` positional root, `scripts.generate_tampa_targets` from the test's import) in the same run, blocking further type checking.
- **Fix:** Added an empty `scripts/__init__.py` — mypy's own suggested resolution (option a). No effect on `uv run python scripts/*.py` execution.
- **Files modified:** `scripts/__init__.py` (new)
- **Verification:** `uv run mypy src migrations scripts tests` — only pre-existing, unrelated errors remain (see Issues Encountered).
- **Committed in:** `ad5eaa4`

**3. [Rule 1 - Bug] Several existing tests hard-coded the old 5-entry default config's cardinality/order**
- **Found during:** Task 1, running the full test suite (`uv run pytest -q`) after regenerating `config/course_targets.toml`.
- **Issue:** `tests/refresh/test_targets.py` (6 tests) and `tests/api/test_rankings_api.py::test_seat_freshness_and_coverage_api` called `load_targets()` with no explicit path, relying on the ambient default config being the 5-course pilot set (exact section-count lists, "Missing targets: N" counts, first-target identity `== "MAC"`). Growing the default to 1,402 entries broke these assertions' premises, not their logic.
- **Fix:** Added `_pilot_config()`/`_write_pilot_targets_file()` (test_targets.py) and an inline monkeypatch of `easy_a.api.routes.metadata.load_targets` (test_rankings_api.py) to isolate these tests' assertions on the original 5-course pilot set, independent of the production default's cardinality. Only `test_config_parsing_and_filters`' count assertion was changed in substance (`== 5` -> `>= 1400`), since that test specifically validates the real committed default.
- **Files modified:** `tests/refresh/test_targets.py`, `tests/api/test_rankings_api.py`
- **Verification:** `uv run pytest -q` — 276 passed, 3 skipped (full suite green).
- **Committed in:** `6838cda`

---

**Total deviations:** 3 auto-fixed (1 bug fix required for correctness at scale, 1 blocking mypy-resolution fix, 1 bug fix decoupling pre-existing tests from the config's cardinality).
**Impact on plan:** All three deviations were direct, necessary consequences of the plan's own required action (regenerating `config/course_targets.toml` to full scale). None touch `src/easy_a/refresh/coverage.py`, `targets.py`, or `target_cli.py` (verified `git diff --exit-code` clean throughout). No scope creep — no new features, no architectural changes.

## Issues Encountered

- The first live CHM ingestion attempt was launched under an explicit `timeout 300` wrapper and killed at 300s with no output, because `target_cli.main()` buffers all `print()` output until the whole batch completes — a 300s ceiling wasn't sufficient for 23 sequential catalog+schedule round-trips against live USF endpoints plus Supabase writes. Re-ran without the artificial timeout (in the background, then synchronously re-verified); the actual run completed successfully well within a few minutes.
- `uv run mypy src migrations scripts tests` surfaces 5 pre-existing, unrelated errors in `tests/test_database_config.py` (confirmed pre-existing via isolated `uv run mypy tests/test_database_config.py`, with no `scripts/` involvement) and one pre-existing `ruff` `E501` in `src/easy_a/refresh/cleanup.py:496` (confirmed pre-existing by inspecting the pre-change file). Both logged to `.planning/phases/06-mvp1-p3-all-tampa-section-ingestion-10-3-782/deferred-items.md` and left unfixed per the Scope Boundary rule (not directly caused by this plan's changes).

## User Setup Required

None beyond the plan's stated precondition, which was already satisfied: `EASY_A_DATABASE_URL` (hosted Supabase, via `.env`) was already configured from the Phase 05 pilot, and `courses.csv` was already present in the working tree (1,402 data rows, git-ignored).

## Next Phase Readiness

- The all-Tampa architecture is proven end-to-end on one full subject at live scale: the generator, the full committed target config, the unmodified per-course ingestion loop, the suffix guard, the Tampa scope guard, and the D-20 honest-coverage contract all held with 0 quality errors and 0 non-Tampa rows.
- `06-02-PLAN.md` (batch ingestion across all remaining ~211 subjects) and `06-03-PLAN.md` (validation) can proceed against the now-committed full `config/course_targets.toml` with no further target-generation work needed.
- Known, expected state after this plan: only CHM (23 courses) plus the original 10 pilot courses are ingested (427 Tampa sections total); the remaining ~211 subjects are configured but not yet ingested — that is explicitly 06-02's scope, not a gap in this plan.
- `data/coverage-pilot-2026-09-20/suffix-query-risks.json`'s 33 base/suffix pairs are now only partially spot-checked (4 of 33 at the unit level, CHM validated live); 06-02/06-03 should treat full-scale ingestion itself as further validation of the remaining 29 pairs, consistent with 06-RESEARCH.md's own recommendation.

## Self-Check: PASSED

All key files created/modified in this plan confirmed present on disk, and all 8 commits
(2020173, 284e987, 572302e, b542896, ad5eaa4, 6838cda, d27dbd0, ba68fc1) confirmed present in
`git log`.

---
*Phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782*
*Completed: 2026-09-21*
