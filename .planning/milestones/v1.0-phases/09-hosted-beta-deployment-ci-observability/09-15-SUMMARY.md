---
phase: 09-hosted-beta-deployment-ci-observability
plan: 15
subsystem: infra
tags: [render, go-live, soak, hosted-sweep, change-only-writes, p95, worker-restart]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-14 migration 0004, dry run and merged, green-CI code; 09-11 worker CLI; 09-13 Dockerfile and render.yaml"
provides:
  - "Hosted beta live on Render (api, worker, static web, region ohio for api and worker) serving real synced data"
  - "First and second hosted sweeps recorded; change-only writes reconciled exactly between two READ ONLY snapshots"
  - "Hosted single-client search p95 212.56 ms (bar 1,500 ms)"
  - "SIGTERM handling (A1) and the restart floor confirmed on the hosted worker"
  - "STATE.md live facts: URLs, origin/main, section counts, auto-added courses, D-21 re-baseline, hosted p95"
affects: [phase-9-verification, phase-10]

actuals:
  tokens: 10500
  tasks: 3
  commits: 3
plan_head_before: f2a188770adab5b51341a3a447cd7be4be078825
plan_head_after: cbaf8efc5242eb3554d8615607d85cde0b5a5feb

tech-stack:
  added: []
  patterns:
    - "Two READ ONLY snapshots bracketing a sweep, reconciled against the sweep's own logged counts (rows added = changes + inserts)"
    - "Sweep line next_start_at is the floor; the following sleeping line carries the jitter"

key-files:
  created:
    - .planning/phases/09-hosted-beta-deployment-ci-observability/09-15-SUMMARY.md
  modified:
    - .planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "The 30 s sweep-duration criterion is recorded as a GAP (50.69 s and 37.166 s), not a pass; the threshold was not loosened and the operator has not decided."
  - "Snapshot 2 was taken at 20:05:25Z, before sweep 3 (due 20:38:57Z); it covers sweep 2 only."
  - "Two soak items the operator approved without itemizing (web UI checks, instructor spot check) are recorded as operator-approved with no itemized results; the executor verified the instructor changes at the API and database level only."

requirements-completed: [REQ-OPS-01, REQ-SYNC-01]

duration: about 12 min for the Task 3 close-out (Tasks 1 and 2 ran earlier the same day, 18:27Z to 18:35Z; operator waits excluded)
completed: 2026-09-30
---

# Phase 9 Plan 15: Hosted Go-Live and Soak Summary

**The Render beta is live at easy-a-api.onrender.com and easy-a-web.onrender.com; the worker has completed two hosted sweeps with change-only writes that reconcile exactly to the row, search p95 is 212.56 ms, and the one unmet soak criterion (sweeps under 30 s; measured 50.69 s and 37.166 s) is recorded as an open gap rather than a pass.**

## Performance

- **Duration:** about 12 min for the Task 3 close-out (Tasks 1 and 2 earlier; operator waits excluded)
- **Completed:** 2026-09-30
- **Tasks:** 3 of 3 (Task 1 and the Task 3 observations and restart were operator actions; Task 3 approved by the operator)
- **Commits:** 3 measured from the plan ledger (`f2a1887` to `cbaf8ef`); the final metadata commit that holds this SUMMARY, STATE.md, ROADMAP.md and REQUIREMENTS.md comes after and is not counted

## Accomplishments

- **Go-live (Task 1/2, `12de5db`):** three services on `main`; `/health` returns `{"status":"ok"}`; `GET` with the web origin returns `access-control-allow-origin` exactly equal to it. The API total (3,698 at that time) equals the DB active set with 0 removed CRNs present.
- **First hosted sweep:** status succeeded; 24 inserted, 560 updated, 109 removed, 156 instructor changes, 100 seat changes; 10 courses auto-added (all `subject` fallback, never course history, D-20); 4 deferred by the per-sweep cap.
- **Hosted p95:** 212.56 ms over 50 calls after 5 warmups (p50 131.53, max 371.92); single-client, deployed host, one workstation. Browser and concurrent-user latency NOT MEASURED.
- **Soak (Task 3, `61258b1`, `cbaf8ef`):**
  - Two sweeps (IngestRuns 113 and 114), 68.6 min apart, outside a registration window.
  - Snapshot 2 (20:05:25Z) versus snapshot 1 (18:29:39Z) reconciles exactly to sweep 2: `section_instructors` +11 (6 changes + 5 inserts), `seat_snapshots` +6 (1 + 5), active sections +5, removed unchanged at 109, ingest_runs +1.
  - `failures_last_24h` 0, `is_stale` false (20:05:19Z).
  - The API search set equals the 3,703 active CRNs exactly and contains none of the 109 removed CRNs (20:08:36Z).
  - Six sweep-2 instructor changes (three Staff to named) all appear in the hosted API as the new names.
  - One operator restart: the old instance logged `worker_stopped` (20:01:57Z), proving SIGTERM reached Python (A1 confirmed); the new instance slept until 20:38:57Z (floor 20:32:01Z) and did not sweep immediately.
  - Worker self-reported peak RSS 193.6 and 223.4 MB; operator-reported Render Metrics peak under 350 MB.

## Task Commits

1. **Task 1 (operator):** Blueprint creation, secrets, URLs, notifications, no repo commit
2. **Task 2 (tracer):** `12de5db` docs(09-15): record go-live, first hosted sweep, hosted p95 and D-21 re-baseline
3. **Task 3 (soak):** `61258b1` docs(09-15): record soak across two sweeps, restart check and the 30 s duration gap; `cbaf8ef` docs(09-15): record sweep 1 instructor-change breakdown against the research diff

All commits are local (branch `codex/render-setup`); nothing was pushed.

## Deviations from Plan

### Auto-fixed Issues

None. One correction to a working assumption, not a code deviation: the operator's note that the jitter differed between sweep 1 (+68.6 min) and sweep 2 (exactly +60 min) compared two different log fields. See the jitter item below.

The plan's Task 2 spot-check of removed CRNs via a `q=` parameter was invalid (the endpoint has no free-text parameter); it was replaced by a full API-versus-DB set comparison, recorded in the evidence (this was done in the earlier Task 2 run).

## Auth gates

Render Blueprint creation, secret entry and the worker restart were operator dashboard actions by design (blocking-human gate on Task 1). No authentication failure occurred for the executor.

## Items flagged for user review

1. **UNRESOLVED: the 30 s per-sweep duration criterion is not met.** Sweep 1 took 50.69 s and sweep 2 took 37.166 s against "each sweep under 30 s" (RESEARCH Pitfall 2; live-sync plan soak criteria). Recorded as a GAP. The threshold was not loosened, the cause is not established (no per-phase breakdown in the log line; hypotheses untested: 0.5 CPU worker parse time, fetch time from Render, database round trips over the pooler), and the operator has not decided whether to accept it. Sweep 3 (due about 20:38:57Z) will be a third data point. Note the 30 s figure was an engineering bar, not a requirement text in ROADMAP or REQUIREMENTS.
2. **Jitter interpretation (correction).** The `next_start_at` inside the `sweep_succeeded` line is the floor (start plus exactly 60 min) in both sweeps. The `sleeping` line that follows carries the jitter: +68.59 min after sweep 1, +65.96 min after sweep 2, and +66.94 min after the restart. So jitter occurred on every sleep, and actual gaps between sweeps are 66 to 69 min, slightly over the nominal 60 min cadence (still under the 7,200 s stale threshold). Whether the ROADMAP wording "within one cadence interval" should be read as floor plus jitter is for the operator.
3. **NEB 0001 is a permanent failed record.** It was "deferred: per-sweep cap" in sweep 1 and "no catalog heading" in sweep 2, so every sweep reports `records_failed` 1 while staying `succeeded` (`failures_last_24h` counts 0). Students cannot find NEB 0001 sections. Decide: accept, exclude the course, or fix the lookup.
4. **Instructor-change delta, 150 and 156 versus 89.** Sweep 1's 156 changes split 112 Staff to named, 30 named to other, 14 named to Staff; the research diff a day earlier had 52, 24 and 13. Nearly all the growth is Staff to named (+60). Cause unverified (hypothesis: departments assigning instructors as registration nears, or a definitional difference). The hosted data matches what USF returned; this is an open observation, not a failure.
5. **D-07..D-13, accepted as Claude's lean and now running:** D-07 `/api/v1/metadata/sync-status` (live, read above); D-08 latency via request-duration logs, hosted p95 from the benchmark script only; D-09 Render built-in failure email only (the notification settings are a dashboard view, NOT independently verified, resting on the operator's confirmation); D-10 "Updated N min ago" (operator approved; not itemized); D-11 CI hard gates (ruff, pytest, frontend); D-12 `mypy` report-only as written, with Open Question 5 (promote `mypy src` to a hard gate; it was clean at 0 errors) still pending; D-13 `autoDeployTrigger: checksPass` set in `render.yaml` (the Blueprint-created deploy had trigger `blueprint_sync`; later deploys not exercised here).
6. **Research Open Question 2 (cancelled `U`/`C` sections still shown to students) and status `R` label:** unchanged, still unanswered and out of Phase 9's locked scope.
7. **Open Question 3 (extend the Jan 7 window to Jan 15):** unchanged, D-02 kept as locked; it is a one-line config edit. Not exercised: the first registration window (Nov 2, 2026) has not arrived.
8. **Open Question 8 (per-sweep USF load):** bytes are 7.10 MB and `Content-Encoding` is null (no compression) on all three observed requests (dry run, sweep 1, sweep 2); the roughly 10,080-request volume over the D-02 windows is still awaiting explicit acceptance. Open Question 6: `seat_snapshots` grew +124 (sweep 1 catch-up) and +6 (sweep 2); growth at 5-minute cadence is NOT MEASURED.
9. **Not itemized by the operator:** the web UI checks ("Updated N min ago", no stale warning, search works, removed CRN not listed) and the instructor spot check were approved without results. The executor did not open the web UI; the API, log and database evidence is in the evidence file.
10. **Sweep 3 not observed.** Snapshot 2 predates it (due 20:38:57Z). A later sweep is an additional check on the duration gap, not required by the plan.
11. **Unpushed commits.** This plan's commits and the earlier `09-14` docs commits on `codex/render-setup` are local; nothing was pushed.

## Known Stubs

None. No UI or source files were created or changed in this plan.

## Threat Flags

None. No new network endpoint, auth path or trust-boundary file access was introduced; the plan changed only `.planning/` documents.

## Self-Check: PASSED

- Evidence sections present (`## Go-live`, `## First hosted sweep`, `## Hosted search and p95`, `## D-21 re-baseline after sync`, `## Soak`); negative grep for connection strings and the pooler hostname returns nothing.
- Commits `12de5db`, `61258b1` and `cbaf8ef` exist on `codex/render-setup`.
