---
gsd_state_version: "1.0"
current_plan: Not started
status: ready_to_plan
stopped_at: Phase 08 complete, ready to plan Phase 9
last_updated: "2026-09-24T20:24:06.801Z"
state_head: 7db0ddb3dea293295f31b2bceceab52439d74181
progress:
  total_phases: 10
  completed_phases: 7
  total_plans: 20
  completed_plans: 20
  percent: 70
last_activity: 2026-09-24
current_phase: 9
current_phase_name: Hosted Beta — Deployment, CI, Observability
last_activity_desc: Phase 08 (MVP1-P5) complete (5/5 plans) — 08-05 gap closure fixed CR-01 (D-21 integrity gate) and WR-01 (stale_cache window), documented WR-02, and re-confirmed Phase 8 / MVP-1 (D-21) verdicts PASS live against hosted Supabase (2026-09-24)
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

Current Plan: Not started
Total Plans in Phase: 0 (Phase 9 not yet planned)

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

**Do next:** MVP 1 is verified end to end and Phase 08 is complete. Merge PR #29, then either
close the MVP-1 milestone (`/gsd-audit-milestone`, `/gsd-complete-milestone`) or start Phase 9 —
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
- D-08 / D-09: bounded, narrow USF requests; no scraping/crawling
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
- **Deployment host and domain** not yet supplied.

## Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links (MVP 2), a scoring methodology rewrite. All remain candidate
later phases / optional research unless explicitly approved.

## Session Continuity

**Stopped at:** Phase 08 complete, ready to plan Phase 9
Stale Phase 08 handoff (`HANDOFF.json`, `.continue-here.md`) removed after resumption.
**Resume file:** None

Earlier session: 2026-09-23. Phase 07 execution ran across three sessions. Codex (Windows clone)
completed the 07-01 benchmarks and baseline. A Claude Code WSL session fetched that branch,
committed the measurement script and 07-02 grade batching, then ended mid-measurement. A third
session resumed from the commits and the untracked perf report, batched the per-section rebuild
lookups, tuned the serve path (07-03), and recorded the final evidence.

Last session: 2026-09-24T19:28:54.090Z
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
