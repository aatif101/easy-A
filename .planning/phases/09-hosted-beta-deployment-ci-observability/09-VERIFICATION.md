---
phase: 09-hosted-beta-deployment-ci-observability
verified: 2026-09-30T23:30:00Z
status: human_needed
score: 9/9 must-haves verified
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
  previous_score: 8/9
  gaps_closed:
    - "ROADMAP criterion 3 on the hosted system: the CR-01 fix and the corrected runbook are now on origin/main (merge 046aa5d, CI green) and both Render services run 046aa5d"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification:
  - test: "1. Hosted student UI"
    expected: "Open https://easy-a-web.onrender.com and pick Spring 2027. 'Updated N min ago' appears above the course index (N small, under about 70 min, since sweeps run hourly); no stale warning; search returns results (for example 'RUS 4241'); removed CRNs 10525, 10832 and 11141 are not listed."
    why_human: "The operator said 'approved' without itemized results and no executor or verifier has driven the browser UI. The API behind it is verified live (sync-status fresh, the three CRNs absent from search and marked removed in the DB)."
  - test: "2. Render failure-email notifications (D-09)"
    expected: "Render Workspace Settings, Notifications: failed-deploy and service-failure emails are enabled and cover all three services (easy-a-api, easy-a-web, easy-a-worker)."
    why_human: "Dashboard-only setting; not readable through the Render CLI or API."
  - test: "3. Render Metrics worker memory"
    expected: "easy-a-worker peak memory under 350 MB over the soak and no OOM events (plan limit 512 MB)."
    why_human: "Only self-reported peak_rss_mb (193.6 and 223.4) is independently evidenced. The operator stated 'under 350 MB' from Render Metrics with no number, and Metrics is not readable by tooling."
  - test: "4. Instructor names against the USF schedule page, by hand"
    expected: "A few sections (for example CRN 10841 RUS 4241 and CRN 11043 ACG 2071) show the same instructor on the official USF schedule search as in the hosted app."
    why_human: "Automation compared the API to the database only; a USF request from tooling would exceed the D-22 request budget."
  - test: "5. Optional gate-recovery rehearsal on the deployed image"
    expected: "On the deployed image (Render shell or a workstation with DATABASE_URL), `--dry-run --max-missing-fraction X` prints the new help text and exits 0 with empty gate_reasons on a normal response. Optionally also confirm that the first sweep after the redeploy (due about 2026-09-30T23:58:46Z) is recorded as succeeded, which would be the first sweep on the 046aa5d image."
    why_human: "Needs a Render shell or DATABASE_URL and a real USF request (D-22). No failed sweep has ever occurred on the hosted system, so the recovery has never been exercised end to end. Optional; not a blocker for the goal."
---

# Phase 9: Hosted Beta, Deployment, CI, Observability: Verification Report (final re-verification)

**Phase Goal:** The corrected application runs as a hosted beta with enough automation and measurement to keep it running.
**Verified:** 2026-09-30T23:30:00Z
**Status:** human_needed
**Re-verification:** Yes, after the CR-01 fix was merged (PR #35, `046aa5d`) and deployed

I started from the hypothesis that the goal was missed and re-checked each item from git, the Render CLI, the hosted API, a READ ONLY database transaction (`transaction_read_only = on`) and the real code. Nothing on Render was changed, no sweep was triggered, nothing was pushed or written, nothing was committed.

## What closed the only gap: criterion 3 on the hosted system

| Check | Evidence | Result |
|---|---|---|
| Fix is on origin/main | `git merge-base --is-ancestor` true for `9496118`, `db60379` and `e36de54` against `origin/main`; `git diff origin/main -- src` is empty (the working branch differs from main only in `.planning/WINDOWS.md` and `09-ROLLOUT-EVIDENCE.md`). `gate_thresholds` is defined in `gate.py:56` and called in `sweep.py:261`. | PASS |
| CI green on main | `gh run list`: `ci` on `Merge pull request #35`, branch main, push, success, 2026-09-30T23:22:53Z (1m19s). PR-branch CI (23:19:50Z, 23:19:52Z) also success. | PASS |
| Worker live on the fix | `render deploys list srv-daul6tnpn0mc7384h5jg`: `dep-daupk7g473hc739ujv9g` `live`, commit `046aa5d2d7c3...`, finished 23:24:37Z; previous `b485efb` deploy `deactivated`. Worker log: `worker_started` 23:24:38Z with `last_sweep_started_at` 22:54:23Z, `sleeping` until `next_start_at` 23:58:46Z, old instance `worker_stopped` 23:25:37Z. | PASS |
| API live on the fix | `srv-daul6tfpn0mc7384h4fg`: `dep-daupk7g473hc739ujv6g` `live`, commit `046aa5d2d7c3...`, finished 23:24:45Z; `b485efb` deploy `deactivated`. | PASS |
| Hosted endpoints | 23:26Z: `GET /health` `{"status":"ok"}`; web `/` HTTP 200; `GET /api/v1/metadata/sync-status?term=202701`: `last_status` succeeded, `last_success_at` 22:54:44Z, `failures_last_24h` 0, `is_stale` false. | PASS |
| CR-01 reproduction, real code | `evaluate_gate(GateInput(500,1000,500,1000,S,S))` with defaults (no override): `passed=False`, reasons `missing_fraction 0.500 above 0.100 ...` and `row_floor 500 below 90% of 1000` (fails closed). Same input with `gate_thresholds(0.9)` (`GateThresholds(0.9, 0.1, 0.9, 2)`): `passed=True, reasons=()`. | PASS |
| Tests | `pytest tests/sync/test_gate.py tests/sync/test_cli.py`: 49 passed. (The previous verification also ran `tests/sync`, CI, deploy and sync-status tests: 235 passed, 1 skipped, and confirmed the new CLI tests fail against the old source.) | PASS |
| Runbook matches the deployed code | The gate-recovery playbook and the per-rule override table were checked against `cli.py`, `sweep.py` and the tests in the previous report (flags, exit codes 0/1/3, dry-run semantics). The deployed image now equals that code. | PASS |

**No sweep has run since the redeploy.** The last recorded sweep is IngestRun 117 (started 22:54:23Z, before the 23:24Z deploy, so on the old `b485efb` image). The first sweep on `046aa5d` is due about 23:58:46Z. This does not block criterion 3: the worker loop passes no override (`cli.py:438`), the default thresholds equal the old literals (`gate_thresholds(None) == GateThresholds(0.10, 0.90, 0.02, 2)`, pinned by tests), and `evaluate_gate`'s body is unchanged. It is listed as an optional confirmation under human item 5.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP 1: hosted beta reachable, serves real data | VERIFIED | 23:26Z: `/health` ok, web 200, search for `RUS 4241` returns real section data with fresh seat observations (`observed_at` 22:54:43Z). DB active (not removed) sections: 3,703. |
| 2 | ROADMAP 2: CI runs Python and frontend checks on push | VERIFIED | `.github/workflows/ci.yml` (python, web, docker jobs). Green on main at `046aa5d` and on the PR branch head. |
| 3 | ROADMAP 3: an operator can follow the runbook to refresh data and recover from a failed refresh, on the hosted system | VERIFIED | See the table above: fix on main, CI green on main, worker and API live on `046aa5d`, CR-01 reproduction passes from the real code, 49 targeted tests pass, runbook matches deployed behaviour. Residual (not a gap): the recovery has not been rehearsed on the deployed image (human item 5, optional). |
| 4a | ROADMAP 4: seats, instructors and existence within one cadence interval of USF | VERIFIED | Five hosted sweeps, all `succeeded`: 113 (18:23:25Z), 114 (19:32:01Z), 115 (20:38:57Z), 116 (21:44:20Z), 117 (22:54:23Z). Gaps between starts 68.6, 66.9, 65.4 and 70.1 min against a 60 min cadence (D-01 jitter; `stale_after_seconds` 7200). `is_stale` false at 23:26Z, `failures_last_24h` 0. |
| 4b | ROADMAP 4: an unchanged sweep writes no instructor or seat rows | VERIFIED | Sweeps 115, 116, 117 report 0 inserted and 10, 32 and 0 updated. Sweep 117 updated 0 rows. Update counts track real changes, not sections touched. Backed by the passing `tests/sync` run. |
| 4c | ROADMAP 4: removed sections leave search | VERIFIED | CRNs 10525, 10832 and 11141 have `removed_at` set in `sections` (READ ONLY), and a search for each returns no match on the hosted API. 3,703 sections remain active. (WR-07: the invariant relies on cache-row deletion, not a route guard; known and deferred.) |
| 4d | ROADMAP 4: UI shows when data was last verified | VERIFIED in code; human check open | `SyncStatus` is rendered in `web/src/App.tsx`, fed by live `/metadata/sync-status`. Browser-level itemized check is human item 1. |
| 5 | 09-15: hosted search p95 below 1,500 ms, single-client | VERIFIED (recorded evidence) | 212.56 ms over 50 calls per `09-ROLLOUT-EVIDENCE.md`; not re-run. |
| 6 | 09-15: worker under the 512 MB plan with no OOM, and each sweep under 30 s | PASSED (override) for duration; memory clause VERIFIED on self-report | Duration clause: operator override (2026-09-30T20:27:43Z) in frontmatter, scoped to duration only. Extra data, not needed for the override: sweeps 115, 116, 117 took 27.209, 28.093 and 20.921 s (READ ONLY `ingest_runs`); the first two hosted sweeps took 50.69 and 37.17 s. Memory: self-reported `peak_rss_mb` 193.6 and 223.4. The Render Metrics figure is human item 3. |
| 7 | 09-15: restart logs `worker_stopped` and the new instance does not sweep at once | VERIFIED | Earlier restart: sweep 115 began exactly at the persisted `next_start_at`, none between 114 and 115. The post-deploy restart repeats it: `worker_started` 23:24:38Z, then `sleeping` until 23:58:46Z (after the 22:54:23Z last start plus 60 min), old instance `worker_stopped` 23:25:37Z, no IngestRun after 117. |
| 8 | 09-15: first sweep succeeded; catch-up recorded; removed absent; auto-added courses never show course history (D-20) | VERIFIED | IngestRun 113 `succeeded` (3,702 seen, 24 inserted, 560 updated); 115, 116 and 117 `succeeded` (3,704 seen each). |
| 9 | 09-15: STATE.md records the new live facts; 08-D21-EXCEPTIONS.md untouched | Accepted | Not goal-critical. |

**Score:** 9/9 truths verified (truth 6 counted as PASSED (override) for its duration clause). 0 present-but-behavior-unverified.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/easy_a/sync/gate.py` | `gate_thresholds`, `GateThresholds`, `DEFAULT_*` | VERIFIED | On origin/main; substantive, wired (sweep imports and calls it). |
| `src/easy_a/sync/sweep.py` | `run_sweep(max_missing_fraction: float | None)` using `gate_thresholds` | VERIFIED | All four thresholds passed to `evaluate_gate` (`sweep.py:261-275`). |
| `src/easy_a/sync/cli.py` | flag passed as None or X; worker loop has no override | VERIFIED | As in the previous report; on main. |
| `tests/sync/test_gate.py`, `tests/sync/test_cli.py` | override table, reviewer case, CR-01 reproduction | VERIFIED | 49 passed here. |
| `docs/runbooks/hosted-beta-operations.md` | corrected section 4 and gate recovery playbook | VERIFIED | On main and matching the deployed code. |
| `.github/workflows/ci.yml`, `render.yaml`, `SyncStatus.tsx`, migration `0004_sync_removed_at` | as before | VERIFIED | Unchanged. |
| `09-ROLLOUT-EVIDENCE.md` | dated evidence | VERIFIED | Now records sweep 3 and the post-merge deploy. It does not mention sweeps 116 and 117, which are visible in the database (see note below). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli._run_single_sweep` | `sweep.run_sweep` | `max_missing_fraction=args.max_missing_fraction` | WIRED | None when the flag is absent |
| worker loop | `run_sweep` | no override argument | WIRED, no override path | `cli.py:438` |
| `sweep._sweep_in_transaction` | `gate.evaluate_gate` | `gate_thresholds(...)`, four keywords | WIRED | `sweep.py:261-275` |
| override sweep's succeeded IngestRun | next sweep's `row_floor` baseline | `load_db_state.last_success_records_seen` | WIRED | tested |
| fix | hosted worker and API | merge to main and Render redeploy | WIRED | Both deploys `live` on `046aa5d` |
| sweep to cache to SyncStatus | | | WIRED | IngestRun 117 to `last_success_at` 22:54:44Z in the API |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| SyncStatus | `last_success_at`, `is_stale` | IngestRun 117 via `/metadata/sync-status` (live 23:26:11Z) | Yes | FLOWING |
| Search results | instructor, seats | worker-written rows; seat `observed_at` 22:54:43Z | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gate and CLI tests | `pytest tests/sync/test_gate.py tests/sync/test_cli.py -q` | 49 passed | PASS |
| CR-01 case, no override | `evaluate_gate(GateInput(500,1000,500,1000,S,S))` | refused: `missing_fraction` and `row_floor` | PASS (fails closed) |
| CR-01 case, `gate_thresholds(0.9)` | same input | `passed=True` | PASS |
| Fix on main | `git diff origin/main -- src` | empty | PASS |
| Deploys live on the fix | `render deploys list` (worker, API) | `046aa5d` `live` on both | PASS |
| Hosted health and freshness | GET `/health`, `/metadata/sync-status` | ok; not stale; failures_last_24h 0 | PASS |
| Removed CRNs out of search | hosted search for 10525, 10832, 11141 | 0 matches each | PASS |
| Sweep durations | READ ONLY `ingest_runs` | 115: 27.209 s, 116: 28.093 s, 117: 20.921 s | PASS (extra data) |
| Sweep since the redeploy | `ingest_runs` | none (latest is 117, pre-deploy) | NOT YET OBSERVABLE (next due about 23:58:46Z) |

The full workspace suite was not re-run here (the executor reported 706 passed, 4 skipped); targeted suites pass.

### Probe Execution

No phase-declared `probe-*.sh` scripts; step skipped.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| REQ-OPS-01 | 09-01, 06, 10, 11, 13, 14, 15, 16 | SATISFIED for everything tooling can verify; two dashboard-only facts remain human (items 2 and 3) | Deploy, CI on main, request logging, sync-status, p95, and runbook recovery (now deployed) are verified. Failure-email notifications and the Render Metrics memory figure rest on operator statements. |
| REQ-SYNC-01 | 09-02 to 09-08, 11, 12, 14, 15, 16 | SATISFIED | Five hosted sweeps, change-only writes, removals out of search, UI freshness wired, fail-closed default gate. The 30 s clause is an accepted override. The student-visible UI is human item 1. |

No orphaned Phase 9 requirement IDs. Plans 01 to 16 all have SUMMARYs. REQUIREMENTS.md `[ ]` boxes for these two IDs can be ticked once the human items are confirmed (orchestrator decision).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| TBD/FIXME/XXX in files modified by 09-16 | | none found (previous report) | None | |
| `cli.py`, `schedule/client.py`, sync runner | | WR-01..WR-08, IN-01..IN-04 (deliberately deferred, `open` in 09-REVIEW-DISPOSITION.md) | Warning (known) | None breaks a must-have. |
| hosted worker | | NEB 0001 fails every sweep (`records_failed` 1 in sweeps 115 to 117; WINDOWS entry 11) | Warning (known) | Students cannot find its sections; not a must-have. |

### Bookkeeping checks

- `.planning/WINDOWS.md` entry 10 (the 30 s gap) now reads `waived`, with the operator-acceptance rationale and a `2026-09-30T23:25:37Z` close time. Entry 11 (NEB 0001) stays `open`. Confirmed in the file.
- `09-ROLLOUT-EVIDENCE.md` was updated on this branch with sweep 3 and the post-merge deploy. Minor, non-blocking: it says sweep 3 "succeeded in 27.209 s" and does not mention sweeps 116 (28.093 s) and 117 (20.921 s), which occurred before the redeploy.

### Human Verification Required

Five items, detailed in the frontmatter `human_verification` block: (1) hosted UI "Updated N min ago", no stale warning, search works, CRNs 10525, 10832, 11141 absent; (2) Render failure-email notifications for all three services (D-09); (3) Render Metrics worker memory under 350 MB and no OOM; (4) a few instructor names checked by hand against the USF schedule page (for example CRN 10841 RUS 4241, CRN 11043 ACG 2071); (5) optional gate-recovery rehearsal on the deployed image, plus optionally confirming the first post-redeploy sweep (due about 23:58:46Z) succeeded.

### Gaps Summary

No gaps. The single remaining gap from the previous report (criterion 3 on the hosted system) is closed by independent evidence: the fix is on origin/main, CI is green on that commit, both Render services are live on it, the CR-01 reproduction passes from the real code, and the runbook matches the deployed behaviour. The phase goal is achieved as far as tooling can verify. The status is `human_needed`, not `passed`, only because the five human-only items above are unconfirmed.

Known, deliberately deferred, not gaps: WR-01..WR-08, IN-01..IN-04, NEB 0001 (WINDOWS entry 11). WINDOWS entry 10 is `waived`.

---

_Verified: 2026-09-30T23:30:00Z_
_Verifier: Claude (gsd-verifier)_
