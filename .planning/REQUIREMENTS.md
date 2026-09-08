# Requirements: Easy-A

**Defined:** 2026-09-08 (from document ingest — see `.planning/intel/requirements.md`)
**Core Value:** Every number a student sees is a real observed outcome with a visible
denominator, a named source and a timestamp — and when the evidence does not exist, the product
says so instead of producing a plausible-looking score.

**Sources.** 13 requirements carry the source PRD's own IDs (`docs/final-mvp-plan.md` section 1
table). 4 are derived from prose contracts in the same PRD and are marked `derived`. Native IDs
are preserved inside the `REQ-` slug so the source's own traceability table (section 7) still
resolves. Binding UI/API/calculation detail lives in `.planning/intel/constraints.md`
(CON-UI-01..09, CON-CALC-01..02, CON-API-01, CON-OPS-01, CON-NFR-01).

**Precedence on any contradiction:** ADR (`docs/gsd-core-mvp-prompt.md`) > SPEC
(`docs/final-mvp-ui-spec.md`) > PRD (`docs/final-mvp-plan.md`) > DOC
(`docs/live-source-drift-2026-09-01.md`).

---

## v1 Requirements

### Grade evidence

- [ ] **REQ-GRADE-01**: Historical grade ease comes only from grade distributions, with a
  published formula and small-sample adjustment.
  *Acceptance*: Method v2 is `g = (4A + 3B + 2C + D) / (4N)`;
  `adjusted_g = (N*g + k*mu) / (N+k)`; `historical_grade_ease = 10 * adjusted_g`. `mu` is a
  **measured** reference grade-favorability mean from eligible imported history; `k` is prior
  strength. No withdrawals, RMP data, seats, syllabus signals, modality or GenEd enter the
  calculation. Retain the 0-10 presentation scale. Worked synthetic example: A=40 B=30 C=20 D=5
  F=5 W=10 gives N=100, g=0.7375; with mu=0.70 and k=60, ease=7.234375 displayed as 7.2/10.
  Changing W alone must not change grade ease.

- [ ] **REQ-GRADE-02**: A rate is prominent and identifies its numerator and denominator.
  *Acceptance*: `100 * A / N` where `N = A+B+C+D+F`. Display "A grades among A-F outcomes" and
  `A of N`. Excludes W/I/S/U/O. Null when N is zero or counts are unusable.

- [ ] **REQ-GRADE-03**: Students can see observed A/B/C/D/F counts and percentages.
  *Acceptance*: Each A-F bucket shows its observed integer count and `100 * bucket / N`. F is
  included in the denominator. A text table accompanies the chart. W/I/S/U/O counts are listed
  beneath the distribution so students can reconcile A-F totals with all recorded outcomes. Do
  not invent finer distinctions such as A-minus if the source only provides an A bucket.

- [ ] **REQ-GRADE-04**: Observed withdrawal rate appears separately, with its own denominator.
  *Acceptance*: `100 * W / T` where `T = A+B+C+D+F+I+S+U+W+O`, verified against the source Total
  Grades field. Display `W of T recorded outcomes`. Not a percentage of current enrollment. Null
  when T is zero or invalid. Independent of grade ease.

- [ ] **REQ-EVID-01**: Actual sample size, sections, named semesters, date coverage, and
  professor-course versus course-only history are visible.
  *Acceptance*: Expose actual named semesters, earliest/latest included term, section count, N,
  T, evidence scope, fallback reason, source identity, data refresh time and methodology
  version. Evidence-strength labels are descriptive (see RULE-60C) and are **not** probabilities
  of getting an A. Never call a subject reference cohort the professor's sample. Say "recorded
  outcomes" or "A-F grades", not "unique students".

- [ ] **REQ-EVID-02**: Missing, invalid, suppressed, or insufficient evidence never produces a
  plausible default score.
  *Acceptance*: Independent nullable metric states — `available`, `insufficient`, `unavailable`,
  `suppressed`, `invalid` — each with a reason, not one blanket boolean. Enforce RULE-20,
  RULE-60A and RULE-60B independently. Source suppression rules take precedence over the display
  threshold. Never substitute 0.75, another hard-coded population mean, or a subject/global
  score. Zero-valued reference means stay valid. W-only history can provide a valid withdrawal
  rate but no A rate or ease. Unknown scores sort after known scores in either numeric direction;
  no hidden zero coercion; unscored rows get no apparent ease ranking.

- [ ] **REQ-DATA-01** *(derived — plan section 2 findings + section 3 cohort rules)*: Historical
  grade rows resolve to real course identity and are deduplicated before they can be used as
  evidence.
  *Acceptance*: Grade import currently initializes `course_id` to null, so importing XLSX files
  alone does not establish usable course coverage — preserve/resolve parsed course identity and
  backfill or explicitly exclude unresolved history. Grade rows are unique by term/CRN/**source**,
  not term/CRN, so explicit source selection is required to avoid double-counting duplicate
  exports. Historical instructor selection uses name-based joins across stored instructor
  observations; validate that old assignments, ambiguous names and co-teaching cannot attribute a
  whole section's grades to the wrong professor. Use verified Tampa history for the Tampa product;
  normalize and validate campus data rather than pooling campuses implicitly. Preserve course
  identity across catalog editions and term-scoped CRNs. Exclude unresolved, duplicate,
  conflicting, invalid or source-suppressed rows with recorded reasons. A blank source cell must
  not silently become zero unless documented export semantics permit it. Exclude current/future
  target terms from both observed history and references. Never average section percentages
  equally — sum eligible counts, then calculate rates.

### Sources and provenance

- [ ] **REQ-RMP-01**: Only a verified "View on Rate My Professors" link is displayed for the
  applicable instructor.
  *Acceptance*: Operator-maintained registry of instructor identity, university identity,
  canonical profile URL, verification status, verification timestamp and verification
  evidence/note, managed by a CLI/import file and a validation command (no new admin UI). The
  profile must be verified against the named instructor **and** USF using identity evidence
  including department where needed; a search result or matching name alone is not verified. Only
  canonical HTTPS RMP profile URLs are allowed. Recheck when instructor assignments change and
  during launch curation. Ambiguous names, `Staff`, missing profiles and rejected matches show
  "Verified RMP link unavailable". No imported ratings, review counts, review text, tags or
  summaries, and no bulk RMP crawler.
  *Coverage risk*: see PROJECT.md OQ-02 — all sampled Spring 2027 Tampa sections show `Staff`.

- [ ] **REQ-POLICY-01**: Existing supported policy chips retain evidence, source term, source
  scope, and a correct syllabus or schedule-source link.
  *Acceptance*: Reuse the nine supported categories — attendance, late work, exams, exam
  location, participation, curve, lab, quiz, delivery format. Keep the precedence chain: current
  syllabus → supported schedule note → historical same instructor/course → historical same
  course. Expose the resolved syllabus URL independently from extracted chips; a syllabus may
  exist even when no supported policy is found. Each chip retains its short evidence quote,
  source term, source type and link. Historical chips state whether the match is this
  professor/course or only the course. A schedule-note chip links to its schedule source and must
  not be labeled a syllabus quote. Never infer "no attendance requirement" from absent text. Do
  not silently combine contradictory sources.
  *Coverage risk*: see PROJECT.md OQ-03 — the historical-source path is likely primary, not a
  fallback.

### Seats

- [ ] **REQ-SEAT-01**: Each section shows the latest known count, availability state, and last
  successful observation time.
  *Acceptance*: Expose section number, source status, capacity, enrollment, seats remaining,
  waitlist seats, last successful observation, last attempt and freshness **separately**. Waitlist
  capacity is not an available course seat. Classify source-supported active sections with valid
  positive remaining seats as open, zero as full, and valid negative remaining seats as full/over
  capacity, preserving the signed observation for diagnostics. Invalid or contradictory values
  become unavailable. Cancellation, closed registration or incompatible source status must not be
  overruled by a positive count. An observed positive seat count means availability was reported,
  not that a particular student can enroll; link to official USF registration and do not automate
  registration.
  *Baseline defect*: the dual seat source of truth (`Section` columns vs `SeatSnapshot`, with a
  `sections.current_seat_fields` fallback) must be resolved, not merely timestamped over.

- [ ] **REQ-SEAT-02**: A scheduled service refreshes availability and detects valid openings
  without depending on a student's browser.
  *Acceptance*: A durable scheduled Python worker shares the existing PostgreSQL database. Network
  acquisition stays outside long database transactions. Poll bounded subject/course or CRN
  queries, sharing one observation among all subscribers; never poll once per subscriber and never
  let a student search trigger an upstream crawl. Proposed targets: watched sections every 5
  minutes, remaining supported launch sections every 30 minutes, freshness expiring after two
  expected intervals — configurable product targets, not verified USF rate limits. Record failed
  attempts without advancing the successful observation timestamp. Do not classify empty/partial/
  error responses as zero seats or cancel sections on a single missing row. Store observations
  atomically, reject out-of-order state updates, serialize state transitions per term/CRN, persist
  polling leases/checkpoints and a worker heartbeat; restart must not lose monitoring state.

### Email alerts

- [ ] **REQ-ALERT-01**: A student can verify an email address, watch a section, receive an
  availability email, and cancel or rearm the watch.
  *Acceptance*: Rate-limited verification email; watch pending until a short-lived token is
  confirmed; no opening email to an unverified address. The confirmation page identifies course,
  term, section, CRN, current availability, monitoring cadence and watch status. An active watch
  is emailed when a fresh validated observation reports seats available; a known full-to-open
  transition is an opening, while a first known positive value or recovery after an unknown
  interval is described as "Seats are available" without inventing when it opened. The email
  includes observed seat count, checked-at time, term/CRN, section detail link, official
  registration link and unsubscribe action. Each verified watch sends **one** availability alert
  then becomes completed; the student can rearm through a private management link, and rearming
  while already open waits for a later confirmed full-to-open event. A private management page
  lists watches for the verified address and supports cancel and rearm, with an "Email me my
  management link" recovery flow and no passwords. Persist each watch trigger mode —
  `next_available` or `future_opening` — across restarts.

- [ ] **REQ-ALERT-02** *(derived — plan section 5 delivery contract)*: Delivery is durable,
  deduplicated and independent from opening detection.
  *Acceptance*: Transactional outbox with a unique watch/event delivery key. Polling and delivery
  are independent jobs. Recheck that the watch is active and the latest state is fresh/open before
  sending queued availability messages; suppress outdated opening messages when the latest valid
  state is full or cancelled. Do not remove a pending delivery until success, permanent failure,
  expiry or explicit suppression is recorded. Persist retries, provider message IDs, next-attempt
  time and terminal state. Use provider idempotency to handle a crash after provider acceptance
  but before the database update. Do not promise exactly-once email delivery. With the proposed
  default provider Resend the idempotency window is 24 hours; keep retries inside that window or
  reconcile uncertain results instead of blindly resending. A provider-accepted email is not proof
  of inbox delivery.

- [ ] **REQ-ALERT-03** *(derived — plan section 5 security contract)*: Watch identity uses
  expiring scoped tokens and does not become an accounts product.
  *Acceptance*: Expiring, purpose-scoped, random tokens stored as hashes. Verify/consume ownership
  tokens through deliberate confirmation rather than an email scanner GET request. Keep tokens and
  full email addresses out of logs and analytics. Scope unsubscribe tokens to the watch and
  support direct unsubscribe without login. Enforce per-address/IP limits, pending expiry,
  duplicate-watch protection, maximum active watches, and cancellation on term/registration
  expiry. Validate signed provider webhooks if used and suppress bounces/complaints. Store only
  the email and watch data needed for the service; publish and implement retention/deletion
  behavior. Use section/session registration deadlines where available, with an
  operator-configured cutoff when the source lacks them.

### Interface

- [ ] **REQ-UI-01**: Search, details, methodology, and alert flows work on mobile and desktop,
  including all missing-data and failure states.
  *Acceptance*: The binding contract is CON-UI-01 through CON-UI-09 in
  `.planning/intel/constraints.md` (source: `docs/final-mvp-ui-spec.md`, precedence 1). Five
  required surfaces: search/results, linkable section details, methodology/data coverage, watch
  signup/confirmation, private watch management. Browser verification at 360px, 768px and 1440px
  and at 200% zoom, with keyboard-only and screen-reader spot checks. Charts have a text
  alternative; focus is restored correctly; chips have readable contrast; small-sample and unknown
  states use text as well as color. Record screenshots of real integrated states. A static mockup,
  generated design image, fixture-only page or passing component test is not the finished UI. Fix
  the hard-coded Spring 2027 term preference and the implicit production fixture fallback in
  `web/src/api/rankings.ts`.

### Launch and operations

- [ ] **REQ-LAUNCH-01** *(derived — plan section 7, Phase 1)*: A launch coverage manifest defines
  the declared scope before implementation proceeds.
  *Acceptance*: User-confirmed launch scope (2026-09-08): all offered USF Tampa sections in
  Spring 2027 (`202701`), the only supported and default registration term. Enumerate every
  offered subject/course; record actual historical grade terms and refresh cadence. Samples
  validate acquisition before full expansion; do not call a two-course fixture demo a finished
  campus product. Missing evidence does not exclude a section. Publish exclusions and
  missing historical coverage. Do not invent actual imported semesters or coverage percentages
  before inspecting available data. Historical-only terms must not automatically become selectable
  registration targets. Must also inventory named-instructor coverage (OQ-02) and current-term
  syllabus availability (OQ-03) within the declared scope.

- [ ] **REQ-OPS-01**: Production runs against real data with reproducible deployment, monitoring,
  recovery, and demonstrated end-to-end behavior.
  *Acceptance*: Import actual approved historical exports with correct terms and source
  provenance. Refresh declared launch schedule/catalog coverage, map historical instructors
  conservatively, ingest available syllabus documents and curate RMP links. Report coverage
  separately for searchable sections, grade evidence, professor-specific history, fresh seats,
  syllabi and verified RMP; honest unavailable labels are allowed, claiming broad coverage based
  on fixtures is not. Benchmark full-scope search, not one course. Add PostgreSQL integration
  tests for queries, migrations, job claiming, uniqueness and concurrency (**net-new** — no test
  has ever run on the deployment dialect, and migrations are never applied in tests). Package
  API/frontend/worker, migration command and environment configuration; configure TLS/origins,
  persistent database, backup/restore, secrets, sender domain and scheduler. Add CI for Python and
  frontend checks plus deployment smoke tests (**net-new** — there is no `.github/` directory and
  no CI config anywhere in the repo). Readiness tests database access; worker health exposes last
  successful tick and source freshness. Track poll failures, outbox backlog, retry age and email
  failures without logging personal data. Production must fail visibly on missing API
  configuration or use an explicitly configured same-origin API; never silently enter fixture mode.

---

## Threshold rules

Four distinct numeric rules in this product involve the number 60, plus one 20-outcome floor.
They are recorded separately because the locked ADR's summary phrase "a 60-outcome
professor-history threshold" is lossy (`.planning/INGEST-CONFLICTS.md` INFO 3). **Each is
independently testable. Do not collapse them, and do not merge any of them with the display-only
label boundaries.**

| Rule | Statement | Kind | Owning requirement | Phase |
|------|-----------|------|--------------------|-------|
| **RULE-20** | Require at least **20 A-F outcomes** in the selected course cohort before a displayed adjusted score is shown. Smaller samples may show source-permitted observed counts/rates with a prominent "Small sample" label while the score reads "Insufficient data". Source suppression rules take precedence over this display threshold. | Gating (score eligibility) | REQ-EVID-02 | 2 |
| **RULE-60A** | Prefer same-professor / same-course evidence over course-only evidence **only after** conservative identity resolution **and** at least **60 A-F outcomes** in that professor-course cohort. | Gating (cohort selection) | REQ-EVID-02, REQ-DATA-01 | 2 |
| **RULE-60B** | Require at least **60 eligible A-F reference outcomes** before a reference mean `mu` may be computed. If no measured reference qualifies, the adjusted score is **unavailable** with reason "Reference data unavailable" while valid observed grade facts remain visible. Zero-valued reference means stay valid. Never fall back to 0.75 or any hard-coded mean. | Gating (reference eligibility) | REQ-EVID-02, CON-CALC-02 | 2 |
| **RULE-60C** | Evidence-strength label boundaries: "Limited" under 60 A-F outcomes, "Moderate" 60-179, "Strong" 180 or more, downgraded one level if only one term is covered. **Display-only and descriptive.** These are not probabilities of getting an A and have no effect on score eligibility or cohort selection. | Display label | REQ-EVID-01 | 2 |
| **RULE-K60** | `k = 60` is the shrinkage **prior strength** in `adjusted_g = (N*g + k*mu) / (N+k)`. It is a formula coefficient, not a count threshold, and is unrelated to RULE-60A/B/C. | Formula coefficient | REQ-GRADE-01, ADR-12 | 2 |

RULE-60A, RULE-60B and RULE-60C must each have their own tests. A test that exercises one must
not be treated as coverage for another. `.planning/codebase/CONCERNS.md` notes that
`src/easy_a/analytics/confidence.py` already hardcodes `LOW_CONFIDENCE_MAX_EFFECTIVE_N = 60.0`
and `HIGH_CONFIDENCE_MIN_EFFECTIVE_N = 180.0` against *effective* N — that is the existing
approximation of RULE-60C and must be re-derived against observed A-F outcome counts, not
effective N.

### Reference cohort chain (supplies `mu` only)

Per CON-CALC-02 and INFO 2: for professor-course history, try other sections of the same course
first; otherwise other courses in the subject; then the eligible institutional reference corpus.
For a course-only cohort, start with other courses in its subject. Exclude the displayed cohort
from the reference at every level. **This chain supplies `mu` only.** ADR-02 and ADR-03 (locked)
forbid any subject-level or corpus-level value from becoming a displayed score.

---

## v2 Requirements

None. The source PRD defines a single milestone with no deferred-but-tracked tier — everything
not in v1 is in Out of Scope below.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Imported RMP ratings, review counts, review text, tags, summaries | ADR-10: verified profile link only; importing content is a licensing and accuracy liability |
| RMP scraping / bulk RMP crawler | ADR-10; the registry is operator-curated and manually verified |
| AI summaries, AI scoring, AI-inferred difficulty | ADR-09 no-fabrication boundary |
| Predicted personal grades, workload predictions | Historical outcomes are not personal predictions (REQ-EVID-01) |
| Difficulty inferred from syllabus wording | Inference is not evidence; only quotable supported chips ship |
| Social reviews | Different product |
| Schedule generation, degree planning | Different product |
| Payments, SMS, browser push, native apps | ADR-09 explicit scope boundary |
| Automatic registration | Link to official USF registration only; ADR-09 |
| Multi-university expansion | USF Tampa only for this milestone |
| General user-profile / account system | ADR-08: verified email ownership + private management links, no passwords, no accounts product |
| Recency weighting of grade cohorts | ADR-12 keeps it disabled for this launch; CON-CALC-01 |
| Redis / Celery platform | CON-OPS-01: unnecessary unless measured requirements justify it; PostgreSQL `SKIP LOCKED` outbox suffices |
| New admin UI for the RMP registry | REQ-RMP-01: CLI/import file and a validation command instead |

---

## Traceability

Phase mapping preserved from `docs/final-mvp-plan.md` section 7. **Implementation phase** owns
delivery of the requirement. **Integrated proof** phases verify it end-to-end without adding new
implementation scope — this two-column structure is the source PRD's own, not an artifact of
double-mapping.

| Requirement | Implementation phase | Integrated proof | Status |
|-------------|----------------------|------------------|--------|
| REQ-GRADE-01 | Phase 2 | Phases 6, 8 | Pending |
| REQ-GRADE-02 | Phase 2 | Phases 6, 8 | Pending |
| REQ-GRADE-03 | Phase 2 | Phases 6, 8 | Pending |
| REQ-GRADE-04 | Phase 2 | Phases 6, 8 | Pending |
| REQ-EVID-01 | Phase 2 (scope defined Phase 1) | Phases 6, 7, 8 | Pending |
| REQ-EVID-02 | Phase 2 (states defined Phase 1) | Phases 6, 7, 8 | Pending |
| REQ-DATA-01 | Phase 2 | Phases 7, 8 | Pending |
| REQ-RMP-01 | Phase 3 | Phases 6, 7, 8 | Pending |
| REQ-POLICY-01 | Phase 3 | Phases 6, 7, 8 | Pending |
| REQ-SEAT-01 | Phase 4 | Phases 7, 8 | Pending |
| REQ-SEAT-02 | Phase 4 | Phases 7, 8 | Pending |
| REQ-ALERT-01 | Phase 5 | Phases 6, 7, 8 | Pending |
| REQ-ALERT-02 | Phase 5 | Phases 7, 8 | Pending |
| REQ-ALERT-03 | Phase 5 | Phases 7, 8 | Pending |
| REQ-UI-01 | Phase 6 (contract Phase 1; feature UI Phases 2-5) | Phase 8 | Pending |
| REQ-OPS-01 | Phase 7 (source planning Phase 1) | Phase 8 | Pending |
| REQ-LAUNCH-01 | Phase 1 | Phases 7, 8 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to an implementation phase: 17
- Unmapped: 0 ✓
- Every phase 1-7 owns at least one requirement; Phase 8 owns the deployed-release half of
  REQ-OPS-01 and provides integrated proof for all 17.

### Final acceptance matrix

From `docs/final-mvp-plan.md` section 8. This is the release gate verified in Phase 8, and it is
half of the project's success definition (the other half is ADR-18, in PROJECT.md `<decisions>`).

| Scenario | Required evidence | Requirements |
|----------|-------------------|--------------|
| Supported professor history | Displayed A rate, buckets, W rate, score, N/T and terms reconcile with a selected actual aggregate; professor identity is supported | GRADE-01..04, EVID-01, DATA-01 |
| Course-only history | Staff/unknown or insufficient professor evidence clearly uses course-only history; same-course sections do not claim different professor scores without evidence | EVID-01, EVID-02, DATA-01, RULE-60A |
| No usable history | Section is searchable with "Insufficient data"/reason; no numeric stand-in score and no invented grade percentages | EVID-02 |
| Small, invalid or suppressed data | Raw metrics follow source permission and denominator rules; adjusted score eligibility is enforced in backend **and** UI | EVID-02, RULE-20, RULE-60B |
| Sources | A verified RMP link opens the correct profile; current/historical syllabus links and policy quotes match the displayed source | RMP-01, POLICY-01 |
| Seats | Actual observation time is visible; stale/unknown/invalid/cancelled states do not masquerade as open; waitlist seats remain separate | SEAT-01, SEAT-02 |
| Email lifecycle | Verification → active watch → one availability alert → completed/rearm or unsubscribe works with a test inbox | ALERT-01 |
| Delivery resilience | Duplicate polls, transient errors, crash around provider acceptance, expired jobs and restarts do not create uncontrolled duplicate mail or false availability | ALERT-02, SEAT-02 |
| Privacy | Other recipients' watches cannot be read or changed; tokens expire; logs and public responses do not expose email addresses or credentials | ALERT-03 |
| Mobile/desktop | Search/filter → detail → methodology/source → watch → manage works at target sizes with keyboard, visible focus and chart text alternatives | UI-01 |
| Real launch | Coverage manifest and dashboard values use real data; production fixture mode is disabled; declared support matches coverage | LAUNCH-01, OPS-01 |
| Operations | Production URL works; migrations, health, polling, delivery, recovery and backup restoration have recorded evidence | OPS-01 |

---
*Requirements defined: 2026-09-08 from `.planning/intel/requirements.md`*
*Last updated: 2026-09-08 after initial roadmap creation*
