---
phase: "08"
slug: "mvp1-p5-end-to-end-mvp-1-verification"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-23"
---

# Phase 8 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest and Vitest |
| Config | `pyproject.toml`, `web/vite.config.ts` |
| Quick run | `uv run pytest tests/refresh/test_validate_tampa_ingest.py tests/api/test_benchmark_rankings_search.py -q` |
| Full run | `uv run pytest -q`; `npm --prefix web test` |
| Feedback latency | Record measured duration during execution |

## Sampling Rate

- After a source change, run its focused test and record the result.
- After each wave, run the relevant Python or frontend suite.
- Before Phase 8 sign-off, run the full suites and live hosted gates against one dated term snapshot.
- A PostgreSQL integration skip is reported as a skip, not as a pass.

## Per-Task Verification Map

| Requirement | Behavior | Automated command | Existing? |
|---|---|---|---|
| REQ-COVERAGE-03 | Tampa target/cache count and suffix ownership | `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q` | Yes |
| REQ-COVERAGE-03 | All stored term/CRN identities appear exactly once over API pages | Focused new test and live HTTP page scan | Wave 0 gap |
| REQ-GRADES-01 | Every represented course has attributed source history and nonzero effective N for its sections | Focused new inventory test and live read-only inventory | Wave 0 gap |
| REQ-GRADES-01 | Global and subject fallback presentation is honest | Focused frontend component tests | Wave 0 gap |
| REQ-PERF-01 | Full-scale search p95 below 1.5 s | `uv run python scripts/benchmark_rankings_search.py --live --http-base-url http://127.0.0.1:8000 --term 202701 --iterations 50` | Yes |

## Wave 0 Requirements

- [ ] Add focused tests for grade inventory and complete API page identity scan.
- [ ] Add focused frontend tests for global and subject fallback presentation.

## Manual-Only Verifications

| Behavior | Why manual | Instructions |
|---|---|---|
| Browser display at desktop and mobile sizes | Existing component tests cannot prove layout | Inspect representative course, subject, and global rows; record screenshots or observations without claiming a deployed-host latency. |
| Hosted Supabase evidence | Credentials and service availability are environment-specific | Run existing live commands, record UTC time, denominators, and explicit PASS/FAIL/NOT MEASURED verdicts. |

## Validation Sign-Off

- [ ] All new tasks have focused tests or a documented live gate.
- [ ] Live result distinguishes Phase 8 checks from literal MVP 1 completion.
- [ ] Full suite, quality, grade inventory, coverage, and p95 results recorded.
- [ ] `nyquist_compliant: true` only after required tests and live gates pass.

**Approval:** pending
