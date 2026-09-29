---
phase: "09"
slug: hosted-beta-deployment-ci-observability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-29"
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Full requirement→test map lives in `09-RESEARCH.md` § Validation Architecture; the planner fills the per-task map below.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.3.0 (Python), vitest ^3.2.4 (web) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`); `web/vite.config.ts` |
| **Quick run command** | `uv run pytest tests/sync tests/schedule tests/api -q -x` |
| **Full suite command** | `uv run pytest -q` and `npm --prefix web test` |
| **Estimated runtime** | ~25 seconds (8 s Python + 16 s web) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/sync -q -x` (plus `npm --prefix web test` for UI tasks)
- **After every plan wave:** `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`, `npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test && npm --prefix web run build`
- **Before `/gsd-verify-work`:** Full suite must be green (CI included)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner from 09-RESEARCH.md § Phase Requirements → Test Map) | | | REQ-OPS-01 / REQ-SYNC-01 | | | | | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/sync/__init__.py` and `tests/sync/test_*.py` — REQ-SYNC-01
- [ ] Synthetic whole-term fixture generator (never commit the real 7 MB response)
- [ ] Fix E501 at `scripts/refresh_all_tampa.py:150` and `src/easy_a/refresh/cleanup.py:496` so `ruff check .` is green
- [ ] Prove the 3 skipped Postgres tests against `postgres:16` (docker compose or first CI run)
- [ ] `web/src/components/SyncStatus.test.tsx` — REQ-SYNC-01

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Hosted beta reachable, serves real data, "Updated N min ago" advances, Staff→named appears within one cadence interval | REQ-OPS-01 / REQ-SYNC-01 | Needs deployed hosts | Runbook checklist + live soak protocol |
| Dockerfile builds and 512 MB worker fits | REQ-OPS-01 | Docker unavailable locally | CI `docker build` job; first Render build |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
