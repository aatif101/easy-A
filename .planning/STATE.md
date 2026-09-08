---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 8
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-09-08)

**Core value:** Every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking score.
**Current focus:** Phase 1 — Baseline, Scope and Contracts

## Current Position

Phase: 1 of 8 (Baseline, Scope and Contracts)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-09-08 — Resolved OQ-01 with the user's confirmed worktree strategy;
fetched origin/main and verified current worktree ancestry. No implementation performed.

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:** No plans executed yet.

*Updated after each plan completion*

## Accumulated Context

### Decisions

18 LOCKED decisions (D-ADR-01..18) live in the PROJECT.md `<decisions>` block, all from
`docs/gsd-core-mvp-prompt.md`. Most load-bearing for Phase 1 planning:

- D-ADR-13: start from current `origin/main` in a safe branch/worktree; preserve untracked work
- OQ-01 resolved (user confirmation, 2026-09-08): implementation stays in worktrees off
  `origin/main` (freshly fetched at `06634490`). Leave local `main` and its untracked files
  alone until developer 1 merges. Continue Phase 1 planning on `claude/gsd-onboard-774626`
  in this worktree, keeping planning commits in the same PR as onboarding.
- D-ADR-15: eight delivery outcomes in sequence — one milestone, not eight MVPs
- D-ADR-02 / D-ADR-03: grade ease is grade-only; a prior may adjust real evidence, never replace it
- D-ADR-12 (locked *default* set): k=60, 20-outcome score floor, 60-outcome professor threshold,
  5-minute watched cadence, one-alert-then-rearm — revisable only with documented evidence
- D-ADR-18: done means deployed, real-data, verified email journey — not a roadmap or a fixture demo

Project-level decisions (PROJECT.md Key Decisions): preserve the source PRD's 8-phase structure
and dependency graph rather than applying GSD `standard` granularity; keep the three uses of "60"
as independently testable rules; treat PostgreSQL tests and CI as net-new builds.

### Pending Todos

None yet.

### Blockers/Concerns

Four open questions remain for Phase 1 (full text: PROJECT.md "Open Questions"). OQ-01 is
resolved and no longer blocks planning. The primary checkout remains at `d880d3c` with untracked
work: **do not check out, merge or fast-forward local `main`.** OQ-02 and OQ-03 remain unresolved
scope decisions from `.planning/INGEST-CONFLICTS.md`:
- **OQ-02**: All sampled Spring 2027 Tampa sections show instructor `Staff` (5 MAC 1105 + 41
  ENC 1101). Threatens REQ-RMP-01 coverage and Phase 3's exit criterion. Inventory named-instructor
  coverage in Phase 1 before restating that criterion.
- **OQ-03**: No current-term syllabus found for either sampled course. The historical-source path
  is likely **primary**, not a fallback, for REQ-POLICY-01. Order Phase 3 acceptance cases
  accordingly.
- **OQ-04**: Baseline test count conflict — PRD says 166 Python at `06634490`, codebase map says
  ~154 at `894da473`. ADR-16 locks the baseline, so resolve the exact number in Phase 1.
- **OQ-05**: Unsupplied external dependencies — real grade exports and their terms, launch
  term/subject scope, deployment host and domain, email provider and sender-domain DNS, designated
  test inbox. Blocks Phases 5, 7, 8. Identify in Phase 1; do not purchase services.

Baseline defects to resolve rather than paper over (evidence in `.planning/codebase/CONCERNS.md`):
dual seat source of truth (Phase 4), the 7.8/10-from-nothing composite (Phase 2), `course_id`
null on grade import (Phase 2), silent frontend fixture fallback (Phase 6).

## Deferred Items

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-09-08
Stopped at: OQ-01 resolved and Phase 1 planning unblocked on the onboarding branch.
No phase planned, executed or implemented.
Resume file: None
Next action: `/gsd-plan-phase 1` on `claude/gsd-onboard-774626` in the current worktree.
Keep Phase 1 planning commits in the same PR as onboarding; no further OQ-01 confirmation needed.
