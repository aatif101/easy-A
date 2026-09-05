# Technology Stack

**Analysis Date:** 2026-09-05

## Languages

**Primary:**
- Python `>=3.12` (target `py312`) - Backend data pipeline, analytics, FastAPI API under `src/easy_a/`
- TypeScript `~5.9.2` - React frontend under `web/src/`

**Secondary:**
- SQL / Alembic migration scripts - `migrations/versions/0001_create_data_core.py`, `migrations/versions/0002_create_section_syllabus_tables.py`
- HTML/CSS (Tailwind directives) - `web/index.html`, `web/src/styles.css`

## Runtime

**Environment:**
- CPython 3.12+ (`pyproject.toml` → `requires-python = ">=3.12"`)
- Node.js (ESM, `"type": "module"` in `web/package.json`); `@types/node` ^24.3.0 implies Node 24-class tooling
- PostgreSQL 16 (container image `postgres:16` in `docker-compose.yml`)

**Package Manager:**
- Backend: `uv` (lockfile `uv.lock` present, ~241 KB); build backend `hatchling`, wheel packages `src/easy_a`
- Frontend: `npm` (lockfile `web/package-lock.json` present)

## Frameworks

**Core:**
- FastAPI `>=0.141.1` - HTTP API, app factory in `src/easy_a/api/app.py`
- Uvicorn `>=0.52.4` - ASGI server
- SQLAlchemy `>=2.0.0` - ORM/Core models in `src/easy_a/models/`
- Alembic `>=1.16.0` - Schema migrations, config `alembic.ini`, scripts `migrations/`
- Pydantic `>=2.10.0` + pydantic-settings `>=2.8.0` - API schemas (`src/easy_a/api/schemas.py`) and settings (`src/easy_a/config.py`)
- React `^19.1.1` / react-dom `^19.1.1` - Frontend UI, entry `web/src/main.tsx`, root `web/src/App.tsx`

**Testing:**
- pytest `>=8.3.0` - Backend tests, `testpaths = ["tests"]` in `pyproject.toml`
- Vitest `^3.2.4` with `jsdom` `^26.1.0` - Frontend tests, config in `web/vite.config.ts`, setup `web/src/test/setup.ts`
- Testing Library: `@testing-library/react` ^16.3.0, `@testing-library/jest-dom` ^6.8.0, `@testing-library/user-event` ^14.6.1

**Build/Dev:**
- Vite `^7.1.3` with `@vitejs/plugin-react` `^5.0.2` - `web/vite.config.ts`
- Tailwind CSS `^3.4.17` + PostCSS `^8.5.6` + autoprefixer `^10.4.21` - `web/tailwind.config.ts`, `web/postcss.config.js`
- Ruff `>=0.9.0` - Lint/format, config in `pyproject.toml` (`line-length = 100`, rules `B,C4,E,F,I,SIM,UP`)
- mypy `>=1.14.0` - Strict typing (`strict = true`, `warn_return_any`, `ignore_missing_imports = false`)
- ESLint `^9.34.0` + typescript-eslint `^8.41.0` - `web/eslint.config.js`
- TypeScript project references - `web/tsconfig.json`, `web/tsconfig.app.json`, `web/tsconfig.node.json`

## Key Dependencies

**Critical:**
- `httpx >=0.28.0` - All outbound HTTP scraping clients (`src/easy_a/catalog/client.py`, `src/easy_a/schedule/client.py`, `src/easy_a/syllabi/client.py`)
- `beautifulsoup4 >=4.13.0` + `lxml >=5.3.0` - HTML parsing of catalog/schedule/syllabus pages
- `pandas >=2.2.0` + `openpyxl >=3.1.0` - XLSX grade-distribution parsing (`src/easy_a/grades/parser.py` uses `pd.read_excel(..., engine="openpyxl")`)
- `psycopg[binary] >=3.2.0` - PostgreSQL driver (`postgresql+psycopg://` URLs)

**Infrastructure:**
- Docker Compose - local Postgres 16 with healthcheck and named volume `easy_a_pgdata` (`docker-compose.yml`)

**Dev type stubs:**
- `pandas-stubs`, `types-beautifulsoup4`, `types-openpyxl` (`pyproject.toml` dev group)

## Configuration

**Environment:**
- Settings class `Settings` in `src/easy_a/config.py`, loaded via `pydantic-settings` from `.env` (`env_file=".env"`, `extra="ignore"`), cached by `get_settings()` (`lru_cache`)
- Backend vars: `DATABASE_URL` (default `postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a`), `EASY_A_ECHO_SQL`, `EASY_A_API_HOST` (default `127.0.0.1`), `EASY_A_API_PORT` (default `8000`), `EASY_A_ALLOWED_FRONTEND_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`)
- Frontend var: `VITE_API_BASE_URL`, read in `web/src/api/rankings.ts`; when unset the app falls back to synthetic fixtures in `web/src/fixtures/`
- `.env.example` present at repo root as the template (contents not read); `.env` is developer-local

**Build:**
- `pyproject.toml` (hatchling wheel target `src/easy_a`)
- `alembic.ini` (`script_location = migrations`, hardcoded local `sqlalchemy.url`)
- `web/vite.config.ts`, `web/tsconfig*.json`, `web/tailwind.config.ts`, `web/postcss.config.js`

## Platform Requirements

**Development:**
- `uv sync` for Python env; `npm install` + `npm run dev` inside `web/`
- Docker (or a local Postgres 16) for the database
- Windows/PowerShell-friendly workflow documented in `README.md`
- CLI entry scripts in `scripts/`: `ingest_catalog.py`, `ingest_grades.py`, `ingest_schedule.py`, `ingest_syllabus.py`, `refresh_data.py`, `rank_course.py`, `rank_section.py`, `analyze_course.py`, `check_data_quality.py`, `extract_section_signals.py`, `resolve_historical_section.py`

**Production:**
- Not applicable — local beta only. `README.md` states no authentication or deployment is in scope; no Dockerfile, CI config, or `.github/` workflows exist.

---

*Stack analysis: 2026-09-05*
