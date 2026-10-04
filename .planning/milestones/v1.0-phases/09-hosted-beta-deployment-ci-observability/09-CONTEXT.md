# Phase 9: Hosted Beta — Deployment, CI, Observability - Context

**Gathered:** 2026-09-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Run the corrected Easy-A application as a hosted beta on Render (API + always-on live schedule
sync worker + static frontend, hosted Supabase as the DB), with CI on push, basic observability
(sweep success/failure, search latency, visible data freshness) and an operator runbook.
Requirements: REQ-OPS-01, REQ-SYNC-01. Professor-level grades (Phase 10), email seat alerts
(backlog 999.1), auth, RMP and any scoring change are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (already locked — do not re-ask)
- **Hosting (STATE.md, 2026-09-29):** Render, region **ohio** (same AWS region as Supabase
  us-east-2). `render.yaml` Blueprint: `api` (web service, Starter), `worker` (background worker,
  Starter, ~512 MB), `web` (static site, free). Free `*.onrender.com` URLs, no custom domain.
  Env group `easy-a-shared` already holds `DATABASE_URL` (Supabase transaction pooler, port 6543,
  IPv4). One Dockerfile (uv-based Python image) serves both `api` and `worker`. API listens on
  `0.0.0.0:$PORT`; `EASY_A_ALLOWED_FRONTEND_ORIGINS` = the static-site URL; frontend built with
  `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL` = the API URL. Expected cost ≈ $14/month.
- **Migrations stay manual.** No `MIGRATION_DATABASE_URL` on Render. The `sections.removed_at`
  migration needs explicit user go-ahead before it is applied to hosted Supabase.
- **Sync design (D-22, D-23, live-sync plan Phase A):** one whole-term Tampa StaffScheduleSearch
  request per sweep; change-only instructor/seat writes; `sections.removed_at` (marked, never
  deleted; cleared if the CRN reappears); sanity gate that aborts a short/empty/reshaped response
  before any write; one `IngestRun` per sweep; Postgres advisory lock; `--dry-run`; freshness from
  `Section.last_seen_at`; rankings cache rebuild when anything changed; SIGTERM-clean loop with
  jitter and backoff; identifying `DEFAULT_USER_AGENT`.

### Sync cadence (registration windows)
- **D-01:** Cadence is **every 5 minutes inside a registration window, every 60 minutes outside**
  (the D-22 limits, with ±20% jitter that must never go below the 5-minute floor).
- **D-02:** Windows are **several separate date ranges** in a config file under `config/`
  (next to `course_targets.toml`), not one continuous block. For Spring 2027:
  1. **Priority/class-standing registration: Nov 2 – Nov 30, 2026** (source: USF Registrar
     "Registration Times" page; first group Nov 2, last listed group, Non-Degree, Nov 30).
  2. **State Employee Registrants: Jan 7, 2027** (single day).
  3. **Drop/add week for Spring 2027**: the exact dates are NOT on the registration-times page.
     The researcher must look them up on USF's official academic calendar and cite the source.
     Never guess them.
  December break between windows runs at the hourly cadence. The page lists dates only, no
  times, so windows are whole days in America/New_York.

### Sync scope (which sections/courses)
- **D-03:** The whole-term response (6,663 rows on 2026-09-28) is much larger than the tracked
  1,402 courses / 3,783 sections, which came from the **undergraduate** catalog (265 prefixes).
  The breakdown of the gap has NOT been measured: distinct CRNs vs rows, graduate vs
  undergraduate, catalog vs non-catalog. Planning/research should measure it, for example in the
  first dry-run summary, and report it.
- **D-04:** Scope is **undergraduate Tampa courses only**: course number below the 5000 level.
  Graduate courses are excluded. — **Reversibility:** costly — widening or narrowing later
  touches the sync filter, coverage reporting and D-21 exception accounting.
- **D-05:** The **worker auto-adds each sweep**: any undergraduate Tampa course in the sweep
  that is not yet in Easy-A is added automatically, together with its sections. This includes
  courses USF adds later in the term. Nobody should need to regenerate `course_targets.toml`
  by hand for coverage to stay complete.
  Constraints the plan must respect:
  - Newly added courses have no imported grade history, so they must show the honest
    no-course-history / `subject`/`global` fallback label (D-20). They must never appear to have
    evidence-backed analytics.
  - Courses today come from the catalog (`easy_a.catalog.ingest.upsert_catalog_courses`), and
    `resolve_course_id` raises for unknown courses. How a new course row gets created is Claude's
    discretion (see below), but it must stay within D-09/D-22. Any catalog lookups must be
    bounded, paced, per-new-course requests. No crawling. A course whose details could not be
    fetched must be reported, never silently skipped (D-06).
  - How the tracked-target list (`config/course_targets.toml`), coverage metadata and the D-21
    counts treat auto-added courses must be decided explicitly and documented.

### First live sync rollout
- **D-06:** **Just turn it on.** No gated human review of a dry-run diff is required before the
  worker starts writing. The worker begins applying changes right after deploy (and after the
  `removed_at` migration, which still needs its own explicit go-ahead). The expected first-sweep
  catch-up of ~92 removals, ~84 instructor changes and ~7 new sections (2026-09-28 drift) is
  applied automatically, protected by the sanity gate. Removals are marks (`removed_at`), not
  deletes, so they can be reversed.
  - `--dry-run` still ships as a tool (and belongs in the runbook). It just isn't a required
    rollout gate.
  - Note: with D-04/D-05 the first sweep also auto-adds the missing undergraduate courses, so
    it will be larger than the 2026-09-28 figures. The sanity gate's ~10% row-drop threshold
    must be based on the scoped row count, so a sweep that *adds* many rows is not mistaken for
    a failure.

### Failure alerts & freshness UI — **Claude's lean, user to review later**
The user deferred this area to Claude's recommendation and will review it later. Planner: treat
these as the working decisions, but flag them in the plan summary for user review.
- **D-07:** Operator status via an API endpoint (or an extension of `GET /api/v1/metadata/...`)
  showing the last successful sweep time, the last sweep status/error and the recent failure
  count, read from `IngestRun`.
- **D-08:** Search latency is measured with per-request duration logging in the API (structured
  log line with route, status and duration). p95 is derived from those logs, or from the existing
  `scripts/benchmark_rankings_search.py` pointed at the hosted URL. No metrics vendor.
- **D-09:** Alerting uses only Render's built-in service-failure email notifications (worker or
  API crash/deploy failure). Custom "N consecutive failed sweeps" alerting is deferred.
- **D-10:** Students see "Updated N min ago" (from `last_seen_at` / last successful sweep). A
  visible "seat data may be out of date" warning appears once data is older than **2× the current
  cadence** (≈10 min in a window, ≈2 h outside).

### CI gates & deploy trigger — **Claude's lean, user to review later**
Same deferral as above: working decisions, flagged for review.
- **D-11:** GitHub Actions (net-new `.github/workflows/`). **Hard gates:** `ruff`, `pytest` with a
  Postgres service container so `EASY_A_TEST_POSTGRES_URL` integration tests actually run, and the
  web `lint`, `typecheck`, `test` (vitest) and `build`.
- **D-12:** `mypy` runs **report-only** (non-blocking) until the known baseline (36 errors / 11
  files, WINDOWS.md entry 9) is cleaned up.
- **D-13:** Render deploys `main` **only after CI passes** (Render auto-deploy "after CI checks
  pass"), not on every push.

### Claude's Discretion
- How auto-added courses get their `Course` row (paced catalog fetch per new course vs. a
  schedule-derived row explicitly marked as such), within D-05's constraints.
- Exact config file name/format for registration windows.
- Runbook structure and location (e.g. `docs/runbook.md` or README section), as long as it covers
  refreshing data, recovering from a failed sweep, pausing/resuming the worker, running
  `--dry-run`, and un-marking a wrongly removed section.
- Dockerfile/Blueprint details within the carried-forward hosting decisions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and decisions
- `.planning/ROADMAP.md` §"Phase 9: Hosted Beta — Deployment, CI, Observability" — scope and success criteria
- `.planning/REQUIREMENTS.md` — REQ-OPS-01, REQ-SYNC-01 acceptance criteria
- `.planning/PROJECT.md` `<decisions>` — D-02 (frozen scoring), D-03, D-06/D-07, D-09, D-20, D-21, D-22 (USF request policy), D-23 (sequencing/hosting)
- `.planning/STATE.md` §"Next action" — Render workspace, env group, service plan/region facts
- `AGENTS.md` — hard constraints

### Live sync design and evidence
- `.planning/research/live-sync-and-prof-grades-plan-2026-09-28.md` — Phase A (A1–A6): the sync design this phase implements
- `.planning/research/instructor-grade-feasibility-2026-09-28.md` — whole-term request measurement and the 2026-09-28 drift figures

### External
- https://www.usf.edu/registrar/register/registration_times.aspx — Spring 2027 registration dates (D-02)
- USF academic calendar (researcher to locate) — Spring 2027 drop/add dates (D-02 item 3)

### Codebase maps (dated, pre-Sprint-5; structure only)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/TESTING.md`, `.planning/codebase/STACK.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/easy_a/schedule/client.py` (`build_form_data`, `StaffScheduleClient`): add an explicit whole-term path; keep narrow-query validation for existing callers.
- `src/easy_a/schedule/parser.py` / `normalize.py`: parse and normalize whole-term HTML unchanged.
- `src/easy_a/schedule/ingest.py` (`_upsert_sections`, `_section_values`, `_update_section`): current ingest appends instructor + seat rows every run, so the sync must become change-only.
- `src/easy_a/common/instructors.py` (`get_current_instructor_states`): current-instructor diffing.
- `src/easy_a/common/lookups.py` (`resolve_course_id`): raises for unknown courses, which matters for D-05.
- `src/easy_a/catalog/ingest.py` (`upsert_catalog_courses`): the existing course-creation path.
- `src/easy_a/refresh/coverage.py` (`refresh_targets`): Tampa-only and duplicate-CRN guards.
- `src/easy_a/rankings/cache.py` (`refresh_section_rankings`): whole-term rebuild, 4.77 s.
- `src/easy_a/schedule/freshness.py` (`snapshot_freshness`): switch its basis to `Section.last_seen_at`.
- `src/easy_a/models/core.py` (`IngestRun`): per-sweep observability row already exists.
- `scripts/benchmark_rankings_search.py`: p95 measurement; can be pointed at the hosted API.

### Established Patterns
- Config via pydantic-settings (`src/easy_a/config.py`, `EASY_A_*` env vars; CORS from `EASY_A_ALLOWED_FRONTEND_ORIGINS`).
- uv + `pyproject.toml` (ruff, strict mypy, pytest). Frontend in `web/` (Vite; scripts `lint`, `typecheck`, `test`, `build`).
- Postgres integration tests skip unless `EASY_A_TEST_POSTGRES_URL` is set.
- No `.github/`, no `Dockerfile`, no `render.yaml` exist yet; `docker-compose.yml` is Postgres only.

### Integration Points
- API: `src/easy_a/api/app.py` (middleware for request timing), `src/easy_a/api/routes/metadata.py` (status/freshness endpoint), `src/easy_a/api/routes/rankings.py` (exclude `removed_at IS NOT NULL`).
- Frontend: `web/src/api/rankings.ts` (API base URL / mock toggle), UI "Updated N min ago" + stale warning.
- Alembic `migrations/`: `sections.removed_at` (manual apply, go-ahead required).

</code_context>

<specifics>
## Specific Ideas

- The user expects missing Tampa undergraduate classes to be added. Their instinct was that
  Easy-A should cover every offered Tampa undergraduate class, and keep covering new ones
  automatically.
- The first-sweep changes are real USF-side drift since the 2026-09-20..22 snapshot (professor
  assignments, cancelled/merged sections), not errors. The user is comfortable letting the worker
  apply them directly.

</specifics>

<deferred>
## Deferred Ideas

- Custom alerting on N consecutive failed sweeps (email/Slack), beyond Render's crash notifications.
- Importing historical grades for the auto-added undergraduate courses (would extend Phase 5-style import; its own phase/task).
- Graduate course coverage.
- Email seat alerts (backlog 999.1), which build on this worker.
- Making mypy a hard CI gate after the baseline cleanup.
- User review of D-07..D-13 (alerting, freshness UI, CI gates, deploy trigger): accepted as Claude's lean for now.

</deferred>

---

*Phase: 09-hosted-beta-deployment-ci-observability*
*Context gathered: 2026-09-29*
