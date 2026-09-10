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
   the current work.** Removal tooling (`scripts/cleanup_non_tampa_sections.py`) and an
   error-severity `unsupported_campus_section` quality check now exist, but **neither has been
   run against the beta database**.
2. **Sprint 5 is complete** (PR #14, #15) and **real-data validation is complete** (2026-09-09).
   `origin/main` = `d72f8f3` (verified by fetch 2026-09-09; `62fb2f1` is an ancestor). Do not
   re-plan or re-implement either.
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

**Next actionable work:** run `scripts/cleanup_non_tampa_sections.py --term 202701` against the
beta database (dry run, then `--apply --expect-removed 47 --json`), with
`scripts/check_data_quality.py --term 202701` before and after as an independent confirmation →
clean Tampa refresh → API and coverage verification, recording final counts and confirming no
grades or Tampa sections were lost. Then historical grade imports, then hosted beta.

Test baseline (2026-09-10 at `d72f8f3` plus the cleanup tooling and campus check): 215 passed /
1 skipped without `EASY_A_TEST_POSTGRES_URL` (216 collected); 78 frontend passed. A default run does not use
PostgreSQL, and the PostgreSQL-configured figure has not been re-measured since it was 193 at
`62fb2f1`.
