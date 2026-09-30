---
phase: 09-hosted-beta-deployment-ci-observability
verified: 2026-09-30T20:30:00Z
status: gaps_found
score: 7/9 must-haves verified
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
  - docs/runbooks/hosted-beta-operations.md
  - render.yaml
  - src/easy_a/sync/gate.py
  - src/easy_a/sync/sweep.py
covered_digest: "v2:sha256:702a389049b08bc14fcce69c4373d84294b70b44e72b7d5e756715958692950f"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "each sweep takes under 30 s end to end"
    scope: "duration clause only; the memory clause of the same must-have is unaffected"
    reason: "Operator accepted the gap (2026-09-30) rather than investigate. Basis recorded: hosted sweeps of 37.166-50.69 s fit inside a 300-3600 s cadence and no roadmap criterion depends on 30 s; the cause of the slower hosted time was not established."
    accepted_by: "aatif101"
    accepted_at: "2026-09-30T20:27:43Z"
gaps:
  - truth: "09-15 must-have: each sweep takes under 30 s end to end (RESEARCH Pitfall 2; live-sync plan soak criteria)"
    status: overridden
    reason: "ACCEPTED BY OPERATOR (see overrides). Hosted sweeps took 50.69 s (IngestRun 113) and 37.166 s (IngestRun 114), re-derived from ingest_runs started_at/finished_at in a READ ONLY query. The threshold is a PLAN must-have (09-15-PLAN.md line 39), not a ROADMAP success criterion or REQUIREMENTS acceptance line. The operator has not decided whether to accept it. Cause not established (no per-phase timing in the log line)."
    artifacts:
      - path: ".planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md"
        issue: "Records the gap honestly; WINDOWS.md entry 10 is open"
    missing:
      - "Operator decision: accept the 30 s bar as an engineering target that hosted 0.5 CPU cannot meet (add an override), or investigate and reduce sweep time (add per-phase timing, fetch vs parse vs DB)"
      - "Optional: sweep 3 (due about 20:38:57Z) as a third data point"
  - truth: "ROADMAP criterion 3: an operator can follow the runbook to recover from a failed refresh (runbook section 4, kind 'gate')"
    status: partial
    reason: "CR-01 is real. The runbook tells the operator to run --once --max-missing-fraction X for a legitimate mass removal. run_sweep forwards only max_missing_fraction to evaluate_gate, so row_floor (90% of last succeeded IngestRun.records_seen) and subjects_absent keep their defaults. Reproduced in this verification: evaluate_gate(GateInput(500, 1000, 500, 1000, S, S), max_missing_fraction=0.9) returns passed=False, reasons=('row_floor 500 below 90% of 1000',). Hosted IngestRuns 113 and 114 succeeded, so last_success_records_seen is set in production and the path is live. A failed sweep never advances it, so the gate stays blocked for every later sweep until a code change or a hand-inserted IngestRun. The other eight failure kinds have workable playbooks."
    artifacts:
      - path: "src/easy_a/sync/sweep.py"
        issue: "evaluate_gate called with max_missing_fraction only (lines ~257-267)"
      - path: "src/easy_a/sync/gate.py"
        issue: "row_floor and subjects_absent not overridable"
      - path: "docs/runbooks/hosted-beta-operations.md"
        issue: "Section 4 'gate' row relies on an override that cannot clear row_floor or subjects_absent"
    missing:
      - "Make the override cover row_floor (and relax subjects_absent), seed a succeeded IngestRun in the override test (tests/sync/test_cli.py ~538)"
      - "Or amend the runbook to state that row_floor and subjects_absent have no override and give the real recovery steps"
---

# Phase 9: Hosted Beta, Deployment, CI, Observability: Verification Report

**Phase Goal:** The corrected application runs as a hosted beta with enough automation and measurement to keep it running.
**Verified:** 2026-09-30T20:30:00Z
**Status:** gaps_found
**Re-verification:** No, initial verification

I started from the assumption that the goal was missed and checked SUMMARY.md claims against the repo, the hosted API, the hosted database (READ ONLY transactions, `transaction_read_only = on`) and GitHub Actions. No Render service was changed, no sweep was triggered, no write was made.

## Goal Achievement

### Observable Truths

ROADMAP success criteria come first (non-negotiable), then plan-level must-haves that add detail.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ROADMAP 1: hosted beta is reachable and serves real data | VERIFIED | Live at 20:21Z: `GET /health` `{"status":"ok"}`; web 200; `GET /api/v1/rankings/search?term=202701` total 3,703 (equals DB active count 3,703), real instructor, seats, grade-derived easiness (`score_source: course`, `effective_n 11`). `alembic_version` is `0004_sync_removed_at`. |
| 2 | ROADMAP 2: CI runs Python and frontend checks on push | VERIFIED | `.github/workflows/ci.yml` has python (ruff hard gate, alembic round-trip, pytest on postgres:16 with a no-skip guard, mypy report-only), web (lint, typecheck, test, build) and docker jobs, triggered on `push: "**"` and `pull_request`. `gh run list`: latest runs on main and PR branches all `success` (e.g. 36675480644, 36674223585). The first run did fail (2 test bugs) and was honestly fixed. |
| 3 | ROADMAP 3: an operator can follow the runbook to refresh data and recover from a failed refresh | PARTIAL (FAILED for the `gate` path) | Runbook has health check, refresh, dry run, nine failure kinds, pause/resume, un-mark, p95, alerts. Refresh (`--once`, exit codes) and restore are exercised in tests. But CR-01 makes the documented gate recovery non-functional (see Gaps). Not exercised on the hosted system: no failed sweep has occurred, so no recovery has been rehearsed. |
| 4a | ROADMAP 4: seats, instructors and section existence stay within one cadence interval of USF | VERIFIED (with note) | Hosted sweeps at 18:23:25Z and 19:32:01Z (IngestRuns 113, 114, both `succeeded`). Actual gap 68.6 min against a nominal 60 min cadence: the `sleeping` target carries D-01 jitter (+8.6 min, inside the +/-20% design). `is_stale` false, `stale_after_seconds` 7200. Sweep 3 had not run at 20:21Z (not yet due). Only two sweeps observed. |
| 4b | ROADMAP 4: an unchanged sweep writes no instructor or seat rows | VERIFIED | Snapshot-to-snapshot growth reconciles exactly to the logged changes (instructors +11 = 6 changes + 5 inserts; seats +6 = 1 + 5) while 49 sections were "updated". Backed by passing `tests/sync` (run here). No sweep with zero changes has occurred on the hosted system; this is inferred from sweep 2 (49 updated sections wrote no rows). |
| 4c | ROADMAP 4: removed sections leave search | VERIFIED | DB: 109 sections with `removed_at` set, 0 `section_rankings` rows belong to them; API `total` 3,703 equals the active count. (WR-07: the search route has no `removed_at` guard and depends on cache-row deletion; holds today, unenforced.) |
| 4d | ROADMAP 4: the UI shows when data was last verified | VERIFIED in code; UNVERIFIED by a human | `SyncStatus` component is imported and rendered in `web/src/App.tsx:204`, fed by `fetchSyncStatus`; 7 vitest tests pass here; the API it reads returns real `last_success_at`. The hosted UI was never itemized by the operator ("approved"), and the executor did not open it. See Human Verification. |
| 5 | 09-15: hosted search p95 below 1,500 ms from the benchmark over 50 calls, labeled single-client | VERIFIED | Evidence: 212.56 ms (p50 131.53, max 371.92), 50 calls after 5 warmups, explicitly labeled single-client; browser and concurrent latency recorded as NOT MEASURED. I did not rerun it (recorded evidence only, plausible against the observed API latency). |
| 6 | 09-15: worker under the 512 MB plan with no OOM restarts AND each sweep takes under 30 s | FAILED (duration half) | Memory half: self-reported `peak_rss_mb` 193.6 and 223.4; Render Metrics and OOM list not independently read. Duration half: 50.69 s and 37.166 s, re-derived from `ingest_runs` (see Gaps). One truth, so the truth is failed as written. |
| 7 | 09-15: worker restart logs `worker_stopped` and new instance does not sweep immediately | VERIFIED (evidence only) | Log evidence in 09-ROLLOUT-EVIDENCE.md (old instance `worker_stopped` 20:01:57Z; new `next_start_at` 20:38:57Z). DB confirms no IngestRun between 114 (19:32) and now. I did not see the logs directly. |
| 8 | 09-15: first sweep succeeded; catch-up recorded; removed absent; auto-added courses never show course history (D-20) | VERIFIED | IngestRun 113 `succeeded` 3,702 seen / 24 inserted / 560 updated / 4 failed; 109 removed reconciles. Evidence records `score_source` `subject` for every auto-added course. |
| 9 | 09-15: STATE.md records the new live facts; 08-D21-EXCEPTIONS.md left untouched | NOT RE-CHECKED in depth | Plan summary lists the STATE.md update; not a goal-critical truth. Accepted on the commit log without a line-by-line diff. |

**Score:** 7/9 truths verified (truths 3 and 6 fail or are partial); 0 present-but-behavior-unverified.

### The 30 s gap: is it required?

Yes, by a must-have, though not by the goal. The 30 s bar is in `09-15-PLAN.md` must_haves truth 6, sourced from RESEARCH Pitfall 2 and the live-sync plan soak criteria. It is not in ROADMAP Phase 9's four success criteria and not in the REQ-OPS-01 or REQ-SYNC-01 acceptance text. The verifier contract says PLAN must-haves cannot be dropped, so I treat it as failed. Since it is an engineering threshold, a reasonable operator can accept it with a recorded override. The gap does not threaten any roadmap criterion: sweeps of 37 to 51 s fit comfortably inside a 3,600 s or even a 300 s cadence. I did not decide this for the operator.

This suggested override looks intentional and defensible. To accept the deviation, add to this file's frontmatter:

```yaml
overrides:
  - must_have: "each sweep takes under 30 s end to end"
    reason: "<operator to state: e.g. bar was a workstation-derived engineering target; hosted 0.5 CPU sweeps of 37-51 s are harmless against a 300-3600 s cadence>"
    accepted_by: "<operator>"
    accepted_at: "<ISO timestamp>"
```

Because truth 6 also carries the memory half, an override should be scoped to the duration clause. If the operator accepts it and also fixes CR-01, status would move to human_needed (items below), not passed.

### CR-01 analysis (does it break a must-have?)

Yes, for ROADMAP criterion 3. Everything else the runbook covers works, but the single recovery step for a gate refusal caused by a legitimate mass removal is broken, and the code path is live on the hosted worker. Effect in practice: a sweep that drops more than 10% of active sections trips `missing_fraction`; the operator raises `--max-missing-fraction`, but `row_floor` still refuses, because the drop also takes `in_scope_rows` under 90% of the last succeeded run. The error is misleading (the operator did everything the runbook says). The likelihood before Spring 2027 is low, but the criterion is about recoverability. It is not a correctness or data-corruption issue, and the gate failing closed is safe. Severity: BLOCKER for criterion 3 as stated; one fix is small (derive `min_row_ratio` from the override and add a test with a prior succeeded IngestRun).

The other eight review warnings were not individually re-verified. By their own analysis none breaks a roadmap criterion. WR-03 and WR-04 weaken the documented D-22 floor guarantees (overlapping workers on deploy, repeated `--dry-run`) without any observed breach; the runbook section 3 already states dry runs are not rate limited, which contradicts the "No flag bypasses the floor" line in Standing rules and should be reconciled. WR-07 is an unenforced invariant that holds today (verified above). All are `open` in 09-REVIEW-DISPOSITION.md.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/ci.yml` | Python and web CI | VERIFIED | Substantive; runs green on main and PRs |
| `render.yaml` | Blueprint, 3 services, region ohio, checksPass | VERIFIED | Matches evidence (3 services live) |
| `docs/runbooks/hosted-beta-operations.md` | Operator runbook | PARTIAL | Complete, but gate playbook depends on CR-01 |
| `src/easy_a/sync/{gate,sweep,...}.py` | Whole-term sweep | VERIFIED (wired) | `evaluate_gate` called in `_sweep_in_transaction`; 100+ sync tests pass here |
| `web/src/components/SyncStatus.tsx` | Freshness line | VERIFIED (wired) | Rendered in `App.tsx`; 7 tests pass |
| `migrations/versions/0004_sync_removed_at.py` | `removed_at` column | VERIFIED | Hosted head is `0004_sync_removed_at` |
| `09-ROLLOUT-EVIDENCE.md` | Dated evidence | VERIFIED | Consistent with my independent DB and API probes (ingest run ids, counts, durations) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| easy-a-web | easy-a-api | `VITE_API_BASE_URL` baked at build; CORS exact origin | WIRED (evidence) | Bundle contains the API origin per evidence; CORS header exact per evidence; I did not re-request CORS. Web returns 200. |
| easy-a-worker | Supabase | `DATABASE_URL`, `pg_try_advisory_xact_lock`, source `usf_schedule_sync:202701` | WIRED | IngestRuns 113 and 114 exist under that source. |
| sweep | search/rankings cache | cache rebuild on change; removed rows deleted | WIRED | 0 cache rows for removed sections; API total equals active. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Search results | `items[*].instructor`, `seats` | `section_instructors`, `seat_snapshots` written by the worker | Yes (observed 2026-09-30T19:32:22Z rows served) | FLOWING |
| SyncStatus | `last_success_at`, `is_stale` | `IngestRun` via `/metadata/sync-status` | Yes (live response at 20:21:35Z) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Sync, status, freshness, CI and deploy-config tests | `pytest tests/sync tests/api/test_sync_status.py tests/rankings/test_verified_freshness.py tests/test_ci_workflow.py tests/test_deploy_config.py` | all passed | PASS |
| SyncStatus UI tests | `vitest run src/components/SyncStatus.test.tsx` | 7 passed | PASS |
| Gate override (CR-01) | `evaluate_gate(GateInput(500,1000,500,1000,S,S), max_missing_fraction=0.9)` | `passed=False, row_floor 500 below 90% of 1000` | FAIL (confirms CR-01) |
| Sweep durations | READ ONLY query on `ingest_runs` | 113: 50.69 s; 114: 37.166 s | FAIL vs 30 s (confirms gap) |
| Hosted search equals DB | GET search `total` vs READ ONLY count | 3,703 vs 3,703 (109 removed) | PASS |

The full workspace suite was not rerun; CI recorded 693 passed on head 79f9efd.

### Probe Execution

No phase-declared `probe-*.sh` scripts; step skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| REQ-OPS-01 | 09-01, 06, 10, 11, 13, 14, 15 | Deployable, observable, reproducible hosted beta; CI; runbook | PARTIALLY SATISFIED | Deploy, CI, request logging (`duration_ms`), sync-status and p95 verified. Runbook recovery broken for `gate` (CR-01). Failure-email notifications rest on operator confirmation. |
| REQ-SYNC-01 | 09-02 to 09-08, 11, 12, 14, 15 | Near-live seats, instructors, existence; change-only; removals leave search; IngestRun; UI freshness | SATISFIED (functionally) | Verified above. Acceptance text contains no 30 s clause. Note REQUIREMENTS.md already ticks both boxes `[x]` while the 30 s gap and CR-01 are open. |

All 15 plans declare requirements; every ID maps to one of these two. No orphaned Phase 9 requirement IDs in REQUIREMENTS.md. All plans 01 to 15 are present with SUMMARYs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/easy_a/sync/sweep.py` / `gate.py` | ~257 / 60 | Override covers one of three gate rules (CR-01) | Blocker | Documented recovery non-functional |
| `src/easy_a/sync/cli.py` | 64, 91 | URL scrub corrupts failed-sweep JSON (WR-01) | Warning | Observability contract broken on the likeliest failure |
| `src/easy_a/schedule/client.py` | 88-111 | No total fetch deadline under advisory lock (WR-02) | Warning | One slow response can stall sync |
| sync CLI/runner | | Floor checked outside the lock; dry run unrecorded (WR-03, WR-04) | Warning | D-22 floor weaker than documented |
| TBD/FIXME/XXX in phase files | | none found | None | |

`.planning/WINDOWS.md` has two open Phase 9 entries: 10 (unmet-truth, the 30 s gap) and 11 (NEB 0001 fails every sweep, `records_failed` stays 1, students cannot find its sections). With `workflow.windows_enforce`, `/gsd-ship` would block while `open_count > 0` (it is 10 now, including older entries from phases 03.5 and 08).

### Human Verification Required

1. **Student-facing freshness line on the hosted site.** Test: open https://easy-a-web.onrender.com, pick Spring 2027. Expected: "Updated N min ago" under the current tier, no stale warning, search works, a removed CRN (e.g. 10525) not listed. Why human: the operator said "approved" without itemized results and the executor never opened the UI.
2. **Render failure-email notifications (D-09).** Test: Workspace Settings, Notifications, confirm failed-deploy and service-failure emails cover all three services. Why human: dashboard-only, not readable by CLI; currently resting on operator word.
3. **Worker memory in Render Metrics.** Test: read the worker's peak memory and OOM events. Expected: under 350 MB target, no OOM. Why human: only self-reported `peak_rss_mb` (194 to 223 MB) is independently evidenced; Metrics figure was stated as "under 350 MB" with no number.
4. **Instructor change vs the USF page.** Test: compare two or three Staff-to-named sections with the USF schedule page by hand. Why human: automation only compared the API to the database, and a USF request from tooling would exceed D-22.
5. **Soak sweep 3 (optional).** Sweep 3 was due about 20:38:57Z and had not run at 20:21Z. A third sweep would add a duration data point and a second check that steady-state sweeps leave no extra rows. Not required by the roadmap.

### Gaps Summary

The hosted beta is real: reachable, serving synced data that matches the database and USF-derived counts, CI is green on main, change-only writes reconcile to the row, removed sections are out of search and the freshness component is wired to live data. REQ-SYNC-01 is functionally met.

Two gaps keep this from `passed`:

1. **Sweep duration (plan-level must-have, not a roadmap criterion).** 50.69 s and 37.166 s against "under 30 s". The plan must-have is unmet and unresolved; it needs an operator decision (accept via override, or investigate) rather than more engineering by default. It does not undermine any roadmap success criterion.
2. **CR-01 (roadmap criterion 3).** The runbook's `gate` recovery cannot work once a prior successful sweep exists, which is the hosted configuration. Fix the override or correct the runbook.

Beyond those, open items that are not gaps but should not be lost: NEB 0001 fails every sweep and students cannot find it (WINDOWS 11); 8 review warnings are open; the soak covered two sweeps only; UI checks, email notifications and Render memory metrics rest on operator statements. REQUIREMENTS.md already marks both requirements complete, which is ahead of this verification: REQ-OPS-01 is complete only after CR-01 is fixed or the runbook corrected, and REQ-SYNC-01's evidence line correctly carries the 30 s caveat.

---

_Verified: 2026-09-30T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
