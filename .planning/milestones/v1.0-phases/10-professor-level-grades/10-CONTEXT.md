# Phase 10: Professor-level grades - Context

**Gathered:** 2026-09-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Show a named instructor's own grade history for a course, next to the course-wide history, wherever the evidence supports it (REQ-PROF-01). Four scope items from ROADMAP.md: (1) one-time five-term historical backfill of sections/instructors (D-22e), (2) instructor-course scoring retune (D-24, now approved), (3) landmine handling (labs, co-teaching, name collisions), (4) per-instructor UI breakdown.

Success criteria: join coverage re-measured against the DB matches the 2026-09-28 report (3,216 pairs; 1,329 / 2,178 / 2,829 at n >= 60 / 30 / 15); every instructor-level figure shows denominator, term count and source (D-06, D-07).

</domain>

<decisions>
## Implementation Decisions

### Scoring retune (D-24 — APPROVED 2026-09-30)
- **D-01:** User explicitly approves D-24 in full, amending D-02 for instructor-course scoring only: `instructor_course_min_effective_n` 60 -> 30, instructor-level prior strength ~30, single-term flag. PROJECT.md D-24 must be updated from "pending approval" to approved, with a methodology note and tests. — **Reversibility:** costly — changes live ranking output; undo requires reverting constants and rebuilding the ranking cache.
- **D-02:** The single-term flag is **label only**: the score is unchanged; the UI shows a "based on 1 term" chip. No extra shrinkage and no multi-term activation requirement.
- **D-03:** Add a **new named config field** (e.g. `instructor_prior_strength` = 30) beside `grade_prior_strength` (60) and change the `instructor_course_min_effective_n` default to 30. Do NOT lower the shared `grade_prior_strength`; course-level scores must be byte-identical before and after.
- **D-04:** Rollout gate is a **before/after diff report**: rebuild the cache, report which sections changed score/rank and by how much, confirm course-level scores are unchanged, and review it before the change goes live on the hosted beta. No runtime feature flag.

### Historical backfill (D-22e)
- **D-05:** Run as a **one-off CLI script** (reusing `StaffScheduleClient` / `parse_schedule_html` and the existing upsert path), executed by the user against hosted Supabase. Not added to the Render worker; do not touch live-sync change-only/removal semantics.
- **D-06:** Write **only sections whose term+CRN has a `grade_distributions` row**, for catalog courses, for the five terms 202408, 202501, 202505, 202508, 202601 (~8.7k rows rather than the ~27k pulled).
- **D-07:** Guardrails: a dry-run mode that prints counts first; idempotent upserts (re-runnable, no duplicates); historical rows scoped to past term codes so live sweeps never mark them removed; post-run re-measure must match the 2026-09-28 report numbers.
- **D-08:** "Staff"/blank instructor sections are stored as Staff and never matched to a named instructor (they still count toward course-level history as today).

### Instructor breakdown UI
- **D-09:** The breakdown lives **inside the existing `RankingDetails` component** (new "instructors for this course" block, next to course-wide history). No new route/page, no inline table-row stats.
- **D-10:** List **all instructors with enough history** in the course, sorted by n, with the section's current instructor pinned first and highlighted. Instructors below a minimum n (planner to pick, ~15) collapse into "others". For Staff sections this is the "historically taught by..." list.
- **D-11:** For Staff sections the list is **display only** — it never feeds the section's score or rank (no speculative blending).
- **D-12:** Each row shows raw A%, n (grades), term count/range, and the shrunk score used in scoring, plus a "based on 1 term" chip where applicable (e.g. "X. Ou · 40% A · 175 grades · 3 terms (Spr 25–Spr 26)").

### Landmines
- **D-13:** **Laboratory sections are excluded from instructor-level stats** (not counted toward an instructor's pair or score) and **labeled in the UI**: lab sections show course-level history with a note that instructor history is not shown for labs.
- **D-14:** Instructor identity: **within a single course, key by name**; **any cross-course or pooled professor view keys on name + college**. Phase 10 builds no cross-course professor page beyond honoring this rule.
- **D-15:** Co-teaching caveat is a **single InfoTip on the instructor block** ("USF lists one instructor per section; co-taught courses are attributed to the listed instructor"); per-row chips only for single-term and low-n.

### Claude's Discretion
- Exact minimum-n cutoff for collapsing instructors into "others" (~15 suggested).
- API response shape / field naming for the instructor breakdown, cache-rebuild timing, and ordering of backfill vs. scoring rollout (backfill must precede scoring activation since the join needs the section rows).
- Exact config field name, chip/InfoTip copy, and CLI flags.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Decisions and scope
- `.planning/ROADMAP.md` — Phase 10 section (scope, success criteria, REQ-PROF-01)
- `.planning/PROJECT.md` — D-02 (scoring baseline), D-06/D-07 (denominator/term/source display), D-09, D-20, D-21, D-22 (esp. 22e), D-23, D-24 (now approved; update it)
- `.planning/REQUIREMENTS.md` — REQ-PROF-01
- `.planning/STATE.md` — current facts (hosted DB snapshot, sweep behavior)

### Research
- `.planning/research/instructor-grade-feasibility-2026-09-28.md` — pair histogram, coverage numbers, case studies, landmines, operational findings
- `.planning/research/live-sync-and-prof-grades-plan-2026-09-28.md` — sync + professor-grades plan

### Phase 9 (live sync that Phase 10 sits next to)
- `.planning/phases/09-hosted-beta-deployment-ci-observability/09-CONTEXT.md` — sync decisions (change-only writes, removed = marked not deleted)
- `.planning/phases/09-hosted-beta-deployment-ci-observability/09-ROLLOUT-EVIDENCE.md` — hosted beta facts

### Code
- `src/easy_a/analytics/queries.py` — `_fetch_instructor_course_grade_observations`, `_instructor_section_ids`
- `src/easy_a/analytics/scoring.py` — `instructor_course_min_effective_n`, `has_sufficient_instructor_course_evidence`
- `src/easy_a/analytics/grades.py` — `effective_n` definition
- `web/src/components/RankingDetails.tsx`, `web/src/utils/rankings.ts` — UI integration point

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StaffScheduleClient` / `parse_schedule_html`: already used for the 2026-09-28 historical pull and the live sync.
- `_fetch_instructor_course_grade_observations`: join already exists; populating Section/SectionInstructor for grade terms activates it with no query change.
- `ScoreSource.instructor_course` and `has_sufficient_instructor_course_evidence`: existing gate to retune.
- `InfoTip`, `Badges`, `SignalChips`, `CoverageNotice` components for caveats and chips.

### Established Patterns
- Presentation-only labels for D-20 style honesty (e.g. "No letter-grade history — score is a prior").
- Change-only writes and mark-don't-delete for live sync (Phase 9) — backfill must not interfere.
- `RankingEvidence.test.tsx` style tests for evidence display.

### Integration Points
- Ranking cache rebuild (instructor_course scores appear only after backfill + rebuild).
- API ranking-detail response (needs instructor breakdown data) and `RankingDetails.tsx`.

</code_context>

<specifics>
## Specific Ideas

- Row format example: "X. Ou · 40% A · 175 grades · 3 terms (Spr 25–Spr 26)" plus shrunk score, with "based on 1 term" chip.
- Research case studies (CNT 4419, PSY 2012, ENC 1101, MAC 1105) are good fixtures for tests/UAT.

</specifics>

<deferred>
## Deferred Ideas

- Cross-course professor profile page (would need name + college keying) — future phase.
- Blending an expected-instructor score into Staff sections — rejected as speculative.
- Per-instructor full grade-distribution bars — possible later UI enhancement.
- Carry-over from Phase 9 (not Phase 10 scope): WR-03 cadence-floor race before Spring 2027 registration, NEB 0001 failing every sweep, deferred gate-recovery rehearsal, 30 s sweep-duration gap.

</deferred>

---

*Phase: 10-Professor-level grades*
*Context gathered: 2026-09-30*
