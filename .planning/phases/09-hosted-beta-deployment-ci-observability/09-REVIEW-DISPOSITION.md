---
phase: 09-hosted-beta-deployment-ci-observability
source: 09-REVIEW.md
created: 2026-09-30
---

# Phase 09 — Code review disposition

Advisory record: one row per finding in `09-REVIEW.md`. Every finding is `open` until the user
triages it. Nothing has been fixed; the hosted worker is live on the code as merged.

| ID | Severity | Summary | Disposition |
|----|----------|---------|-------------|
| CR-01 | critical | `--max-missing-fraction` cannot override the gate once a prior sweep succeeded (`row_floor` still fails) | open |
| WR-01 | warning | `_JsonLineFormatter` URL scrub corrupts the JSON of failed-sweep log lines | open |
| WR-02 | warning | Whole-term fetch has no wall-clock deadline while holding the advisory lock | open |
| WR-03 | warning | Cadence floor checked outside the lock; overlapping workers can breach D-22(b) | open |
| WR-04 | warning | `--dry-run` is a full USF request but is never recorded, so the floor does not constrain it | open |
| WR-05 | warning | `require_sync_schema` reports any DB error as "migration 0004 not applied" | open |
| WR-06 | warning | One failing course auto-add can abort and repeat the whole sweep | open |
| WR-07 | warning | Public search has no `removed_at` guard; relies on cache-row deletion | open |
| WR-08 | warning | Legacy narrow ingest clears `removed_at` without rebuilding the cache or taking the sweep lock | open |
| IN-01 | info | `sanitize_error_detail` only redacts `postgres[ql]://` URLs | open |
| IN-02 | info | Legacy freshness fallback logs a warning with traceback per call | open |
| IN-03 | info | String-munged class names in `SyncStatus` | open |
| IN-04 | info | CI/deploy config minor hardening | open |
