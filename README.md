# Easy A

**Find your next USF class.**

Search courses and instructors, compare historical grade distributions, and check the latest observed seats for USF Tampa.

**[Try it at easya.fyi →](https://easya.fyi)**

![React](https://img.shields.io/badge/React-18232F?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-18232F?style=flat-square&logo=typescript&logoColor=3178C6)
![FastAPI](https://img.shields.io/badge/FastAPI-18232F?style=flat-square&logo=fastapi&logoColor=009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18232F?style=flat-square&logo=postgresql&logoColor=4169E1)

## What it does

- Search by course code, CRN, subject, number, title, or instructor.
- Compare an instructor's past grades **in that course**, with sample sizes and covered terms.
- Browse GenEd requirements and see seat counts with their last-checked time.
- Open Rate My Professors links and copy a CRN for registration in OASIS.

## How it's built

A React/TypeScript frontend talks to a FastAPI backend backed by PostgreSQL on Supabase. A background worker refreshes USF schedule data; historical grade imports retain their source and academic term. The API, worker, and frontend are hosted on Render.

Grade history comes from USF InfoCenter reports. Missing history stays unavailable, and small samples are labeled. Past grades are not a prediction of your grade; confirm seats in OASIS. RMP links are references only—ratings and reviews are not imported or used in scoring.

<details>
<summary><strong>Run locally</strong></summary>

### Frontend demo

Requires Node.js and npm. From the repository root:

```sh
cd web
npm ci
```

Copy `web/.env.example` to `web/.env.local`, keeping `VITE_USE_MOCK_DATA=true`, then run `npm run dev`. This mode uses labeled synthetic fixtures and needs no database.

### Full application

Requires Python 3.12+, uv, Node.js, and Docker.

1. Run `uv sync` from the repository root.
2. Copy `.env.example` to `.env`. The included connection string targets local Docker PostgreSQL.
3. Start the database, apply migrations, and start the API:

```sh
docker compose up -d db
uv run alembic upgrade head
uv run uvicorn easy_a.api.app:app --reload
```

4. Set these values in `web/.env.local`:

```dotenv
VITE_USE_MOCK_DATA=false
VITE_API_BASE_URL=http://localhost:8000
```

5. In a second terminal, run `npm ci` and `npm run dev` from `web/`.

A fresh database is empty. Schedule and approved aggregate grade data must be imported separately; production source exports are not included. See the [operations runbook](docs/runbooks/hosted-beta-operations.md) and [ingestion scripts](scripts/).

### Checks

From the repository root:

```sh
uv run pytest
uv run ruff check .
uv run mypy src migrations scripts tests
```

From `web/`:

```sh
npm test
npm run lint
npm run typecheck
npm run build
```

PostgreSQL integration tests require a separate test database via `EASY_A_TEST_POSTGRES_URL`.

</details>

<details>
<summary><strong>Grade methodology</strong></summary>

Displayed A share is `A / (A + B + C + D + F)`, accompanied by the observed grade count. It is distinct from the backend's historical easiness score.

The backend combines normalized grade favorability (80%) and the complement of withdrawal rate (20%), using Bayesian shrinkage for small samples. Seats, GenEd requirements, modality, syllabus signals, and RMP links do not affect that score.

### Instructor-course history

Instructor scoring requires at least 30 effective graded students and a usable instructor assignment in the same course. Grade favorability is shrunk toward the course mean with a prior strength of 30; course-level grade priors and withdrawal priors remain 60.

Laboratory sections use course-level history and are excluded from instructor-level statistics. Staff and blank names are never assigned to a named instructor. Names are matched within a course, not pooled across courses. Single-term histories are labeled without an extra scoring penalty.

When instructor evidence is insufficient, scoring falls back through course, subject, and global history. A subject or global fallback is never presented as observed course history. Confidence labels describe data coverage, not certainty.

Implementation: [analytics](src/easy_a/analytics/) · [rankings](src/easy_a/rankings/)

</details>

<details>
<summary><strong>Data and development notes</strong></summary>

Only approved aggregate grade data and its provenance belong in the application. Never commit raw grade exports, student-level records, credentials, or `.env` files. Tests use synthetic fixtures.

- [Hosted operations and recovery](docs/runbooks/hosted-beta-operations.md)
- [Agent and contributor instructions](AGENTS.md)
- [Project state](.planning/STATE.md)
- [Earlier technical notes](https://github.com/aatif101/easy-A/blob/a00221e549fb056b88b352ce0b08969a403d5a05/README.md) — historical reference; some sections are superseded.

</details>

---

Independent student project. Not affiliated with or endorsed by the University of South Florida.
