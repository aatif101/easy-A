# Agent Instructions — Easy-A

Entry point for any AI coding agent working in this repository. Everything needed for ordinary
continuation is in the repo — you should not need prior conversation context.

## Read first, in this order

1. **`AGENTS.md`** (this file) — constraints and orientation
2. **`.planning/STATE.md`** — current position and the next action
3. **`.planning/PROJECT.md`** — scope, decisions, open questions
4. **`.planning/ROADMAP.md`** — phase sequence and backlog
5. **`README.md`** — as needed, for commands and local setup

## Current state

Easy-A is a **working application**, not a prototype and not a greenfield build. FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, configurable course coverage, and seat freshness classification.

| | |
|---|---|
| Baseline | `origin/main` = `9d686c01bca44b3bbf79a2277a4a1b2618df00a9` (verified 2026-09-15) |
| Sprint 5 | ✓ **Complete** — merged via PR #14 and PR #15. Do not re-plan or re-implement it. |
| PR #16 | ✓ **Merged** — pins `campus="T"` and rejects non-Tampa rows before ingestion |
| Real-data validation | ✓ **Complete** (2026-09-09) — five targets verified, **75 Tampa sections** |
| Tampa-only correction | ✓ **Complete** — verified 2026-09-14 and merged via PR #18; PR #17 closed as superseded |
| **Now** | Prepare Phase 3 and obtain approved historical grade exports, starting with AMH 2020 |
| Then | Hosted beta — deployment, CI, performance measurement, observability, runbook |

Fetch and verify current `origin/main` before planning rather than trusting the SHA above.

### Tampa-only correction — completed, verified and merged via PR #18

The first expansion pass inserted **47 non-Tampa Spring 2027 sections** before PR #16 fixed the
cause. On 2026-09-14 the Phase 2 cleanup removed exactly those 47 sections: current term,
configured target course, nonblank stored campus other than Tampa after trimming and
case-folding. It also removed 47 linked seat snapshots and 47 instructor observations, with zero
syllabi and zero grade rows removed. Blank/null campus rows were excluded from deletion.

The required clean refresh then produced **77 current Tampa sections and zero other-campus
sections**: MAC 1105 = 5, ENC 1101 = 41, AMH 2020 = 19, PSY 2012 = 10, BSC 1005 = 2. Stored,
rankings API and `GET /api/v1/metadata/coverage` counts agreed. The two-section increase from the
75 observed on 2026-09-09 is real source drift in AMH 2020, not contamination. All 237 grade rows,
all 263 historical sections and every pre-cleanup Tampa section remained intact. PR #18 merged the
verified correction and PR #17 was closed as superseded. The current remaining action is Phase 3
preparation and obtaining the approved AMH 2020 historical grade export; do not rerun the
destructive cleanup expecting 47.

### Test baseline

Measured 2026-09-09 at `62fb2f1`:

| Condition | Result |
|-----------|--------|
| `uv run pytest -q`, no `EASY_A_TEST_POSTGRES_URL` | **192 passed, 1 skipped** (193 collected) |
| Backend with PostgreSQL configured | **193 passed** |
| Frontend `npm test` in `web/` | **78 passed** |

Both facts are true: a **default run does not use PostgreSQL** — most of the suite runs on SQLite
and the integration test skips unless `EASY_A_TEST_POSTGRES_URL` is set; with it set, all 193
pass. Do not state only one.

Phase 2 branch verification on 2026-09-14: **216 passed, 2 skipped** without PostgreSQL;
**218 passed** with PostgreSQL configured; ruff and strict mypy passed. The frontend baseline was
not re-measured during this backend/data-correction phase.

### Configured course targets

`config/course_targets.toml`, catalog edition 2026-2027:

Validated against real Spring 2027 data on 2026-09-09:

| Course | Catalog | Verified Tampa sections | Historical grade data |
|--------|---------|-------------------------|-----------------------|
| MAC 1105 | present | 5 | Real data; high-confidence course analytics |
| ENC 1101 | present | 41 | Real data; high-confidence course analytics |
| AMH 2020 | present | 17 | **None** — global fallback, `effective_n = 0` |
| PSY 2012 | present | 10 | **None** — global fallback, `effective_n = 0` |
| BSC 1005 | present | 2 | **None** — global fallback, `effective_n = 0` |
| **Verified Tampa total** | | **75** | |

**Section coverage and grade coverage are different things.** All five have verified sections;
only two have historical grade data. **The AMH / PSY / BSC fallback scores are not evidence-backed
course history** — they are global priors with zero observed outcomes. Never present them as
course history. Import priority: AMH 2020 → PSY 2012 → BSC 1005.

The 75 total above is the dated 2026-09-09 validation result. The clean 2026-09-14 refresh found
77 Tampa sections because AMH 2020 increased from 17 to 19.

## Hard constraints

- **No scoring rewrite without explicit approval.** The historical easiness score — its
  grade/withdrawal composition, Bayesian shrinkage, confidence labels, and course /
  instructor-course fallback — is the baseline.
- **No email alerts yet.** Candidate later phase. Do not add subscriber, watch, outbox or
  email-provider work.
- **No RMP yet.** Candidate later phase. And whenever it is picked up: no scraping, no bulk
  crawler, no imported ratings or review content.
- **No LLM or AI features.**
- **No fabricated data or coverage.** Every figure carries a real source and a date. Report what
  failed rather than omitting it.
- **A global-prior fallback is not course history.** Never present a course with `effective_n = 0`
  as having evidence-backed historical analytics.
- **Never commit raw grade export files.** The repo stores derived aggregates and provenance.
- **Narrow, bounded requests to USF public sources.** No broad crawling.
- **Preserve term + CRN identity**, source provenance and deduplication. Grade rows are unique by
  term/CRN/**source**; duplicate exports must not double-count.
- **Seats, GenEd, modality and syllabus signals must not affect scoring.**
- **Verify `origin/main` by fetch**; work from a branch or worktree descended from it. Do not
  check out, merge or fast-forward a local `main` you have not verified.

Full set: `D-01`..`D-19` in the `.planning/PROJECT.md` `<decisions>` block.

## Repository layout for context

| Path | What it answers |
|---|---|
| `.planning/STATE.md` | Where the project is; what to do next |
| `.planning/PROJECT.md` | Scope, constraints, decisions, open questions |
| `.planning/REQUIREMENTS.md` | Complete / current / next / deferred requirements with evidence |
| `.planning/ROADMAP.md` | Sprint 5 (complete) → validation → hosted beta, plus backlog |
| `.planning/codebase/` | Codebase maps — **dated 2026-09-05 at `06634490`, pre-Sprint-5**; useful for structure, stale on specifics |
| `.planning/phases/_superseded/` | Planning from a roadmap that no longer applies. Do not execute. |
| `docs/*.md` | **Archival proposals.** Not approved scope — see below. |

## The `docs/` handoff files are proposals, not scope

`docs/final-mvp-plan.md`, `docs/final-mvp-ui-spec.md` and `docs/gsd-core-mvp-prompt.md` are
proposals from an earlier planning conversation. Despite the "LOCKED RULES" heading in the third,
four of their claims are **not adopted**: email alerts as required scope, verified RMP links as
required scope, a grade-only scoring rewrite, and all offered USF Tampa sections as launch scope.

They are typed `DOC` at low precedence in `docs/gsd-mvp-manifest.yaml` and carry `type: doc`
frontmatter so a future `/gsd-ingest-docs` run cannot promote them over current planning. Do not
restore them to ADR/PRD/SPEC.

## Still-open issues

Real and unresolved. Do not paper over them, and do not treat them as licence to redesign:

- **No historical grades for AMH 2020, PSY 2012, BSC 1005** — global fallback, `effective_n = 0`
  (REQ-GRADES-01)
- **Search performance needs work at widened coverage** — an initial local measurement on the
  corrected 77-section dataset took about 10.1 seconds; hosted measurement remains REQ-PERF-01
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Needs a real or sample InfoCenter export nobody
  currently has.
- **Deployment host and domain** not yet supplied.

Fixed, do **not** re-plan: silent frontend fixture fallback, missing seat freshness contract,
absent PostgreSQL integration coverage, hard-coded Spring 2027 term preference (all Sprint 5);
configured refresh querying all campuses (PR #16); stored cross-campus contamination (Phase 2).

Confirmed healthy by the validation run: zero data-quality errors across 202408 / 202501 / 202508
/ 202701; seat refresh preserved previous snapshots, section identity and all 237 grade rows;
frontend and API verification passed with no console errors.

## Workflow

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- Phase 2 is merged through PR #18 and PR #17 is closed as superseded; do not re-plan or rerun its
  47-row cleanup.
- `/gsd-plan-phase 3` — plan historical grade coverage after approved exports are available.
- `/gsd-execute-phase N` — execute a planned phase

If you are not running GSD, read `.planning/STATE.md` and `.planning/ROADMAP.md` before changing
code, and keep `STATE.md` accurate when you finish.
