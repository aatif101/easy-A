---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
verified: 2026-09-24T19:35:00Z
status: passed
score: 10/10 must-haves verified
covered_files:

  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/WINDOWS.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-01-PLAN.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-01-SUMMARY.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-02-PLAN.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-02-SUMMARY.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-03-PLAN.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-03-SUMMARY.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-04-PLAN.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-04-SUMMARY.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-05-PLAN.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-05-SUMMARY.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-D21-EXCEPTIONS.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-PATTERNS.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-RESEARCH.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-REVIEW.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VALIDATION.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md"
  - ".planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/COVERAGE.md"
  - "scripts/inventory_tampa_grades.py"
  - "scripts/validate_tampa_ingest.py"
  - "scripts/verify_rankings_pages.py"
  - "tests/api/test_verify_rankings_pages.py"
  - "tests/refresh/test_inventory_tampa_grades.py"
  - "tests/refresh/test_validate_tampa_ingest.py"
  - "web/src/components/RankingDetails.tsx"
  - "web/src/components/RankingEvidence.test.tsx"
  - "web/src/components/RankingTable.tsx"
  - "web/src/utils/rankings.ts"

covered_digest: "v1:sha256:f8e1388e9ea3aea4f226c5071fb588282c5505c67d575b64f7c7c1d4c94a69a9"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 9/10
  gaps_closed:
    - "D-21 grade-coverage integrity verdict never silently absorbs a reported integrity anomaly (CR-01: rows_at_or_after_term now gates verdicts.integrity / verdicts.d21_grade_coverage, proven by a structural invariant test over every reported counter plus a CLI end-to-end regression test)."
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "Open the rankings page in a real browser (desktop width and a mobile viewport) and visually inspect the evidence wording on a course row, a course/effective_n=0 row, a subject-fallback row and a global-fallback row, in both the table/card view and the expanded details panel."
    expected: "The wording matches describeEvidence()'s four scopes exactly as asserted by the 8 passing RankingEvidence.test.tsx jsdom tests, with no visual truncation, overlap, or layout regression in a real rendering engine."
    why_human: "No Chromium/Playwright is available in this execution environment (.planning/WINDOWS.md entry 8, open since 2026-09-24). jsdom component tests prove the exact text is produced, but cannot prove real-viewport layout/rendering correctness."
---

# Phase 8: MVP1-P5 — End-to-End MVP-1 Verification — Re-Verification Report

**Phase Goal:** MVP 1 is demonstrably met end to end (ROADMAP.md Phase 8 success criteria; grade-coverage criterion is the locked PROJECT.md D-21).
**Verified:** 2026-09-24T19:35:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (08-05)

## Summary

The previous verification (2026-09-24T19:10:00Z) found 9/10 must-haves verified with one
blocking gap (CR-01): the D-21 inventory's `rows_at_or_after_term` integrity counter was
reported in JSON but never gated `verdicts.integrity` / `verdicts.d21_grade_coverage`, so a
future nonzero value would still print PASS. Gap-closure plan 08-05 (commits `b124e0a`,
`0dc05aa`, `2af00c1`, `9170356`) fixed CR-01, fixed a related warning (WR-01, `stale_cache`
computed from out-of-window grade rows), and documented a second warning (WR-02) without
narrowing its guard. This re-verification independently re-read the fixed code, independently
re-ran every regression test named in the plan, independently re-ran the full test suites, and
independently re-ran both live gates read-only against hosted Supabase — it does not rely on
SUMMARY.md's claims.

**Result: the CR-01 gap is closed in the codebase, not just claimed.** All 10 must-have truths
from the original verification now verify. One item remains correctly routed to human
verification — the browser-viewport visual check (`.planning/WINDOWS.md` entry 8) — which was
never resolvable in this environment and is not a regression.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | All ~3,782 Tampa Spring 2027 sections are searchable through the complete rankings API page walk, with exact identity-set equality. | ✓ VERIFIED (unchanged, regression check) | `scripts/verify_rankings_pages.py` unmodified since prior verification (`git diff --quiet a1f6d45 -- scripts/verify_rankings_pages.py`, exit 0, independently re-run). Not touched by 08-05; no regression risk. |
| 2 | Every stored Tampa section is classified into exactly one D-21 state, and the D-21 verdict is PASS only when zero integrity failures exist and every non-evidence-backed section is a listed exception. | ✓ VERIFIED | **Gap closed.** `Inventory.to_dict` in `scripts/inventory_tampa_grades.py` now builds the `"integrity"` JSON mapping once as a local (`unattributed_grade_rows`, `bucket_sum_mismatch_rows`, `rows_at_or_after_term`, `stale_cache`, `non_tampa_section_count`) and derives `integrity_ok = failure_section_count == 0 and not any(integrity.values())` from that same local — independently confirmed by direct code read (lines ~202-226). `test_every_reported_integrity_counter_gates_the_verdict` independently re-run and passes: it enumerates every key of `to_dict()["integrity"]`, dirties each in turn via `dataclasses.replace`, and asserts both verdicts flip to FAIL — a structural invariant, not a hardcoded check of one field. `test_rows_at_or_after_term_gates_integrity_verdict[3-FAIL]` and `test_main_exits_nonzero_when_grade_row_at_or_after_term_exists` (CLI end-to-end through `main()`, seeded DB row, exit code 1) both independently re-run and pass. Live re-run against hosted Supabase (this verifier, 2026-09-24T19:32:16Z) confirms `sections_by_state` still sums to 3,783 = 3,122 + 361 + 300 and `verdicts` = PASS/PASS with all five integrity counters clean. |
| 3 | The Tampa validator's honest-coverage check agrees with D-21; its verified count matches the inventory's exception_non_letter_grade count. | ✓ VERIFIED (unchanged, regression check) | `assert_honest_coverage`'s logic untouched by 08-05 (only `assert_suffix_exact_ingest`'s docstring/comment/message changed, WR-02). Live re-run by this verifier: `PASS honest-coverage (verified non-letter-grade exceptions: 300)`, equal to the inventory's `exception_non_letter_grade=300` exactly. |
| 4 | Every student-visible evidence surface states the true evidence scope, with no misleading text and no scoring/API change. | ✓ VERIFIED (unchanged, regression check) | `web/src` confirmed unchanged since `a1f6d45` (`git diff --quiet a1f6d45 -- web/src`, exit 0). Not touched by 08-05. 8/8 `RankingEvidence.test.tsx` tests independently re-run and pass (part of the 86/86 frontend suite below). |
| 5 | Search p95 is below 1.5s on hosted Supabase, single-client loopback, full stored term. | ✓ VERIFIED (unchanged, regression check) | `scripts/benchmark_rankings_search.py` confirmed unchanged since `a1f6d45`. Not re-measured live in this re-verification (no server started; 08-05's plan explicitly scopes out re-measurement since the harness and scoring/API/cache paths are untouched) — the 08-04 recorded value (p95 277.25 ms) stands, consistent with the unchanged harness and D-02 invariance. |
| 6 | Scoring model, cache semantics and API contract are unchanged by this phase (D-02). | ✓ VERIFIED | `git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api src/easy_a/models migrations web/src/types web/src/api` independently re-run by this verifier: exit 0. 08-05 touched only `scripts/inventory_tampa_grades.py`, `scripts/validate_tampa_ingest.py`, their tests, and two Phase 8 markdown records — none of which are D-02-covered paths. |
| 7 | No raw grade export, CSV, credential, connection string or CRN-level grade bucket is committed. | ✓ VERIFIED | `test -z "$(git ls-files -- '*.xlsx' '*.xls' '*.csv')"` independently re-run, exit 0. `08-VERIFICATION-REPORT.md` and `08-05-SUMMARY.md` spot-checked for `postgresql://`/`pooler.supabase.com` substrings and a_count..w_count columns: none found. |
| 8 | The 202701 evidence-backed and exception counts are reported separately and no exception/fallback row is folded into course-history coverage. | ✓ VERIFIED | `08-VERIFICATION-REPORT.md` "## D-21 grade coverage" still states evidence-backed (3,122) and exceptions (661) separately, unchanged by 08-05's edits (which only appended a new section and touched three Gates-row Reason cells). |
| 9 | The phase issues independent Phase 8 and MVP-1 (D-21) verdicts, each PASS/FAIL/NOT MEASURED, with every FAIL naming an exact list and repair action; no new grade sourcing is proposed. | ✓ VERIFIED | **Advisory resolved.** The prior verification flagged this truth as `coincidental-reliance` because the underlying D-21 inventory gate did not fully enforce what it reported. That precondition is now genuinely enforced (Truth 2), so the verdict text in `08-VERIFICATION-REPORT.md`'s "## Verdicts" and the new "## Gap closure re-verification (08-05)" section is no longer merely internally consistent but built on a gate that actually verifies. No `coincidental-reliance` flag remains for this truth. |
| 10 | Requirement IDs REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01 are each satisfied with evidence, and no requirement mapped to Phase 8 is orphaned. | ✓ VERIFIED | See "Requirements Coverage" below — all three IDs appear in plan frontmatter (including 08-05's `[REQ-GRADES-01, REQ-COVERAGE-03]`) and ROADMAP.md's Phase 8 requirement table, now marked complete with the 2026-09-24 date. No additional Phase-8-mapped ID exists in REQUIREMENTS.md. |

**Score:** 10/10 truths verified (0 present, behavior-unverified; 0 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `scripts/inventory_tampa_grades.py` | D-21 grade-coverage classifier CLI whose integrity verdict gates every reported counter | ✓ VERIFIED (gap closed) | `integrity_ok` derived from the same local mapping emitted under `"integrity"` — one definition, not two lists. Code read confirms lines ~202-226 match the plan's `key_links` contract exactly (`pattern: "integrity_ok"`). |
| `tests/refresh/test_inventory_tampa_grades.py` | Regression tests for every D-21 state and the verdict contract, including a nonzero `rows_at_or_after_term` | ✓ VERIFIED (gap closed) | `_make_inventory` now accepts `**overrides` via `dataclasses.replace`, no longer hardcodes `rows_at_or_after_term=0`. 9 new/changed named tests independently re-run and pass; full file (28 tests including the 6 new ones from 08-05) passes as part of the 42-test scoped run below. |
| `scripts/validate_tampa_ingest.py` | Honest-coverage check amended for D-21; suffix-leak guard fail-closed and documented | ✓ VERIFIED | `assert_suffix_exact_ingest`'s raise condition, queries, loop and `continue` are byte-for-byte unchanged from `a1f6d45` per the plan's own acceptance criterion (independently spot-checked via `git diff a1f6d45 -- scripts/validate_tampa_ingest.py`, confirmed diff is docstring/comment/message-only). |
| `tests/refresh/test_validate_tampa_ingest.py` | Cross-term suffix guard tests | ✓ VERIFIED | 2 new named tests independently re-run and pass; existing leak-detection tests (`test_assert_suffix_exact_ingest_raises_on_leaked_suffix_section`) still pass unmodified. |
| `.planning/phases/.../08-VERIFICATION-REPORT.md` | Gap-closure re-verification section, updated Gates rows | ✓ VERIFIED | "## Gap closure re-verification (08-05)" section present with UTC window, HEAD SHA, commands, observed-vs-08-04 delta table (all "none"), test/lint/type results, invariance results, and all five 08-REVIEW.md finding dispositions. Three Gates rows reference 08-05's re-confirmation. |
| `.planning/phases/.../08-VALIDATION.md` | Requirement-map row for 08-05 | ✓ VERIFIED | One row present: `REQ-GRADES-01 / REQ-COVERAGE-03 \| 08-05 \| ... \| Yes - closed 08-05 (8 tests); live PASS re-confirmed 08-05`. |
| `.planning/phases/.../08-D21-EXCEPTIONS.md` | Unregenerated, byte-identical to `a1f6d45` | ✓ VERIFIED | `git diff --quiet a1f6d45 -- .../08-D21-EXCEPTIONS.md` independently re-run, exit 0 — 08-05 did not write hosted data or regenerate the exception list, matching its stated read-only scope. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `scripts/inventory_tampa_grades.py` `Inventory.to_dict` integrity mapping | `verdicts.integrity` / `verdicts.d21_grade_coverage` / `main()` exit code | Same local dict is emitted under `"integrity"` and reduced into `integrity_ok` | ✓ WIRED (gap closed, was NOT WIRED) | Structural invariant test (`test_every_reported_integrity_counter_gates_the_verdict`) independently re-run and passes; a nonzero/true value on ANY of the 5 reported keys flips both verdicts to FAIL. CLI end-to-end regression test proves this through `main()` on a seeded DB, not just the dataclass method. |
| `scripts/inventory_tampa_grades.py` `_aggregate_grade_rows` | `stale_cache` in `collect_inventory` | `evidence_ingested_at_max`, updated only for rows with `term_code < before_term` (same filter as `src/easy_a/analytics/queries.py`'s scoring query) | ✓ WIRED (WR-01 fixed) | Code read confirms `overall_ingested_at_max` (every row) and `evidence_ingested_at_max` (scoring-window rows only) are tracked separately; `stale_cache` compares against the latter. Both directions independently tested and re-run (`test_stale_cache_ignores_out_of_window_grade_ingest`, `test_stale_cache_trips_on_newer_in_window_grade_ingest`). |
| Live inventory + validator vs. `08-VERIFICATION-REPORT.md`'s recorded 08-05 values | Hosted Supabase, term 202701 | Read-only re-run | ✓ WIRED | This verifier's own independent live runs (2026-09-24T19:32:16Z inventory, ~19:34Z validator) reproduce the report's recorded 08-05 values exactly: PASS/PASS, 3,122/361/300, all five integrity counters clean, `evidence_grade_ingested_at_max == grade_ingested_at_max`, validator honest-coverage 300. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| CR-01 fix: the 9 named 08-05 regression tests pass | `uv run pytest <9 named tests> -q` | `9 passed` | ✓ PASS (independently reproduced by this verifier) |
| Every reported integrity counter gates the verdict (structural invariant, not a single-field check) | `uv run pytest tests/refresh/test_inventory_tampa_grades.py::test_every_reported_integrity_counter_gates_the_verdict -q` | included in the 9-test run above; passed | ✓ PASS (independently reproduced) |
| Scoped test suites for both fixed gate scripts pass | `uv run pytest tests/refresh/test_inventory_tampa_grades.py tests/refresh/test_validate_tampa_ingest.py -q` | `42 passed` | ✓ PASS (independently reproduced) |
| Full Python suite baseline | `uv run pytest -q` | `374 passed, 3 skipped` | ✓ PASS (independently reproduced; matches the instructed expected baseline exactly) |
| Frontend suite baseline | `npm --prefix web test -- --run` | `86 passed` (6 files) | ✓ PASS (independently reproduced; matches the instructed expected baseline exactly) |
| Live D-21 inventory reproduces PASS/PASS on the fixed gate | `uv run python scripts/inventory_tampa_grades.py --term 202701` | `verdicts: {'integrity': 'PASS', 'd21_grade_coverage': 'PASS'}`, `integrity` all 0/false, `sections_by_state` 3,122/361/300 | ✓ PASS (independently reproduced by this verifier, 2026-09-24T19:32:16Z) |
| Live validator reproduces three PASS lines | `uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` | `PASS suffix-exact`, `PASS reconciliation`, `PASS honest-coverage (verified non-letter-grade exceptions: 300)` | ✓ PASS (independently reproduced by this verifier) |
| D-02 invariance holds | `git diff --quiet origin/main -- src/easy_a/analytics src/easy_a/rankings src/easy_a/api src/easy_a/models migrations web/src/types web/src/api` | exit 0 | ✓ PASS (independently reproduced) |
| Non-08-05 artifacts (exceptions list, API scanner, benchmark, web/src) unchanged since `a1f6d45` | `git diff --quiet a1f6d45 -- .../08-D21-EXCEPTIONS.md scripts/verify_rankings_pages.py scripts/benchmark_rankings_search.py web/src` | exit 0 | ✓ PASS (independently reproduced) |
| No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers in the four 08-05-touched files | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across `scripts/inventory_tampa_grades.py`, `scripts/validate_tampa_ingest.py`, and their two test files | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| REQ-COVERAGE-03 | 08-01, 08-04, 08-05 | All ~3,782 Tampa sections ingested and searchable | ✓ SATISFIED | Validator suffix-exact/reconciliation PASS (independently re-run), API identity scan PASS (unchanged, prior verification), ROADMAP.md marks it `✓ Complete`. |
| REQ-GRADES-01 | 08-02, 08-03, 08-04, 08-05 | Ingested Tampa courses have real historical grade data; easiness computed from it; honest fallback labeling; D-21 verdict gate enforces every reported integrity counter | ✓ SATISFIED (gap closed) | D-21 inventory classification, validator cross-check and UI wording all independently reproduced and correct on current live data; the inventory's PASS/FAIL gate now structurally enforces every counter it reports (Truth 2), closing the prior gap. ROADMAP.md marks it `✓ Complete under D-21`. |
| REQ-PERF-01 | 08-04 | Full-Tampa-scale search p95 < ~1.5s on Supabase | ✓ SATISFIED | p95 277.25 ms recorded in 08-04, unaffected by 08-05 (benchmark harness and all scoring/API/cache paths confirmed unchanged since `a1f6d45`/`origin/main`). |

No orphaned requirements: ROADMAP.md maps exactly REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01 to Phase 8, and all three appear across the five plans' frontmatter (08-01, 08-02/08-03, 08-04, 08-05).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | (none) | — | The prior 🛑 blocker (CR-01: integrity signal computed and reported but not gated) is resolved — `integrity_ok` now derives from the same mapping reported under `"integrity"`, independently confirmed by code read and by the invariant test. The prior ⚠️ WR-01 warning (`stale_cache` computed from out-of-window rows) is also resolved. WR-02 (suffix existence lookup catalog-scoped, not term-scoped) remains, by design, as a documented fail-closed ambiguity — not narrowed, since narrowing it would silently delete the Phase 06 leak guard; this is an accepted, explained design tradeoff, not a defect. IN-01 (`_environment_label` duplication) and IN-02 (fractional `effective_n` rounding) remain deferred, unchanged, both low-severity and non-manifesting on current data. |

No `TBD`/`FIXME`/`XXX` debt markers found in this phase's changed files (independently re-confirmed).

### Human Verification Required

- **Browser-viewport visual inspection of the desktop table / mobile card evidence wording** (course, course/effective_n=0, subject, global) — no Chromium/Playwright available in this execution environment; logged as `.planning/WINDOWS.md` entry 8 (open since 2026-09-24T18:26:16Z, unresolved by 08-05, which did not touch `web/src`). The 8/8 passing `RankingEvidence.test.tsx` jsdom component tests substitute for text-content correctness but not for a real-viewport visual/layout check. This item was correctly identified as NOT MEASURED (not fabricated as PASS) by the prior verification and by 08-05's own report, and remains genuinely unresolvable without a browser in this environment — it is not a regression and does not reflect incomplete work by 08-05, which was scoped only to the D-21 gate fix.

### Gaps Summary

**No gaps remain.** The single blocking gap from the prior verification (CR-01: `rows_at_or_after_term` computed and reported but not gating the D-21 integrity verdict) is closed in the codebase: `Inventory.to_dict` derives `integrity_ok` from the same local mapping it emits under `"integrity"`, proven end-to-end through `main()` by a CLI regression test and, independent of any specific field, by a structural invariant test that dirties every reported counter in turn and asserts both verdicts flip to FAIL. This verifier independently re-read the fix, independently re-ran all 9 named 08-05 regression tests plus the two full scoped/full suites (374 passed/3 skipped Python, 86 passed frontend — both matching the instructed baselines exactly), and independently re-ran both live gates read-only against hosted Supabase, reproducing PASS/PASS with all five integrity counters clean and the same 3,122/361/300 section split reported in `08-VERIFICATION-REPORT.md`.

The only remaining item is the pre-existing, environment-limited browser-viewport visual check (`.planning/WINDOWS.md` entry 8), which routes this phase to `human_needed` rather than `passed` per the decision tree — not because of any newly found deficiency, but because a genuine human-in-the-loop check was never resolvable in this environment and 08-05 did not (and could not) change that. A human should confirm this NOT MEASURED item is acceptable before treating MVP-1 as ready to ship, consistent with STATE.md's own "Do next" note.

---

*Verified: 2026-09-24T19:35:00Z*
*Verifier: Claude (gsd-verifier)*

## Post-verification closeout note (2026-09-24T20:24:01Z)

After this report was written, two covered documentation files changed during phase closeout; no code, test, or live-data change occurred:
- `08-VALIDATION.md`: manual browser-display row updated NOT MEASURED → PASS from human UAT (`08-UAT.md` test 1, passed 2026-09-24); status → validated; validation audit appended (0 gaps).
- `COVERAGE.md`: opt-out reason shortened to ≤200 chars to satisfy the api-coverage verify:pre gate (same meaning: no external API integrated).
The human_verification item above is therefore resolved (UAT pass), and `status` is `passed`. `covered_digest` was recomputed with `gsd-tools query verification.fingerprint` over the unchanged `covered_files` list. Security (`08-SECURITY.md`, 23/23 closed) and UI review (`08-UI-REVIEW.md`, 19/24, advisory) were added afterward and are not covered files.
