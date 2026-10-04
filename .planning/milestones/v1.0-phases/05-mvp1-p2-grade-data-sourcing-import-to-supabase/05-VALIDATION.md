---
phase: "05"
slug: "mvp1-p2-grade-data-sourcing-import-to-supabase"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (`testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/grades tests/analytics tests/test_grade_course_attribution.py tests/test_grade_schedule_integration.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/grades tests/analytics tests/test_grade_course_attribution.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green, plus a real run of `scripts/check_data_quality.py --term 202701 --json` against the actual post-import hosted Supabase state
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | REQ-GRADES-01 | — | N/A | unit | `{command}` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*(Filled by validate-phase after plans exist; existing suites at `tests/grades/`, `tests/analytics/`, `tests/test_grade_course_attribution.py`, `tests/test_grade_schedule_integration.py` cover every code path this phase touches — see RESEARCH.md Validation Architecture.)*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.* No new framework install and no new test scaffolding is required for the code paths this phase touches. The phase's actual gate is real-data validation, not new test coverage. If a real InfoCenter export's blank-cell behavior (OQ-04) is encoded as a fixture, the one new unit test belongs in `tests/grades/test_ingest.py` or a new `tests/grades/test_parser_real_export_shape.py`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Per-course analytics match the source aggregate (raw `total_grade_count`, not the smoothed score) | REQ-GRADES-01 | Depends on a real, externally-sourced export that does not exist in-repo (Codex-owned; raw files never committed) | After import + `--term 202701` cache-only rebuild, run `scripts/analyze_course.py` per imported course and compare raw counts to the source workbook total |
| Imported courses flip from `effective_n=0`/`score_source=global` to `effective_n>0`/`score_source=course`; courses still lacking data recorded (not omitted) | REQ-GRADES-01 | Requires the real post-import hosted Supabase state | Run `scripts/check_data_quality.py --term 202701 --json` against the live DB; confirm `no_historical_analytics` info findings only for genuinely un-sourced courses |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
