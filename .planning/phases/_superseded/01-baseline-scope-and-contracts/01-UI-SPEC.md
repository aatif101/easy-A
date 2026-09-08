---
phase: 1
slug: baseline-scope-and-contracts
status: draft
shadcn_initialized: false
preset: none
created: 2026-09-08
---

# Phase 1 — UI Design Contract

This adapts the existing `docs/final-mvp-ui-spec.md` into the Phase 1 contract. It is a specification, not a rendered design, implemented feature, or record of browser verification. Preserve the inherited visual direction and five surfaces. Phase 1 produces traceable UI/API states, methodology and coverage contracts; feature screens are implemented in Phases 2–5 and integrated in Phase 6.

## Design System

| Property | Value |
|----------|-------|
| Tool | none; retain the existing manual Tailwind design system |
| Preset | not applicable |
| Component library | Existing React components; no third-party component library detected in `web/package.json` |
| Icon library | None declared in `web/package.json`; retain existing text controls; no icon dependency required for this contract |
| Font | Body: Aptos, Segoe UI, sans-serif. Course headings: Charter, Bitstream Charter, Cambria, serif. Existing optional technical stack: IBM Plex Mono, Cascadia Mono, monospace |
| Token source | `web/tailwind.config.ts` and `web/src/styles.css` inspected 2026-09-08; the `.js` configuration path does not exist |
| Existing patterns | `FilterBar`, `RankingTable`, `RankingDetails`, `SignalChips`, `Badges`, `InfoTip`; adapt in later owning phases |
| Initialization decision | No `components.json` detected. Context D-06/D-07 and the user's reuse instruction select adaptation of the existing system; do not initialize shadcn or repeat a design-preference interview for this documentation phase |

**Observed versus specified:** The palette and type stacks below exist in code. The source UI contract calls for readable labels and reduced decorative texture. Current CSS still contains 11px labels, additional type sizes and uppercase decoration; it has not been verified against this contract. The compact scale below is a future implementation default within the inherited direction, not a claim about current CSS. No new branding, fonts, images, screenshots, or library migration is required in Phase 1.

## Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon-to-label and compact inline gaps |
| sm | 8px | Related labels, badges and controls |
| md | 16px | Body groups, table cell horizontal padding, card padding |
| lg | 24px | Detail section padding and group separation |
| xl | 32px | Layout gutters and major panel gaps |
| 2xl | 48px | Major section separation |
| 3xl | 64px | Maximum page-level section separation; no marketing hero |

Source: inherited 8px rhythm with a 4px compact default. Exception: interactive targets have a minimum 44px hit area (also a multiple of 4). Use 8px corner radii as the default within the inherited 6–10px range. Existing spacing is not being globally rewritten in Phase 1.

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.5 |
| Label and supporting count | 14px | 400; 700 for active control/status emphasis | 1.5 |
| Heading / primary A rate | 20px | 700 | 1.2 |
| Display / course page heading | 28px | 700 | 1.2 |

Exactly four sizes and two weights (400/700) form the phase contract defaults. Body and numeric labels use the existing sans stack; course headings use the display stack. Use tabular numerals for counts and rates. Show the A-rate denominator adjacent to its value; do not shrink it to fit. The 14px supporting default satisfies the inherited minimum of 12px. These defaults standardize later feature work without introducing a new type family.

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | paper `#f4f1e8` | Page and reading surfaces; observed token |
| Secondary (30%) | white `#ffffff`, moss `#dce8dc` sparingly | Result/detail surfaces and subdued grouping; white is a contract default, moss is observed |
| Accent (10% maximum) | spruce `#064c3b` | Primary search/watch submit CTA, selected filter indication, focus ring and fresh-valid-open seat label; observed token |
| Destructive | `#991b1b` | Confirmed cancel/stop-all action only; contract default |

Accent reserved for the four listed uses; ordinary links and evidence counts use dark ink `#18231f` with underline or other non-color affordance. Preserve rule borders `#d8d4c8`. Amber is the inherited semantic exception for limited/stale evidence: use brass `#b7791f` as border/mark with dark ink text on paper, not small brass body text. Unavailable data uses neutral text and a literal state label. Percentages describe intended visual emphasis, not an acceptance claim based on pixel measurement. Every status has text; stale positive counts must not retain the fresh-open green treatment.

## Copywriting Contract

Curly-brace values are substitutions from actual API/manifest fields, never sample production data. Copy derives from the source UI contract; unspecified recovery sentences and button labels are defaults.

| Element | Copy |
|---------|------|
| Primary search CTA | Search courses |
| Scope indicator | USF Tampa · Spring 2027 |
| Empty state heading | No matching sections |
| Empty state body | No sections match these filters for USF Tampa, Spring 2027. Clear filters to see more results. Action: Clear filters |
| Unsupported term | This registration term is not supported. View Spring 2027 sections. |
| Search error | We couldn't load sections. Try again. Action: Retry search |
| Partial coverage | Schedule coverage is incomplete. Some subjects are still being checked. View data coverage. |
| No usable history | Insufficient data. No usable course history is available. |
| Small sample | Small sample: {N} A–F outcomes |
| No measured reference | Reference data unavailable. Observed counts remain available where permitted. |
| Suppressed / invalid | Data suppressed by source. / Source data could not be validated. |
| Course fallback | Course-only history; not specific to this instructor |
| A-rate denominator | {A} of {N} A–F grades |
| Withdrawal denominator | {W} of {T} recorded outcomes |
| Missing verified profile | Verified RMP link unavailable |
| Verified profile action | View on Rate My Professors |
| Missing policy evidence | No supported policy information available |
| Historical policy badge | Historical syllabus · {source term} · {professor/course scope} |
| Policy conflict | Sources disagree. Review the source documents. |
| Source actions | Open syllabus / View schedule source |
| Fresh valid seats | {count} seats available · Checked {relative time} |
| Full / over capacity | Full / Full · Over capacity |
| Stale seats | Last known: {count} seats · Checked {time} · Update overdue |
| Unknown / cancelled | Seat availability unavailable / Section cancelled |
| Detail and registration actions | View section / Open USF registration |
| Watch CTA for full/unknown/stale | Email me when a seat opens; for unknown/stale add: Availability has not been confirmed. |
| Open-section watch CTA | Watch for a future opening; explain: Waits for a later confirmed full-to-open change. |
| Signup submit | Send verification email |
| Verification pending | Check your email. Monitoring starts after you confirm your address. |
| Deliberate verification | Confirm email and activate watch |
| Watch submit failure | We couldn't save your watch. Try again; your email is still entered. |
| Completed watch | Availability email sent; show only after provider acceptance, without claiming inbox delivery |
| Rearm action | Watch again; while open explain that the watch waits for a later confirmed full-to-open change |
| Manage link request | Email me my management link |
| Generic manage response | If this address can receive a management link, we'll email it. |
| Expired / invalid / consumed token | This link has expired. / This link is invalid. / This link has already been used. Action: Request a new link; an already-active watch reports its current state without another activation |
| Empty private list | No active watches. Browse Spring 2027 sections to create a watch. |
| Cancel one confirmation | Stop alerts for {course}, section {section}, CRN {CRN}? Action: Stop alerts; alternate: Keep watch |
| Stop-all confirmation | Stop all your alerts? You will no longer receive availability emails for these watches. Action: Stop all alerts; alternate: Keep watches |
| Cancel result / failure | Alerts stopped. / We couldn't stop alerts. Try again. Do not display success on failure. |
| Expired registration | Monitoring ended because registration for this section has ended. |

Direct email unsubscribe remains available without login; it reports its outcome rather than requiring an account or a second confirmation. Confirmations above apply to in-app management actions. Resend is rate-limited, preserves the address, and offers Change email. A submitting action is disabled against duplicate submission and exposes its progress. Source-derived text must be escaped.

## Surface and Payload Contract

Phase 1's downstream UI/API artifact must map each group below to named fields, nullable states/reasons and concrete acceptance cases. This table establishes semantic requirements, not claims that the present API already supplies them.

| Surface | Required arrangement and interactions | Payload / artifact obligations | Later implementation |
|---------|---------------------------------------|--------------------------------|----------------------|
| Search/results | Immediate search, small header (Easy-A, Methodology, Manage alerts); desktop semantic table and mobile full-width cards. A rate and seats visible before detail, ease secondary. Keep subject, GenEd, modality, open-seat filters; mobile secondary filters collapse. | Metadata supports/defaults only `202701`, campus Tampa; distinguish historical terms. Each row carries course/title, actual section number, term/CRN, instructor/Staff, independent grade metrics and reasons, N/T, scope/terms and seat state/time. | Phases 2–4 feature fields; Phase 6 integration |
| Linkable section detail | Identity → metric summaries → evidence → A–F chart/text table → seats/watch → policies → verified RMP → supporting facts. Route identity includes term and CRN; Back restores results. Desktop page or focus-managed drawer; mobile page. | N/T, named historical semesters and date bounds, section count, source identity/refresh, method version, fallback reason. A–F counts/percentages; W/I/S/U/O separately. Seat success time and attempt time separate; capacity, enrollment and waitlist separate. Source quote/type/term/scope/link and independent syllabus URL. | Phases 2–5, integrated Phase 6 |
| Methodology/data coverage | Permanent `/methodology`, linked from header and score help. Explain formula, denominators, cohort selection, small-sample adjustment, labels, sources and cadence. | Reproducible method v2 and separate RULE-20, RULE-60A/B/C, RULE-K60; measured reference and version/date. Coverage manifest distinguishes declared full scope from observed acquisition and evidence availability; show exclusions/failures without inventing percentages. | Phase 1 written artifacts; Phases 2/6 rendering; Phase 7 real coverage |
| Watch signup/confirmation | Exact section identity, email, one-alert behavior and configured cadence. Explicit confirm action; pending, active, already-open, expired/invalid/used, service-failure and completed states. | Persisted lifecycle state, trigger mode (`next_available` or `future_opening`), latest seat observation and configured cadence; provider acceptance distinguished from receipt. Never activate via a GET alone. | Phase 5; Phase 6 integration |
| Private watch management | Generic link recovery, private list, cancel, rearm, stop-all, no-password access, expired-link recovery. | Scope to verified address; zero/one/many watches with term/CRN, state, current availability and permitted actions. No public email/watch listing or token leakage to titles/referrers/analytics. | Phase 5; Phase 6 integration |

Search ordering is grade ease descending by default, with unscored rows after scored rows and no rank number for unscored rows. Offer ease, A rate, W rate, seat count and course code sorts; nulls remain last in both numeric directions. Include each row's sample beside raw-rate ordering. Open-only filtering requires fresh, valid, source-compatible positive seats. Search, filters, term, sort and page persist in the URL; restoration includes result position. Server pagination covers all offerings; an evidence inner join must never remove a section.

All offered Tampa Spring 2027 sections are in declared scope, including sections with no grades/instructor/syllabus/RMP. Samples validate acquisition only. Publish subject/section reconciliation with complete, partial, failed and unqueried inventory states and observation timestamps. Current instructor and syllabus coverage remain unverified across this scope until the Phase 1 inventory runs; the two-course September 1 observation is not a coverage denominator. Keep actual historical terms separate from registration metadata. Seat cadence values are configurable targets, not guarantees about source limits or freshness.

## UI Considerations

Applicable state considerations resolved: **8 covered, 0 backstop, 0 unresolved** at contract level. Here, covered means specified for planner acceptance, not implemented or tested. Each row must be represented in the Phase 1 state/payload matrix and assigned to its later verification phase.

| Category | Element(s) | Status | Resolution / Reason |
|----------|------------|--------|---------------------|
| empty | Search list, grade chart/table, policy list, private watch list, email form | ✅ covered | Matrix includes zero results and initial blank form with labels; use Copywriting Contract recovery rows. Absent counts produce no chart; W-only data keeps W/T available while A/ease/distribution are unavailable. No policy chip is inferred from missing text; a valid syllabus link remains visible without chips. |
| loading | Search, details, forms, navigation, sort/filter controls | ✅ covered | Specify reserved result layout/loading status, preserved filters/input, disabled duplicate submissions and stale-response rejection. Background refresh leaves existing facts visible with their actual timestamps; navigation cannot expose another section's retained data. |
| error | Search/detail fetch, source links, watch/management forms | ✅ covered | Specify retry copy, failed operations retaining prior state, invalid/expired/used link recovery, and generic management response. API/source outage must never enter fixtures or advance seat success time. Source validation errors are distinct from a valid zero result. |
| populated | Result table/cards, chart/text table, evidence/source groups, watch list | ✅ covered | Matrix supplies semantic desktop headers/caption and mobile order from the surface contract; grade buckets reconcile to N, recorded outcomes to T, and each fact has provenance. A valid numeric zero is rendered as zero, never treated as missing. |
| partial | Evidence metrics, instructor/source groups, inventory, watch forms | ✅ covered | Specify independent available/insufficient/unavailable/suppressed/invalid metric states; no history, small sample, no reference, W-only, no professor match, absent/current/historical/conflicting syllabus and missing RMP. Specify full/over-capacity, stale, unknown, invalid, cancelled and incompatible source states without a fresh-open badge. An incomplete inventory does not assert complete coverage or remove known sections. |
| overflow | Results, table, pagination, nav, evidence lists | ✅ covered | At 360/768/1440px and 200% zoom require no horizontal page scrolling. Use mobile cards when the table no longer fits; wrap source terms/labels and page controls, put long policy/GenEd content in details, paginate many results. No clipped focus or action controls. Phase 6 supplies browser evidence. |
| zero-one-many | Search results, grade buckets, chips, watch management | ✅ covered | Matrix has zero/one/many examples with correct singular/plural labels. A single section retains full identity/actions; many sections retain server pagination; zero watches offers browsing. A valid zero bucket stays in the text table; absent counts are a separate state. |
| long-text | Course/instructor names, quotes, email input, controls, method text | ✅ covered | Matrix uses long course/instructor names, evidence quotes and email values as stress cases. Wrap headings/buttons/source names; preserve the full accessible value if a compact preview truncates. Email input scrolls internally, error text wraps below it, source quotes remain readable on expansion. Phase 6 verifies target widths and zoom. |

Additional interaction acceptance: all five surfaces support keyboard-only use and visible focus. Tooltips open on focus/click; controls have associated labels/errors and 44px minimum hit areas. A chart always has a grade/count/percentage text alternative. Drawer/dialog focus is contained, Escape closes it and focus returns to its trigger. Controls inside cards remain distinct links/buttons. Announce meaningful result/watch changes without announcing each seat poll. Honor reduced motion; use predictable safe external links. Screenshots, keyboard/zoom checks, screen-reader spot checks and an actual frontend-to-API grade result are later browser evidence, not Phase 1 completion claims.

## Phase 1 Acceptance and Exclusions

- The written UI/API matrix covers all five surfaces and every state listed above, with field/state/reason mapping and requirement/phase ownership; no screen implementation is needed to pass Phase 1.
- The launch contract explicitly includes all Tampa Spring 2027 offerings, explains missing evidence separately, and prevents historical terms from becoming selectable registration terms.
- The method artifact explains exact denominators and all five threshold rules separately; insufficient evidence never maps to a numeric substitute. Synthetic worked examples are labeled synthetic and never serve production results.
- Source inventory completion and actual imported historical coverage require recorded observations; this spec itself does not resolve OQ-02/OQ-03 or establish data possession.
- Reuse existing clients, components, source UI specification and prior onboarding. No redesign, shadcn initialization, production feature implementation, imagery, worker/email deployment, source-coverage fabrication, RMP content import, general accounts product or local-main change is part of this adaptation.

## Source Traceability

| Source | Decisions used |
|--------|----------------|
| `01-CONTEXT.md`, D-01–D-07 | All Tampa offerings; Spring 2027 only; samples not scope; keep missing-evidence sections; safe worktree continuity; reuse existing work; research-first without repeated interview |
| `docs/final-mvp-ui-spec.md`, sections 1–7 | All seven sections inherited: visual hierarchy, search, detail, methodology, watch screens, failure states and accessibility/acceptance |
| `web/tailwind.config.ts`, `web/src/styles.css`, `web/package.json` | Observed palette, type stacks, existing CSS deviations and dependency inventory; no claim of rendered conformance |
| `.planning/REQUIREMENTS.md` | REQ-LAUNCH-01, REQ-UI-01, REQ-EVID-01/02; grade/source/seat/alert state obligations and their owning phases |
| `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` | Locked evidence rules, no fabricated defaults, current planning position, Phase 1 exit criteria and later implementation boundaries |
| Research | No new external design research needed: this task adapts an already supplied authoritative specification; technical coverage research is tracked separately |
| Defaults in this adaptation | Exact four-size/two-weight scale, 4px compact spacing, 8px radius, white grouping surface, destructive color and recovery copy; all labeled as defaults rather than observed implementation |

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| None | None | Not applicable; manual existing system and local components only. Dependency/config inspection recorded 2026-09-08; no registry import or third-party block added. |

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending independent checker. Status remains draft; this file does not assert implemented or visually verified UI.
