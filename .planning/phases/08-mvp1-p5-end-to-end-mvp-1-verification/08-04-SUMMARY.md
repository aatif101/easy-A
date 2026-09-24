---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
plan: 04
subsystem: testing
tags: [verification, d21, req-coverage-03, req-grades-01, req-perf-01, hosted-supabase]

# Dependency graph
requires:
  - phase: 08-mvp1-p5-end-to-end-mvp-1-verification (plan 01)
    provides: scripts/verify_rankings_pages.py and its live PASS verdict (3,783/3,783/3,783
      identity reconciliation) for the REQ-COVERAGE-03 API identity gate
  - phase: 08-mvp1-p5-end-to-end-mvp-1-verification (plan 02)
    provides: scripts/inventory_tampa_grades.py, the amended validate_tampa_ingest.py
      honest-coverage check, and the live PASS/PASS D-21 verdict (3,122 evidence-backed /
      661 exceptions) for the REQ-GRADES-01 gates
  - phase: 08-mvp1-p5-end-to-end-mvp-1-verification (plan 03)
    provides: describeEvidence() and the wired RankingTable/RankingDetails evidence wording,
      proven by 8 RankingEvidence.test.tsx tests, for the REQ-GRADES-01 evidence-wording gate
provides:
  - "08-VERIFICATION-REPORT.md: one dated, reproducible hosted-Supabase verification record
    with a Gates table (10 rows, all PASS), a D-21 grade-coverage section, a provenance-by-term
    reconciliation, a full regression/invariance section, and independent Phase 8 / MVP-1
    (D-21) verdicts, both PASS"
  - "08-D21-EXCEPTIONS.md: the committed, machine-generated per-section D-21 exception list
    (661 rows: 361 no_rows + 300 non_letter_grade), written directly by
    inventory_tampa_grades.py --exceptions-md, never hand-transcribed"
  - "08-VALIDATION.md updated to measured status: all three Wave 0 gaps closed,
    nyquist_compliant: true, status: complete"
affects: [ship, hosted-beta, mvp1-milestone-close]

# Actuals (#2632)
actuals:
  tokens: 14373
  tasks: 3
  commits: 3
plan_head_before: c55dfdcc0d538b7d5497a41f6e7b1a1c1c88d877

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Snapshot-freeze-then-repeat: capture five snapshot fields (section_count,
      cache_row_count, cache_refreshed_at_max, grade_row_count, grade_ingested_at_max) before
      the live gates, then re-run the read-only inventory after and diff all five -- proves the
      hosted evidence didn't drift mid-report without needing a database lock."
    - "Cross-script reconciliation as a pass condition, not a nice-to-have: the API's
      api_score_source_split, the inventory's sections_by_state and the validator's verified
      non-letter-grade count are three independently-computed views of the same hosted state;
      requiring exact numeric agreement across all three is what makes the PASS verdict mean
      something rather than just three scripts each independently claiming success."

key-files:
  created:
    - .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md
    - .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md
  modified:
    - .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md
    - .planning/WINDOWS.md

key-decisions:
  - "Reported the repo-wide mypy count as measured now (36 errors in 11 files) rather than
    re-quoting the 2026-09-23 planning-time baseline (30/9), after confirming the +6/+2 delta is
    entirely in two test files 08-01/08-02 added (tests/api/test_verify_rankings_pages.py,
    tests/refresh/test_inventory_tampa_grades.py). Both sit outside 08-04's declared file scope
    (08-VERIFICATION-REPORT.md/08-D21-EXCEPTIONS.md/08-VALIDATION.md only), so they were not
    edited; logged to .planning/WINDOWS.md entry 9 instead of silently repeating a now-inaccurate
    baseline (D-06/D-07). This plan's own scoped mypy check (the three production gate scripts)
    is 0 issues."
  - "Treated the 661 listed D-21 exceptions as the honest, complete end state rather than a gap
    to close: verified their machine-generated exception list total (661) equals the inventory
    JSON's exception count exactly, and issued MVP-1 PASS without proposing any new grade
    sourcing or import, per D-21's explicit stop-here decision."

requirements-completed: [REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01]

coverage:
  - id: D1
    description: "REQ-COVERAGE-03: validator (suffix-exact + reconciliation) and API identity
      scanner both PASS against hosted Supabase term 202701 -- 3,783/3,783/3,783 sections
      reconciled with 0 missing/extra/duplicate/non-Tampa identities."
    requirement: "REQ-COVERAGE-03"
    verification:
      - kind: e2e
        ref: "uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml"
        status: pass
      - kind: e2e
        ref: "uv run python scripts/verify_rankings_pages.py --term 202701 --http-base-url http://127.0.0.1:8000"
        status: pass
    human_judgment: false
  - id: D2
    description: "REQ-GRADES-01: D-21 inventory (3,122 evidence-backed / 661 listed exceptions),
      validator honest-coverage (300 verified non-letter-grade exceptions matching the
      inventory exactly), API score-source split matching the cache split exactly, and the
      08-03 evidence-wording component tests (8/8) together prove every section is either
      evidence-backed or a listed, honestly-labeled D-21 exception."
    requirement: "REQ-GRADES-01"
    verification:
      - kind: e2e
        ref: "uv run python scripts/inventory_tampa_grades.py --term 202701 --exceptions-md .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md"
        status: pass
      - kind: unit
        ref: "web/src/components/RankingEvidence.test.tsx (8 tests, re-run as part of the 86-test frontend suite)"
        status: pass
    human_judgment: false
  - id: D3
    description: "REQ-PERF-01: single-client loopback HTTP p95 = 277.25 ms (< 1,500 ms), 50
      calls after 5 warmups, hosted Supabase, full 3,783-section stored term. Not interrupted."
    requirement: "REQ-PERF-01"
    verification:
      - kind: e2e
        ref: "uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-02 invariance (empty diff vs. origin/main across scoring/cache/API/model/
      migration/frontend-contract paths) and D-19 hygiene (no tracked spreadsheet/CSV) both
      hold; full Python (366/3) and frontend (86) suites green; browser-viewport visual
      inspection recorded honestly as NOT MEASURED (no Chromium in this environment)."
    verification: []
    human_judgment: true
    rationale: "The browser-viewport observation genuinely requires a human with a real
      browser -- no Chromium/Playwright is available in this execution environment, and this
      was already logged as WINDOWS.md entry 8 in 08-03. A human should confirm whether that
      remains acceptable before treating the MVP-1 verdict as final for shipping."

# Metrics
duration: 15min
completed: 2026-09-24
status: complete
---

# Phase 08 Plan 04: End-to-End MVP-1 Verification Summary

**Dated hosted-Supabase verification report proving REQ-COVERAGE-03, REQ-GRADES-01 and REQ-PERF-01 all PASS against one frozen snapshot (3,783 sections, 3,122 evidence-backed, 661 listed D-21 exceptions, p95 277.25 ms), a committed machine-generated 661-row exception list, and independent Phase 8 and MVP-1 (D-21) verdicts, both PASS — no gate failed, no repair action required.**

## Performance

- **Duration:** ~15 min (three live-gate task cycles plus regression suite)
- **Started:** 2026-09-24T18:29:44Z
- **Completed:** 2026-09-24T18:41:00Z (approx)
- **Tasks:** 3 completed
- **Files modified:** 4 (2 new, 2 modified)

## Accomplishments

- **Task 1 — froze the D-21 snapshot end to end.** Ran `inventory_tampa_grades.py --term 202701
  --exceptions-md 08-D21-EXCEPTIONS.md`: both verdicts PASS, 3,122 evidence-backed sections,
  661 listed exceptions (361 `no_rows` + 300 `non_letter_grade`), 0 integrity failures across
  all nine possible classification states. `validate_tampa_ingest.py` printed `PASS
  suffix-exact`, `PASS reconciliation`, `PASS honest-coverage (verified non-letter-grade
  exceptions: 300)` — an exact match to the inventory's own `exception_non_letter_grade` count.
  Reconciled every per-term grade-row count (202408 179 / 202501 2,096 / 202505 465 / 202508
  2,887 / 202601 3,035; 8,662 total) against the dated import ledger and `05-IMPORT-RECORD.md`
  with 0 deltas.
- **Task 2 — cross-checked identity, quality and p95 against the same snapshot.**
  `verify_rankings_pages.py`: PASS, 3,783/3,783/3,783 reconciled, 0
  missing/extra/duplicate/non-Tampa; its `api_score_source_split` matched the inventory's
  cached-state split exactly (course 3,422/300 effective_n=0, subject 311, global 50).
  `check_data_quality.py --json`: 0 errors, 1,058 warnings, 50 info — reproducing the ledger's
  final baseline exactly. `benchmark_rankings_search.py --live`: p50 220.15 ms, **p95
  277.25 ms**, max 340.29 ms over 50 calls / 5 warmups, single-client loopback HTTP. Re-ran the
  inventory after: all five snapshot fields unchanged — no gate needed repeating.
- **Task 3 — closed regression/invariance and issued both verdicts.** D-02 invariance PASS
  (empty diff against `origin/main` across `src/easy_a/analytics`, `rankings`, `api`, `models`,
  `migrations`, `web/src/types`, `web/src/api`); D-19 hygiene PASS. Full suite: **366 passed / 3
  skipped** Python, **86 passed** frontend, typecheck/lint/build all clean. PostgreSQL
  integration honestly reported as skipped (`EASY_A_TEST_POSTGRES_URL` unset). Discovered and
  honestly recorded (not silently re-quoted) that repo-wide `mypy` grew from the 2026-09-23
  baseline (30/9 files) to 36/11 files — the +6/+2 delta is entirely in two test files 08-01/08-02
  added, outside 08-04's own file scope; this plan's own scoped mypy check (3 production gate
  scripts) is 0 issues. Logged to `.planning/WINDOWS.md` entry 9. Issued **Phase 8 verdict PASS**
  and **MVP-1 verdict (D-21) PASS**: every one of the 10 Gates-table rows is PASS, and the 661
  listed exceptions are the honest end state (no repair action, no new grade sourcing proposed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Freeze the snapshot and carry the D-21 grade gate end to end into the report** —
   `9ecce88` (feat)
2. **Task 2: Run the identity, quality and p95 gates against the same snapshot and confirm it
   held** — `6dc0a96` (feat)
3. **Task 3: Close regression and invariance gates and issue the Phase 8 and MVP-1 verdicts** —
   `a311105` (feat)

**Plan metadata:** commit pending below (this SUMMARY + STATE/ROADMAP/REQUIREMENTS).

## Files Created/Modified

- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md` — the
  dated Phase 8 / MVP-1 verification record (new)
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md` — the
  committed, machine-generated 661-row D-21 exception list (new)
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md` — updated to
  measured status: Wave 0 gaps closed, `nyquist_compliant: true`, `status: complete`
- `.planning/WINDOWS.md` — appended entry 9 (the mypy test-file delta, `kind: lint-warning`)

## Decisions Made

See `key-decisions` in frontmatter. In summary: recorded the repo-wide mypy regression honestly
rather than re-quoting a stale baseline, without fixing files outside this plan's declared
scope; and treated the 661 D-21 exceptions as the honest, complete end state (not a gap),
issuing MVP-1 PASS without proposing new grade sourcing, per D-21's stop-here decision.

## Deviations from Plan

### Auto-fixed Issues

None — every gate this plan's `<action>` and `<verify>` blocks required ran clean on the first
attempt (validator timed out at the default 90s Bash timeout on the first invocation of Task 1
and was simply re-run with a longer timeout; this was an execution-environment adjustment, not a
code or content fix, so it is not logged as a Rule 1-3 auto-fix).

### Out-of-scope finding (SCOPE BOUNDARY, not auto-fixed)

**1. Repo-wide mypy delta in two 08-01/08-02 test files**
- **Found during:** Task 3, repo-wide mypy comparison against the planning-time baseline
- **Issue:** `uv run mypy src migrations scripts tests` reports 36 errors in 11 files, up from
  the 2026-09-23 baseline of 30 in 9 files. The +6/+2 delta is entirely in
  `tests/api/test_verify_rankings_pages.py` (5 errors: missing return-type annotation, two
  untyped-function calls, an unused `type: ignore`, an `int()` overload mismatch) and
  `tests/refresh/test_inventory_tampa_grades.py` (1 error: a re-export of
  `scripts.inventory_tampa_grades.os`) — both added by 08-01 and 08-02, not by this plan.
- **Disposition:** Not fixed. 08-04's `files_modified` frontmatter lists only
  `08-VERIFICATION-REPORT.md`, `08-D21-EXCEPTIONS.md` and `08-VALIDATION.md` — the two affected
  test files are out of this plan's declared scope. Per the SCOPE BOUNDARY rule, out-of-scope
  discoveries are logged, not fixed inline.
- **Logged to:** `.planning/WINDOWS.md` entry 9 (`kind: lint-warning`, phase 08).
- **Impact:** None on this plan's gates — the three production gate scripts
  (`verify_rankings_pages.py`, `inventory_tampa_grades.py`, `validate_tampa_ingest.py`) that
  08-04's own `<verify>` blocks require remain mypy-clean (0 issues, confirmed directly).

---

**Total deviations:** 0 auto-fixed. 1 out-of-scope finding logged (not fixed, per SCOPE
BOUNDARY). **Impact:** No scope creep; every REQ-COVERAGE-03 / REQ-GRADES-01 / REQ-PERF-01 gate
PASSED against fresh hosted evidence.

## Issues Encountered

`validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` did not complete
within the default 90-second command timeout on its first invocation (the full-scale suffix,
reconciliation and honest-coverage checks against 3,783 hosted sections legitimately take longer
than 90s over the network). Re-ran with a 240-second timeout; it completed in ~2m38s with all
three checks PASS. No code or content change was needed — purely an execution-environment
timeout adjustment.

## User Setup Required

None — no external service configuration required. `DATABASE_URL` (hosted Supabase) was already
configured in the environment and resolved successfully for every live gate.

## Next Phase Readiness

- MVP 1 is verified end to end: `08-VERIFICATION-REPORT.md` records PASS for REQ-COVERAGE-03,
  REQ-GRADES-01 and REQ-PERF-01, a PASS Phase 8 verdict, and a PASS MVP-1 verdict (D-21) — ready
  to feed `/gsd-ship` or a milestone-close workflow.
- The one open item is the browser-viewport visual inspection (`.planning/WINDOWS.md` entry 8,
  carried from 08-03, unchanged and not a regression) — a human with a real browser should
  confirm this is acceptable before treating MVP-1 as ready to ship. `.planning/WINDOWS.md`
  entry 9 (the mypy test-file delta) is a minor follow-up type-annotation cleanup, not a
  correctness, security or scoring issue.
- No blockers. `git diff --quiet origin/main` on all D-02-scoped paths is empty; no scoring,
  cache, API, model, migration or frontend-contract file changed in Phase 8.

---
*Phase: 08-mvp1-p5-end-to-end-mvp-1-verification*
*Completed: 2026-09-24*

## Self-Check: PASSED

- FOUND: .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md
- FOUND: .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md
- FOUND: .planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md (updated)
- FOUND: .planning/WINDOWS.md (updated, entry 9)
- FOUND: 9ecce88 (Task 1)
- FOUND: 6dc0a96 (Task 2)
- FOUND: a311105 (Task 3)
