# Retrospective

## Milestone: v1.0 — MVP 1

**Shipped:** 2026-10-04
**Phases:** 8 phase directories (plus legacy Sprint 5 / Phases 1-3) | **Plans:** 47 | **Span:** 2026-08-31 to 2026-10-04 (git history)

### What Was Built
Full Tampa Spring 2027 coverage (~3,783 sections) on hosted Supabase, course-attributed historical grades, a cached ranking search (p95 277 ms), a live Render hosted beta with a near-live sync worker, and professor-level grade history (Phase 10).

### What Worked
- Read-only measurement gates (ranking diff exit codes, pair re-measure) before the one production write made the Phase 10 apply uneventful: 8,535 inserted as reviewed, course-level scores unchanged.
- Recording owner overrides verbatim in VERIFICATION frontmatter kept SC1 decisions auditable.

### What Was Inefficient
- Phases 03.5, 06 and 07 never got VERIFICATION.md, and phases 04, 08 and 09 went stale after later code changes, so the milestone closed as an override.
- Roadmap carried legacy Phases 1-3 with no phase directories, which tripped the "unstarted phases" close check.
- Phase 10 UAT items sat queued across sessions until the P10-WR-01 fix was merged and deployed.

### Patterns Established
- Operator-run destructive steps behind `--expect-inserted`, in-transaction invariants and the sweep lock.
- Evidence files with dated, counts-only numbers instead of names or connection strings.

### Key Lessons
- Re-run the verifier after late code changes, or the close gate reads phases as stale.
- Document operational rebuild steps (grade re-import, `--rebuild-term`, Render `sync:false` variables); the audit found them undocumented-by-code.
- Fix P10-WR-02 and P10-WR-03 before any backfill re-run.

### Cost Observations
Not recorded.

## Cross-Milestone Trends

| Milestone | Phases | Plans | Closeout |
|-----------|--------|-------|----------|
| v1.0 MVP 1 | 8 | 47 | override_closeout (tech_debt audit) |
