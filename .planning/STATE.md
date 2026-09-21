---
gsd_state_version: "1.0"
status: planning
last_updated: "2026-09-21T03:36:01.056Z"
state_head: abb8f5d5db9e8a9043ddab59687c19f5f0055c93
progress:
  total_phases: 10
  completed_phases: 3
  total_plans: 7
  completed_plans: 0
  percent: 0
last_activity: 2026-09-20
current_phase_name: MVP1-P1 — Grade→course attribution fix
current_phase: 04
stopped_at: MVP 1 milestone set up; Phase 4 ready to plan
last_activity_desc: MVP 1 milestone set up; Phase 4 (grade attribution) ready to plan
---

# Project State

`STATE.md` is the single source of **current, volatile facts** (counts, SHA, next action). Durable
rules live in `PROJECT.md` `<decisions>`; the phase sequence lives in `ROADMAP.md`; dated history
lives in `ARCHIVE.md`.

## Current state — as of 2026-09-20

**Repo / git**

- `origin/main` = `a70a85346796d886f5f04741b5fd2330b660e2cc` (verify by fetch before planning).
  PR #18 (Tampa guard) and PR #19 (Supabase wiring) are **merged**. Working branch:
  `dev1/tampa-coverage-pilot` (ahead of `origin/main`, unmerged).

**Database (hosted Supabase — the only live DB now; the old local beta DB is history in `ARCHIVE.md`)**

- Term 202701: **132 sections, all campus=Tampa, across 10 courses** — ACG 2021 (17), ACG 2071
  (15), AMH 2020 (19), ANT 2000 (5), BSC 1005 (2), ECO 2013 (3), ENC 1101 (41), MAC 1105 (5),
  MAC 2311 (15), PSY 2012 (10). 132 seat snapshots. **0 non-Tampa rows.**
- **0 `GradeDistribution` rows and 0 syllabi.** Every easiness score is therefore the
  `effective_n = 0` global fallback — **no course has grade-evidence-backed easiness** (quality
  CLI: 0 errors, 132 low-confidence warnings, 132 no-history info).
- `config/course_targets.toml` lists only 5 courses while the DB has 10 — config and stored data
  are out of sync (reconcile during MVP1-P3).

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

## Next action

Docs declutter is done (this update). Next build steps, in order (see ROADMAP MVP1-P1..P5):

1. **MVP1-P1** — fix grade→course attribution (`GradeDistribution.course_id` is hard-coded `None`
   at `src/easy_a/grades/ingest.py:140`); prove easiness-from-grades end-to-end on a sample export.
2. **MVP1-P2** — grade data sourcing (Codex-owned): source USF InfoCenter grade XLSX for Tampa
   courses and load into Supabase. Depends on P1, or the loaded grades will not attribute.
3. **MVP1-P3** — all-Tampa section ingestion (10 → ~3,782); resolve the CHM 2045/2045L suffix-guard
   blocker (33 base courses have suffix variants); reconcile config vs stored data.
4. **MVP1-P4** — full-scale cache build + tune search to p95 < ~1.5s on Supabase.
5. **MVP1-P5** — end-to-end MVP-1 verification.

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

- **Grade→course attribution broken for MVP** — `course_id` set to `None` at ingest
  (`src/easy_a/grades/ingest.py:140`); imported historical grades won't attach to current-term
  sections until fixed (MVP1-P1).
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every blank
  cell to `0` with no suppression path. Needs a real/sample InfoCenter export.
- **Suffix-course query guard** — USF's CHM 2045 query also returns CHM 2045L; the exact-course
  guard rejects it. 33 base courses have suffix variants; resolve before scaling (do not weaken it).
- **Search p95 at full scale** — ~2.40s on Supabase at 3,782 sections; must reach < ~1.5s for MVP 1.
- **Deployment host and domain** not yet supplied.

## Deferred — do not reintroduce as current scope

Email seat alerts, verified RMP links (MVP 2), a scoring methodology rewrite. All remain candidate
later phases / optional research unless explicitly approved.

## Session Continuity

Last session: 2026-09-20. Stopped at: Phase 03.5 delivered (perf goal deferred); docs decluttered;
MVP 1 scoped and its roadmap encoded.
Resume file: `.claude/plans/typed-gliding-cocke.md` (docs declutter + MVP-1 roadmap plan).
Next action: begin MVP1-P1 — fix grade→course attribution.

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 03.5 P01 | 15min | 2 tasks | 7 files |
| Phase 03.5 P02 | 7min | 2 tasks | 5 files |
| Phase 03.5 P03 | 8min | 3 tasks | 8 files |
| Phase 03.5 P04 | 20min | 2 tasks | 2 files |
