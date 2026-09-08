# Requirements (PRD intel)

Extracted from documents classified `PRD`. Precedence rank 2.
One source doc in this ingest set: `docs/final-mvp-plan.md` (`locked: false`).

Native requirement IDs from the source table are preserved inside the `REQ-` slug so
downstream traceability tables in the source (section 7) still resolve.

Explicitly out of scope per the source: imported RMP ratings/reviews, RMP scraping, AI
summaries or scoring, predicted personal grades, workload predictions, difficulty
inferred from syllabus wording, social reviews, schedule generation, degree planning,
payments, SMS, browser push, native apps, automatic registration, multi-university
expansion, or a general user-profile/account system.

---

## REQ-GRADE-01: Grade-only historical ease with published method
- source: docs/final-mvp-plan.md
- description: Historical grade ease comes only from grade distributions, with a published formula and small-sample adjustment.
- acceptance: Method v2 is `g = (4*A + 3*B + 2*C + D) / (4*N)`; `adjusted_g = (N*g + k*mu) / (N+k)`; `historical_grade_ease = 10 * adjusted_g`. `mu` is a measured reference grade-favorability mean from eligible imported history; `k` is prior strength. No withdrawals, RMP data, seats, syllabus signals, modality or GenEd enter the calculation. Retain the 0-10 presentation scale. Worked synthetic example: A=40 B=30 C=20 D=5 F=5 W=10 gives N=100, g=0.7375; with mu=0.70 and k=60, ease=7.234375 displayed as 7.2/10. Changing W alone must not change grade ease.
- scope: ease score method, methodology page

## REQ-GRADE-02: Prominent A rate with visible numerator and denominator
- source: docs/final-mvp-plan.md
- description: A rate is prominent and identifies its numerator and denominator.
- acceptance: `100 * A / N` where `N = A+B+C+D+F`. Display "A grades among A-F outcomes" and `A of N`. Excludes W/I/S/U/O. Null when N is zero or counts are unusable.
- scope: A rate, search results, section detail

## REQ-GRADE-03: Full observed A-F distribution
- source: docs/final-mvp-plan.md
- description: Students can see observed A/B/C/D/F counts and percentages.
- acceptance: Each A-F bucket shows its observed integer count and `100 * bucket / N`. F is included in the denominator. A text table accompanies the chart. W/I/S/U/O counts are listed beneath the distribution so students can reconcile A-F totals with all recorded outcomes. Do not invent finer distinctions such as A-minus if the source only provides an A bucket.
- scope: distribution chart, accessible count table

## REQ-GRADE-04: Separate observed withdrawal rate
- source: docs/final-mvp-plan.md
- description: Observed withdrawal rate appears separately, with its own denominator.
- acceptance: `100 * W / T` where `T = A+B+C+D+F+I+S+U+W+O`, verified against the source Total Grades field. Display `W of T recorded outcomes`. Not a percentage of current enrollment. Null when T is zero or invalid. Independent of grade ease.
- scope: withdrawal rate, denominator explanation

## REQ-EVID-01: Visible evidence scope and sample
- source: docs/final-mvp-plan.md
- description: Actual sample size, sections, named semesters, date coverage, and professor-course versus course-only history are visible.
- acceptance: Expose actual named semesters, earliest/latest included term, section count, N, T, evidence scope, fallback reason, source identity, data refresh time and methodology version. Evidence-strength labels are descriptive: "Limited" (fewer than 60 A-F outcomes), "Moderate" (60-179), "Strong" (at least 180), downgraded one level if only one term is covered. Labels are not probabilities of getting an A. Never call a subject reference cohort the professor's sample. Say "recorded outcomes" or "A-F grades", not "unique students".
- scope: evidence panel, labels

## REQ-EVID-02: No plausible default score from absent evidence
- source: docs/final-mvp-plan.md
- description: Missing, invalid, suppressed, or insufficient evidence never produces a plausible default score.
- acceptance: Independent nullable metric states - `available`, `insufficient`, `unavailable`, `suppressed`, `invalid` - each with a reason, not one blanket boolean. Require at least 20 A-F outcomes in the selected course cohort for a displayed adjusted score; smaller samples may show source-permitted observed counts/rates with a prominent "Small sample" label while the score says "Insufficient data". Source suppression rules take precedence over this display threshold. Require at least 60 eligible A-F reference outcomes for a reference mean; if no measured reference is available the adjusted score is unavailable with reason "Reference data unavailable" while valid observed grade facts remain visible. Never substitute 0.75, another hard-coded population mean, or a subject/global score. Zero-valued reference means stay valid. W-only history can provide a valid withdrawal rate but no A rate or ease. Unknown scores sort after known scores in either numeric direction; no hidden zero coercion; unscored rows get no apparent ease ranking.
- scope: metric states, sorting, no-fabrication

## REQ-RMP-01: Verified RMP profile link only
- source: docs/final-mvp-plan.md
- description: Only a verified "View on Rate My Professors" link is displayed for the applicable instructor.
- acceptance: Operator-maintained registry of instructor identity, university identity, canonical profile URL, verification status, verification timestamp and verification evidence/note, managed by CLI/import file and a validation command (no new admin UI). The profile must be verified against the named instructor and USF using identity evidence including department where needed; a search result or matching name alone is not verified. Only canonical HTTPS RMP profile URLs are allowed. Recheck when instructor assignments change and during launch curation. Ambiguous names, Staff, missing profiles and rejected matches show "Verified RMP link unavailable". No imported ratings, review counts, review text, tags or summaries, and no bulk RMP crawler.
- scope: RMP registry, verification, unavailable state

## REQ-POLICY-01: Supported policy chips with correct provenance and links
- source: docs/final-mvp-plan.md
- description: Existing supported policy chips retain evidence, source term, source scope, and a correct syllabus or schedule-source link.
- acceptance: Reuse the nine supported categories - attendance, late work, exams, exam location, participation, curve, lab, quiz, delivery format. Keep the current syllabus to supported schedule note to historical same instructor/course to historical same course precedence. Expose the resolved syllabus URL independently from extracted chips; a syllabus may exist even when no supported policy is found. Each chip retains its short evidence quote, source term, source type and link. Historical chips state whether the match is this professor/course or only the course. A schedule-note chip links to its schedule source and must not be labeled a syllabus quote. Never infer "no attendance requirement" from absent text. Do not silently combine contradictory sources.
- scope: policy extraction, syllabus links, provenance

## REQ-SEAT-01: Honest per-section seat state
- source: docs/final-mvp-plan.md
- description: Each section shows the latest known count, availability state, and last successful observation time.
- acceptance: Expose section number, source status, capacity, enrollment, seats remaining, waitlist seats, last successful observation, last attempt and freshness separately. Waitlist capacity is not an available course seat. Classify source-supported active sections with valid positive remaining seats as open, zero as full, and valid negative remaining seats as full/over capacity, preserving the signed observation for diagnostics. Invalid or contradictory values become unavailable. Cancellation, closed registration or incompatible source status must not be overruled by a positive count. An observed positive seat count means availability was reported, not that a particular student can enroll; link to official USF registration and do not automate registration.
- scope: seat projection, availability classification

## REQ-SEAT-02: Scheduled browser-independent refresh
- source: docs/final-mvp-plan.md
- description: A scheduled service refreshes availability and detects valid openings without depending on a student's browser.
- acceptance: A durable scheduled Python worker shares the existing PostgreSQL database. Network acquisition stays outside long database transactions. Poll bounded subject/course or CRN queries, sharing one observation among all subscribers; never poll once per subscriber and never let a student search trigger an upstream crawl. Proposed targets: watched sections every 5 minutes, remaining supported launch sections every 30 minutes, freshness expiring after two expected intervals - configurable product targets, not verified USF rate limits. Record failed attempts without advancing the successful observation timestamp. Do not classify empty/partial/error responses as zero seats or cancel sections on a single missing row. Store observations atomically, reject out-of-order state updates, serialize state transitions per term/CRN, persist polling leases/checkpoints and a worker heartbeat; restart must not lose monitoring state.
- scope: polling worker, cadence, failure handling

## REQ-ALERT-01: Verified email watch lifecycle
- source: docs/final-mvp-plan.md
- description: A student can verify an email address, watch a section, receive an availability email, and cancel or rearm the watch.
- acceptance: Rate-limited verification email; watch pending until a short-lived token is confirmed; no opening email to an unverified address. The confirmation page identifies course, term, section, CRN, current availability, monitoring cadence and watch status. An active watch is emailed when a fresh validated observation reports seats available; a known full-to-open transition is an opening, while a first known positive value or recovery after an unknown interval is described as "Seats are available" without inventing when it opened. The email includes observed seat count, checked-at time, term/CRN, section detail link, official registration link and unsubscribe action. Each verified watch sends one availability alert then becomes completed; the student can rearm through a private management link, and rearming while already open waits for a later confirmed full-to-open event. A private management page lists watches for the verified address and supports cancel and rearm, with an "Email me my management link" recovery flow and no passwords. Persist each watch trigger mode - `next_available` or `future_opening` - across restarts.
- scope: verification, alert delivery, management

## REQ-ALERT-02: Durable delivery with a transactional outbox
- source: docs/final-mvp-plan.md
- description: Delivery is durable, deduplicated and independent from opening detection. (Derived from the plan section 5 delivery contract supporting ALERT-01.)
- acceptance: Transactional outbox with a unique watch/event delivery key. Polling and delivery are independent jobs. Recheck that the watch is active and the latest state is fresh/open before sending queued availability messages; suppress outdated opening messages when the latest valid state is full or cancelled. Do not remove a pending delivery until success, permanent failure, expiry or explicit suppression is recorded. Persist retries, provider message IDs, next-attempt time and terminal state. Use provider idempotency to handle a crash after provider acceptance but before the database update. Do not promise exactly-once email delivery. With the proposed default provider Resend, the idempotency window is 24 hours; keep retries inside that window or reconcile uncertain results instead of blindly resending. A provider-accepted email is not proof of inbox delivery.
- scope: outbox, retries, idempotency

## REQ-ALERT-03: Token, privacy and abuse controls
- source: docs/final-mvp-plan.md
- description: Watch identity uses expiring scoped tokens and does not become an accounts product. (Derived from the plan section 5 security contract supporting ALERT-01.)
- acceptance: Expiring, purpose-scoped, random tokens stored as hashes. Verify/consume ownership tokens through deliberate confirmation rather than an email scanner GET request. Keep tokens and full email addresses out of logs and analytics. Scope unsubscribe tokens to the watch and support direct unsubscribe without login. Enforce per-address/IP limits, pending expiry, duplicate-watch protection, maximum active watches, and cancellation on term/registration expiry. Validate signed provider webhooks if used and suppress bounces/complaints. Store only the email and watch data needed for the service; publish and implement retention/deletion behavior. Use section/session registration deadlines where available, with an operator-configured cutoff when the source lacks them.
- scope: tokens, privacy, rate limiting

## REQ-UI-01: Responsive integrated UI across all surfaces and states
- source: docs/final-mvp-plan.md
- description: Search, details, methodology, and alert flows work on mobile and desktop, including all missing-data and failure states.
- acceptance: See constraints.md for the binding UI contract (docs/final-mvp-ui-spec.md, precedence 1). Browser verification at 360px, 768px and 1440px and at 200% zoom, with keyboard-only and screen-reader spot checks. Charts have a text alternative; focus is restored correctly; chips have readable contrast; small-sample and unknown states use text as well as color. Record screenshots of real integrated states. A static mockup, generated design image, fixture-only page or passing component test is not the finished UI. Fix the hard-coded Spring 2027 term preference and the implicit production fixture fallback.
- scope: search, detail, methodology, alerts, accessibility

## REQ-OPS-01: Production on real data with reproducible operations
- source: docs/final-mvp-plan.md
- description: Production runs against real data with reproducible deployment, monitoring, recovery, and demonstrated end-to-end behavior.
- acceptance: Import actual approved historical exports with correct terms and source provenance. Refresh declared launch schedule/catalog coverage, map historical instructors conservatively, ingest available syllabus documents and curate RMP links. Report coverage separately for searchable sections, grade evidence, professor-specific history, fresh seats, syllabi and verified RMP; honest unavailable labels are allowed, claiming broad coverage based on fixtures is not. Benchmark full-scope search, not one course. Add PostgreSQL integration tests for queries, migrations, job claiming, uniqueness and concurrency. Package API/frontend/worker, migration command and environment configuration; configure TLS/origins, persistent database, backup/restore, secrets, sender domain and scheduler. Add CI for Python and frontend checks and deployment smoke tests. Readiness tests database access; worker health exposes last successful tick and source freshness. Track poll failures, outbox backlog, retry age and email failures without logging personal data. Production must fail visibly on missing API configuration or use an explicitly configured same-origin API; never silently enter fixture mode.
- scope: real data, deployment, CI, monitoring

## REQ-LAUNCH-01: Declared launch coverage manifest
- source: docs/final-mvp-plan.md
- description: A launch coverage manifest defines the declared scope before implementation proceeds. (Derived from plan section 7, Phase 1.)
- acceptance: Define USF Tampa, supported registration term(s), supported subjects/courses, grade terms, default term, and refresh cadence. Include all intended courses in that declared scope; do not call a two-course fixture demo a finished campus product. Publish exclusions and missing historical coverage. Do not invent actual imported semesters or coverage percentages before inspecting available data. Historical-only terms must not automatically become selectable registration targets.
- scope: launch scope, metadata, coverage reporting

## REQ-DATA-01: Resolve grade-to-course identity and deduplicate sources
- source: docs/final-mvp-plan.md
- description: Historical grade rows must resolve to real course identity and be deduplicated before they can be used as evidence. (Derived from plan section 2 findings and section 3 cohort rules.)
- acceptance: Grade import initializes `course_id` to null, so importing XLSX files alone does not establish usable course coverage - preserve/resolve parsed course identity and backfill or explicitly exclude unresolved history. Grade rows are unique by term/CRN/source, not term/CRN alone, so explicit source selection is required to avoid double-counting duplicate exports. Historical instructor selection uses name-based joins across stored instructor observations; validate that old assignments, ambiguous names and co-teaching cannot attribute a whole section's grades to the wrong professor. Use verified Tampa history for the Tampa product; normalize and validate campus data rather than pooling campuses implicitly. Preserve course identity across catalog editions and term-scoped CRNs. Exclude unresolved, duplicate, conflicting, invalid or source-suppressed rows with recorded reasons. A blank source cell must not silently become zero unless documented export semantics permit it. Exclude current/future target terms from both observed history and references. Never average section percentages equally - sum eligible counts, then calculate rates.
- scope: grade ingestion, cohort eligibility, attribution
