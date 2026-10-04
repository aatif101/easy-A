# Milestones

## v1.0 MVP 1 (Shipped: 2026-10-04)

**Phases completed:** 8 phases, 47 plans, 101 tasks

**Key accomplishments:**
- Course-batched `section_rankings` cache with live seat hydration; ranking search served in two SQL queries (hosted p95 277 ms at 3,783 sections, target ~1.5 s).
- Grade ingestion attributes every grade row to a course (`GradeDistribution.course_id`), failing closed on blank cells; all ingested Tampa courses have real, reconciled historical grades.
- All ~3,783 USF Tampa Spring 2027 sections ingested and searchable on hosted Supabase, verified in a dated Phase 8 report (REQ-COVERAGE-03, REQ-GRADES-01, REQ-PERF-01).
- Hosted beta live on Render: Docker image, Blueprint, CI with Postgres, near-live sync worker (`python -m easy_a.sync`), `removed_at` handling, `/metadata/sync-status` and a web freshness notice.
- Professor-level grades (Phase 10): 8,535 historical sections backfilled, 637 sections moved to instructor-level scores, per-instructor breakdown in the ranking panel; UAT 9/9 passed.

**Closeout:** override_closeout. Audit status `tech_debt` (see [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)). Phases 03.5, 06, 07 have no VERIFICATION.md (covered by Phase 8); 04, 08, 09 read as stale to the verifier. 5 open artifact items acknowledged (1 phase-03.5 context list, 4 deferred items). Known gaps: REQ-TEST-01 partial by design; Phase 9 sweep-duration gap (37-51 s vs 30 s); P10-WR-02 and P10-WR-03 open. Milestone closed with `--force` because Phases 1-3 are legacy roadmap entries with no phase directories.

---
