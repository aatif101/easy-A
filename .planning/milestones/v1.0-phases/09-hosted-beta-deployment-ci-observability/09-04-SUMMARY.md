---
phase: 09-hosted-beta-deployment-ci-observability
plan: 04
subsystem: infra
tags: [whole-term-fetch, chunked-parse, scope, sanity-gate, advisory-lock, httpx, sync-worker]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: plan 09-03 easy_a.sync package root, cadence engine and runner loop
provides:
  - "StaffScheduleClient.search_term, build_whole_term_form_data, WholeTermPage, WholeTermResponseError"
  - "easy_a.sync.fetch: parse_whole_term (chunked, fail-closed), fetch_whole_term, WholeTermParse, FetchedTerm"
  - "easy_a.sync.scope: is_undergraduate_number, apply_scope, ScopeReport, SweepScopeError"
  - "easy_a.sync.gate: GateInput, GateResult, evaluate_gate"
  - "easy_a.sync.lock: SYNC_LOCK_KEY, try_sweep_lock"
  - "tests/sync/wholeterm_html.py: synthetic whole-term HTML builder"
affects: [09-08, 09-10, 09-11, sync-worker]

actuals:
  tokens: 8275
  tasks: 2
  commits: 2
plan_head_before: 52f4e2d84a7ed5ef791b117f5a38fa5b1f63ff9f
plan_head_after: fb1fe639319556886b8966515361226f5fab587c

tech-stack:
  added: []
  patterns:
    - "Whole-term request kept as a separate client method so ScheduleSearchQuery validation stays strict"
    - "Chunked parsing that feeds the unchanged parse_schedule_html and checks parsed rows against td-row count"
    - "Pure gate with exact-decimal threshold comparison (Fraction of the threshold's decimal text)"
    - "Transaction-scoped advisory lock (pg_try_advisory_xact_lock) with a no-op SQLite branch"
    - "Light import graph: no pandas and nothing from easy_a.refresh in fetch, scope, gate, lock"

key-files:
  created:
    - src/easy_a/sync/fetch.py
    - src/easy_a/sync/scope.py
    - src/easy_a/sync/gate.py
    - src/easy_a/sync/lock.py
    - tests/sync/wholeterm_html.py
    - tests/sync/test_fetch.py
    - tests/sync/test_gate.py
    - tests/sync/test_lock_postgres.py
  modified:
    - src/easy_a/schedule/client.py

key-decisions:
  - "build_form_data now delegates to a private _form_fields helper; the narrow output is byte-identical and ScheduleSearchQuery is untouched"
  - "The undergraduate rule lives only in is_undergraduate_number (first four characters are digits and below 5000); apply_scope shares a _has_numeric_prefix helper so unparseable numbers are counted separately from graduate ones"
  - "Gate thresholds are compared as exact decimals, so 'exactly 10 percent' and 'exactly 90 percent' pass regardless of float rounding"
  - "fetch_whole_term keeps only the transport metadata and the parse result; the HTML string is deleted before it returns"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "search_term sends one POST to the Results path with P_SEMESTER=term, P_CAMPUS=T, empty P_SUBJ/P_REF/P_NUM, the identifying User-Agent and a 120 s read timeout; ScheduleSearchQuery without a subject or CRN still raises"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_fetch.py (test_search_term_posts_one_whole_term_request, test_search_term_reports_content_encoding_and_uses_long_read_timeout, test_search_term_does_not_loosen_narrow_query_validation)"
        status: pass
      - kind: unit
        ref: "tests/schedule/test_client.py (unchanged, passes)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A non-HTML Content-Type or a body over the byte cap is rejected before any parsing"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_fetch.py (test_search_term_rejects_non_html_content_type, test_search_term_rejects_oversized_body)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Chunked parse equals a single full parse over 600 rows, tolerates the USF error tail, and fails closed on a missing header or a short row (reporting both counts)"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_fetch.py (test_chunked_parse_equals_single_full_parse, test_error_tail_is_tolerated_and_recorded, test_missing_header_fails_closed, test_short_row_fails_closed_with_both_counts)"
        status: pass
    human_judgment: false
  - id: D4
    description: "apply_scope keeps 0001 and 4999, drops 5000, 6xxx, non-numeric and non-Tampa rows, raises on a duplicate in-scope CRN, and reports the D-03 counts"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_fetch.py (test_is_undergraduate_number, test_apply_scope_keeps_undergraduate_tampa_only, test_apply_scope_rejects_duplicate_in_scope_crn, test_scope_report_counts_on_mixed_sample)"
        status: pass
    human_judgment: false
  - id: D5
    description: "evaluate_gate trips each of its four rules alone just over the threshold, passes at exactly the threshold, never fails because rows were added, and passes the first-sweep catch-up (104 of 3,783)"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_gate.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "try_sweep_lock issues pg_try_advisory_xact_lock on PostgreSQL and returns True on SQLite; a second real connection is excluded until the first transaction ends"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "tests/sync/test_lock_postgres.py (SQLite branch, statement-shape check with a fake PostgreSQL session)"
        status: pass
      - kind: integration
        ref: "tests/sync/test_lock_postgres.py#test_postgres_xact_lock_excludes_a_second_connection_until_commit"
        status: skipped
    human_judgment: true
    rationale: "The two-connection exclusion test needs EASY_A_TEST_POSTGRES_URL. No PostgreSQL is available in this WSL distro, so it was skipped locally and must be seen passing (not skipping) in the 09-01 CI job."

duration: 25min
completed: 2026-09-29
---

# Phase 9 Plan 04: Whole-Term Fetch, Scope, Gate and Lock Summary

**One whole-term Tampa POST, a chunked fail-closed parse of the USF error-tailed response, the D-04 undergraduate scope with a D-03 breakdown, a pure four-rule sanity gate and a pooler-safe transaction advisory lock.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-09-29
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 8 created, 1 modified

## Accomplishments

- `StaffScheduleClient.search_term(term, campus="T")` streams one POST with `httpx.Timeout(120, connect=15)`, checks `Content-Type` contains `text/html`, and aborts the read once the body passes 25,000,000 bytes. It returns a `WholeTermPage` (html, byte count, content type, content encoding, elapsed seconds) so the worker can log bytes and encoding on the first sweeps.
- `build_form_data` is refactored onto a private `_form_fields` helper. Its output is unchanged for narrow queries (the existing client tests pass untouched), and `ScheduleSearchQuery` still rejects a term with no subject or CRN.
- `parse_whole_term` feeds 250-row chunks to the unchanged `parse_schedule_html` and normalizes each row. It fails with `ScheduleParseError` when the header row is missing or when parsed rows differ from the number of `<tr>` blocks holding `<td>` cells (the parser skips short rows silently). The USF error tail is not an error; it is recorded as `tail_error=True`.
- `apply_scope` keeps Tampa rows whose course number starts with four digits below 5000. It counts total rows, distinct CRNs, non-Tampa, graduate, unparseable-number and in-scope rows plus distinct subjects and course keys (`as_dict()` for logging), and raises `SweepScopeError` listing up to 10 CRNs on a duplicate in-scope CRN.
- `evaluate_gate` is pure and returns every failed rule: `zero_rows`, `missing_fraction`, `row_floor`, `subjects_absent`. Thresholds are compared as exact decimals, and the row rules use scoped counts, so a sweep that adds sections never fails.
- `try_sweep_lock` runs `SELECT pg_try_advisory_xact_lock(:key)` on PostgreSQL with the fixed key `0x45415359_4E43` ("EASYNC") and returns True elsewhere.
- Tests use a synthetic builder (`tests/sync/wholeterm_html.py`) that reproduces the live shape (24-cell rows, no `</table>`, USF error `<h3>`). No real USF response is committed.

## Task Commits

1. **Task 1: whole-term client path, chunked fail-closed parse, D-04 scope and D-03 report** - `8bed84a` (feat)
2. **Task 2: sanity gate and transaction-scoped advisory lock** - `fb1fe63` (feat)

## Verification

- `uv run pytest tests/sync tests/schedule -q -rs`: 120 passed, 1 skipped (the PostgreSQL lock test, reason text `Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration`, the text the 09-01 CI no-skip check looks for). Full suite: 501 passed, 4 skipped.
- Import check: importing `easy_a.sync.fetch`, `scope`, `gate` and `lock` leaves `pandas` and every `easy_a.refresh*` module out of `sys.modules`.
- `uv run mypy src`: Success, no issues in 81 source files. `uv run ruff check .`: all checks passed.
- Tracer gate: the tracer's `<verify>` carried only automated checks, so it was re-run end to end (tests, import graph, mypy, ruff) after the Task 1 commit and passed before Task 2 started.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Float threshold comparison could misjudge the exact boundary**
- **Found during:** Task 2 design
- **Issue:** The plan says "passes at exactly the threshold". Comparing against `0.90 * n` or `0.10 * n` in binary floating point can land one ulp on the wrong side for some counts.
- **Fix:** Thresholds are read as exact decimals (`Fraction(str(value))`) before multiplying, so 3,330 of 3,700 and 100 of 1,000 pass and 3,329 and 101 fail.
- **Files modified:** `src/easy_a/sync/gate.py`
- **Commit:** `fb1fe63`

**2. [Rule 2 - Missing critical functionality] Lock statement was untestable without a PostgreSQL server**
- **Found during:** Task 2 verify
- **Issue:** No PostgreSQL is available locally, so the only test proving `pg_try_advisory_xact_lock` (not the session-level variant) is issued would have been skipped everywhere except CI.
- **Fix:** Added a unit test with a fake PostgreSQL-dialect session that asserts the statement text and bound key, plus a check that `SYNC_LOCK_KEY` is a positive bigint spelling "EASYNC".
- **Files modified:** `tests/sync/test_lock_postgres.py`
- **Commit:** `fb1fe63`

**Total deviations:** 2 auto-fixed (1 bug, 1 missing test coverage). **Impact:** none on scope.

## Flagged for user review

1. **Research Open Question 2 (cancelled sections).** USF lists 359 undergraduate cancelled sections (secondary status U or C) and 10 with an unlabelled status R. They appear in the sweep, so they are not "removed" and stay searchable exactly as today. This plan changes nothing about them and adds no label for R. Hiding or labelling cancelled sections is a separate one-line decision for you.
2. **D-04 reversibility (costly).** The undergraduate-only rule touches the sync filter, coverage reporting and D-21 exception accounting if it is widened or narrowed later. It lives in one function, `is_undergraduate_number`, which 09-10 should reuse.
3. **PostgreSQL exclusion test not run locally.** `test_postgres_xact_lock_excludes_a_second_connection_until_commit` skipped here (no local PostgreSQL). Confirm it runs and passes in CI (09-01).

## Authentication Gates

None.

## Known Stubs

None. No placeholder data, empty defaults flowing to UI, or TODO markers in the files created or modified.

## Threat Flags

None. `search_term` is the one new outbound request path and it is the D-22(a) request already in the threat model (T-09-10, T-09-11, T-09-13). It adds no new endpoint, auth path, file access or schema change.

## Next Phase Readiness

- 09-08 (sweep) can call `fetch_whole_term(client, term, now_fn=...)`, then `apply_scope`, build a `GateInput` from three bulk DB reads, call `evaluate_gate`, and take `try_sweep_lock` as the first locking statement of the sweep transaction.
- `FetchedTerm.parse.tail_error`, `byte_count` and `content_encoding` are there for the sweep log line. `ScopeReport.as_dict()` is the D-03 log payload.
- 09-10 should import `is_undergraduate_number` rather than re-deriving the rule.
- Open items for 09-08: pick a sweep-level error kind from `SYNC_ERROR_KINDS` for `WholeTermResponseError` (`usf_response`), `ScheduleParseError` (`parse`), `SweepScopeError` (`scope`) and a failed gate (`gate`). Per RESEARCH Pitfall 3 (A2), if the soak shows an idle-in-transaction timeout, fall back to fetch-then-lock.

## Self-Check: PASSED

- Files present: `src/easy_a/sync/fetch.py`, `scope.py`, `gate.py`, `lock.py`, `src/easy_a/schedule/client.py`, `tests/sync/wholeterm_html.py`, `test_fetch.py`, `test_gate.py`, `test_lock_postgres.py`.
- Commits `8bed84a` and `fb1fe63` exist on `codex/render-setup`; `git rev-list --count` from the recorded base `52f4e2d` gives 2.
- Acceptance criteria re-run: existing `tests/schedule/test_client.py` passes unchanged; MockTransport test asserts empty `P_SUBJ` and `P_CAMPUS` of `T`; 600-row chunk parity; scope boundaries 0001/4999 in and 5000 out; gate boundary tests for all four rules; skip reason text matches verbatim; no real USF response committed.
