---
phase: 09-hosted-beta-deployment-ci-observability
plan: 09
subsystem: ui
tags: [react, typescript, freshness, sync-status, vitest, fake-timers]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-06 GET /api/v1/metadata/sync-status and the SyncStatusResponse contract"
provides:
  - "SyncStatus component: fresh, stale, never-verified, error+retry and synthetic states above the course index"
  - "fetchSyncStatus loader (live and labelled-synthetic mock branch) with SyncStatus and SyncStatusLoader types"
  - "syntheticSyncStatus fixture that never carries a last_success_at"
affects: [09-10, 09-11, 09-12]

actuals:
  tokens: 5700
  tasks: 2
  commits: 2
plan_head_before: dfceac53c4a8a6b0803751b72de180d4ca909c10
plan_head_after: d10ef4b3ac8760d35d1a240d700061143a85f87f

tech-stack:
  added: []
  patterns:
    - "Loader-prop component with AbortController effect (CoverageNotice pattern) plus a 30 s render tick and 5 min refetch"
    - "Browser compares elapsed time only with the API's stale_after_seconds; it owns no threshold"
    - "A failed refresh keeps the last known status on screen; only the first load shows loading text"

key-files:
  created:
    - web/src/components/SyncStatus.tsx
    - web/src/components/SyncStatus.test.tsx
  modified:
    - web/src/types/rankings.ts
    - web/src/api/rankings.ts
    - web/src/App.tsx
    - web/src/fixtures/rankings.ts
    - web/src/App.test.tsx
    - web/src/api/rankings.test.ts

key-decisions:
  - "D-10 copy is Claude's lean, pending user review: 'Updated N min ago', 'Seat data may be out of date.', 'Seat data has not been verified by the live sync yet.', 'Data freshness unavailable.' with 'Retry freshness', 'Synthetic demo data: seat freshness is not live.'"
  - "Synthetic mode does not call the loader at all: the notice is static, so no request is made and no time can be fabricated. The mock branch of fetchSyncStatus remains as a defensive fallback that also returns last_success_at null."
  - "A refresh failure after a successful load keeps the previous status (its 'Updated' time is still true, and elapsed-time staleness keeps working); the error notice shows only when no status was ever loaded."
  - "The relative time and the elapsed-time staleness check share one 'now' state, resynced on each successful fetch, so the two never disagree."

patterns-established:
  - "Freshness notice keyed by term so a previous term's status is never displayed"

requirements-completed: [REQ-SYNC-01]

coverage:
  - id: D1
    description: "Students see 'Updated N min ago' from last_success_at of the live /sync-status response, with the absolute UTC time as the title; App renders it above CoverageNotice for the selected term"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "web/src/components/SyncStatus.test.tsx#a fresh status shows a relative time with the UTC time as its title"
        status: pass
      - kind: unit
        ref: "web/src/App.test.tsx#shows the freshness line from the sync-status loader above the course index"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stale warning appears from the API is_stale flag, and appears on a long-open page once elapsed time passes stale_after_seconds without a new fetch result; refetch every 5 minutes keeps the status on screen"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "web/src/components/SyncStatus.test.tsx#is_stale from the API renders the amber warning"
        status: pass
      - kind: unit
        ref: "web/src/components/SyncStatus.test.tsx#staleness appears on a long-open page without a new fetch result, then a refetch happens"
        status: pass
    human_judgment: false
  - id: D3
    description: "Honest states: never-verified text with no 'Updated', failed request with 'Retry freshness', synthetic mode never shows an Updated time; unmount clears both intervals"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "web/src/components/SyncStatus.test.tsx (never-verified, error+retry, synthetic, unmount tests)"
        status: pass
      - kind: unit
        ref: "web/src/api/rankings.test.ts#explicit mock sync status is synthetic and never carries a success time"
        status: pass
    human_judgment: false
  - id: D4
    description: "fetchSyncStatus requests /api/v1/metadata/sync-status?term= and the whole frontend suite, typecheck, lint and production build pass"
    requirement: REQ-SYNC-01
    verification:
      - kind: unit
        ref: "web/src/api/rankings.test.ts#sync status is requested from the API with the term query parameter"
        status: pass
      - kind: command
        ref: "npm --prefix web test && npm --prefix web run typecheck && npm --prefix web run lint && VITE_USE_MOCK_DATA=false VITE_API_BASE_URL=https://example.onrender.com npm --prefix web run build"
        status: pass
    human_judgment: false
  - id: D5
    description: "Wording and visual treatment of the freshness notice (D-10 copy, amber panel, placement above the coverage notice) is Claude's lean and needs user review; UI-SPEC was intentionally skipped"
    requirement: REQ-SYNC-01
    verification: []
    human_judgment: true
    rationale: "D-10 is a working decision flagged for user review; no test asserts UX adequacy"

duration: 15min
completed: 2026-09-29
---

# Phase 09 Plan 09: Data freshness notice Summary

**A SyncStatus notice above the course index shows "Updated N min ago" from the real /sync-status `last_success_at` (UTC time as title), warns "Seat data may be out of date." from the API's `is_stale` or elapsed time past the API's `stale_after_seconds` on a long-open page, and says so honestly when the data was never verified, the request failed or the data is synthetic.**

## Performance

- **Duration:** about 15 min of executor time
- **Completed:** 2026-09-29
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files:** 2 created, 6 modified (web only)

## Accomplishments

- Tracer: `SyncStatus` type mirroring `SyncStatusResponse`, `fetchSyncStatus` (live branch builds `/api/v1/metadata/sync-status?term=`), the component with five states, and `syncStatusLoader` prop wiring in `App` (default `fetchSyncStatus`, `key={term}`, `synthetic={mockMode}`) placed immediately before `CoverageNotice`. Tracer tests and typecheck/lint verified before expansion.
- Long-open page: a 30 s tick re-renders the relative text and re-checks staleness; a 5 min interval refetches while keeping the current status visible; both intervals are cleared on unmount (`vi.getTimerCount()` is 0 after unmount). Fake-timer test: a 5 min old status with `stale_after_seconds` 600 has no warning at first, then after 6 more minutes reads "Updated 11 min ago" with the warning and exactly one refetch.
- `syntheticSyncStatus` moved into `web/src/fixtures/rankings.ts` (null `last_success_at`, cadence 3600, stale_after 7200) and imported by the loader.
- No `dangerouslySetInnerHTML`; timestamps go through the existing strict `parseTimestamp` via `formatRelativeTime` and `formatAbsoluteTime`; no npm package added.
- Verification: full vitest 96 passed (7 files), `tsc -b` clean, `eslint .` clean, production build with `VITE_USE_MOCK_DATA=false VITE_API_BASE_URL=https://example.onrender.com` succeeds.

## Task Commits

1. **Task 1: Students see "Updated N min ago" from the live /sync-status endpoint** - `058647b` (feat)
2. **Task 2: Staleness appears while the page stays open; synthetic fixture; App and loader tests updated** - `d10ef4b` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] App test text collided with the seat rows' own "Updated N min ago"**
- **Found during:** Task 2
- **Issue:** the new App assertion using a 4 minute stub matched multiple elements, because the ranking rows render their own seat freshness as "Updated 4 min ago".
- **Fix:** the sync stub in `App.test.tsx` uses a distinct 37 minute age with whole-second timestamps.
- **Files modified:** web/src/App.test.tsx
- **Commit:** d10ef4b

**Total deviations:** 1 auto-fixed (test-only). **Impact:** none on shipped behaviour.

Two interpretation notes, not deviations: (a) in synthetic mode the component makes no request at all (the plan's Task 1 text only required the synthetic notice); (b) a failed refresh after a successful load keeps the last status rather than replacing it with the error notice, which the plan's "keep the current status on screen while refreshing" implies.

## Issues Encountered

None blocking. Observation for review: real API timestamps carry sub-second precision, and the existing `formatAbsoluteTime` then renders a title such as `2027-01-15 11:56:00.123 UTC` (milliseconds kept). It is cosmetic and left unchanged because `time.ts` is shared with seat freshness and outside this plan's files.

## Known Stubs

None. The mock-mode `syntheticSyncStatus` is an intentional, labelled fixture used only when `VITE_USE_MOCK_DATA=true`, and it deliberately has no timestamp.

## Threat Flags

None. Server strings are rendered only as React text; mock mode never shows an "Updated" time (T-09-26, T-09-27 mitigated); no packages added (T-09-SC).

## Next Phase Readiness

Ready for 09-10. D-10 copy needs user review before the beta announcement.

## Self-Check: PASSED

- FOUND: web/src/components/SyncStatus.tsx, web/src/components/SyncStatus.test.tsx
- FOUND commits: 058647b, d10ef4b
