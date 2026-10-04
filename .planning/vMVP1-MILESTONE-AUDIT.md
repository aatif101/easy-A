---
milestone: MVP 1
audited: 2026-10-04
status: tech_debt
scores:
  requirements: 12/13 satisfied, 1 partial by design
  phases: 5/8 with a VERIFICATION.md (04, 05, 08, 09, 10); 03.5, 06, 07 covered by Phase 8
  integration: 11/11
  flows: 7/7
gaps:
  requirements: []
  integration: []
  flows: []
tech_debt:
  - phase: milestone
    items:
      - "REQ-TEST-01 partial by design: Postgres-only paths (advisory lock, removed_at deletes, backfill transaction) skip without EASY_A_TEST_POSTGRES_URL"
      - "Phases 03.5, 06, 07 have no VERIFICATION.md; their requirements (REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01) are verified in 08-VERIFICATION.md"
      - "W1: render.yaml sync:false values (EASY_A_ALLOWED_FRONTEND_ORIGINS, VITE_API_BASE_URL) have no startup guard; unset origins silently default to localhost and the hosted site fails CORS"
      - "W2: no automatic cache rebuild after a grade re-import; operator must rebuild (confirm runbook says so)"
      - "W3: worker hard-codes --term 202701; other terms and post-backfill 202701 need a manual rebuild (--rebuild-term)"
  - phase: 10-professor-level-grades
    items:
      - "P10-WR-02: DB error text can reach CLI stdout / --report-json (fix before any backfill re-run)"
      - "P10-WR-03: wrong --rebuild-term gives a vacuous invariant and stale cache (fix before any backfill re-run)"
      - "UAT 9: instructor_course drift 637 -> 664 attributed to USF section changes by owner, not independently verified"
      - "10-VERIFICATION override accepted_at time-of-day is a placeholder"
  - phase: 09-hosted-beta-deployment-ci-observability
    items:
      - "Carry-over per memory note: WR-03, NEB 0001, deferred rehearsal, branch cleanup (status not re-checked in this audit)"
nyquist:
  compliant_phases: [04, 07, 08, 09, 10]
  not_validated_phases: [03.5, 05, 06]
  missing_phases: []
  overall: partial
---

# MVP 1 Milestone Audit

Audited on `main` = 54dd482. Integration checks are read-only; pytest gave 1043 passed, 4 skipped, 1 xfailed, vitest 119 passed. Hosted and live-Postgres checks were not re-run in this audit.

## Requirements (3-source cross-reference)

| REQ-ID | Phase | Verified in | REQUIREMENTS.md | Status |
|--------|-------|-------------|-----------------|--------|
| REQ-COVERAGE-01, REQ-SEAT-01, REQ-SEAT-02, REQ-CONFIG-01 | pre-04 | earlier delivery | [x] | satisfied |
| REQ-COVERAGE-02 | 04 | 04-VERIFICATION (passed) | [x] | satisfied |
| REQ-DATA-02 | 05 | 05-VERIFICATION (passed) | [x] | satisfied |
| REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01 | 06-08 | 08-VERIFICATION (passed, 10/10) | [x] | satisfied |
| REQ-OPS-01, REQ-SYNC-01 | 09 | 09-VERIFICATION (passed) | [x] | satisfied |
| REQ-PROF-01 | 10 | 10-VERIFICATION (passed), UAT 9/9 | [x] | satisfied |
| REQ-TEST-01 | cross-cutting | n/a | [◐] | partial by design |

No orphaned requirements. I did not re-extract SUMMARY `requirements-completed` frontmatter for every phase, so the SUMMARY leg of the cross-check is only spot-covered by the Phase 8 and Phase 10 reports.

## Integration (gsd-integration-checker)

11 links wired, 0 orphaned, 0 broken, 4 warnings (W1-W4 above). 7 of 7 E2E flows complete; flows 5 (backfill vs sweep) and 6 (hosted deploy) rest on code reading, not executed checks.

## Nyquist

04, 07, 08, 09, 10 compliant. 03.5, 05, 06 have `status: draft` VALIDATION.md (not yet reconciled by validate-phase, a coverage TODO, not a failure).

## Verdict

No blockers. Status `tech_debt`: all requirements met or partial by design, with the deferred items above to review.
