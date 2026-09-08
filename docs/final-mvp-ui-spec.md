# Easy-A final MVP UI contract

> **STATUS: PROPOSAL — NOT CONFIRMED SCOPE (annotated 2026-09-08).**
> This document is design thinking from an earlier planning conversation. It is retained as input,
> not as a record of approved decisions. Four of its positions are explicitly **not adopted**:
> email seat alerts as required scope, verified RMP links as required scope, a grade-only scoring
> rewrite, and all offered USF Tampa sections as launch scope. The existing scoring model is
> preserved as the current baseline; alerts and RMP are candidate later phases; broader coverage
> is an expansion target subject to validation.
> Authoritative current scope: `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`,
> `.planning/ROADMAP.md`. Current planning phase is **Sprint 5**.


Status: proposed UI contract for the [final MVP plan](final-mvp-plan.md), September 5, 2026. Implement within the existing React/TypeScript/Vite/Tailwind application. This specifies the finished flows; it is not a rendered design or a claim of visual verification.

## 1. Product hierarchy and visual direction

Primary question: “What do the historical grades look like, and are seats available?” A rate and seat availability should be visible without opening details. Historical grade ease provides a secondary comparison aid. Evidence scope and sample size travel with the numbers.

Keep the existing deep green, warm paper background, dark ink, understated borders and typographic course headings. Use green for available seats, amber for limited/stale evidence, and neutral gray for unavailable data. Every status has a text label; color never carries meaning alone. Reduce decorative texture and excessive uppercase labels where they interfere with reading.

Reuse the existing type stacks and Tailwind tokens. Use a readable sans-serif for body copy and numeric labels, tabular numerals for rates/counts, and the existing display face for course headings. Body text normally 16px; supporting text no smaller than 12px. Use 8px spacing increments, restrained 6–10px corner radii, comfortable row spacing and consistent focus rings. Avoid a giant marketing hero; the useful search appears immediately.

Required surfaces: search/results, linkable section details, methodology/data coverage, watch signup/confirmation, and private watch management. Header navigation stays small: Easy-A, Methodology, Manage alerts. Browsing needs no login.

## 2. Search and results

### Shared controls

Show “USF Tampa” and the selected term. Use configured supported registration terms and a deliberate default from metadata; do not hard-code Spring 2027. Search accepts the existing course-code format, with clear examples and normalized spacing/case. Keep subject, GenEd, modality and open-seats filters; put secondary filters in a collapsible area on mobile.

Sort options: historical grade ease, A rate, withdrawal rate, open seat count and course code. Default to grade ease descending with available evidence, followed by unscored sections without rank numbers. Nulls sort last for ascending and descending numeric sorts; raw A-rate ordering must still show each row's sample size. “Open seats only” requires a fresh valid positive count and compatible source status.

Persist selected term, search, filters, sort and page in the URL. Restoring a link or using Back must restore the result position and filters. Keep server pagination, loading feedback, useful empty states and retry actions.

### Desktop results

Use a compact responsive table with these information groups:

| Group | Visible content |
| --- | --- |
| Course/section | Course code, short title, actual section number, CRN. |
| Instructor | Current name or Staff/unknown. Verified RMP action in detail or a clearly labeled secondary link. |
| A rate | Prominent percentage or “Unavailable”; `A of N A–F grades`. |
| Historical grade ease | One decimal `/10`, with methodology help; “Insufficient data” instead of a number where required. |
| Withdrawals | Observed percentage; denominator explanation accessible on focus/click. |
| Evidence | “This professor + course” or “Course only,” N and term count; limited/insufficient label where needed. |
| Seats/action | Open/full/unknown/stale, count where valid, checked-at time; view details/watch action. |

Move long GenEd labels, policy lists and detailed enrollment breakdowns into details rather than forcing them into an extremely wide table. Preserve modality/GenEd as compact metadata where space allows. Use real header semantics and a table caption. Sorting controls expose current direction.

### Mobile results

Use full-width section cards without horizontal page scrolling. Order: course/section and instructor; prominent A rate plus sample; secondary ease and W rate; evidence scope/terms; seats and checked-at; “View section” and “Email me when a seat opens.” Avoid wrapping the entire card in a button when it contains links or other buttons.

Illustrative content only — these values must come from the API in the real product:

```text
MAC 1105 · College Algebra
Section 001 · CRN 12345 · Example Instructor

A rate 40.0%                    Historical grade ease 7.2/10
40 of 100 A–F grades            Withdrawal rate 9.1%
Course only · 100 A–F grades · 3 semesters

2 seats available · Checked 2 minutes ago
[View section]   [Email me when a seat opens]
```

Do not show a subscribe action that pretends an already-open section is full. For an open section, offer official registration and “Watch for a future opening” with explicit behavior. Unknown/stale sections may be watched, but explain that availability has not been confirmed.

## 3. Section detail

Use a linkable route keyed by term and CRN. A dedicated mobile page and desktop page or drawer can share the same content. A drawer must manage focus and preserve a usable direct URL.

Content order:

1. Course title, term, actual section/CRN, instructor and supported schedule facts; back to results preserves search state.
2. A-rate, historical-grade-ease and withdrawal summaries, each with its own state and short definition. Explain that W uses all recorded outcomes, while A rate uses A–F only.
3. Evidence summary: exact N and T, named semesters, section count, history scope and fallback reason. Show “Course-only history; not specific to this instructor” when applicable.
4. A–F distribution chart plus an always-available accessible table of grade, count and percentage. Use readable labels and a count/percent view switch only if it improves space. List W/I/S/U/O separately below. Do not draw a chart for absent counts.
5. Seat panel: available count/state, capacity/enrollment if valid, waitlist availability separately, absolute and relative checked-at time, refresh status and monitoring cadence. Official registration link and watch action live here.
6. Policies: supported chips with current/historical badges. Expanding a chip reveals the exact evidence quote, named source term, professor/course scope and “Open syllabus” or “View schedule source.” Also show the syllabus link when no chip was extracted.
7. Verified “View on Rate My Professors” action, or a short unavailable label. Do not create a ratings panel, stars, review cards or AI commentary.
8. Compact supporting GenEd/modality facts and link to the method/data coverage page.

Evidence descriptions are ordinary language. Replace student-facing “effective_n,” “global prior,” and “87% rule confidence” with understandable context. Advanced methodology may expose precise formula parameters and reference-cohort details. Avoid putting internal rule scores in prominent product decisions.

## 4. Methodology and data coverage

Provide a permanent `/methodology` page accessible from the header and score help. Explain:

- What historical grade ease measures and the exact grade-only formula.
- A-rate and W-rate denominators, including excluded/included grade categories.
- The small-sample adjustment, measured reference population, prior strength, minimum sample rules and method version/date.
- Why an insufficient score can coexist with observed counts, seats or policy evidence.
- Professor-course versus course-only evidence and the meaning of evidence-strength labels.
- How to read historical policy sources and checked-at seat observations.
- Supported campus/registration terms and actual historical coverage, plus refresh cadence.
- A worked example explicitly labeled synthetic; production course results must use real observations.

Keep the explanation skimmable. The headline formula and denominators cannot be hidden only in a repository README. Historical outcomes do not guarantee an individual's result. Seat observations do not guarantee registration eligibility or reserve a seat.

## 5. Email watch screens

| Screen/state | Required content and action |
| --- | --- |
| Signup | Exact course, term, section/CRN, email field, one-alert behavior, cadence and “Send verification email.” |
| Submitting | Prevent duplicate submission and preserve input while showing progress. |
| Check email | Explain that monitoring activates after confirmation; rate-limited resend, change-email action. |
| Confirmation | Deliberate confirm action for ownership token; clear active/expired/invalid/already-used result. |
| Active | Exact watched section, latest availability/check time, expected cadence, cancel action and how alerts stop after one email. |
| Already open | Say seats are currently reported; offer registration and explicitly described future-opening watch. |
| Completed | “Availability email sent” only after provider acceptance; current seats separately; offer rearm. Do not claim inbox receipt. |
| Manage link request | Email field and generic confirmation that does not reveal another person's subscriptions. |
| Private management | All watches for the verified address, term/CRN, state, cancel/rearm and stop-all action. No public watch lists. |
| Unsubscribed/expired | Clear outcome, no continued sending, optional new watch where registration is still supported. |
| Service failure | Useful retry copy; retain existing state. Never show a successful subscription if creation failed. |

Expired ownership or management tokens offer a new-link flow. Avoid exposing credentials in page titles, analytics or referrer headers. Notification emails use the same clear identity, actual observed seat count/time, official registration and unsubscribe links. Escape all source-derived text.

## 6. Required data and failure states

| State | What the student sees |
| --- | --- |
| No course history | “Insufficient data” for ease, unavailable grade facts, and a clear reason. Independently available seats/policies still work. |
| Small observed sample | Real rates/counts when permitted, “Small sample: N A–F outcomes”; ease unavailable below threshold. |
| No measured reference | Observed rates/counts remain; ease unavailable with an adjustment-reference explanation. |
| W-only outcomes | A/distribution/ease unavailable; observed W rate and denominator remain visible. |
| Suppressed or invalid source | Explicit source limitation, no reconstructed counts or made-up percentages. |
| No professor match | Course-only history and reason; never imply a professor estimate. |
| No current syllabus | Clearly dated historical source if supported, otherwise no policy information. |
| Missing RMP verification | “Verified RMP link unavailable.” No guessed or search-result link. |
| Full/over capacity | Full status; no negative “available” badge. Over-capacity detail only where source values validate it. |
| Stale seat data | “Last known: 2 seats · Checked [time] · Update overdue”; no green live-open badge. |
| Unknown/cancelled seat state | Plain unavailable/cancelled label; do not claim availability based on contradictory counts. |
| API/source outage | Existing valid cached facts only with age/status; error and retry feedback; never synthetic fallback. |
| Empty search/unsupported term | Scope-aware explanation and a useful filter reset or supported-term action. |

## 7. Interaction, accessibility and acceptance

Target 360px, 768px and 1440px layouts and 200% zoom. Use approximately 44px touch targets, readable contrast, persistent visible keyboard focus and reduced-motion support. Tooltips must work on focus/click, not hover alone. Input labels and validation errors must be programmatically associated. Announce meaningful search/watch results without constantly announcing every seat poll.

Charts require grade labels and the text table; neither color nor hover is necessary to understand them. Use safe external links and make opening a new tab predictable. Dialogs/drawers need focus containment, Escape handling and focus restoration. Avoid layout jumps when data loads; keep filters usable during background refresh and ignore outdated responses.

Browser acceptance must demonstrate all five surfaces, all states above, keyboard navigation, an actual frontend-to-API grade result, verified source links, and the complete email management flow. Save desktop/mobile screenshots for representative available, insufficient and stale cases. A generated design image, fixture-only page or passing component test is not a substitute for integrated browser verification.
