---
phase: 09-hosted-beta-deployment-ci-observability
verified: 2026-09-30T21:10:00Z
status: gaps_found
score: 8/9 must-haves verified
covered_files:
  - .github/workflows/ci.yml
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-01-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-01-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-02-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-02-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-03-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-03-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-04-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-04-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-05-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-05-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-06-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-06-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-07-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-07-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-08-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-08-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-09-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-09-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-10-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-10-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-11-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-11-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-12-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-12-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-13-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-13-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-14-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-14-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-15-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-15-SUMMARY.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-16-PLAN.md
  - .planning/phases/09-hosted-beta-deployment-ci-observability/09-16-SUMMARY.md
  - docs/runbooks/hosted-beta-operations.md
  - render.yaml
  - src/easy_a/sync/cli.py
  - src/easy_a/sync/gate.py
  - src/easy_a/sync/sweep.py
  - tests/sync/test_cli.py
  - tests/sync/test_gate.py
covered_digest: "v2:sha256:3d01c11a6ab48ba35e3c899cde26558e87aa3d0d7cb1c7c8ddb8a9c3f59f4191"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "each sweep takes under 30 s end to end"
    scope: "duration clause only; the memory clause of the same must-have is unaffected"
    reason: "Operator accepted the gap (2026-09-30) rather than investigate. Basis recorded: hosted sweeps of 37.166-50.69 s fit inside a 300-3600 s cadence and no roadmap criterion depends on 30 s; the cause of the slower hosted time was not established."
    accepted_by: "aatif101"
    accepted_at: "2026-09-30T20:27:43Z"
re_verification:
  previous_status: gaps_found
  previous_score: 7/9
  gaps_closed:
    - "30 s sweep duration: closed by the operator override above (recorded and applied, duration clause only)"
    - "CR-01 in code: gate_thresholds maps the operator fraction onto row_floor and subjects_absent (committed on local branch codex/render-setup only)"
  gaps_remaining:
    - "ROADMAP criterion 3 for the HOSTED system: the CR-01 fix and the corrected runbook are not on origin/main and not deployed to the Render worker/API"
  regressions: []
gaps:
  - truth: "ROADMAP criterion 3: an operator can follow the runbook to recover from a failed refresh (runbook section 4, kind 'gate'), on the hosted system"
    status: partial
    reason: "FIXED IN BRANCH, PENDING MERGE AND DEPLOY. The code fix (commits c8b813b, 458029d) and the rewritten runbook playbook (3c71b04) exist only on local branch codex/render-setup (HEAD 0873efc). origin/codex/render-setup is still 79f9efd (nothing pushed) and origin/main is b485efb, which the hosted worker and API run. `git diff origin/main -- src/easy_a/sync/gate.py` shows the whole change. On main, `--max-missing-fraction` still forwards only max_missing_fraction to the gate, so the CR-01 failure (row_floor and subjects_absent not clearable after a prior succeeded IngestRun) is still live on the hosted system, and the main-branch runbook still gives the broken instruction. Hosted IngestRuns 113, 114 and 115 all succeeded, so the row_floor baseline is set in production. CI has also never run against the fix (the branch was not pushed; evidence is local pytest only)."
    artifacts:
      - path: "src/easy_a/sync/gate.py"
        issue: "gate_thresholds exists only on codex/render-setup, not on origin/main"
      - path: "src/easy_a/sync/sweep.py"
        issue: "run_sweep on main still passes only max_missing_fraction to evaluate_gate"
      - path: "docs/runbooks/hosted-beta-operations.md"
        issue: "main version still lacks the Gate refusal playbook; branch version describes behaviour the deployed worker does not have"
    missing:
      - "Push codex/render-setup, open and merge a PR to main (CI must pass on the new head), then let Render redeploy easy-a-api and easy-a-worker (src/** buildFilter, checksPass)"
      - "After deploy, confirm the hosted worker is on the merge commit (Render dashboard or a worker_started log line) and re-run this verification; no further code work is expected"
      - "Close WINDOWS.md entry 10 (30 s gap, now an operator-accepted override)"
deferred: []
human_verification:
  - test: "Student-facing freshness line on the hosted site"
    expected: "Open https://easy-a-web.onrender.com, pick Spring 2027. 'Updated N min ago' under the current tier, no stale warning, search works, removed CRN 10525 not listed."
    why_human: "The operator said 'approved' without itemized results and the executor never opened the UI. The API it reads is live and correct (verified here)."
  - test: "Render failure-email notifications (D-09)"
    expected: "Workspace Settings, Notifications: failed-deploy and service-failure emails cover easy-a-api, easy-a-web and easy-a-worker."
    why_human: "Dashboard only; not readable by CLI or API."
  - test: "Worker memory in Render Metrics"
    expected: "Peak memory under the 350 MB target and no OOM events over the soak."
    why_human: "Only self-reported peak_rss_mb (193.6, 223.4) is independently evidenced; the Metrics figure was stated as 'under 350 MB' with no number. Sweep 3's peak_rss_mb is in the worker log, which I cannot read."
  - test: "Instructor changes against the USF schedule page"
    expected: "Two or three Staff-to-named sections match the USF schedule search by hand."
    why_human: "Automation compared API to DB only; a USF request from tooling would exceed D-22."
  - test: "Rehearse the gate recovery on the hosted system after the merge and deploy"
    expected: "Optional: a dry run with --dry-run --max-missing-fraction X on the deployed image prints the new help text and exits 0 with empty gate_reasons on a normal response."
    why_human: "Needs a Render shell or workstation with DATABASE_URL, and a real USF request (D-22). No failed sweep has ever occurred on the hosted system, so no recovery has been rehearsed."
---

# Phase 9: Hosted Beta, Deployment, CI, Observability: Verification Report (re-verification)

**Phase Goal:** The corrected application runs as a hosted beta with enough automation and measurement to keep it running.
**Verified:** 2026-09-30T21:10:00Z
**Status:** gaps_found
**Re-verification:** Yes, after gap closure plan 09-16 and the operator override for the 30 s clause

I kept the hypothesis that the goal was missed and checked the code, tests, git history, the hosted API and the hosted database (READ ONLY transaction, `transaction_read_only = on`). Nothing on Render was changed, no sweep was triggered, nothing was pushed or written, nothing was committed.

## The honesty decision: criterion 3 and the unmerged fix

**ROADMAP criterion 3 cannot be marked VERIFIED for the hosted system. It is reported as fixed-in-branch, pending merge and deploy, and the phase is therefore `gaps_found`, not `passed`.**

Evidence, from git, not the SUMMARY:

- `git log origin/main` head is `b485efb` (Merge PR 34). The 09-16 commits `c8b813b`, `458029d`, `3c71b04` (plus docs `a46b93e`, `0873efc`) are in `origin/main..HEAD` only.
- `git branch -r --contains c8b813b` returns nothing: the commits are not on any remote branch. `git ls-remote origin codex/render-setup` is `79f9efd`, so the branch itself was never pushed. CI has therefore never run against the fix.
- `git diff origin/main -- src/easy_a/sync/gate.py src/easy_a/sync/sweep.py src/easy_a/sync/cli.py docs/runbooks/hosted-beta-operations.md` carries the entire change (gate +49, sweep +18, cli, runbook +27). On main the override is still the CR-01 shape.
- The hosted worker and API run `b485efb` (09-ROLLOUT-EVIDENCE.md; Render deploys from main via checksPass, `src/**` buildFilter). The running worker has the old gate.

Consequence: the CR-01 defect is still live in production. The runbook on main still tells the operator to use an override that cannot clear `row_floor` or `subjects_absent` after a prior succeeded sweep, and the hosted database has three (IngestRuns 113 to 115). The branch runbook, read as written, describes a CLI that the deployed worker does not implement. The remedy needs no new engineering: push, pass CI, merge, redeploy, re-verify.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP 1: hosted beta reachable, serves real data | VERIFIED | Re-checked 21:01Z: `/health` `{"status":"ok"}`, web 200, search returns real sections, sync-status live. DB active sections 3,703, same as the earlier API total. |
| 2 | ROADMAP 2: CI runs Python and frontend checks on push | VERIFIED | Unchanged from the initial verification: `.github/workflows/ci.yml` (python, web, docker jobs), green on main and PR branches. The CR-01 branch head has no CI run (not pushed); see gap. |
| 3 | ROADMAP 3: an operator can follow the runbook to refresh data and recover from a failed refresh | PARTIAL: fixed in branch, NOT on main, NOT deployed (see decision above) | In the branch the fix is correct and complete (evidence below). On the hosted system the `gate` recovery is still non-functional. Not counted as verified. |
| 4a | ROADMAP 4: seats, instructors, existence within one cadence interval of USF | VERIFIED | Three hosted sweeps now: 113 (18:23:25Z), 114 (19:32:01Z), 115 (20:38:57Z), all `succeeded`. Gaps 68.6 and 66.9 min against a 60 min cadence (D-01 jitter, inside +/-20%). `is_stale` false at 21:01Z, `failures_last_24h` 0. |
| 4b | ROADMAP 4: an unchanged sweep writes no instructor or seat rows | VERIFIED | New data point: sweep 115 reported 10 sections "updated", 0 inserted, and wrote only 2 `section_instructors` rows and 1 `seat_snapshots` row (observed_at 20:38 to 20:41Z window; read-only count). Sweep 114 wrote 11 and 6. Growth tracks real changes, not sections touched. Backed by the passing `tests/sync` run. |
| 4c | ROADMAP 4: removed sections leave search | VERIFIED | 0 `section_rankings` rows belong to a section with `removed_at` set (re-queried). Active count 3,703. (WR-07 remains: the invariant depends on cache-row deletion, not a route guard.) |
| 4d | ROADMAP 4: UI shows when data was last verified | VERIFIED in code; human check still open | `SyncStatus` rendered in `web/src/App.tsx`, fed by live `/metadata/sync-status` (`last_success_at` 20:39:24Z, not stale). Hosted UI itemized check is human item 1. |
| 5 | 09-15: hosted search p95 below 1,500 ms, single-client | VERIFIED (recorded evidence) | 212.56 ms over 50 calls per 09-ROLLOUT-EVIDENCE.md; not re-run. |
| 6 | 09-15: worker under 512 MB plan with no OOM AND each sweep under 30 s | PASSED (override) for duration; memory half VERIFIED on self-report | Duration clause: operator override 2026-09-30T20:27:43Z recorded in frontmatter and applied, scoped to the duration clause only. Extra data point, not needed for the override: sweep 115 took 27.209 s (20:38:57.48 to 20:39:24.69Z, READ ONLY `ingest_runs`), under 30 s, so the steady-state sweep now meets the bar the first two missed (50.69 s, 37.17 s). Memory half: self-reported `peak_rss_mb` 193.6 and 223.4; Render Metrics figure still human item 3. |
| 7 | 09-15: restart logs `worker_stopped` and the new instance does not sweep at once | VERIFIED | Sweep 115 started 20:38:57.48Z, exactly the `next_start_at` (20:38:57Z) recorded before the restart, and no IngestRun falls between 114 and 115. This independently confirms the new instance waited out the persisted cadence. |
| 8 | 09-15: first sweep succeeded; catch-up recorded; removed absent; auto-added courses never show course history (D-20) | VERIFIED | IngestRun 113 `succeeded` (3,702 seen, 24 inserted, 560 updated); 115 `succeeded` 3,704 seen. Unchanged from the initial verification. |
| 9 | 09-15: STATE.md records the new live facts; 08-D21-EXCEPTIONS.md untouched | Accepted | Not goal-critical; unchanged from the initial verification. |

**Score:** 8/9 truths verified (truth 6 counted as PASSED (override) for its duration clause; truth 3 partial). 0 present-but-behavior-unverified.

### CR-01 verification against the actual code (not the SUMMARY)

Code read in full: `src/easy_a/sync/gate.py`, the `gate_thresholds` call in `sweep.py` (lines ~258-275), `cli.py` `_run_single_sweep`, `_run_worker_loop`.

Reproductions executed here (`uv run python`, pure functions, no I/O):

| Case | Result |
|---|---|
| Reviewer's case, `evaluate_gate(GateInput(500,1000,500,1000,S,S))` with defaults | `passed=False`, reasons `missing_fraction 0.500 above 0.100 ...` and `row_floor 500 below 90% of 1000` (fails closed, as before) |
| Same input with `gate_thresholds(0.9)` | `GateThresholds(0.9, 0.1, 0.9, 2)`; `passed=True, reasons=()` |
| `gate_thresholds(None) == GateThresholds(0.10, 0.90, 0.02, 2)` and `== gate_thresholds(0.10)` | True, True: default path unchanged |
| X=0.0 | `GateThresholds(0.0, 0.9, 0.02, 2)`: only missing_fraction changes, tightening preserved |
| X=0.7 boundary | 300 of 1000 passes, 299 fails (exact decimal, `min_row_ratio` exactly 0.3) |
| `zero_rows` with X in {0.0, 0.5, 0.9, 1.0} on an empty scoped response | always `passed=False`, `zero_rows` always present: never overridable |
| X=-0.1 and X=1.1 | `ValueError: gate override must be between 0 and 1` |
| Truncated response (50 of 100 subjects gone), defaults | `subjects_absent 50 above 2` refuses |
| Same truncated response, X=0.9 | `passed=True` (see note below); X=0.3 still refuses on `subjects_absent 50 above 30` |

Wiring checks:

- `evaluate_gate`'s body is byte-identical to main; only its keyword defaults now reference the four `DEFAULT_*` constants, whose values are 0.10, 0.90, 0.02, 2 (the old literals). `git diff origin/main -- gate.py` confirms.
- `grep "run_sweep(" src`: two call sites. `cli.py:390` (`--once`/`--dry-run`) passes `max_missing_fraction=args.max_missing_fraction` (None when the flag is absent). `cli.py:438` (worker loop) is `run_sweep(session_factory, term=term, client=client, now_fn=now_fn)`: no override path. `_parse` still rejects `--max-missing-fraction` outside `--once`/`--dry-run` (`cli.py:171`).
- Cadence floor code (`latest_sweep_start`, `earliest_next_start`, exit 3) is untouched by the diff.
- Tests: `uv run pytest tests/sync tests/test_ci_workflow.py tests/test_deploy_config.py tests/api/test_sync_status.py` gives 235 passed, 1 skipped. The named CR-01 tests (`test_override_applies_a_mass_removal_after_a_prior_succeeded_sweep` for `--once` and `--dry-run`, `test_default_gate_refuses_...`, `test_next_default_sweep_passes_after_an_override_sweep`, `test_help_describes_...`) pass. Red-on-old-code check: I ran the new `test_cli.py` against an `origin/main` worktree source; `-k prior_succeeded` failed, so the tests really detect CR-01 (temporary worktree, removed afterwards).

Note on the override's blast radius (not a gap, design consequence): above 0.10 a large X also relaxes `subjects_absent`, so at X=0.9 a response missing half the subjects passes. That is by design (the plan's table) and the runbook steps 3 and 4 put the truncation check (a subject USF still lists) and a by-hand CRN check before any override. It is the operator's check, not a code barrier. Removals are reversible (`removed_at`, `--restore-crn`).

### Runbook "Gate refusal: legitimate mass removal" against real CLI behaviour

Read against `cli.py`, `sweep.py` and the test suite:

- Flags and scope: `--max-missing-fraction` only with `--once`/`--dry-run` (true, `_parse`), worker loop uses defaults (true, `cli.py:438`), never changes the cadence floor (true). X between 0 and 1 (true, `_fraction_arg`).
- Per-rule table matches `gate_thresholds` exactly (table cases above reproduced).
- Exit codes: exit 3 = refused by floor with the earliest time printed (true, `EXIT_REFUSED`, `print("refused: next sweep allowed at ...")`); `--once` success exit 0 (true); a failed gate sweep exits 1.
- Dry run: makes the real USF request, runs in a read-only transaction and, on a gate refusal, `_record_failure` skips the IngestRun when `dry_run` is true (`sweep.py:364`), so a refused dry run moves neither the floor nor `/sync-status`; `gate_reasons` are printed in the JSON line. The runbook's claims that dry runs record nothing and are not rate-limited by the tool are true, and the Standing rules bullet no longer contradicts section 3.
- Step 7's "wait one tier interval" after the dry run is operator discipline, not something the tool enforces (the tool's floor counts recorded IngestRuns only). The runbook states this honestly.
- Step 9's claim that the next automatic sweep passes at defaults is backed by `test_next_default_sweep_passes_after_an_override_sweep` and by `load_db_state` (`last_success_records_seen` is the newest succeeded run).
- Step 1 (suspend the worker first) is consistent with the advisory lock and with failed-sweep IngestRuns advancing the floor.

The playbook is accurate for the branch code. It is not accurate for the deployed worker until merged and deployed.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/easy_a/sync/gate.py` | `gate_thresholds`, `GateThresholds`, `DEFAULT_*` | VERIFIED on branch; ABSENT on main | Substantive and wired (sweep imports and calls it). |
| `src/easy_a/sync/sweep.py` | `run_sweep(max_missing_fraction: float | None)` using `gate_thresholds` | VERIFIED on branch | Wired into `evaluate_gate`, all four thresholds passed. |
| `src/easy_a/sync/cli.py` | flag passed as None or X; help text | VERIFIED on branch | |
| `tests/sync/test_gate.py`, `tests/sync/test_cli.py` | override table, reviewer case, CR-01 reproduction | VERIFIED | Pass here; fail against main source. |
| `docs/runbooks/hosted-beta-operations.md` | corrected section 4 and playbook | VERIFIED on branch; main has the old text | |
| `.github/workflows/ci.yml`, `render.yaml`, `SyncStatus.tsx`, migration `0004_sync_removed_at` | as initial verification | VERIFIED | Unchanged. |
| `09-ROLLOUT-EVIDENCE.md` | dated evidence | VERIFIED | Sweep 3 is now also observable; not yet added to the evidence file. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli._run_single_sweep` | `sweep.run_sweep` | `max_missing_fraction=args.max_missing_fraction` | WIRED (branch) | None when flag absent |
| worker loop | `run_sweep` | no override argument | WIRED, no override path | `cli.py:438` |
| `sweep._sweep_in_transaction` | `gate.evaluate_gate` | `gate_thresholds(...)`, four keywords | WIRED (branch) | |
| override sweep's succeeded IngestRun | next sweep's `row_floor` baseline | `load_db_state.last_success_records_seen` | WIRED | tested |
| branch fix | hosted worker | merge to main and Render redeploy | NOT WIRED | origin/main `b485efb`; fix unmerged, unpushed |
| easy-a-web, worker, sweep-to-cache links | as initial verification | | WIRED | Unchanged; sweep 115 adds a third run under `usf_schedule_sync:202701`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| SyncStatus | `last_success_at`, `is_stale` | `IngestRun` 115 via `/metadata/sync-status` (live 21:01:15Z) | Yes | FLOWING |
| Search results | instructor, seats | worker-written rows; sweep 115 appended 2 instructor and 1 seat row | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Sync, status, CI, deploy tests | `pytest tests/sync tests/test_ci_workflow.py tests/test_deploy_config.py tests/api/test_sync_status.py -q` | 235 passed, 1 skipped | PASS |
| Reviewer's CR-01 case, branch code | `evaluate_gate(... ) with gate_thresholds(0.9)` | passed | PASS (branch) |
| Reviewer's case, defaults | same input, no override | `missing_fraction` and `row_floor` refusals | PASS (fail closed) |
| zero_rows never overridable | X in {0, .5, .9, 1} | always refused | PASS |
| CR-01 tests detect the bug | new test_cli against main source | 1 failed | PASS (RED on old code) |
| Hosted health and freshness | GET `/health`, `/metadata/sync-status` | ok; `last_success_at` 20:39:24Z, not stale | PASS |
| Sweep 3 duration | READ ONLY `ingest_runs` | 115: 27.209 s | PASS (extra data point) |
| Fix present on origin/main | `git diff origin/main -- src/easy_a/sync/gate.py` | 49-line diff: absent | FAIL for the hosted system |

The full workspace suite was not re-run here; the executor reported 706 passed, 4 skipped, and the targeted suites above pass.

### Probe Execution

No phase-declared `probe-*.sh` scripts; step skipped.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| REQ-OPS-01 | 09-01, 06, 10, 11, 13, 14, 15, 16 | PARTIALLY SATISFIED (hosted) | Deploy, CI, request logging, sync-status, p95 verified. Runbook recovery correct in branch, not deployed. Failure-email notifications rest on operator confirmation. REQUIREMENTS.md still shows `[ ]`; do not tick until the merge and deploy are verified. |
| REQ-SYNC-01 | 09-02 to 09-08, 11, 12, 14, 15, 16 | SATISFIED (functionally) | Three hosted sweeps, change-only writes, removals out of search, UI freshness wired. The 30 s clause is an accepted override. The default gate remains fail-closed. |

No orphaned Phase 9 requirement IDs. Plans 01 to 16 all have SUMMARYs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| TBD/FIXME/XXX in files modified by 09-16 | | none found | None | |
| `cli.py`, `schedule/client.py`, sync runner | | WR-01..WR-08, IN-01..IN-04 (deliberately deferred, all `open` in 09-REVIEW-DISPOSITION.md) | Warning (known) | None breaks a must-have. WR-01 (URL scrub corrupts failed-sweep JSON) means `gate_reasons` in a failed sweep's log line may be damaged; the operator can still read the reasons from `--dry-run` (step 2) or `error_detail`, so the playbook survives it. |
| hosted worker on main | | NEB 0001 fails every sweep (`records_failed` 1, WINDOWS 11) | Warning (known) | Students cannot find its sections; not a must-have. |

### Human Verification Required

Unchanged from the initial verification, except sweep 3 is now checked read-only (done above, 27.2 s, change-only writes).

1. **Hosted UI freshness line and search.** Open https://easy-a-web.onrender.com, pick Spring 2027. Expect "Updated N min ago", no stale warning, search works, removed CRN 10525 absent. The operator said "approved" with no itemized results.
2. **Render failure-email notifications (D-09).** Confirm failed-deploy and service-failure emails cover all three services. Dashboard only.
3. **Render Metrics worker memory.** Peak under 350 MB, no OOM. Only self-reported 194 to 223 MB is evidenced.
4. **Instructor names against the USF page by hand** for two or three Staff-to-named sections.
5. **After merge and deploy:** optional rehearsal of the gate recovery on the deployed image (see frontmatter).

### Gaps Summary

What changed since the first report:

- The 30 s sweep-duration must-have is closed by the operator's recorded override (duration clause only). Sweep 3 (IngestRun 115) took 27.2 s, so the gap may also be shrinking on its own; this is informational and does not alter the override.
- CR-01 is fixed correctly in code and tests, and the new runbook playbook matches real CLI behaviour (flags, exit codes 0/1/3, cadence floor, dry-run semantics).

What keeps the phase from `passed`:

- **ROADMAP criterion 3 is not met on the hosted system.** The fix and the runbook are only on local branch `codex/render-setup`; origin/main and the running Render worker/API are at `b485efb`. The branch is not even pushed, so CI has never run on it. Merge, redeploy and re-verify are the only remaining steps for this gap.
- Even after that, the status would be `human_needed` (items 1 to 4 above), not `passed`, because those human-only checks remain.

Known, deliberately deferred, not new gaps: WR-01..WR-08, IN-01..IN-04, NEB 0001. WINDOWS.md entry 10 (the 30 s gap) still reads `open` and should be closed now that the override is recorded; entry 11 (NEB 0001) stays open. REQUIREMENTS.md REQ-OPS-01 and REQ-SYNC-01 are still unticked and should stay so until the merge and deploy are verified.

---

_Verified: 2026-09-30T21:10:00Z_
_Verifier: Claude (gsd-verifier)_
