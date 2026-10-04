---
phase: 09-hosted-beta-deployment-ci-observability
plan: 10
subsystem: ops
tags: [benchmark, p95, remote-url, validation, d21-inventory, removed-sections, auto-added]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-04 is_undergraduate_number sync scope and sections.removed_at; 09-07 active-only coverage_metadata"
provides:
  - "scripts/benchmark_rankings_search.py --remote-url https://<host>: hosted search p50/p95/max over HTTPS with the existing representative query mix, no DB"
  - "Active-section reconciliation (removed_at IS NULL) in benchmark --live and verify_rankings_pages"
  - "validate_tampa_ingest: D-05 auto-added accounting (INFO line) and active-section reconciliation"
  - "inventory_tampa_grades: D-21 inventory over active sections only"
affects: [09-11, 09-12, 09-15]

actuals:
  tokens: 6400
  tasks: 2
  commits: 2
plan_head_before: 7ddff0dd2e92493284b22715b198802035383c1d
plan_head_after: 01f5047a1091edfa8030faf66f12a19b4b42ed02

tech-stack:
  added: []
  patterns:
    - "Hosted benchmark client: httpx.Client(timeout=60, trust_env=False, follow_redirects=False), no auth, cookies or DATABASE_URL"
    - "Auto-added course is derived, not stored: untargeted stored course whose active sections are all Tampa with an undergraduate number"

key-files:
  created: []
  modified:
    - scripts/benchmark_rankings_search.py
    - scripts/verify_rankings_pages.py
    - scripts/validate_tampa_ingest.py
    - scripts/inventory_tampa_grades.py
    - tests/api/test_benchmark_rankings_search.py
    - tests/api/test_verify_rankings_pages.py
    - tests/refresh/test_validate_tampa_ingest.py
    - tests/refresh/test_inventory_tampa_grades.py

key-decisions:
  - "D-05 accounting decision (1): config/course_targets.toml stays the frozen configured list; the worker never writes it because the container filesystem is ephemeral."
  - "D-05 accounting decision (2): an auto-added course is derived, not stored. It has at least one active 202701 section and is not a configured target. There is no schema marker."
  - "D-05 accounting decision (3): /api/v1/metadata/coverage keeps meaning configured targets."
  - "D-05 accounting decision (4): the validator lists auto-added courses as an allowed category. Reconciliation is stored_active == coverage_sum(targets) + auto_added_active_sections == rankings_total, and a graduate or non-Tampa untargeted course still fails."
  - "D-05 accounting decision (5): the D-21 inventory shows auto-added sections as listed exceptions (no_rows with subject/global fallback). 08-D21-EXCEPTIONS.md stays the dated 2026-09-24 record; the post-sync inventory in plan 09-15 records the new baseline."
  - "assert_suffix_exact_ingest keeps counting all sections including removed ones (a removed section was still ingested under the right course); only a comment was added, its raise condition is byte-for-byte unchanged (Phase 08 WR-02)."
  - "rankings_total in the validator stays the raw section_rankings count so a stale cache row for a removed section surfaces as a count mismatch."

requirements-completed: [REQ-OPS-01, REQ-SYNC-01]

coverage:
  - id: D1
    description: "Hosted p95 is measurable in one command: --remote-url accepts only plain https origins, runs 5 warmups plus N timed calls through the representative query mix, and reports p50/p95/max without a DB, credentials, cookies, redirects or proxy env"
    requirement: REQ-OPS-01
    verification:
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_remote_run_reports_p95_and_sends_no_credentials"
        status: pass
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_remote_origin_rejects_non_plain_https_origins"
        status: pass
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_cli_rejects_remote_url_combinations"
        status: pass
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_remote_run_fails_on_empty_term_and_redirects"
        status: pass
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_remote_failure_does_not_print_transport_details"
        status: pass
    human_judgment: false
  - id: D2
    description: "The loopback --http-base-url validator and its tests are unchanged; the smoke mode still reports p95"
    requirement: REQ-OPS-01
    verification:
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_http_target_rejects_non_loopback_or_ambiguous_urls"
        status: pass
      - kind: command
        ref: "uv run python scripts/benchmark_rankings_search.py --smoke"
        status: pass
    human_judgment: false
  - id: D3
    description: "benchmark --live and verify_rankings_pages reconcile against active sections only, so a removed section no longer raises or fails"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/api/test_benchmark_rankings_search.py#test_live_mode_reconciles_active_sections_after_removal"
        status: pass
      - kind: unit
        ref: "tests/api/test_verify_rankings_pages.py#test_removed_section_is_excluded_from_stored_identities_and_still_passes"
        status: pass
    human_judgment: false
  - id: D4
    description: "validate_tampa_ingest accepts undergraduate Tampa auto-adds with an INFO auto-added (D-05) line and the four-number reconciliation, fails graduate and non-Tampa untargeted courses, excludes removed sections, and leaves the suffix-exact raise condition unchanged"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_auto_added_undergraduate_tampa_course_passes_and_main_prints_info_line"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_untargeted_graduate_course_fails_reconciliation"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_untargeted_non_tampa_course_fails_reconciliation"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_reconciliation_mismatch_names_all_four_numbers"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_removed_sections_are_excluded_from_every_count"
        status: pass
      - kind: unit
        ref: "tests/refresh/test_validate_tampa_ingest.py#test_suffix_exact_still_counts_removed_sections"
        status: pass
    human_judgment: false
  - id: D5
    description: "The D-21 inventory excludes removed sections and lists auto-added sections as no_rows exceptions with subject/global fallback, never as evidence-backed history"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/refresh/test_inventory_tampa_grades.py#test_inventory_excludes_removed_sections_and_lists_auto_added_as_exception"
        status: pass
      - kind: command
        ref: "uv run pytest -q"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-09-29
---

# Phase 09 Plan 10: Operator tools for removed sections and auto-added courses Summary

**`benchmark_rankings_search.py --remote-url https://<host>` measures the hosted search p50/p95/max with the existing query mix (no DB, no redirects, no proxy env, no credentials), and the benchmark `--live` gate, page scan, ingest validator and D-21 inventory now count active sections only, with undergraduate Tampa auto-adds reported as an explicit D-05 category.**

## Performance

- **Duration:** about 12 min of executor time
- **Completed:** 2026-09-29
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 8 modified, none created

## D-05 accounting decision (recorded)

1. `config/course_targets.toml` stays the frozen configured list and the worker never writes it (the container filesystem is ephemeral).
2. An "auto-added" course is derived, not stored: it has at least one active 202701 section and is not a configured target. No schema marker.
3. `/api/v1/metadata/coverage` keeps meaning configured targets.
4. The validator lists auto-added courses as an allowed category (`INFO auto-added (D-05): N course(s): SUBJ NUM, ...`), and reconciliation is `stored_active == coverage_sum(targets) + auto_added_active_sections == rankings_total`. The allowance needs every active section of the course to be Tampa and `is_undergraduate_number` to be true; a graduate or non-Tampa untargeted course still fails.
5. The D-21 inventory shows their sections as listed exceptions. `08-D21-EXCEPTIONS.md` remains the dated 2026-09-24 record, and the post-sync inventory in plan 09-15 records the new baseline.

## Accomplishments

- Tracer: `_remote_https_origin` (https only, hostname required, no userinfo, path, query or fragment, fixed message "Remote target must be a plain https origin"), `--remote-url` wiring in `main` (mutually exclusive with `--live`, `--smoke`, `--url`, `--http-base-url`; at least 50 iterations), and `_run_remote` using `httpx.Client(timeout=60, trust_env=False, follow_redirects=False)`. One broad query asserts `total > 0`, then 5 warmups and N timed calls run through `_http_search`. Failures print only the exception type. `_http_base_url` and its parametrized tests are untouched.
- The report body was split out of `_report` into `_print_latency` so the remote mode prints the identical Dataset size / Environment / Iterations / p50 / p95 / max format (the environment line names the hosted host, which is a validated plain origin).
- `_run_live` and `verify_rankings_pages.stored_identities` now filter `Section.removed_at IS NULL` (RESEARCH Pitfall 6). Tests build a removed section and show no raise and a PASS verdict.
- `assert_coverage_reconciled` splits untargeted stored keys into auto-added and illegitimate, returns the sorted auto-added keys, and names all four numbers on a mismatch; `main` prints the INFO line just before `PASS reconciliation`. `assert_honest_coverage` joins `Section` and excludes removed sections. The D-21 inventory section query adds `removed_at IS NULL`.
- Verification: `uv run pytest -q` gives 642 passed, 4 skipped; `--smoke` still reports p95; ruff check is clean.

## Task Commits

1. **Task 1: hosted p95 via --remote-url plus active-section reconciliation in benchmark and page scan** - `da5395b` (feat)
2. **Task 2: validator and D-21 inventory account for removed sections and auto-added courses** - `01f5047` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test contradicted the new D-05 rule**
- **Found during:** Task 2
- **Issue:** `test_assert_coverage_reconciled_raises_on_untargeted_course` stored CHM 2045L (an undergraduate Tampa course) without a target and expected a raise. Under the plan's own D-05 rule that layout is a legitimate auto-add, so the old expectation and the plan's "existing tests keep their expectations" line cannot both hold.
- **Fix:** Renamed to `test_assert_coverage_reconciled_auto_adds_untargeted_undergraduate_tampa_course`, asserting the return value `[("CHM", "2045L")]`. The failing behavior is now covered by the new graduate-course and non-Tampa tests (`test_untargeted_graduate_course_fails_reconciliation`, `test_untargeted_non_tampa_course_fails_reconciliation`).
- **Files modified:** tests/refresh/test_validate_tampa_ingest.py
- **Commit:** 01f5047

**2. [Rule 3 - Blocking] Accidental blanket formatter run reverted**
- **Found during:** Task 1
- **Issue:** `ruff format scripts tests` reformatted 16 unrelated tracked files and unrelated hunks of the verify test.
- **Fix:** Reverted each unrelated file individually with `git checkout -- <path>` and re-applied only this plan's edits; the final diffs contain no formatting-only hunks.
- **Commit:** none (never committed)

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3). **Impact:** none on scope; the only change to a pre-existing expectation is the one the plan's own rule forces.

## Known Stubs

None.

## Threat Flags

None. The only new network surface is the operator-run `--remote-url` client covered by T-09-28 (https-only plain origin, no redirects, `trust_env=False`, no DB URL or credentials in remote mode, exception text redacted).

## Issues Encountered

None. Not run: the benchmark against a real hosted host (plan 09-15 owns that measurement).

## Next Phase Readiness

Ready for 09-11. Plan 09-15 can run `uv run python scripts/benchmark_rankings_search.py --remote-url https://<api>.onrender.com --iterations 50` and record the post-sync D-21 inventory as the new baseline.

## Self-Check: PASSED

- Modified files exist and the commits `da5395b` and `01f5047` are in `git log`.
- Acceptance criteria re-run: `--remote-url` exists and reports p50/p95/max; `_http_base_url` tests pass unchanged; live and page-scan tests include a removed section; the validator prints the auto-added INFO line and fails graduate courses; the suffix-exact diff adds only a comment; the inventory test lists the auto-added section as a `no_rows` exception.
- Plan verification: `uv run pytest -q` passed (642 passed, 4 skipped) and `--smoke` prints a p95 figure.
