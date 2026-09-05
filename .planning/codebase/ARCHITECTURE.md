<!-- refreshed: 2026-09-05 -->
# Architecture

**Analysis Date:** 2026-09-05

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    Browser (React SPA)                       │
├──────────────────┬──────────────────┬───────────────────────┤
│   App shell      │  Filter/Table UI │   API client layer     │
│  `web/src/App.tsx`│ `web/src/components/`│ `web/src/api/rankings.ts`│
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │  HTTP GET /api/v1/... (VITE_API_BASE_URL)
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI HTTP layer                        │
│  `src/easy_a/api/app.py` · routes in `src/easy_a/api/routes/`│
│  DI + validation: `src/easy_a/api/dependencies.py`           │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                Domain service layer (pure Python)            │
│  rankings `src/easy_a/rankings/service.py`                   │
│  analytics `src/easy_a/analytics/` · signals `src/easy_a/signals/`│
│  refresh orchestration `src/easy_a/refresh/service.py`       │
│  quality `src/easy_a/quality/checks.py`                      │
└────────┬───────────────────────────────────┬────────────────┘
         │                                   │
         ▼                                   ▼
┌────────────────────────────┐   ┌───────────────────────────┐
│ Ingest pipelines           │   │ SQLAlchemy ORM + session  │
│ catalog/ grades/ schedule/ │   │ `src/easy_a/models/`      │
│ syllabi/ (client→parser→   │   │ `src/easy_a/db.py`        │
│ ingest)                    │   │                           │
└────────┬───────────────────┘   └──────────┬────────────────┘
         │ HTTP fetch of USF public sources │
         ▼                                  ▼
┌────────────────────────────┐   ┌───────────────────────────┐
│ USF catalog / schedule /   │   │ PostgreSQL 16             │
│ syllabus / grade files     │   │ `docker-compose.yml`      │
│                            │   │ migrations `migrations/`  │
└────────────────────────────┘   └───────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App factory | Builds FastAPI app, CORS, error handler, router wiring | `src/easy_a/api/app.py` |
| Rankings routes | `/api/v1/rankings/{section,course,search}` HTTP surface | `src/easy_a/api/routes/rankings.py` |
| Metadata routes | Terms/subjects/gen-ed/delivery filter vocabularies | `src/easy_a/api/routes/metadata.py` |
| API DI | Session generator, Banner term normalization/422 | `src/easy_a/api/dependencies.py` |
| Response schemas | Request enums + envelope models | `src/easy_a/api/schemas.py` |
| Ranking service | Composes section ranking from analytics, signals, seats, modality | `src/easy_a/rankings/service.py` |
| Ranking DTOs | `SectionRanking` and nested pydantic models (shared by API + CLI) | `src/easy_a/rankings/models.py` |
| Analytics | Historical grade aggregation, easiness scoring, confidence labels | `src/easy_a/analytics/queries.py`, `scoring.py`, `confidence.py` |
| Signals | Deterministic syllabus rule extraction and per-section resolution | `src/easy_a/signals/extract.py`, `rules.py`, `resolver.py` |
| Refresh orchestrator | Runs staged, independently committed ingest of all sources | `src/easy_a/refresh/service.py` |
| Ingest pipelines | Fetch → parse → upsert per source | `src/easy_a/{catalog,grades,schedule,syllabi}/` |
| Quality checks | Post-refresh data-quality assertions | `src/easy_a/quality/checks.py` |
| ORM models | Table definitions and relationships | `src/easy_a/models/core.py`, `sections.py` |
| DB plumbing | Engine, session factory, `session_scope`, naming convention | `src/easy_a/db.py` |
| Settings | Env-driven pydantic-settings config | `src/easy_a/config.py` |
| Web API client | Fetch + mock-fixture fallback for the SPA | `web/src/api/rankings.ts` |

## Pattern Overview

**Overall:** Layered modular monolith — a package-per-domain Python backend serving both a thin read-only HTTP API and argparse CLIs over a shared service layer, with a decoupled React SPA client.

**Key Characteristics:**
- Every domain package follows the same internal shape: `client.py` (network) → `parser.py` (HTML/file → dataclasses) → `ingest.py` (upsert) → `cli.py` (entry point).
- The API is a thin adapter: routes contain no business logic, only exception translation to HTTP status codes.
- Pydantic models in `src/easy_a/rankings/models.py` double as domain DTOs and FastAPI response models, so CLI JSON and API JSON are identical.
- Read path and write (ingest) path are fully separate; the API never fetches from USF sources.
- Frontend is source-agnostic: it renders synthetic fixtures when `VITE_API_BASE_URL` is unset.

## Layers

**Presentation (web):**
- Purpose: Filter, sort, page, and explain section rankings
- Location: `web/src/`
- Contains: React 19 function components, hooks-based state in `web/src/App.tsx`
- Depends on: `web/src/api/rankings.ts`, `web/src/types/rankings.ts`
- Used by: Browser only

**HTTP API:**
- Purpose: Read-only JSON over computed rankings
- Location: `src/easy_a/api/`
- Contains: Routers, dependencies, schemas
- Depends on: Domain services, ORM models
- Used by: `web/`, direct HTTP consumers

**Domain services:**
- Purpose: Ranking composition, analytics, signal resolution, refresh orchestration
- Location: `src/easy_a/rankings/`, `analytics/`, `signals/`, `refresh/`, `quality/`
- Contains: Pure functions taking an explicit `Session` as first argument
- Depends on: `src/easy_a/models/`, `src/easy_a/common/`
- Used by: API routes, CLIs, tests

**Ingest:**
- Purpose: Pull USF public data into Postgres
- Location: `src/easy_a/catalog/`, `grades/`, `schedule/`, `syllabi/`
- Contains: HTTP clients, parsers, upsert routines
- Depends on: `src/easy_a/models/`, `src/easy_a/common/lookups.py`
- Used by: `src/easy_a/refresh/service.py`, `scripts/ingest_*.py`

**Persistence:**
- Purpose: Schema and session management
- Location: `src/easy_a/models/`, `src/easy_a/db.py`, `migrations/`
- Contains: Declarative models on `Base`, Alembic revisions
- Depends on: PostgreSQL
- Used by: Everything above

## Data Flow

### Primary Request Path (ranking search)

1. SPA issues `GET /api/v1/rankings/search?...` (`web/src/api/rankings.ts`)
2. FastAPI validates and normalizes the Banner term via `get_banner_term` (`src/easy_a/api/dependencies.py`)
3. Route handler `search_rankings` builds the filtered candidate query (`src/easy_a/api/routes/rankings.py`)
4. `rank_section` / `rank_course_sections` compose the ranking (`src/easy_a/rankings/service.py`)
5. Service pulls historical analytics (`src/easy_a/analytics/queries.py`), resolved syllabus signals (`src/easy_a/signals/resolver.py`), seat snapshot and modality (`src/easy_a/models/sections.py`)
6. `SectionRanking` pydantic models serialize directly as the response body (`src/easy_a/rankings/models.py`)
7. SPA renders rows in `web/src/components/RankingTable.tsx` with detail expansion in `RankingDetails.tsx`

### Refresh / ingest flow

1. `scripts/refresh_data.py` → `src/easy_a/refresh/cli.py` builds a `RefreshConfig` (`src/easy_a/refresh/models.py`)
2. `refresh_data` runs each stage through `_run_stage`, wrapping failures in `RefreshStageError` (`src/easy_a/refresh/service.py`)
3. Stages: term setup → catalog → schedule → syllabi → grades → quality checks; each stage commits independently
4. Each stage delegates to `client.fetch_*` then `ingest_*_html` for parse-and-upsert
5. `run_quality_checks` records outcomes (`src/easy_a/quality/checks.py`)

### CLI flow

1. `scripts/*.py` are one-line shims that call a `*_main` in the owning package's `cli.py` (e.g. `scripts/rank_course.py` → `easy_a.rankings.cli.course_main`)
2. CLI parses args with `argparse`, opens a session from `get_session_factory()`, calls the same service function the API uses, prints `model_dump(mode="json")`

**State Management:**
- Backend is stateless per request; all state lives in PostgreSQL.
- Frontend state is local `useState` in `web/src/App.tsx` (term, filters, page, expanded CRN) — no global store or data-fetching library.

## Key Abstractions

**SectionRanking (and nested `SeatInfo`, `ModalityInfo`, `RankingSignal`, `RankingProvenance`, `RankingFreshness`):**
- Purpose: The single canonical ranking payload
- Examples: `src/easy_a/rankings/models.py`, mirrored in TypeScript at `web/src/types/rankings.ts`
- Pattern: Pydantic model reused as FastAPI `response_model` and CLI JSON shape

**Ingest result dataclasses:**
- Purpose: Report inserted/updated counts per stage
- Examples: `CatalogIngestResult` (`src/easy_a/catalog/ingest.py`), `ScheduleIngestResult` (`src/easy_a/schedule/ingest.py`), `SyllabusIngestResult`, `GradeIngestResult`
- Pattern: Frozen-style dataclasses returned from `ingest_*` functions

**Domain error types:**
- Purpose: Layer-appropriate failure signalling
- Examples: `RankingResolutionError` (`src/easy_a/rankings/service.py`), `SignalResolutionError` (`src/easy_a/signals/resolver.py`), `TermParseError` (`src/easy_a/common/terms.py`), `ScheduleIngestError` (`src/easy_a/schedule/ingest.py`), `RefreshStageError` (`src/easy_a/refresh/service.py`)
- Pattern: Subclass `ValueError`/`RuntimeError`, translated to HTTP status at the route boundary

**Annotated DI aliases:**
- Purpose: Reusable typed dependencies
- Examples: `DbSession`, `BannerTerm` in `src/easy_a/api/dependencies.py`
- Pattern: `Annotated[T, Depends(...)]`

**Loader injection (frontend):**
- Purpose: Testable data access
- Examples: `AppProps.rankingLoader` / `metadataLoader` defaults in `web/src/App.tsx`
- Pattern: Props-injected async loaders overridden by tests and fixtures

## Entry Points

**FastAPI app:**
- Location: `src/easy_a/api/app.py` (module-level `app = create_app()`)
- Triggers: `uvicorn easy_a.api.app:app`
- Responsibilities: CORS from `EASY_A_ALLOWED_FRONTEND_ORIGINS`, `/health`, router mounting

**SPA:**
- Location: `web/src/main.tsx` mounting `web/src/App.tsx`
- Triggers: `npm run dev` (Vite) or built assets
- Responsibilities: Initial metadata load, term selection, filter/page state

**Scripts:**
- Location: `scripts/*.py` (11 shims)
- Triggers: `uv run python scripts/<name>.py`
- Responsibilities: Delegate to the matching package `cli.py`

**Migrations:**
- Location: `migrations/env.py`, revisions in `migrations/versions/`
- Triggers: `alembic upgrade head`, config at `alembic.ini`

## Architectural Constraints

- **Threading:** Single-process async FastAPI, but all route handlers are synchronous `def` (run in the threadpool) since SQLAlchemy usage is sync. Ingest and CLIs are single-threaded.
- **Global state:** `get_settings()` is `@lru_cache`-memoized (`src/easy_a/config.py`) — env changes require process restart or cache clear. `app` is instantiated at import time in `src/easy_a/api/app.py`. `get_engine()` creates a new engine per call rather than caching one.
- **Sessions:** Services never open their own session; the caller supplies a `Session`. Session lifecycle belongs to `get_db_session` (API), `session_scope` (`src/easy_a/db.py`), or the CLI.
- **Circular imports:** None observed. Dependency direction is strictly api → services → models → db.
- **Database:** PostgreSQL-specific ordering/search behavior is assumed in ranking queries; SQLite is not a supported backend.
- **API is read-only:** CORS allows only `GET`; no write endpoints exist.
- **Term codes:** All term inputs must pass `normalize_banner_term_code` (`src/easy_a/common/terms.py`) before reaching a query.

## Anti-Patterns

### Business logic in route handlers

**What happens:** Query composition and filtering can creep into `src/easy_a/api/routes/rankings.py` alongside HTTP concerns.
**Why it's wrong:** It becomes untestable without an HTTP client and unreachable from the CLIs, breaking API/CLI parity.
**Do this instead:** Put the logic in `src/easy_a/rankings/service.py` and have the route only translate `RankingResolutionError` to a 404.

### Opening a session inside a service function

**What happens:** Calling `get_session_factory()` inside a service instead of accepting a `Session`.
**Why it's wrong:** Breaks transaction composition across refresh stages and forces tests to hit a real engine.
**Do this instead:** Take `session: Session` as the first parameter, as in `rank_section` (`src/easy_a/rankings/service.py`).

### Raising `HTTPException` from domain code

**What happens:** Domain modules import FastAPI to signal errors.
**Why it's wrong:** Couples CLIs and ingest jobs to the web framework.
**Do this instead:** Raise a domain error (`RankingResolutionError`, `SignalResolutionError`) and map it at the route boundary.

### Duplicating the ranking payload shape

**What happens:** New response fields defined ad hoc in a route or hand-typed in the frontend.
**Why it's wrong:** `web/src/types/rankings.ts` silently drifts from `src/easy_a/rankings/models.py`.
**Do this instead:** Extend the pydantic model in `src/easy_a/rankings/models.py`, then mirror it in `web/src/types/rankings.ts` and the fixtures in `web/src/fixtures/rankings.ts`.

### Accepting a raw term string

**What happens:** Passing user-supplied `term` straight into a filter.
**Why it's wrong:** Bypasses the 422 contract and produces silent empty results.
**Do this instead:** Depend on `BannerTerm` (`src/easy_a/api/dependencies.py`) or call `normalize_banner_term_code`.

## Error Handling

**Strategy:** Domain-specific exception classes raised low, translated once at each boundary.

**Patterns:**
- Domain errors subclass `ValueError` (`RankingResolutionError`, `SignalResolutionError`, `TermParseError`, `ScheduleIngestError`).
- Routes catch domain errors and raise `HTTPException` with an explicit status (`404` for unresolved sections, `422` for bad terms).
- A global `SQLAlchemyError` handler in `src/easy_a/api/app.py` returns a generic `{"detail": "Database error."}` 500 so driver internals never leak.
- `get_db_session` rolls back on `SQLAlchemyError` and always closes (`src/easy_a/api/dependencies.py`).
- `session_scope` commits on success, rolls back on any exception (`src/easy_a/db.py`).
- Refresh stages wrap failures in `RefreshStageError` carrying the stage name so partial progress is preserved (`src/easy_a/refresh/service.py`).
- Frontend surfaces load failures as `metadataError` / `rankingsError` state in `web/src/App.tsx`.

## Cross-Cutting Concerns

**Logging:** No logging framework in application code; Alembic/SQLAlchemy logging configured in `alembic.ini`, and SQL echo is toggled by `EASY_A_ECHO_SQL` via `src/easy_a/config.py`. CLIs report via stdout JSON.
**Validation:** Pydantic models plus FastAPI `Query` constraints (`min_length`, `ge`/`le`, `limit` capped at 200) in `src/easy_a/api/routes/rankings.py`; domain normalization in `src/easy_a/common/terms.py`.
**Provenance & freshness:** Every ranking carries `RankingProvenance` and `RankingFreshness` (`src/easy_a/rankings/models.py`, `src/easy_a/signals/provenance.py`) so the UI can attribute each number to a source.
**Authentication:** None — the API is public and read-only.
**Configuration:** Centralized in `src/easy_a/config.py` (`.env` supported, `extra="ignore"`); frontend uses `VITE_API_BASE_URL`.
**Data quality:** `src/easy_a/quality/checks.py` runs as the terminal refresh stage and is independently invocable via `scripts/check_data_quality.py`.

---

*Architecture analysis: 2026-09-05*
