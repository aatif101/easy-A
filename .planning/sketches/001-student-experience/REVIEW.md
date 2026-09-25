# Visual review and acceptance record

**2026-09-25 — user selected A: Student guide.** This records the visual direction choice;
final specification review and actual-student comprehension testing remain open.

User response: “A — Student guide (recommended).” No specific screen changes accompanied
the selection. A is now visibly marked as selected in the review workspace; B is preserved.

## Concrete review

Open `index.html`, switch between A and B, then select Phone and each journey state. Use
`comparison.html` for before/after captures. The actual current application begins its first
course at **y=1085.75px** on a 390 × 844 viewport. Both proposals begin their first course at
**y=549.08px**, with the A percentage and denominator visible on the first screen. A also fits
the first course's complete disclosure action. Measurement excludes review-workspace controls.

| Question | A: Student guide | B: Compact comparison |
|---|---|---|
| Can I understand a course quickly? | Course name, percentage, then plain evidence sentence | Same evidence, arranged into more desktop columns |
| Can I compare grade distributions? | Full counts in expanded view | A–F strip and labels in every course summary |
| Does the phone feel manageable? | First course and action fit without scrolling | Strip and legend add height; first action can require scrolling |
| Is limited evidence obvious? | Label beside percentage, exact denominator underneath | Same treatment; denser desktop column needs enough label width |
| Is the next step apparent? | Outlined “See grades & N sections” | Underlined action; quieter but slightly less emphatic |

**Selected direction:** A provides a clearer first-visit reading order. Keep B available for reference;
its strip may help students who already know what grade distributions mean. A possible synthesis
is A's summaries with a distribution strip only after opening the evidence. That synthesis has not
been selected or built as a third variant.

**Tradeoffs still worth reviewing:**

- Sorting by the frozen score can put small samples near the top (MVJ 1111 is a real example).
  Labels make that uncertainty visible; they do not fix a student's possible ranking inference.
  Do not silently add a new scoring threshold to address this design concern.
- “Browse all electives” needs student comprehension testing; it must not imply program eligibility.
- Forty-one ENC 1101 sections make a long expanded list. A production section search/pagination
  pattern needs planning, with correct totals and complete retrieval, not silent truncation.
- The eight-course sample tests visual states, not full-catalog diversity or production latency.
- With no named instructor evidence in this sample, a future instructor-specific presentation
  remains unvalidated. Existing attribution rules remain authoritative.

## Acceptance evidence

Browser: existing local Chromium 1243 via Playwright, loopback static preview. Verification recorded
in `verification.json` at **2026-09-25T20:04:33.803Z**. Screenshots were inspected for discovery,
expanded grades, compact comparison and limited evidence. No production test baseline was changed.

| Check | Result and limit |
|---|---|
| Phone first screen includes both paths and useful course evidence | PASS at 390 × 844, both variants; A also includes the first action |
| Percentage has a visible denominator without help | PASS in every evidence-backed card; raw count arithmetic reconciled with API |
| Find MAC 1105 by name or code; locate CRN | PASS; five complete current sections, keyboard selection and clipboard round trip |
| Course history distinguished from instructor history | PASS in expanded copy; no fabricated instructor attribution |
| Limited/unavailable claims | PASS, real MVJ 1111 and CAI 1000; missing history has neither percentage nor course score |
| Search at any level | PASS with THE3111 while discovery defaults to lower levels |
| GenEd, level, format and sort | PASS; MAC format filter correctly yields four CL sections out of five total |
| Empty recovery | PASS; reset clears search/filters, restores discovery and focuses search |
| Keyboard and focus | PASS for expand/collapse, visible focus and logical native controls; no hover-only interaction |
| Responsive reflow | PASS at 320, 375, 390, 768, 844 and 1440px, including landscape |
| Enlarged text | PASS at 200% root font size on 390px section view; no horizontal page overflow |
| Reduced motion | PASS; transitions become zero-duration |
| Contrast/semantics automation | PASS: 28 state/viewport axe runs, no WCAG A/AA violations detected |
| Browser console/runtime | PASS: no detected errors |
| Before/after | PASS: real current app and both alternatives at 1440 × 1000 and 390 × 844 |
| Student comprehension | PENDING actual freshmen/sophomores; automation cannot prove this |
| Visual direction selection | COMPLETE: user chose A, Student guide, 2026-09-25 |
| Further refinement and final specification review | OPEN; use selected A, no repeat direction-selection gate |

The browser check found and prompted a text-enlargement fix: search grid tracks needed a zero
minimum width. Decorative chart bars are omitted from the narrow expanded grade table so its
explicit counts and percentages reflow. Body typography uses rem units for text enlargement.
The compact uncertainty label's column was widened to keep its wording easy to read.

## Brief actual-student walkthrough

Recruit 3–5 consenting USF freshmen/sophomores. No outreach was sent and no participants were
simulated. Do not collect grades, identifiers, or account information. Use a phone and alternate
the order of A/B across participants to reduce first-seen preference bias. Allow about 10 minutes.

1. From discovery: “What can this page help you decide? Show me a class you would investigate.”
   Observe their route without teaching them the controls.
2. “Find College Algebra. In your own words, what does 48% mean? Where did that number come from?”
   Success: describes 1,534 As among 3,200 past A–F outcomes, not a personal probability or score.
3. “How much history is behind it? Does this tell you about your current instructor?”
   Success: locates course-wide period/sections and distinguishes instructor evidence.
4. “Show me a section's CRN so you could find it in registration.”
   Success: opens details, chooses a section, identifies/copies the CRN without help.
5. Show MVJ 1111 and CAI 1000: “What can you conclude from each? Which would you trust more, and why?”
   Success: notices the five-grade sample; does not interpret unavailable as 0% or a bad course.
6. “Find a class for a requirement. Does this mean you qualify to take it?”
   Success: treats GenEd/level as discovery, checks prerequisites separately.
7. Switch designs: “Which makes those tasks clearer? What would you change?”

Record anonymous participant labels, task completion/help needed, exact comprehension mistakes,
and A/B preference. Do not invent timing or satisfaction scores. Any recurring confusion about
denominators, course-vs-instructor evidence, missing history or eligibility requires revision and
a repeat walkthrough. Report observations as a small qualitative study, not population proof.

## Selection handoff

A is selected and marked in the workspace, README, manifest, and specification. Preserve its
verified layout until concrete critique or the student walkthrough identifies a change. Carry
forward the remaining long-list, eligibility-wording and score-comprehension questions above.
Final specification review should assess A and its refinements, not ask the user to select A/B again.

Selection follow-up verification (2026-09-25): browser check passed for the selected A marker,
A/B switching, 390px review viewport and expanded MAC 1105 grade state; no runtime errors.
The student-facing prototype is unchanged, so its existing 28-render verification remains applicable.
