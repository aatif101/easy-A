# Phase 9: Hosted Beta — Deployment, CI, Observability - Research

**Researched:** 2026-09-29
**Domain:** Python worker + FastAPI on Render (Docker), GitHub Actions CI, Supabase transaction pooler, USF StaffScheduleSearch whole-term sync
**Confidence:** HIGH on codebase facts and measurements (read/measured this session); MEDIUM on Render runtime behaviours not exercised (no Docker in this WSL distro, no deploy performed)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (already locked — do not re-ask)**
- **Hosting (STATE.md, 2026-09-29):** Render, region **ohio** (same AWS region as Supabase us-east-2). `render.yaml` Blueprint: `api` (web service, Starter), `worker` (background worker, Starter, ~512 MB), `web` (static site, free). Free `*.onrender.com` URLs, no custom domain. Env group `easy-a-shared` already holds `DATABASE_URL` (Supabase transaction pooler, port 6543, IPv4). One Dockerfile (uv-based Python image) serves both `api` and `worker`. API listens on `0.0.0.0:$PORT`; `EASY_A_ALLOWED_FRONTEND_ORIGINS` = the static-site URL; frontend built with `VITE_USE_MOCK_DATA=false` and `VITE_API_BASE_URL` = the API URL. Expected cost ≈ $14/month.
- **Migrations stay manual.** No `MIGRATION_DATABASE_URL` on Render. The `sections.removed_at` migration needs explicit user go-ahead before it is applied to hosted Supabase.
- **Sync design (D-22, D-23, live-sync plan Phase A):** one whole-term Tampa StaffScheduleSearch request per sweep; change-only instructor/seat writes; `sections.removed_at` (marked, never deleted; cleared if the CRN reappears); sanity gate that aborts a short/empty/reshaped response before any write; one `IngestRun` per sweep; Postgres advisory lock; `--dry-run`; freshness from `Section.last_seen_at`; rankings cache rebuild when anything changed; SIGTERM-clean loop with jitter and backoff; identifying `DEFAULT_USER_AGENT`.

**Sync cadence (registration windows)**
- **D-01:** Cadence is **every 5 minutes inside a registration window, every 60 minutes outside** (the D-22 limits, with ±20% jitter that must never go below the 5-minute floor).
- **D-02:** Windows are **several separate date ranges** in a config file under `config/` (next to `course_targets.toml`), not one continuous block. For Spring 2027:
  1. **Priority/class-standing registration: Nov 2 – Nov 30, 2026** (source: USF Registrar "Registration Times" page; first group Nov 2, last listed group, Non-Degree, Nov 30).
  2. **State Employee Registrants: Jan 7, 2027** (single day).
  3. **Drop/add week for Spring 2027**: the exact dates are NOT on the registration-times page. The researcher must look them up on USF's official academic calendar and cite the source. Never guess them.
  December break between windows runs at the hourly cadence. The page lists dates only, no times, so windows are whole days in America/New_York.

**Sync scope (which sections/courses)**
- **D-03:** The whole-term response (6,663 rows on 2026-09-28) is much larger than the tracked 1,402 courses / 3,783 sections, which came from the **undergraduate** catalog (265 prefixes). The breakdown of the gap has NOT been measured: distinct CRNs vs rows, graduate vs undergraduate, catalog vs non-catalog. Planning/research should measure it, for example in the first dry-run summary, and report it.
- **D-04:** Scope is **undergraduate Tampa courses only**: course number below the 5000 level. Graduate courses are excluded. — **Reversibility:** costly — widening or narrowing later touches the sync filter, coverage reporting and D-21 exception accounting.
- **D-05:** The **worker auto-adds each sweep**: any undergraduate Tampa course in the sweep that is not yet in Easy-A is added automatically, together with its sections. This includes courses USF adds later in the term. Nobody should need to regenerate `course_targets.toml` by hand for coverage to stay complete.
  Constraints the plan must respect:
  - Newly added courses have no imported grade history, so they must show the honest no-course-history / `subject`/`global` fallback label (D-20). They must never appear to have evidence-backed analytics.
  - Courses today come from the catalog (`easy_a.catalog.ingest.upsert_catalog_courses`), and `resolve_course_id` raises for unknown courses. How a new course row gets created is Claude's discretion (see below), but it must stay within D-09/D-22. Any catalog lookups must be bounded, paced, per-new-course requests. No crawling. A course whose details could not be fetched must be reported, never silently skipped (D-06).
  - How the tracked-target list (`config/course_targets.toml`), coverage metadata and the D-21 counts treat auto-added courses must be decided explicitly and documented.

**First live sync rollout**
- **D-06:** **Just turn it on.** No gated human review of a dry-run diff is required before the worker starts writing. The worker begins applying changes right after deploy (and after the `removed_at` migration, which still needs its own explicit go-ahead). The expected first-sweep catch-up of ~92 removals, ~84 instructor changes and ~7 new sections (2026-09-28 drift) is applied automatically, protected by the sanity gate. Removals are marks (`removed_at`), not deletes, so they can be reversed.
  - `--dry-run` still ships as a tool (and belongs in the runbook). It just isn't a required rollout gate.
  - Note: with D-04/D-05 the first sweep also auto-adds the missing undergraduate courses, so it will be larger than the 2026-09-28 figures. The sanity gate's ~10% row-drop threshold must be based on the scoped row count, so a sweep that *adds* many rows is not mistaken for a failure.

**Failure alerts & freshness UI — Claude's lean, user to review later** (planner: treat as working decisions, flag in plan summary)
- **D-07:** Operator status via an API endpoint (or an extension of `GET /api/v1/metadata/...`) showing the last successful sweep time, the last sweep status/error and the recent failure count, read from `IngestRun`.
- **D-08:** Search latency is measured with per-request duration logging in the API (structured log line with route, status and duration). p95 is derived from those logs, or from the existing `scripts/benchmark_rankings_search.py` pointed at the hosted URL. No metrics vendor.
- **D-09:** Alerting uses only Render's built-in service-failure email notifications (worker or API crash/deploy failure). Custom "N consecutive failed sweeps" alerting is deferred.
- **D-10:** Students see "Updated N min ago" (from `last_seen_at` / last successful sweep). A visible "seat data may be out of date" warning appears once data is older than **2× the current cadence** (≈10 min in a window, ≈2 h outside).

**CI gates & deploy trigger — Claude's lean, user to review later**
- **D-11:** GitHub Actions (net-new `.github/workflows/`). **Hard gates:** `ruff`, `pytest` with a Postgres service container so `EASY_A_TEST_POSTGRES_URL` integration tests actually run, and the web `lint`, `typecheck`, `test` (vitest) and `build`.
- **D-12:** `mypy` runs **report-only** (non-blocking) until the known baseline (36 errors / 11 files, WINDOWS.md entry 9) is cleaned up.
- **D-13:** Render deploys `main` **only after CI passes** (Render auto-deploy "after CI checks pass"), not on every push.

### Claude's Discretion
- How auto-added courses get their `Course` row (paced catalog fetch per new course vs. a schedule-derived row explicitly marked as such), within D-05's constraints.
- Exact config file name/format for registration windows.
- Runbook structure and location (e.g. `docs/runbook.md` or README section), as long as it covers refreshing data, recovering from a failed sweep, pausing/resuming the worker, running `--dry-run`, and un-marking a wrongly removed section.
- Dockerfile/Blueprint details within the carried-forward hosting decisions.

### Deferred Ideas (OUT OF SCOPE)
- Custom alerting on N consecutive failed sweeps (email/Slack), beyond Render's crash notifications.
- Importing historical grades for the auto-added undergraduate courses (would extend Phase 5-style import; its own phase/task).
- Graduate course coverage.
- Email seat alerts (backlog 999.1), which build on this worker.
- Making mypy a hard CI gate after the baseline cleanup.
- User review of D-07..D-13 (alerting, freshness UI, CI gates, deploy trigger): accepted as Claude's lean for now.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-OPS-01 | Hosted beta is deployable, observable, reproducible: minimal portable deployment config; CI runs Python + frontend checks (net-new); basic observability covers refresh success/failure and search latency; operator runbook covers refreshing data and recovering from a failed refresh. | Dockerfile + validated `render.yaml` draft (Code Examples); CI baseline measured on a clean checkout on Python 3.12 (Pitfall 9); observability = `IngestRun` + `/sync-status` + request-duration log (Patterns 7, 8); Render latency graphs are Pro-only so logs are required (Pitfall 12); runbook topics enumerated (Open Questions / Validation). |
| REQ-SYNC-01 | Spring 2027 seats, instructor names and section existence stay near-live: one whole-term Tampa request per sweep under D-22 (tiered cadence, single worker); instructor/seat rows appended only on change; sections absent from a sanity-checked sweep marked removed and leave search; each sweep records an `IngestRun`; UI shows when data was last verified. | Measured whole-term response (truncated-tail behaviour, scope, memory) in Summary and Pitfalls 1-3; sweep-transaction, diff, gate, lock, cadence and freshness patterns; `removed_at` consumer audit (Pitfall 6); migration ordering (Pitfall 8). |
</phase_requirements>

## Summary

Phase 9 is mostly integration work on a codebase that already has the hard parts (parser, normalizer, cache rebuild, `IngestRun`, pydantic-settings). The risky parts are not the Blueprint or the workflow files; they are behaviours of the live USF response and of the hosting platforms that the earlier plan (`live-sync-and-prof-grades-plan-2026-09-28.md`) did not know about. I verified the locked decisions against the code, ran the whole test/lint/build baseline on a clean checkout under Python 3.12, made **one** whole-term request (plus one narrow PHC request and nine paced catalog lookups) to measure the D-03 gap, and ran a **read-only** diff of the live Supabase data against that sweep (rolled back, nothing written).

Ten findings change how the plan should be written:

1. **The whole-term response is always cut off by a USF server error.** It has no `</table>`, no `</html>`, no "N records were found" footer, and ends with `<h3>We're sorry but an unexpected error has occured in this application. Please try back later.</h3>`. All 6,640 rows before that are complete (my narrow PHC request returned exactly the same 162 CRNs as the whole-term rows for PHC, which sits in the last college group). So the footer cannot be used as an integrity check, and the sanity gate must key on row count, subject coverage and a parsed-vs-`<tr>` row count instead. [VERIFIED: measured 2026-09-29]
2. **Memory: the existing parser will OOM a 512 MB worker.** `parse_schedule_html` (BeautifulSoup) on the 7.1 MB response peaked at **443 MB RSS** on Python 3.12 (295 MB on 3.14) once the worker's imports (106 MB with pandas) are included. A chunked wrapper that feeds groups of 250 `<tr>` elements to the *unchanged* `parse_schedule_html` produced byte-identical results (`out == full` → `True`, 6,640 rows) at **121 MB peak in 2.6 s**. Use it. [VERIFIED: measured]
3. **Scope (D-03) is now measured**: 6,640 rows = 6,640 distinct CRNs (no duplicate CRNs), 231 subjects, all `Tampa`. **3,700 rows / 1,370 courses are below 5000** (undergraduate, D-04); 2,940 rows are graduate (0 of them in the tracked list). Only **11 undergraduate courses** are not in Easy-A yet. [VERIFIED: measured]
4. **First-sweep catch-up is now larger than the plan's numbers** (read-only diff vs live DB, 2026-09-29): **104 removals** (2.7% of 3,783 active sections, well under the 10% gate), **21 new CRNs** (11 of them in the 11 new courses), **89 instructor changes** (52 Staff→named, 24 named→other, 13 named→Staff), 85 sections with seat-column changes. [VERIFIED: read-only query]
5. **Session-level advisory locks do not work on the transaction pooler** the env group uses (port 6543). Use a *transaction-scoped* lock (`pg_try_advisory_xact_lock`) taken at the start of the sweep transaction, before the USF fetch. [CITED: supabase.com/docs/guides/database/connecting-to-postgres]
6. **Freshness thresholds (600 s / 1800 s) contradict the hourly cadence.** With `Section.last_seen_at` as basis and hourly sweeps outside windows, every section would read "stale" most of the day. Thresholds must become cadence-aware (D-10: stale after 2× the current cadence). Also: **seat-only changes never require a rankings-cache rebuild** (the cache has no seat columns), so rebuild only on instructor / add / remove / restore / delivery changes.
7. **`removed_at` has 15+ consumers** that count or list sections (search cache rebuild, `/section`, `/course`, coverage, quality checks, three ops scripts). Two of them will *break* rather than mis-count: `scripts/benchmark_rankings_search.py` raises when `stored != cached`, and it only accepts a **plain loopback http origin**, so D-08's "pointed at the hosted URL" needs a small script change.
8. **Render:** `autoDeployTrigger: checksPass` does not deploy when *zero* checks ran for the commit (so no path filters on the workflow); zero-downtime deploys apply to workers, so **old and new workers overlap for ~60-90 s at every deploy** (the advisory lock is not optional); `render blueprints validate` rejects `fromGroup: easy-a-shared` as "non-existent group" (conflicts with STATE.md; needs a human check); response-latency graphs need a Pro workspace.
9. **CI baseline is not green today:** `ruff check .` fails with 2 pre-existing E501 errors (a hard gate would fail its first run). `mypy src` is already clean (0 errors / 73 files); `mypy .` shows 35 errors in 10 files, all in tests/scripts. `astral-sh/setup-uv` has **no floating major tag**; pin the exact version.
10. **Registration dates verified from the official USF Registrar calendar** (raw page, not a summary): Spring 2027 drop/add is **Jan 11-15, 2027** (classes begin Jan 11; "Spring drop/add ends" Jan 15). [VERIFIED: usf.edu/registrar/calendars/index.aspx, fetched 2026-09-29]

**Primary recommendation:** Build `easy_a.sync` as one sweep = one Postgres transaction (xact advisory lock → fetch → chunked parse → integrity gate → in-memory diff against three bulk reads → apply → `IngestRun` → commit; failures roll back and write a `failed` `IngestRun` in a second short transaction), keep the worker's import graph free of `easy_a.refresh.coverage` (it pulls pandas), and land the migration, consumer audit and cadence-aware freshness *before* the Blueprint is created.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Whole-term fetch, parse, diff, apply | Worker (background process, Python) | Database | Long-running, single-writer, no inbound traffic; DB holds the state and the lock |
| Single-sweep mutual exclusion | Database (advisory xact lock) | Worker | Must survive Render's 60-90 s deploy overlap; pooler-safe only as a transaction lock |
| Cadence / registration windows | Worker (schedule) | API (reads same config for thresholds) | Worker decides when to fetch; API needs the same tier to classify freshness |
| Section removal / restore | Database (`sections.removed_at`) | API (filters), Worker (writes) | Marks, not deletes; search excludes via cache-row deletion plus service-level filters |
| Rankings cache upkeep | Worker (calls `refresh_section_rankings`) | Database (`section_rankings`) | Only on structural changes; seat data is read live from snapshots |
| Seat/last-verified display | API (classification) | Browser (relative time text) | README: the frontend does not calculate freshness thresholds |
| "Updated N min ago" indicator | Browser (render + ticking clock) | API (`/sync-status` payload with `is_stale`) | Threshold decision stays in API; browser only formats |
| Request-latency measurement | API (middleware, structured log) | Render logs (7-day retention) | Render latency graphs are Pro-only |
| Failure alerts | Render (built-in email) | — | D-09; custom alerting deferred |
| CI gates | GitHub Actions | Render (`checksPass` gate) | Render deploys only if the commit's checks pass |
| Static frontend hosting | CDN / Static (Render static site) | — | Built with `VITE_*` at build time |
| Migrations | Operator (manual, local) | — | Locked: no `MIGRATION_DATABASE_URL` on Render |

## Standard Stack

### Core (all already in the repo; no new runtime library is required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 (tested: 3.12.14) | Runtime for api + worker image and CI | `requires-python >=3.12`; full suite passes under 3.12 with `uv sync --frozen` [VERIFIED: ran, 374 passed / 3 skipped] |
| uv | 0.12.17 | Dependency install (Docker + CI) | Repo standard; local version verified; pin in Docker instead of `:latest` [VERIFIED: `uv --version`] |
| FastAPI / uvicorn | fastapi>=0.141.1, uvicorn>=0.52.4 (from `pyproject.toml`) | API process | Already used; run with `--host 0.0.0.0 --port $PORT` |
| SQLAlchemy 2 + psycopg 3 | sqlalchemy>=2.0.0, psycopg[binary]>=3.2.0 | DB access; `prepare_threshold=None` already set for the pooler | `db.py:41` `kwargs["connect_args"] = {"prepare_threshold": None}` |
| httpx | >=0.28.0 | USF client | `StaffScheduleClient` already reuses `DEFAULT_USER_AGENT` |
| BeautifulSoup + lxml | bs4>=4.13.0, lxml>=5.3.0 | Row parsing (reuse unchanged via chunking) | Parity proven on the real 6,640-row response |
| Alembic | >=1.16.0 | Migration 0004 (manual apply) | Existing head is `0003_create_section_rankings` [VERIFIED: migrations/versions/0003_create_section_rankings.py] |
| pytest / ruff / mypy | pytest>=8.3.0, ruff>=0.9.0, mypy>=1.14.0 | CI gates | Already the project toolchain |
| Vite / vitest / eslint / tsc | vite ^7.1.3, vitest ^3.2.4 (web/package.json) | Frontend gates | `lint`, `typecheck`, `test`, `build` all pass locally (86 tests) |

### Supporting

| Library / tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `zoneinfo` (stdlib) + `tzdata` | tzdata: any current | America/New_York registration windows | `uv.lock` pins `tzdata` only for `sys_platform == 'win32'` / emscripten (lines 805, 880), so it is **not** installed on Linux; the slim Docker image may lack `/usr/share/zoneinfo` (unverified — Docker not available here). Add an explicit `tzdata` dependency (see audit; flagged SUS by the seam, false positive) or `apt-get install tzdata` in the image, plus a startup self-check `ZoneInfo("America/New_York")` |
| `render` CLI | 2.28.0 (installed, logged in) | `render blueprints validate render.yaml` | Local pre-flight before Blueprint creation |
| `actions/checkout` | v7 (floating tag exists; latest v7.0.1) | CI checkout | [VERIFIED: `gh api` tag lookup] |
| `astral-sh/setup-uv` | **v10.2.0 exact** | CI uv + cache | `v10`/`v9` floating tags return 404; pin exact tag or SHA `c18668ad3cf93ea998bef934396af7bb5c839dc7` [VERIFIED: gh api] |
| `actions/setup-node` | v7 (latest v7.0.0) | CI Node + npm cache | [VERIFIED: gh api] |
| `postgres:16` service container | 16 | `EASY_A_TEST_POSTGRES_URL` integration tests | Same major as `docker-compose.yml` (`image: postgres:16`) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Chunked reuse of `parse_schedule_html` | `lxml.etree.iterparse(html=True)` streaming | iterparse hit 35 MB peak / 0.1 s on the same file, but re-implements cell extraction (title/note split) and needs its own parity tests; chunking gets exact parity for free. Prefer chunking; keep iterparse as the fallback if memory is still tight |
| Xact advisory lock held across the fetch | Session-mode pooler URL (port 5432) + session lock | Supabase says session mode "supports prepared statements" and session state; would need a second URL on Render, contradicting the locked single `DATABASE_URL`. Only if idle-in-transaction during the ~16 s fetch proves a problem (A2) |
| Blueprint `fromGroup: easy-a-shared` | Per-service `DATABASE_URL` with `sync: false` | See Pitfall 11: the CLI validator rejects the dashboard-created group |
| Bigger worker plan | `1c-2g` ($25/mo) | Only if chunked parse + DB stage still exceed ~350 MB in the soak; changes the ≈$14/mo locked cost |
| `mypy` report-only (D-12) | `mypy src` hard gate + `mypy .` report-only | `mypy src` is 0 errors today and would protect the new sync code; deviates from D-12 as written, so flag for user review |

**Installation:** no new install commands except the optional `uv add tzdata` (behind the checkpoint below). CI/Docker use `uv sync --locked` (`--no-dev` in the image).

**Version verification (this session):** `uv 0.12.17`, Python 3.12.14 (via `uv sync --frozen --python 3.12` into a scratch venv), Node v24.21.0 / npm 11.19.0, Render CLI v2.28.0, `gh` 2.46.0. `tzdata` latest release 2026-09-12 per the legitimacy seam.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| tzdata (optional, for `zoneinfo`) | PyPI | multi-year (CPython-team package; latest release 2026-09-12) | seam returned `null` | github.com/python/tzdata | [SUS] — seam reasons `too-new`, `unknown-downloads` (both reflect only the latest release date and a missing stat; the package is `python/tzdata`, already a transitive lock entry for win32 via pandas and psycopg) | Flagged — planner must add `checkpoint:human-verify` before adding it as a direct dependency; fallback is `apt-get install tzdata` in the Dockerfile (no new Python package) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** `tzdata` — planner inserts `checkpoint:human-verify` before the install.

No other Python or npm package is added by this phase. GitHub Actions (`actions/checkout`, `actions/setup-node`, `astral-sh/setup-uv`) and container images (`python:3.12-slim-trixie`, `ghcr.io/astral-sh/uv`) are not registry packages; the three actions were resolved with `gh api` against their official orgs. The image names come from the uv Docker guide [CITED: docs.astral.sh/uv/guides/integration/docker/] and the exact `python:3.12-slim-trixie` tag should be confirmed on the first Render/CI build (Docker is not installed in this WSL distro: `docker` "could not be found in this WSL 2 distro").

## Architecture Patterns

### System Architecture Diagram

```
                     config/registration_windows.toml  (read by worker AND api)
                                     |
   +-------------------------------- v -------------------------------------+
   |  WORKER  (python -m easy_a.sync --term 202701)   Render worker, 512 MB |
   |                                                                         |
   |  loop:  sleep until next_run (tier 5 min in window / 60 min outside,    |
   |         jitter only upward, capped to next window start, backoff)       |
   |            |                                                            |
   |            v                                                            |
   |   BEGIN (Supabase transaction pooler, port 6543)                        |
   |   SELECT pg_try_advisory_xact_lock(k) --false--> log "busy", ROLLBACK   |
   |            | true                                                       |
   |            v                                                            |
   |   ONE whole-term POST (P_CAMPUS=T, P_SUBJ="")  --HTTP 200, ~7 MB, 9-16s-|--> usfweb.usf.edu
   |            v                                                            |
   |   split into <tr> chunks -> unchanged parse_schedule_html -> normalize  |
   |   INTEGRITY GATE (rows>0, header ok, parsed == <tr> count, subject and  |
   |   row-count floor vs DB active set, missing<=10%)  --fail--> ROLLBACK,  |
   |                        failed IngestRun in 2nd short txn, backoff       |
   |            v pass                                                       |
   |   scope filter: campus Tampa, int(number[:4]) < 5000, no dup CRN        |
   |   auto-add new courses (paced catalog fetch, cap, negative cache)       |
   |   3 bulk reads: sections(term), current instructors, latest snapshots   |
   |   pure diff -> SweepPlan {insert, update, instructor+, snapshot+,       |
   |                            removed+, restored, failures}                |
   |            v (skipped when --dry-run: print plan, ROLLBACK)             |
   |   apply: section fields, instructor rows (on change), snapshots (on     |
   |   change), removed_at, ONE bulk UPDATE last_seen_at, delete cache rows  |
   |   of removed sections, refresh_section_rankings ONLY if structural      |
   |   change, IngestRun(succeeded) -> COMMIT (releases lock)                |
   +-------------------------------------------------------------------------+
                        |                                   ^
                        v                                   |
                 Supabase Postgres (us-east-2)  <-----------+---------------+
                        ^                                                   |
                        | reads                                             |
   +--------------------+---------------------+             +---------------+--------+
   | API (uvicorn 0.0.0.0:$PORT, Render web)  |             | GitHub Actions (push/PR) |
   |  request-duration middleware -> stdout   |             |  python: ruff, pytest+pg |
   |  GET /api/v1/rankings/search|section|... |             |  web: lint,tsc,vitest,   |
   |  GET /api/v1/metadata/sync-status        |             |       build; docker build|
   |  cadence-aware seat freshness            |             +-----------+--------------+
   +--------------------+---------------------+                         | checks pass
                        ^                                               v
   Browser (Render static site, VITE_API_BASE_URL) ---GET--->  Render auto-deploy (main)
     "Updated N min ago" + stale warning
```

### Recommended Project Structure

```
Dockerfile                     # one image; default CMD = api; worker overrides dockerCommand
.dockerignore                  # MUST exclude .env, .venv, .git, web/node_modules, data/, courses.csv, .planning/
render.yaml                    # api + worker + web (validated draft below)
.github/workflows/ci.yml       # python, web, docker jobs; no path filters
config/registration_windows.toml
src/easy_a/sync/
├── __init__.py
├── __main__.py                # python -m easy_a.sync
├── cli.py                     # --term, --dry-run, --once, --log-level
├── windows.py                 # model + load + cadence_for(now) + next_run(...) + freshness thresholds
├── fetch.py                   # whole-term fetch + chunked parse + integrity checks
├── plan.py                    # pure diff (no DB writes)
├── apply.py                   # writes, bulk last_seen_at, cache upkeep
├── courses.py                 # auto-add (catalog fetch, pacing, negative cache)
├── lock.py                    # pg_try_advisory_xact_lock (no-op on non-postgres)
└── runner.py                  # loop, SIGTERM Event, backoff, jitter
src/easy_a/schedule/client.py  # + StaffScheduleClient.search_term(); narrow validation untouched
src/easy_a/schedule/freshness.py   # + verified_at basis + cadence-aware thresholds
src/easy_a/api/routes/metadata.py  # + GET /sync-status (NOT piggybacked on /coverage)
src/easy_a/api/app.py              # + request-duration middleware + logging config
migrations/versions/0004_*.py      # sections.removed_at (+ seat_snapshots index); manual apply
docs/runbooks/hosted-beta-operations.md
web/src/api/rankings.ts            # + fetchSyncStatus (mock branch labelled synthetic)
web/src/components/SyncStatus.tsx  # "Updated N min ago" + stale warning (mirror CoverageNotice states)
tests/sync/                        # new package (needs __init__.py like other test dirs)
```

### Pattern 1: One sweep = one transaction; failure evidence in a second transaction
**What:** `session.begin()` → xact lock → fetch → gate → apply → `IngestRun(status="succeeded")` → commit. Any exception rolls back everything, then a *separate* short transaction inserts `IngestRun(status="failed", error_message=..., records_failed=1)` (the pattern `catalog/ingest.py` uses: `status="running"` at :31, `run.status = "failed"` at :44, `run.status = "succeeded"` at :51 — reuse those literal status strings).
**When to use:** always; it makes "sanity gate aborts before any write" true by construction and leaves no stale `running` rows after a SIGKILL.
**Why not one row per sweep created up front:** a crash would leave `running` forever and the status endpoint would have to age it out.

### Pattern 2: Chunked reuse of the existing parser (memory-bounded, exact parity)
Proven on the real response: header regex, `<tr>` regex, 250 rows per chunk, wrapper `<table>{header}{rows}</table>` handed to `parse_schedule_html`. Result equals the full parse (6,640 rows, `True`), peak 121 MB vs 443 MB. **Fail closed:** raise if the header row is not found, and compare `len(parsed)` with the count of `<tr>` blocks that contain `<td>` — `parse_schedule_html` silently `continue`s on rows whose cell count differs from 24 (`parser.py:85` `if len(cells) != len(EXPECTED_HEADERS):`), so a truncated or reshaped row would otherwise vanish without a trace.

### Pattern 3: Pure planner + thin applier
`plan.py` takes (normalized rows, DB snapshot dataclasses) and returns a `SweepPlan`; `apply.py` executes it. `--dry-run` = build the plan and print it; on Postgres additionally `SET TRANSACTION READ ONLY` (benchmark script already does this at `scripts/benchmark_rankings_search.py:255`-ish `session.execute(text("SET TRANSACTION READ ONLY"))`). Dry-run must **skip auto-add catalog fetches** (report "would add N courses: [...]") so it makes exactly one USF request.

### Pattern 4: Three bulk reads, no per-row queries
The legacy `_upsert_sections` does `select(Section)` per row (3,783 round trips over a remote pooler). The sweep needs: (1) all `Section` rows for the term keyed by CRN; (2) `get_current_instructor_states(session, section_ids)` (already batched); (3) latest snapshot per section. For (3) compare against the **latest `SeatSnapshot`** (what the API serves), not just `Section` seat columns: the API reads `SeatSnapshot` (`rankings.py:_latest_snapshot`, `service._seat_info_for`), so a section whose columns match USF but whose latest snapshot is older would never get a fresh snapshot and would display stale seats forever. Use the portable `ROW_NUMBER()` subquery pattern already in `rankings.py:183` (`_latest_snapshot`), which also runs on SQLite for tests.

### Pattern 5: Instructor change detection
`get_current_instructor_states` treats all rows sharing the max `observed_at` as the current state. Append **one** `SectionInstructor` row only when the whitespace-collapsed, case-folded name differs from `state.name`/`latest_names`. `blank_latest_state`/`no_observations` count as "different" from any non-blank name. The whole-term data has one instructor per CRN (0 blank, 2 rows like `P. Scesa, Jr` that are a single name with a suffix), so no multi-row append is needed; co-teaching is invisible in the source.

### Pattern 6: Cadence and jitter as pure functions
`cadence_for(now_utc, windows) -> timedelta` (300 s in a window, 3600 s outside). Whole-day windows in `America/New_York` (`[start 00:00, end+1d 00:00)` local). Jitter is **upward only**: `interval = base * uniform(1.0, 1.2)`. D-22(b) says "no more often than every 5 minutes" in a window and "no more often than every 60 minutes otherwise", so a -20% jitter would violate both floors (the D-01 wording about "never below the 5-minute floor" is only satisfiable outside windows by also refusing to go below 60 min). Measure the interval from the previous sweep **start**. Cap the sleep so the first sweep of a window fires at local midnight (otherwise the hour-long sleep at 23:10 on Nov 1 skips the first ~50 minutes of Nov 2). On failure: `interval = max(tier_interval, min(60 min, 5 min * 2**failures))` (never shorter than the tier floor; no retry storms).

### Pattern 7: `/api/v1/metadata/sync-status` (new endpoint, not `/coverage`)
`/coverage` loops over all 1,402 targets and runs 3 queries per target (`coverage_metadata`, `coverage.py:44-70`), about 4,200 statements per call; the plan's A6 suggestion to hang the health signal on it would make every page load expensive. Return: `term`, `last_success_at` (max `finished_at` of `status == "succeeded"` for the sync source), `last_run_at`, `last_status`, `failures_recent` (count of `failed` in last 24 h), `cadence_seconds`, `stale_after_seconds`, `is_stale`. **Do not return raw `error_message`** on a public unauthenticated endpoint (a psycopg error can contain the pooler hostname and port); return a coarse `error_kind` and keep the full text in `ingest_runs` and logs.

### Pattern 8: Request-duration log line
`@app.middleware("http")` with `time.perf_counter()`, one JSON line: `{"event":"request","method","route","status","duration_ms"}`, using `request.scope["route"].path` (the template, not the raw URL). **Configure logging explicitly**: a `logging.getLogger("easy_a.request").info(...)` call is dropped under the default root level WARNING that uvicorn leaves in place; call `logging.basicConfig(level=INFO)` (or a named handler) at app creation. Render allows up to 6,000 log lines/min per instance and keeps 7 days on the Hobby plan [CITED: render.com/docs/logging].

### Pattern 9: Cadence-aware seat freshness
Keep `classify_observation(observed_at, fresh_seconds=, stale_seconds=)` as is. Add `verified_at` (Section.last_seen_at) as the observation time and pass thresholds from the current tier: `stale_seconds = 2 * interval` (D-10), `fresh_seconds = round(1.25 * interval)` (covers +20% jitter plus sweep duration). That is 375 s / 600 s in a window and 4,500 s / 7,200 s outside. Keep `EASY_A_SEAT_FRESH_SECONDS` / `EASY_A_SEAT_STALE_SECONDS` as explicit operator overrides only when set. `snapshot_freshness` has three callers (`rankings/service.py:251`, `rankings/cache.py:259`, `quality/coverage.py:42`); keep the old behaviour when `verified_at is None` so existing tests and legacy flows do not change.

### Pattern 10: Auto-adding courses (D-05 discretion)
Recommendation: **paced catalog fetch per new course** using the existing `fetch_catalog_html` + `parse_catalog_html(html, catalog_edition)` + `upsert_catalog_courses` with `catalog_edition` taken from `config/course_targets.toml` (`"2026-2027"`). I probed it: 9 of the 11 missing courses returned a matching catalog page (title parsed; LDR 3363 also carried 1 GenEd attribute); `NEB 0001` (a non-credit "Chemistry Peer Leading" row) has no catalog heading (`CatalogParseError: Could not find a course heading in catalog HTML.`) and `POT 4936` failed with a transient DNS error in my sandbox. Rules: at most ~10 new courses per sweep, 2 s pacing, a per-course negative cache (retry a failed course no more than every ~6 h), failures counted in `records_failed` and logged by name (D-06), the sweep itself still `succeeded`. **Do not** insert schedule-derived `Course` rows: `resolve_course_id` orders by `Course.catalog_edition.desc()` (`lookups.py:42`), so any placeholder edition string that sorts above `"2026-2027"` (for example `"schedule-derived"`) would *outrank* the real catalog row later, and the unique key `(subject, number, catalog_edition)` would split one course into two rows. Auto-added courses keep the honest `subject`/`global` fallback automatically because they have no `GradeDistribution` rows (the score-source logic is unchanged, D-02/D-20).
- **Targets file:** leave `config/course_targets.toml` untouched (the container filesystem is ephemeral and it is the frozen D-21 baseline). Report auto-added courses through the sweep log and `/sync-status` counts. `/coverage` keeps meaning "configured targets".

### Anti-Patterns to Avoid
- **Session-level advisory lock** (`pg_try_advisory_lock`) on the 6543 pooler: the lock is lost between transactions.
- **Footer/`</table>` check** on the whole-term response: it is *always* missing.
- **`parse_schedule_html(response.text)` on the whole response** in the worker (443 MB peak).
- **Importing `easy_a.refresh.coverage`** in the worker: it drags in pandas via `easy_a.grades.parser` (worker imports 58 MB without vs 106 MB with). Re-implement the two guards (Tampa-only, duplicate CRNs) locally.
- **Per-row `SELECT`/`UPDATE`** inside the sweep, and a per-row ORM `last_seen_at` write (use one bulk `UPDATE ... WHERE term_id = :t AND crn IN (:chunk)`).
- **Rebuilding the rankings cache on every sweep** (seat-only changes do not need it).
- **`fromGroup` with a dashboard-only group** without re-validating (Pitfall 11).
- **Path filters on the CI workflow** (Render sees zero checks and refuses to deploy).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing the schedule table | A new HTML/regex cell extractor | Existing `parse_schedule_html` + `normalize_schedule_row`, fed in chunks | Title/note splitting (`<br>`), `&nbsp;`, 24-column contract, parity proven |
| Instructor current-state logic | New "latest name" query | `get_current_instructor_states` | Handles blank/ambiguous/no-observation states and is already batched |
| Course creation | Placeholder `Course` rows | `fetch_catalog_html` + `parse_catalog_html` + `upsert_catalog_courses` | Preserves catalog identity, GenEd attributes, edition ordering |
| Cache rebuild | Custom ranking writer | `refresh_section_rankings(session, term=...)` (optionally per-course args) | Frozen scoring (D-02); already whole-term batched |
| Time zones | Manual UTC-offset math | `zoneinfo.ZoneInfo("America/New_York")` | DST-correct; note Nov 1, 2026 is the DST end, one day before the first window |
| Env/config parsing | `os.environ` reads | `pydantic-settings` `Settings` (`EASY_A_*` aliases) | Established pattern (`config.py:33-43`) |
| Graceful shutdown | Custom signal juggling | `threading.Event` set by a `signal.signal(SIGTERM)` handler; `event.wait(timeout)` as the sleep | One primitive for both sleep and stop |
| Latency percentiles | An in-process metrics store | Structured request log + a fixed remote benchmark mode | No metrics vendor (D-08); Render graphs need Pro |
| CI for Postgres | A hand-started DB in the workflow | GitHub Actions `services: postgres:16` with health check | Standard; tests create a throwaway schema themselves |
| Uv/Node caching in CI | Manual cache steps | `setup-uv` `enable-cache`, `setup-node` `cache: npm` | Maintained by the tool owners |

**Key insight:** every "obvious" custom piece (parser, instructor state, course creation, cache rebuild) already exists and is battle-tested; the new code is orchestration plus diffing plus two pure functions (cadence, freshness thresholds). The failure modes live in the seams (pooler semantics, memory, truncated responses), which is exactly where the tests should be.

## Common Pitfalls

### Pitfall 1: Treating the whole-term response's error tail as a failure (or ignoring its meaning)
**What goes wrong:** A "response complete" check (`</table>`, `</html>`, `N records were found`) rejects every sweep; or, conversely, nothing detects a *mid-table* cut.
**Why it happens:** USF appends `<h3>We're sorry but an unexpected error has occured in this application...` after the last row of a whole-term result. Narrow results (`tests/fixtures/schedule_current.html`) end with `</table><p>2 records were found matching your criteria.</p></body></html>`. The earlier 6,663-row (9.2 s) and today's 6,640-row (15.9 s, 7,098,264 bytes) responses are both consistent with "all rows, then error".
**How to avoid:** Gate on (a) parse yields > 0 rows; (b) header row present and equal to `EXPECTED_HEADERS`; (c) parsed rows == number of `<tr>` blocks that contain `<td>`; (d) missing-vs-active ≤ 10% of the DB's active in-scope sections **and** total rows ≥ 90% of the last succeeded sweep's `records_seen`; (e) the count of distinct subjects present must not drop by more than a few percent (a cut truncates whole trailing colleges: colleges appear in order AC, AI, BC, BU, CS, DP, EN, EU, GS, HC, MD, MS, NR, PH, RO). Record `tail_error=true` in the log line, and log `Content-Encoding` and byte size on the first sweep.
**Warning signs:** rows per sweep swinging by more than a few dozen; `RO`/`PH` subjects missing from a sweep.

### Pitfall 2: The 512 MB worker runs out of memory
**What goes wrong:** Render restarts the worker on OOM; every sweep dies at the parse step.
**Why:** 443 MB peak for parse + normalize on Python 3.12 (imports alone 106 MB when `easy_a.refresh.coverage` is imported).
**How to avoid:** chunked parse (121 MB peak), lean imports, drop references to the raw HTML string as soon as chunking is done, and measure peak RSS (`/usr/bin/time -v` or `resource.getrusage`) over the whole sweep including the cache rebuild in the local soak; target < 350 MB. Docker is not installed in this WSL distro, so the first true 512 MB measurement happens on Render (watch the Metrics tab and logs).

### Pitfall 3: Session advisory lock on the transaction pooler
**What goes wrong:** Two workers (deploy overlap) both believe they hold the lock.
**Why:** "Session-level state is lost between transactions. This covers set and reset, session-level advisory locks…" [CITED: supabase.com/docs/guides/database/connecting-to-postgres].
**How to avoid:** `SELECT pg_try_advisory_xact_lock(:key)` as the first statement of the sweep transaction; sleep *outside* any transaction; no-op on SQLite. The transaction stays open during the ~16 s fetch. The `postgres` role has no statement timeout other than the ~2 min global cap [CITED: supabase.com/docs/guides/database/postgres/timeouts], and statement timeouts do not count idle time, but `idle_in_transaction_session_timeout` on this project was not verified (A2): if the soak shows "terminating connection due to idle-in-transaction timeout", fall back to fetch-then-lock (writes stay serialized; only the USF request is unguarded during the overlap) and document the trade-off.

### Pitfall 4: Deploy overlap doubles the worker for 60-90 s
**What goes wrong:** New instance is up; the old one gets SIGTERM only after 60 s and SIGKILL after `maxShutdownDelaySeconds` (default 30) [CITED: render.com/docs/deploys, "Zero-downtime deploys"]. Two sweeps in flight would violate D-22(c).
**How to avoid:** the xact lock; `maxShutdownDelaySeconds: 90` (accepted by `render blueprints validate`); a SIGTERM handler that stops sleeping immediately and lets an in-flight sweep finish or roll back; an exec-form start so the Python process is PID 1 (a shell wrapper would not forward SIGTERM). Whether Render tokenizes `dockerCommand` without a shell is unverified (A1): confirm from the first restart's logs that the "shutting down" line appears.

### Pitfall 5: Hourly cadence vs the 600/1800 s freshness thresholds
See Pattern 9. Also handle window boundaries: worker sleep capped to the next window start; API and worker must read the same `config/registration_windows.toml` (copy `config/` into the image; both processes resolve the path from a setting like `EASY_A_REGISTRATION_WINDOWS_PATH`, default `config/registration_windows.toml`, mirroring `course_targets_path`).

### Pitfall 6: `removed_at` is a cross-cutting filter
**What goes wrong:** Removed sections keep appearing in counts, coverage, quality findings, or pages; two scripts fail outright.
**Audit list (grep of `select(Section` / `Section.term_id` / `join(Section` across `src` and `scripts`):**
- `rankings/cache.py:99-103` (`refresh_section_rankings` selects **all** sections of the term, including removed ones): add `Section.removed_at.is_(None)`; also `DELETE FROM section_rankings WHERE section_id IN (newly removed)` in the sweep so the search path (which reads only `SectionRankingCache`) needs no extra join.
- `rankings/service.py:126-130` (`rank_course_sections`) and `:152-155` (`_get_section_course_term`, used by `/rankings/section`): filter, so a removed CRN returns 404.
- `analytics/queries.py:168,241`, `signals/resolver.py:68`, `refresh/coverage.py:57,95`, `api/routes/metadata.py:54` (delivery methods), `refresh/service.py:98,102` (counts), `quality/checks.py:80,315`, `quality/coverage.py:34`.
- Scripts: `scripts/validate_tampa_ingest.py:109-156` (compares section count with cache count), `scripts/verify_rankings_pages.py:105`, `scripts/inventory_tampa_grades.py:428`.
- **`scripts/benchmark_rankings_search.py:261`** `if not stored or cached != stored:` raises once removed sections exist (cache rows are deleted, `sections` rows remain), and `:186-203` `_http_base_url` accepts only a plain **loopback http** origin (`parsed.scheme != "http"`), so it cannot target the hosted URL; `tests/api/test_benchmark_rankings_search.py` asserts non-loopback URLs are rejected. Add a separate `--remote-url` (https only, no DB comparison) rather than loosening the loopback validator.
- Legacy narrow ingest `_update_section` should also set `section.removed_at = None` if the CRN is seen again.
- No index on `(term_id, removed_at)`: the cache-side deletion means search never filters on it, and the table is ~4k rows.

### Pitfall 7: `seat_snapshots` has no `(section_id, observed_at)` index
`migrations/versions/0002_create_section_syllabus_tables.py` creates `seat_snapshots` with only the primary key (no FK or lookup index; the grep for `create_index` shows none). Every latest-snapshot lookup (`hydrate_ranking`, `_seat_info_for`, the `seats_open`/`seats_desc` window function over the **whole** table when `section_ids` is `None`) scans it. Today it has 4,226 rows; after weeks of change-only sweeps in registration windows it can reach millions (A5). Put `CREATE INDEX ix_seat_snapshots_section_id_observed_at ON seat_snapshots (section_id, observed_at DESC, id DESC)` in the same 0004 migration (one go-ahead) and re-run `benchmark_rankings_search.py` against the hosted API after the soak (REQ-PERF-01 is p95 < ~1.5 s; measured 309.91 ms on 2026-09-23 before the worker existed).

### Pitfall 8: Migration ordering with `checksPass` auto-deploy
Code that references `Section.removed_at` errors against a database without the column; old code against the new column is harmless. Sequence: merge PR (CI green) → operator applies 0004 to Supabase (explicit go-ahead; `uv run alembic upgrade head` with the session-pooler URL as `MIGRATION_DATABASE_URL`) → *then* create the Blueprint (its first deploy starts immediately). After the Blueprint exists, "apply the migration before merging code that needs it" becomes a standing runbook rule. Add a startup guard (`SELECT removed_at FROM sections LIMIT 0` or an Alembic-head check) in the worker (exit non-zero with a clear message) and a startup check in the API lifespan; keep `/health` DB-free because Render polls it.

### Pitfall 9: The CI gates are not green on day one
Measured on a `git archive HEAD` clean checkout, Python 3.12, no `.env`, no `DATABASE_URL`: `pytest` **374 passed, 3 skipped**; `ruff check .` **2 errors**, both E501: `scripts/refresh_all_tampa.py:150` and `src/easy_a/refresh/cleanup.py:496` (a 2-line fix); `ruff format --check .` would reformat 39 files, so do **not** gate on format; `mypy src` **0 errors / 73 files**; `mypy .` **35 errors / 10 files** (tests/scripts). Web (Node 24): lint, typecheck, vitest (86 tests), build all pass. Fix the E501s in the CI plan's first task or the first run fails. The 3 skipped tests are the Postgres integration tests (`tests/refresh/test_postgres_coverage.py:22`, `tests/refresh/test_cleanup.py:322` read `EASY_A_TEST_POSTGRES_URL`); they have **not** been proven against a plain `postgres:16` container. Treat the first CI run with the service container as a Wave-0 verification and run them locally against `docker compose up -d db` (Docker Desktop on the Windows side) before relying on them.

### Pitfall 10: `checksPass` deploys nothing when zero checks ran
[CITED: render.com/docs/deploys] "Render does not trigger a deploy if: Zero checks are detected for the new commit / At least one CI check fails". So: workflow `on: push: branches: [main]` and `pull_request`, **no `paths:` filters**, and no `cancel-in-progress` on `main` (a cancelled check is not a pass). Use `buildFilter` on the Render services (api/worker: `src/**`, `config/**`, `migrations/**`, `pyproject.toml`, `uv.lock`, `Dockerfile`; web: `web/**`) so `.planning/` and docs commits do not restart the worker; `[skip render]` in a commit message also skips a deploy. The draft with `buildFilter` validates.

### Pitfall 11: `fromGroup: easy-a-shared` is rejected by the validator
`render blueprints validate` (CLI 2.28.0, active workspace "My Workspace (tea-datbnkm7bikc73cuhkq0)") returned `env var group linkage depends on non-existent group: easy-a-shared` for both services, while STATE.md says the group holds `DATABASE_URL`. A Blueprint that **defines** the group in `envVarGroups` validates, but the docs say group variables cannot use `sync: false`, so the secret cannot live in a Blueprint-defined group. Either the dashboard group is named differently/in another workspace, or the validator only sees Blueprint-managed groups. Resolve with a human check first; the safe fallback is per-service `DATABASE_URL` with `sync: false` (prompted once at Blueprint creation; later changes are manual). Also `EASY_A_ALLOWED_FRONTEND_ORIGINS` and `VITE_API_BASE_URL` cannot be wired with `fromService`: for a static site `host` is the *private-network* hostname, not the public URL. They are circular (API needs the site origin, site needs the API URL), so use `sync: false` and fill them after the first create (public URLs are `https://<service-name>.onrender.com`, with a random suffix if the name is taken), then redeploy the static site (`VITE_*` is baked in at build time). The origin must match exactly: scheme + host, no trailing slash (CORS uses `allow_origins=settings.allowed_frontend_origin_list()`).

### Pitfall 12: Latency observability
Render's Response Times graph requires a Pro workspace [CITED: render.com/docs/service-metrics]; the workspace plan was not verified (A6). Per-request log lines (Pattern 8) are the only universal source; Render keeps logs 7 days on Hobby, so a p95 needs a documented one-liner over exported logs, or a remote benchmark run (Pitfall 6). Also: no Render alert fires if the worker is alive but every sweep fails (D-09 accepts this); the `/sync-status` failure count plus the student-facing stale warning are the safety net, so the runbook needs a "check sync-status daily" step.

### Pitfall 13: Registration windows: the page says more than D-02 encodes
The Registrar's registration page states that once a student's time has passed they "can continue to access the registration system through the end of the add/drop period" (raw WebFetch summary, no date on the page). Demand for fresh seats therefore runs Nov 2 through Jan 15, not only on the listed group days. D-02 is locked (Nov 2-30, Jan 7, Jan 11-15, hourly in between), so encode it as data and surface the alternative in Open Questions. Volume check for the user: D-02 windows = 29 + 1 + 5 = 35 days x 288 sweeps = 10,080 whole-term requests (~2 GB/day of 7 MB responses; 9-16 s of USF server time each).

### Pitfall 14: Legacy ingest still appends
`scripts/refresh_all_tampa.py`, `refresh_seats.py` and `refresh_course_coverage.py` call `ingest_schedule_html`, which appends an instructor row and a snapshot for every section on every run (`schedule/ingest.py:88-104`, and `seat_snapshots_created=len(rows)`). Running them for 202701 after the worker is live re-creates the append-everything problem and issues many USF requests. Runbook: for Spring 2027 use the worker (`--once` / `--dry-run`), not the legacy scripts.

### Pitfall 15: Cancelled sections are still listed by USF
Of 3,700 undergraduate rows, 359 have `secondary_status` `U`/`C` (Cancelled without/with Enrollment) and 10 have a status `R` that is missing from `SECONDARY_STATUS_LABELS` (`normalize.py:10-16` has A, C, H, N, U). They are *present* in the sweep, so `removed_at` never marks them, yet students see them as normal sections today. This is existing behaviour and outside the locked decisions; flag it (Open Questions) rather than silently changing search semantics.

### Pitfall 16: Timezone data in the image
`zoneinfo.ZoneInfo("America/New_York")` raises `ZoneInfoNotFoundError` if neither the OS tz database nor the `tzdata` package exists. Not verifiable here (no Docker). Add a startup self-check in both processes and either the explicit `tzdata` dependency (checkpoint) or `apt-get install tzdata`.

### Pitfall 17: `.env` in the Docker build context
The working tree has a real `.env` with `DATABASE_URL` (git-ignored). Render builds from git so it is safe there, but a local `docker build` would bake it into a layer. `.dockerignore` must list `.env`, `.env.*`, `.venv`, `.git`, `web/node_modules`, `web/dist`, `data/`, `courses.csv`, `.planning/`, `*.xlsx`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache` and must **not** exclude `README.md` (hatchling's `readme = "README.md"` is read at `uv sync` time), `pyproject.toml`, `uv.lock`, `src/`, `config/`, `migrations/`, `alembic.ini`.

## Code Examples

Sketches only; the planner turns these into tasks. Provenance is noted per block.

### Whole-term client path (explicit; narrow validation untouched)
```python
# Source: reuses build_form_data (src/easy_a/schedule/client.py:65-90) and RESULTS_PATH (:10).
# Quoted values: RESULTS_PATH = "/DSS/StaffScheduleSearch/StaffSearch/Results"
#                "P_CAMPUS": (query.campus or "").strip().upper(),  "P_SUBJ": (query.subject or "").strip().upper(),
# ScheduleSearchQuery.__post_init__ raises ValueError("A narrow schedule search requires --crn or --subject.")
def search_term(self, term: str, campus: str = "T") -> str:
    # Build the form without ScheduleSearchQuery so its narrow-query guard is not loosened.
    form = build_form_data(_WholeTermQuery(term=term, campus=campus))  # duck-typed: term/campus/subject=None/course=None/crn=None
    response = self._client.post(RESULTS_PATH, data=form)
    response.raise_for_status()
    return response.text
# Use a longer read timeout for this call: measured 9.2 s and 15.9 s; StaffScheduleClient default is 30 s.
```

### Chunked parse with fail-closed checks (parity-verified prototype)
```python
# Prototype measured 2026-09-29 on the real response: 6,640 rows, parity with full parse True,
# peak RSS 121 MB (vs 443 MB), 2.6 s. Regexes are the ones that matched the live page.
HEADER_RE = re.compile(r"<tr[^>]*>\s*(?:<th.*?</th>\s*)+</tr>", re.S | re.I)
ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S | re.I)

def parse_whole_term(html: str, chunk: int = 250) -> list[ParsedScheduleRow]:
    header = HEADER_RE.search(html)
    if header is None:
        raise ScheduleParseError("Schedule result table headers were not found.")
    body = html[header.end():]
    rows: list[ParsedScheduleRow] = []
    buf: list[str] = []
    td_rows = 0
    for m in ROW_RE.finditer(body):
        block = m.group(0)
        if "<td" in block.lower():
            td_rows += 1
        buf.append(block)
        if len(buf) >= chunk:
            rows += parse_schedule_html("<table>" + header.group(0) + "".join(buf) + "</table>")
            buf.clear()
    if buf:
        rows += parse_schedule_html("<table>" + header.group(0) + "".join(buf) + "</table>")
    if len(rows) != td_rows:  # parse_schedule_html silently skips rows without 24 cells
        raise ScheduleParseError(f"Parsed {len(rows)} rows from {td_rows} data rows.")
    return rows
```

### Transaction-scoped advisory lock
```python
# Source: Supabase docs (session-level advisory locks are lost between transactions on port 6543).
SYNC_LOCK_KEY = 0x45415359_4E43  # arbitrary stable bigint, e.g. "EASYNC"

def try_sweep_lock(session: Session) -> bool:
    if session.get_bind().dialect.name != "postgresql":
        return True  # SQLite tests
    return bool(session.scalar(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": SYNC_LOCK_KEY}))
```

### Cadence (pure, upward-only jitter, window-start cap)
```python
def interval_for(now: datetime, windows: RegistrationWindows) -> timedelta:
    return timedelta(minutes=5) if windows.contains(now) else timedelta(minutes=60)

def next_start(prev_start: datetime, now: datetime, windows: RegistrationWindows, *, rng: random.Random,
               failures: int = 0) -> datetime:
    base = interval_for(prev_start, windows)
    interval = base * rng.uniform(1.0, 1.2)                 # never below the floor
    if failures:
        interval = max(interval, min(timedelta(minutes=60), timedelta(minutes=5) * 2**failures))
    target = max(prev_start + interval, now)
    boundary = windows.next_boundary_after(prev_start)      # local-midnight window start
    if boundary is not None and boundary < target and boundary >= prev_start + timedelta(minutes=5):
        target = boundary                                   # fire at window start
    return target
```

### `config/registration_windows.toml` (dates verified from official USF pages)
```toml
# Whole days, interpreted in `timezone`. Sources fetched 2026-09-29. Dates are subject to change.
term = "202701"
timezone = "America/New_York"

[[windows]]
label = "Priority registration by class standing (first group Nov 2, Non-Degree Nov 30)"
start = 2026-11-02
end = 2026-11-30
source = "https://www.usf.edu/registrar/register/registration_times.aspx"

[[windows]]
label = "Spring State employee registration (5 p.m.)"
start = 2027-01-07
end = 2027-01-07
source = "https://www.usf.edu/registrar/calendars/index.aspx"

[[windows]]
label = "Spring drop/add: classes begin Jan 11, drop/add ends Jan 15"
start = 2027-01-11
end = 2027-01-15
source = "https://www.usf.edu/registrar/calendars/index.aspx"
```
Verified USF Registrar text (raw page, fetched 2026-09-29): "November 2 Spring registration begins for degree-seeking students … November 30 Non-degree registration begins for Spring … January 7 Spring State employee registration at 5 p.m. January 8 Last day to register for Spring without late registration fee penalty … January 11 Spring classes begin … January 15 Spring drop/add ends; fee liability/tuition payment deadline". The page header adds: "Dates and times listed below are subject to change."

### Blueprint draft (passes `render blueprints validate`, CLI 2.28.0)
```yaml
# Validated 2026-09-29 with `render blueprints validate render3.yaml -o text` -> {"valid": true}.
# fromGroup was deliberately left out (Pitfall 11); DATABASE_URL is sync:false per service.
services:
  - type: web
    name: easy-a-api
    runtime: docker
    region: ohio
    plan: starter            # accepted; the docs table also lists the ID 0.5c-512mb ($7/mo, 512 MB, 0.5 CPU)
    autoDeployTrigger: checksPass
    healthCheckPath: /health
    dockerfilePath: ./Dockerfile
    dockerContext: .
    buildFilter:
      paths: [src/**, config/**, migrations/**, pyproject.toml, uv.lock, Dockerfile]
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: EASY_A_ALLOWED_FRONTEND_ORIGINS
        sync: false
  - type: worker
    name: easy-a-worker
    runtime: docker
    region: ohio
    plan: starter
    autoDeployTrigger: checksPass
    dockerCommand: python -m easy_a.sync --term 202701
    maxShutdownDelaySeconds: 90
    buildFilter:
      paths: [src/**, config/**, pyproject.toml, uv.lock, Dockerfile]
    envVars:
      - key: DATABASE_URL
        sync: false
  - type: web
    name: easy-a-web
    runtime: static
    autoDeployTrigger: checksPass
    buildCommand: cd web && npm ci && npm run build
    staticPublishPath: web/dist
    buildFilter:
      paths: [web/**]
    envVars:
      - key: VITE_USE_MOCK_DATA
        value: "false"
      - key: VITE_API_BASE_URL
        sync: false
      - key: NODE_VERSION
        value: "24"
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
```

### Dockerfile sketch (Docker is not available locally; verify in the CI `docker build` job)
```dockerfile
# Pattern from docs.astral.sh/uv/guides/integration/docker/ (python:3.12-slim-trixie + uv layers).
FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project
COPY src ./src
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked
# Default = API. exec so uvicorn is PID 1 and receives SIGTERM. PORT defaults to 10000 on Render.
CMD ["sh", "-c", "exec uvicorn easy_a.api.app:app --host 0.0.0.0 --port ${PORT:-10000}"]
```
The worker overrides with `dockerCommand: python -m easy_a.sync --term 202701`. `Settings.course_targets_path` is relative (`config/course_targets.toml`), so `WORKDIR /app` matters. Note `EASY_A_API_HOST`/`EASY_A_API_PORT` exist in `config.py` but no code reads them (grep), so bind through the uvicorn flags.

### CI workflow sketch
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
jobs:
  python:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: easy_a, POSTGRES_USER: easy_a, POSTGRES_PASSWORD: easy_a }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U easy_a -d easy_a" --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      EASY_A_TEST_POSTGRES_URL: postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.2.0        # exact tag; no floating major tag exists
        with: { python-version: "3.12", enable-cache: true }
      - run: uv sync --locked
      - run: uv run ruff check .                 # fix the 2 pre-existing E501 first
      - run: uv run pytest -q
      - run: uv run mypy src                     # 0 errors today; recommend hard gate (deviation from D-12, flag)
      - run: uv run mypy .
        continue-on-error: true                  # report-only baseline (35 errors / 10 files)
  web:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: web } }
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with: { node-version: "24", cache: npm, cache-dependency-path: web/package-lock.json }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test
      - run: npm run build
        env: { VITE_USE_MOCK_DATA: "false", VITE_API_BASE_URL: "https://example.onrender.com" }
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: docker build -t easy-a:ci .
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `autoDeploy: true/false` in `render.yaml` | `autoDeployTrigger: commit \| checksPass \| off` | Deprecated field; new field takes precedence | Use `checksPass` for D-13 |
| Render plan names `starter`/`standard` | Plan IDs `free`, `0.5c-512mb`, `1c-2g`… (legacy `starter` still validates) | Current docs list only the new IDs | Prefer `0.5c-512mb` once you have re-validated; both pass the CLI today |
| Floating major tags for actions | `astral-sh/setup-uv` publishes exact tags only (no `v10`/`v9`) | Current | Pin `@v10.2.0` or a SHA |
| Session-level DB state through poolers | Transaction-scoped state only on Supabase 6543 | Supavisor design | `pg_try_advisory_xact_lock` |
| Per-subject USF fetches (212 requests) | One whole-term request (D-22) | 2026-09-28 finding | Sweep is 1 request; response is always error-tailed |

**Deprecated/outdated:**
- `.planning/codebase/*` maps are dated pre-Sprint-5 (structure only).
- STATE.md's "323 passed, 3 skipped" baseline is stale; measured today: 374 passed, 3 skipped.
- The plan's "~92 removals / ~84 instructor changes / ~7 new" figures are superseded by today's 104 / 89 / 21.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Render's `dockerCommand` runs a single command without a wrapping shell, so `python -m easy_a.sync` is PID 1 and gets SIGTERM directly | Pitfall 4 | Graceful shutdown never runs; worker is SIGKILLed mid-sweep (safe because of single-transaction design, but noisy) |
| A2 | Supabase does not kill an idle-in-transaction session during the ~16 s USF fetch (`idle_in_transaction_session_timeout` unverified for this project) | Pitfall 3 | Sweep fails on every run; fallback is fetch-then-lock |
| A3 | Render's shared outbound IPs are not blocked or throttled by `usfweb.usf.edu` | Summary | Worker gets 403/timeouts; sweeps fail from the host though they succeed locally |
| A4 | `NODE_VERSION=24` (a bare major) is accepted for static-site builds | Blueprint draft | Static build uses Render's default Node; Vite 7 needs a recent Node |
| A5 | `seat_snapshots` growth in registration windows reaches 10^5 rows/day (10-30% of ~3.7k sections changing per sweep) | Pitfall 7 | DB size and search p95 regress; may need retention/compaction sooner |
| A6 | The Render workspace is on a plan below Pro (so latency graphs are unavailable) | Pitfall 12 | Log-based p95 is unnecessary extra work |
| A7 | `python:3.12-slim-trixie` lacks (or has) system tzdata; unverified, Docker not installed here | Pitfall 16 | `ZoneInfoNotFoundError` at startup unless `tzdata` is installed |
| A8 | The whole-term response is complete apart from the error tail for *all* subjects (verified by exact CRN match for PHC only, plus the 231-subject count matching 2026-09-28) | Pitfall 1 | A partial sweep passes the gate; mitigated by the subject/row-count checks and reversible `removed_at` |
| A9 | Node 24 is the current LTS line | CI sketch | CI uses an older Node than local; low risk (local gates pass on v24.21.0) |
| A10 | Render OOM behaviour: the platform restarts an instance that exceeds its plan memory | Pitfall 2 | Different failure mode than modelled |
| A11 | The Supabase plan/database size limit is large enough for the snapshot growth in A5 | Pitfall 7 | Writes fail when the size limit is hit |

## Open Questions

1. **Does the dashboard env group `easy-a-shared` really exist under that name in the active workspace?**
   - What we know: `render blueprints validate` says it does not; STATE.md says it exists with `DATABASE_URL`.
   - What's unclear: whether the validator only sees Blueprint-defined groups.
   - Recommendation: first plan task is a `checkpoint:human-verify` in the dashboard, then re-run validate; if it still fails, use per-service `DATABASE_URL` (`sync: false`).

2. **Should sections USF lists as cancelled (`secondary_status` `U`/`C`, 359 undergraduate rows) stay in search?**
   - What we know: today they display like normal sections; they are *not* "removed" (they are present in the sweep).
   - Recommendation: out of Phase 9's locked scope; ask the user whether to hide or label them (a one-line filter/label decision), and add `R` to `SECONDARY_STATUS_LABELS` once its meaning is confirmed.

3. **Should the Jan 7 window be extended to Jan 15 (contiguous)?**
   - What we know: D-02 locks Jan 7 and Jan 11-15 as separate windows; Jan 8 is "last day to register without late fee".
   - Recommendation: keep D-02 as locked; make it a one-line config edit and mention it in the plan summary.

4. **Where does the per-sweep change summary live?** `IngestRun` has no summary column (`source`, `started_at`, `finished_at`, `status`, `records_seen`, `records_inserted`, `records_updated`, `records_failed`, `error_message`).
   - Recommendation: map inserted → new sections, updated → sections with any change, failed → auto-add/row failures, and put the full change summary in a structured log line. Adding a JSON column in 0004 is possible (same go-ahead) but not required.

5. **`mypy src` as a hard gate (deviation from D-12 as written)?** It is clean today. Recommend yes, keep `mypy .` report-only; flag for user review with D-11..D-13.

6. **Retention/growth of `seat_snapshots`** after the registration windows (A5): decide at the soak whether a later compaction phase is needed. Not Phase 9 scope, but measure row growth and record it.

7. **Term rollover:** the worker is per-term (`--term 202701`); Summer/Fall 2027 registration (Summer/Fall opens Mar 29, 2027) needs a config and Blueprint change. Out of scope; note it in the runbook.

8. **Per-sweep USF load** (Pitfall 13): confirm the user accepts ~10,080 whole-term requests over the D-02 windows; consider logging `Content-Encoding`/bytes on the first sweep to confirm compression.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | install/test/CI | yes | 0.12.17 | — |
| Python 3.12 (via uv) | image parity, tests | yes | 3.12.14 | — |
| Node / npm | web gates | yes | v24.21.0 / 11.19.0 | — |
| Render CLI | Blueprint validation | yes (logged in, "My Workspace") | 2.28.0 | Dashboard validation |
| `gh` CLI | verify Actions tags, repo settings | yes | 2.46.0 | — |
| GitHub Actions on the repo | CI | yes (public repo, Actions enabled, `allowed_actions: all`) | — | — |
| Docker | local image build/memory test | **no** ("docker could not be found in this WSL 2 distro"; Docker Desktop WSL integration off) | — | CI `docker build` job; first true 512 MB measurement on Render; or enable WSL integration |
| Postgres for `EASY_A_TEST_POSTGRES_URL` locally | 3 integration tests | not running locally | — | CI service container; `docker compose up -d db` from Windows |
| Hosted Supabase (read-only queries) | measurements | yes (`DATABASE_URL` set locally; queried inside `SET TRANSACTION READ ONLY`, rolled back) | — | — |
| USF StaffScheduleSearch / catalog / registrar pages | measurements | yes from this WSL host | — | — |

**Missing dependencies with no fallback:** none blocking planning.
**Missing dependencies with fallback:** Docker (see above).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.3.0 (Python), vitest ^3.2.4 (web) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]`; `web/vite.config.ts` (`environment: "jsdom"`, `setupFiles: "./src/test/setup.ts"`) |
| Quick run command | `uv run pytest tests/sync tests/schedule tests/api -q -x` |
| Full suite command | `uv run pytest -q` (about 8 s, 374 passed / 3 skipped baseline) and `cd web && npm test` (about 16 s, 86 tests) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-SYNC-01 | `search_term` sends empty `P_SUBJ`, `P_CAMPUS=T`; `ScheduleSearchQuery` still rejects narrow-less queries | unit (httpx `MockTransport`) | `uv run pytest tests/schedule/test_client.py -q` | extend existing |
| REQ-SYNC-01 | Chunked parse equals full parse; error tail tolerated; header missing raises; `<td>` row count mismatch raises | unit | `uv run pytest tests/sync/test_wholeterm_parse.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Scope filter: Tampa only, `int(number[:4]) < 5000` (incl. `0001`, excl. `5xxx`/`9xxx`), duplicate CRN rejected | unit | `uv run pytest tests/sync/test_scope.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Unchanged sweep writes 0 instructor rows and 0 snapshots; name change writes exactly 1; seat change writes exactly 1; new CRN inserts; absent CRN sets `removed_at`; reappearing CRN clears it; `last_seen_at` bulk-updated | unit (SQLite `db_session`) | `uv run pytest tests/sync/test_diff_apply.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Sanity gate: empty, header-changed, >10% missing, row floor, subject-drop each abort with DB unchanged and a `failed` `IngestRun` in a second transaction | unit | `uv run pytest tests/sync/test_gate.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Auto-add: fake catalog fetch adds course + sections with fallback label; failed course counted in `records_failed`; per-sweep cap; negative cache | unit | `uv run pytest tests/sync/test_courses.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Rebuild only on structural change (seat-only sweep does not call `refresh_section_rankings`); removed sections' cache rows deleted | unit | `uv run pytest tests/sync/test_cache_upkeep.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Cadence: in-window 300 s floor, outside 3600 s floor, jitter never below floor, window-start cap, `America/New_York` boundaries (DST ended Nov 1, 2026), failure backoff never below tier floor | unit (pure, injected `now`/`rng`) | `uv run pytest tests/sync/test_windows.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Windows config validates (`extra=forbid`, ordered, non-overlapping, dates as in D-02) | unit | `uv run pytest tests/sync/test_windows_config.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Advisory xact lock: second connection cannot acquire while first sweep transaction is open | Postgres integration (skips w/o env) | `EASY_A_TEST_POSTGRES_URL=... uv run pytest tests/sync/test_lock_postgres.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | `--dry-run` performs no writes (row counts unchanged; READ ONLY on Postgres) and makes no catalog requests | unit + Postgres | `uv run pytest tests/sync/test_dry_run.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Loop stops promptly on SIGTERM Event; never starts a sweep sooner than the floor | unit | `uv run pytest tests/sync/test_runner.py -q` | ❌ Wave 0 |
| REQ-SYNC-01 | Freshness uses `last_seen_at` and cadence-aware thresholds; legacy behaviour unchanged when `verified_at is None` | unit | `uv run pytest tests/schedule tests/rankings tests/api -q` | extend existing |
| REQ-SYNC-01 | Search, `/rankings/section`, `/rankings/course` exclude removed sections | API test | `uv run pytest tests/api/test_rankings_api.py -q` | extend existing |
| REQ-SYNC-01 | UI shows "Updated N min ago" and stale warning from `is_stale` | vitest | `cd web && npm test` | ❌ Wave 0 (`SyncStatus.test.tsx`) |
| REQ-OPS-01 | `/api/v1/metadata/sync-status` returns last success, last status, recent failures, cadence, `is_stale`, no raw error text | API test | `uv run pytest tests/api/test_sync_status.py -q` | ❌ Wave 0 |
| REQ-OPS-01 | Request-duration log line carries route template, status, `duration_ms` | unit (`caplog`) | `uv run pytest tests/api/test_request_logging.py -q` | ❌ Wave 0 |
| REQ-OPS-01 | Benchmark remote mode accepts https only and skips DB comparison; loopback validator unchanged; count check uses `removed_at IS NULL` | unit | `uv run pytest tests/api/test_benchmark_rankings_search.py -q` | extend existing |
| REQ-OPS-01 | CI workflow runs the gates on a clean checkout | integration (GitHub) | push a branch; all jobs green | ❌ Wave 0 |
| REQ-OPS-01 | Blueprint valid; Dockerfile builds; image runs both commands | manual + CI | `render blueprints validate render.yaml -o text`; CI `docker build` | ❌ Wave 0 |
| REQ-OPS-01 | Hosted beta reachable, serves real data, "Updated N min ago" advances, Staff→named appears within one cadence interval | manual (live) | runbook checklist | manual-only (needs deployed hosts) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/sync -q -x` (plus `cd web && npm test` for UI tasks)
- **Per wave merge:** `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`, `cd web && npm run lint && npm run typecheck && npm test && npm run build`
- **Phase gate:** full suite green in CI (including the Postgres service container) before `/gsd-verify-work`; then the live soak and hosted checklist

### Wave 0 Gaps
- [ ] `tests/sync/__init__.py` and the `tests/sync/test_*.py` files above (other test dirs are packages with `__init__.py`)
- [ ] A **synthetic** whole-term fixture generator (repeat/vary rows from the existing 2-row `tests/fixtures/schedule_current.html` shape, append the USF error tail; never commit the real 7 MB response)
- [ ] Fix `scripts/refresh_all_tampa.py:150` and `src/easy_a/refresh/cleanup.py:496` (E501) so `ruff check .` is green
- [ ] Prove the 3 skipped Postgres tests against `postgres:16` (locally via `docker compose` or on the first CI run)
- [ ] `web/src/components/SyncStatus.test.tsx`
- [ ] Live soak protocol: run the worker locally for a few hours against Supabase (after the go-ahead migration), confirm `ingest_runs` accumulate, unchanged sweeps write no instructor/seat rows, each sweep < 30 s, peak RSS < 350 MB, then `benchmark_rankings_search.py --live` p95

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (absent = enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth/accounts by project decision |
| V3 Session Management | no | Stateless read-only API |
| V4 Access Control | limited | New endpoint is read-only public aggregate data; Render dashboard/GitHub permissions gate deploys |
| V5 Input Validation | yes | Treat the USF response as untrusted: content-type and size cap (refuse > ~25 MB), fail-closed parse, pydantic models (`ParsedScheduleRow`, `NormalizedSection`); ORM/bound parameters only; registration-window config validated by pydantic (`extra=forbid`) |
| V6 Cryptography | no | TLS only (httpx verifies certificates; Supabase URL uses `sslmode=require`); nothing hand-rolled |
| V7 Error Handling / Logging | yes | Structured logs must never contain `DATABASE_URL`, passwords or raw DSNs; public status endpoint returns an error *category*, not the exception text |
| V13/V14 API & Configuration | yes | Secrets only in Render env (`sync: false`); `.dockerignore` excludes `.env`; CI has no secrets; CORS exact origin (`allow_methods=["GET"]`, `allow_credentials=False` already in `app.py`) |
| V10 Malicious code / supply chain | yes | Pin third-party Action to an exact tag/SHA (`setup-uv@v10.2.0`), `permissions: contents: read`, `uv sync --locked`, `npm ci`; new dependency `tzdata` behind a human check |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Truncated/poisoned upstream response marks half the catalog removed | Tampering / DoS | Integrity gate before any write; single transaction; removals are reversible marks; restore on reappearance |
| Two workers during deploy overlap poll USF and write concurrently | Tampering | `pg_try_advisory_xact_lock` at transaction start |
| Secret baked into an image layer | Information disclosure | `.dockerignore`; Render builds from git; no `ARG`/`ENV` secrets in the Dockerfile |
| DB host/port leaked through a public status endpoint | Information disclosure | Return coarse `error_kind`; raw text stays in `ingest_runs`/logs |
| Runaway request rate against USF (bug in cadence) | Abuse of upstream | Floor enforced in one pure function with tests; interval measured from previous *start*; backoff never shortens the interval; identifying User-Agent kept |
| CI compromise via mutable action tag | Tampering | Exact-tag/SHA pin for non-official action, least-privilege token |
| Oversized response exhausts memory | DoS | Size cap + chunked parse + 512 MB budget check |

## Project Constraints (from CLAUDE.md / AGENTS.md)

`CLAUDE.md` only points to `AGENTS.md`; the actionable directives (treated with the authority of locked decisions):
- No scoring rewrite without explicit approval; the historical easiness score is frozen (D-02). Seats, GenEd, modality and syllabus signals must not affect scoring (D-03). Auto-added courses must show the `subject`/`global` fallback label (D-20); never present `effective_n = 0` as evidence-backed.
- No fabricated data or coverage; every figure has a real source and date; report failures instead of omitting them (D-06); explicit unavailable/insufficient states (D-07).
- Preserve term + CRN identity and grade-row uniqueness by term/CRN/source (D-04).
- Never commit raw grade export files (D-19). (By extension, do not commit the raw 7 MB whole-term HTML; use a synthetic fixture.)
- Narrow, bounded requests to USF public sources; the only exception is D-22's single whole-term request per sweep on the tiered cadence and the five-term backfill (D-08/D-09/D-22). Catalog lookups for auto-added courses must be bounded, paced, per-new-course requests.
- No LLM/AI features, no auth/accounts, no auto-registration.
- Verify `origin/main` by fetch and work from a branch descended from it; do not check out or fast-forward an unverified local `main` (D-10).
- Keep `.planning/STATE.md` accurate when finishing; live facts live only there.
- The measurements in this research issued: 1 whole-term request, 1 narrow PHC request, 9 paced catalog requests (2 s spacing), 1 registrar page fetch plus 1 registration-times fetch, and one read-only DB session. They are recorded here as provenance; none wrote to hosted data.

## Sources

### Primary (HIGH confidence)
- Codebase files read this session with line references: `src/easy_a/schedule/{client,parser,normalize,ingest,freshness}.py`, `src/easy_a/models/{core,sections}.py`, `src/easy_a/common/{instructors,lookups}.py`, `src/easy_a/rankings/{cache,service}.py`, `src/easy_a/api/{app,dependencies}.py`, `src/easy_a/api/routes/{metadata,rankings}.py`, `src/easy_a/refresh/{coverage,targets,service}.py`, `src/easy_a/catalog/{ingest,client,parser}.py`, `src/easy_a/{config,db}.py`, `migrations/versions/0002*,0003*`, `scripts/benchmark_rankings_search.py`, `tests/conftest.py`, `tests/schedule/test_ingest.py`, `web/src/api/rankings.ts`, `web/src/utils/time.ts`, `web/src/components/{Badges,CoverageNotice}.tsx`, `pyproject.toml`, `uv.lock`
- Live measurements 2026-09-29 (this session): whole-term response analysis, PHC cross-check, catalog probes, read-only Supabase diff, baseline test/lint/type/build runs on Python 3.12 and Node 24, memory measurements
- `render blueprints validate` output (Render CLI v2.28.0) for the draft Blueprints
- USF Registrar calendar (raw HTML): https://www.usf.edu/registrar/calendars/index.aspx
- USF Registrar registration times: https://www.usf.edu/registrar/register/registration_times.aspx

### Secondary (MEDIUM confidence)
- Render docs: https://render.com/docs/blueprint-spec (plan IDs, `autoDeployTrigger`, `buildFilter`, static site keys, env group rules), https://render.com/docs/deploys (CI-checks behaviour, zero-downtime, graceful shutdown, `[skip render]`), https://render.com/docs/web-services and https://render.com/docs/environment-variables (`PORT` default 10000, bind `0.0.0.0`), https://render.com/docs/service-metrics (latency graphs Pro-only, retention), https://render.com/docs/logging (7-day retention, 6,000 lines/min), https://render.com/docs/notifications (failure emails), https://render.com/pricing ($7/mo 512 MB 0.5 CPU `0.5c-512mb`)
- Supabase docs: https://supabase.com/docs/guides/database/connecting-to-postgres (transaction mode loses session-level advisory locks; prepared statements), https://supabase.com/docs/guides/database/postgres/timeouts (`postgres` role: no role timeout, capped by ~2 min global)
- uv Docker guide (WebFetch summary): https://docs.astral.sh/uv/guides/integration/docker/
- GitHub Actions tag lookups via `gh api` (checkout v7.0.1, setup-node v7.0.0, setup-uv v10.2.0; `v10`/`v9` floating tags absent)

### Tertiary (LOW confidence)
- Assumptions A1-A11 above (Render runtime specifics not exercised; Debian slim tzdata; Supabase idle-in-transaction default; USF-side treatment of Render IPs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — everything is already in the repo; versions measured; only `tzdata` is new and optional.
- Architecture: HIGH for the sync transaction, gate, memory and consumer audit (measured/read); MEDIUM for Render runtime semantics (validated by the CLI and docs, not by a deploy).
- Pitfalls: HIGH for 1-3, 6-10, 14-15, 17 (measured or read in code/docs this session); MEDIUM for 4, 11-13, 16 (docs or unverifiable here).

**Research date:** 2026-09-29
**Valid until:** 2026-10-13 for Render/GitHub Actions specifics (fast-moving); the USF response shape and registrar dates should be re-checked at plan execution and again before Nov 2, 2026 because the registrar states dates are subject to change.
