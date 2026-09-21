# Agent Instructions — Easy-A

Canonical entry point for any AI coding agent working in this repository. Everything needed for
ordinary continuation is in the repo — you should not need prior conversation context.

## Read first, in this order

1. **`AGENTS.md`** (this file) — durable constraints and orientation
2. **`.planning/STATE.md`** — **current position, live facts, and the next action** (single source of volatile truth)
3. **`.planning/PROJECT.md`** — scope, the active milestone (MVP 1), decisions, open questions
4. **`.planning/ROADMAP.md`** — phase sequence and backlog
5. **`README.md`** — as needed, for commands and local setup

## What this is

Easy-A is a **working application**, not a prototype or a greenfield build: Python 3.12 / FastAPI /
SQLAlchemy / Alembic / PostgreSQL (hosted on Supabase) on the backend, React / TypeScript / Vite /
Tailwind on the frontend. It has real USF Spring 2027 schedule ingestion, an XLSX grade-import
pipeline, a historical easiness score with Bayesian shrinkage and confidence labels, configurable
course coverage, seat-freshness classification, GenEd metadata, and a data-quality pipeline.

**Core value:** every number a student sees is a real observed outcome with a visible denominator,
a named source and a timestamp — and when the evidence does not exist, the product says so instead
of producing a plausible-looking result.

## Where the project stands right now

**Do not hard-code current facts in this file — they drift.** `.planning/STATE.md` is the single
source for the live `origin/main` SHA, the working branch, section/course/grade counts, the test
baseline, and the next action. Read it. Anything in an older doc that states a count, SHA, or
"current gate" as *present-tense fact* is history unless STATE.md repeats it.

## Current milestone — MVP 1

The active goal is **MVP 1**: all ~3,782 USF Tampa Spring 2027 sections ingested and searchable
against hosted Supabase, each with historical grade distributions imported and easiness computed
from that real data (not the `effective_n=0` global fallback), with search p95 < ~1.5s. Verified
RMP instructor links/ratings are **MVP 2**. The definition lives in `.planning/PROJECT.md`; the
phase sequence to get there lives in `.planning/ROADMAP.md`.

## Hard constraints

These are durable and govern all work. The authoritative set is `D-01`..`D-20` in the
`.planning/PROJECT.md` `<decisions>` block; the load-bearing ones:

- **No scoring rewrite without explicit approval.** The historical easiness score — its
  grade/withdrawal composition, Bayesian shrinkage, confidence labels, and course /
  instructor-course fallback — is the frozen baseline (D-02).
- **A global-prior fallback is not course history.** Never present a course with `effective_n = 0`
  as having evidence-backed historical analytics (D-20).
- **No fabricated data or coverage.** Every figure carries a real source and a date; report what
  failed rather than omitting it (D-06). Explicit unavailable/insufficient/suppressed states (D-07).
- **Seats, GenEd, modality and syllabus signals must not affect scoring** (D-03).
- **Preserve term + CRN identity, provenance and deduplication.** Grade rows are unique by
  term/CRN/**source**; duplicate exports must not double-count (D-04).
- **Never commit raw grade export files.** The repo stores derived aggregates and provenance (D-19).
- **Narrow, bounded requests to USF public sources.** No scraping, no broad crawling (D-08, D-09).
- **No LLM/AI features; no auth/accounts; no auto-registration** (D-06, out-of-scope in PROJECT.md).
- **Verify `origin/main` by fetch** and work from a branch/worktree descended from it; do not check
  out, merge or fast-forward a local `main` you have not verified (D-10).

## Repository layout for context

| Path | What it answers |
|---|---|
| `.planning/STATE.md` | Where the project is now; live facts; what to do next |
| `.planning/PROJECT.md` | Scope, the MVP-1 milestone, constraints, decisions, open questions |
| `.planning/REQUIREMENTS.md` | Requirement ledger with evidence |
| `.planning/ROADMAP.md` | Phase sequence and backlog |
| `.planning/ARCHIVE.md` | Superseded dated history (Sprint 5 / Phase 1 / Phase 2 results) |
| `.planning/codebase/` | Codebase maps — **dated, pre-Sprint-5**; useful for structure, stale on specifics |
| `.planning/phases/_superseded/` | Planning from a roadmap that no longer applies. Do not execute. |
| `docs/*.md` | **Archival proposals.** Not approved scope — see below. |

## The `docs/` handoff files are proposals, not scope

`docs/final-mvp-plan.md`, `docs/final-mvp-ui-spec.md` and `docs/gsd-core-mvp-prompt.md` are
proposals from an earlier planning conversation. Despite the "LOCKED RULES" heading in the third,
their claims are **not adopted as-is**: email alerts as required scope, verified RMP links as
required scope, and a grade-only scoring rewrite are all rejected/deferred. They are typed `DOC` at
low precedence in `docs/gsd-mvp-manifest.yaml` so a future `/gsd-ingest-docs` run cannot promote
them over current planning. Do not restore them to ADR/PRD/SPEC.

## Workflow

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- `/gsd-plan-phase <N>` — plan a phase; `/gsd-execute-phase <N>` — execute a planned phase

If you are not running GSD, read `.planning/STATE.md` and `.planning/ROADMAP.md` before changing
code, and keep `STATE.md` accurate when you finish.
