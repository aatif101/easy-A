---
phase: 1
slug: baseline-scope-and-contracts
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-08
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

Measured directly in this worktree during Phase 1 research (see `01-RESEARCH.md`), not
taken from either conflicting document figure.

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python), vitest (frontend, under `web/`) |
| **Config file** | `pyproject.toml` (pytest); `web/package.json` + `web/vite.config.ts` |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest -q` then `cd web && npm test` |
| **Estimated runtime** | Python and frontend suites both complete in well under a minute |

**Measured baseline (2026-09-08, worktree `claude/gsd-onboard-774626`):**
166 Python tests passing, 19 frontend tests passing. This resolves OQ-04 — it confirms
the PRD figure and supersedes `.planning/codebase/TESTING.md`'s approximate "~154".

**Known infrastructure gap:** all 166 Python tests run against
`sqlite+pysqlite:///:memory:` while the deployment target is PostgreSQL 16. Locked
decision D-ADR-16 requires real PostgreSQL tests for query, migration and concurrency
behavior. That is net-new build work scheduled in Phase 7, not a Phase 1 deliverable,
but Phase 1 must record the SQLite-only baseline as a known limitation rather than
report 166 passing tests as evidence of PostgreSQL compatibility.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest -q` and `cd web && npm test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Populated by `gsd-planner` when Phase 1 PLAN.md files are written. Phase 1 is a
contracts-and-inventory phase, so several deliverables are documents rather than code;
those require the explicit manual-verification entries below rather than a test command.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| *(pending planner)* | — | — | REQ-LAUNCH-01 | — | — | — | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Record the exact baseline test counts as a reproducible command plus captured
      output, so later phases can detect regression against a real number
- [ ] No framework install needed — pytest and vitest are both present and green

---

## Manual-Only Verifications

Phase 1's exit gate is largely documentary. These cannot be asserted by a test runner
and must be checked by a reader against the written artifact.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Method v2 is reproducible from the written contract alone | REQ-EVID-01 | Requires a human to re-derive the formula from prose | Give the contract to a reader with no prior context; they must reproduce the worked example (A=40 B=30 C=20 D=5 F=5 W=10 → A rate 40%, W 9.09%, ease 7.2/10) without reading source code |
| RULE-20 / 60A / 60B / 60C / K60 are each independently stated | REQ-EVID-01 | Checks separateness of prose rules, not runtime behavior | Confirm five distinct rules with distinct test intents; a test for one must not be cited as coverage for another |
| Launch coverage manifest names no invented semester or percentage | REQ-LAUNCH-01 | Requires cross-checking claims against real source data | Every named term and coverage number traces to an inspected artifact; unavailable data is labeled unavailable |
| Named-instructor and syllabus coverage inventories reflect real counts | REQ-LAUNCH-01 | Requires a bounded live inventory run, not a unit test | Inventory output carries a timestamp, the queried scope, and per-subject counts |
| Phase 3 exit criterion restated to match observed coverage | REQ-RMP-01 | Editorial judgment against inventory evidence | ROADMAP Phase 3 criterion is provable given the inventory's actual numbers |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
