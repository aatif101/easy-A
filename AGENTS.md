# Agent Instructions — Easy-A

Entry point for any AI coding agent working in this repository. Everything needed for ordinary
continuation is in the repo — you should not need prior conversation context.

## ⛔ Step 0 — before you write anything, check what is already in flight

**Run this first, every session, no exceptions:**

```bash
uv run python scripts/project_status.py
```

It fetches the remote and reports every unmerged branch, who owns it, what files it
touches, and whether two branches are building the same thing. Exit code `0` means clear,
`1` means work is in flight, `2` means duplicate work is already underway.

**The planning files below describe the last *merged* state. They are stale by exactly the
work sitting in open pull requests.** When `project_status.py` and `.planning/STATE.md`
disagree, the branches are right and the planning file is out of date.

This step is not optional bookkeeping. On 2026-09-10 two contributors each built complete,
independent Tampa-cleanup tooling — same four file paths, same CLI design — because the
second one read `main`, where `STATE.md` correctly said no such tooling existed, while the
first one's finished implementation sat unmerged in PR #17. Both followed the documented
process. The process was missing this step.

If the report shows someone already doing your task: **stop, read their branch, and tell
the user.** Build on their work or merge it. Do not write a second version.

## Read first, in this order

0. **`uv run python scripts/project_status.py`** — live state; outranks every file below
1. **`AGENTS.md`** (this file) — constraints and orientation
2. **`.planning/STATE.md`** — current position and the next action *as of the last merge*
3. **`.planning/PROJECT.md`** — scope, decisions, open questions
4. **`.planning/ROADMAP.md`** — phase sequence and backlog
5. **`README.md`** — as needed, for commands and local setup

## Current state

Easy-A is a **working application**, not a prototype and not a greenfield build. FastAPI backend,
React/TypeScript frontend, PostgreSQL, real Spring 2027 schedule ingestion, real historical grade
imports, configurable course coverage, and seat freshness classification.

| | |
|---|---|
| Baseline | `origin/main` = `62fb2f189c8cac67a1500863f080e0f638469df1` |
| Sprint 5 | ✓ **Complete** — merged via PR #14 and PR #15. Do not re-plan or re-implement it. |
| PR #16 | ✓ **Merged** — pins `campus="T"` and rejects non-Tampa rows before ingestion |
| Real-data validation | ✓ **Complete** (2026-09-09) — five targets verified, **75 Tampa sections** |
| **Now** | ⛔ **Tampa-only data correction — BLOCKING.** 47 non-Tampa rows still stored. |
| Then | Historical grade imports for AMH 2020 → PSY 2012 → BSC 1005 |
| Then | Hosted beta — deployment, CI, performance measurement, observability, runbook |

Fetch and verify current `origin/main` before planning rather than trusting the SHA above.

### ⛔ Current blocker — read before touching data

The first expansion pass ran before the campus-scope bug was found: configured refresh queried all
campuses and inserted **47 non-Tampa Spring 2027 sections** into the beta database. PR #16 fixed
the cause but **did not remove the rows** — its merged description says they "remain visible in
stored coverage/API counts until a separately reviewed cleanup."

**Stored counts, API counts and `GET /api/v1/metadata/coverage` counts are therefore still
contaminated and do not equal 75.** Any coverage figure read from the running database today is
wrong. No section-deletion tooling exists in `scripts/` — the cleanup has to be written and
reviewed.

The cleanup must record: rows removed and the criteria used; final Tampa-only stored counts;
final API counts; final coverage-endpoint counts; and explicit confirmation that **no historical
grades and no Tampa sections were deleted** (237 grade rows and all 75 Tampa sections intact).

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

75 is the *verified* Tampa count, not the *currently stored* count — see the blocker above.

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
- **Claim work by pushing, before you build it.** Branch from verified `origin/main` using the
  lane that matches the area (`dev1/*` backend and data, `dev2/*` frontend `web/`), then push
  that branch immediately — a stub or failing test is enough. A pushed branch is visible to
  everyone's `project_status.py`; an unpushed branch is invisible, and invisible work gets
  built twice. Open a draft pull request as soon as there is anything to look at.
- **Never end a session without recording it.** Update `.planning/STATE.md` — position, next
  action, and what is in flight — and push. Prefer a separate docs-only pull request for that
  update so it reaches `main` without waiting on code review; a state update trapped inside an
  unmerged feature branch is invisible, which is precisely how the duplicate work above
  happened. Distinguish **written** from **run**: tooling that exists but has never executed
  must say so.

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

- **47 non-Tampa sections stored** — the current blocker, above (REQ-DATA-02)
- **No historical grades for AMH 2020, PSY 2012, BSC 1005** — global fallback, `effective_n = 0`
  (REQ-GRADES-01)
- **Search performance unmeasured at widened coverage** — `GET /api/v1/rankings/search` ranks
  sections before slicing pagination; Phase 1 did not measure it (REQ-PERF-01)
- **Blank grade-cell / suppression semantics** — `src/easy_a/grades/parser.py` converts every
  blank cell to `0` with no suppression path. Needs a real or sample InfoCenter export nobody
  currently has.
- **Deployment host and domain** not yet supplied.

Fixed, do **not** re-plan: silent frontend fixture fallback, missing seat freshness contract,
absent PostgreSQL integration coverage, hard-coded Spring 2027 term preference (all Sprint 5);
configured refresh querying all campuses (PR #16 — cause fixed, rows still need cleanup).

Confirmed healthy by the validation run: zero data-quality errors across 202408 / 202501 / 202508
/ 202701; seat refresh preserved previous snapshots, section identity and all 237 grade rows;
frontend and API verification passed with no console errors.

## Workflow

### Starting and ending a session

Every session opens and closes the same way, whatever tool you are using:

| | Claude Code | Any other agent, or a human |
|---|---|---|
| **Start** | `/resume-work` | `uv run python scripts/project_status.py`, then follow Step 0 above |
| **End** | `/wrap-up` | update `.planning/STATE.md`, push, open or update the pull request |

`/resume-work` and `/wrap-up` live in `.claude/commands/`. They are thin wrappers around the
rules in this file — if you cannot run slash commands, read those two files and do what they
say, because the obligations are identical.

Say **"resume work"** and the expected behaviour is: check live state first, report anything
already in flight, and only then pick up the next action.

### GSD planning

This repo uses GSD. Planning artifacts live in `.planning/`, not `.gsd/`.

- `/gsd-progress` — check state and get the next action
- `/gsd-plan-phase 2` — plan Phase 2 (Tampa-Only Data Correction), the current work. **Not
  Sprint 5 and not Phase 1** — both are already complete.
- `/gsd-execute-phase N` — execute a planned phase

GSD commands do not replace Step 0. Run `project_status.py` before any of them — GSD reads
the planning files, and the planning files do not know about unmerged branches.

If you are not running GSD, read `.planning/STATE.md` and `.planning/ROADMAP.md` before changing
code, and keep `STATE.md` accurate when you finish.
