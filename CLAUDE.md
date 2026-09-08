# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first.** It is the canonical agent entry point for this
repository and is kept current; this file only points at it so the two cannot drift.

Four things that matter most, repeated here because they are easy to get wrong:

1. **`.planning/STATE.md` is the orientation file.** Start there. Current planning phase is
   **Sprint 5**: broader configurable course coverage, near-live seat freshness, deployment-safe
   configuration.
2. **This is a working application with a validated real-data beta**, not a greenfield build.
   `README.md` is accurate about what runs today; `.planning/` is authoritative for what is next.
3. **The handoff documents in `docs/` are proposals, not approved scope.** One carries a
   "LOCKED RULES" heading; four of its claims are not adopted — email alerts, RMP links, a
   grade-only scoring rewrite, and campus-wide launch coverage. The existing scoring model is
   preserved as the baseline.
4. **Do not check out, merge, or fast-forward local `main`.** It sits at `d880d3c` with untracked
   files. Work from a branch or worktree descended from `origin/main` (`06634490`).
