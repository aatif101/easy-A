# Easy-A final MVP: evidence, policies, and seat alerts

Status: proposed implementation plan, prepared September 5, 2026. This is a handoff for GSD Core, not a claim that the MVP has shipped. Reader: the developer or GSD agent taking the existing application through a usable public release.

Companion documents: [UI contract](final-mvp-ui-spec.md), [GSD Core starting prompt](gsd-core-mvp-prompt.md), and [ingestion manifest](gsd-mvp-manifest.yaml).

## 1. Final product and scope

A USF Tampa student can find a section, understand its historical grade results and the strength of that evidence, inspect supported syllabus policies, visit a verified Rate My Professors profile, see recently checked seat availability, and subscribe to an email when seats become available. The complete product includes a deployed responsive website, real data, scheduled refresh, durable email delivery, and an operator runbook.

The user explicitly requested these features and confirmed **seat counts plus email alerts**. Preserve existing course search, term selection, GenEd and modality filters where useful. They are supporting navigation, not new recommendation systems.

| ID | Required outcome |
| --- | --- |
| GRADE-01 | Historical grade ease comes only from grade distributions, with a published formula and small-sample adjustment. |
| GRADE-02 | A rate is prominent and identifies its numerator and denominator. |
| GRADE-03 | Students can see observed A/B/C/D/F counts and percentages. |
| GRADE-04 | Observed withdrawal rate appears separately, with its own denominator. |
| EVID-01 | Actual sample size, sections, named semesters, date coverage, and professor-course versus course-only history are visible. |
| EVID-02 | Missing, invalid, suppressed, or insufficient evidence never produces a plausible default score. |
| RMP-01 | Only a verified “View on Rate My Professors” link is displayed for the applicable instructor. |
| POLICY-01 | Existing supported policy chips retain evidence, source term, source scope, and a correct syllabus or schedule-source link. |
| SEAT-01 | Each section shows the latest known count, availability state, and last successful observation time. |
| SEAT-02 | A scheduled service refreshes availability and detects valid openings without depending on a student's browser. |
| ALERT-01 | A student can verify an email address, watch a section, receive an availability email, and cancel or rearm the watch. |
| UI-01 | Search, details, methodology, and alert flows work on mobile and desktop, including all missing-data and failure states. |
| OPS-01 | Production runs against real data with reproducible deployment, monitoring, recovery, and demonstrated end-to-end behavior. |

Explicitly outside this MVP: imported RMP ratings/reviews, RMP scraping, AI summaries or scoring, predicted personal grades, workload predictions, difficulty inferred from syllabus wording, social reviews, schedule generation, degree planning, payments, SMS, browser push, native apps, automatic registration, multi-university expansion, or a general user-profile/account system. Email verification and private watch management are required; a full account product is not.

## 2. Audited baseline

The baseline is freshly fetched GitHub `origin/main`, commit `06634490de5c765bdc7b55e4f439476b0e4fa0f7` (PR #12). The user's local `main` was still `d880d3c2bd31158c2392725e5c203ac92b2088fa`, with an untracked `web/` directory. Do not treat that older local checkout as the current product, overwrite local work, or copy its built frontend over source on current main.

The audit used a separate detached checkout of the fetched commit. Existing verification completed there: **166 Python tests passed; 19 frontend tests passed; the TypeScript/Vite production build passed.** Python tests use SQLite fixtures. These results establish an offline baseline, not production PostgreSQL compatibility, real-data coverage, email delivery, or visual browser acceptance. No production database contents were audited.

| Area | What current main already has | Work still required |
| --- | --- | --- |
| Foundation | Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL development configuration; React, TypeScript, Vite, Tailwind frontend. | Production configuration, durable worker, deployment, health/readiness, operational checks. |
| Historical grades | XLSX import, all ten grade buckets, totals, source hashes, term/CRN joins, aggregation, smoothing and evidence counts. | Reliable grade-to-course mapping, approved real history coverage, observed grade payloads, eligibility and exclusion rules. |
| Ease score | A documented 0–10 score, shrinkage, course/instructor selection, low/medium/high labels. | Remove the 20% withdrawal component; eliminate subject/global stand-in scores and hard-coded no-evidence defaults. Publish the new method in the UI. |
| A rate/distribution | A/B/C/D/F counts are stored internally. | Neither A rate nor full bucket counts are exposed through the ranking summary or rendered for students. |
| Withdrawal | Raw rate exists internally; API/UI use a smoothed rate. | Expose observed W/total, clearly explain its denominator, and keep it independent of grade ease. |
| Evidence | Sample/term/section counts and score-source metadata; some details in UI. | Named terms/date range, actual denominator near A rate, clear professor-course/course-only labels, unavailable reasons, and complete source coverage. |
| RMP | No integration. | A small curated identity/link registry, verification process, API fields, and UI link/unavailable state. |
| Policies | Deterministic extraction for nine supported categories; provenance, exact short evidence, historical labeling. Syllabus URLs are stored. | Expose and render the correct source links; avoid implying historical policy is current; explain unsupported or conflicting evidence. |
| Seats | Public schedule client, canonical section fields, appended snapshots, open-seat filter and badges. | Structured timestamps and freshness; validated availability state; scheduled acquisition, transitions, worker health, expiry and failure behavior. |
| Alerts | No subscriptions, email transport, outbox, verification, or worker. | Entire verified-email watch flow and operational delivery system. |
| UI | Responsive table/cards, metadata-backed filters, pagination, expandable details, error/loading/empty states. | A-rate-led information hierarchy, grade chart, deep links, source links, methodology, alerts, final accessibility and visual QA. |

Important implementation findings:

- With no grade history, the default grade prior is 0.75 and withdrawal prior is 0.10. The current composite can therefore produce **7.8/10 without course evidence**. Removing this is a first-priority requirement, including API, sorting, tests, fixtures and CLI output.
- Course lookup can fall back to another course's subject history as the displayed evidence. A population prior may regularize observed evidence; it must never masquerade as this course's history.
- Grade import initializes `course_id` to null. Analytics can join through historical sections, so importing XLSX files alone does not establish usable course coverage. Preserve/resolve parsed course identity and backfill or explicitly exclude unresolved history.
- Historical instructor selection uses name-based joins across stored instructor observations. Validate that old assignments, ambiguous names, and co-teaching cannot attribute a whole section's grades to the wrong professor.
- Grade rows are unique by term/CRN/source, not term/CRN alone. Explicit source selection is required to avoid double-counting duplicate exports from different sources.
- Seats are labeled current based on latest stored record, irrespective of its age. Existing quality warnings do not automatically prevent invalid seat values from reaching the API or triggering future alerts.
- The API omits section number and UI currently says “Section unavailable” even though the schedule model stores it. Expose the real section identity.
- Search computes candidate rankings before slicing pagination and repeatedly invokes course analytics. Benchmark and batch work before launching broad term searches; do not assume a 50-row page limits backend work.
- The UI favors Spring 2027 when that term exists and defaults to fixtures when no API base URL is configured. Replace both with explicit launch configuration and safe production behavior.

Evidence anchors at the audited revision: [analytics and defaults](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/analytics/scoring.py), [cohort selection](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/analytics/queries.py), [ranking payload](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/rankings/models.py), [seat projection](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/rankings/service.py), [current UI](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/web/src/components/RankingTable.tsx), [grade importer](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/grades/ingest.py), and [search implementation](https://github.com/aatif101/easy-A/blob/06634490de5c765bdc7b55e4f439476b0e4fa0f7/src/easy_a/api/routes/rankings.py).

## 3. Grade and evidence contract

### Observed metrics

Use one explicitly selected historical cohort for the headline A rate, distribution, withdrawal rate, and ease score. Do not put a professor-only A rate beside a course-wide distribution without labeling and separating them. All headline raw counts remain unweighted. Keep recency weighting disabled for this launch.

Let `N = A + B + C + D + F`, and let `T = A+B+C+D+F+I+S+U+W+O`, verified against the source's Total Grades field.

| Metric | Calculation and display rule |
| --- | --- |
| A rate | `100 * A / N`; display “A grades among A–F outcomes,” and `A of N`. Excludes W/I/S/U/O. Null when N is zero or counts are unusable. |
| Distribution | Each A–F bucket shows its observed integer count and `100 * bucket / N`. Include F in the denominator. A text table accompanies the chart. |
| Withdrawal rate | `100 * W / T`; display `W of T recorded outcomes`. This includes all recorded grade categories in T and is not a percentage of current enrollment. Null when T is zero or invalid. |
| Other outcomes | List W/I/S/U/O counts beneath the distribution so students can reconcile A–F totals with all recorded outcomes. Do not invent finer distinctions such as A-minus if the source only provides an A bucket. |
| Sample | Say “recorded outcomes” or “A–F grades,” not “unique students”: repeat enrollments may exist and aggregate data cannot deduplicate people. |

Never average section percentages equally. Sum eligible counts, then calculate rates. Zero is a valid observed rate; null means unavailable. Round only for display.

### Proposed historical grade ease v2

Retain the existing 0–10 presentation scale, with this simpler grade-only method:

```text
g = (4*A + 3*B + 2*C + D) / (4*N)
adjusted_g = (N*g + k*mu) / (N+k)
historical_grade_ease = 10 * adjusted_g
```

`mu` is a measured reference grade-favorability mean from eligible imported history; `k` is prior strength. No withdrawals, RMP data, seats, syllabus signals, modality, or GenEd data enter this calculation. A rate and the distribution remain observed values, not smoothed numbers.

Recommended initial defaults for GSD to implement and version, subject to checking the actual launch dataset:

- `k = 60`, retaining the existing regularization strength. This is a transparent product setting, not a statistically calibrated guarantee.
- Require at least **20 A–F outcomes** in the selected course cohort for a displayed adjusted score. Smaller samples may show source-permitted observed counts/rates with a prominent “Small sample” label; the score says “Insufficient data.” Source suppression rules take precedence over this display threshold.
- Prefer same-professor/same-course evidence only after conservative identity resolution and at least **60 A–F outcomes**. Otherwise use course-only evidence and state why. Do not manufacture professor specificity by using their RMP profile as evidence of historical teaching assignments.
- For professor-course history, first try other sections of the same course as the reference cohort. Otherwise try other courses in the subject, then the eligible institutional reference corpus. For a course-only cohort, start with other courses in its subject. Exclude the displayed cohort from the reference at every level.
- Require at least **60 eligible A–F reference outcomes** for a reference mean. If no measured reference is available, the adjusted score is unavailable with reason “Reference data unavailable”; valid observed grade facts remain visible. Never substitute 0.75, another hard-coded population mean, or a subject/global score.
- Keep zero-valued reference means valid. Exclude current/future target terms from both observed history and references. Use deduplicated, valid data within the declared scope; version cohort boundaries and method settings.
- Use “Limited,” “Moderate,” and “Strong” evidence as descriptive labels: fewer than 60, 60–179, and at least 180 A–F outcomes, downgrading one level if only one term is covered. Show “Insufficient data” where score eligibility fails. Always show actual counts and terms; these labels are not probabilities of getting an A.

These numerical defaults are recommendations in this plan, not decisions previously supplied by the user. GSD may revise them with a documented rationale and updated methodology/tests; it may not weaken the no-fabrication rule.

Worked synthetic example, not a claim about a real course: A=40, B=30, C=20, D=5, F=5, W=10, all other buckets zero. N=100; T=110; A rate=40%; W rate=9.09%; g=0.7375. If a measured reference supplies mu=0.70 and k=60, ease=7.234375, displayed as 7.2/10. Changing W alone must not change grade ease.

### Cohort and availability rules

Use verified Tampa history for the Tampa product; normalize and validate campus data rather than pooling campuses implicitly. Historical grade-to-course linkage must preserve course identity across catalog editions and term-scoped CRNs. Exclude unresolved, duplicate, conflicting, invalid or source-suppressed rows with recorded reasons. A blank source cell must not silently become zero unless the source's documented export semantics permit that conversion.

When an instructor is Staff, unknown, ambiguous, or has insufficient matching history, label course-only history explicitly. If no eligible course history exists, return an unavailable state; matching subject history cannot fill the gap. Keep the section searchable and preserve independently available seats, syllabus evidence and verified links.

Define independent nullable metric states, not one blanket boolean: `available`, `insufficient`, `unavailable`, `suppressed`, or `invalid`, plus a reason. W-only history can provide a valid withdrawal rate but no A rate/ease. Valid A–F data can remain visible even when an adjustment reference is unavailable.

Expose actual named semesters, earliest/latest included term, section count, N, T, evidence scope, fallback reason, source identity, data refresh time, and methodology version. Never call a subject reference cohort the professor's sample. Unknown scores sort after known scores in either numeric direction; no hidden zero coercion. Do not give unscored rows an apparent ease ranking. An explicit minimum-score filter can exclude them, while normal search retains them.

## 4. RMP and policy contract

RMP is a curated external-link feature. Create an operator-maintained registry of instructor identity, university identity, canonical profile URL, verification status, verification timestamp and verification evidence/note. Use a CLI/import file and validation command; a new admin UI is unnecessary.

Verify that the profile matches the named instructor and USF using identity evidence, including department where needed. A search result or matching name alone is not a verified link. Allow only canonical HTTPS RMP profile URLs. Recheck when instructor assignments change and during launch curation. Ambiguous names, Staff, missing profiles and rejected matches show “Verified RMP link unavailable.” Do not import ratings, review counts, review text, tags, or summaries, or run a bulk RMP crawler.

Reuse the nine supported policy categories: attendance, late work, exams, exam location, participation, curve, lab, quiz, delivery format. Keep current syllabus → supported schedule note → historical same instructor/course → historical same course precedence. Preserve existing source selection unless a tested conflict requires a conservative fix; do not silently combine contradictory sources.

Expose the resolved syllabus URL independently from extracted chips: a syllabus may exist even when no supported policy is found. Each chip retains its short evidence quote, source term, source type and link. Historical chips and links clearly state whether the match is this professor/course or only the course. A schedule-note chip links to its schedule source; it must not be labeled a syllabus quote. Never infer “no attendance requirement” from absent text.

## 5. Seats and email alerts

### Availability and refresh

Reuse the existing public schedule adapter and `(term, CRN)` section identity. Expose section number, source status, capacity, enrollment, seats remaining, waitlist seats, last successful observation, last attempt, and freshness separately. Waitlist capacity is not an available course seat.

The official [USF registration page](https://www.usf.edu/registrar/register/) directs students to Student Self-Service and documents registration restrictions. An observed positive seat count therefore means availability was reported, not that a particular student can enroll. Link students to official registration; do not automate registration.

Classify source-supported active sections with valid positive remaining seats as open, zero as full, and valid negative remaining seats as full/over capacity. Preserve the signed observation for diagnostics. Invalid/contradictory values become unavailable. Cancellation, closed registration, or incompatible source status must not be overruled by a positive count. Unknown source statuses require conservative handling and source-specific validation.

Use a durable scheduled Python worker sharing the existing PostgreSQL database. Keep network acquisition outside long database transactions. Poll bounded subject/course or CRN queries, sharing one observation among all subscribers. Never poll once per subscriber or make a student's search trigger an upstream crawl. The existing [USF public schedule form](https://usfweb.usf.edu/DSS/StaffScheduleSearch/) is an acquisition starting point; availability, status meanings and a sustainable request cadence still require narrow live validation.

Proposed targets: watched sections every **5 minutes**, remaining supported launch sections every **30 minutes**; expire freshness after two expected intervals. These are configurable product targets, not verified USF rate limits or a promise of real-time delivery. Validate request volume in Phase 1; if unsustainable, narrow launch coverage or publish a slower cadence. Schedule, grades, catalog and syllabus refreshes have different cadences; do not download all sources every five minutes.

Record failed attempts without advancing the successful observation timestamp. Mark data stale at its age threshold and show refresh trouble separately. Do not classify empty/partial/error responses as zero seats or cancel sections on a single missing row. Store observations atomically, reject out-of-order state updates, and serialize state transitions per term/CRN. Persist polling leases/checkpoints and a worker heartbeat; restart must not lose the monitoring state.

### Student alert flow

1. A student selects “Email me when a seat opens” on a section and enters an email address.
2. Send a rate-limited verification email. The watch is pending until the student confirms a short-lived token. No opening email is sent to an unverified address.
3. The confirmation page identifies the course, term, section and CRN, current availability, monitoring cadence and watch status. If already open, say so; do not claim a new opening was observed.
4. An active watch receives an email when a fresh validated observation reports seats available. A known full-to-open transition is an opening; a first known positive value or recovery after an unknown interval is described as “Seats are available,” without inventing when it opened.
5. Email includes the observed seat count, checked-at time, term/CRN, section detail link, official registration link and unsubscribe action. Seats may change before the email is read.
6. For the simplest launch, each verified watch sends **one availability alert**, then becomes completed. The student can rearm it through a private management link. If rearmed while already open, clearly configure it to wait for a later confirmed full-to-open event. This avoids repeated emails while a section stays open.
7. A private management page lists watches for the verified address and supports cancel and rearm. An “Email me my management link” recovery flow avoids passwords. Do not expose watch lists or email addresses publicly.

Implement a transactional outbox and unique watch/event delivery key. Polling and delivery are independent jobs. Recheck that the watch is active and the latest state is fresh/open before sending queued availability messages; suppress outdated opening messages when the latest valid state is full or cancelled. Do not remove a pending delivery until success, permanent failure, expiry or explicit suppression is recorded.

Persist retries, provider message IDs, next-attempt time and terminal state. Use provider idempotency where available to handle a crash after provider acceptance but before the database is updated. Do not promise exactly-once email delivery. If using the proposed default provider Resend, its [idempotency window is 24 hours](https://resend.com/docs/dashboard/emails/idempotency-keys); keep retries inside that window or reconcile uncertain results instead of blindly resending later. A provider-accepted email is not proof of inbox delivery.

Persist each watch's trigger mode: `next_available` for a full/unknown section, or `future_opening` when the student explicitly watches an already-open section. The latter must observe a valid closed/full state before a later positive observation can notify. Store that armed state across restarts. Use section/session registration deadlines where available, with an operator-configured cutoff when the source lacks them; a term-end date alone may be too late.

Use expiring, purpose-scoped, random tokens stored as hashes. Verify/consume ownership tokens through deliberate confirmation rather than an email scanner's GET request. Keep tokens and full email addresses out of logs and analytics. Scope unsubscribe tokens to the watch; support a direct unsubscribe action without a login. Enforce per-address/IP limits, pending expiry, duplicate-watch protection, maximum active watches, and cancellation on term/registration expiry. Validate signed provider webhooks if used and suppress bounces/complaints. Store only email and watch data needed for the service; publish and implement retention/deletion behavior.

A suitable simple deployment is one API service plus one worker and PostgreSQL, with the built frontend served by the existing hosting arrangement. A PostgreSQL outbox can use row locking and `SKIP LOCKED` for concurrent job claiming; its suitability for queue-like tables is documented in [PostgreSQL 16 SELECT](https://www.postgresql.org/docs/16/sql-select.html). FastAPI response [background tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) are not, by themselves, a persisted scheduler or delivery ledger. A full Redis/Celery platform is unnecessary unless measured requirements justify it.

## 6. API and storage changes

Preserve the existing application stack and service boundaries. Add migrations for durable state; keep derived grade results computed or cached, rather than treating a final score table as primary evidence.

| Boundary | Planned contract |
| --- | --- |
| Grade analytics | Observed buckets, independently nullable metrics/statuses, selected cohort, empirical reference metadata, named terms and methodology version. |
| Search/detail API | New historical-grade-ease fields, A rate, observed withdrawal, section identity, freshness, source URLs, RMP link status and null-safe sorts/filters. Keep aliases only as a documented short transition; never retain old blended semantics under the new label. |
| Metadata | Configured supported terms/campus/subjects, default registration term, coverage and last refresh information. Historical-only terms should not automatically become selectable registration targets. |
| Seat status | Shared latest validated state, successful observation timestamp, status reason, polling cadence, refresh failure and source URL; an inexpensive endpoint for visible-page refresh if needed. |
| Alert endpoints | Create pending watch; confirm ownership; request management link; list/cancel/rearm authenticated watches; provider webhook only if required. Public responses avoid email enumeration. |
| RMP storage | Curated verified/rejected/unknown identity mappings with audit fields and canonical URL. |
| Worker storage | Poll state/leases, opening events, subscribers/watches, hashed tokens, outbox/deliveries, job outcomes and heartbeat. Unique constraints prevent duplicate watches and deliveries. |

Update Python models, serializers, TypeScript types, real client, fixtures, UI and CLI consumers together. Production must fail visibly on missing API configuration or use an explicitly configured same-origin API; never silently enter fixture mode. Keep fixtures explicitly opt-in for development/tests. Configure allowed write methods and origins for alert endpoints; enforce private management authorization on the server.

## 7. Delivery roadmap to the finished MVP

These are delivery phases, not multiple MVPs. GSD should translate them into its next available phase numbers and produce small executable plans with requirements and acceptance evidence. A phase is complete when its behavior works end-to-end, including its UI where specified.

| Phase | Outcome | Depends on |
| --- | --- | --- |
| 1 | Current-main baseline, real-source coverage, method decisions and UI contract are established. | None |
| 2 | Students can inspect honest historical grade evidence and a published method. | 1 |
| 3 | Students can follow verified RMP and syllabus evidence links. | 1; use shared payload from 2 |
| 4 | Students see reliable recently checked seats; a worker refreshes them. | 1; shared API/UI contract from 2 |
| 5 | Verified email watches deliver availability alerts and can be managed. | 4 |
| 6 | The integrated UI is polished and usable on mobile and desktop. | 2, 3, 4, 5 |
| 7 | Complete real-data coverage for the declared launch scope and production operations are ready. | 2–6; provision prerequisites early |
| 8 | Deployed end-to-end acceptance passes and the public MVP is released. | 7 |

Requirement traceability:

| Requirements | Implementation | Integrated proof |
| --- | --- | --- |
| GRADE-01, GRADE-02, GRADE-03, GRADE-04 | Phase 2 | Phases 6 and 8: source-to-screen reconciliation and published method. |
| EVID-01, EVID-02 | Phases 1 and 2 | Phases 6–8: scope, insufficient/suppressed states, source coverage and no fabricated scores. |
| RMP-01, POLICY-01 | Phase 3 | Phases 6–8: correct real links, provenance and missing-source states. |
| SEAT-01, SEAT-02 | Phase 4 | Phases 7 and 8: real adapter, timestamped UI, scheduled worker and failure/recovery behavior. |
| ALERT-01 | Phase 5 | Phases 6–8: private management, durable delivery, test inbox and unsubscribe. |
| UI-01 | UI contract in Phase 1; feature UI in Phases 2–5; completion in Phase 6 | Phase 8: all deployed user journeys on mobile and desktop. |
| OPS-01 | Source planning in Phase 1; deployment work in Phase 7 | Phase 8: real release, health, recovery and operator handoff. |

### Phase 1 — Baseline, scope and contracts

Create a safe implementation branch/worktree from freshly fetched main and preserve untracked work. Read this plan and UI contract; bootstrap or merge `.planning/` using GSD Core's document ingestion. Inventory source availability early: actual aggregate XLSX files and their real terms, grade-course joins, historical instructor coverage, public schedule status semantics, syllabus availability and candidate RMP identities.

Define a launch coverage manifest: USF Tampa, supported registration term(s), supported subjects/courses, grade terms, default term, and refresh cadence. Include all intended courses in that declared scope; do not call a two-course fixture demo a finished campus product. Publish exclusions and missing historical coverage. Do not invent actual imported semesters or coverage percentages before inspecting available data.

Lock method v2 and state definitions, API examples, alert lifecycle and the UI component/state contract. Confirm source suppression/blank-cell interpretation from available source documentation. Identify hosting, sender-domain and real-data access dependencies now while implementation proceeds independently.

Exit: baseline checks recorded; every requirement mapped; source gaps and owners listed; formulas reproducible; UI screens and failure states specified. An unavailable grade export does not block seat work, but it remains a grade-launch dependency.

### Phase 2 — Honest grade evidence, API through UI

Preserve/resolve grade course identity, backfill existing rows, deduplicate canonical outcomes, and filter eligible scope/terms. Implement observed rates/buckets and grade-only shrinkage. Make missing/small/invalid/suppressed states explicit; remove subject/global displayed fallbacks and default 7.8 scores. Harden historical instructor attribution and course-only fallback.

Expose evidence and named terms in the API; update schema, frontend types, fixtures, CLI output, sorting and filtering. Add A rate to search/cards, chart and count table to details, clear withdrawal denominator and evidence labels, and a methodology page with the exact formula/version and example.

Exit: the worked example matches; zero-history and W-only sections behave correctly; small samples cannot outrank supported evidence via fabricated scores; raw metrics share the labeled cohort; changing only W/seats/policies/RMP cannot change grade ease. Prove this through unit, API and rendered UI tests, including null sorting and term/CRN isolation.

### Phase 3 — Verified RMP and policy sources

Implement the curated registry, import/validation CLI and API resolution for the current instructor. Curate actual unambiguous launch examples. Expose syllabus metadata independently of chips and source-specific links for every supported evidence path. Retain conservative historical labels and unknown/conflicting states.

Exit: a verified profile opens the correct professor/university; Staff/ambiguous identities never link incorrectly; a historical syllabus displays its actual term and scope; a current syllabus without recognized chips still has a working link. No imported RMP content appears in database, API or UI.

### Phase 4 — Fresh seats and scheduled observation

Extend seat projection with timestamps and validated availability/freshness. Make invalid source data fail closed for availability, and prevent old observations overwriting newer state. Add polling worker, bounded shared fetches, leases, backoff, state transitions, expiry and heartbeat. Preserve existing refresh-stage isolation.

Wire open/full/over-capacity/unknown/stale/cancelled UI, checked-at labels and an open-seat filter that excludes stale or invalid values. Visible-page refresh reads the local service with bounded polling and pauses when hidden; it does not own acquisition. Add the official registration link.

Exit: deterministic full→open, open→open, full→unknown→open, out-of-order, partial-response, cancelled-with-positive-count and outage/recovery scenarios pass. A narrow real schedule check validates source parsing. Worker restart preserves state and one observation serves multiple watchers.

### Phase 5 — Email watches

Add subscriber/watch/token/outbox migrations, verified-email endpoints, delivery adapter, templates, limits, expiry, cancellation/rearm and private management flow. Implement one-alert completion, provider idempotency and safe retries; keep opening detection independent from delivery. Include confirmation, invalid/expired-token, provider-failure, completed and unsubscribed UI states.

Use one email provider. Prefer an already configured provider; otherwise Resend is a proposed simple default behind a replaceable transport. Sender-domain ownership and DNS setup are prerequisites; see [verified-domain documentation](https://resend.com/docs/dashboard/domains/introduction). Do not buy services as part of planning.

Exit: controlled source transitions generate one durable delivery per watch; repeated polls and worker restart do not duplicate; unverified/cancelled/expired watches cannot send; stale or now-closed events are suppressed; tokens cannot access another recipient's watches. Demonstrate verification, availability email and unsubscribe with a designated test inbox after it is supplied/authorized.

### Phase 6 — Final integrated UI

Implement the companion UI contract across search, section details, methodology and alert management. Preserve useful filters; make A rate prominent without hiding uncertainty. Add URL-backed search/detail navigation, back-button behavior, section identity, consistent raw-rate formatting and contextual source links. Fix the fixed-term and implicit production-fixture behavior.

Perform browser verification at 360px, 768px and 1440px and at 200% zoom; use keyboard-only and screen-reader spot checks. Ensure charts have a text alternative, focus is restored correctly, chips have readable contrast, and small-sample/unknown states use text as well as color. Record screenshots of real integrated states; do not treat a static mockup as the finished UI.

Exit: a student can find a class, understand A/W denominators, inspect evidence, open the correct source and manage an email watch without developer knowledge. UI tests and visual acceptance cover all required failure/empty states, and production has no synthetic results.

### Phase 7 — Real data, performance and deployment readiness

Import actual approved historical exports with correct terms and source provenance. Refresh the declared launch schedule/catalog coverage, map historical instructors conservatively, ingest available syllabus documents and curate RMP links. Report coverage separately for searchable sections, grade evidence, professor-specific history, fresh seats, syllabi and verified RMP. Honest unavailable labels are allowed; claiming broad coverage based on fixtures is not.

Benchmark full-scope search, not just one course. Batch shared aggregates, prefetch related evidence and add indexes/caching where measurements require them. Cache keys include data/method versions; seat freshness and watch processing cannot depend on stale ranking caches. Add PostgreSQL integration tests for queries, migrations, job claiming, uniqueness and concurrency.

Package API/frontend/worker, migration command and environment configuration; configure TLS/origins, persistent database, backup/restore, secrets, sender domain and scheduler. Add CI for Python and frontend checks and deployment smoke tests. Readiness should test database access; worker health should expose last successful tick and source freshness. Track poll failures, outbox backlog, retry age and email failures without logging personal data.

Proposed acceptance budgets on the selected staging host: representative search p95 ≤2 seconds at 20 concurrent users; interactive usable search within 3 seconds on the agreed mobile test profile; watched sections ordinarily observed within the validated 5-minute target; queue-to-provider acceptance within 60 seconds of a validated opening under normal operation. Measure and record results. These are engineering targets; do not promise upstream or inbox latency.

Exit: real coverage report, passing PostgreSQL checks, benchmark evidence, reproducible staging deployment, validated sender setup, backup restore drill, restart behavior and operator runbook. External credentials and domain ownership are specific dependencies, not tasks to silently skip.

### Phase 8 — Deployed acceptance and release

Run the full user journeys on the deployed staging system against real imported aggregates and live public schedule observations. Use a clearly isolated test adapter to simulate an opening when no live transition occurs; label that evidence honestly. Deliver test emails to the designated inbox; separately verify the production source adapter, worker scheduling and delivery transport. Do not alter a real section to force a seat transition.

Resolve launch-blocking findings, deploy the approved release, verify production config and complete the following acceptance matrix. Record release commit, deployed URL, environment/method versions and runbook location. Only mark the milestone complete after the actual production outcome is verified; absent credentials leave deployment explicitly pending.

## 8. Final acceptance matrix

| Scenario | Required evidence |
| --- | --- |
| Supported professor history | Displayed A rate, buckets, W rate, score, N/T and terms reconcile with a selected actual aggregate; professor identity is supported. |
| Course-only history | Staff/unknown or insufficient professor evidence clearly uses course-only history; same-course sections do not claim different professor scores without evidence. |
| No usable history | Section is searchable with “Insufficient data”/reason; no numeric stand-in score and no invented grade percentages. |
| Small, invalid or suppressed data | Raw metrics follow source permission and denominator rules; adjusted score eligibility is enforced in backend and UI. |
| Sources | A verified RMP link opens the correct profile; current/historical syllabus links and policy quotes match the displayed source. |
| Seats | Actual observation time is visible; stale/unknown/invalid/cancelled states do not masquerade as open; waitlist seats remain separate. |
| Email lifecycle | Verification → active watch → one availability alert → completed/rearm or unsubscribe works with a test inbox. |
| Delivery resilience | Duplicate polls, transient errors, crash around provider acceptance, expired jobs and restarts do not create uncontrolled duplicate mail or false availability. |
| Privacy | Other recipients' watches cannot be read or changed; tokens expire; logs and public responses do not expose email addresses or credentials. |
| Mobile/desktop | Search/filter → detail → methodology/source → watch → manage works at target sizes with keyboard, visible focus and chart text alternatives. |
| Real launch | Coverage manifest and dashboard values use real data; production fixture mode is disabled; declared support matches coverage. |
| Operations | Production URL works; migrations, health, polling, delivery, recovery and backup restoration have recorded evidence. |

## 9. GSD handoff and unresolved inputs

Use the [starting prompt](gsd-core-mvp-prompt.md). The installed GSD Core supports document ingestion into `.planning/`; this repository had no tracked GSD planning directory at the audited revision. Bootstrap from the manifest when absent, merge when present, and continue existing phase numbering. Do not initialize a separate GSD2 `.gsd/` project or replace the application.

Resolve these concrete inputs during Phase 1 or before their dependent release step: exact launch term/subject coverage, available real grade export terms and campus metadata, sustainable schedule cadence/status interpretation, available historical instructor/syllabus data, launch RMP identity curation, deployment host/domain, email provider/sender-domain access, and designated test inbox. The user has already decided email alerts are in scope; do not reopen that choice.

The recommended thresholds, one-alert-then-rearm lifecycle, monitoring cadence and service budgets are explicit defaults for execution, not verified empirical facts. GSD should record any evidence-driven changes and keep all feature requirements intact. Final delivery means the integrated deployed product, not merely passing fixture tests or finishing the backend.
