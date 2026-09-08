# Roadmap: Easy-A

## Overview

Easy-A already searches USF Tampa sections and already stores most of the raw material it needs
— A-F grade buckets, syllabus policy extractions with provenance, seat snapshots. What it does
not yet do is show any of that honestly. A section with no grade history currently scores 7.8/10
from a hard-coded prior; A rates and bucket counts are stored but never rendered; seats are
labeled "current" regardless of age; there is no RMP integration, no email alert system, no
worker, no CI, no PostgreSQL test coverage and no deployment path.

This milestone takes the existing application to a deployed public release across eight delivery
phases. Phase 1 fixes the ground truth — baseline, declared launch scope, method contract, UI
contract — and answers the three open coverage questions before anything is built on top of them.
Phases 2 through 5 deliver the four evidence pillars end-to-end, each including its own feature
UI: honest grade evidence, verified source links, fresh seats with a scheduled worker, and
verified email watches with durable delivery. Phase 6 integrates and polishes the UI across all
five surfaces and every failure state. Phase 7 loads real data, adds the net-new PostgreSQL
tests and CI, and makes the system deployable. Phase 8 deploys, runs the acceptance matrix
against real data, and releases.

**These are eight delivery phases of ONE milestone, not eight MVPs.** The sequence and its
dependency edges are preserved verbatim from `docs/final-mvp-plan.md` section 7 and are locked by
ADR-15. GSD's default `standard` granularity (4-6 phases) was deliberately not applied:
compressing this structure would silently drop dependency edges the source states explicitly.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Baseline, Scope and Contracts** - Establish the real baseline, the declared launch coverage manifest, the locked method contract and the UI/state contract before implementation
- [ ] **Phase 2: Honest Grade Evidence, API Through UI** - Replace the composite score with grade-only method v2, expose observed A rate / distribution / withdrawal rate, and make every insufficient state explicit
- [ ] **Phase 3: Verified RMP and Policy Sources** - Curated RMP identity registry with verification, plus syllabus and schedule-source links with correct provenance
- [ ] **Phase 4: Fresh Seats and Scheduled Observation** - One seat source of truth with visible observation age, plus a durable polling worker with leases, transitions and failure handling
- [ ] **Phase 5: Email Watches** - Verified email watch lifecycle with a transactional outbox, one-alert-then-rearm semantics and a private management flow
- [ ] **Phase 6: Final Integrated UI** - All five surfaces and every failure state working on mobile and desktop, with browser and accessibility acceptance
- [ ] **Phase 7: Real Data, Performance and Deployment Readiness** - Real imported coverage, net-new PostgreSQL integration tests, net-new CI, benchmarks, packaging and operational readiness
- [ ] **Phase 8: Deployed Acceptance and Release** - Deployed end-to-end acceptance against real data, launch-blocking fixes, and the public release

**Dependency graph** (from `docs/final-mvp-plan.md` section 7, preserved):

```text
                    ┌──► 2 ──┐
                    │        │
  1 ────────────────┼──► 3 ──┼──► 6 ──┐
                    │        │        │
                    └──► 4 ──┴──► 5 ──┴──► 7 ──► 8
```

- Phase 2, 3 and 4 all depend only on Phase 1 and may proceed in parallel once Phase 1 exits.
- Phase 3 consumes the shared payload shape established in Phase 2 (soft edge, not a hard block).
- Phase 4 consumes the shared API/UI contract established in Phase 2 (soft edge).
- Phase 5 hard-depends on Phase 4 — there is nothing to alert on without validated openings.
- Phase 6 hard-depends on 2, 3, 4 and 5.
- Phase 7 depends on 2-6, with external provisioning identified in Phase 1.
- Phase 8 depends on 7.

## Phase Details

### Phase 1: Baseline, Scope and Contracts

**Goal**: The team knows exactly what baseline it is building on, what scope it has declared, and
what method and UI contracts every later phase must satisfy — with the three live coverage risks
answered by evidence rather than assumption.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-LAUNCH-01
**Also establishes**: REQ-EVID-01 / REQ-EVID-02 state definitions, REQ-UI-01 component and state
contract, REQ-OPS-01 source and provisioning planning
**Confirmed scope (2026-09-08)**: All offered USF Tampa sections, Spring 2027 (`202701`) only.
Samples validate acquisition before a complete subject/section reconciliation; unavailable
grades, instructor names, verified profiles, or syllabi must not remove sections from scope.
Reuse completed onboarding, maps and source specifications; investigate only remaining gaps.
**Success Criteria** (what must be TRUE):

  1. A published launch coverage manifest names USF Tampa, the supported registration term(s),
     the supported subjects/courses, the grade terms, the default term and the refresh cadence —
     with exclusions and missing historical coverage stated, and no invented semester or coverage
     percentage. Historical-only terms are not selectable registration targets.

  2. The implementation baseline is recorded and confirmed: which commit, which branch strategy,
     and what happens to the untracked `web/` directory on local `main`. The recorded exact
     baseline test counts (Python and frontend) replace both conflicting figures.

  3. A reader can reproduce method v2 from the written contract alone: the formula, `k`, `mu`,
     RULE-20, RULE-60A, RULE-60B, RULE-60C and RULE-K60 each stated separately with their own
     test intent, plus the confirmed source suppression and blank-cell interpretation.

  4. Named-instructor coverage and current-term syllabus availability across the *declared* launch
     scope are inventoried with counts, and the Phase 3 exit criterion is restated to match what
     the data actually supports.

  5. Every requirement in REQUIREMENTS.md maps to a phase, every UI screen and failure state is
     specified, and every external dependency (grade exports, host, domain, email provider, sender
     domain, test inbox) is listed with its owner and its blocked phase.
**Open questions resolved here**: OQ-01, OQ-02, OQ-03, OQ-04; OQ-05 identified
**Exit gate**: Baseline checks recorded; every requirement mapped; source gaps and owners listed;
formulas reproducible; UI screens and failure states specified. An unavailable grade export does
not block seat work, but it remains a grade-launch dependency.
**Scope decisions carried in, NOT resolved facts** (from `.planning/INGEST-CONFLICTS.md`):

  - **OQ-01 resolved, 2026-09-08.** The user confirmed implementation stays in worktrees off
    `origin/main`; leave local `main` and untracked work alone until developer 1 merges.
    Phase 1 planning stays on `claude/gsd-onboard-774626`, in the same PR as onboarding.
    Fresh fetch verified `origin/main` at `06634490` and current worktree ancestry.
    **The primary checkout remains protected.** `refs/heads/main` is still
    `d880d3c2bd31158c2392725e5c203ac92b2088fa`, the user's primary checkout is on it, and `web/`
    is untracked there (tracked at `06634490`). This ingest ran at `894da473` in a worktree
    descended from `origin/main` = `06634490de5c765bdc7b55e4f439476b0e4fa0f7`. PROJECT.md records
    that descendant-worktree baseline as the confirmed decision. **Do not overwrite untracked
    local work.** Exact baseline test counts remain open under OQ-04.

  - **RMP / instructor coverage risk.** All five sampled Spring 2027 Tampa `MAC 1105` sections and
    all 41 sampled `ENC 1101` sections show instructor `Staff`. This is a two-course sample, not a
    campus-wide fact. If it generalizes, verified RMP links and professor-specific grade evidence
    have near-zero launch coverage. The user has confirmed all Tampa offerings: retain every
    section and show course-only evidence where eligible plus "Verified RMP link unavailable"
    when verification is absent. Inventory actual coverage and condition Phase 3 real-example
    acceptance on that evidence. Do not narrow scope to courses with matches.

  - **Current-term syllabus risk.** No Spring 2027 syllabus was found for either sampled course;
    matching public library results were Fall 2026 only. If this generalizes, the historical-source
    path is **primary**, not a fallback, and "syllabus link exists but no chip extracted" is a
    primary Phase 3 acceptance case rather than an edge case.
**Plans**: 5 plans

Plans:
**Wave 1**

- [ ] 01-01-PLAN.md — Record the confirmed implementation baseline and write the method v2 reproducibility contract
- [ ] 01-02-PLAN.md — Build the bounded subject-enumeration inventory and run it to answer OQ-02 with counts

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-03-PLAN.md — Probe the syllabus search surface and answer OQ-03 with a bounded, labelled pass
- [ ] 01-04-PLAN.md — Write the UI/API state contract, verify requirement coverage, and register external dependencies

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-05-PLAN.md — Publish the launch coverage manifest and restate the Phase 3 exit criterion

**Waves**: 1 → plans 01 and 02 in parallel; 2 → plans 03 and 04 in parallel; 3 → plan 05.
Plans 02, 03 and 05 carry blocking human checkpoints and are not autonomous.
**UI hint**: yes

### Phase 2: Honest Grade Evidence, API Through UI

**Goal**: A student looking at any section sees only grade numbers that came from real observed
outcomes, with visible denominators and named terms — and sees an explicit reason instead of a
number wherever the evidence does not qualify.
**Depends on**: Phase 1
**Requirements**: REQ-GRADE-01, REQ-GRADE-02, REQ-GRADE-03, REQ-GRADE-04, REQ-EVID-01,
REQ-EVID-02, REQ-DATA-01
**Success Criteria** (what must be TRUE):

  1. A student sees a prominent A rate labeled "A grades among A-F outcomes" with its `A of N`
     denominator, a full A/B/C/D/F chart with an always-available count table, W/I/S/U/O counts
     listed separately beneath it, and a withdrawal rate labeled `W of T recorded outcomes` — all
     drawn from one explicitly selected and labeled cohort.

  2. A section with no usable grade history shows "Insufficient data" with a reason and **no
     number**; the 7.8/10-from-nothing behavior is gone, along with every subject/global displayed
     fallback and the 0.75/0.10 no-evidence defaults.

  3. The published methodology page states the exact grade-only formula, both denominators, the
     small-sample adjustment, the measured reference population, the method version and date, and
     a worked example explicitly labeled synthetic — reachable at `/methodology` from the header
     and from score help.

  4. A student can tell whose history they are looking at: "This professor + course" versus
     "Course only" with the fallback reason, named semesters, exact N and T, section count, and a
     descriptive Limited/Moderate/Strong label that is never presented as a probability.

  5. Changing only W, seats, policies, RMP or modality provably cannot change grade ease; unknown
     scores sort after known scores in both directions with no hidden zero coercion; and duplicate
     grade exports cannot double-count because source selection is explicit.
**Threshold rules delivered here**: RULE-20, RULE-60A, RULE-60B, RULE-60C, RULE-K60 — each
independently tested. A test exercising one is not coverage for another.
**Exit gate**: The worked example matches; zero-history and W-only sections behave correctly;
small samples cannot outrank supported evidence via fabricated scores; raw metrics share the
labeled cohort; changing only W/seats/policies/RMP cannot change grade ease. Proven through unit,
API and rendered UI tests including null sorting and term/CRN isolation.
**Baseline work**: net-new — A rate and bucket counts are stored internally but exposed nowhere;
`course_id` backfill/resolution and source-explicit dedup are new; the 80/20 composite and both
hard-coded priors are removed from `src/easy_a/analytics/scoring.py`.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Verified RMP and Policy Sources

**Goal**: Every source link a student follows lands on the correct, actually-verified source — and
where no verified source exists, the product says so rather than guessing.
**Depends on**: Phase 1; consumes the shared payload shape from Phase 2
**Requirements**: REQ-RMP-01, REQ-POLICY-01
**Success Criteria** (what must be TRUE):

  1. A "View on Rate My Professors" link appears only where an operator has verified the profile
     against both the named instructor and USF with recorded identity evidence and a timestamp;
     everywhere else the student sees "Verified RMP link unavailable".

  2. `Staff`, ambiguous names, missing profiles and rejected matches never produce a link, and no
     RMP rating, review count, review text, tag or summary exists anywhere in the database, API or
     UI.

  3. A policy chip shows its short evidence quote, its named source term, whether it is this
     professor/course or course-only, and a working link that is labeled correctly — a schedule
     note links to the schedule source and is never presented as a syllabus quote.

  4. A syllabus link is exposed independently of chips: a syllabus with no recognized supported
     policy still has a working "Open syllabus" link, and a clearly dated historical source is
     never presented as current.

  5. An operator can add, validate and re-verify registry entries through a CLI and an import file
     with a validation command — no new admin UI, and rechecks trigger when instructor assignments
     change.
**Exit gate**: A verified profile opens the correct professor/university; Staff/ambiguous
identities never link incorrectly; a historical syllabus displays its actual term and scope; a
current syllabus without recognized chips still has a working link. No imported RMP content
appears in database, API or UI.
**Carried from Phase 1**: the exit criterion above is stated as the source PRD wrote it. Per OQ-02
it may be unprovable with real launch data if named-instructor coverage is near zero — Phase 1
must restate it against actual coverage before this phase is planned. Per OQ-03 the historical
syllabus path and the "link but no chip" state are likely **primary** acceptance cases, not edge
cases; order tests accordingly.
**Baseline work**: RMP is entirely net-new (no integration exists). Policy extraction, provenance
and evidence quotes already exist in `src/easy_a/signals/` — the net-new work is rendering correct
source links, current-vs-historical badging and conflict states.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Fresh Seats and Scheduled Observation

**Goal**: A student can trust a seat count because they can see exactly when it was last
successfully checked — and the checking happens on a durable server-side schedule, not in their
browser.
**Depends on**: Phase 1; shared API/UI contract from Phase 2
**Requirements**: REQ-SEAT-01, REQ-SEAT-02
**Success Criteria** (what must be TRUE):

  1. Every section shows its availability state with an absolute and relative "checked at" time,
     and stale data reads "Last known: N seats — Checked [time] — Update overdue" rather than a
     green live-open badge.

  2. Waitlist seats are displayed separately and never counted as available course seats;
     cancelled, closed-registration or incompatible source status is never overruled by a positive
     count; valid negative remaining seats classify as full/over capacity with the signed
     observation preserved for diagnostics.

  3. Seats refresh on a schedule with no browser open: one shared observation serves every watcher,
     a student's search never triggers an upstream crawl, and worker restart preserves polling
     state, leases and checkpoints.

  4. A failed or partial upstream request records the attempt without advancing the successful
     observation timestamp, without fabricating zero seats and without cancelling a section on a
     single missing row.

  5. The "open seats only" filter returns only sections with a fresh, valid, positive count and a
     compatible source status, and every section links to official USF registration with no
     automated registration anywhere.
**Exit gate**: Deterministic full→open, open→open, full→unknown→open, out-of-order,
partial-response, cancelled-with-positive-count and outage/recovery scenarios pass. A narrow real
schedule check validates source parsing. Worker restart preserves state and one observation serves
multiple watchers.
**Baseline defect to resolve, not paper over**: `.planning/codebase/CONCERNS.md` and the PRD
independently identify two parallel seat sources of truth — canonical `Section` columns written by
`src/easy_a/schedule/ingest.py` and appended `SeatSnapshot` rows — with a fallback in
`src/easy_a/rankings/service.py` that reports `sections.current_seat_fields` provenance, so a
stale column can look current. Adding timestamps on top of the dual source does not satisfy
ADR-06. Note also that `SeatSnapshot` currently grows unbounded with no change-dedup or retention.
**Baseline work**: schedule client, section columns, snapshots and the open-seat filter exist. The
worker, leases, heartbeat, transition serialization, freshness expiry and validated availability
classification are net-new.
**Plans**: TBD
**UI hint**: yes

### Phase 5: Email Watches

**Goal**: A student who verifies their email address is told once, reliably, when a watched section
reports seats — and can cancel, rearm or unsubscribe without an account.
**Depends on**: Phase 4
**Requirements**: REQ-ALERT-01, REQ-ALERT-02, REQ-ALERT-03
**Success Criteria** (what must be TRUE):

  1. A student submits an email for a specific section, deliberately confirms a short-lived
     ownership token, and sees an active watch naming the exact course, term, section, CRN, current
     availability, cadence and the one-alert behavior — with no email ever sent to an unverified
     address.

  2. When a fresh validated observation reports seats, the student receives exactly one email
     containing the observed count, the checked-at time, term/CRN, a section detail link, the
     official registration link and an unsubscribe action; the watch then reads "completed" and
     offers rearm.

  3. Repeated polls, transient provider errors, a crash between provider acceptance and the
     database update, expired jobs and worker restart do not produce duplicate mail — and an
     opening message queued before the section closed again is suppressed rather than sent.

  4. A student reaches a private management page from an emailed link, sees only their own watches,
     and can cancel, rearm or stop all — while a token cannot read or change another recipient's
     watches and expired tokens offer a new-link flow.

  5. The product never claims inbox delivery: "Availability email sent" appears only after provider
     acceptance, and provider acceptance is described as acceptance.
**Exit gate**: Controlled source transitions generate one durable delivery per watch; repeated
polls and worker restart do not duplicate; unverified/cancelled/expired watches cannot send; stale
or now-closed events are suppressed; tokens cannot access another recipient's watches. Verification,
availability email and unsubscribe demonstrated with a designated test inbox after it is supplied
and authorized.
**External dependencies (OQ-05)**: email provider account, sender-domain ownership and DNS setup,
and a designated test inbox. These are prerequisites, not tasks. Do not purchase services (ADR-17).
One provider behind a replaceable transport; Resend is the proposed default with a 24-hour
idempotency window — keep retries inside that window or reconcile rather than blindly resending.
**Baseline work**: entirely net-new. No subscriptions, tokens, email transport, outbox or delivery
code exists.
**Plans**: TBD
**UI hint**: yes

### Phase 6: Final Integrated UI

**Goal**: A student with no developer knowledge can find a class, understand what every number
means, follow its sources, and manage an email watch — on a phone or a desktop, with a keyboard or
a screen reader.
**Depends on**: Phases 2, 3, 4, 5
**Requirements**: REQ-UI-01
**Verifies**: REQ-GRADE-01..04, REQ-EVID-01, REQ-EVID-02, REQ-RMP-01, REQ-POLICY-01,
REQ-ALERT-01 as integrated rendered behavior
**Success Criteria** (what must be TRUE):

  1. All five surfaces work end to end — search/results, linkable section detail, methodology/data
     coverage, watch signup/confirmation, private watch management — with A rate leading the
     hierarchy without hiding uncertainty.

  2. Search state (term, query, filters, sort, page) lives in the URL: sharing a link or pressing
     Back restores the same results, position and filters, and section detail is a real linkable
     route keyed by term and CRN.

  3. Every required failure and empty state renders correctly and is reachable in a browser: no
     history, small sample, no measured reference, W-only, suppressed/invalid source, no professor
     match, no current syllabus, missing RMP verification, full/over capacity, stale seats,
     unknown/cancelled, API outage, and empty or unsupported-term search.

  4. Verification passes at 360px, 768px and 1440px and at 200% zoom, with keyboard-only
     navigation, persistent visible focus, focus restoration from drawers and dialogs, chart text
     alternatives, readable chip contrast, and status conveyed by text and not by color alone.

  5. Production never shows synthetic data: the implicit fixture fallback in
     `web/src/api/rankings.ts` and the hard-coded Spring 2027 term preference are both gone, and a
     missing API configuration fails visibly.
**Exit gate**: A student can find a class, understand A/W denominators, inspect evidence, open the
correct source and manage an email watch without developer knowledge. UI tests and visual
acceptance cover all required failure/empty states, and production has no synthetic results.
Screenshots of real integrated states recorded for representative available, insufficient and
stale cases. A static mockup, generated design image, fixture-only page or passing component test
is not a substitute.
**Plans**: TBD
**UI hint**: yes

### Phase 7: Real Data, Performance and Deployment Readiness

**Goal**: The system runs on real imported USF data at declared launch scale, on the database
dialect it actually deploys to, fast enough to use, and can be deployed and operated
reproducibly.
**Depends on**: Phases 2-6; external provisioning identified in Phase 1
**Requirements**: REQ-OPS-01
**Verifies**: REQ-DATA-01, REQ-EVID-01, REQ-EVID-02, REQ-RMP-01, REQ-POLICY-01, REQ-SEAT-01,
REQ-SEAT-02, REQ-ALERT-01..03, REQ-LAUNCH-01 against real data
**Success Criteria** (what must be TRUE):

  1. Real approved historical grade exports are imported with correct terms and source provenance,
     the declared launch schedule/catalog coverage is refreshed, syllabi are ingested and RMP links
     are curated — with coverage reported **separately** for searchable sections, grade evidence,
     professor-specific history, fresh seats, syllabi and verified RMP. Honest unavailable labels
     are fine; claiming coverage based on fixtures is not.

  2. PostgreSQL integration tests pass for queries, migrations, job claiming, uniqueness and
     concurrency — closing the gap where every existing test runs on in-memory SQLite and Alembic
     migrations are never applied.

  3. CI runs Python checks (`ruff`, `mypy`, `pytest`), frontend checks (`tsc -b`, `vitest`,
     ESLint) and deployment smoke tests on every change.

  4. Measured benchmark evidence exists for full-scope search — not one course — against the
     budgets: search p95 ≤ 2s at 20 concurrent users, usable search within 3s on the agreed mobile
     profile, watched sections observed within the 5-minute target, queue-to-provider acceptance
     within 60s of a validated opening. Recorded as measurements, not promises.

  5. A reproducible staging deployment exists with API, frontend and worker packaged, a migration
     command, TLS/origins, a persistent database, secrets, a validated sender domain and a
     scheduler — plus readiness that tests database access, worker health exposing last successful
     tick and source freshness, a completed backup restore drill, and an operator runbook.
**Exit gate**: Real coverage report, passing PostgreSQL checks, benchmark evidence, reproducible
staging deployment, validated sender setup, backup restore drill, restart behavior and operator
runbook. External credentials and domain ownership are specific dependencies, not tasks to
silently skip.
**Baseline work — both net-new, not modifications**:

  - **PostgreSQL tests**: `tests/conftest.py` builds `sqlite+pysqlite:///:memory:` and uses
    `Base.metadata.create_all`; the deployment target is PostgreSQL 16 and migrations have never
    been exercised. Nothing exists to modify.

  - **CI**: there is no `.github/` directory and no CI config anywhere in the repository. Nothing
    exists to modify.

  - Also net-new: any Dockerfile, production ASGI configuration, frontend serve path, and
    structured logging (there is no logging configuration in `src/easy_a/` at all).
**Known performance work**: `GET /api/v1/rankings/search` ranks every section in the term before
slicing pagination, issuing ~6 queries per section, and recomputes course analytics per CRN. Cache
keys must include data and method versions; seat freshness and watch processing must not depend on
ranking caches.
**External dependencies (OQ-05)**: real approved grade exports and their actual terms, deployment
host, domain, email sender domain. Named dependencies, not skippable tasks.
**Plans**: TBD

### Phase 8: Deployed Acceptance and Release

**Goal**: The product is actually deployed, actually running on real data, and a real student
journey has been verified end to end on it — or the specific blocking dependency is named and the
acceptance item is left explicitly incomplete.
**Depends on**: Phase 7
**Requirements**: REQ-OPS-01 (deployed release, health, recovery and operator handoff)
**Verifies**: all 17 requirements via the final acceptance matrix in REQUIREMENTS.md
**Success Criteria** (what must be TRUE):

  1. Every row of the final acceptance matrix has recorded evidence from the deployed system
     running against real imported aggregates and live public schedule observations — supported
     professor history, course-only history, no usable history, small/invalid/suppressed data,
     sources, seats, email lifecycle, delivery resilience, privacy, mobile/desktop, real launch and
     operations.

  2. A student journey completes on the deployed URL: find a real section → read observed grades
     and evidence → follow a verified source → see an honestly timestamped seat count → receive and
     manage a verified email alert.

  3. Where no live full-to-open transition occurred, an opening was simulated through a clearly
     isolated test adapter and that evidence is labeled honestly — no real USF section was altered
     to force a transition, and the production source adapter, worker scheduling and delivery
     transport are separately verified.

  4. The release record exists: release commit, deployed URL, environment and method versions,
     coverage figures and runbook location — with production configuration verified and production
     fixture mode confirmed disabled.

  5. Any acceptance item blocked by an unavailable external dependency is left **explicitly
     incomplete** with a precise statement of what is needed. The milestone is not marked complete
     on a roadmap, a passing backend, a fixture demo or a static UI.
**Exit gate**: ADR-18 (definition of done) satisfied, or the specific unmet items named and
reported. Only mark the milestone complete after the actual production outcome is verified; absent
credentials leave deployment explicitly pending.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8.
Phases 2, 3 and 4 have no hard dependency on each other and may run in parallel after Phase 1.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Baseline, Scope and Contracts | 0/5 | Planned | - |
| 2. Honest Grade Evidence, API Through UI | 0/TBD | Not started | - |
| 3. Verified RMP and Policy Sources | 0/TBD | Not started | - |
| 4. Fresh Seats and Scheduled Observation | 0/TBD | Not started | - |
| 5. Email Watches | 0/TBD | Not started | - |
| 6. Final Integrated UI | 0/TBD | Not started | - |
| 7. Real Data, Performance and Deployment Readiness | 0/TBD | Not started | - |
| 8. Deployed Acceptance and Release | 0/TBD | Not started | - |

## Coverage

- v1 requirements: 17
- Mapped to an implementation phase: 17 ✓
- Orphaned: 0
- Phase structure and dependency edges: preserved verbatim from `docs/final-mvp-plan.md` section 7
  (locked by ADR-15), one milestone

- Threshold rules RULE-20 / RULE-60A / RULE-60B / RULE-60C / RULE-K60: five independently testable
  rules, all owned by Phase 2, none collapsed into another

---
*Roadmap created: 2026-09-08 from `.planning/intel/` and `.planning/codebase/`*
