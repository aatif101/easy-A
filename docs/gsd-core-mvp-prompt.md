# Ready-to-paste GSD Core prompt

Paste the block below into GSD Core while working in this repository. Keep the companion plan and UI contract available in the implementation checkout. This starts planning and execution in GSD Core; the current planning task has not executed the application changes.

```text
Use GSD Core to take the existing Easy-A application from current main to the complete, deployed MVP described below. Work in this existing repository and preserve its stack and completed features.

Read these authoritative handoff documents first:
- docs/final-mvp-plan.md
- docs/final-mvp-ui-spec.md
- docs/gsd-mvp-manifest.yaml

BASELINE AND SETUP
Fetch origin/main and inspect its current commit before planning. The handoff audited 06634490de5c765bdc7b55e4f439476b0e4fa0f7, which already includes FastAPI, the React frontend, real-data refresh and quality checks. The older local main was d880d3c and had untracked web files. Preserve untracked/user work and start implementation from current main in a safe codex/ branch or worktree. Reconcile newer changes rather than assuming the audit is still exact.

Use GSD Core's installed workflows and .planning/ structure, not GSD2 .gsd/ milestone conventions. If no planning setup exists, bootstrap it from the supplied documents using $gsd-ingest-docs --manifest docs/gsd-mvp-manifest.yaml. If planning already exists, merge with its existing state and continue its phase numbering. Check the installed workflow syntax before use. Keep the handoff docs available across worktrees. Do not rewrite the application or create a separate product.

FINAL SCOPE
1. Historical grade ease calculated only from observed grade distributions, with a publicly explained formula, small-sample adjustment, and method version.
2. Prominent observed A rate: A/(A+B+C+D+F), with numerator/denominator and sample visible.
3. Full observed A/B/C/D/F distribution with counts and percentages, and other recorded outcome categories explained.
4. Separate observed withdrawal rate: W/all recorded grade outcomes. Do not include W in the ease score.
5. Evidence strength: actual sample counts, section counts, named semesters/date coverage, same-professor-and-course versus course-only history, and explicit fallback reasons.
6. A verified “View on Rate My Professors” profile link. No imported ratings, review counts, reviews, tags, scraping, or AI summaries.
7. Existing supported syllabus policy chips, evidence quotes, current/historical source labels, and correct syllabus or schedule-source links. Expose a syllabus link even if no chip is extracted.
8. Explicit unavailable/insufficient/suppressed/invalid states. Never generate an apparently reasonable score from absent course history.
9. Recently checked section seat counts, open/full/unknown/stale status, observation timestamps, and scheduled refresh.
10. Email alerts when a watched section has seats available, with email verification, durable delivery, cancellation and private management. The user explicitly selected seat counts PLUS email alerts.
11. A finished responsive search/detail/methodology/alert UI and an operational production deployment with real data.

LOCKED RULES
- Preserve the existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vite/Tailwind architecture.
- Historical grade ease is not the existing 80% grade / 20% withdrawal composite. Remove subject/global displayed-score fallbacks and fixed 0.75/0.10 no-evidence defaults.
- A prior may adjust a real eligible sample; it cannot stand in for this course's history. Unknown is not zero. Same-cohort raw rates and distribution must reconcile.
- Respect term/CRN identity, actual campus scope, real grade-file terms, source suppression, deduplication and conservative professor attribution.
- RMP, syllabus, seats, modality and GenEd must not change the grade score.
- Seat observation age must be visible. Failed requests must not advance the success timestamp, fabricate zero seats or generate opening events. Waitlist capacity is separate from available seats.
- Email monitoring must run without an open browser, share polling across subscribers, survive restart and use a persisted outbox with idempotency and bounded retries. Do not claim exactly-once inbox delivery.
- Use verified email ownership and private management links; do not expand this into a general accounts product. No email to unverified subscribers.
- No production synthetic fallback, guessed profile link, unsupported policy assertion, silent scope expansion, auto-registration, SMS, push, payments, or AI features.

DEFAULTS
Use the explicit proposed defaults in the plan: 0–10 grade-only shrinkage, k=60, a 20-outcome score floor, a 60-outcome professor-history threshold, empirical reference data, no recency weighting, a configurable five-minute watched-seat target, and one availability alert per watch followed by an explicit rearm action. These are implementation defaults, not calibrated scientific claims or verified upstream rate limits. Revise only with documented evidence and update methodology/tests consistently. Preserve all locked user requirements.

ROADMAP TO COMPLETION
Create traceable requirements and a complete roadmap matching these delivery outcomes:
1. Baseline, launch data/source coverage, method and UI contracts.
2. Honest grade evidence end-to-end: ingestion/linkage, analytics, API, observed rates/distribution, insufficient states, and methodology UI.
3. Verified RMP links and supported policy/syllabus source UI.
4. Validated seat freshness, scheduled polling, transitions, failure handling and seat UI.
5. Verified email watches, outbox delivery, management/cancellation/rearm UI and provider integration.
6. Integrated mobile/desktop UI, deep links, accessibility and browser acceptance.
7. Declared real-data coverage, PostgreSQL integration, measured performance, CI, deployment and operational readiness.
8. Deployed end-to-end acceptance, fixes and final public release.

Create .planning/PROJECT.md, REQUIREMENTS.md, ROADMAP.md and STATE.md through the installed GSD workflows as appropriate. Map every requirement to phases and acceptance evidence. Create UI-SPEC contracts before frontend implementation, using the supplied UI contract as the starting point. Generate executable plans for the next phase, then continue planning, implementing and verifying the remaining phases using the installed Core workflow. Do not stop at a roadmap, backend completion, fixture demo or static UI.

VALIDATION AND OPERATIONS
Preserve the existing passing baseline and update tests for changed semantics. Cover no history, W-only data, small samples, zero-valued priors, ambiguous instructors, duplicate sources, cross-term CRNs, nullable sorting, stale/cancelled/contradictory seats, duplicate polling, provider retries, worker crashes, token expiry and unsubscribe. Add real PostgreSQL tests for query/migration/concurrency behavior; current baseline Python tests are SQLite-based.

Perform integrated browser checks at 360/768/1440px and keyboard/zoom checks. Reconcile selected actual grade aggregates with rendered results. Demonstrate a narrow real schedule observation and controlled opening transitions without changing real university data. Demonstrate email verification, availability delivery and unsubscribe with a designated authorized test inbox; distinguish provider acceptance from inbox receipt.

Identify missing real grade exports, launch term/subject scope, source cadence, hosting/domain credentials, sender-domain setup and test inbox early. Continue independent work while those dependencies are resolved. Ask only for necessary external input or an explicit product change, not to repeat settled scope. Never invent data coverage, source permissions, credential access or deployment completion. Do not purchase services. Before any external approval that is actually required, make the proposed result concrete and reviewable.

DONE MEANS
A deployed responsive product lets a student find a real section, inspect observed grades and evidence, follow verified sources, see honestly timestamped seats, and receive/manage a verified email alert. Real data refresh, worker scheduling, delivery, monitoring, recovery and the operator runbook are demonstrated. Record the release commit, URL, method version, coverage and acceptance evidence. If an external dependency prevents deployment or real email validation, leave that acceptance item explicitly incomplete and report exactly what is needed.
```
