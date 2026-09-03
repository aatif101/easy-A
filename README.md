# Easy-A

Easy-A is a course-intelligence tool for University of South Florida Tampa students.

V1 ranks course sections using historical grade outcomes, withdrawal
rates, syllabus signals, current seat availability, modality, General Education
requirements, and current instructor assignments.

The local beta includes a FastAPI API and React frontend. It intentionally does
not include authentication, deployment, RateMyProfessors integration, LLM scoring,
user accounts, or a persisted final rankings table.

## Development Status

Current branch work contains:

- Python 3.12 project bootstrap managed by `uv`
- PostgreSQL 16 local database via Docker Compose
- SQLAlchemy 2 models and Alembic migration setup
- Banner term normalization helpers
- Public catalog HTML client/parser/ingest layers
- Local XLSX-only grade distribution parser/ingest layers
- Historical grade analytics and a V1 historical easiness score
- Computed section ranking output that joins analytics, current section facts,
  GenEd attributes, seats, modality, and deterministic signals
- Offline tests using synthetic HTML and generated synthetic XLSX fixtures

Developer 1 owns the catalog, historical grades, term normalization, and database
foundation. Developer 2 owns schedule, seats, instructors, and Simple Syllabus.
Those pipelines will eventually join on `(term, CRN)`.

The canonical grade-to-section join is `grade_distributions.term_id = sections.term_id`
and `grade_distributions.crn = sections.crn`. Grade distributions intentionally do
not store `section_id`, because CRNs are scoped by term and section rows may be
re-ingested independently from historical grade rows.

## Local Setup

Install `uv`, then create the virtual environment and install dependencies:

```powershell
uv sync
```

Copy `.env.example` to `.env` for local development and adjust values if needed.

## Frontend

The Sprint 4 frontend is a React, TypeScript, Vite, and Tailwind CSS app under
`web/`. It provides a responsive section-ranking table, server-backed filters,
pagination, and expandable policy and analytics details.

```powershell
cd web
npm install
npm run dev
```

For frontend-only development, leave `VITE_API_BASE_URL` unset. The app then
uses clearly labeled synthetic fixtures covering Staff and named instructors,
course and instructor-course scores, current and historical policy signals,
missing signals and seats, and low-confidence analytics.

To use the real API, create `web/.env.local` and set:

```text
VITE_API_BASE_URL=http://localhost:8000
```

The typed client loads terms, subjects, GenEd attributes, and delivery methods
from the metadata endpoints, then sends selected filters to
`GET /api/v1/rankings/search`. It uses the API's `items`, `total`, `limit`, and
`offset` fields for results and pagination. A configured API failure is shown as
an error and is not silently replaced by mock data. Frontend quality commands are:

```powershell
npm test
npm run lint
npm run typecheck
npm run build
```

This V1 has no authentication, accounts, RateMyProfessors data, LLM features,
or deployment configuration.

## Local Beta Smoke Test

Terminal 1 — start PostgreSQL:

```powershell
docker compose up -d db
```

Terminal 2 — start the API from the repository root:

```powershell
uv run uvicorn easy_a.api.app:app --reload
```

Terminal 3 — start the frontend with the real API configured:

```powershell
cd web
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

Verify that:

- the term selector loads from API metadata;
- searches for `MAC 1105` and `ENC 1101` work;
- the open-seats and GenEd filters work;
- a section detail panel opens;
- historical signals are explicitly labeled;
- unknown instructors, seats, modalities, and signals display safely.

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

Current migration chain:

```text
0001_create_data_core
0002_create_section_syllabus_tables
```

## Real-Data Refresh

USF ODS has approved aggregate USF InfoCenter grade-distribution data for this
project. The approval covers aggregate section outcomes only: Easy-A does not
store student-level records or personally identifiable information. The
application may use derived aggregate statistics after preserving the source
provenance and an explicit Banner term on every imported grade row.

Apply migrations, then use the refresh command to coordinate whichever sources
are available for the target term. This file-backed example is suitable for a
repeatable offline or operator-supplied refresh:

```powershell
uv run python scripts/refresh_data.py `
  --term 202701 `
  --catalog-source file `
  --catalog-edition 2026-2027 `
  --catalog-file C:\local\catalog.html `
  --schedule-source file `
  --schedule-file C:\local\schedule.html `
  --grade-file C:\private\infocenter-grades.xlsx `
  --syllabus-source file `
  --syllabus-file bpvdotxa9=C:\local\syllabus.html
```

Live public catalog and schedule acquisition can be mixed with omitted private
or unavailable inputs:

```powershell
uv run python scripts/refresh_data.py `
  --term 202701 `
  --catalog-source live `
  --catalog-edition 2026-2027 `
  --catalog-url https://cloud.usf.edu/academic-programs/details/prefix/MAC/code/1105 `
  --schedule-source live `
  --schedule-campus T `
  --schedule-subject MAC `
  --schedule-course 1105 `
  --skip-grades `
  --skip-syllabi
```

No data source is mandatory. Omitting a source leaves that stage out, and the
explicit `--skip-catalog`, `--skip-schedule`, `--skip-grades`, and
`--skip-syllabi` switches let an operator temporarily disable configured stages.
Live schedule requests must remain narrow by providing a subject or CRN. Live
syllabus refresh accepts one or more `--syllabus-document` IDs or public URLs;
file mode accepts repeatable `--syllabus-file DOCUMENT_ID=HTML` mappings.

The term is always required, including when a grade file is supplied.
`--grade-file` belongs to exactly the `--term` supplied on that command. The
workbook does not encode a trusted term, and its filename is never used as term
metadata. Operators must import historical grade workbooks with their actual
historical Banner term. For example, never load a Fall 2024 export under Spring
2027 merely because Spring 2027 is the current ranking term. Run that grade-only
historical import with its real term instead:

```powershell
uv run python scripts/refresh_data.py `
  --term 202408 `
  --grade-file C:\private\fall-2024-infocenter-grades.xlsx `
  --skip-catalog `
  --skip-schedule `
  --skip-syllabi
```

Remote acquisition completes before its database transaction begins. Each
ingestion stage has its own transaction: a successful stage commits, while a
failed stage rolls back without undoing previously completed stages. Schedule
reruns update canonical `(term, CRN)` sections while appending seat and
instructor observations, and the final quality report runs only after successful
stage commits.

The refresh summary reports the target term, distinct courses represented by
target-term sections, canonical sections, instructor observations and seat
snapshots added by this run, stored target-term grade rows and syllabi, and
quality error and warning counts. Exit status is `0` when the refresh and quality
checks succeed, `1` when ingestion succeeds but quality errors are present, and
`2` when an ingestion stage fails.

## Data Quality

Run the quality checks independently for any stored term:

```powershell
uv run python scripts/check_data_quality.py --term 202701
uv run python scripts/check_data_quality.py --term 202701 --stale-after-days 14 --json
```

The report checks duplicate `(term, CRN)` sections, grade bucket totals, orphan
grade and instructor rows, impossible seat values, unknown delivery methods,
ambiguous current instructors, stale schedule observations, missing historical
analytics coverage, and low-confidence rankings. Staleness is configurable and
is reported as a warning rather than treated as invalid data. Human-readable
output looks like:

```text
Term: 202701
Sections: 46
Errors: 0
Warnings: 8
Info: 3

WARN ambiguous_instructor CRN 12345 [section:17]: Latest instructor observation contains multiple names: Instructor A / Instructor B
WARN low_confidence_ranking CRN 19410 [section:21]: Computed historical ranking confidence is low.
INFO no_historical_analytics CRN 13173 [section:19]: Section has no historical grade analytics coverage.
```

The quality command exits nonzero only when at least one error-level finding is
present. Warnings and informational coverage gaps do not fail the command.

## Narrow public-source commands

```powershell
uv run python scripts/ingest_schedule.py --term 202701 --campus T --subject MAC --course 1105
uv run python scripts/resolve_historical_section.py --term 202408 --crn 89033 --subject MAC --course 1105
uv run python scripts/ingest_syllabus.py --document-id bpvdotxa9
uv run python scripts/analyze_course.py --term 202701 --subject MAC --course 1105
uv run python scripts/rank_section.py --term 202701 --crn 19410
uv run python scripts/rank_course.py --term 202701 --subject MAC --course 1105
```

Schedule searches use the public form POST, and syllabus ingestion accepts one known
document ID or URL at a time. Neither command is a broad crawler.

## Deterministic Syllabus Signals

Sprint 2 extracts a narrow set of human-readable policy and course-format signals
from already-stored syllabus text and schedule section notes. Extraction is
deterministic and rules-based; it does not call an LLM or any model API.

Every returned signal includes its type, normalized value, rule confidence, source
kind and identifier, source term, extraction time, and a short exact evidence window
of at most 240 characters. Categories without supported evidence are omitted rather
than filled with a fabricated value.

For a current section, source precedence is:

1. current-term syllabus;
2. current schedule section note, if it contains a supported signal;
3. historical syllabus for the same course and conservatively resolved instructor;
4. latest historical syllabus for the same course; or
5. unavailable.

Historical signals are explicitly labeled as historical and retain their source
term. They are never silently combined with current statements. Instructor matching
accepts exact normalized names, or a unique first-initial plus exact-surname match
within the course history. Current instructors come only from the latest
`observed_at` state; `Staff`, multiple conflicting instructors in that latest state,
and ambiguous abbreviations do not receive an instructor match.

Extract signals for one section already present in the database:

```powershell
uv run python scripts/extract_section_signals.py --term 202701 --crn 19410
```

Known limitations: rules cover only explicit phrases in the current rule set;
unusual wording remains unknown, confidence scores describe rule specificity rather
than calibrated probability, and the latest same-course syllabus is only a
historical reference rather than evidence of current policy. Signal objects are
computed at request time in Sprint 2; no persistent `syllabus_signals` or
`section_rankings` table is created.

## Section Ranking Integration

Sprint 2 integrates the merged historical analytics and deterministic signal
systems into a computed, typed section-level ranking output in
`easy_a.rankings`. It is still backend-only and intentionally does not add a
frontend, FastAPI API, RateMyProfessors integration, LLM scoring, user accounts,
or deployment.

For one stored current section, the ranking service resolves the row by
`(term, CRN)` and joins:

- current `terms`, `sections`, and exact `courses` data;
- the latest observed `section_instructors` state;
- delivery method and current seat fields, preferring the latest
  `seat_snapshots` row when one exists;
- stored `course_attributes` GenEd code-label pairs;
- historical easiness analytics from `grade_distributions`; and
- resolved deterministic syllabus or section-note signals.

The CLI prints JSON so downstream consumers can see the full provenance contract
without an API:

```powershell
uv run python scripts/rank_section.py --term 202701 --crn 19410
uv run python scripts/rank_course.py --term 202701 --subject MAC --course 1105
```

## FastAPI API

Sprint 3 exposes the computed ranking service through a thin FastAPI app. It does
not add authentication, accounts, deployment infrastructure, RateMyProfessors,
LLM scoring, or a persisted rankings table.

Run the API locally after syncing dependencies and applying migrations:

```powershell
uv run uvicorn easy_a.api.app:app --reload
```

The app reads `DATABASE_URL` for the SQLAlchemy connection. Development CORS is
restricted to local frontend origins by default:
`http://localhost:5173,http://127.0.0.1:5173`. Override it with a comma-separated
`EASY_A_ALLOWED_FRONTEND_ORIGINS` value when needed.

Endpoints:

- `GET /health` returns `{"status":"ok"}`.
- `GET /api/v1/rankings/section?term=202701&crn=19410` ranks one stored section.
- `GET /api/v1/rankings/course?term=202701&subject=MAC&course_number=1105`
  ranks all stored sections for one course.
- `GET /api/v1/rankings/search?term=202701&gened_code=SMEL&seats_open=true`
  searches stored current sections, computes rankings for candidates, applies
  filters, and returns `items`, `total`, `limit`, and `offset`.
- `GET /api/v1/metadata/terms`
- `GET /api/v1/metadata/subjects`
- `GET /api/v1/metadata/gened-attributes`
- `GET /api/v1/metadata/delivery-methods`

Sample requests:

```powershell
curl "http://127.0.0.1:8000/health"
curl "http://127.0.0.1:8000/api/v1/rankings/section?term=202701&crn=19410"
curl "http://127.0.0.1:8000/api/v1/rankings/course?term=202701&subject=MAC&course_number=1105"
curl "http://127.0.0.1:8000/api/v1/rankings/search?term=202701&sort=easiness_desc&limit=25"
curl "http://127.0.0.1:8000/api/v1/metadata/gened-attributes"
```

Search filters are intentionally V1-simple: candidate sections come from the
canonical term/course/section tables, the existing ranking service computes each
candidate, and derived filters such as open seats, minimum easiness, and
confidence are applied to those computed outputs. Default `limit` is `50`; max
`limit` is `200`. Supported sort values are `easiness_desc`, `easiness_asc`,
`withdrawal_asc`, `seats_desc`, and `course`.

The top-level score fields are historical-only: `easiness_score`,
`smoothed_withdrawal_rate`, `confidence_label`, `effective_n`, and
`score_source` come from historical grade outcomes and the analytics fallback
rules. Current seats, delivery method, section notes, syllabus signals, GenEd
attributes, and future professor/RMP data do not influence easiness scoring.

Each output keeps missing or uncertain data explicit rather than filling guesses:
empty signal resolution is reported as `unavailable`, historical syllabus signals
are marked `historical` with their source term, seat data says whether it came
from a seat snapshot or canonical section fields, and GenEd attributes remain an
empty list with unavailable provenance when no course attributes are stored.

The ranking output is computed on demand. No `section_rankings` table or Alembic
migration is added in Sprint 2 because the existing source tables already hold
the canonical facts. If a future workflow needs cached, versioned ranking
artifacts, that should be a derived table chained after
`0002_create_section_syllabus_tables`; live seats, modality, and other source
facts should remain in their source tables.

API ranking caveats match the computed service caveats: easiness uses historical
grade outcomes and withdrawal rates only. Current seats, delivery method, GenEd
attributes, syllabus or section-note signals, and future professor/RMP fields do
not affect the score. Historical signals are labeled historical and should not be
presented as current policy.

USF ODS approved use of aggregate InfoCenter grade-distribution data for this
project. This authorization does not imply USF endorsement of Easy-A.
Production-quality rankings still depend on a complete, correctly provenanced set
of approved aggregate rows. Local development databases may be partial, synthetic,
or missing historical coverage, so low-confidence and fallback scores should be
treated as exploratory rather than definitive.

## Tests And Quality

```powershell
uv run pytest
uv run ruff check .
uv run mypy src migrations scripts tests
```

## Grade Distribution Ingestion

USF InfoCenter grade exports are parsed from local `.xlsx` files only. The
workbook does not encode a trusted academic term, so `--term` is required and
filenames are never used to infer term metadata. The file must be imported under
the actual Banner term represented by its rows, even when a different term is
currently being ranked.

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

## Historical Analytics

The analytics package computes historical outcome statistics from completed grade
and withdrawal buckets already in the database. It does not create the final
`section_rankings` table.

The V1 grade favorability metric uses only completed letter grades:

```text
(4*A + 3*B + 2*C + 1*D + 0*F) / (4 * (A + B + C + D + F))
```

USF grade distribution exports provide only coarse `A`, `B`, `C`, `D`, and `F`
buckets. They do not include plus/minus grades, so this metric stays a normalized
favorability score rather than a transcript-style average.

Withdrawal rate is computed separately as:

```text
W / Total Grades
```

when `Total Grades` is greater than zero. `I`, `S`, `U`, `W`, and `Other` are not
included in the grade-favorability denominator.

The historical easiness score is a transparent V1 composite:

```text
10 * (0.80 * smoothed_grade_favorability + 0.20 * (1 - smoothed_withdrawal_rate))
```

The result is clamped to `0` through `10`. It uses historical academic outcomes
only. Syllabus signals, RateMyProfessors, seat availability, modality, and similar
non-grade inputs do not affect this score.

Small samples are regularized with a simple empirical-Bayes shrinkage:

```text
weight = n / (n + prior_strength)
smoothed = weight * observed + (1 - weight) * prior
```

The default prior strengths are V1 regularization constants, not statistically
optimal claims. Instructor-course history uses course-level history as its prior.
Course-level history can fall back to subject-level or global history.

Each result includes a confidence label based on effective sample size:

```text
low: effective_n < 60
medium: 60 <= effective_n < 180
high: effective_n >= 180
```

One-term histories are treated more conservatively. Confidence is a rough data
coverage signal, not statistical certainty.

Example analytics command:

```powershell
uv run python scripts/analyze_course.py `
  --term 202701 `
  --subject MAC `
  --course 1105
```

Output includes current section CRN, instructor, historical easiness, historical
withdrawal rate, confidence, effective sample size, and score source.

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

USF ODS approval permits aggregate grade-distribution data and derived aggregate
statistics to be used by Easy-A. It does not permit storing student-level data or
PII. Every ingested grade row must retain its explicit term and source provenance.

Raw source exports must never be committed to GitHub. The repository ignores
`.xlsx`, `.xls`, `data/`, and `research/raw/`; tests generate synthetic workbooks
only in temporary directories. Do not commit authenticated-session data,
credentials, cookies, `.env` files, internal-use USF data, or real InfoCenter
exports.

Code correctness for parsing and scoring remains separate from source handling:
operators are responsible for keeping raw authenticated exports outside the
repository while the application stores only approved aggregate records and
their derived statistics. USF ODS approved use of aggregate InfoCenter
grade-distribution data for this project; this does not imply USF endorsement of
Easy-A, and the repository's data safety restrictions still apply.
