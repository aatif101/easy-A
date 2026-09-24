---
gsd_state_version: "1.0"
current_plan: 3
status: ready_to_execute
stopped_at: Completed 08-02-PLAN.md
last_updated: "2026-09-24T17:30:46.225Z"
state_head: c306e3da723be0d87cb8b009ee2c258c078203ed
progress:
  total_phases: 10
  completed_phases: 6
  total_plans: 19
  completed_plans: 17
  percent: 60
last_activity: 2026-09-23
current_phase: 8
current_phase_name: MVP1-P5 — End-to-end MVP-1 verification
last_activity_desc: Phase 08 re-planned against live D-21 inventory (3,122 evidence-backed / 661 exceptions); checker passed
---

# Project State

`STATE.md` is the single source of **current, volatile facts** (counts, SHA, next action). Durable
rules live in `PROJECT.md` `<decisions>`; the phase sequence lives in `ROADMAP.md`; dated history
lives in `ARCHIVE.md`.

## Current state — as of 2026-09-23

**Repo / git**

- `origin/main` = `c063c27727f9cb87bb55da7b8f2ea76175abab67` (verified by fetch on
  2026-09-23; grade import, D-21 amendment and Phase 08 drafts merged via PRs #26–#28).

**Database (hosted Supabase — the only live DB now; the old local beta DB is history in `ARCHIVE.md`)**

- Term 202701 (as of 2026-09-22, Phase 06 full ingest): **3,783 sections, all campus=Tampa, across
  1,401 represented courses / 212 subjects. 0 non-Tampa rows. Quality: 0 errors.** (Live count
  2026-09-22; the 1,402-entry target list is not the represented-course count.) (Was 132 sections / 10 courses
  before Phase 06.)

- **8,662 `GradeDistribution` rows** in hosted Supabase (live query 2026-09-23): `202408` 179
  (pilot), `202501` 2,096, `202505` 465, `202508` 2,887, `202601` 3,035; 0 with null `course_id`.
  Summer 2026 returned no rows. Spring 2025 is the oldest term for coverage work; coverage work is
  stopped by decision (D-21). Ledger: `grade-coverage-import-2026-09-23.md`.
- Spring 2027 Tampa `section_rankings` (live, rebuilt 2026-09-23 21:51Z after the last grade
  ingest): `course` & `effective_n > 0` **3,122** sections / 1,117 courses (evidence-backed);
  `course` & `effective_n = 0` 300 (x4900 non-letter-grade); `subject` 311; `global` 50. D-21:
  3,122 evidence-backed, 661 listed source-limited exceptions. Do not describe subject/global
  fallback as that course's own grade distribution.

- `config/course_targets.toml` reconciled during Phase 06-01: now the full git-tracked 1,402-course
  Tampa list (was 5), generated reproducibly from `courses.csv` via `scripts/generate_tampa_targets.py`.

**Full Tampa universe (for MVP-1 sizing)**

- Enumerated 2026-09-20 across 265 public undergraduate catalog prefixes: **1,402 courses /
  3,782 Tampa sections** across 212 subjects. `courses.csv` is Git-ignored.

**Search performance (Phase 07, 2026-09-23) — REQ-PERF-01 met**

- Loopback HTTP `GET /api/v1/rankings/search` (local API over hosted Supabase, transaction
  pooler, 3,783 stored sections, 50 measured after 5 warmups): **p50 217 ms, p95 309.91 ms**,
  max 334 ms. Baseline was 1,202 ms p95. The Phase 3.5 synthetic 2.40 s figure is superseded.
  Deployed and browser latency are not measured.
- Whole-term cache rebuild: 3,783 rows in **4.77 s** (15 statements). The pre-batch run lost
  its connection after about 30 minutes. Whole-term quality pass: **2.45 s** (was about 35 minutes).
- Test baseline: 323 passed, 3 skipped. PostgreSQL integration tests still skip without
  `EASY_A_TEST_POSTGRES_URL`.

## Current milestone — MVP 1

All ~3,782 USF Tampa Spring 2027 sections ingested + searchable against hosted Supabase, each with
historical grade distributions imported and easiness computed from that real data, search
p95 < ~1.5s. Full definition + phase breakdown in `PROJECT.md` and `ROADMAP.md`. RMP links = MVP 2.

## Current Position

Current Plan: 3
Total Plans in Phase: 4

## Next action

**Phase 07 (MVP1-P4) is complete (3/3 plans).** REQ-PERF-01 is met with live evidence in
`.planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md`.
The fixes were one DB engine per API process, key-first search paging with page-only latest-seat
hydration, and whole-term batching of grade, instructor, GenEd and syllabus reads for the cache
rebuild and quality pass. No scoring, API-contract or schema change; Alembic head is still 0003.

**Grade coverage (live, 2026-09-23, after cache rebuild):** 8,662 grade rows (Spring 2025-Spring 2026
plus 179 Fall 2024 pilot). Spring 2027 Tampa: 3,783 sections. `score_source=course` 3,422 (3,122
with effective_n>0; the 300 with 0 are x4900-series independent-study/internship courses whose
history has no letter-grade weight, so they show the prior); `subject` fallback 311; `global` 50.
The 361 unmatched sections are source-limited (InfoCenter omits <5-student courses). Quality: 0
errors. See `.planning/grade-coverage-import-2026-09-23.md`.

**Do next:** `/gsd-execute-phase 8`. Phase 08 plans (08-01..08-04, 2 waves) were revised to encode
D-21 against the live inventory and passed the independent plan checker (0 blockers, 0 warnings) on
2026-09-23. UI decision (user, 2026-09-23): `course`/`effective_n = 0` rows show "No letter-grade
history (pass/fail or independent study) — score is a prior" — presentation-only, in 08-03.

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

- **Grade-history coverage for the remaining courses** — 1,212 Spring 2027 Tampa sections / 608
  courses still lack their own course's historical rows after the three-college import. Other
  colleges have not yet been processed in this coverage run. See the dated import ledger.

- **Blank grade-cell / suppression semantics (OQ-04)** — the upstream meaning of a blank InfoCenter
  cell is still genuinely unknown. MVP1-P1 (04-02, 2026-09-21) made the parser fail closed on any
  blank canonical count instead of silently coercing to `0`; that is a safety policy, not a
  resolution of OQ-04. Needs a real/sample InfoCenter export.

- ~~**Suffix-course query guard**~~ **RESOLVED (Phase 06)** — the merged `_retain_exact_course_rows`
  guard held across all 33 base/suffix pairs at full scale; `assert_suffix_exact_ingest` confirms no
  L-variant leakage. Guard code unchanged.

- ~~**Search p95 at full scale**~~ **RESOLVED (Phase 07)**: loopback HTTP p95 309.91 ms at 3,783
  sections on hosted Supabase. Deployed-host latency is still to be measured once a host exists.
- **Deployment host and domain** not yet supplied.

## Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links (MVP 2), a scoring methodology rewrite. All remain candidate
later phases / optional research unless explicitly approved.

## Session Continuity

**Stopped at:** Completed 08-02-PLAN.md
Stale Phase 08 handoff (`HANDOFF.json`, `.continue-here.md`) removed after resumption.
**Resume file:** None

Earlier session: 2026-09-23. Phase 07 execution ran across three sessions. Codex (Windows clone)
completed the 07-01 benchmarks and baseline. A Claude Code WSL session fetched that branch,
committed the measurement script and 07-02 grade batching, then ended mid-measurement. A third
session resumed from the commits and the untracked perf report, batched the per-section rebuild
lookups, tuned the serve path (07-03), and recorded the final evidence.

Last session: 2026-09-24T17:30:46.160Z
/ 1,402 courses / 3,783 sections, 0 non-Tampa, 0 quality errors) → scale validation (all 3 checks
pass). The operator authorized the live run and it completed. Two operational fixes landed in the
orchestrator: `--subject-timeout` (a stalled subject no longer freezes the run) and deferring the
per-subject whole-term quality scan to one final pass (O(n²)→O(n)); `coverage.py`/`target_cli.py`
guards untouched. Deferred to Phase 07: batch/hoist the per-course grade aggregate. Next action:
Phase 07 (MVP1-P4) — full-scale cache build + search p95 < ~1.5s.

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
| Phase 07 P01 | split sessions | 2 tasks | 4 files |
| Phase 07 P02 | ~1h | 2 tasks | 10 files |
| Phase 07 P03 | ~45min | 2 tasks | 5 files |
| Phase 08 P01 | 55min | 2 tasks | 2 files |
| Phase 08 P08-02 | ~35min | 3 tasks | 4 files |

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
- [Phase 07]: The REQ-PERF-01 gate is loopback HTTP p95 (request + body + JSON validation) with the API on hosted Supabase. Direct route timing is a diagnostic only.
- [Phase 07]: No search index added. At ~4k rows the slow page was a join strategy (a nested loop over a materialized latest-seat window), fixed by key-first paging. seat_snapshots(section_id, observed_at DESC, id DESC) is the candidate index if snapshot history grows.
- [Phase 07]: Whole-term rebuild takes refreshed_at from one transaction-time now() (equal to per-row func.now() on PostgreSQL) so ORM updates batch.
- [Phase 8]: [Phase 08-01]: Implemented scripts/verify_rankings_pages.py as one complete bounded-walk/identity-reconciliation algorithm in Task 1 rather than incrementally; all 16 Task 1+2 tests (including every boundary/ordering/empty-term case) passed with zero additional production-code changes in Task 2.
- [Phase 8]: [Phase 08-01]: Live 202701 scan against hosted Supabase returned PASS -- 3,783/3,783 sections reconciled exactly, api_score_source_split matches STATE.md's D-21 inventory (course 3,422/300 effective_n=0, subject 311, global 50).
- [Phase 8]: [Phase 08-02]: evidence_backed requires both attributed letter-grade weight and cached-total reconciliation against a cache built by the real refresh_section_rankings path (not a numeric score alone); assert_honest_coverage's exception is scoped to score_source=course, effective_n=0, with stored A-F sum 0 and total_grades sum > 0 for the exact course key -- every other zero-sample claim still fails (D-20, D-21).
- [Phase 8]: [Phase 08-02]: Live 202701 run against hosted Supabase returned PASS/PASS -- 3,122 evidence-backed, 661 listed exceptions (361 no_rows + 300 non_letter_grade); validator's verified non-letter-grade exception count (300) equals the inventory's exception_non_letter_grade count exactly.
