# Phase 1: Baseline, Scope and Contracts - Context

**Gathered:** 2026-09-08
**Status:** Ready for research and planning
**Provenance:** User decisions in the current Codex conversation, after onboarding and OQ-01 resolution. No separate discuss-phase rerun.

<domain>
## Phase Boundary

Establish the verified baseline, declared launch coverage, source inventory, reproducible method v2,
and UI/API state contracts described by Phase 1 in ROADMAP.md. Plan the remaining work on the existing
application. Feature implementation remains in Phases 2-8. A campus-wide acquisition/inventory
utility is in scope where needed to establish coverage; a new application, grading algorithm
implementation, seat worker, email service, and deployment are not Phase 1 deliverables.
</domain>

<decisions>
## Implementation Decisions

### Launch coverage
- **D-01:** Include all offered USF Tampa classes/sections; do not restrict launch to sample courses, matched professors, available syllabi, or courses with grade history. St. Petersburg and Sarasota-Manatee are outside scope.
- **D-02:** Spring 2027 (Banner term `202701`) is the only supported registration term for now. Historical grade/source terms retain their actual identities and are not selectable registration targets. Express the supported/default term through configuration/contracts rather than adding hard-coded frontend assumptions.
- **D-03:** Use representative samples to validate acquisition and joins before expanding to all Tampa offerings. Samples are a testing strategy, never evidence of campus-wide completeness. Prove expansion with subject/section reconciliation and explicit failed/partial/unqueried states.
- **D-04:** Keep sections visible even without grades, a named instructor, a verified RMP profile, or a current syllabus. Render explicit unavailable/insufficient states for missing evidence; do not fabricate a score or silently narrow coverage.

### Continuity and workflow
- **D-05:** Keep implementation in worktrees off current `origin/main`; leave local `main` and untracked files alone until developer 1 merges. Phase 1 planning stays on `claude/gsd-onboard-774626`, in the same PR as onboarding. OQ-01 is resolved and must not be asked again.
- **D-06:** Reuse completed onboarding, codebase maps, ingested specs, existing clients/importers, and verified decisions. Do not repeat completed steps. Recheck only a demonstrated gap, changed code, stale external fact, or missing acceptance evidence, and record why the check is needed.
- **D-07:** Proceed with existing documents and research first, then plan and check the plans. The discussion of Phase 1 and data sources has occurred; no additional scope interview is needed to plan. Actual grade exports and provisioning remain explicit dependencies, not reasons to restart planning.

</decisions>

<specifics>
## Existing Evidence and Reuse

- `b05cc7d`: codebase mapping completed; reuse `.planning/codebase/`.
- `a18888e`, `894da47`: handoff documents and manifest tracked.
- `792dde2`: PROJECT, REQUIREMENTS, ROADMAP and STATE bootstrapped from ingested documents.
- `1653f2b`: agent entry points and README scope guidance recorded.
- `43f5b4d`: OQ-01 resolved, upstream commit/ancestry checked; do not redo checkout work.
- `docs/live-source-drift-2026-09-01.md`: two-course Spring 2027 observation only. Retain as dated evidence; a wider inventory is new work, not a rerun of onboarding.
- `docs/final-mvp-ui-spec.md`: existing visual and flow contract. Reuse it; Phase 1 translates it into traceable state/payload acceptance, not a redesign.

The README records ODS approval for aggregate grade data. No real grade-export availability,
actual historical terms, or campus-wide coverage has been verified in this planning session.
Do not treat the documented permission claim as possession of data. Raw grade files stay out of Git.
</specifics>

<canonical_refs>
## Canonical References

- `AGENTS.md` and `.planning/STATE.md` - repository constraints and current position.
- `.planning/PROJECT.md` - all 18 locked ADR decisions, constraints, remaining questions.
- `.planning/ROADMAP.md` - Phase 1 success criteria and eight-phase boundaries.
- `.planning/REQUIREMENTS.md` - REQ-LAUNCH-01 and evidence/UI/operations contracts.
- `docs/gsd-core-mvp-prompt.md` - source locked ADR.
- `docs/final-mvp-plan.md` - source PRD, especially sections 2-7.
- `docs/final-mvp-ui-spec.md` - existing UI contract, all seven sections.
- `.planning/INGEST-CONFLICTS.md` - OQ-01 resolution and unresolved source/test questions.
- `.planning/codebase/TESTING.md`, `INTEGRATIONS.md`, `CONCERNS.md` - prior technical evidence.
</canonical_refs>

<deferred>
## Dependencies and Later Work

Historical grade files and actual source terms, hosting/domain, email provider/sender DNS,
and designated test inbox remain dependencies to identify. Registration scope is now settled.
Phase 2 fixes grade scoring and joins; Phase 3 implements verified source links; Phase 4 builds
durable seat refresh; Phase 5 builds verified watches; Phases 6-8 integrate and release.
</deferred>
