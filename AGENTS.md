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
| Baseline | `origin/main` = `180afe0b8faf72a70c297e4c3d4af40c8c3b15a0` |
| Sprint 5 | **Complete** — merged via PR #14 and PR #15. Do not re-plan or re-implement it. |
| Now | **Real-data expansion validation** — validate the five configured Spring 2027 targets against real ingestion |
| Next | Hosted beta — deployment, CI, performance measurement, observability, operator runbook |

Fetch and verify current `origin/main` before planning rather than trusting the SHA above.

### Test baseline

Measured 2026-09-08 at `180afe0`: **191 Python passed / 1 skipped**, **78 frontend passed**.

The skip is the PostgreSQL integration test, which skips when `EASY_A_TEST_POSTGRES_URL` is
unset. PostgreSQL integration coverage exists but most of the suite still runs on SQLite — do not
describe it as a PostgreSQL suite.

### Configured course targets

`config/course_targets.toml`, catalog edition 2026-2027:

| Subject | Number | Status |
|---------|--------|--------|
| MAC | 1105 | Previously validated |
| ENC | 1101 | Previously validated |
| AMH | 2020 | Configured, **not validated** |
| PSY | 2012 | Configured, **not validated** |
| BSC | 1005 | Configured, **not validated** |

**Configuration is not coverage.** Do not claim a target is covered until real ingestion
validates it.

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

- **Ranking search cost at broader coverage** — `GET /api/v1/rankings/search` ranks sections
  before slicing pagination. Measure during validation.
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Needs a real or sample InfoCenter export nobody
  currently has.
- **Broader real-data coverage is unvalidated** — three of five configured targets have never
  been ingested.
- **Deployment host and domain** not yet supplied.

Fixed in Sprint 5, do **not** re-plan: silent frontend fixture fallback, missing seat freshness
contract, absent PostgreSQL integration coverage, hard-coded Spring 2027 term preference.

## Workflow

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- `/gsd-plan-phase 1` — plan Phase 1 (Real-Data Expansion Validation). **Not Sprint 5**, which is
  already implemented and merged.
- `/gsd-execute-phase N` — execute a planned phase

If you are not running GSD, read `.planning/STATE.md` and `.planning/ROADMAP.md` before changing
code, and keep `STATE.md` accurate when you finish.
