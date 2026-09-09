# Codebase Structure

**Analysis Date:** 2026-09-05

## Directory Layout

```
easy-a/
├── src/easy_a/               # Python package (all backend logic)
│   ├── api/                  # FastAPI HTTP layer
│   │   └── routes/           # Routers: rankings, metadata
│   ├── analytics/            # Grade aggregation, easiness scoring, confidence
│   ├── catalog/              # USF catalog ingest pipeline
│   ├── common/               # Shared helpers: terms, instructors, lookups
│   ├── grades/               # Grade-distribution file ingest
│   ├── models/               # SQLAlchemy ORM models
│   ├── quality/              # Data-quality checks
│   ├── rankings/             # Ranking composition service + DTOs
│   ├── refresh/              # Multi-stage refresh orchestration
│   ├── schedule/             # Section/schedule ingest + resolver
│   ├── signals/              # Deterministic syllabus signal extraction
│   ├── syllabi/              # Syllabus fetch/parse/ingest
│   ├── config.py             # pydantic-settings Settings
│   └── db.py                 # Base, engine, session factory, session_scope
├── web/                      # React 19 + Vite + Tailwind SPA
│   └── src/
│       ├── api/              # HTTP client + mock fallback
│       ├── components/       # Presentational React components
│       ├── fixtures/         # Synthetic ranking data for mock mode
│       ├── test/             # Vitest setup
│       ├── types/            # TS mirrors of backend DTOs
│       └── utils/            # Filter parsing/state helpers
├── tests/                    # pytest suite mirroring src/easy_a packages
├── scripts/                  # One-line CLI shims into package cli.py modules
├── migrations/               # Alembic env + versions
├── docs/                     # Investigation notes
├── .planning/                # GSD planning artifacts
├── alembic.ini               # Migration config
├── docker-compose.yml        # Local PostgreSQL 16
├── pyproject.toml            # Deps, ruff, mypy, pytest config
└── uv.lock                   # uv dependency lockfile
```

## Directory Purposes

**`src/easy_a/api/`:**
- Purpose: Thin read-only HTTP surface over ranking services
- Contains: App factory, routers, DI aliases, response schemas
- Key files: `src/easy_a/api/app.py`, `src/easy_a/api/dependencies.py`, `src/easy_a/api/schemas.py`, `src/easy_a/api/routes/rankings.py`, `src/easy_a/api/routes/metadata.py`

**`src/easy_a/models/`:**
- Purpose: Declarative ORM schema
- Contains: `Term`, `Course`, `CourseAttribute`, `GradeDistribution`, `IngestRun` in `src/easy_a/models/core.py`; `Section`, `SectionInstructor`, `SeatSnapshot`, `Syllabus` in `src/easy_a/models/sections.py`
- Key files: `src/easy_a/models/__init__.py` re-exports all models

**Ingest packages (`catalog/`, `schedule/`, `syllabi/`, `grades/`):**
- Purpose: One package per external data source
- Contains: `client.py` (fetch), `parser.py` (HTML/XLSX → dataclasses), `ingest.py` (upsert), `cli.py` (entry)
- Key files: `src/easy_a/catalog/ingest.py`, `src/easy_a/schedule/ingest.py`, `src/easy_a/schedule/normalize.py`, `src/easy_a/schedule/resolver.py`, `src/easy_a/syllabi/ingest.py`, `src/easy_a/grades/parser.py`

**`src/easy_a/rankings/`:**
- Purpose: Compose the `SectionRanking` payload consumed by API, CLI, and web
- Key files: `src/easy_a/rankings/service.py`, `src/easy_a/rankings/models.py`, `src/easy_a/rankings/cli.py`

**`src/easy_a/analytics/`:**
- Purpose: Historical grade statistics and easiness scoring
- Key files: `src/easy_a/analytics/queries.py`, `scoring.py`, `confidence.py`, `grades.py`

**`src/easy_a/signals/`:**
- Purpose: Deterministic rule-based syllabus signal extraction with provenance
- Key files: `src/easy_a/signals/rules.py`, `extract.py`, `resolver.py`, `provenance.py`, `models.py`

**`src/easy_a/refresh/`:**
- Purpose: Stage-by-stage orchestration of every ingest source plus quality checks
- Key files: `src/easy_a/refresh/service.py`, `src/easy_a/refresh/models.py`

**`src/easy_a/common/`:**
- Purpose: Cross-domain helpers used by more than one package
- Key files: `src/easy_a/common/terms.py` (Banner term normalization), `instructors.py`, `lookups.py`

**`web/src/`:**
- Purpose: Ranking browser SPA
- Key files: `web/src/App.tsx`, `web/src/api/rankings.ts`, `web/src/types/rankings.ts`, `web/src/utils/rankings.ts`, `web/src/fixtures/rankings.ts`

**`tests/`:**
- Purpose: pytest suite mirroring the `src/easy_a` package tree one directory per domain
- Key files: `tests/conftest.py`, `tests/test_models.py`, `tests/test_grade_schedule_integration.py`, `tests/test_fixture_safety.py`

**`scripts/`:**
- Purpose: Discoverable command entry points; each file is a shim raising `SystemExit(<pkg>.cli.<x>_main())`
- Key files: `scripts/refresh_data.py`, `scripts/rank_course.py`, `scripts/rank_section.py`, `scripts/check_data_quality.py`

## Key File Locations

**Entry Points:**
- `src/easy_a/api/app.py`: FastAPI `app` object (`uvicorn easy_a.api.app:app`)
- `web/src/main.tsx`: React root mount
- `scripts/*.py`: CLI shims
- `migrations/env.py`: Alembic runtime

**Configuration:**
- `src/easy_a/config.py`: `Settings` (DATABASE_URL, EASY_A_API_HOST/PORT, EASY_A_ECHO_SQL, EASY_A_ALLOWED_FRONTEND_ORIGINS)
- `.env.example`: Template for local env (an `.env` file is loaded if present)
- `pyproject.toml`: ruff (line-length 100, py312), mypy strict, pytest `testpaths`
- `alembic.ini`, `docker-compose.yml`
- `web/vite.config.ts`, `web/tailwind.config.ts`, `web/tsconfig*.json`, `web/eslint.config.js`, `web/postcss.config.js`

**Core Logic:**
- `src/easy_a/rankings/service.py`: Ranking composition
- `src/easy_a/analytics/queries.py`: Historical outcome aggregation with fallbacks
- `src/easy_a/refresh/service.py`: Refresh staging
- `src/easy_a/db.py`: Session and metadata naming convention

**Testing:**
- `tests/` (pytest), `web/src/**/*.test.ts(x)` (vitest), setup at `web/src/test/setup.ts`

## Naming Conventions

**Python files:**
- `snake_case.py`; role-based names repeated across domains: `client.py`, `parser.py`, `ingest.py`, `cli.py`, `models.py`, `service.py`
- Private helpers prefixed with `_` (e.g. `_upsert_sections` in `src/easy_a/schedule/ingest.py`)
- CLI entry functions named `<verb>_main` (e.g. `course_main`, `section_main` in `src/easy_a/rankings/cli.py`)
- Ingest functions named `ingest_<source>_html` / `ingest_<source>_file`

**Python directories:**
- `src/easy_a/<domain>/` — one lowercase noun per domain, each with `__init__.py` re-exporting the public surface

**Migrations:**
- `migrations/versions/NNNN_snake_case_description.py` (e.g. `0001_create_data_core.py`)

**Tests:**
- `tests/<domain>/test_<module>.py`, mirroring `src/easy_a/<domain>/<module>.py`

**Web files:**
- Components: `PascalCase.tsx` in `web/src/components/` with a matching named export
- Non-component modules: `camelCase.ts` (`web/src/api/rankings.ts`, `web/src/utils/rankings.ts`)
- Tests: co-located `<name>.test.ts(x)`
- API field names in TS types use backend `snake_case` verbatim (`gened_attributes`, `delivery_method`); locally derived values use `camelCase`

**Scripts:**
- `scripts/<verb>_<noun>.py` (e.g. `ingest_schedule.py`, `resolve_historical_section.py`)

## Where to Add New Code

**New data source (ingest pipeline):**
- Create `src/easy_a/<source>/` with `client.py`, `parser.py`, `ingest.py`, `cli.py`, `__init__.py`
- Add ORM tables to `src/easy_a/models/core.py` or `sections.py` and re-export from `src/easy_a/models/__init__.py`
- Add an Alembic revision under `migrations/versions/`
- Wire a new stage into `src/easy_a/refresh/service.py` and its input model in `src/easy_a/refresh/models.py`
- Add `scripts/ingest_<source>.py` shim
- Tests in `tests/<source>/`

**New API endpoint:**
- Router in `src/easy_a/api/routes/` (or extend `rankings.py`), then `include_router` in `src/easy_a/api/app.py`
- Response/request models in `src/easy_a/api/schemas.py` or `src/easy_a/rankings/models.py`
- Business logic in the relevant `service.py`, never in the route
- Tests in `tests/api/`

**New ranking factor / signal:**
- Rule in `src/easy_a/signals/rules.py`, surfaced through `src/easy_a/signals/extract.py`
- Scoring change in `src/easy_a/analytics/scoring.py`
- Payload field in `src/easy_a/rankings/models.py`, mirrored in `web/src/types/rankings.ts` and `web/src/fixtures/rankings.ts`

**New UI feature:**
- Component in `web/src/components/`, wired from `web/src/App.tsx`
- Pure filter/derivation helpers in `web/src/utils/rankings.ts`
- Fetch logic in `web/src/api/rankings.ts` (keep the mock branch in sync)
- Test alongside as `<Name>.test.tsx`

**Shared helper used by 2+ domains:**
- `src/easy_a/common/` with tests in `tests/common/`

**New CLI command:**
- Add a `*_main` in the owning package's `cli.py`, then a one-line `scripts/<name>.py` shim

## Special Directories

**`migrations/versions/`:**
- Purpose: Alembic revision history (`0001_create_data_core.py`, `0002_create_section_syllabus_tables.py`)
- Generated: Semi (autogenerate then hand-edited)
- Committed: Yes

**`web/src/fixtures/`:**
- Purpose: Synthetic ranking data powering mock mode when `VITE_API_BASE_URL` is unset
- Generated: No
- Committed: Yes — guarded by `tests/test_fixture_safety.py`

**`tests/fixtures/`:**
- Purpose: Sample HTML/data inputs for parser and ingest tests
- Generated: No
- Committed: Yes

**`docs/`:**
- Purpose: Dated investigation notes (`docs/live-source-drift-2026-09-01.md`)
- Committed: Yes

**`.planning/`:**
- Purpose: GSD planning and codebase-map artifacts
- Generated: Yes (by GSD commands)
- Committed: Yes

**`web/node_modules/`, `.venv/`, `web/dist/`:**
- Generated: Yes
- Committed: No (see `.gitignore`)

---

*Structure analysis: 2026-09-05*
