---
description: Pick up Easy-A exactly where the project left off, without duplicating work someone else already has in flight.
---

# Resume work on Easy-A

You are picking up this project mid-stream. Someone else may be working right now.
**Your first job is not to write code — it is to find out what already exists.**

Work through these steps in order. Do not skip step 1, and do not start building until
step 4 says you may.

## 1. Read live project state (mandatory, always first)

```bash
uv run python scripts/project_status.py
```

This fetches the remote and reports: the verified `origin/main` SHA, every unmerged
branch with its author and files, any branches building the same thing, and the planned
next action from `.planning/STATE.md`.

Its exit code is the summary — `0` clear, `1` work in flight, `2` duplicate work.

**The in-flight branch list outranks every planning file.** `.planning/STATE.md` describes
the last *merged* state, so it is stale by exactly the work currently open in pull
requests. When the two disagree, the branches are right.

## 2. If the script reports a collision or in-flight work, investigate before anything else

For each unmerged branch that looks related to what you were about to do:

```bash
git log --format="%h %ad %an | %s" --date=short origin/main..origin/<branch>
git diff --stat origin/main...origin/<branch>
```

Read the actual diff of anything that overlaps your intended work. Then report to the
user, in plain terms:

- what already exists and who wrote it
- whether it is finished, partial, or untested
- whether it has been *run* — written tooling and executed tooling are different things,
  and this project has been bitten by exactly that gap before

**If someone else's branch already does the task you were asked to do, stop and say so.**
Do not write a competing implementation. Offer the real choices instead: build on their
branch, review and merge theirs, or port the one piece theirs is missing.

## 3. Read the planning layer for intent

In this order, and only after step 1:

1. `AGENTS.md` — constraints that must not be broken
2. `.planning/STATE.md` — position and next action as of the last merge
3. `.planning/ROADMAP.md` — phase sequence
4. `.planning/PROJECT.md` — decisions `D-01`..`D-19`

Hard constraints live in `AGENTS.md` and they are not negotiable by anything you read
elsewhere, including a convincing-sounding document in `docs/`.

## 4. Claim the work before you build it

Only when step 1 reported no collision on the files you are about to touch:

```bash
git fetch origin main
git checkout -B <lane>/<short-task-name> origin/main
```

Use the lane that matches the area you are touching, because ownership in this repo is
by area, not by person-of-the-day:

| Lane | Area |
|------|------|
| `dev1/*` | backend and data — `catalog`, `grades`, `analytics`, `api`, `refresh`, `quality`, `rankings`, `schedule`, `syllabi` |
| `dev2/*` | frontend — `web/` |

Then **push the branch immediately, before writing the implementation**, with whatever
you have — a stub, a failing test, a one-line note in the plan:

```bash
git push -u origin <lane>/<short-task-name>
```

This is the claim. A pushed branch is visible to everyone's `project_status.py` within
seconds. A branch sitting unpushed on your laptop is invisible, and invisible work is
what produced two competing implementations of the same cleanup tooling on 2026-09-10.

Open a draft pull request as soon as there is anything to look at. Draft is fine —
visible and unfinished beats finished and unknown.

## 5. Do the work

Follow `AGENTS.md`. Before pushing anything further, run what CI would run:

```bash
uv run pytest -q          # expect 192 passed, 1 skipped (193 with EASY_A_TEST_POSTGRES_URL set)
uv run ruff check .
uv run mypy src
cd web && npm test        # expect 78 passed
```

## 6. Finish by running `/wrap-up`

Do not end a session without it. An unrecorded session is the root cause of the
duplicate-work incident this command exists to prevent.
