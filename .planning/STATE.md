---
gsd_state_version: "1.0"
current_plan: 8
status: design_direction_selected
stopped_at: Completed 10-07-PLAN.md (D-04 approved; next 10-08)
last_updated: "2026-10-01T21:25:41.823Z"
state_head: 0819965ad200a12ee44c01c0c47c636c23f3aee2
progress:
  total_phases: 11
  completed_phases: 7
  total_plans: 45
  completed_plans: 43
  percent: 64
last_activity: 2026-09-30
current_phase: 10
current_phase_name: Professor-level grades
last_activity_desc: Plan 09-15 complete; hosted beta live on Render, two sweeps soaked, 30 s sweep-duration gap open for operator decision
---

# Project State

`STATE.md` is the single source of **current, volatile facts** (counts, SHA, next action). Durable
rules live in `PROJECT.md` `<decisions>`; the phase sequence lives in `ROADMAP.md`; dated history
lives in `ARCHIVE.md`.

## Current state — as of 2026-09-30 (database facts retain their observation dates)

**Repo / git**

- `origin/main` = `b485efb91e95aae0ec93f5578636a8f1c7542f99` (verified by fetch on 2026-09-30;
  merges PR #34 `docs/phase-9-rollout-evidence`; PR #33 `5def356` carried the Phase 9 code). The
  hosted worker deployed exactly this commit.
- Working branch: `codex/render-setup`, descends from `origin/main`. Its 09-15 evidence and
  state commits are **local only (not pushed)**. Pre-existing untracked `.planning/config.json`,
  `.planning/research/`, `.planning/state.json`, `phase1_report.md` and `.mcp.json` were
  preserved.

**Hosted beta (live since 2026-09-30, Render, region ohio; evidence in
`.planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md`)**

- API `https://easy-a-api.onrender.com` (`srv-daul6tfpn0mc7384h4fg`, web, Starter); worker
  `easy-a-worker` (`srv-daul6tnpn0mc7384h5jg`, background worker, Starter); static site
  `https://easy-a-web.onrender.com` (`srv-daul6tfpn0mc7384h50g`). All on `main`, auto-deploy on.
  `/health` returns `{"status":"ok"}`; CORS returns exactly the web origin. Failure-email
  notifications (D-09) rest on the operator's confirmation, not independently verified.
- Worker sweeps hourly outside registration windows (next registration window Nov 2, 2026).
  Sweep 1 (2026-09-30 18:23:25Z): 24 inserted, 560 updated, 109 removed, 156 instructor changes,
  100 seat changes, 10 courses auto-added, 4 deferred by the per-sweep cap, duration 50.69 s.
  Sweep 2 (19:32:01Z): 5 inserted, 49 updated, 0 removed, 6 instructor changes, 1 seat change,
  3 courses auto-added (LDR 3363, LDR 4204, POT 4936), duration 37.166 s. `failures_last_24h` 0,
  `is_stale` false (20:05Z). Change-only writes reconcile exactly between the two snapshots.
- **Open gap: both sweeps exceed the plan's 30 s soak criterion; not accepted or resolved.**
  NEB 0001 stays unapplied ("no catalog heading"), so every sweep reports `records_failed` 1.
- One operator restart (2026-09-30 ~20:01Z) confirmed SIGTERM handling (`worker_stopped`, A1)
  and the restart floor (new instance slept until 20:38:57Z). Worker `peak_rss_mb` 193.6 / 223.4;
  operator-reported Render Metrics peak under 350 MB.

**Database (hosted Supabase — the only live DB now; the old local beta DB is history in `ARCHIVE.md`)**

- **Live after the worker's sweeps (READ ONLY snapshot 2026-09-30T20:05Z, Alembic head
  `0004_sync_removed_at`): term 202701 has 3,703 active sections and 109 removed sections**
  (3,812 rows in `sections`; removed sections are excluded from search and the rankings cache).
  Score sources on the 3,703 cache rows: `course` 3,332, `subject` 322, `global` 49. 13 auto-added
  non-target courses (ARH 4301, ART 3781C, ART 4930, FIL 4839, FIN 4934, FRE 2201, HUM 4368,
  HUM 4391, HUM 4434, HUM 4890, LDR 3363, LDR 4204, POT 4936), all `subject` fallback, none
  showing own-course history (D-20). `section_instructors` 4,417; `seat_snapshots` 4,356;
  `ingest_runs` 114. The D-21 figures below are the 2026-09-24 record.
- **D-21 re-baseline after the first sync (2026-09-30, inventory over 3,698 active sections, taken
  after sweep 1 and before the 5 sweep-2 inserts): 3,046 evidence-backed, 652 listed exceptions
  (368 `no_rows`, 284 `non_letter_grade`); 1,081 evidence-backed courses; integrity PASS.**
  The grade data was not touched; the shift is the sync's 109 removals, 24 inserts and 10 new
  courses. `08-D21-EXCEPTIONS.md` is unchanged, the dated 2026-09-24 record.

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
- **Hosted single-client p95 (2026-09-30T18:30Z, `benchmark_rankings_search.py --remote-url`,
  public HTTPS from one workstation, 50 calls / 5 warmups, 3,698 sections): p50 131.53 ms, p95
  212.56 ms, max 371.92 ms. Below the 1,500 ms bar.** Browser and concurrent-user latency: NOT
  MEASURED.
- Test baseline: CI on PR #33 head `79f9efd`: 693 Python tests passed (PostgreSQL integration
  tests executed on postgres:16) and 96 frontend tests passed. The 2026-09-23 "323 passed, 3
  skipped" figure is superseded.

## Current milestone — MVP 1

All ~3,782 USF Tampa Spring 2027 sections ingested + searchable against hosted Supabase, each with
historical grade distributions imported and easiness computed from that real data, search
p95 < ~1.5s. Full definition + phase breakdown in `PROJECT.md` and `ROADMAP.md`. RMP links = MVP 2.

## Current Position

Current Plan: 8
Total Plans in Phase: 9

## Next action

**Current (2026-10-01): Phase 9 is COMPLETE** (verification `passed`, UAT 4 passed + 1 optional deferred
follow-up, security 58/58 closed; PR #33 and #35 merged, hosted beta live on `046aa5d`). The first hosted
sweep on the CR-01 fix image succeeded (2026-09-30T23:58:46Z, about 26 s). Still open by decision: review
warnings WR-01..WR-08 / IN-01..IN-04 (WR-03, the cadence-floor race during worker overlap, is worth fixing
before Spring 2027 registration), NEB 0001 (fails every sweep), and the optional gate-recovery rehearsal
(`09-UAT.md` test 5). **Next: Phase 10 (professor-level grades)** via `/gsd-discuss-phase 10`;
D-24 (instructor-course scoring retune) was approved 2026-09-30. **Phase 10 status (2026-10-01): plan 10-01 complete** (retune + Laboratory rule in code, tests and docs, branch `phase-10-prof-grades`; 720 Python tests passed, 4 skipped); **plan 10-02 complete** (historical backfill CLI `scripts/backfill_historical_sections.py`, tested only against a fake USF client; no live run yet, the operator run is plan 10-08; 742 Python tests passed, 4 skipped); **plan 10-03 complete** (read-only D-04 ranking diff `scripts/report_ranking_diff.py` and join re-measure `scripts/measure_instructor_pairs.py`, tested on seeded SQLite only; no hosted run yet, those are 10-07 and 10-08; 783 Python tests passed, 4 skipped); **plan 10-04 complete** (web `InstructorBreakdown` block in `RankingDetails` per the UI-SPEC, all states and locked copy, synthetic mock-mode breakdowns; 118 frontend tests passed, production build passes; it renders only once plan 10-05 emits `historical_analytics.instructor_breakdown`; held-out 320 px visual checks deferred to 10-09); **plan 10-05 complete** (instructor breakdown embedded in `historical_analytics`, served by the search, section and course APIs; no migration); **plan 10-06 complete** (backfill CLI is now the D-04 rollout instrument: `--dry-run` what-if, `--apply --rebuild-term` atomic under the sweep lock with `--expect-inserted`, `--rollback [--yes]`, `--rebuild-only`, runbook `docs/runbooks/historical-instructor-backfill.md`; tested on SQLite and a fake USF client only, no hosted run yet; 843 Python tests passed, 4 skipped); **plan 10-07 complete (2026-10-01)** (hosted rollout part 1: code-only parity PASS after a 1e-9 float tolerance; four five-term dry runs and 20 USF requests in all, nothing written to the hosted DB; gap fixes: float tolerance, lost-rows diagnostics, anchor repair, all-campus backfill request with allow-list {Tampa, Off-campus - Tampa}, campus gate before normalising, TBA/ARR-only time cells, row quarantine, response save and replay; 1043 Python tests passed, 4 skipped, 1 xfailed). Dry run 4: exit 0, guards all clear, would-insert 8,535, 637 sections change course to instructor_course, course_level_violations 0, `pairs_match_reference` FAIL with small deltas. **D-04 decision: approve (user, 2026-10-01T21:23:24Z, no reason given beyond the word), deltas accepted in writing, allow-list kept**; the approval covers starting plan 10-08 only, NOT the apply, a merge, a push or any live request. Open follow-ups: 58 unmatched graded CRNs and the courses +31 / multi-term +45 deltas unexplained; Spring 2027 live-term campus blind spot (10-GAP-05); the shared-normaliser TBA/ARR change is live-visible (10-GAP-06); WR-03 and NEB 0001 untouched; REQ-PROF-01 not complete. Evidence: `.planning/phases/10-professor-level-grades/10-ROLLOUT-EVIDENCE.md`. **Next: plan 10-08** (merge with green CI, a fresh dry run with empty guard failures, then the operator-run apply with `--expect-inserted`, each step with its own gates).

**Earlier (2026-09-28): live schedule sync, then professor-level grades — planned.** Branch `codex/live-sync-plan` from verified `origin/main` `db8a98a`.
- Investigation (read-only; hosted DB not written): `.planning/research/instructor-grade-feasibility-2026-09-28.md`.
  Production has 0 historical sections/instructors, so `instructor_course` cannot activate at any
  threshold. Live `section_rankings`: 3,422 course / 311 subject / 50 global / 0 instructor_course.
- Stored Spring 2027 schedule already drifted by 2026-09-28: 92 sections gone at USF, 84 instructor
  changes, 7 new CRNs in tracked courses. A single whole-term request returns all 6,663 Tampa rows
  in 9.2 s.
- Plan: `.planning/research/live-sync-and-prof-grades-plan-2026-09-28.md`. Decisions: D-22 (USF
  request policy, narrow D-09 exception) and D-23 (sync first in Phase 9, container host) locked;
  **D-24 (instructor-course scoring retune) pending user approval** at Phase 10 planning.
- Next: `/gsd-discuss-phase 9` → `/gsd-plan-phase 9`. The Phase A migration (`sections.removed_at`)
  needs explicit go-ahead before it is applied to hosted Supabase.
- **Hosting set up (2026-09-29): Render**, free `*.onrender.com` subdomains for the beta (no custom
  domain yet). Workspace "My Workspace" (`tea-datbnkm7bikc73cuhkq0`), no services yet. Payment
  method added; Render GitHub app has access to `aatif101/easy-A`; environment group
  **`easy-a-shared`** holds `DATABASE_URL` (Supabase transaction pooler, port 6543, IPv4). No
  `MIGRATION_DATABASE_URL` on Render — migrations stay manual. Render CLI v2.28.0 installed and
  logged in locally (`render blueprints validate ./render.yaml` available).
- Phase 9 still owns (code, not done): Dockerfile; `render.yaml` Blueprint with `api` (web,
  Starter), `worker` (background worker, Starter, ~512 MB) and `web` (static site, free), all in
  region **ohio** (same AWS region as Supabase us-east-2); API listens on `0.0.0.0:$PORT`;
  `EASY_A_ALLOWED_FRONTEND_ORIGINS` = the static site URL; frontend built with
  `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL` = the API URL. Expected cost ≈ $14/month.

The 2026-09-25 student-experience design work below is still valid input for later UI work.

**Active user-directed work (2026-09-25): student-experience visual review before rebuilding.**
Two interactive alternatives and the selected Student guide specification are available in
`.planning/sketches/001-student-experience/`. Start the static preview with
`python3 -m http.server 4173 --bind 127.0.0.1 --directory .planning/sketches`, then open
`http://127.0.0.1:4173/001-student-experience/`. `index.html` switches A/B, viewport and journey
state; `comparison.html` compares the current app and sketches at identical dimensions.
**The user selected A — Student guide (2026-09-25).** Selection is recorded in the review UI,
README, manifest and specification; B is preserved. Do not ask the user to choose A/B again.
Next: use A for any requested refinement and final specification review; carry out the actual
freshman/sophomore comprehension walkthrough (`REVIEW.md`). No specific screen changes
accompanied the choice. Production implementation remains a later task. Phase 9 remains the
next roadmap phase, not the active task.

Verified design evidence: eight selected real courses, complete current section sets, derived
grade aggregates/provenance only. MAC 1105 confirmed 1,534/3,200 A–F grades; five current sections.
28 browser state/viewport checks passed with no axe violations or console errors, plus keyboard,
filters/search, CRN copy, narrow reflow and 200% text checks. On a 390×844 phone the first course
starts at y=549px versus y=1,086px in the current app. These are prototype checks, not evidence of
student comprehension, production performance, or an update to the full-dataset test baseline.

**Phase history / roadmap context follows.** The former merge/Phase-9 next action below is
superseded for this session by the user's visual-design request.

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

**Phase 08 (MVP1-P5) is complete (5/5 plans, including the 08-05 gap-closure plan).**
`08-04-SUMMARY.md` and `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md`
record a dated, live hosted-Supabase run (2026-09-24) with **Phase 8 verdict: PASS** and **MVP-1
verdict (D-21): PASS**. All ten Gates-table rows PASS: REQ-COVERAGE-03 (validator + API identity
scan, 3,783/3,783/3,783, 0 missing/extra/duplicate/non-Tampa), REQ-GRADES-01 (D-21 inventory 3,122
evidence-backed / 661 listed exceptions, validator honest-coverage 300 == inventory's 300, API
score-source split matches the cache split exactly, 08-03 evidence wording 8/8 tests), REQ-PERF-01
(p95 277.25 ms < 1,500 ms, 50 calls / 5 warmups, single-client loopback HTTP), D-02 invariance
(empty diff vs `origin/main`), D-19 hygiene, and grade provenance (0 deltas vs the dated ledger).
The committed `08-D21-EXCEPTIONS.md` (661 rows, machine-generated) is the honest, complete D-21
end state; no repair action or new grade sourcing was proposed.

**08-05 (gap closure, 2026-09-24) closed the one blocking Phase 8 verification gap**: the code
review (`08-REVIEW.md`) found the D-21 inventory's `rows_at_or_after_term` integrity counter was
reported in the JSON output but never gated `verdicts.integrity` (CR-01, critical). `Inventory.to_dict`
now derives both verdicts from the same mapping it emits under `"integrity"`, so any reported
counter — including `rows_at_or_after_term` — fails the gate the moment it is nonzero, proven end
to end through `main()`. Also fixed: `stale_cache` now derives only from grade rows inside the
scoring evidence window, not every fetched row (WR-01). The Phase 06 suffix-leak guard's raise
condition was kept byte-for-byte unchanged and its ambiguous zero-section case documented as
fail-closed rather than narrowed (WR-02). Both fixed gates were re-run read-only against hosted
Supabase and reproduced the 08-04 baseline exactly (PASS/PASS, 3,122/361/300, all five integrity
counters clean); no hosted data was written. Full suite after 08-05: **374 passed / 3 skipped
Python, 86 passed frontend.** See `08-05-SUMMARY.md` and `08-VERIFICATION-REPORT.md`'s "## Gap
closure re-verification (08-05)" section.

**Phase 08 closeout (2026-09-24):** the browser-viewport check passed human UAT (`08-UAT.md`,
`.planning/WINDOWS.md` entry 8 now fixed); Nyquist validation compliant (`08-VALIDATION.md`);
security 23/23 threats closed (`08-SECURITY.md`); UI audit 19/24 advisory (`08-UI-REVIEW.md` — top
fixes: widen the 160px desktop evidence note, replace `text-[11px]`, consolidate amber tokens);
`08-VERIFICATION.md` status passed; phase marked complete. PR #29 (`codex/phase8-replan`) is open.
`.planning/WINDOWS.md` entry 9 logs a minor repo-wide mypy test-file delta, now 35/10 (down from 36/11 at 08-04 — 08-05's
Task 2 fixed the `test_inventory_tampa_grades.py` portion; `tests/api/test_verify_rankings_pages.py`
stays open, out of 08-05's scope, not a gate blocker).

**Roadmap continuation after the design review:** MVP 1 is verified end to end and Phase 08 is
complete; fetched main now includes the Phase 8 merge (PR #30). Either close the MVP-1 milestone
(`/gsd-audit-milestone`, `/gsd-complete-milestone`) or start Phase 9 —
Hosted Beta (deployment, CI, observability) with `/gsd-discuss-phase 9` / `/gsd-plan-phase 9`.
Deployment host and domain are still not supplied.

## History

Sprint 5 / Phase 1 / Phase 2 results, the 2026-09-09 data-quality run, and dated test baselines
are in `.planning/ARCHIVE.md`. They describe the earlier local beta DB and are not current facts.

## Decisions (load-bearing; full set is PROJECT.md `<decisions>` D-01..D-20)

- D-02: scoring model preserved — **no rewrite without explicit approval**
- D-06: no fabricated data / invented coverage figures; D-07: explicit unavailable states
- D-20: a global-prior fallback (`effective_n = 0`) is **not** course history — never present it as such
- D-04 / D-19: term/CRN/source dedup; never commit raw grade export files
- D-08 / D-09: bounded, narrow USF requests; no scraping/crawling. D-22 is the scoped exception for the live sync worker and the five-term historical backfill
- D-23: live sync ships first inside Phase 9; D-24 (instructor-course scoring retune) is approved (2026-09-30) and implemented in 10-01; it goes live only after the Phase 10 D-04 diff review
- D-10: verify `origin/main` by fetch; do not check out/merge an unverified local `main`
- Note: the D-18 "broader launch coverage is deferred" decision is **superseded** — full Tampa
  breadth is now the MVP-1 goal (see PROJECT.md). Email alerts (D-16) and RMP (D-17, = MVP 2) stay deferred.

- Phase 03.5: cache non-seat ranking fields and hydrate live seats at read time; whole-term cache
  rebuild wrapped into `refresh_data`; cleanup cascade covers `section_rankings`.

## Still open

- ~~**Grade-history coverage for the remaining courses**~~ **RESOLVED under D-21 (locked
  2026-09-23, verified in Phase 8, 2026-09-24)** — the 1,212-section gap from the three-college
  import is now the D-21 honest end state: 661 listed source-limited exceptions (361 `no_rows` +
  300 `non_letter_grade`) with correct subject/global fallback labeling, and 3,122 sections
  evidence-backed. Coverage work is stopped by decision; no further grade sourcing is in scope.
  See `.planning/grade-coverage-import-2026-09-23.md` and
  `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-VERIFICATION-REPORT.md`.

- **Blank grade-cell / suppression semantics (OQ-04)** — the upstream meaning of a blank InfoCenter
  cell is still genuinely unknown. MVP1-P1 (04-02, 2026-09-21) made the parser fail closed on any
  blank canonical count instead of silently coercing to `0`; that is a safety policy, not a
  resolution of OQ-04. Needs a real/sample InfoCenter export.

- ~~**Suffix-course query guard**~~ **RESOLVED (Phase 06)** — the merged `_retain_exact_course_rows`
  guard held across all 33 base/suffix pairs at full scale; `assert_suffix_exact_ingest` confirms no
  L-variant leakage. Guard code unchanged.

- ~~**Search p95 at full scale**~~ **RESOLVED (Phase 07)**: loopback HTTP p95 309.91 ms at 3,783
  sections on hosted Supabase. Deployed-host latency is still to be measured once a host exists.
- ~~**Deployment host and domain**~~ **Host supplied (Render, 2026-09-29) and live (2026-09-30)** on free `*.onrender.com` subdomains; no custom domain yet.

## Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links (MVP 2), a scoring methodology rewrite. All remain candidate
later phases / optional research unless explicitly approved.

## Session Continuity

**Stopped at:** Completed 10-07-PLAN.md (D-04 approved; next 10-08)
Final specification review and student walkthrough remain open. See
`.planning/sketches/001-student-experience/README.md`.
Stale Phase 08 handoff (`HANDOFF.json`, `.continue-here.md`) removed after resumption.
**Resume file:** None

Earlier session: 2026-09-23. Phase 07 execution ran across three sessions. Codex (Windows clone)
completed the 07-01 benchmarks and baseline. A Claude Code WSL session fetched that branch,
committed the measurement script and 07-02 grade batching, then ended mid-measurement. A third
session resumed from the commits and the untracked perf report, batched the per-section rebuild
lookups, tuned the serve path (07-03), and recorded the final evidence.

Last session: 2026-10-01T21:25:41.752Z
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
| Phase 08 P03 | 53min | 2 tasks | 4 files |
| Phase 08 P04 | 15min | 3 tasks | 4 files |
| Phase 08 P05 | ~30min | 3 tasks | 6 files |
| Phase 09 P01 | 2 min | 2 tasks | 4 files |
| Phase 09 P02 | 25 min | 2 tasks | 8 files |
| Phase 09 P03 | 12 min | 2 tasks | 8 files |
| Phase 09 P04 | 25 min | 2 tasks | 9 files |
| Phase 09 P05 | 8 min | 2 tasks | 8 files |
| Phase 09 P06 | 12 min | 2 tasks | 5 files |
| Phase 09 P07 | 4 min | 3 tasks | 12 files |
| Phase 09 P08 | 25min | 3 tasks | 9 files |
| Phase 09 P09 | 15 min | 2 tasks | 8 files |
| Phase 09 P10 | 12 min | 2 tasks | 8 files |
| Phase 09 P11 | 30 min | 2 tasks | 5 files |
| Phase 09 P12 | 20 min | 2 tasks | 7 files |
| Phase 09 P13 | 25 min | 3 tasks | 8 files |
| Phase 09 P14 | 25min | 3 tasks | 3 files |
| Phase 09 P15 | 12min | 3 tasks | 5 files |
| Phase 09 P16 | 3 min | 3 tasks | 6 files |
| Phase 10 P01 | 25 min | 3 tasks | 7 files |
| Phase 10 P02 | 20 min | 2 tasks | 5 files |
| Phase 10 P03 | 12 min | 2 tasks | 6 files |
| Phase 10 P04 | 8 min | 3 tasks | 8 files |
| Phase 10 P05 | 35 min | 3 tasks | 9 files |
| Phase 10 P06 | 10 min | 3 tasks | 6 files |
| Phase 10 P07 | about 15 h wall clock | 3 tasks | 28 files |

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
- [Phase 8]: [Phase 08-03]: Implemented describeEvidence()'s full rule set (course_history, no_letter_grade_history, subject_fallback, no_course_evidence) in Task 1's single commit rather than splitting production code across Task 1/Task 2, since the four scopes form one exhaustive rule table; Task 2's tests pass immediately against that implementation (documented in SUMMARY, no tdd_mode gate violation since workflow.tdd_mode=false).
- [Phase 8]: [Phase 08-03]: Restricted the pre-existing low-confidence 'Based on limited historical data.' InfoTip/paragraph to the course_history evidence scope only, so a fallback/no-evidence row that also has confidence_label=low never shows both the fallback note and a string implying it has limited-but-real course data.
- [Phase 8]: [Phase 08-04]: Reported the repo-wide mypy delta (30/9 -> 36/11 files) as measured, not re-quoted, after tracing it to two 08-01/08-02 test files outside 08-04's scope; logged to WINDOWS.md entry 9 rather than fixed, since this plan's own scoped mypy check (3 production gate scripts) is 0 issues.
- [Phase 8]: [Phase 08-04]: Issued Phase 8 verdict PASS and MVP-1 verdict (D-21) PASS from one frozen hosted-Supabase snapshot (3,783 sections, verified unchanged across all live gates via a before/after five-field comparison): 3,122 evidence-backed, 661 listed D-21 exceptions treated as the honest end state (no repair action, no new grade sourcing), p95 277.25ms.
- [Phase 8]: [Phase 8]: [Phase 08-05]: Closed the CR-01 verification gap by deriving verdicts.integrity/d21_grade_coverage from the same mapping emitted under integrity (not a hardcoded 4-of-5 check), so rows_at_or_after_term can never print PASS while nonzero; proven end to end through main().
- [Phase 8]: [Phase 8]: [Phase 08-05]: Fixed WR-01 by tracking a second running max (evidence_ingested_at_max) over only the rows that pass the scoring query's term_code < before_term filter, so stale_cache reflects only evidence that actually feeds the cached scores; kept WR-02's suffix-guard raise condition byte-for-byte unchanged and documented the ambiguous zero-section case as fail-closed rather than narrowing it.
- [Phase 8]: [Phase 8]: [Phase 08-05]: Re-ran the fixed D-21 inventory and validator read-only against hosted Supabase (202701) and reproduced the 08-04 baseline exactly (PASS/PASS, 3,122/361/300, all integrity counters clean); no hosted data written, 08-D21-EXCEPTIONS.md not regenerated.
- [Phase 09]: 09-01: mypy src stays report-only per D-12; promotion to hard gate flagged for user review (research Open Question 5)
- [Phase 09]: 09-02: migration 0004_sync_removed_at authored and tested offline only; hosted apply stays manual in 09-14 — Carried decision: migrations stay manual; downgrade would discard removal marks
- [Phase 09]: 09-02: removal is a reversible removed_at mark; cache rebuild deletes only section_rankings rows of removed sections — PROJECT.md D-23; history retained
- [Phase 09]: Plan 09-03: sweep jitter is uniform in [1.0, 1.2] (never negative) so no gap breaks the D-22(b) 300 s / 3600 s floors; flagged for user review
- [Phase 09]: Plan 09-03: first sweep of a registration window fires at local midnight, or previous start + 300 s when the previous sweep began under 300 s before midnight
- [Phase 09]: 09-04: undergraduate scope rule lives only in is_undergraduate_number (first four chars digits, below 5000); gate thresholds compared as exact decimals; whole-term request is a separate search_term path so narrow-query validation stays strict
- [Phase 09]: 09-05: partial seat-freshness env overrides are ignored (cadence applies) and warned once; both must be set to override
- [Phase 09]: 09-05: unreadable registration-windows file falls back to legacy 600/1800 s freshness thresholds (never optimistic) instead of failing search
- [Phase 09]: 09-06: /sync-status is a separate endpoint from /coverage and latency observability is structured request logs with no metrics vendor (D-07/D-08, Claude's lean, pending user review)
- [Phase 09]: 09-06: sync-status last_status is limited to succeeded/failed and last_error_kind comes only from SYNC_ERROR_KINDS; error_message is never serialized
- [Phase 09]: 09-07: removed_at filtered on every current-term consumer (coverage, refresh counts, analytics listings, quality); legacy ingest clears removed_at; signals/resolver.py intentionally unfiltered
- [Phase 09]: 09-07: stale_seat_observation judged from Section.last_seen_at with cadence thresholds (7200 s stale outside registration windows)
- [Phase 09]: 09-08: IngestRun has no summary column; sweep counts map to records_seen/inserted/updated/failed and the full summary is the returned SweepOutcome (Open Question 4)
- [Phase 09]: 09-08: existing sections keep course_id; DB sections count as in scope for the gate and removals only when Tampa and undergraduate
- [Phase 09]: 09-09: D-10 freshness copy ('Updated N min ago', 'Seat data may be out of date.') is Claude's lean pending user review; synthetic mode makes no request and never shows an Updated time
- [Phase 09]: D-05 accounting: auto-added courses are derived (active 202701 section, not a configured target, all-Tampa undergraduate), never stored; validator reconciles stored_active == coverage_sum + auto_added_active_sections == rankings_total; D-21 inventory lists their sections as no_rows exceptions
- [Phase 09]: Hosted p95 measured with benchmark --remote-url (plain https origin, no DB, no redirects, trust_env False); operator scripts count active sections only (removed_at IS NULL)
- [Phase 09]: 09-11: CLI cadence floor is seeded from the latest IngestRun start (any status) for --once/--dry-run/loop; no bypass flag; --max-missing-fraction only with --once/--dry-run — PROJECT.md D-22(b); a restart or manual run must never sweep sooner than the tier floor
- [Phase 09]: 09-11: SweepOutcome.extra carries removed/restored/instructor_changes/seat_changes; CLI stdout is JSON-only (non-dict log records wrapped as event=log) — Log-line contract in must_haves; one JSON line per sweep outcome
- [Phase 09]: 09-11: repeated --dry-run is not floor-limited because a dry run records no IngestRun; runbook (09-14) must tell operators not to loop dry runs — Known limitation of the read-only dry-run design (09-08)
- [Phase 09]: 09-12: course auto-add uses a paced (2 s), capped (10/sweep) catalog fetch per new course with a 6 h negative cache; never a schedule-derived stand-in row — A made-up edition could outrank the real one in resolve_course_id; keeps D-05 within D-09/D-20
- [Phase 09]: 09-12: tests/sync autouse fixture gives the default course adder an offline fetch so no sync test reaches USF — Sweeps without an explicit adder use the worker singleton
- [Phase 09]: 09-13: render.yaml keeps per-service DATABASE_URL (sync:false); env group easy-a-shared exists in the dashboard but render blueprints validate rejects fromGroup — Plan rule: switch to fromGroup only if the variant validates; it did not. Operator fills DATABASE_URL once per service at Blueprint creation.
- [Phase 09]: 09-13: tzdata via apt in the image, no PyPI tzdata; runbook documents that --dry-run is not rate-limited because it records no IngestRun — Avoids a package-legitimacy checkpoint; dry-run behaviour verified in sweep.py.
- [Phase 09]: 09-14: Earliest Blueprint creation is 2026-09-30T06:15:46Z (dry-run start plus 60-minute floor); phase 9 code merged to main via PR #33 (5def356) after two CI-only test fixes
- [Phase 09]: 09-15: 30 s per-sweep duration criterion recorded as an unresolved GAP (50.69 s, 37.166 s), not loosened; operator decision pending
- [Phase 09]: 09-15: sweep-line next_start_at is the 60 min floor; jitter is on the following sleeping line (real gaps 66-69 min)
- [Phase 09]: 09-16: gate override maps one fraction onto every size rule; above 0.10 row floor = 1 - X (exact decimal), absent-subject limit = X, zero_rows never overridable; None (no flag, worker loop) keeps the 0.10/0.90/0.02/2 defaults
- [Phase 10]: 10-01: instructor_prior_strength (30) applies to grade favorability only; withdrawal prior stays 60 at every level — Literal reading of PROJECT.md D-24; keeps the D-02 amendment minimal
- [Phase 10]: 10-01: Laboratory rule lives in common/section_types.py with exact normalized match on 'laboratory'; vocabulary confirmed against hosted data in 10-07 — Combined and unknown types stay included; single home for the D-13 rule
- [Phase 10]: 10-02: backfill writes via Core executemany plus one id read, change-only, never seat snapshots or removed_at; a failed guard never writes in --apply — ORM unit of work issued one INSERT per row (81 vs 21 statements for 40 vs 10 rows); D-07 idempotence and D-05 isolation
- [Phase 10]: 10-03: ranking diff counts a mapped_instructor_section_count-only change as informational, never a gate failure; pair effective_n is min(sum A-F, sum total) with recency off — The backfill raises the mapped count on course-level rows without moving any score; the pair definition matches the 2026-09-28 research
- [Phase 10]: 10-04: instructor block gated on course_history scope plus non-null breakdown; Staff/ambiguous/unknown sections ignore is_current (no pin, no highlight, no score claim); thresholds come from the API object — D-11, D-13, D-20; UI-SPEC copy locked, thresholds never hard-coded in the frontend
- [Phase 10]: Plan 10-05: instructor breakdown is embedded in historical_analytics JSON (no migration), collapse cutoff 15, rows keyed by exact name_raw so the pinned row and instructor_course score share one stats helper
- [Phase 10]: 10-06: undo modes (--rollback --yes, --rebuild-only) report the applied diff but never gate on it; only --apply gates on the course-level invariant and --expect-inserted — Blocking an undo because a diff looks odd is worse than the odd diff
- [Phase 10]: 10-06: rollback preview performs the real deletion and cache rebuild inside a rolled-back transaction under the sweep lock; eligibility needs backfill-only instructor rows, no seat snapshot, no syllabus link, historical terms only — Preview and commit cannot differ; T-10-20
- [Phase 10]: 10-07: D-04 approved by the operator with the pairs_match_reference deltas accepted in writing (n>=1 -63, n>=60 -15, n>=30 -25, n>=15 -44, named -127 = 58 unmatched + 69 non-allow-listed campus CRNs; courses +31 and multi-term +45 unexplained); allow-list {Tampa, Off-campus - Tampa} kept — User chose approve, no written reason given. Covers starting 10-08 only; does not authorise apply, merge, push or live requests. --expect-inserted 8535 valid only for a rerun with empty guard failures
- [Phase 10]: 10-07: gap fixes found by live dry runs, each user-decided: ranking-diff float tolerance 1e-9, lost-rows diagnostics, unterminated-anchor repair, all-campus backfill request with allow-list, campus gate before normalising, TBA/ARR-only time cells (shared normaliser), row quarantine guard, response save and replay — Dry runs 1 to 3 failed or tripped guards on real data (20 USF requests in total, nothing written); live sync request stays campus=T. Open: 58 unmatched CRNs, courses/multi-term deltas, Spring 2027 campus blind spot (10-GAP-05), TBA TBA live-visible change (10-GAP-06), WR-03 and NEB 0001 untouched
