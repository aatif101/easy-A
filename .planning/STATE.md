---
gsd_state_version: "1.0"
current_plan: 3
status: ready
stopped_at: Completed 06-03-PLAN.md -- REQ-COVERAGE-03 proven at scale against live hosted Supabase; Phase 06 (MVP1-P3) complete
last_updated: "2026-09-22T09:16:59.935Z"
state_head: 95d57e43905784b20542a3ef9c0e4ad03eff3e0d
progress:
  total_phases: 10
  completed_phases: 5
  total_plans: 12
  completed_plans: 12
  percent: 50
last_activity: 2026-09-21
current_phase: 6
current_phase_name: MVP1-P3 — All-Tampa section ingestion
last_activity_desc: Phase 05 complete and operator-approved; all 10 pilot courses now have reconciled Fall 2024 history and course-backed live rankings
---

# Project State

`STATE.md` is the single source of **current, volatile facts** (counts, SHA, next action). Durable
rules live in `PROJECT.md` `<decisions>`; the phase sequence lives in `ROADMAP.md`; dated history
lives in `ARCHIVE.md`.

## Current state — as of 2026-09-21

**Repo / git**

- `origin/main` = `d556c2822f7a7dd8d0d450cf543c4eb1c8fb55f7` (verified by fetch).
  Phase 5 planning tip `origin/dev1/tampa-coverage-pilot` =
  `8893b9b178df005b7f4a30e4a1fa84c7b6f961c4`. Checkpoint branch:
  `codex/phase5-1-tracer-checkpoint`, based directly on that planning tip.

**Database (hosted Supabase — the only live DB now; the old local beta DB is history in `ARCHIVE.md`)**

- Term 202701 (as of 2026-09-22, Phase 06 full ingest): **3,783 sections, all campus=Tampa, across
  1,402 courses / 212 subjects. 0 non-Tampa rows. Quality: 0 errors.** (Was 132 sections / 10 courses
  before Phase 06.)
- **179 `GradeDistribution` rows, unchanged — only the 10 pilot courses carry sourced Fall-2024
  history** (`effective_n > 0`, `score_source=course`). Every one of the ~1,392 newly ingested
  courses is the honest `effective_n=0` / `score_source=global` state (D-20) — NOT course history.
  Scaling grade coverage to the rest of Tampa is a separate future effort (bounded per-course SGDIS
  imports, mirroring Phase 05), not MVP1-P3 scope.
- `config/course_targets.toml` reconciled during Phase 06-01: now the full git-tracked 1,402-course
  Tampa list (was 5), generated reproducibly from `courses.csv` via `scripts/generate_tampa_targets.py`.

**Full Tampa universe (for MVP-1 sizing)**

- Enumerated 2026-09-20 across 265 public undergraduate catalog prefixes: **1,402 courses /
  3,782 Tampa sections** across 212 subjects. `courses.csv` is Git-ignored.

**Phase 3.5 (ranking search performance) — delivered, NOT closed**

- SQL search rewrite, `section_rankings` cache, cleanup cascade, and benchmark all shipped (5/5).
  Circular import that blocked `check_data_quality.py` fixed (`2bb984a`). Postgres suite 256
  passed; quality 0 errors.
- Performance goal **not met**: p95 ~**2.40s** at a 3,782-section synthetic fixture over Supabase,
  above the ~1.5s target. Accepted deviation (`WINDOWS.md`); folded into MVP-1 as blocking phase
  MVP1-P4 (since MVP 1 targets Supabase, not local).

## Current milestone — MVP 1

All ~3,782 USF Tampa Spring 2027 sections ingested + searchable against hosted Supabase, each with
historical grade distributions imported and easiness computed from that real data, search
p95 < ~1.5s. Full definition + phase breakdown in `PROJECT.md` and `ROADMAP.md`. RMP links = MVP 2.

## Current Position

Current Plan: 3
Total Plans in Phase: 3

## Next action

**Phase 05 is complete and human-approved.** Ten bounded authenticated InfoCenter SGDIS reports
for Tampa, Fall 2024, produced 179 aggregate rows totaling 7,544 grades. Every per-course hosted
database raw total matches its source report; all 132 live sections report `effective_n > 0` /
`score_source=course` after the separate 202701 cache rebuild. Quality is 0/0/0, idempotency was
proved by repeat import, and no raw workbook is tracked.

**2/2 plans complete** in Phase 05. **Do next: plan/execute Phase 06 (MVP1-P3) to expand from the
10-course pilot to the full Tampa Spring 2027 universe, preserving the same honest grade-coverage
contract for every newly added course.**

Remaining build steps, in order (see ROADMAP MVP1-P2..P5):

1. **MVP1-P3** — all-Tampa section ingestion (10 → ~3,782); resolve the CHM 2045/2045L suffix-guard
   blocker (33 base courses have suffix variants); reconcile config vs stored data.
2. **MVP1-P4** — full-scale cache build + tune search to p95 < ~1.5s on Supabase.
3. **MVP1-P5** — end-to-end MVP-1 verification.

## History

Sprint 5 / Phase 1 / Phase 2 results, the 2026-09-09 data-quality run, and dated test baselines
are in `.planning/ARCHIVE.md`. They describe the earlier local beta DB and are not current facts.

## Decisions (load-bearing; full set is PROJECT.md `<decisions>` D-01..D-20)

- D-02: scoring model preserved — **no rewrite without explicit approval**
- D-06: no fabricated data / invented coverage figures; D-07: explicit unavailable states
- D-20: a global-prior fallback (`effective_n = 0`) is **not** course history — never present it as such
- D-04 / D-19: term/CRN/source dedup; never commit raw grade export files
- D-08 / D-09: bounded, narrow USF requests; no scraping/crawling
- D-10: verify `origin/main` by fetch; do not check out/merge an unverified local `main`
- Note: the D-18 "broader launch coverage is deferred" decision is **superseded** — full Tampa
  breadth is now the MVP-1 goal (see PROJECT.md). Email alerts (D-16) and RMP (D-17, = MVP 2) stay deferred.
- Phase 03.5: cache non-seat ranking fields and hydrate live seats at read time; whole-term cache
  rebuild wrapped into `refresh_data`; cleanup cascade covers `section_rankings`.

## Still open

- **Historical coverage must scale with Phase 06** — the current 10-course pilot is fully backed by
  real Fall 2024 aggregates, but every newly ingested Tampa course must receive sourced history or
  remain an explicit `effective_n=0` / `score_source=global` state.
- **Blank grade-cell / suppression semantics (OQ-04)** — the upstream meaning of a blank InfoCenter
  cell is still genuinely unknown. MVP1-P1 (04-02, 2026-09-21) made the parser fail closed on any
  blank canonical count instead of silently coercing to `0`; that is a safety policy, not a
  resolution of OQ-04. Needs a real/sample InfoCenter export.
- **Suffix-course query guard** — USF's CHM 2045 query also returns CHM 2045L; the exact-course
  guard rejects it. 33 base courses have suffix variants; resolve before scaling (do not weaken it).
- **Search p95 at full scale** — ~2.40s on Supabase at 3,782 sections; must reach < ~1.5s for MVP 1.
- **Deployment host and domain** not yet supplied.

## Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links (MVP 2), a scoring methodology rewrite. All remain candidate
later phases / optional research unless explicitly approved.

## Session Continuity

**Stopped at:** Completed 06-03-PLAN.md -- REQ-COVERAGE-03 proven at scale against live hosted Supabase; Phase 06 (MVP1-P3) complete
**Resume file:** None

Last session: 2026-09-22T09:16:59.891Z
06-02 Task 1 (resumable, paced orchestrator + unit test + runbook) is committed and verified. The
plan is intentionally halted at Task 2 — a `gate="blocking-human"` checkpoint — before Task 3 (the
~2,800-request live USF ingestion). Next action: the operator must review
`docs/runbooks/all-tampa-ingestion.md` and confirm courses.csv freshness + pacing, then explicitly
authorize the live run before any executor proceeds to Task 3.

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 03.5 P01 | 15min | 2 tasks | 7 files |
| Phase 03.5 P02 | 7min | 2 tasks | 5 files |
| Phase 03.5 P03 | 8min | 3 tasks | 8 files |
| Phase 03.5 P04 | 20min | 2 tasks | 2 files |
| Phase 04 P01 | 25min | 2 tasks | 3 files |
| Phase 04 P02 | 15min | 2 tasks | 4 files |
| Phase 05 P01 | 54min | 3 tasks | 3 files |
| Phase 05 P02 | 55min | 3 tasks | 2 files |
| Phase 06 P01 | 30min | 2 tasks | 8 files |
| Phase 06 P03 | 75min | 3 tasks | 2 files |

## Decisions

- [Phase 04]: Reused resolve_course_id() for grade attribution instead of a grade-specific matcher, and treated course_id as a mutable attributed property (never part of the term/CRN/source identity) so a same-key re-import can backfill it (D-04).
- [Phase 04-02]: Wrote the blank-cell rejection reason as a stated two-sided ambiguity (cannot distinguish zero from unavailable or suppressed) rather than asserting suppression, and kept unattributed_grade_row additive alongside grade_total_mismatch/orphan_grade_row rather than merging them (D-06, D-07).
- [Phase 05-01]: Reconciled the exact source Total Grades sum to raw total_grade_count, never the Bayesian-smoothed easiness score, and required a separate 202701 cache rebuild after historical imports.
- [Phase 05-01]: Advanced hosted Supabase from migration 0002 to checked-in migration 0003 after the tracer exposed the missing section_rankings table.
- [Phase 05-02]: Used one exact-course Fall 2024 Tampa report per course, imported each historically, then rebuilt the 202701 cache once after all imports.
- [Phase 05-02]: No observed real export contained a blank canonical count, so OQ-04 remains open and the fail-closed parser was left unchanged.
- [Phase 6]: [Phase 06-01]: Reconciled config/course_targets.toml to the full ~1,402-entry generated list (locked decision 1); CHM ingested end-to-end (23 courses/295 sections) against hosted Supabase with 0 quality errors, proving the suffix guard, Tampa scope guard, and D-20 honest-coverage contract at scale.
- [Phase 6]: [Phase 06-01]: Fixed src/easy_a/refresh/cleanup.py's _target_filter (OR-of-AND -> composite tuple_(...).in_(...)) after the full-scale config tripped SQLite's expression-tree depth limit in an existing test; coverage.py/targets.py/target_cli.py remained unmodified throughout.
- [Phase 06]: [Phase 06-02]: Built scripts/refresh_all_tampa.py as a resumable, paced per-subject orchestrator that shells out to the unmodified refresh_course_coverage.py once per subject (own process/transaction each), records completed subjects to a progress file for resume, and continues past a failed subject rather than aborting; coverage.py/target_cli.py remain unmodified. Halted at the plan's blocking-human checkpoint before the ~2,800-request live USF run.
- [Phase 6]: [Phase 06-03]: validate_tampa_ingest.py's suffix-leak signal is a suffix course ingested but owning 0 stored sections (not a Section-Course join mismatch, which the FK guarantees can't happen); real proof against the live DB found no leak across all 33 pairs.
- [Phase 6]: [Phase 06-03]: gsd tdd-red-evidence is Node-TAP-specific and cannot classify pytest output (always zero_tests_discovered); workflow.tdd_mode is false for this project so the automated gate isn't enforced -- RED/GREEN was verified directly via pytest's own per-test evidence instead.
