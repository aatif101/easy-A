# CLAUDE.md

**Read [`AGENTS.md`](AGENTS.md) first.** It is the canonical agent entry point for this
repository and is kept current; this file only points at it so the two cannot drift.

Read order: `AGENTS.md` → `.planning/STATE.md` → `.planning/PROJECT.md` →
`.planning/ROADMAP.md` → `README.md` for commands.

Six things that matter most, repeated here because they are easy to get wrong:

1. **⛔ 47 non-Tampa Spring 2027 sections are still stored in the beta database.** The first
   expansion pass queried all campuses. PR #16 fixed the cause (`campus="T"` pinned, non-Tampa
   rows rejected) but **did not delete the rows**. Stored, API and coverage-endpoint counts are
   therefore contaminated and do not equal the verified Tampa total of 75. **Cleaning this up is
   the current work.** No section-deletion tooling exists yet.
2. **Sprint 5 is complete** (PR #14, #15) and **real-data validation is complete** (2026-09-09).
   Do not re-plan or re-implement either. Current `origin/main` = `d72f8f3` (verified by fetch
   2026-09-11; PR #13 merged the GSD planning set). The **code** baseline is still `62fb2f1`
   (Sprint 5 + PR #16) — every commit between `62fb2f1` and `d72f8f3` touches only
   `.planning/`, `AGENTS.md`, `CLAUDE.md`, `docs/`, `README.md` and `.gitignore`, so no
   application code or test changed. `.planning/STATE.md`, `.planning/ROADMAP.md` and `AGENTS.md`
   still quote `62fb2f1` as `origin/main`; read that as the code baseline, not the tip.
3. **Five targets validated, 75 verified Tampa sections** — MAC 1105 (5), ENC 1101 (41),
   AMH 2020 (17), PSY 2012 (10), BSC 1005 (2). But **only MAC and ENC have historical grade
   data.** AMH, PSY and BSC use a global fallback with `effective_n = 0` — **that is not
   evidence-backed course history and must never be described as such.** Import priority:
   AMH 2020 → PSY 2012 → BSC 1005.
4. **Scoring is unchanged and stays unchanged.** No rewrite without explicit approval.
5. **Alerts and RMP remain deferred.** The `docs/` handoff files are archival proposals, not
   approved scope, despite the "LOCKED RULES" heading in one of them.
6. **Verify `origin/main` by fetch** and work from a branch or worktree descended from it. Do not
   check out, merge or fast-forward a local `main` you have not verified.

**Next actionable work:** targeted removal of the 47 non-Tampa sections → clean Tampa refresh →
API and coverage verification, recording final counts and confirming no grades or Tampa sections
were lost. Then historical grade imports, then hosted beta.

Test baseline (measured 2026-09-09 at `62fb2f1`; still current at `d72f8f3`, which adds no code
commits): 192 passed / 1 skipped without `EASY_A_TEST_POSTGRES_URL` (193 collected); 193 passed
with PostgreSQL configured; 78 frontend passed. A default run does not use PostgreSQL.
