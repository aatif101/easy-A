# Easy-A

Easy-A is a course-intelligence tool for University of South Florida Tampa students.

V1 will eventually rank course sections using historical grade outcomes, withdrawal
rates, syllabus signals, current seat availability, modality, General Education
requirements, and professor information.

This sprint is data-pipeline only. It intentionally does not include a frontend,
API, authentication, deployment, RateMyProfessors integration, easiness scoring, or
LLM syllabus extraction.

## Development Status

Current branch work contains:

- Python 3.12 project bootstrap managed by `uv`
- PostgreSQL 16 local database via Docker Compose
- SQLAlchemy 2 models and Alembic migration setup
- Banner term normalization helpers
- Public catalog HTML client/parser/ingest layers
- Local XLSX-only grade distribution parser/ingest layers
- Offline tests using synthetic HTML and generated synthetic XLSX fixtures

Developer 1 owns the catalog, historical grades, term normalization, and database
foundation. Developer 2 owns schedule, seats, instructors, and Simple Syllabus.
Those pipelines will eventually join on `(term, CRN)`.

## Local Setup

Install `uv`, then create the virtual environment and install dependencies:

```powershell
uv sync
```

Copy `.env.example` to `.env` for local development and adjust values if needed.

## PostgreSQL

Start PostgreSQL 16 locally:

```powershell
docker compose up -d db
```

The default local connection string is:

```text
postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a
```

## Migrations

Run Alembic migrations after the database is healthy:

```powershell
uv run alembic upgrade head
```

To create a new migration after model changes:

```powershell
uv run alembic revision --autogenerate -m "describe change"
```

## Narrow public-source commands

```powershell
uv run python scripts/ingest_schedule.py --term 202701 --campus T --subject MAC --course 1105
uv run python scripts/resolve_historical_section.py --term 202408 --crn 89033 --subject MAC --course 1105
uv run python scripts/ingest_syllabus.py --document-id bpvdotxa9
```

Schedule searches use the public form POST, and syllabus ingestion accepts one known
document ID or URL at a time. Neither command is a broad crawler.

## Tests And Quality

```powershell
uv run pytest
uv run ruff check .
uv run mypy src tests scripts
```

## Grade Distribution Ingestion

USF InfoCenter grade exports are parsed from local `.xlsx` files only. The workbook
does not contain the academic term, so `--term` is required and filenames are never
used to infer term metadata.

```powershell
uv run python scripts/ingest_grades.py `
  --term 202408 `
  --file C:\local\path\sample.xlsx
```

The parser expects the structural columns:

```text
course, A, % A, B, % B, C, % C, D, % D, F, % F, I, % I,
S, % S, U, % U, W, % W, O, % O, Total Grades
```

It ignores hierarchy and total rows that do not match a section identifier like:

```text
MAC-1105 -001-C (89033)
```

For each section, `A + B + C + D + F + I + S + U + W + O` must equal
`Total Grades`; invalid rows fail ingestion and are logged in `ingest_runs`.
Percentage columns are informational source data and are not stored canonically.

## Catalog Ingestion

Catalog acquisition and parsing are separate. The parser can be tested offline with
HTML fixtures, while the client fetches public catalog/course inventory pages.

```powershell
uv run python scripts/ingest_catalog.py `
  --catalog-edition 2026-2027 `
  --url https://cloud.usf.edu/academic-programs/details/prefix/ENC/code/1101
```

You can also ingest a local HTML fixture:

```powershell
uv run python scripts/ingest_catalog.py `
  --catalog-edition 2026-2027 `
  --file tests\fixtures\catalog\enc_1101.html
```

Course attributes are stored as raw code-label pairs. Attribute codes are not
globally unique because the same code can appear with different labels.

## Data Safety

Raw USF InfoCenter exports must not be committed to this repository.

Do not commit authenticated-session data, credentials, cookies, `.env` files,
internal-use USF data, or real InfoCenter `.xlsx` exports.
