# External Integrations

**Analysis Date:** 2026-09-05

## APIs & External Services

All external integrations are unauthenticated public HTTP scrapes of USF sources. No API keys or tokens exist anywhere in the codebase.

**USF Public Course Catalog:**
- Fetches catalog HTML for course descriptions, prerequisites, and GenEd attributes
  - Client: `src/easy_a/catalog/client.py` (`fetch_catalog_html(url, timeout_seconds=30.0)`, plain `httpx.Client`, `follow_redirects=True`)
  - Parser/ingest: `src/easy_a/catalog/` (invoked via `scripts/ingest_catalog.py` → `easy_a.catalog.cli:main`)
  - Auth: none — URL is supplied per invocation
  - User-Agent: `Easy-A data pipeline (https://github.com/aatif101/easy-A)`

**USF Staff Schedule Search (Banner-backed):**
- Current-term sections, seats, instructors, modality
  - Base URL: `https://usfweb.usf.edu`, path `/DSS/StaffScheduleSearch/StaffSearch/Results` (POST form search)
  - Client: `src/easy_a/schedule/client.py` (`StaffScheduleClient`, `ScheduleSearchQuery` requires `--crn` or `--subject`)
  - Term codes normalized by `src/easy_a/common/terms.py` (`normalize_banner_term_code`)
  - Auth: none

**Simple Syllabus (USF tenant):**
- Syllabus documents parsed for grading policy signals
  - Base URL: `https://usf.simplesyllabus.com`, endpoints `/api2/doc-html/{document_id}` (fetch) and `/en-US/doc/{id}?mode=view` (human link)
  - Client: `src/easy_a/syllabi/client.py` (`SimpleSyllabusClient`, document IDs validated against `^[A-Za-z0-9_-]+$`)
  - Auth: none

**USF InfoCenter grade distributions:**
- Not an HTTP integration — XLSX files are downloaded manually and parsed offline
  - Parser: `src/easy_a/grades/parser.py` (`pandas.read_excel(..., engine="openpyxl")`)
  - Ingest source tag: `usf_infocenter_grade_distribution_xlsx` in `src/easy_a/grades/ingest.py`
  - Entry point: `scripts/ingest_grades.py`

**Known drift:** live-source behavior changes are tracked in `docs/live-source-drift-2026-09-01.md`.

## Data Storage

**Databases:**
- PostgreSQL 16 (local, Docker Compose service `db` in `docker-compose.yml`; DB/user/password all `easy_a`, port 5432, volume `easy_a_pgdata`)
  - Connection: `DATABASE_URL` env var, default `postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a` (`src/easy_a/config.py`)
  - Client: SQLAlchemy 2 engine factory in `src/easy_a/db.py` (`get_engine`), models in `src/easy_a/models/`
  - Migrations: Alembic, `alembic.ini` + `migrations/versions/0001_create_data_core.py`, `migrations/versions/0002_create_section_syllabus_tables.py`

**File Storage:**
- Local filesystem only — grade XLSX inputs are read from paths passed to `scripts/ingest_grades.py`

**Caching:**
- None. Only in-process `lru_cache` on `get_settings()` in `src/easy_a/config.py`.

## Authentication & Identity

**Auth Provider:**
- None. `README.md` explicitly scopes the local beta as having no authentication and no user accounts. The API in `src/easy_a/api/app.py` exposes read-only `GET` routes with `allow_credentials=False`.

## Monitoring & Observability

**Error Tracking:**
- None. A single SQLAlchemy exception handler in `src/easy_a/api/app.py` converts `SQLAlchemyError` into a generic 500 `{"detail": "Database error."}`.

**Logs:**
- Alembic/SQLAlchemy logging configured in `alembic.ini` (console handler on stderr; root WARNING, alembic INFO). Optional SQL echo via `EASY_A_ECHO_SQL`.

## CI/CD & Deployment

**Hosting:**
- Not applicable — local development only. No Dockerfile for the app, no deployment manifests.

**CI Pipeline:**
- None. No `.github/` directory or other CI configuration exists.

## Environment Configuration

**Required env vars:**
- `DATABASE_URL` - Postgres connection string
- `EASY_A_ALLOWED_FRONTEND_ORIGINS` - CORS allowlist consumed by `Settings.allowed_frontend_origin_list()`
- `EASY_A_API_HOST`, `EASY_A_API_PORT` - Uvicorn bind settings
- `EASY_A_ECHO_SQL` - SQL echo toggle
- `VITE_API_BASE_URL` - Frontend API base (`web/src/api/rankings.ts`); unset → synthetic fixture mode

**Secrets location:**
- Local `.env` file (git-ignored) generated from `.env.example`. No secret manager, and no third-party credentials are needed since all sources are public.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None. All external traffic is outbound request/response scraping via `httpx`.

## API Surface (internal, frontend → backend)

- FastAPI app: `src/easy_a/api/app.py` (title "Easy-A API", version 0.1.0)
- Routes: `src/easy_a/api/routes/rankings.py`, `src/easy_a/api/routes/metadata.py`, plus `GET /health`
- Frontend client: `web/src/api/rankings.ts` (fetch against `VITE_API_BASE_URL`, trailing slash trimmed), tests in `web/src/api/rankings.test.ts`

---

*Integration audit: 2026-09-05*
