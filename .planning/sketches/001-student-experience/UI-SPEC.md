---
status: direction_selected_pending_final_spec_review
date: 2026-09-25
sketch: 001
winner: "A"
selected_by: user
selected_on: 2026-09-25
production_implementation: not_started
---

# Student guide — selected design direction

The user selected **A — Student guide** on 2026-09-25. This revision makes A the baseline for
refinement and retains B as a comparison, not a competing implementation target. The selection
approves the visual direction; final specification review and the actual-student walkthrough
remain open. All PROJECT.md constraints continue to apply.

## Purpose and hierarchy

Help a student answer: what is this class, how did students do, how much evidence supports that,
and which current section should I inspect? Known-course lookup and open-ended discovery have
equal visual prominence. The page shows one result per course, then current section choices.

Order: identity/term → short introduction → course search and exploration → visible course-level
filter and optional filters → results with explicit sort → course evidence → grades → sections.
Student-facing copy avoids “effective sample,” “W rate,” “API mode,” and implementation terms.

## Visual contract

| Item | Proposal |
|---|---|
| Surface | White `#ffffff`, light neutral `#f5f7f5` for search and expanded evidence |
| Text | `#182f26`; secondary `#526259` |
| Actions | Green `#176348`, hover `#104c36`; visible 3px focus outline |
| Limited history | Text `#77500c` on `#faf3e3`, beside the outcome claim |
| Dividers | `#d4dcd7`; no decorative shadows or floating metric cards |
| Type | Local Segoe UI / Helvetica Neue / Arial sans-serif; no external font fetch |
| Body | 1rem, 1.5 line height; secondary 0.875rem; tabular outcome numerals |
| Headline | 1.75–2.375rem; course names 1.3125–1.375rem in guide |
| Rhythm | 4/8/12/16/24/32px spacing; 44px minimum controls |
| Content | 1,112px outer max width, 32px desktop gutters, 20px phone gutters |
| Responsive | Single-column search and summaries at ≤680px; content-driven wrapping |
| Motion | Short color feedback only; reduced-motion turns transitions off |

**A: Student guide.** Course identity and evidence are the main reading path. The observed
percentage aligns to the right on desktop and precedes the denominator on phones. A clear
outlined disclosure action follows the evidence. **Selected by the user for refinement.**

**B: Compact comparison (retained alternative).** Desktop summaries use identity/evidence/outcome columns, tighter
vertical spacing, and a supplementary A–F distribution strip. Direct text labels give the share
for each grade; no hover or color decoding is required. On phones it becomes one column, so
the strip uses extra vertical space. The list disclosure looks like an underlined action.

Both use the same data, search controls, sort, detail contents and section behavior. Preserve both
alternatives for reference. A is the selected direction; do not silently mix B into A.

## Search, discovery and results

- Discovery defaults to **1000–2000 level**, visibly removable; restoring it is one click.
- Direct name/code search covers any course level. While a query exists, show “Searching all
  course levels” in place of the discovery chip. Clearing search restores the prior discovery level.
- Enter or Search moves focus to the results heading. Typing updates the small local preview.
  Production search should debounce requests, cancel stale responses, and announce result counts.
- Selecting Explore starts discovery by clearing the query. GenEd uses recorded course attributes,
  never inferred degree eligibility. “Browse all electives” means browsing subjects/courses, not
  promising applicability to a student's program. Review this wording during student testing.
- “More filters” reveals course level and recorded class format. A format filter matches courses
  having at least one such section and shows only matching sections inside the course.
- Native select controls expose active **Easy-A score**, **Course name**, or **Most grade history**
  sorting. “How ranking works” explains score vs observed A share without an obstructive modal.
- Proposed course sorting uses existing course-level analytics, not the best individual section's
  score. Courses without their own letter-grade evidence appear last for score sorting. This is a
  proposed presentation policy for review; no score formula or fallback logic changes.
- Empty state gives a useful sample search and a single reset action. Reset returns focus to search.
  The prototype names its eight-course scope; production replaces that note with genuine totals.

## Evidence contract

For course-backed letter-grade history, display rounded `A / (A+B+C+D+F) × 100`, labeled
“A grades.” Immediately give the exact numerator and denominator, historical section count,
named source, and first/last observed historical term. These are raw observed aggregates, not
Bayesian estimates. Rounded distribution percentages need not sum to 100.

Use the frozen confidence classification: `low` → “Limited history” beside the claim, with the
actual denominator visible. The expanded view describes moderate/substantial evidence without
suggesting a personal prediction. Do not introduce a new scoring or confidence threshold.

No imported rows → **Grade history unavailable**, no percentage. Non-letter-only course rows
must likewise suppress an A share and state **No recorded A–F grades**, showing the available
non-letter outcomes in detail. A subject/global/prior fallback is never course history. The latter
non-letter and suppressed-data cases are production requirements, not demonstrated real examples
in this eight-course snapshot. Never assert upstream suppression merely because data is missing.

Expanded evidence shows:

1. Course-wide history and its period; explicit grade counts and percentages.
2. Existing calculated Easy-A score with grade/withdrawal and shrinkage explanation.
3. Withdrawals with their separate all-outcomes denominator; incomplete, satisfactory,
   unsatisfactory and other outcomes separately named; import date and source.
4. A clear distinction from instructor evidence. Only show an instructor-specific claim when
   its identity mapping and evidence meet the existing backend rules.

No seats, modality, GenEd, or syllabus signal affects scoring. Nothing predicts the student's grade.

## Section journey

“See grades & N sections” is a native disclosure on both desktop and phone. Opening preserves
the student's place and reveals grades before current section choices. Closing returns to the same
course. There is no dialog focus trap or desktop-only click target.

Each section shows term + CRN, section number, named instructor or **Instructor not yet named**,
exact recorded modality label or unavailable state, seat count with observation date/staleness,
and schedule provenance/date. Negative counts remain honest over-capacity observations.
Unknown seats never become zero. Quoted schedule notes are labeled as schedule notes, never
presented as syllabus policy; missing syllabus evidence is stated concisely.

A radio choice keeps the CRN visible in a confirmation block. **Copy CRN** has visible success
feedback, with a manual-copy fallback when clipboard access fails. Selection reserves nothing and
does not register the student. No account, saved list, email alert, RMP, or auto-registration feature.
A future official-registration link must use a verified destination; none was guessed for the sketch.

## Production data support after approval

The current section search API cannot implement these course results by grouping a returned page.
Plan an additive course search response and complete course-section retrieval within the existing
FastAPI/SQLAlchemy and React/Vite architecture:

| Requirement | Contract to establish |
|---|---|
| Course identity | Exact normalized subject/number; join catalog editions carefully; preserve suffixes |
| Search | Case-insensitive title and normalized code search, any level for direct lookup |
| Pagination | Filter/count/order distinct courses before paging; stable course-code tie break |
| Section choices | Complete term+CRN list or independent section pagination with true total |
| Observed outcomes | All ten counts, A–F denominator, all-outcome denominator, section/term counts |
| Evidence scope | Course vs instructor-course vs no course history; no substituting subject counts |
| Provenance | Source identifier(s), source selection/dedup policy, first/last observed term, import date |
| Score | Reuse existing analytics/confidence, separate from raw percentage; no formula rewrite |
| Filters | Level, recorded GenEd, section format with correct course totals and section counts |
| Availability | Existing seat snapshot/freshness fields and successful observation timestamp |

Protect term/CRN/source uniqueness and existing endpoints. Course aggregates should be computed
in bounded batch queries or cache reads, not an N+1 per course. Use the same evidence window for
counts and score. The exporter establishes only that the sample has no overlapping sources;
production must define fail-closed source handling for the whole dataset. Keep existing scoring
parity tests and remeasure course-search p95 at full hosted scale after implementing the endpoint.

Production UI also needs real loading, API error/retry, stale-request cancellation, and paginated
results. The preview's state selector and static sample are review utilities, not production controls.
Do not ship the snapshot or its design-sample count as a live data path.

## Approval and validation

Browser evidence and the self-critique live in `REVIEW.md`. A brief walkthrough with actual
freshmen/sophomores is still required before claiming comprehension or calling the experience
intuitive. Direction selection is complete: the user chose A. Further critique and final
specification review should work from A rather than reopening the alternatives. No specific
screen changes accompanied the selection, so the verified A layout is preserved.

Focus further refinement on the selected experience: comprehension of the score sort despite
small samples, elective/requirement wording, and long section lists. The proposed API and
production loading/error/pagination work remains a later implementation task.
