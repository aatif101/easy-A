---
phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782
plan: 03
subsystem: data-quality
tags: [validation, tdd, suffix-guard, coverage-reconciliation, honest-coverage, supabase]

# Dependency graph
requires:
  - phase: 06-02
    provides: full Tampa Spring 2027 universe ingested into hosted Supabase (212 subjects / 1,402 courses / 3,783 sections, 0 non-Tampa, 0 quality errors)
provides:
  - scripts/validate_tampa_ingest.py — reusable, read-only scale validator (derive_suffix_pairs, assert_suffix_exact_ingest, assert_coverage_reconciled, assert_honest_coverage)
  - Green, measured proof of REQ-COVERAGE-03's success criteria against the live post-ingest hosted Supabase for term 202701
affects: [07-mvp1-p4-search-performance]

# Actuals (#2632)
actuals:
  tokens: 3900
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Read-only scale validator: pure assertion functions over a SQLAlchemy Session (unit-testable on synthetic in-memory SQLite, reusable unmodified against the live hosted DB via a thin CLI)."
    - "Suffix-leak detection at DB scale: a suffix (L-variant) Course row that is ingested but owns 0 stored sections for the term is the observable signature of a leak into the base course -- cheaper and more general than re-deriving from raw schedule HTML."

key-files:
  created:
    - scripts/validate_tampa_ingest.py
    - tests/refresh/test_validate_tampa_ingest.py
  modified: []

key-decisions:
  - "TDD RED evidence: the gsd tdd-red-evidence checker is TAP-format-specific (Node --test); it cannot parse pytest's default output and always reports zero_tests_discovered regardless of the real pytest result. Project config has workflow.tdd_mode: false, so the automated gate is not enforced here -- RED/GREEN discipline was still followed and independently verified via pytest's own per-test failure/pass evidence (8 targeted NotImplementedError failures at RED, 0 collection errors; 8 passed at GREEN) plus the git-log RED/GREEN commit-pattern check from tdd.md's Executor Gate Validation section."
  - "assert_suffix_exact_ingest's real leak signal is 'suffix course ingested but owns 0 stored sections for the term' (its sections were absorbed into/never separated from the base course), not a Section-Course join mismatch (which is structurally guaranteed true by the FK/join itself and is checked only as a defensive invariant)."

patterns-established:
  - "Pattern 1: A validation script's assertion functions take a bare SQLAlchemy Session and raise AssertionError naming the offending course/CRN -- identical code path for the synthetic-SQLite unit test and the live hosted-Postgres CLI run, no test-only branching."

requirements-completed: [REQ-COVERAGE-03]

coverage:
  - id: D1
    description: "Read-only scale validator (scripts/validate_tampa_ingest.py) with derive_suffix_pairs, assert_suffix_exact_ingest, assert_coverage_reconciled, assert_honest_coverage, built TDD (RED then GREEN)"
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py -- 8 tests (all pass on GREEN)"
        status: pass
      - kind: other
        ref: "uv run python -c \"... print('pairs', len(v.derive_suffix_pairs(...)))\" -> pairs 33"
        status: pass
    human_judgment: false
  - id: D2
    description: "Suffix-exact ingest + coverage reconciliation hold at full scale against the live hosted Supabase: all 33 suffix-variant base courses ingested their exact course only, 0 non-Tampa rows, 0 data-quality errors, stored/coverage/rankings counts agree (3,783=3,783=3,783), every stored course is a configured target"
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: other
        ref: "uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml -> PASS suffix-exact / PASS reconciliation (run twice, dated 2026-09-22)"
        status: pass
      - kind: other
        ref: "uv run python scripts/check_data_quality.py --term 202701 --json -> errors 0, noncampus 0 (dated 2026-09-22)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Honest-coverage (D-20) holds at scale: no ranking row presents a global fallback as course history; all 10 named pilot courses remain course-backed (score_source=course, effective_n>0); no *.xlsx/*.xls tracked and courses.csv not committed; scoring model / coverage.py / quality/checks.py unmodified"
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: other
        ref: "uv run python scripts/validate_tampa_ingest.py --term 202701 -> PASS honest-coverage; per-pilot-course query confirms all 10 course-backed (dated 2026-09-22)"
        status: pass
      - kind: other
        ref: "git ls-files -- '*.xlsx' '*.xls' (empty) + git status --porcelain courses.csv (empty) + git diff --exit-code -- src/easy_a/refresh/coverage.py src/easy_a/quality/checks.py src/easy_a/ (all clean)"
        status: pass
    human_judgment: false

# Metrics
duration: 75min
completed: 2026-09-22
status: complete
---

# Phase 6 Plan 3: All-Tampa Scale Validation Summary

**Read-only `scripts/validate_tampa_ingest.py` (TDD, 8 tests) proves REQ-COVERAGE-03 at full scale: all 33 suffix pairs exact, 0 non-Tampa rows, 0 quality errors, counts reconciled 3,783=3,783=3,783, D-20 honest-coverage holds, and all 10 pilot courses stay course-backed.**

## Performance

- **Duration:** ~75 min (dominated by a ~35 min `check_data_quality.py --term 202701` whole-term run over 3,783 sections / 1,402 courses -- the known O(n^2) per-course analytics query documented in 06-02, deferred to Phase 7/MVP1-P4, not addressed here)
- **Tasks:** 3 (1 TDD build task, 2 read-only validation-against-live-DB tasks)
- **Files created:** 2 (`scripts/validate_tampa_ingest.py`, `tests/refresh/test_validate_tampa_ingest.py`)
- **Files modified:** 0 (read-only plan; `coverage.py` / `quality/checks.py` / scoring model untouched)

## Accomplishments

- Built and TDD'd `scripts/validate_tampa_ingest.py`: `derive_suffix_pairs`, `assert_suffix_exact_ingest`, `assert_coverage_reconciled`, `assert_honest_coverage`, plus a `build_parser()`/`main(argv)->int` CLI (`--term`, `--targets`). `derive_suffix_pairs` over the committed `config/course_targets.toml` yields exactly 33 pairs (locked decision 2).
- Ran the validator against the live post-ingest hosted Supabase for term 202701 (dated 2026-09-22): **suffix-exact PASS, reconciliation PASS, honest-coverage PASS** on two separate runs.
- Ran `check_data_quality.py --term 202701 --json`: **0 errors, 0 `unsupported_campus_section`** across 3,783 sections (6,176 total findings, all `warning`/`info` -- `low_confidence_ranking` (3,088) and `no_historical_analytics` (3,088), the expected honest state for the ~1,392 newly ingested courses with no sourced grade history yet).
- Confirmed all 10 named pilot courses (ACG 2021, ACG 2071, AMH 2020, ANT 2000, BSC 1005, ECO 2013, ENC 1101, MAC 1105, MAC 2311, PSY 2012) remain course-backed (`score_source=course`, `effective_n>0`) across every one of their stored sections.
- Ran the verbatim Phase-05 tracked-exports guard: `git ls-files -- '*.xlsx' '*.xls'` empty; `courses.csv` git-ignored and not staged/committed.
- Confirmed `git diff --exit-code` clean for `coverage.py`, `quality/checks.py`, and all of `src/easy_a/` -- this plan is read-only validation as designed.

## Task Commits

TDD Task 1 produced two atomic commits (test -> feat); Tasks 2 and 3 are read-only validation runs against the live DB and produced no code changes (no commit -- evidence recorded here instead):

1. **Task 1 RED: add failing test for tampa ingest scale validator** - `730390d` (test)
2. **Task 1 GREEN: implement tampa ingest scale validator** - `7704caa` (feat)
3. **Task 2: suffix-exact + reconciliation gate against the ingested universe** - no commit (read-only; evidence above)
4. **Task 3: honest-coverage (D-20) + tracked-exports gate at scale** - no commit (read-only; evidence above)

**Plan metadata:** committed separately after this SUMMARY (docs commit).

## Files Created/Modified

- `scripts/validate_tampa_ingest.py` - Read-only scale validator: `derive_suffix_pairs(targets)`, `assert_suffix_exact_ingest(session, term, pairs)`, `assert_coverage_reconciled(session, term, targets)`, `assert_honest_coverage(session, term)`, `build_parser()`/`main(argv)->int` CLI.
- `tests/refresh/test_validate_tampa_ingest.py` - Unit tests for each validator function over a synthetic in-memory SQLite dataset (CHM 2045 base / CHM 2045L suffix courses, honest + injected-violation cases).

## TDD Gate Compliance

- **RED:** `test(06-03): add failing test for tampa ingest scale validator` (`730390d`) -- committed with `scripts/validate_tampa_ingest.py` containing only function signatures raising `NotImplementedError`, so the test module imports cleanly and pytest reports 8 genuinely targeted failures (not a collection crash). `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q` -> `8 failed`, each failure the `NotImplementedError` from the exact behavior under test.
- **GREEN:** `feat(06-03): implement tampa ingest scale validator` (`7704caa`) -- real implementation; `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q` -> `8 passed`.
- **REFACTOR:** none needed -- `ruff check` and `mypy --strict` were both clean on the GREEN implementation as written.
- **Known tooling gap (not a plan deviation):** `gsd_run check tdd-red-evidence` is scoped to Node's `--test` TAP output (`parseNodeTestSummary`/`tapFailedTestNames` in `prohibition-enforcement.cjs`). Running it against the pytest `-q` RED-phase output always classifies as `INVALID_RED` / `zero_tests_discovered`, regardless of the actual pytest result, because pytest's default output is not TAP. This repo's `.planning/config.json` has `workflow.tdd_mode: false`, so the automated gate is not enforced for this project; RED/GREEN discipline was instead verified directly against pytest's own per-test pass/fail evidence and the git-log `test(...)`/`feat(...)` commit-pattern check (both present, in order, above). Fixing the checker for pytest/TAP13 output is out of scope for this read-only validation plan.

## Decisions Made

- Interpreted "suffix Course owns its own sections" as: if a suffix (L-variant) Course row is ingested (exists in the catalog) but has 0 stored sections for the term, that is the leak signature -- its sections were absorbed into (or never separated from) the base course. The reverse Section->Course join-number check is included as a defensive schema invariant (structurally guaranteed true by the FK/join) per the plan's `<behavior>` wording, but the suffix-zero-section check is the assertion that actually catches a real leak; both are exercised by the same injected-violation unit test (reassigning a suffix section's `course_id` to the base course's id).
- `assert_coverage_reconciled` checks "every stored course is a configured target" (the untargeted-course direction) first, distinct from "every target has a stored course" -- a target may legitimately have 0 sections (an unoffered course this term), which is not a reconciliation violation. This matched reality: `MHS 4023` is catalog-present (a Course row exists, and it is one of the 1,402 configured targets) but has 0 stored sections for term 202701, which is why the live distinct-course-with-sections count is 1,401 while the configured target count is 1,402 -- both are correct given `coverage_metadata`'s own "missing" status semantics, and this did not trip the reconciliation assertion.

## Deviations from Plan

None - plan executed exactly as written. No real ingestion defect was found against the live DB (all three assertions passed on the first live run and were re-confirmed on a second live run in Task 3); nothing needed re-ingesting via `scripts/refresh_all_tampa.py`, and no guard, check, or the scoring model was touched.

## Issues Encountered

- `check_data_quality.py --term 202701 --json` took materially longer than an initial 590s `timeout` wrapper allowed (the wrapper killed the first attempt at `exit=124` with an empty output file). Re-ran without an external `timeout` wrapper (`nohup ... &`, polled by PID) and it completed in ~35 min. This reconfirms the known deferred O(n^2) per-course analytics N+1 documented in 06-02 (Phase 7/MVP1-P4 follow-up); not fixed here per the plan's explicit instruction not to optimize it in this plan.
- The `gsd_run check tdd-red-evidence` TAP-parser mismatch above (documented under TDD Gate Compliance, not a code deviation).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REQ-COVERAGE-03's success criteria are proven with measured, dated evidence against the live hosted Supabase: full Tampa universe ingested (212 subjects / 1,402 courses / 3,783 sections), 0 non-Tampa rows, 0 quality errors, the suffix guard holds across all 33 pairs, config/DB are reconciled, and the honest-coverage (D-20) contract holds at scale with the 10 pilot courses intact.
- `scripts/validate_tampa_ingest.py` is a reusable regression check -- re-run it after any future re-ingest or schema change touching `Course`/`Section`/`section_rankings`.
- Ready for **Phase 7 (MVP1-P4)**: full-scale cache build + search performance tuning to p95 < ~1.5s on Supabase, including the deferred `get_course_historical_outcome_stats` N+1 optimization that both `check_data_quality.py`'s whole-term pass and this plan's ~35 min run reconfirmed.
- Separate future effort (not MVP1-P3/P4 scope): sourced Fall-2024-equivalent grade history for the ~1,392 newly ingested courses currently in the honest `effective_n=0`/`score_source=global` state.

---
*Phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: scripts/validate_tampa_ingest.py
- FOUND: tests/refresh/test_validate_tampa_ingest.py
- FOUND: 06-03-SUMMARY.md
- FOUND commit: 730390d (test RED)
- FOUND commit: 7704caa (feat GREEN)
