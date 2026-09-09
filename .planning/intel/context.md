# Context (DOC intel)

Extracted from documents classified `DOC`. Precedence rank 3 (lowest).
One source doc in this ingest set: `docs/live-source-drift-2026-09-01.md`.

Content is appended verbatim in substance with source attribution. Per the
classification note, this document is observational evidence only - its seat and
instructor values are point-in-time observations, not requirements or configuration
defaults. Nothing here was promoted into requirements.md or constraints.md.

Also recorded below: baseline facts verified against the repository and the
evidence-backed codebase map during synthesis. Those are marked as verification notes,
not ingested document content.

---

## Topic: Live source drift check, 2026-09-01

- source: docs/live-source-drift-2026-09-01.md
- scope: Spring 2027 (`202701`), Tampa (`T`), `MAC 1105` and `ENC 1101` only
- method: two narrow public Staff Schedule searches and two course searches in the public Simple Syllabus library. It did not ingest, crawl, or retain source HTML, and it does not change signal scoring.

Schedule observations:
- `MAC 1105`: five Tampa sections currently listed. All instructors remain `Staff`. Against the checked-in `schedule_current.html` baseline, CRN `13173` remains capacity/enrollment/seats `135/0/135`; CRN `19410` changed from `190/207/-17` to `135/0/135`. The live note for CRN `19410` now says video lectures are on Canvas, weekly SMART Lab time is required, and quizzes and exams are in person in the SMART Lab.
- `ENC 1101`: 41 Tampa sections currently listed, all with instructor `Staff` and capacity/enrollment/seats `19/0/19`. The repository has no checked-in Spring 2027 ENC schedule baseline, so instructor and seat change cannot be determined; these are current observations only.

Syllabus observations:
- No Spring 2027 `MAC 1105` syllabus appeared in the public Simple Syllabus library.
- No Spring 2027 `ENC 1101` syllabus appeared in the public Simple Syllabus library.
- Matching public library results for both courses were Fall 2026 documents only.

Stated result: instructor assignments did not change for the comparable MAC rows; a seat snapshot changed for CRN `19410`; and no new current-term syllabus was found for either requested course. ENC change status remains unknown because no prior ENC baseline exists in the repository.

Downstream relevance (recorded, not asserted as requirement):
- Every observed section in the sampled scope has instructor `Staff`. REQ-RMP-01 and professor-specific grade evidence depend on named instructors. See INGEST-CONFLICTS.md WARNING 2.
- No current-term syllabus was found for either sampled course. REQ-POLICY-01 depends on the historical-source path in this scope. See INGEST-CONFLICTS.md WARNING 3.
- A real upstream row published negative seats remaining (`-17`). This corroborates the REQ-SEAT-01 rule that valid negative remaining seats are treated as full/over capacity. See INGEST-CONFLICTS.md INFO 6.

## Topic: Baseline commit state (verification note, not ingested doc content)

- source: repository inspection during synthesis, cross-referenced with docs/final-mvp-plan.md section 2 and docs/gsd-core-mvp-prompt.md
- `refs/remotes/origin/HEAD` = `06634490de5c765bdc7b55e4f439476b0e4fa0f7` - the commit the handoff audited.
- `refs/heads/main` = `d880d3c2bd31158c2392725e5c203ac92b2088fa` - the user's local main, unchanged.
- Worktree `C:/Users/smati/VS Code Projects/easy-A` is checked out on `main` at `d880d3c` and reports untracked `web/` plus untracked copies of the four handoff documents.
- `web/` is not tracked at `d880d3c` but is tracked at `06634490`.
- This ingest ran in worktree `.claude/worktrees/gsd-onboard-774626` on branch `claude/gsd-onboard-774626` at `894da473d2e2eefa5dc4797b1f598dd63cf2c15f`, a descendant of `06634490`.
- Consequence: the hazard described in docs/final-mvp-plan.md section 2 is still live, not resolved. See INGEST-CONFLICTS.md WARNING 1.

## Topic: Codebase map corroboration (verification note, not ingested doc content)

- source: .planning/codebase/ (STACK.md, TESTING.md, CONCERNS.md) plus direct file inspection
- `src/easy_a/analytics/scoring.py` defines `DEFAULT_GRADE_WEIGHT = 0.80`, `DEFAULT_NON_WITHDRAWAL_WEIGHT = 0.20`, `DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR = 0.75` and `DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR = 0.10`. The PRD claim about the 80/20 composite and the 0.75/0.10 no-evidence defaults is accurate, and locked decision ADR-02 is grounded in current code.
- STACK.md confirms the stack ADR-01 requires preserving: Python >=3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16, React 19, TypeScript ~5.9, Vite, Tailwind.
- TESTING.md records Python tests running on `sqlite+pysqlite:///:memory:` via `tests/conftest.py` while the default `DATABASE_URL` targets PostgreSQL 16. This is the exact gap ADR-16 and REQ-OPS-01 require closing.
- CONCERNS.md records no `.github/` directory and no CI config anywhere in the repo. REQ-OPS-01 requires CI; it is a net-new build, not a modification.
- CONCERNS.md records two parallel seat sources of truth - canonical `Section` columns written by `src/easy_a/schedule/ingest.py` and `SeatSnapshot` rows - with a fallback in `src/easy_a/rankings/service.py` that can make a stale canonical column look current. This directly threatens REQ-SEAT-01 freshness honesty and ADR-06.
- CONCERNS.md independently cites docs/live-source-drift-2026-09-01.md as evidence that upstream genuinely publishes negative seats-remaining.
