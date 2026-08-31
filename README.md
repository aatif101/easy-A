# Easy-A

Easy-A is a course-intelligence tool for University of South Florida Tampa students.

This repository currently contains the Python data-pipeline foundation. The first sprint is focused on ingestion infrastructure only: PostgreSQL, SQLAlchemy, Alembic, and offline-testable parsing boundaries for future catalog, grade, schedule, and syllabus data.

No frontend, API, authentication, deployment, RateMyProfessors integration, easiness scoring, or LLM syllabus extraction is part of this sprint.

## Development Status

Bootstrap in progress.

## Local Setup

Install `uv`, then create a virtual environment and install dependencies:

```powershell
uv sync
```

Copy `.env.example` to `.env` for local development and adjust values if needed.

## PostgreSQL

Start PostgreSQL 16 locally:

```powershell
docker compose up -d db
```

## Migrations

Run Alembic migrations after the database is healthy:

```powershell
uv run alembic upgrade head
```

## Tests And Quality

```powershell
uv run pytest
uv run ruff check .
uv run mypy src tests scripts
```

## Data Safety

Raw USF InfoCenter exports must not be committed to this repository.
