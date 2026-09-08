# Agent Instructions — Easy-A

Entry point for any AI coding agent working in this repository.

## Read this before README.md

`README.md` documents the **current local beta**. It is accurate about what the code
does today and misleading about scope: it states V1 has no RateMyProfessors data,
accounts, or deployment. Those are all **in scope** for the MVP now being built
(Phases 3, 5, and 7–8 respectively).

For target scope, read `.planning/`. For current behavior, read `README.md`.

## Start here

**`.planning/STATE.md`** — current position, next action, open questions, and the
load-bearing decisions. One file, written to orient a cold start. Read it first.

## Repository layout for context

| Path | What it answers |
|---|---|
| `.planning/STATE.md` | Where the project is; what to do next |
| `.planning/PROJECT.md` | Scope, constraints, locked decisions, open questions |
| `.planning/REQUIREMENTS.md` | 17 requirements, all mapped to phases |
| `.planning/ROADMAP.md` | 8 delivery phases, one milestone, with dependencies |
| `.planning/codebase/` | What the code **is** — 7 evidence-backed maps |
| `.planning/intel/` | What the source handoff docs **said**, with provenance |
| `.planning/INGEST-CONFLICTS.md` | What is uncertain, and why |
| `docs/final-mvp-plan.md` | The source PRD (authoritative on detail) |
| `docs/final-mvp-ui-spec.md` | The source UI contract |
| `docs/gsd-core-mvp-prompt.md` | The source ADR — carries LOCKED RULES |

## Hard constraints

**Do not check out, merge, or fast-forward local `main`.** `refs/heads/main` is at
`d880d3c` and carries an **untracked `web/` directory** plus untracked handoff docs.
`origin/main` is at `06634490`. All implementation happens in a worktree or branch
descended from `origin/main`. OQ-01 was resolved by the user on 2026-09-08: keep
implementation in these worktrees and leave local `main` alone until developer 1 merges.
Phase 1 planning continues on the onboarding branch, in the same PR. The primary
checkout's untracked work remains protected; see `PROJECT.md` for the confirmed decision.

**18 decisions are LOCKED** in the `PROJECT.md` `<decisions>` block (`D-ADR-01`
through `D-ADR-18`), sourced from `docs/gsd-core-mvp-prompt.md`. Do not silently
revise them. They may be changed only with documented evidence and matching updates
to methodology and tests.

**Never fabricate evidence.** The product's core value is that every displayed number
is a real observed outcome with a visible denominator, a named source, and a
timestamp. When evidence is absent the product must say so rather than produce a
plausible-looking score. This applies to your work too: do not invent data coverage,
source permissions, credential access, or deployment completion.

## Known baseline defects

Do not paper over these; they are scheduled work with evidence in
`.planning/codebase/CONCERNS.md`:

- A `7.8/10` score can be produced with no course evidence (Phase 2)
- `course_id` is null on grade import (Phase 2)
- Dual seat source of truth — canonical columns vs. snapshot rows (Phase 4)
- Frontend silently falls back to fixtures when no API base URL is set (Phase 6)

## Workflow

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- `/gsd-plan-phase N` — plan a phase before implementing it
- `/gsd-execute-phase N` — execute a planned phase

If you are not running GSD, still read `.planning/STATE.md` and `.planning/ROADMAP.md`
before changing code, and keep `STATE.md` accurate when you finish.
