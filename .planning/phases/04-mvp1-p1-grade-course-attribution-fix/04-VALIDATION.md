---
phase: "04"
slug: "mvp1-p1-grade-course-attribution-fix"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-20"
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`) |
| **Quick run command** | `uv run pytest -q tests/grades tests/test_grade_course_attribution.py tests/refresh/test_rankings_cache_refresh.py` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~6 seconds locally (research baseline: 253 passed, 3 skipped in 5.56s) |

---

## Sampling Rate

- **After every task commit:** Run the task's narrow pytest target plus `uv run ruff check` on changed Python paths.
- **After every plan wave:** Run `uv run pytest -q tests/grades tests/analytics tests/test_grade_course_attribution.py tests/rankings/test_cache_parity.py tests/refresh/test_rankings_cache_refresh.py`.
- **Before `/gsd:verify-work`:** Full pytest, ruff, strict mypy, and the configured PostgreSQL path must be green; verify that Git tracks no raw `.xlsx` or `.xls` exports.
- **Max feedback latency:** 15 seconds for the local automated suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | REQ-GRADES-01 / D-20 | T-04-01 | Generated XLSX proves direct attribution, `effective_n > 0`, honest no-history fallback, and cache refresh | vertical integration | `uv run pytest -q tests/test_grade_course_attribution.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | REQ-GRADES-01 | T-04-02 / T-04-03 | Resolve every canonical course key before mutation; repair null attribution while preserving term/CRN/source identity and provenance | integration | `uv run pytest -q tests/grades/test_ingest.py -x` | ✅ | ⬜ pending |
| 04-02-01 | 02 | 2 | REQ-GRADES-01 / D-07 | T-04-07 | Reject blank canonical counts; accept explicit integer zero | unit | `uv run pytest -q tests/grades/test_parser.py -x` | ✅ | ⬜ pending |
| 04-02-02 | 02 | 2 | REQ-GRADES-01 / D-06 | T-04-13 | Surface any stored null-attribution grade row as a quality finding | unit | `uv run pytest -q tests/quality/test_checks.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_grade_course_attribution.py` — generated-XLSX vertical proof that does not rely on a historical `Section`, then rebuilds the 202701 rankings cache and checks with-history/no-history controls.
- [ ] Extend `tests/grades/test_ingest.py` with canonical attribution, same-key null-row backfill, missing-course atomicity, deduplication, and provenance assertions.
- [ ] Replace the blank-as-zero expectation in `tests/grades/test_parser.py` with fail-closed blank handling while retaining an explicit-zero success case.
- [ ] Extend `tests/quality/test_checks.py` if the plan includes an `unattributed_grade_row` finding.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PostgreSQL/Supabase dialect path | REQ-GRADES-01 | `EASY_A_TEST_POSTGRES_URL` and `DATABASE_URL` were unavailable during research | In an authorized environment, set `EASY_A_TEST_POSTGRES_URL`, run the planned PostgreSQL integration target, and require a zero exit code with no unexpected skip. |
| Upstream meaning of blank InfoCenter grade cells | REQ-GRADES-01 / D-06 / D-07 | No authoritative approved export or source documentation establishes whether blank means zero, unavailable, or suppressed | Phase 04 must reject such rows. In Phase 05, inspect one approved representative export and record source-backed semantics before accepting blanks. |

---

## Validation Sign-Off

### Strategy completeness

- [x] Every final task is mapped to its actual plan, wave, behavior, and automated target
- [x] All tasks have `<automated>` verification or an explicit Wave 0 dependency
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] No watch-mode flags
- [x] Feedback-latency target is under 15 seconds
- [x] `nyquist_compliant: true` is set in frontmatter

### Execution readiness

- [ ] Wave 0 test code has been implemented
- [ ] All task and phase verification commands have passed during execution

**Approval:** validation strategy is Nyquist-complete; Wave 0 implementation and execution results remain pending.
