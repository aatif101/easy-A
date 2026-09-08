# Easy-A

## What This Is

Easy-A is a course-search website for USF Tampa students. A student finds a real section
and sees, for that section, what the historical grade distribution actually looked like,
how strong that evidence is, which syllabus policies are supported by a quotable source, a
verified Rate My Professors profile link where one genuinely exists, and how many seats were
available the last time the section was successfully checked. If the section is full, the
student can hand over a verified email address and be told once when seats are reported open.

It is an existing application, not a greenfield build. Python 3.12 / FastAPI / SQLAlchemy /
Alembic / PostgreSQL 16 on the backend, React 19 / TypeScript / Vite / Tailwind on the
frontend, plus a net-new durable scheduled worker that shares the same PostgreSQL database.

## Core Value

Every number a student sees is a real observed outcome with a visible denominator, a named
source and a timestamp — and when the evidence does not exist, the product says so instead of
producing a plausible-looking score.

## Requirements

### Validated

<!-- Shipped and confirmed working at baseline commit 06634490. Verified against
     .planning/codebase/ (map date 2026-09-05). These are the platform the milestone
     builds on, not milestone scope. -->

- ✓ Layered FastAPI backend with read-only `/api/v1/rankings/{section,course,search}` and
  `/api/v1/metadata` routes — `src/easy_a/api/`
- ✓ Ingest pipelines for catalog, schedule, syllabi and grades, each shaped
  `client.py → parser.py → ingest.py → cli.py`, orchestrated by `src/easy_a/refresh/service.py`
- ✓ XLSX grade-distribution import covering all ten grade buckets, totals, source hashes and
  term/CRN joins — `src/easy_a/grades/`
- ✓ Deterministic syllabus policy extraction for nine supported categories with provenance and
  short evidence quotes — `src/easy_a/signals/`
- ✓ Alembic migrations `0001_create_data_core` and `0002_create_section_syllabus_tables`
- ✓ React SPA with responsive table/cards, metadata-backed filters, pagination, expandable
  details and error/loading/empty states — `web/src/`
- ✓ Python test suite (~154 tests per `.planning/codebase/TESTING.md`; the handoff PRD records
  166 at commit `06634490` — see OQ-04) and 19 frontend tests, all passing at baseline
- ✓ Strict quality gates: ruff (`B,C4,E,F,I,SIM,UP`), mypy `strict = true` across
  `src migrations scripts tests`, ESLint + `tsc -b` for the frontend

### Active

<!-- v1 milestone scope. Full text and acceptance criteria in .planning/REQUIREMENTS.md. -->

- [ ] **REQ-GRADE-01** — Grade-only historical ease with a published method (v2 formula)
- [ ] **REQ-GRADE-02** — Prominent A rate with visible numerator and denominator
- [ ] **REQ-GRADE-03** — Full observed A-F distribution with an accessible count table
- [ ] **REQ-GRADE-04** — Separate observed withdrawal rate with its own denominator
- [ ] **REQ-EVID-01** — Visible evidence scope, sample size and named semesters
- [ ] **REQ-EVID-02** — No plausible default score from absent evidence
- [ ] **REQ-RMP-01** — Verified RMP profile link only
- [ ] **REQ-POLICY-01** — Supported policy chips with correct provenance and links
- [ ] **REQ-SEAT-01** — Honest per-section seat state with observation age
- [ ] **REQ-SEAT-02** — Scheduled browser-independent seat refresh
- [ ] **REQ-ALERT-01** — Verified email watch lifecycle
- [ ] **REQ-ALERT-02** — Durable delivery with a transactional outbox
- [ ] **REQ-ALERT-03** — Token, privacy and abuse controls
- [ ] **REQ-UI-01** — Responsive integrated UI across all surfaces and states
- [ ] **REQ-OPS-01** — Production on real data with reproducible operations
- [ ] **REQ-LAUNCH-01** — Declared launch coverage manifest
- [ ] **REQ-DATA-01** — Grade-to-course identity resolution and source deduplication

### Out of Scope

Sourced from `docs/final-mvp-plan.md` section 1 and locked by ADR-09/ADR-10.

- Imported RMP ratings, review counts, review text, tags or summaries — ADR-10 permits only a
  verified profile link; importing content is a licensing and accuracy liability
- RMP scraping or any bulk RMP crawler — same reason; the registry is operator-curated
- AI summaries, AI scoring, predicted personal grades, workload predictions — ADR-09 forbids
  fabricated signals; historical outcomes are not personal predictions
- Difficulty inferred from syllabus wording — inference is not evidence; only quotable
  supported chips are shown
- Social reviews, schedule generation, degree planning — different products, not this one
- Payments, SMS, browser push, native apps — ADR-09 explicit scope boundary
- Automatic registration — the product links to official USF registration and never automates it
- Multi-university expansion — USF Tampa only for this milestone
- A general user-profile / account system — ADR-08 permits verified email ownership and private
  management links only; no passwords, no accounts product
- Recency weighting of grade cohorts — ADR-12 keeps it disabled for this launch

## Context

**Repository state.** This is a brownfield repo with a mapped codebase
(`.planning/codebase/`, map date 2026-09-05) and an ingested handoff document set
(`.planning/intel/`, four documents: one locked ADR, one SPEC, one PRD, one observational DOC).
The delivery phase structure and dependency graph in `.planning/ROADMAP.md` are preserved
verbatim from `docs/final-mvp-plan.md` section 7 — they are eight delivery phases of ONE
milestone, not eight MVPs.

**What already exists vs what is net-new** (from `.planning/codebase/`):

| Area | Already exists | Net-new in this milestone |
|------|----------------|---------------------------|
| Backend platform | FastAPI app factory, DI, schemas, domain services, ORM, Alembic | Production config, worker process, health/readiness, structured logging |
| Grade import | XLSX parser, all ten buckets, totals, source hashes | `course_id` resolution/backfill, source-explicit dedup, eligibility rules |
| Ease score | 0-10 score, shrinkage, low/med/high labels in `analytics/scoring.py` | Remove the 80/20 composite and the `0.75`/`0.10` no-evidence priors; publish method v2 |
| A rate / distribution | A-F counts stored internally | Nothing is exposed through the ranking payload or rendered — full API + UI build |
| Withdrawal rate | Raw rate computed internally; API/UI serve a smoothed rate | Expose observed `W/T` with its own denominator, independent of ease |
| RMP | Nothing | Entire curated identity registry, import/validation CLI, API fields, UI states |
| Policies | Nine-category extraction, provenance, evidence quotes, stored syllabus URLs | Render correct source links, current-vs-historical badges, conflict states |
| Seats | Schedule client, `Section` columns, appended `SeatSnapshot` rows, open-seat filter | Single source of truth, validated freshness, scheduled worker, transitions, failure handling |
| Alerts | Nothing | Entire subscriber/watch/token/outbox system, email transport, management UI |
| Tests | ~154 Python + 19 frontend, all on SQLite | **PostgreSQL integration tests are net-new** — no test has ever run on the deployment dialect |
| CI | Nothing — no `.github/` directory, no CI config anywhere | **CI is a net-new build**, not a modification |
| Deployment | `docker-compose.yml` provisions PostgreSQL only | No Dockerfile, no ASGI production config, no frontend serve path — all net-new |

**Known baseline defects the milestone must resolve** (evidence-backed, not speculation):

- With no grade history the composite returns **7.8/10** from the `0.75` grade prior and `0.10`
  withdrawal prior — confirmed present in `src/easy_a/analytics/scoring.py`
  (`DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR = 0.75`, `DEFAULT_GLOBAL_WITHDRAWAL_RATE_PRIOR = 0.10`)
- Two parallel seat sources of truth — canonical `Section` columns written by
  `src/easy_a/schedule/ingest.py` and `SeatSnapshot` rows — with a fallback in
  `src/easy_a/rankings/service.py` that reports `sections.current_seat_fields` provenance, so a
  stale column can look current. Directly threatens ADR-06 and REQ-SEAT-01.
- Grade import initializes `course_id` to null, so importing XLSX files alone does not establish
  usable course coverage
- Grade rows are unique by term/CRN/**source**, not term/CRN, so duplicate exports double-count
  without explicit source selection
- `web/src/api/rankings.ts` silently serves 287 lines of synthetic fixtures when
  `VITE_API_BASE_URL` is unset — a misconfigured deploy renders plausible fake course data
- The frontend hard-codes a Spring 2027 term preference
- `GET /api/v1/rankings/search` ranks every section in the term before slicing pagination,
  issuing ~6 queries per section

**Live-source reality** (`docs/live-source-drift-2026-09-01.md`, observational only, sampled
two courses): every observed Spring 2027 Tampa section in the sample has instructor `Staff`; no
current-term syllabus was found for either sampled course; and CRN `19410` published
`190/207/-17`, confirming that upstream genuinely emits negative seats-remaining. These are
point-in-time observations from a two-course sample, not campus-wide facts. See OQ-02 and OQ-03.

## Constraints

- **Baseline (confirmed by user, 2026-09-08; OQ-01 resolved)**: All implementation stays in
  worktrees descended from `origin/main`, fetched and verified on 2026-09-08 at
  `06634490de5c765bdc7b55e4f439476b0e4fa0f7`. Continue Phase 1 planning on
  `claude/gsd-onboard-774626` in `.claude/worktrees/gsd-onboard-774626`, keeping its planning
  commits in the same PR as onboarding. Before this resolution, the branch was at
  `1653f2b3f276e7e7aac746f816a452be0fde73c2`; ancestry from `origin/main` was verified.
  Fetch and inspect current `origin/main` before subsequent planning, reconciling newer changes
  as required by ADR-13. — ADR-13 requires starting
  from current main, and `06634490` (PR #12) is the audited commit that already includes FastAPI,
  the React frontend, real-data refresh and quality checks.
- **Do not overwrite untracked local work**: `refs/heads/main` is still
  `d880d3c2bd31158c2392725e5c203ac92b2088fa`, the user's primary checkout at
  `C:/Users/smati/VS Code Projects/easy-A` is on it, and `git status` there reports untracked
  `web/` plus untracked copies of the four handoff documents. `web/` is untracked at `d880d3c`
  but tracked at `06634490`. — Any checkout, merge or fast-forward onto local `main` can destroy
  untracked user work. **Leave local `main` and its untracked files alone until developer 1
  merges.** OQ-01 resolves where implementation happens; it does not clean up the primary
  checkout or authorize an automatic checkout/merge/fast-forward after that merge.
- **Tech stack**: Preserve Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and
  React/TypeScript/Vite/Tailwind; work in this repository — ADR-01 forbids a rewrite or a
  separate product.
- **Score isolation**: RMP, syllabus, seats, modality and GenEd must not enter the grade score —
  ADR-05. Changing only W, seats, policies or RMP must not change grade ease.
- **No fabrication in production**: no synthetic fallback, guessed profile link, unsupported
  policy assertion, silent scope expansion or auto-registration — ADR-09.
- **Deployment topology**: one API service + one worker + PostgreSQL, built frontend served by
  the existing hosting arrangement; PostgreSQL outbox with `SKIP LOCKED` for job claiming; no
  Redis/Celery unless measured requirements justify it — CON-OPS-01.
- **Email provider**: one provider behind a replaceable transport; Resend is the proposed default
  with a 24-hour idempotency window; sender-domain ownership and DNS are prerequisites, not tasks
  — CON-OPS-01, REQ-ALERT-02. Do not purchase services (ADR-17).
- **Test dialect gap**: Python tests run on `sqlite+pysqlite:///:memory:` while deployment targets
  PostgreSQL 16, and Alembic migrations are never applied in tests (`Base.metadata.create_all`
  instead) — ADR-16 requires closing both.
- **Performance budgets (targets, not promises)**: representative search p95 ≤ 2s at 20 concurrent
  users; usable search within 3s on the agreed mobile profile; watched sections observed within
  the 5-minute target; queue-to-provider acceptance within 60s of a validated opening — CON-NFR-01.
- **Accessibility**: 360 / 768 / 1440px layouts, 200% zoom, ~44px touch targets, keyboard-only and
  screen-reader spot checks, charts with text alternatives — CON-UI-09.
- **Planning system**: GSD Core `.planning/` structure, not GSD2 `.gsd/` — ADR-14.

## Locked Decisions

All 18 decisions below come from `docs/gsd-core-mvp-prompt.md`, the single locked ADR
(precedence rank 0) in this ingest set. They are LOCKED: not revisable by a plan, a phase or an
implementation convenience. ADR-12 is the one partial exception — it is a locked *default set*,
revisable only with documented evidence, and only with methodology and tests updated together.
Full text: `.planning/intel/decisions.md`.

<decisions>

### Locked (ADR, docs/gsd-core-mvp-prompt.md, precedence 0)

- **D-ADR-01 [locked]:** Preserve the existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vite/Tailwind architecture. Work in the existing repository; do not rewrite the application or create a separate product.
- **D-ADR-02 [locked]:** Historical grade ease is grade-only. It is not the existing 80% grade / 20% withdrawal composite. Remove subject/global displayed-score fallbacks and the fixed 0.75/0.10 no-evidence defaults.
- **D-ADR-03 [locked]:** A prior may adjust a real eligible sample; it cannot stand in for this course's history. Unknown is not zero. Same-cohort raw rates and distribution must reconcile.
- **D-ADR-04 [locked]:** Respect term/CRN identity, actual campus scope, real grade-file terms, source suppression, deduplication and conservative professor attribution.
- **D-ADR-05 [locked]:** RMP, syllabus, seats, modality and GenEd must not change the grade score.
- **D-ADR-06 [locked]:** Seat observation age must be visible. Failed requests must not advance the success timestamp, fabricate zero seats or generate opening events. Waitlist capacity is separate from available seats.
- **D-ADR-07 [locked]:** Email monitoring must run without an open browser, share polling across subscribers, survive restart and use a persisted outbox with idempotency and bounded retries. Do not claim exactly-once inbox delivery.
- **D-ADR-08 [locked]:** Use verified email ownership and private management links; do not expand this into a general accounts product. No email to unverified subscribers.
- **D-ADR-09 [locked]:** No production synthetic fallback, guessed profile link, unsupported policy assertion, silent scope expansion, auto-registration, SMS, push, payments or AI features.
- **D-ADR-10 [locked]:** RMP is a verified "View on Rate My Professors" profile link only. No imported ratings, review counts, reviews, tags, scraping or AI summaries.
- **D-ADR-11 [locked]:** Explicit unavailable/insufficient/suppressed/invalid states. Never generate an apparently reasonable score from absent course history.
- **D-ADR-12 [locked-default]:** Use the proposed launch defaults — 0-10 grade-only shrinkage, k=60 prior strength, a 20-outcome displayed-score floor, a 60-outcome professor-history threshold, empirical reference data, no recency weighting, a configurable five-minute watched-seat target, and one availability alert per watch followed by an explicit rearm. These are implementation defaults, not calibrated scientific claims or verified upstream rate limits. Revise only with documented evidence, updating methodology and tests consistently. Preserve all locked user requirements.
- **D-ADR-13 [locked]:** Fetch origin/main and inspect its current commit before planning. The handoff audited 06634490de5c765bdc7b55e4f439476b0e4fa0f7. The older local main was d880d3c with untracked web files. Preserve untracked/user work and start implementation from current main in a safe branch or worktree. Reconcile newer changes rather than assuming the audit is still exact.
- **D-ADR-14 [locked]:** Use GSD Core's installed workflows and .planning/ structure, not GSD2 .gsd/ milestone conventions. Bootstrap from the supplied documents when no planning setup exists; merge and continue phase numbering when it does. Keep the handoff docs available across worktrees.
- **D-ADR-15 [locked]:** Deliver eight traceable outcomes in sequence — (1) baseline, launch data/source coverage, method and UI contracts; (2) honest grade evidence end-to-end; (3) verified RMP links and supported policy/syllabus source UI; (4) validated seat freshness, scheduled polling, transitions, failure handling and seat UI; (5) verified email watches, outbox delivery, management/cancellation/rearm UI and provider integration; (6) integrated mobile/desktop UI, deep links, accessibility and browser acceptance; (7) declared real-data coverage, PostgreSQL integration, measured performance, CI, deployment and operational readiness; (8) deployed end-to-end acceptance, fixes and final public release.
- **D-ADR-16 [locked]:** Preserve the existing passing baseline and update tests for changed semantics. Cover no history, W-only data, small samples, zero-valued priors, ambiguous instructors, duplicate sources, cross-term CRNs, nullable sorting, stale/cancelled/contradictory seats, duplicate polling, provider retries, worker crashes, token expiry and unsubscribe. Add real PostgreSQL tests for query/migration/concurrency behavior; the current baseline Python tests are SQLite-based. Perform integrated browser checks at 360/768/1440px plus keyboard and zoom checks. Demonstrate a narrow real schedule observation and controlled opening transitions without changing real university data. Distinguish provider acceptance from inbox receipt.
- **D-ADR-17 [locked]:** Identify missing real grade exports, launch term/subject scope, source cadence, hosting/domain credentials, sender-domain setup and test inbox early. Continue independent work while those dependencies are resolved. Ask only for necessary external input or an explicit product change. Never invent data coverage, source permissions, credential access or deployment completion. Do not purchase services. Before any external approval that is actually required, make the proposed result concrete and reviewable.
- **D-ADR-18 [locked]:** Done means a deployed responsive product where a student finds a real section, inspects observed grades and evidence, follows verified sources, sees honestly timestamped seats, and receives and manages a verified email alert. Real data refresh, worker scheduling, delivery, monitoring, recovery and the operator runbook are demonstrated. Record the release commit, URL, method version, coverage and acceptance evidence. If an external dependency prevents deployment or real email validation, leave that acceptance item explicitly incomplete and report exactly what is needed. Do not stop at a roadmap, backend completion, fixture demo or static UI.

</decisions>

## Open Questions

OQ-01 was resolved by the user on 2026-09-08. OQ-02 through OQ-05 remain open.
OQ-01 through OQ-03 originated as WARNINGs in `.planning/INGEST-CONFLICTS.md`; the remaining
scope questions must be answered with evidence before the phase that depends on them is planned.

| ID | Question | Blocks | Resolve by |
|----|----------|--------|------------|
| OQ-01 (resolved) | User confirmed: keep implementation in worktrees off `origin/main`; leave local `main` and its untracked `web/` and handoff docs alone until developer 1 merges. Continue Phase 1 planning on the onboarding branch, in the same PR. Fresh fetch confirmed `origin/main` = `06634490`; current worktree ancestry verified. | None for Phase 1 planning; primary checkout remains protected | Resolved 2026-09-08 |
| OQ-02 | How many sections in the *intended* launch scope have named instructors rather than `Staff`? All five sampled `MAC 1105` and all 41 sampled `ENC 1101` Spring 2027 Tampa sections showed `Staff`. If that generalizes, REQ-RMP-01 and professor-specific grade evidence have near-zero real coverage at launch and Phase 3's "a verified profile opens the correct professor/university" exit criterion is unprovable with real data. Options: choose launch subjects that include named instructors, **or** explicitly accept course-only evidence plus "Verified RMP link unavailable" as the launch-normal state and restate Phase 3's exit criterion. Do not silently narrow scope to whichever courses happen to have RMP matches. | Phase 3 exit criterion; Phase 1 coverage manifest | Phase 1 (inventory during REQ-LAUNCH-01) |
| OQ-03 | Is current-term syllabus availability generally as thin as the sample suggests? No Spring 2027 syllabus was found for either sampled course; matching public library results were Fall 2026 only. If it generalizes, the **historical-source path is primary, not a fallback**, and the "syllabus link exists but no chip extracted" state is a primary acceptance case for Phase 3 rather than an edge case. Building and testing the current-syllabus branch first would leave actual launch behavior least exercised. | Phase 3 test ordering and acceptance cases | Phase 1 |
| OQ-04 | Exact baseline test count. The PRD records 166 Python / 19 frontend passing at `06634490`; `.planning/codebase/TESTING.md` records ~154 Python at `894da473`. ADR-16 locks "preserve the existing passing baseline", so the true number matters as a regression reference. | Phase 1 exit ("baseline checks recorded") | Phase 1 |
| OQ-05 | External dependencies not yet supplied (ADR-17): real approved grade export files and their actual terms, exact launch term/subject scope, deployment host and domain, email provider account and sender-domain DNS, and a designated test inbox. Each is a named dependency, not a task that can be silently skipped. | Phases 5, 7, 8 | Identify in Phase 1; resolve before the dependent phase |

## Key Decisions

<!-- Project-level choices made during planning. Locked ADR decisions live in the
     <decisions> block above and are not repeated here. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Preserve the source PRD's 8 delivery phases and dependency graph verbatim | `docs/final-mvp-plan.md` section 7 and ADR-15 agree one-to-one on the sequence, and ADR-15 is locked. GSD's default `standard` granularity (4-6 phases) was deliberately not applied — compressing would drop dependency edges the source states explicitly. | — Pending |
| Treat the eight phases as ONE milestone | The PRD states plainly: "These are delivery phases, not multiple MVPs." | — Pending |
| Keep implementation in worktrees off `origin/main`; keep Phase 1 planning on the onboarding branch | User confirmed this strategy on 2026-09-08. Fresh fetch verified `06634490` and the current worktree's ancestry. Leave local `main` and untracked work alone until developer 1 merges; planning stays in the onboarding PR. | Confirmed; OQ-01 resolved |
| Keep the three uses of "60" as independently testable rules | `.planning/INGEST-CONFLICTS.md` INFO 3: the ADR's summary phrase "a 60-outcome professor-history threshold" is lossy. The professor-history threshold, the reference-mean threshold and the Limited/Moderate label boundary are three different rules that happen to share a number — plus `k=60` is a fourth. See REQUIREMENTS.md "Threshold rules". | — Pending |
| Subject/corpus data supplies `mu` only, never a displayed score | Resolves the apparent ADR-02 vs PRD-section-3 tension by precedence (INFO 2). When no measured reference qualifies, the adjusted score is unavailable with reason "Reference data unavailable" — never 0.75 or any hard-coded mean. | — Pending |
| PostgreSQL integration tests and CI are net-new builds, not modifications | `.planning/codebase/TESTING.md` (SQLite-only, migrations never applied) and `CONCERNS.md` (no `.github/`, no CI config anywhere) both confirm nothing exists to modify. | — Pending |

---
*Last updated: 2026-09-08 after user confirmation and verification of the OQ-01 worktree strategy*
