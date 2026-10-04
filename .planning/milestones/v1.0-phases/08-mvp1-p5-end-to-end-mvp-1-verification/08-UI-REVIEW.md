# Phase 08 — UI Review

**Audited:** 2026-09-24
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists for this project)
**Screenshots:** Not captured — no Chromium/Playwright available in this environment. Human UAT (08-UAT.md, 2026-09-24) manually verified desktop and mobile rendering and reported pass; this is a code-only review layered on top of that UAT.

**Scope:** Phase 8's only frontend change is plan 08-03 — `describeEvidence()` in `web/src/utils/rankings.ts`, consumed by `web/src/components/RankingTable.tsx` (desktop row + mobile card) and `web/src/components/RankingDetails.tsx` (expanded details). This review audits that change only; pre-existing table/card layout is treated as baseline, not re-litigated, except where the new evidence wording interacts with it.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All four evidence-scope strings are specific, truthful, and fail closed; no generic placeholder copy introduced. |
| 2. Visuals | 3/4 | Evidence note is visually secondary (11px amber text) appended after the primary score — correct hierarchy, but the note is cramped into a `max-w-40` box on desktop next to a large score number. |
| 3. Color | 3/4 | Amber-900/amber-950/amber-800/amber-400/amber-50 all used for warning-adjacent text across the two files — no single consistent "evidence caveat" color token, though all stay within an amber warning family so it reads coherently. |
| 4. Typography | 3/4 | New evidence text sticks to `text-xs`/`text-[11px]` + `font-semibold`, consistent with existing caveat styling, but `text-[11px]` is an arbitrary value outside Tailwind's default scale, repeated 4x in the touched files. |
| 5. Spacing | 2/4 | Desktop evidence note is wrapped in `max-w-40` (160px) inside a table cell that also holds a `text-xl` score — long strings like "No letter-grade history (pass/fail or independent study) — score is a prior" (76 chars) will wrap 5+ lines at 11px in that width, which is disproportionate to the cell's other content. |
| 6. Experience Design | 4/4 | All four evidence scopes (course_history, no_letter_grade_history, subject_fallback, no_course_evidence) are covered on both layouts and in expanded details; unrecognized `score_source` fails closed; 8 component tests lock the behavior in. |

**Overall: 19/24**

---

## Top 3 Priority Fixes

1. **Desktop evidence note is squeezed into a 160px column (`max-w-40`) that also holds the primary easiness score** — long notes (up to 76 characters, e.g. the non-letter-grade wording) will wrap across many short lines at 11px, elongating that table row and visually competing with the `text-xl` score directly above it — widen the note's max-width (e.g. `max-w-56`/`max-w-64` to match the adjacent gened/signals columns) or move it to its own dedicated cell/column so it doesn't force irregular row heights. `web/src/components/RankingTable.tsx:64`

2. **`text-[11px]` arbitrary font size repeated across both touched files instead of `text-xs` (12px)** — introduces a fifth non-scale font size purely for evidence/rank-badge text; consolidate onto `text-xs` (already used elsewhere in the same components) so the type scale stays to the existing set rather than growing with each new feature. `web/src/components/RankingTable.tsx:57,64,66,94`, `web/src/components/RankingDetails.tsx:59`

3. **Five distinct amber shades (amber-900, amber-950, amber-800, amber-400, amber-50) used for evidence/warning text with no single "caveat" token** — makes it harder to guarantee all evidence-adjacent text reads as one consistent warning language as new scopes are added later; standardize on one amber pairing (e.g. `text-amber-900` for all caveat body text, reserve amber-950/amber-400 for the existing historical-reference badge only) and reuse it via a shared class or component rather than inlining per call site. `web/src/components/RankingTable.tsx:64,66,97,99`, `web/src/components/RankingDetails.tsx:26`

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

- `scoreSourceLabel`/`describeEvidence` strings are concrete and non-generic: "No letter-grade history (pass/fail or independent study) — score is a prior", "No course history — score uses {subject} subject-level history", "No historical grades for this course — score is a global prior" (`web/src/utils/rankings.ts:117-160`). No "Submit"/"OK"/"Click here" style generic copy was touched by this plan.
- The fail-closed comment and behavior (unrecognized `score_source` → `no_course_evidence`) is copy-correct: it never invents a false "course history" claim, matching the D-20/D-21 intent stated in the SUMMARY. Verified by `RankingEvidence.test.tsx:169-177`.
- No grep hits for `went wrong`/`try again`/generic `No data` patterns in the touched files — the evidence copy is scope-specific rather than a single reused empty-state string.

### Pillar 2: Visuals (3/4)

- Hierarchy is correct in direction: the primary easiness score stays large (`text-xl`/`text-2xl`, `font-display`) and colored (spruce/stone by confidence), while the evidence caveat is small, semibold, amber — a secondary/tertiary visual weight appropriate for a caveat, not the headline number.
- However the note is bolted directly under a big number inside a narrow, unrelated-width container (`max-w-40` vs. the score's own unconstrained width), which risks it reading as a second stacked "label" rather than a distinct footnote — see Pillar 5 for the concrete metric.
- Expanded details panel presents evidence info cleanly as a `<dt>/<dd>` pair ("Score source", "Effective sample") consistent with the rest of the definition list — no complaint there.
- No icon-only controls were introduced by this plan; `InfoTip` (pre-existing) continues to carry a `label` prop used as accessible name, confirmed by test `RankingEvidence.test.tsx:154-166` querying it via `getByRole("button", { name: "Based on limited historical data." })`.

### Pillar 3: Color (3/4)

- Evidence-adjacent color usage in the two touched files: `text-amber-900` (note, x2), `text-amber-800` (low-confidence label), `border-amber-400 bg-amber-50 text-amber-950` (historical-reference badge, pre-existing but adjacent). That's 4 distinct amber tokens doing "this needs your attention" work.
- All of it is confined to the existing warning/amber family (no clash with the app's spruce/ink/stone palette), so it doesn't blow the 60/30/10 distribution — this is a minor consistency issue, not a brand violation.
- No hardcoded hex/rgb values found in the touched files (`grep -n "#[0-9a-fA-F]\{3,8\}\|rgb("` returns nothing in `RankingTable.tsx`/`RankingDetails.tsx`).

### Pillar 4: Typography (3/4)

- New evidence text uses `text-xs` (details panel `dd`s, mobile note, summary paragraph) and `text-[11px]` (desktop table note, low-confidence label, rank badge, rule-confidence label) — two very close but distinct sizes doing similar caveat work.
- `text-[11px]` is an arbitrary Tailwind value (not on the default scale) and was already present pre-phase for the rank badge — this plan's contribution (`evidence.note` on desktop, `65` char string) inherits and extends that pattern rather than introducing a wholly new one, but it does add more instances of an off-scale size.
- Font weight stays consistent (`font-semibold`/`font-bold`) for all new caveat text — no weight sprawl introduced.

### Pillar 5: Spacing (2/4)

- `web/src/components/RankingTable.tsx:64` — the desktop `evidence.note` span is `mt-1 block max-w-40 text-[11px]`. `max-w-40` = 10rem = 160px. The longest note string is 76 characters ("No letter-grade history (pass/fail or independent study) — score is a prior"); at 11px in a 160px-wide block this wraps to roughly 5-6 lines, while every sibling cell in that row (instructor, W rate, confidence, seats) is one or two lines. This will materially inflate that table row's height whenever a non-letter-grade or global-prior row is rendered, which is now a first-class scope this plan explicitly introduces (not an edge case) — worth a real width increase, not just accepting the wrap.
- Neighboring cells in the same row use wider constraints for comparable prose (`max-w-48` for instructor, `max-w-52` for course title, `max-w-60` for gened, `max-w-64` for signals) — `max-w-40` for the evidence note is the narrowest of the set despite carrying some of the longest strings, an inconsistency introduced by this plan.
- Mobile card and details panel don't share this problem — the mobile note (`RankingTable.tsx:97`) has no width constraint (full card width) and the details panel note (`RankingDetails.tsx:91`) sits in its own paragraph with no max-width — the defect is isolated to the desktop table cell.

### Pillar 6: Experience Design (4/4)

- All four evidence scopes are exercised across both layouts (desktop row, mobile card) and both details regions by `RankingEvidence.test.tsx` (8 tests): course_history (with and without low-confidence explanation), no_letter_grade_history (effective_n=0 course), subject_fallback (named subject), and no_course_evidence (global effective_n=0, global effective_n=22, subject effective_n=0 falling closed, and an unrecognized `score_source` falling closed) — `web/src/components/RankingEvidence.test.tsx:28-177`.
- Fail-closed behavior is explicitly tested (`score_source === "unheard_of_source"` still renders the global-prior wording, never course-level history) — this is the correct defensive default for a scoring transparency feature.
- Negative assertions are present, not just positive ones: tests confirm "Course-level history", "0 grades", and the course-history low-confidence tooltip button are absent when they shouldn't render — this is above-average rigor for state coverage and catches the exact "quietly implies course history when there is none" failure mode this plan exists to prevent.
- Human UAT (08-UAT.md) independently confirmed rendering at desktop and mobile widths passed with no reported truncation/overlap, which corroborates the automated coverage for visual states this code-only review cannot directly observe.

---

## Files Audited

- `web/src/utils/rankings.ts` (describeEvidence, scoreSourceLabel)
- `web/src/components/RankingTable.tsx` (desktop row, mobile card)
- `web/src/components/RankingDetails.tsx` (expanded details)
- `web/src/components/RankingEvidence.test.tsx` (test coverage cross-check)
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-03-SUMMARY.md`
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-03-PLAN.md`
- `.planning/phases/08-mvp1-p5-end-to-end-mvp-1-verification/08-UAT.md`
