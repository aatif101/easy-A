---
phase: 07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
plan: 02
subsystem: analytics, rankings-cache, quality
tags: [batching, n+1, parity, supabase]

requires:
  - phase: 07-01
    provides: live baseline and measure_term_build.py
provides:
  - get_term_section_historical_analytics (whole-term grade evidence read once)
  - get_current_instructor_states, resolve_term_section_signals, _gened_attributes_by_course_id
  - whole-term cache rebuild in seconds and quality pass in seconds on hosted Supabase
affects: [07-03, 08]

key-files:
  modified:
    - src/easy_a/analytics/queries.py
    - src/easy_a/common/instructors.py
    - src/easy_a/rankings/cache.py
    - src/easy_a/rankings/service.py
    - src/easy_a/signals/resolver.py
    - src/easy_a/quality/checks.py
    - tests/analytics/test_queries.py
    - tests/rankings/test_cache_parity.py
    - tests/quality/test_checks.py
    - tests/common/test_instructors.py

key-decisions:
  - "Batch inputs feed the existing aggregate_grade_observations, fallback and compute functions. No weighted totals are derived by subtraction (D-02)."
  - "Per-section instructor, GenEd and syllabus reads were batched as well, because after grade batching they dominated (the plan's 'optimize only that measured path' clause). A shared _resolve_signals keeps single-section and whole-term signal precedence identical."
  - "refreshed_at comes from one SELECT now() in the caller's transaction, which equals the per-row func.now() value on PostgreSQL. This lets the ORM send UPDATEs as one executemany."

requirements-completed: []

duration: ~1h (across two sessions)
completed: 2026-09-23
status: complete
---

# Phase 7 Plan 2: Batched whole-term evidence

**Whole-term cache rebuild on hosted Supabase: 3,783 rows in 4.77 s with 15 statements. The
pre-batching run lost its connection after about 30 minutes. The whole-term quality pass takes
2.45 s with 12 statements, down from about 35 minutes, with identical findings. Cached rankings
remain byte-for-byte equal to on-demand rankings.**

## Accomplishments

- `get_term_section_historical_analytics` reads pre-term grade evidence and instructor mappings
  once. It then derives course, course-excluding subject, global and instructor-course inputs
  for every course. Output equals the per-course function, including cross-attributed rows.
- The cache rebuild batches instructor states, GenEd attributes, current and historical syllabi,
  and updates. The quality instructor check uses batched states.
- New tests:
  - Cache/on-demand parity across syllabus, note, same-instructor and same-course history,
    GenEd and ambiguous-instructor branches.
  - Batched instructor states equal single-section states across all state kinds.
  - Rebuild and quality statement counts do not grow with section count.

## Task Commits

1. Batch historical evidence plus cache and quality consumers: `77f510f`
2. Batch per-section instructor, GenEd and signal reads: `8855633`

## Deviations

- **[Rule: measured dominant path]** Per-section batching (`8855633`) goes beyond the grade
  batching named in the plan text. The plan explicitly allows it when those lookups become
  dominant. A one-course profile showed about 6 round trips per section at about 78 ms each.
- D-02, D-03 and D-20 hold: no scoring change, seats are not cached or scored, and global
  fallbacks keep `effective_n=0`. The live split (132 course / 563 subject / 3,088 global
  sections) is unchanged.

---
*Completed: 2026-09-23*
