---
phase: 07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s
plan: 01
subsystem: performance
tags: [benchmark, live-baseline, supabase, http, explain, read-only]

requires:
  - phase: 06-03
    provides: full 202701 Tampa term (3,783 sections) and section_rankings in hosted Supabase
provides:
  - scripts/benchmark_rankings_search.py --live (in-process diagnostic) and --live --http-base-url (loopback HTTP gate)
  - scripts/measure_term_build.py (rolled-back whole-term rebuild + read-only quality timing)
  - dated live baseline in 07-PERF-REPORT.md
affects: [07-02, 07-03]

key-files:
  created:
    - scripts/measure_term_build.py
    - tests/api/test_benchmark_rankings_search.py
    - .planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md
  modified:
    - scripts/benchmark_rankings_search.py

key-decisions:
  - "The environment label comes from the resolved engine URL (dialect, host class, pooler), never the CLI URL. Credentials, hosts and failure details are redacted."
  - "The REQ-PERF-01 gate is loopback HTTP p95 (request + body + JSON validation). Direct route timing is a diagnostic only."
  - "The live baseline replaces the synthetic 2.40 s figure as evidence. The old number is not reused."

requirements-completed: []

duration: split across two sessions (Codex on Windows, then Claude Code in WSL)
completed: 2026-09-23
status: complete
---

# Phase 7 Plan 1: Live search and build baseline

**The read-only live and loopback-HTTP benchmarks give the first real full-scale baseline:
3,783 sections, HTTP p95 1,110 ms (Windows) / 1,202 ms (WSL), direct route p95 about 232 ms.
The ~900 ms gap and a 175 ms page plan are the diagnosed bottlenecks. The pre-batching
whole-term cache rebuild did not finish: the pooler dropped the connection after about 30 minutes.**

## Accomplishments

- `benchmark_rankings_search.py --live` times the unchanged `search_rankings` route in-process
  with no seed and no writes. `--http-base-url` issues real GETs to a loopback-only API with the
  same deterministic 50-call query mix after 5 warmups. It checks the stored-term total and
  every response. Non-loopback URLs are rejected.
- `measure_term_build.py` times `refresh_section_rankings` (flush, then rollback) and
  `run_quality_checks`, printing only counts, timings and a sanitized environment label.
- Baseline recorded in `07-PERF-REPORT.md`: live counts (3,783 sections and cache rows,
  1,401 represented courses, 212 subjects, 179 grade rows, 0 non-Tampa), a cache evidence split
  that corrected STATE.md (104 courses use subject fallback, not global), and EXPLAIN for the
  representative count and page queries.

## Task Commits

1. Live and loopback benchmarks: `2336d69`. Failure-detail redaction: `4985b80`
2. Whole-term build timing script: `e608eaa`
3. Baseline evidence: `07-PERF-REPORT.md` (docs commit)

## Deviations / Issues

- **Execution was interrupted and resumed.** The plan started in a Codex session in the Windows
  clone (`C:\Users\smati\VS Code Projects\easy-A`). A later Claude Code session in WSL
  fetched that branch and continued. That session ended while the post-batch build measurement
  was still running, and WSL's `/tmp` was cleared, so its partial output was lost. A third
  session resumed and completed the phase. No commits were lost.
- The pre-batching rebuild baseline has no completion time. Hosted Supabase closed the
  connection after about 30 minutes (course 468 of 1,401). This is recorded as a failure, not
  extrapolated.
- Baseline-time verification: benchmark and search-SQL tests 25 passed; full suite 305 passed,
  3 skipped.

---
*Completed: 2026-09-23*
