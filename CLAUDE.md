# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first.** It is the canonical agent entry point for this
repository and is kept current; this file only points at it so the two cannot drift.

Read order: `AGENTS.md` → `.planning/STATE.md` → `.planning/PROJECT.md` →
`.planning/ROADMAP.md` → `README.md` for commands.

Five things that matter most, repeated here because they are easy to get wrong:

1. **Sprint 5 is complete** — merged via PR #14 and PR #15 at `origin/main` = `62fb2f1`. Do not
   re-plan or re-implement it. Current activity is **real-data expansion validation** for the five
   configured Spring 2027 targets; hosted beta comes after.
2. **This is a working application**, not a greenfield build. `README.md` describes what runs
   today; `.planning/` is authoritative for what is next.
3. **Configuration is not coverage.** Five course targets are configured; only `MAC 1105` and
   `ENC 1101` are validated. Do not claim coverage for `AMH 2020`, `PSY 2012` or `BSC 1005` until
   real ingestion validates them.
4. **The `docs/` handoff files are archival proposals, not approved scope.** One carries a
   "LOCKED RULES" heading; four of its claims are not adopted — email alerts, RMP links, a
   grade-only scoring rewrite, and campus-wide launch coverage. No scoring rewrite without
   explicit approval.
5. **Verify `origin/main` by fetch** and work from a branch or worktree descended from it. Do not
   check out, merge or fast-forward a local `main` you have not verified.

Test baseline (2026-09-08 at `62fb2f1`): 192 Python passed / 1 skipped, 78 frontend passed. The
skip needs `EASY_A_TEST_POSTGRES_URL`; most of the suite still runs on SQLite.
