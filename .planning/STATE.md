---
gsd_state_version: '1.0'
status: planning
progress:
  total_phases: 2
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
of producing a plausible-looking result.

**Current focus:** Phase 1 — Sprint 5: Coverage Expansion, Seat Freshness, Deployment-Safe
Configuration

## Current Position

Phase: 1 of 2 (Sprint 5)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-09-08 — Roadmap and requirements restructured to match the actual project
sequence. The earlier eight-phase greenfield MVP structure was replaced, and scope that had been
recorded as locked without confirmation (email alerts, RMP, a scoring rewrite, campus-wide launch
coverage) was corrected. No implementation performed; no application code changed.

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**Recent Trend:** No plans executed yet.

## Accumulated Context

### Baseline

Easy-A is a working application, not a prototype. FastAPI backend, React/TypeScript frontend,
PostgreSQL, real Spring 2027 schedule ingestion, real historical grade imports, and a validated
real-data beta covering `MAC 1105` and `ENC 1101` with high-confidence historical analytics, GenEd
metadata, seat snapshots and a data-quality pipeline. API and frontend smoke-tested end to end.

**Measured test baseline (2026-09-08, this worktree): 166 Python tests and 19 frontend tests
passing.** All Python tests run on SQLite while the deployment target is PostgreSQL 16.

### Decisions

Constraints that govern the work live in the PROJECT.md `<decisions>` block (D-01..D-18). The
load-bearing ones for Sprint 5 planning:

- D-02: the existing scoring model is preserved as the baseline — no rewrite is approved
- D-05: seat observation age must be visible; a failed request must not advance the success
  timestamp or fabricate a zero count
- D-06: no fabricated data, including no production synthetic fallback and no invented coverage
  figures
- D-14 / D-15: Sprint 5 scope and its explicit exclusions
- D-16 / D-17 / D-18: alerts, RMP and broader launch coverage are deferred, not committed

### Corrections applied 2026-09-08

The ingested handoff documents were treated as confirmed product decisions during onboarding. They
are proposals. Four claims were corrected and are no longer recorded as locked or user-confirmed:

| Claim | Corrected to |
|-------|--------------|
| Email seat alerts are required MVP scope | Candidate later phase, after near-live seat refresh and hosted beta stability |
| Verified RMP links are required MVP scope | Deferred until after hosted beta and core data stability; not a beta blocker |
| Replace the score with a grade-only v2 formula | Existing scoring model preserved as baseline; methodology review is optional research only |
| All offered USF Tampa sections are the launch scope | Validated coverage is `MAC 1105` + `ENC 1101`; broader coverage is an expansion target subject to validation |

The eight-phase delivery sequence built on those claims was replaced by the Sprint 5 → hosted beta
roadmap. Phase planning artifacts produced under the old structure are archived at
`.planning/phases/_superseded/` with an explanation.

### Blockers/Concerns

No blockers for Sprint 5 planning.

Open questions (full text: PROJECT.md "Open Questions"):
- **OQ-03**: how broadly coverage can expand while keeping refresh sustainable and search
  performance acceptable — answered by measurement during Sprint 5 / Phase 2
- **OQ-04**: whether real InfoCenter exports carry suppression markers, or blank genuinely means
  zero. `src/easy_a/grades/parser.py` converts every blank cell to `0` unconditionally. Needs a
  real or sample export; owner is whoever holds ODS/registrar access.
- **OQ-05**: deployment host and domain, needed before the hosted beta

Baseline observations to respect rather than paper over (evidence in `.planning/codebase/`):
silent frontend fixture fallback when `VITE_API_BASE_URL` is unset (Sprint 5, REQ-CONFIG-01);
two seat sources of truth that can make a stale column look current (Sprint 5, REQ-SEAT-01);
`course_id` null on grade import and term/CRN/source dedup safety (watch during expansion);
search ranking every section before pagination (measure at broader coverage).

## Session Continuity

Last session: 2026-09-08
Stopped at: Planning documents corrected and restructured. No phase planned or executed under the
new roadmap.
Resume file: None
Next action: `/gsd-plan-phase 1` — plan Sprint 5 against the corrected roadmap.
