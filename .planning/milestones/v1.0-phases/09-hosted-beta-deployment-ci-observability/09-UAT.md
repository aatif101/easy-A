---
status: complete
phase: 09-hosted-beta-deployment-ci-observability
source: [09-VERIFICATION.md]
started: 2026-09-30T23:28:12Z
updated: 2026-09-30T23:42:58Z
---

## Current Test

[testing complete]

## Tests

### 1. Hosted UI freshness line and search
expected: "Updated N min ago" above the course index, no stale warning, search works, CRNs 10525, 10832, 11141 not listed.
result: pass
reported: "Operator verified personally on 2026-09-30; no itemized measurements supplied."

### 2. Render failure-email notifications (D-09)
expected: Workspace Settings -> Notifications: failed-deploy and service-failure emails cover easy-a-api, easy-a-web and easy-a-worker. Dashboard-only; the CLI cannot read it.
result: pass
reported: "Operator verified personally on 2026-09-30; no itemized measurements supplied."

### 3. Render Metrics worker memory
expected: easy-a-worker peak memory under 350 MB with no OOM events (only self-reported 194-223 MB is independently evidenced).
result: pass
reported: "Operator verified personally on 2026-09-30; no itemized measurements supplied."

### 4. Instructor names against the USF schedule page, by hand
expected: e.g. CRN 10841 (RUS 4241) and CRN 11043 (ACG 2071) show on the hosted site the same instructor as the USF schedule page.
result: pass
reported: "Operator verified personally on 2026-09-30; no itemized measurements supplied."

### 5. Optional: gate-recovery rehearsal and first post-redeploy sweep
expected: On the deployed image, `--dry-run --max-missing-fraction X` exits 0 with empty gate_reasons and shows the new help text (mind the cadence floor and one USF request per dry run); the first sweep on 046aa5d (due about 23:58:46Z 2026-09-30) succeeds.
result: skipped
reason: "Deferred follow-up: gate-recovery rehearsal on the deployed image (one USF request; run `--dry-run --max-missing-fraction X` once) and confirmation that the first sweep on 046aa5d (due about 2026-09-30T23:58:46Z) succeeded. Optional; the operator chose not to run it at phase close (2026-09-30). Not verified."

## Summary

total: 5
passed: 4
issues: 0
pending: 0
skipped: 1
blocked: 0

## Deferred Follow-Ups

- Test 5: gate-recovery rehearsal on the deployed image, and confirm the first post-redeploy sweep (046aa5d) succeeded. Not done at phase close; optional.

## Gaps
