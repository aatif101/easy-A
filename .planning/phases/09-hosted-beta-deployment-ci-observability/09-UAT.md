---
status: testing
phase: 09-hosted-beta-deployment-ci-observability
source: [09-VERIFICATION.md]
started: 2026-09-30T23:28:12Z
updated: 2026-09-30T23:28:12Z
---

## Current Test

number: 1
name: Hosted UI freshness line and search
expected: |
  On https://easy-a-web.onrender.com the course index shows "Updated N min ago" (N small; sweeps are hourly)
  with no "Seat data may be out of date" warning; search returns results; CRNs 10525, 10832 and 11141
  (removed from USF) are not listed.
awaiting: user response

## Tests

### 1. Hosted UI freshness line and search
expected: "Updated N min ago" above the course index, no stale warning, search works, CRNs 10525, 10832, 11141 not listed.
result: [pending]

### 2. Render failure-email notifications (D-09)
expected: Workspace Settings -> Notifications: failed-deploy and service-failure emails cover easy-a-api, easy-a-web and easy-a-worker. Dashboard-only; the CLI cannot read it.
result: [pending]

### 3. Render Metrics worker memory
expected: easy-a-worker peak memory under 350 MB with no OOM events (only self-reported 194-223 MB is independently evidenced).
result: [pending]

### 4. Instructor names against the USF schedule page, by hand
expected: e.g. CRN 10841 (RUS 4241) and CRN 11043 (ACG 2071) show on the hosted site the same instructor as the USF schedule page.
result: [pending]

### 5. Optional: gate-recovery rehearsal and first post-redeploy sweep
expected: On the deployed image, `--dry-run --max-missing-fraction X` exits 0 with empty gate_reasons and shows the new help text (mind the cadence floor and one USF request per dry run); the first sweep on 046aa5d (due about 23:58:46Z 2026-09-30) succeeds.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
