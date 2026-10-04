---
phase: 06-mvp1-p3-all-tampa-section-ingestion-10-3-782
plan: 02
subsystem: data-pipeline
tags: [ingestion, orchestration, resumable, pacing, supabase, performance]

# Dependency graph
requires:
  - phase: 06-01
    provides: full git-tracked config/course_targets.toml (1,402 courses) + proven per-subject ingestion path (CHM)
provides:
  - scripts/refresh_all_tampa.py — resumable, paced per-subject orchestrator (own process/transaction per subject)
  - scripts/refresh_subject_fast.py — bulk per-subject ingest reusing guarded refresh_targets, whole-term quality check deferred
  - docs/runbooks/all-tampa-ingestion.md — operator runbook with dated run-log
  - Full Tampa Spring 2027 universe ingested into hosted Supabase — 212 subjects / 1,402 courses / 3,783 sections, 0 non-Tampa, 0 quality errors
affects: [06-03-validation]

# Actuals
actuals:
  subjects: 212
  courses: 1402
  sections: 3783
  non_tampa_sections: 0
  quality_errors: 0
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-subject process isolation: orchestrator shells out once per subject so each subject is its own OS process + DB transaction; a failure's blast radius is one subject (1-33 courses), never the whole run."
    - "Resumable progress file records completed subjects; a re-run skips them (idempotent upserts make re-fetch safe even if the progress file is lost)."
    - "Per-subject wall-clock ceiling (--subject-timeout): a stalled subprocess is killed + recorded failed so a hang never freezes the sequential run."
    - "Deferred derived work: the O(n^2) per-subject whole-term quality scan is replaced by one whole-term quality check after all subjects (scripts/refresh_subject_fast.py), turning O(n^2) -> O(n)."
---

# 06-02 — All-Tampa batch ingestion (10 → 3,783 sections)

## Outcome

The full USF Tampa Spring 2027 universe is ingested into hosted Supabase:
**212 subjects · 1,402 courses · 3,783 sections · 0 non-Tampa rows · 0 quality errors.**
`grade_distributions` remains 179 (only the 10 pilot courses carry sourced Fall-2024
history; every newly ingested course is the honest `effective_n=0` / `score_source=global`
state per D-20 — never presented as course history).

## Tasks

- **Task 1 (auto, tdd):** built `scripts/refresh_all_tampa.py` — resumable, paced, per-subject
  orchestrator (own process/transaction per subject; `--pace-seconds` default 2s; progress-file
  resume; failed subject recorded and skipped, run continues). Unit-tested with subprocess + sleep
  mocked (no network). Wrote `docs/runbooks/all-tampa-ingestion.md`. `coverage.py` / `target_cli.py`
  untouched.
- **Task 2 (checkpoint: blocking-human):** operator authorized the full-scale live run at
  `--pace-seconds 2`, accepting the dated 2026-09-20 `courses.csv` snapshot.
- **Task 3 (auto):** executed the full-scale ingestion to completion — 0 failed subjects, 0 quality
  errors; dated counts recorded in the runbook run-log.

## Deviations (2, both operational, discovered during the live run)

The full run initially projected to ~20–25h and stalled on subject `CLT`. A DB-latency
investigation (requested by the operator) found the DB itself healthy (~64ms round-trips, us-east-2
transaction pooler) but two structural problems, fixed at the orchestration layer only —
`coverage.py` and `target_cli.py` remain at **zero diff** (guards preserved):

1. **`--subject-timeout` (commit `5f6f54b`)** — a subject subprocess with no statement/DB timeout
   could hang indefinitely (observed on `CLT`, ~96 min), freezing the sequential run. Added a
   per-subject wall-clock ceiling (default 900s; run used 600s): on timeout the subprocess is killed
   and the subject recorded as failed so the run continues and retries on resume.

2. **Defer per-subject quality scan (commit `cbfc070`)** — `run_quality_checks` (via
   `refresh_course_coverage.py` → `target_cli.py:37`) scans and analyzes the **whole term on every
   subject** (`checks.py` filters only by `term_id`; `_check_analytics` runs per-course analytics
   over all term courses). Across 212 subjects that re-analyzes everything ingested so far — **O(n²)**.
   Fix: new `scripts/refresh_subject_fast.py` reuses the same guarded `refresh_targets` (campus +
   suffix guards, per-course scoped ranking refresh) but omits the per-subject quality check;
   `refresh_all_tampa.py` runs **one** whole-term quality check at the end (`--skip-final-quality`
   to opt out). Validated: `CLT` (96-min freeze) then ingested in seconds. Remaining run finished in
   ~1.5h.

Subject `SOW` failed once on a transient `ScheduleParseError` and succeeded on resume (13 courses /
15 sections) — the intended resume-after-transient-failure path.

**Deferred:** the deeper analytics query optimization (batch/hoist the per-course aggregate that
still makes the single final quality pass and search slow) is deferred to **Phase 7 (MVP1-P4)**, the
search-performance phase, per operator decision.

## Verification

- `uv run pytest tests/refresh/test_refresh_all_tampa.py -q` — 11 passed (orchestrator: invocation,
  pacing, progress/resume, failure-continue, subject-timeout, deferred-quality).
- Full run: `Subjects total: 212 · Failed: 0 · Final quality errors: 0`.
- DB (term 202701): 3,783 sections, 1,402 courses, **0 non-Tampa rows**.
- `git diff --exit-code -- src/easy_a/refresh/coverage.py src/easy_a/refresh/target_cli.py` — clean.
- No `courses.csv` / `*.xlsx` / `*.xls` committed.

## Artifacts produced

- `scripts/refresh_all_tampa.py` (`--term`, `--targets`, `--pace-seconds`, `--progress`,
  `--subject-timeout`, `--subjects`, `--skip-final-quality`; `run_final_quality_check`)
- `scripts/refresh_subject_fast.py`
- `tests/refresh/test_refresh_all_tampa.py`
- `docs/runbooks/all-tampa-ingestion.md` (with dated run-log)

## Follow-ups

- **Phase 7 (MVP1-P4):** optimize `get_course_historical_outcome_stats` (compute global/subject
  aggregate once, batch per-course queries) — speeds up both the whole-term quality/ranking rebuild
  and search p95.
- **Separate future effort:** sourced grade history for the newly ingested courses (bounded
  per-course SGDIS imports, mirroring Phase 05) — not in MVP1-P3 scope.
