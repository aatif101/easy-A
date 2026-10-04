---
phase: 09-hosted-beta-deployment-ci-observability
plan: 01
subsystem: infra
tags: [github-actions, ci, ruff, pytest, postgres, alembic, mypy, vite, render]

requires:
  - phase: 08-student-experience
    provides: "Existing Python/FastAPI backend and React web app whose gates CI now runs"
provides:
  - "GitHub Actions workflow .github/workflows/ci.yml with python and web jobs"
  - "Ruff hard gate passing (two E501 lines wrapped)"
  - "Structural guard tests/test_ci_workflow.py"
affects: [09-13 render blueprint (checksPass trigger, docker job), 09-14 first push / real CI run]

plan_head_before: 2d9a83860f32ff174783e442aa379aa24f308e7d
plan_head_after: be7f87ef145d87b11cfe650754993eb1e00786dc

actuals:
  tokens: 9000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Workflow structure locked by stdlib-only text/regex tests (no PyYAML dependency)"
    - "CI never receives hosted DB credentials or repository secrets; postgres:16 service container only"

key-files:
  created:
    - .github/workflows/ci.yml
    - tests/test_ci_workflow.py
  modified:
    - scripts/refresh_all_tampa.py
    - src/easy_a/refresh/cleanup.py

key-decisions:
  - "D-12 implemented as written: both `mypy src` and `mypy .` are report-only (continue-on-error). Promoting `mypy src` to a hard gate is flagged for user review (research Open Question 5) and NOT applied."
  - "Push trigger uses branches ['**'] with no path filters so every commit gets checks for Render checksPass (D-13, Pitfall 10)."
  - "The no-skip guard greps pytest -rs output for the shared PostgreSQL skip reason rather than deselecting or marking tests."

patterns-established:
  - "E501 fixed by wrapping only; no noqa or per-file-ignores"
  - "Third-party actions pinned to exact tags; permissions: contents: read"

requirements-completed: [REQ-OPS-01]

coverage:
  - id: D1
    description: "Ruff is clean: the two pre-existing E501 lines wrapped without behaviour change or suppression"
    requirement: REQ-OPS-01
    verification:
      - kind: other
        ref: "uv run ruff check ."
        status: pass
      - kind: unit
        ref: "uv run pytest -q (382 passed, 3 skipped, no regressions)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CI workflow with python job (ruff, alembic round-trip, pytest on postgres:16, no-skip check) and web job (lint, typecheck, test, build), report-only mypy"
    requirement: REQ-OPS-01
    verification:
      - kind: unit
        ref: "tests/test_ci_workflow.py (13 tests)"
        status: pass
      - kind: other
        ref: "web/node_modules/.bin/js-yaml .github/workflows/ci.yml"
        status: pass
      - kind: other
        ref: "npm --prefix web run lint/typecheck/test and build with VITE_USE_MOCK_DATA=false"
        status: pass
    human_judgment: false
  - id: D3
    description: "The workflow actually runs green on GitHub Actions with the postgres service, and the three PostgreSQL integration tests execute"
    requirement: REQ-OPS-01
    verification: []
    human_judgment: true
    rationale: "Requires a real GitHub Actions run; happens when the branch is pushed in plan 09-14. Docker/Postgres are not available locally, so the alembic round-trip and PostgreSQL tests were not run here."

duration: 2min
completed: 2026-09-29
status: complete
---

# Phase 9 Plan 01: CI Workflow and Ruff Clean-up Summary

**GitHub Actions CI with ruff, Alembic round-trip and full pytest against a postgres:16 service (with a no-skip guard), web lint/typecheck/test/build, and report-only mypy; guarded by a stdlib structural test.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-09-29T17:06:10Z
- **Completed:** 2026-09-29T17:07:32Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Wrapped the two pre-existing E501 lines (`scripts/refresh_all_tampa.py` help string, `cleanup._dependent_ids` annotation); `uv run ruff check .` now prints "All checks passed!" with no noqa or ignore added.
- Added `.github/workflows/ci.yml`: triggers on every push and PR, no path filters, read-only token, no secrets, main runs never cancelled.
- `python` job: postgres:16 service (same image/credentials/health check as docker-compose.yml), ruff, alembic upgrade/downgrade -1/upgrade, `pytest -q -rs` tee'd to a file, and a step that fails if the PostgreSQL skip reason appears.
- `web` job: npm ci, lint, typecheck, vitest, production build with `VITE_USE_MOCK_DATA=false` and a dummy https `VITE_API_BASE_URL`.
- `mypy src` and `mypy .` run report-only with `continue-on-error: true`.
- `tests/test_ci_workflow.py` (13 tests) locks triggers, pins, services, no path filters, no secrets/hosted DATABASE_URL, exactly two jobs, report-only mypy, and that hard gates are not continue-on-error.

## Task Commits

1. **Task 1: Python gates run end to end (tracer)** - `eeb4320` (feat)
2. **Task 2: Frontend gates and report-only mypy** - `be7f87e` (feat)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified
- `.github/workflows/ci.yml` - CI workflow (python and web jobs)
- `tests/test_ci_workflow.py` - structural invariants of the workflow
- `scripts/refresh_all_tampa.py` - `--subject-timeout` help string split across adjacent literals (text unchanged once concatenated)
- `src/easy_a/refresh/cleanup.py` - `_dependent_ids` `model:` union annotation wrapped in parentheses

## Decisions Made
- **Open Question 5 flag (pending user review):** `mypy src` reports 0 errors today ("Success: no issues found in 73 source files", re-verified) and would protect the upcoming sync code as a hard gate, but D-12 says report-only, so it is implemented report-only. Promotion is a one-line change: remove `continue-on-error: true` from the "mypy src" step (and update `test_mypy_steps_are_report_only`). D-11..D-13 remain Claude's lean for the user to review later.
- No other decisions beyond the plan.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- The local venv uses Python 3.14 while CI pins 3.12; full local suite passes (382 passed, 3 skipped), so no impact observed.
- The tracer gate was evaluated in default mode: the tracer `<verify>` is automated-only, so it was re-run (ruff, workflow tests, YAML parse, full pytest) and passed before expansion.

## Verification Results
- `uv run ruff check .` - All checks passed
- `uv run pytest -q` - 382 passed, 3 skipped (the 3 skips are the PostgreSQL tests; they run in CI)
- `uv run pytest tests/test_ci_workflow.py -q` - 13 passed
- `js-yaml .github/workflows/ci.yml` - parses
- `npm run lint / typecheck / test / build` (mock data off) - all exit 0
- `uv run mypy src` - Success: no issues found in 73 source files
- Not verifiable locally: the Alembic round-trip and PostgreSQL integration tests (no Docker/Postgres); the first real run happens in plan 09-14.

## Known Stubs

None.

## Threat Flags

None - no new surface beyond the plan's threat model (T-09-01..T-09-03 mitigated: exact action pins, `permissions: contents: read`, no secrets, no path filters, no cancel on main).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Workflow exists for plan 09-13 to reference (`checksPass`) and extend with the `docker` job.
- The first real CI run (proving the postgres service and the three integration tests) is pending the push in plan 09-14.

## Self-Check: PASSED

- FOUND: .github/workflows/ci.yml, tests/test_ci_workflow.py
- FOUND commits: eeb4320, be7f87e

---
*Phase: 09-hosted-beta-deployment-ci-observability*
*Completed: 2026-09-29*
