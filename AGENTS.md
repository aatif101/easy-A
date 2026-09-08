# Agent Instructions — Easy-A

Entry point for any AI coding agent working in this repository.

## What this project is

Easy-A is a **working application**, not a prototype and not a greenfield build. FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, and a validated real-data beta covering `MAC 1105` and `ENC 1101`.

**Current planning phase: Sprint 5** — broader configurable course coverage, near-live seat
freshness, and deployment-safe configuration.

## Start here

**`.planning/STATE.md`** — current position, next action, open questions, and the constraints that
matter. One file, written to orient a cold start. Read it first.

`README.md` is accurate about what runs today. `.planning/` is authoritative for what comes next.

## Repository layout for context

| Path | What it answers |
|---|---|
| `.planning/STATE.md` | Where the project is; what to do next |
| `.planning/PROJECT.md` | Scope, constraints, decisions, open questions |
| `.planning/REQUIREMENTS.md` | Sprint 5 scope, next, and deferred candidate phases |
| `.planning/ROADMAP.md` | Sprint 5 → hosted beta, plus a backlog of candidate later phases |
| `.planning/codebase/` | What the code **is** — 7 evidence-backed maps |
| `.planning/phases/_superseded/` | Planning built on a roadmap that no longer applies. Do not execute. Its `01-RESEARCH.md` still holds real measurements. |
| `docs/*.md` | Handoff **proposals** from an earlier conversation. Input, not approved scope. |

## Hard constraints

**Do not check out, merge, or fast-forward local `main`.** `refs/heads/main` is at `d880d3c` and
the primary checkout sits on it with untracked files present. `origin/main` is at `06634490`. Work
from branches or worktrees descended from `origin/main`.

**Preserve the existing scoring model.** The historical easiness score — its grade/withdrawal
composition, Bayesian shrinkage, confidence labels, and course / instructor-course fallback — is
the current baseline. A scoring rewrite is **not** approved scope. Seats, modality, GenEd and
syllabus signals must not influence the score.

**Do not treat the handoff documents as approved scope.** `docs/final-mvp-plan.md`,
`docs/final-mvp-ui-spec.md` and `docs/gsd-core-mvp-prompt.md` are proposals. Despite the
"LOCKED RULES" heading in the third, four of their claims are **not adopted**: email seat alerts
as required scope, verified RMP links as required scope, a grade-only scoring rewrite, and all
offered USF Tampa sections as launch scope.

**Do not pull deferred work into the current sequence.** Seat alerts and RMP integration are
candidate later phases. Do not add subscriber, watch, outbox or email-provider work.

**Never fabricate evidence.** Every displayed number must be a real observed outcome with a
visible denominator, a named source and a timestamp. When evidence is absent, say so. This applies
to your work too: do not invent data coverage, source permissions, credential access, or
deployment completion. Coverage is claimed only after it is actually ingested and validated.

**Bounded source access.** Requests to USF public sources stay narrow and bounded, matching
existing practice. No broad crawling. No scraping.

The full constraint set is `D-01` through `D-18` in the `.planning/PROJECT.md` `<decisions>` block.

## Known baseline observations

Real and verified. Do not paper over them, and do not treat them as licence to redesign:

- `web/src/api/rankings.ts` silently serves synthetic fixtures when `VITE_API_BASE_URL` is unset —
  a misconfigured deploy renders plausible fake course data (Sprint 5, REQ-CONFIG-01)
- Two seat sources of truth — canonical `Section` columns vs. `SeatSnapshot` rows — with a
  fallback that can make a stale column look current (Sprint 5, REQ-SEAT-01)
- `course_id` is null on grade import; grade rows are unique by term/CRN/**source**, so duplicate
  exports double-count without explicit source selection
- `GET /api/v1/rankings/search` ranks every section in the term before slicing pagination
- `src/easy_a/grades/parser.py` converts every blank cell to `0` with no suppression path —
  resolving this needs a real InfoCenter export nobody currently has
- Python tests run on SQLite while deployment targets PostgreSQL 16; migrations are never applied
  in tests. Baseline: **166 Python + 19 frontend passing** (measured 2026-09-08).

## Workflow

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- `/gsd-plan-phase N` — plan a phase before implementing it
- `/gsd-execute-phase N` — execute a planned phase

If you are not running GSD, still read `.planning/STATE.md` and `.planning/ROADMAP.md` before
changing code, and keep `STATE.md` accurate when you finish.
