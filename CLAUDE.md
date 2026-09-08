# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first.** It is the canonical agent entry point for this
repository and is kept current; this file only points at it so the two cannot drift.

Three things that matter most, repeated here because they are easy to get wrong:

1. **`.planning/STATE.md` is the orientation file.** Start there, not with `README.md`.
2. **`README.md` describes the current beta, not target scope.** It says V1 has no
   RateMyProfessors data, accounts, or deployment — all three are in scope for the MVP
   (Phases 3, 5, 7–8). Use `.planning/` for scope.
3. **Do not check out, merge, or fast-forward local `main`.** It sits at `d880d3c` with
   an untracked `web/` directory. Work from a branch or worktree descended from
   `origin/main` (`06634490`). See OQ-01 in `.planning/PROJECT.md`.
