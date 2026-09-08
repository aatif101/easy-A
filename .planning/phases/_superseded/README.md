# Superseded phase artifacts

Planning artifacts produced under a roadmap structure that has since been replaced. Kept because
several contain real measurements and verified code findings that remain accurate. **Do not
execute the plans in here** — they target a phase sequence that no longer exists.

## `01-baseline-scope-and-contracts/`

Superseded 2026-09-08.

Produced for "Phase 1: Baseline, Scope and Contracts" of an eight-phase greenfield MVP roadmap.
That roadmap was built from handoff documents that recorded email alerts, verified RMP links, a
grade-only scoring rewrite and campus-wide launch coverage as confirmed, locked scope. None of
those was actually confirmed. The roadmap was restructured to the real project sequence — Sprint 5,
then hosted beta — and these plans went with it.

### Why each file is superseded

| File | Why |
|------|-----|
| `01-01-PLAN.md` | Built a "method v2 contract" for a scoring rewrite that is not approved scope |
| `01-02-PLAN.md` | Campus-wide subject-enumeration inventory, premised on all-Tampa launch scope |
| `01-03-PLAN.md` | Syllabus coverage inventory feeding a deferred RMP/policy phase |
| `01-04-PLAN.md` | UI/API state matrix and requirement coverage against the old requirement set |
| `01-05-PLAN.md` | Launch coverage manifest and restatement of an old "Phase 3" exit criterion |
| `01-CONTEXT.md` | Phase context captured against the old scope |
| `01-UI-SPEC.md` | UI contract covering alert flows that are not current scope |

### What is still accurate and worth reading

- **`01-RESEARCH.md`** — contains directly executed measurements, not inference:
  - **166 Python tests and 19 frontend tests passing**, measured by running the suites in this
    worktree on 2026-09-08. All Python tests run on SQLite; PostgreSQL was unreachable.
  - `origin/main` re-fetched and confirmed at `06634490` with no drift.
  - `StaffScheduleClient` and its CLI hard-require `--subject` or `--crn` — there is no bulk-query
    capability. `SimpleSyllabusClient` fetches only one already-known document ID, with no search
    or enumeration. Any broader coverage work has to account for this.
  - `src/easy_a/grades/parser.py` converts every blank cell to `0` unconditionally, with no
    suppression-marker path. Resolving this needs a real or sample InfoCenter export.
  - `src/easy_a/analytics/confidence.py`'s 60/180 thresholds operate on `effective_n`, which
    equals the observed A-F count only while recency weighting is disabled — an undocumented and
    untested equivalence.
- **`01-PATTERNS.md`** — analog map for code-touching work. Notably: a net-new bounded HTTP
  fetcher should copy `src/easy_a/syllabi/client.py`'s host-pin and regex-validation pattern
  rather than `src/easy_a/catalog/client.py`'s unvalidated fetch. New query objects should follow
  `src/easy_a/schedule/client.py`'s frozen-dataclass-with-validation shape.
- **`01-VALIDATION.md`** — the measured test baseline and its SQLite-only caveat.

Current planning lives in `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` and
`.planning/PROJECT.md`.
