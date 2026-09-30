---
phase: 09-hosted-beta-deployment-ci-observability
plan: 16
subsystem: sync
tags: [sync-gate, gap-closure, cr-01, runbook, operator-override]
status: complete
gap_closure: true

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-11 worker CLI and --max-missing-fraction; 09-12 runbook section 4; sync gate and sweep from phase 7"
provides:
  - "gate_thresholds(override) maps one operator fraction onto every size rule of the sweep gate (CR-01)"
  - "run_sweep(max_missing_fraction: float | None = None) evaluates the gate with all four thresholds"
  - "Runbook section 4 gate row and a Gate refusal playbook whose steps actually clear a legitimate mass removal"
affects: [phase-9-reverification, hosted-worker]

actuals:
  tokens: 4200
  tasks: 3
  commits: 3
plan_head_before: c8d8b141cba33436cbbc003f5ac008ba4bfe8d3e
plan_head_after: 3c71b04f1abe48a0adc08af5d24231f6d681186f

tech-stack:
  added: []
  patterns:
    - "Threshold mapping as a pure function (gate_thresholds) feeding evaluate_gate keywords; evaluate_gate body unchanged"
    - "Exact-decimal complement via Fraction so the 1 - X row floor has no float error (0.7 -> exactly 0.3)"

key-files:
  created: []
  modified:
    - src/easy_a/sync/gate.py
    - src/easy_a/sync/sweep.py
    - src/easy_a/sync/cli.py
    - tests/sync/test_gate.py
    - tests/sync/test_cli.py
    - docs/runbooks/hosted-beta-operations.md

key-decisions:
  - "Override semantics follow the planner's table: X at or below 0.10 changes only max_missing_fraction; X above 0.10 also sets min_row_ratio = 1 - X (exact decimal) and max_absent_subject_fraction = X; min_absent_subjects stays 2; zero_rows is never overridable; X outside [0, 1] raises ValueError."
  - "None means no override everywhere (run_sweep default, CLI flag absent, worker loop); tested with `is None` so 0.0 stays a real override."

requirements-completed: []

duration: about 3 min of executor wall time
completed: 2026-09-30
---

# Phase 9 Plan 16: CR-01 Gate Override Recovery Summary

**`--once --max-missing-fraction 0.9` now clears a legitimate mass removal when a prior succeeded IngestRun exists (the hosted configuration): one operator fraction is mapped onto the missing-fraction, row-floor and absent-subject rules, the no-flag gate is unchanged and pinned by tests, and runbook section 4 gives steps that work.**

## Performance

- **Duration:** about 3 min executor wall time
- **Tasks:** 3 of 3
- **Files modified:** 6 (scope check against plan_head_before lists exactly the six `files_modified`)

## Accomplishments

- **Tracer (Task 1, `c8b813b`).** Added `DEFAULT_*` constants, frozen `GateThresholds` and `gate_thresholds(override)` to `gate.py`; `evaluate_gate`'s body and default values are identical (its keyword defaults now reference the constants). `run_sweep` and `_sweep_in_transaction` take `float | None` and pass all four thresholds to the gate. The CLI forwards `args.max_missing_fraction` unchanged (None when absent) and imports the default constant from `gate.py`. The worker loop's `run_sweep(session_factory, term=term, client=client, now_fn=now_fn)` line is unchanged (grep count 1).
- **Complete semantics (Task 2, `458029d`).** Above 0.10 the override also scales `subjects_absent`; out-of-range input raises `ValueError` naming the value. `--max-missing-fraction` help now states what it relaxes (row floor, absent subject limit, empty response always refused, cadence floor untouched). Tests pin the no-flag gate fail-closed on the production path and prove the next default sweep passes after an override sweep.
- **Runbook (Task 3, `3c71b04`).** Section 4 `gate` row names the four rules and drops "header change". New `### Gate refusal: legitimate mass removal` playbook with the per-rule table and nine steps (suspend, dry run, truncation check, verify CRNs, choose X, dry run under X, wait one tier interval, `--once` under X, Run Log row, resume). Standing rules bullet no longer contradicts section 3 on dry runs.

## RED run (Task 1, before implementation)

- `tests/sync/test_cli.py -k prior_succeeded`: both parametrizations failed with `assert 1 == 0`; the log showed `sweep failed: gate: row_floor 8 below 90% of 13` and `gate_reasons: ['row_floor 8 below 90% of 13']`, error_kind `gate`. This is the CR-01 reproduction on the seeded-prior-success path.
- `tests/sync/test_gate.py` failed at collection: `ImportError: cannot import name 'gate_thresholds' from 'easy_a.sync.gate'`.
- Task 2 RED: 5 failures before implementation (`test_override_above_default_relaxes_every_size_rule`, `test_override_scales_the_absent_subject_limit` with `subjects_absent 30 above 2`, two `test_override_out_of_range_raises`, `test_help_describes_what_the_gate_override_relaxes`). The no-flag pins (`..._refuses_..._after_a_prior_succeeded_sweep`, default-equality) passed immediately, as expected for behaviour that must stay unchanged.

## Verification

- `uv run pytest -q`: 706 passed, 4 skipped (Postgres lock test and similar skip locally, expected).
- `uv run ruff check .`: all checks passed. `uv run ruff format --check` on the five changed Python files: clean.
- `uv run mypy src`: no issues in 87 source files (`src/easy_a/sync`: no issues in 13).
- `gate_thresholds(None) == gate_thresholds(0.10) == GateThresholds(0.10, 0.90, 0.02, 2)` and `gate_thresholds(0.9) == GateThresholds(0.9, 0.1, 0.9, 2)`: confirmed.
- `python -m easy_a.sync --help` exits 0 and shows the new help (argument parsing only, no engine).
- Runbook section 4 content check and the `does not rate-limit repeated dry runs` grep (count 1): pass.
- No hosted Supabase or Render access, no push.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Out-of-scope reformat reverted**
- **Found during:** Task 3 (scope check)
- **Issue:** `uv run ruff format tests/sync` in Task 2 also stripped a trailing blank line in `tests/sync/test_diff_apply.py`, which is not a plan file.
- **Fix:** `git checkout -- tests/sync/test_diff_apply.py` before any commit; it was never staged.
- **Files modified:** none net
- **Commit:** n/a

**2. [Rule 3 - Blocking] Import block spacing**
- **Found during:** Task 1 lint
- **Issue:** ruff I001 on `gate.py` (two blank lines needed between the imports and the new constants block).
- **Fix:** `ruff check --fix` on `gate.py`; committed with Task 1.

**Total deviations:** 2 auto-fixed (both trivial tooling). **Impact:** none on behaviour or scope.

## Issues Encountered

- `tests/sync/test_cli.py::test_loop_sweeps_once_then_stops_cleanly_on_the_stop_event` failed once in a four-test run (after the Task 1 reformat) and passed in every other run, including three consecutive isolated runs and the full suite. It uses a 0.05 s `threading.Timer` race and exercises the unchanged loop path; treated as a pre-existing timing flake, not caused by this plan, and not touched (out of scope).

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path, file access or schema change. The override only changes thresholds for the manual `--once`/`--dry-run` operator path.

## Notes for the orchestrator

- REQUIREMENTS.md was not marked complete (`requirements-completed: []`); re-verification of ROADMAP criterion 3 / CR-01 owns that.
- Commits are local on `codex/render-setup`. Nothing pushed. A merge to `main` redeploys `easy-a-api` and `easy-a-worker` (src/** buildFilter, checksPass), and the redeployed worker behaves identically because the loop has no override path.
- Out of scope and untouched: the accepted 30 s gap, WR-01..WR-08, IN-*, NEB 0001.

## Self-Check: PASSED

- Files exist: gate.py, sweep.py, cli.py, test_gate.py, test_cli.py, hosted-beta-operations.md (all modified, present).
- Commits exist: c8b813b, 458029d, 3c71b04.
- `git rev-list --count c8d8b14..HEAD` = 3 before this SUMMARY commit (matches `actuals.commits`).
