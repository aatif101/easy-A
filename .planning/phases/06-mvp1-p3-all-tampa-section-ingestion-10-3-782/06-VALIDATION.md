---
phase: "6"
slug: "mvp1-p3-all-tampa-section-ingestion-10-3-782"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml `[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/refresh/ tests/catalog/ tests/schedule/ -q` |
| **Full suite command** | `uv run pytest -q` (SQLite default; add `EASY_A_TEST_POSTGRES_URL` for the PostgreSQL-specific suite) |
| **Estimated runtime** | ~30–60 seconds (unit tests); the live full-scale ingestion (06-02 Task 3) is a separate multi-minute operational run |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/refresh/ tests/catalog/ tests/schedule/ -q`
- **After every plan wave:** Run `uv run pytest -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite green, plus a live `scripts/check_data_quality.py --term 202701 --json` run against hosted Supabase reporting 0 errors and `scripts/validate_tampa_ingest.py --term 202701` passing all three checks
- **Max feedback latency:** ~60 seconds for unit tests

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | REQ-COVERAGE-03 | T-06-02 / T-06-06 | Suffix + campus guards hold end-to-end for CHM; malformed config rows rejected | unit + live | `uv run pytest tests/refresh/test_generate_targets.py tests/refresh/test_targets.py -q` ; `uv run python scripts/refresh_course_coverage.py --term 202701 --targets config/course_targets.toml --subject CHM` | ❌ W0 (test_generate_targets.py) | ⬜ pending |
| 06-01-02 | 01 | 1 | REQ-COVERAGE-03 | T-06-02 | Suffix guard generalizes beyond CHM; production guard untouched | unit | `uv run pytest tests/refresh/test_coverage_suffix_guard.py -q` | ✅ (extended) | ⬜ pending |
| 06-02-01 | 02 | 2 | REQ-COVERAGE-03 | T-06-04 / T-06-01 | Per-subject transaction isolation + pacing + resume; no cross-subject transaction | unit | `uv run pytest tests/refresh/test_refresh_all_tampa.py -q` | ❌ W0 (test_refresh_all_tampa.py) | ⬜ pending |
| 06-02-02 | 02 | 2 | REQ-COVERAGE-03 | T-06-01 | Blocking-human authorization before live volume | checkpoint | (blocking-human gate) | — | ⬜ pending |
| 06-02-03 | 02 | 2 | REQ-COVERAGE-03 | T-06-01 / T-06-04 | Full run completes with 0 failed subjects, 0 quality errors | live/integration | `uv run python scripts/refresh_all_tampa.py --term 202701 --targets config/course_targets.toml --pace-seconds 2` ; `scripts/check_data_quality.py --term 202701 --json` | ✅ scripts | ⬜ pending |
| 06-03-01 | 03 | 3 | REQ-COVERAGE-03 | T-06-02 / T-06-07 | Read-only validator; derive_suffix_pairs = 33 | unit | `uv run pytest tests/refresh/test_validate_tampa_ingest.py -q` | ❌ W0 (test_validate_tampa_ingest.py) | ⬜ pending |
| 06-03-02 | 03 | 3 | REQ-COVERAGE-03 | T-06-02 / T-06-08 | 33 suffix base courses exact-only; 0 non-Tampa; counts agree | live/integration | `uv run python scripts/validate_tampa_ingest.py --term 202701 --targets config/course_targets.toml` | ✅ script | ⬜ pending |
| 06-03-03 | 03 | 3 | REQ-COVERAGE-03 | T-06-07 / T-06-03 | Honest coverage (D-20) at scale; no export/snapshot committed | live/integration | `uv run python scripts/validate_tampa_ingest.py --term 202701 ...` ; `git ls-files -- '*.xlsx' '*.xls'` | ✅ script | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/refresh/test_generate_targets.py` — stubs for REQ-COVERAGE-03 (target-list generator validation)
- [ ] `tests/refresh/test_refresh_all_tampa.py` — stubs for REQ-COVERAGE-03 (per-subject orchestrator: invocation, pacing, resume, failure-continue)
- [ ] `tests/refresh/test_validate_tampa_ingest.py` — stubs for REQ-COVERAGE-03 (suffix-exact / reconciliation / honest-coverage assertions)
- Framework install: none — pytest is already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Authorize the ~2,800-request live USF run | REQ-COVERAGE-03 | Live external volume against a third party + writes to the only live DB — a human must decide go/no-go and confirm courses.csv freshness | 06-02 Task 2 blocking-human checkpoint: confirm freshness + pacing, type "approved" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s (unit tests)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
