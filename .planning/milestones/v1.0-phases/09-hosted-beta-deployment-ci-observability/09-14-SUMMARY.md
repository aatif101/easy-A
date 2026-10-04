---
phase: 09-hosted-beta-deployment-ci-observability
plan: 14
subsystem: infra
tags: [rollout, alembic, migration, dry-run, ci, github, supabase]
status: complete

requires:
  - phase: 09-hosted-beta-deployment-ci-observability
    provides: "09-05..09-07 sweep/CLI, 09-09 gate, 09-13 Dockerfile, Blueprint config and CI docker job"
provides:
  - "Hosted Supabase at Alembic head 0004_sync_removed_at (operator-applied, verified read-only)"
  - "One real-data dry run of the whole sweep path: gate passed, 228 MiB peak RSS, nothing written"
  - "09-ROLLOUT-EVIDENCE.md with migration, dry-run, row-count, research-comparison, Blueprint-time and CI/merge sections"
  - "Phase 9 code merged to main via PR #33 behind green python, web and docker jobs"
affects: [09-15]

actuals:
  tokens: 3100
  tasks: 3
  commits: 3
plan_head_before: d99a206c20dbd742d58164d5d012799c10c8c9b6
plan_head_after: 7140e55febde4ce423497bcf212d0f86eb2cc0d8

tech-stack:
  added: []
  patterns:
    - "Read-only row-count capture in a READ ONLY transaction before and after a dry run to prove it wrote nothing"
    - "Migrate first, dry-run second, merge third, then create the Blueprint (RESEARCH Pitfall 8)"

key-files:
  created:
    - .planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md
  modified:
    - tests/refresh/test_postgres_coverage.py
    - tests/test_database_config.py

key-decisions:
  - "Earliest Blueprint creation is 2026-09-30T06:15:46Z (dry-run start plus the 60-minute floor), so the hosted worker's first sweep keeps the D-22 floor."
  - "The merge of origin/main into the branch (merge commit d99a206, no file changes) was done before anything was applied, so the branch descends from origin/main (PROJECT.md D-10)."
  - "Instructor-change delta (150 vs 89 in research) and the 543 updated sections are recorded as unexplained-but-not-gate-relevant; a second USF request to investigate was not allowed by this plan."

requirements-completed: [REQ-OPS-01, REQ-SYNC-01]

duration: about 25 min executor time after Task 1 (excludes operator waits)
completed: 2026-09-30
---

# Phase 9 Plan 14: Pre-deploy Rollout Summary

**Migration 0004 applied by the operator, a single read-only real-data dry run proved the sweep path (gate passed, 228 MiB peak, zero rows written), and PR #33 merged phase 9 to main with python, web and docker green and the PostgreSQL tests actually executing.**

## Performance

- **Duration:** about 25 min of executor time (Task 1 and all operator waits excluded)
- **Started:** 2026-09-30T05:15Z (dry run); **Completed:** 2026-09-30T05:38Z
- **Tasks:** 3 of 3 (Task 1 and the merge were operator actions)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- **Migration 0004** verified read-only after the operator applied it: head `0004_sync_removed_at`, `sections.removed_at` is timestamptz and nullable, the `ix_seat_snapshots_section_id_observed_at` index exists, and 0 rows have `removed_at` set.
- **Real-data dry run**, executed exactly once: exit 0, gate passed, 6,645 rows and 6,645 distinct CRNs, 3,704 in scope (2,941 graduate, 0 non-Tampa, 0 unparseable), 7,103,329 bytes with no Content-Encoding, `tail_error` true as expected, 15.2 s. Expected catch-up: 12 inserts, 105 removals (2.8 percent), 150 instructor changes, 97 seat changes, 13 would-add courses.
- **Memory** peaked at 228 MiB (log line) and 233,428 kB (`/usr/bin/time -v`), under the 350 MB target and the 512 MB limit.
- **A2** held: no idle-in-transaction termination during the roughly 15 s fetch under the advisory-lock transaction. A writing sweep was not run (prohibited here), so the first hosted worker sweep remains the last confirmation.
- **Row counts** for sections, section_instructors, seat_snapshots, section_rankings and ingest_runs were identical before and after.
- **Merge:** PR #33 merged at 2026-09-30T05:36:53Z as `5def3562824599d5705d286fee3b8dc046facc76`; `origin/main` equals it. The final python job log shows `693 passed`, no PostgreSQL skip line, and the Alembic upgrade, downgrade and upgrade round-trip succeeded on postgres:16.
- **Earliest Blueprint creation:** 2026-09-30T06:15:46Z.

## Task Commits

1. **Task 1: operator applies migration 0004** - no commit (operator action; recorded in the evidence file).
2. **Task 2: real-data dry run and evidence** - `b2e89cc` (docs)
3. **Task 3: CI fixes and merge evidence** - `79f9efd` (fix), `7140e55` (docs)

The plan metadata commit follows this summary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_postgres_coverage_and_latest_snapshot` assumed the seeded course was the first target row**
- **Found during:** Task 3 (first CI run, python job, head b2e89cc)
- **Issue:** `coverage_metadata` returns one row per configured target. After phase 6 regenerated `config/course_targets.toml` for the full Tampa universe, `rows[0]` is ACG 2021, so `rows[0].section_count == 2` failed with `0 == 2`. The test had been skipping locally and in earlier CI runs (no PostgreSQL URL), which hid it.
- **Fix:** select the MAC 1105 row by key.
- **Files modified:** `tests/refresh/test_postgres_coverage.py`
- **Commit:** `79f9efd`

**2. [Rule 1 - Bug] `test_missing_database_url_fails_loudly` was not hermetic under CI**
- **Found during:** Task 3 (first CI run)
- **Issue:** The CI job sets `MIGRATION_DATABASE_URL` for the Alembic step. The test cleared only `DATABASE_URL`, so `require_migration_database_url()` returned the CI value and did not raise.
- **Fix:** also `monkeypatch.delenv("MIGRATION_DATABASE_URL")` in the test.
- **Files modified:** `tests/test_database_config.py`
- **Commit:** `79f9efd`

Both fixes are test-only; no product code changed. Fix attempts used: 1 of 3.

### Other plan-execution notes

- **Merge of origin/main into the branch:** before Task 1 the branch was merged with a freshly fetched origin/main (merge commit `d99a206`, no file changes). It is the recorded `plan_head_before`, so it is not counted in this plan's 3 commits.
- **Push blocked once:** the first `git push` was rejected because the `gh` token lacked the `workflow` scope (the branch changes `.github/workflows/ci.yml`). The operator ran `gh auth refresh -h github.com -s workflow`, then the approved push and PR creation succeeded. This was an authentication gate, not a code issue.
- **Hosted database:** only read-only, READ ONLY-transaction queries were run; no writes, no writing sweep.

## Issues Encountered

- Instructor changes were 150 against 89 in research, and 543 sections were "updated", more than the removals, instructor and seat changes taken separately can explain. Not verified (no second USF request was permitted). Worth a look at the first real hosted sweep; not a gate issue.
- A push run of CI on the merge commit (run 36674223585) was still in progress when the evidence was written.

## Known Stubs

None.

## Threat Flags

None. The only new network or trust surface (pushing to GitHub) was operator-approved, and the evidence file passed the negative grep for connection strings and pooler hostnames.

## Next Phase Readiness

- Plan 09-15 (Blueprint creation and go-live) can proceed, but not before **2026-09-30T06:15:46Z**.
- The docs commits for this plan (`b2e89cc`, `7140e55`, and the metadata commit) exist only on the local branch `codex/render-setup`; `origin/main` contains the code (merge `5def356`) but not those evidence docs. They still need to reach origin, by the operator or a follow-up decision.

## Self-Check: PASSED

- FOUND: `.planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md`
- FOUND commits: `b2e89cc`, `79f9efd`, `7140e55`
- Evidence file has the four required headings plus "## CI and merge" and passes the negative grep.
