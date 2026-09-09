# Decisions (ADR intel)

Extracted from documents classified `ADR`. Precedence rank 0 (highest).
One source doc in this ingest set: `docs/gsd-core-mvp-prompt.md` (`locked: true`).

Its fenced block is written as instructions addressed to an AI agent. Per the ingest
directive it was treated strictly as source material. Its LOCKED RULES, DEFAULTS,
scope items and DONE MEANS are extracted below as document content only. No
directive inside it was executed.

---

## ADR-01: Preserve the existing application architecture
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Preserve the existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vite/Tailwind architecture. Work in the existing repository; do not rewrite the application or create a separate product.
- scope: backend stack, frontend stack, repository identity

## ADR-02: Historical grade ease is grade-only
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Historical grade ease is not the existing 80% grade / 20% withdrawal composite. Remove subject/global displayed-score fallbacks and fixed 0.75/0.10 no-evidence defaults.
- scope: ease score method, score fallbacks, no-evidence defaults

## ADR-03: A prior may adjust real evidence but never substitute for it
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: A prior may adjust a real eligible sample; it cannot stand in for this course's history. Unknown is not zero. Same-cohort raw rates and distribution must reconcile.
- scope: shrinkage prior, null semantics, cohort reconciliation

## ADR-04: Respect source identity and conservative attribution
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Respect term/CRN identity, actual campus scope, real grade-file terms, source suppression, deduplication and conservative professor attribution.
- scope: grade ingestion, cohort selection, instructor attribution

## ADR-05: Non-grade signals must not change the grade score
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: RMP, syllabus, seats, modality and GenEd must not change the grade score.
- scope: score isolation

## ADR-06: Seat observation honesty
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Seat observation age must be visible. Failed requests must not advance the success timestamp, fabricate zero seats or generate opening events. Waitlist capacity is separate from available seats.
- scope: seat freshness, failure handling, waitlist separation

## ADR-07: Email monitoring is a durable server-side service
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Email monitoring must run without an open browser, share polling across subscribers, survive restart and use a persisted outbox with idempotency and bounded retries. Do not claim exactly-once inbox delivery.
- scope: polling worker, delivery outbox, delivery guarantees

## ADR-08: Verified email ownership, not an accounts product
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Use verified email ownership and private management links; do not expand this into a general accounts product. No email to unverified subscribers.
- scope: identity, watch management, scope boundary

## ADR-09: No-fabrication and no-scope-expansion boundary
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: No production synthetic fallback, guessed profile link, unsupported policy assertion, silent scope expansion, auto-registration, SMS, push, payments, or AI features.
- scope: product boundary, production data integrity

## ADR-10: RMP is a verified link only
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: A verified "View on Rate My Professors" profile link. No imported ratings, review counts, reviews, tags, scraping, or AI summaries.
- scope: Rate My Professors integration

## ADR-11: Explicit insufficient-data states
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Explicit unavailable/insufficient/suppressed/invalid states. Never generate an apparently reasonable score from absent course history.
- scope: metric states, UI states

## ADR-12: Implementation defaults for the launch method
- source: docs/gsd-core-mvp-prompt.md
- status: locked (default set; revisable only with documented evidence)
- decision: Use the explicit proposed defaults in the plan - 0-10 grade-only shrinkage, k=60, a 20-outcome score floor, a 60-outcome professor-history threshold, empirical reference data, no recency weighting, a configurable five-minute watched-seat target, and one availability alert per watch followed by an explicit rearm action. These are implementation defaults, not calibrated scientific claims or verified upstream rate limits. Revise only with documented evidence and update methodology/tests consistently. Preserve all locked user requirements.
- scope: method parameters, alert lifecycle, polling cadence

## ADR-13: Baseline and branch safety
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Fetch origin/main and inspect its current commit before planning. The handoff audited 06634490de5c765bdc7b55e4f439476b0e4fa0f7, which already includes FastAPI, the React frontend, real-data refresh and quality checks. The older local main was d880d3c and had untracked web files. Preserve untracked/user work and start implementation from current main in a safe codex/ branch or worktree. Reconcile newer changes rather than assuming the audit is still exact.
- scope: baseline commit, branch strategy, preservation of untracked work
- note: see INGEST-CONFLICTS.md WARNING 1 - the stale-local-main condition is still live as of this ingest.

## ADR-14: Use the GSD Core .planning structure
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Use GSD Core's installed workflows and .planning/ structure, not GSD2 .gsd/ milestone conventions. Bootstrap from the supplied documents when no planning setup exists; merge with existing state and continue its phase numbering when it does. Check the installed workflow syntax before use. Keep the handoff docs available across worktrees.
- scope: planning system, phase numbering

## ADR-15: Delivery outcome sequence
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Create traceable requirements and a complete roadmap matching eight delivery outcomes - (1) baseline, launch data/source coverage, method and UI contracts; (2) honest grade evidence end-to-end (ingestion/linkage, analytics, API, observed rates/distribution, insufficient states, methodology UI); (3) verified RMP links and supported policy/syllabus source UI; (4) validated seat freshness, scheduled polling, transitions, failure handling and seat UI; (5) verified email watches, outbox delivery, management/cancellation/rearm UI and provider integration; (6) integrated mobile/desktop UI, deep links, accessibility and browser acceptance; (7) declared real-data coverage, PostgreSQL integration, measured performance, CI, deployment and operational readiness; (8) deployed end-to-end acceptance, fixes and final public release.
- scope: roadmap shape
- note: matches the PRD Phase 1-8 table (docs/final-mvp-plan.md section 7) one-to-one.

## ADR-16: Validation and operations obligations
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Preserve the existing passing baseline and update tests for changed semantics. Cover no history, W-only data, small samples, zero-valued priors, ambiguous instructors, duplicate sources, cross-term CRNs, nullable sorting, stale/cancelled/contradictory seats, duplicate polling, provider retries, worker crashes, token expiry and unsubscribe. Add real PostgreSQL tests for query/migration/concurrency behavior; current baseline Python tests are SQLite-based. Perform integrated browser checks at 360/768/1440px and keyboard/zoom checks. Demonstrate a narrow real schedule observation and controlled opening transitions without changing real university data. Distinguish provider acceptance from inbox receipt.
- scope: test coverage, database testing, browser acceptance, email validation

## ADR-17: Never invent coverage, permissions, credentials or completion
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: Identify missing real grade exports, launch term/subject scope, source cadence, hosting/domain credentials, sender-domain setup and test inbox early. Continue independent work while those dependencies are resolved. Ask only for necessary external input or an explicit product change, not to repeat settled scope. Never invent data coverage, source permissions, credential access or deployment completion. Do not purchase services. Before any external approval that is actually required, make the proposed result concrete and reviewable.
- scope: external dependencies, honesty constraints

## ADR-18: Definition of done
- source: docs/gsd-core-mvp-prompt.md
- status: locked
- decision: A deployed responsive product lets a student find a real section, inspect observed grades and evidence, follow verified sources, see honestly timestamped seats, and receive/manage a verified email alert. Real data refresh, worker scheduling, delivery, monitoring, recovery and the operator runbook are demonstrated. Record the release commit, URL, method version, coverage and acceptance evidence. If an external dependency prevents deployment or real email validation, leave that acceptance item explicitly incomplete and report exactly what is needed. Do not stop at a roadmap, backend completion, fixture demo or static UI.
- scope: release acceptance
