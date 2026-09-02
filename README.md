# Easy-A

Easy-A is a course-intelligence tool for University of South Florida Tampa students.

V1 will eventually rank course sections using historical grade outcomes, withdrawal
rates, syllabus signals, current seat availability, modality, General Education
requirements, and professor information.

The current Sprint 2 analytics work is still backend-only. It intentionally does
not include a frontend, API, authentication, deployment, RateMyProfessors
integration, LLM scoring, user accounts, or a persisted final rankings table.

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

Raw USF InfoCenter exports must not be committed to this repository.

Do not commit authenticated-session data, credentials, cookies, `.env` files,
internal-use USF data, or real InfoCenter `.xlsx` exports.

Code correctness for parsing and scoring is separate from production data
authorization. Production grade data still depends on the approved
USF/public-records route.
