---
description: Close an Easy-A session so the next person — or the next agent — can resume from it without guessing.
---

# Wrap up an Easy-A session

The next person to open this repo will read what you leave behind and trust it. If you
leave nothing, they will start from the last merged state and rebuild what you just did.
That has already happened once on this project.

Run every step. Leaving the work pushed but unrecorded is the specific failure this
command prevents.

## 1. Push what you have, finished or not

```bash
git push -u origin <your-branch>
```

Unfinished work still belongs on the remote. A pushed branch is a visible claim; an
unpushed one is invisible, and invisible work gets duplicated.

## 2. Open or update the pull request

If no pull request exists for the branch, open one now — **draft if the work is
incomplete**. The title should say what the work *is*, and the body must answer three
questions explicitly:

1. **What is done** — and what is written but **not yet run**. These are different, and
   conflating them is how this project ended up with cleanup tooling nobody had executed.
2. **What is left** — the next concrete action, specific enough to act on without you.
3. **What it touches** — the files and areas, so the overlap check can see it.

## 3. Update `.planning/STATE.md`

Edit these sections to match reality:

- **Current Position** — which phase, and its real status
- **Next Action** — the next concrete step. Write it for someone who was not here. If
  the next step is *"review and merge PR #N"* rather than *"build X"*, **say that**, because
  a reader who sees "build X" will build X again.
- **Session Continuity** — today's date, what you stopped at, what is in flight and where

Be exact about the written-versus-run distinction. If you wrote tooling and never executed
it, `STATE.md` must say the tooling exists and has not been run. Never record a measured
number you did not measure.

## 4. Keep the state update out of the feature branch when you can

`STATE.md` edits that ride inside a feature branch stay invisible until that branch merges.
On 2026-09-10 that is exactly how a second person read "no such tooling exists" on `main`
and spent a session rebuilding tooling that already sat in an open pull request.

So prefer a **separate docs-only branch and pull request** for the `STATE.md` update, which
can merge immediately without waiting on code review:

```bash
git stash                                          # if needed
git checkout -B docs/state-$(date +%Y%m%d) origin/main
# edit .planning/STATE.md only
git add .planning/STATE.md && git commit
git push -u origin docs/state-$(date +%Y%m%d)
```

If the state update genuinely belongs with the code, keep it in the feature branch — but
then say so in the pull request body, so the next reader knows `main` is behind.

## 5. Verify the loop actually closed

```bash
uv run python scripts/project_status.py
```

Read the output as a stranger would. Your work must appear in the in-flight list, and the
next action must point at the real next step. If a newcomer reading this output would
redo what you just did, the text is wrong — fix it now.

## 6. Report to the user

Tell them plainly: what landed, what is pushed but unmerged, what is written but unrun,
what the next action is, and anything another person must decide before work continues.
