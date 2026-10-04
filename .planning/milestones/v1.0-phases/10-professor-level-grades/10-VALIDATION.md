---
phase: "10"
slug: professor-level-grades
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-04"
---

# Phase 10 — Validation Strategy

> Reconstructed from plan and summary artifacts (State B) on 2026-10-04 at HEAD 294ac2b. The phase has one requirement, REQ-PROF-01; every plan carries automated verify commands.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python, `uv run`) and vitest (web) |
| **Config file** | `pyproject.toml`, `web/vitest` config |
| **Quick run command** | `uv run pytest -q tests/analytics tests/rankings tests/schedule` |
| **Full suite command** | `uv run pytest -q` and `cd web && npx vitest run` |
| **Estimated runtime** | ~25 s (pytest), ~15 s (vitest) |

Observed 2026-10-04: pytest 1043 passed, 4 skipped, 1 xfailed; vitest 119 passed (9 files).

---

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** full suite command
- **Before `/gsd-verify-work`:** full suite green
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

| Plan | Requirement | Behavior covered | Test files | Status |
|------|-------------|------------------|------------|--------|
| 10-01 | REQ-PROF-01 | Instructor-course prior strength 30; non-instructor rows exactly unchanged | `tests/analytics/test_instructor_retune.py` | ✅ green |
| 10-02 | REQ-PROF-01 | Historical backfill: allowlist, pacing, idempotence, course-key safety, sweep isolation | `tests/schedule/test_backfill.py` | ✅ green |
| 10-03 | REQ-PROF-01 | Read-only ranking diff and pair coverage tools | `tests/rankings/test_diff.py`, `tests/analytics/test_pair_coverage.py` | ✅ green |
| 10-04 | REQ-PROF-01 | InstructorBreakdown component: named, Staff, lab, scope gating, a11y | `web/src/components/InstructorBreakdown.test.tsx` | ✅ green |
| 10-05 | REQ-PROF-01 | API breakdown: iff invariant, cache parity, fallback null, payload bound | `tests/rankings/test_instructor_breakdown.py`, `tests/rankings/test_cache_parity.py`, `tests/api/test_rankings_search_sql.py` | ✅ green |
| 10-06 | REQ-PROF-01 | Backfill CLI: dry-run rollback, sweep lock, gates, rollback/rebuild-only | `tests/schedule/test_backfill_cli.py` | ✅ green |
| 10-07 | REQ-PROF-01 | Live what-if parse diagnostics and failed-response saver | `tests/schedule/test_backfill_gap06.py` and related | ✅ green |
| 10-08 | REQ-PROF-01 | Rollout apply and post-deploy checks | Evidence-based (see Manual-Only) | ✅ evidenced |
| 10-09 | REQ-PROF-01 | STATE/evidence recording | Evidence-based (see Manual-Only) | ✅ evidenced |
| 10-10 | REQ-PROF-01 | P10-WR-01: empty-state gate requires othersCount === 0 | `InstructorBreakdown.test.tsx` | ✅ green |
| 10-11 | REQ-PROF-01 | Owner decision record and UAT 7 scan | Evidence-based (see Manual-Only) | ✅ evidenced |

*Status: ✅ green · ✅ evidenced = recorded in committed evidence, no code under test*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why manual | Result |
|----------|-------------|------------|--------|
| Deployed bundle, layout, focus ring, 320 px wrapping and tooltip in a real browser | REQ-PROF-01 | Needs a live browser and deployed site | UAT 1-7 pass (2026-10-04) |
| P10-WR-01 prevalence on live data | REQ-PROF-01 | Needs live public API | UAT 8 pass; count A = 176 |
| Post-apply live sweep keeps backfilled history | REQ-PROF-01 | Needs live worker and hosted DB (also covered by `test_backfilled_history_survives_a_live_sweep_untouched`) | UAT 9 pass |

---

## Validation Sign-Off

- [x] All tasks have automated verify or documented manual-only entries
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true`

**Approval:** validated 2026-10-04

## Validation Audit 2026-10-04
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
