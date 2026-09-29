# Phase 9: Hosted Beta - Pattern Map

**Mapped:** 2026-09-29
**Files analyzed:** 26 new/modified
**Analogs found:** 21 / 26 (all analog paths verified git-tracked via `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `src/easy_a/sync/__main__.py`, `cli.py` | CLI entry | batch | `src/easy_a/schedule/cli.py` | exact |
| `src/easy_a/sync/runner.py` | service (loop) | event-driven | none (see No Analog) | none |
| `src/easy_a/sync/windows.py` | config/utility | transform | `src/easy_a/refresh/targets.py` | exact |
| `src/easy_a/sync/fetch.py` | service | request-response | `src/easy_a/schedule/client.py` + `parser.py` | role-match |
| `src/easy_a/sync/plan.py` | utility (pure diff) | transform | `src/easy_a/common/instructors.py` | partial |
| `src/easy_a/sync/apply.py` | service | CRUD | `src/easy_a/schedule/ingest.py` (`_upsert_sections`) | role-match |
| `src/easy_a/sync/courses.py` | service | request-response | `src/easy_a/catalog/ingest.py` | role-match |
| `src/easy_a/sync/lock.py` | utility | request-response | none (RESEARCH snippet) | none |
| `src/easy_a/schedule/client.py` (+`search_term`) | service | request-response | itself | exact |
| `src/easy_a/schedule/freshness.py` (modify) | utility | transform | itself | exact |
| `src/easy_a/config.py` (modify) | config | n/a | itself | exact |
| `src/easy_a/api/routes/metadata.py` (+`/sync-status`) | route | request-response | itself (`list_terms`) | exact |
| `src/easy_a/api/app.py` (+middleware, logging) | middleware | request-response | itself | exact |
| `src/easy_a/api/schemas.py` (+SyncStatus) | model | n/a | itself | exact |
| `migrations/versions/0004_*.py` | migration | n/a | `migrations/versions/0003_create_section_rankings.py` | exact |
| `src/easy_a/models/sections.py` (+`removed_at`) | model | CRUD | itself | exact |
| `config/registration_windows.toml` | config | n/a | `config/course_targets.toml` | role-match |
| `web/src/components/SyncStatus.tsx` | component | request-response | `web/src/components/CoverageNotice.tsx` | exact |
| `web/src/components/SyncStatus.test.tsx` | test | n/a | `web/src/components/CoverageNotice.test.tsx` | exact |
| `web/src/api/rankings.ts` (+`fetchSyncStatus`) | service | request-response | `fetchCoverage` in same file | exact |
| `tests/sync/*` (+`__init__.py`) | test | n/a | `tests/schedule/test_ingest.py`, `tests/refresh/test_postgres_coverage.py` | exact |
| `docs/runbooks/hosted-beta-operations.md` | docs | n/a | `docs/runbooks/all-tampa-ingestion.md` | exact |
| `.github/workflows/ci.yml`, `Dockerfile`, `.dockerignore`, `render.yaml` | config | n/a | none (net-new); `docker-compose.yml` for postgres:16 | none |
| `scripts/benchmark_rankings_search.py` (+`--remote-url`) | script | request-response | itself | exact |
| `rankings/cache.py`, `rankings/service.py`, `analytics/queries.py`, etc. (`removed_at` filters) | service | CRUD | RESEARCH Pitfall 6 audit list | exact |

## Pattern Assignments

### `src/easy_a/sync/cli.py` / `__main__.py` (CLI, batch)

**Analog:** `src/easy_a/schedule/cli.py` lines 1-47.

```python
from __future__ import annotations
import argparse
from easy_a.db import get_session_factory
from easy_a.schedule.client import ScheduleSearchQuery, StaffScheduleClient

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    with StaffScheduleClient() as client:
        html = client.search(query)
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        result = ingest_schedule_html(session, html, args.term)
    print("Schedule ingest succeeded: " f"seen={...} ...")
    return 0
```

Copy: `build_parser()`/`main(argv) -> int`, `from __future__ import annotations`, `session_factory.begin()` as the transaction boundary. Add `--dry-run`, `--once`, `--log-level`. `__main__.py` calls `raise SystemExit(main())`.

### `src/easy_a/sync/windows.py` (config, transform)

**Analog:** `src/easy_a/refresh/targets.py` lines 1-60. Frozen pydantic models, `tomllib`, path from settings.

```python
class CourseTargets(BaseModel):
    ...
    model_config = ConfigDict(frozen=True, extra="forbid")
    @model_validator(mode="after")
    def validate_targets(self) -> CourseTargets: ...

def load_targets(path: Path | None = None) -> CourseTargets:
    source = path or Path(get_settings().course_targets_path)
    return CourseTargets.model_validate(tomllib.loads(source.read_text(encoding="utf-8")))
```

Mirror this as `RegistrationWindows` with `load_windows(path=None)` reading a new `registration_windows_path` setting. Use `extra="forbid"`, and validate `start <= end` and that windows do not overlap. `tomllib` parses TOML dates as `datetime.date`. Use `ZoneInfo`, and add the startup self-check for tz data (Pitfall 16). Pure functions `interval_for` / `next_start` come from RESEARCH "Cadence" snippet (upward-only jitter).

### `src/easy_a/config.py` (modify)

**Analog:** itself, lines 33-43. Add fields in the same style.

```python
course_targets_path: str = Field(
    default="config/course_targets.toml", validation_alias="EASY_A_COURSE_TARGETS_PATH"
)
seat_fresh_seconds: int = Field(default=600, ge=0, validation_alias="EASY_A_SEAT_FRESH_SECONDS")
```

Add `registration_windows_path` (`EASY_A_REGISTRATION_WINDOWS_PATH`). Change `seat_fresh_seconds` and `seat_stale_seconds` to `int | None` defaulting to `None`, meaning "derive from cadence, explicit override only when set" (Pattern 9). Keep `get_settings()` `lru_cache`.

### `src/easy_a/sync/fetch.py` and `client.py` `search_term` (service, request-response)

**Analog:** `src/easy_a/schedule/client.py` lines 1-25 (`BASE_URL`, `RESULTS_PATH`, `DEFAULT_USER_AGENT`, `ScheduleSearchQuery.__post_init__` guard). Add `search_term` as in RESEARCH "Whole-term client path". Do not loosen the narrow guard. Use a longer read timeout (measured 9-16 s). Chunked parse: RESEARCH "Chunked parse with fail-closed checks", wrapping the unchanged `parse_schedule_html` and `normalize_schedule_row`. Do not import `easy_a.refresh.coverage` (it pulls pandas); re-implement the Tampa-only and duplicate-CRN guards locally.

### `src/easy_a/sync/apply.py` (service, CRUD) and `plan.py`

**Analog:** `src/easy_a/schedule/ingest.py` lines 56-110 (`_upsert_sections`). Copy the field mapping via `_section_values(row)` / `_update_section`, and the `Section(term_id=..., course_id=..., first_seen_at=observed_at, last_seen_at=observed_at, **_section_values(row))` construction. Do NOT copy the per-row `select(Section)` loop or the unconditional `SectionInstructor` and `SeatSnapshot` appends (Pattern 4, Pitfall 14). Instead use three bulk reads, change-only appends, and one bulk `UPDATE last_seen_at`. Set `removed_at = None` when a CRN reappears.

```python
session.add(SeatSnapshot(
    section_id=section.id, observed_at=observed_at, capacity=row.capacity,
    enrollment=row.enrollment, seats_remaining=row.seats_remaining,
    wait_seats_available=row.wait_seats_available))
```

For instructor state use `easy_a.common.instructors.get_current_instructor_states` (batched). For the latest snapshot use the `ROW_NUMBER()` subquery in `src/easy_a/api/routes/rankings.py` `_latest_snapshot` (~line 183), which is portable to SQLite for tests. Cache upkeep: `refresh_section_rankings(session, term=...)` from `easy_a/rankings/cache.py`, only on structural change.

Test pattern for both: `tests/schedule/test_ingest.py` (uses `db_session` fixture from `tests/conftest.py:14`, in-memory SQLite, fixed `datetime(..., tzinfo=UTC)`, and notes that SQLite drops tz so compare with `.replace(tzinfo=None)`).

### `src/easy_a/sync/courses.py` (service, request-response)

**Analog:** `src/easy_a/catalog/ingest.py` lines 1-70. Reuse the `IngestRun` status literals (`"running"` / `"failed"` / `"succeeded"`), `records_failed`, `error_message`, `finished_at = datetime.now(UTC)`:

```python
except CatalogParseError as exc:
    run.status = "failed"
    run.finished_at = datetime.now(UTC)
    run.error_message = str(exc)
    run.records_failed = 1
```

Use `upsert_catalog_courses(session, courses)`, `parse_catalog_html(html, catalog_edition)`, and `fetch_catalog_html`. Take the edition from `load_targets().catalog_edition`. Catch `CatalogParseError` per course (pace 2 s, cap ~10/sweep, negative cache), count it in `records_failed`, and log by name.

For the sweep's own `IngestRun`, follow RESEARCH Pattern 1. Success is written in the sweep transaction. Failure is written in a second short transaction (do not create the row up front as `catalog/ingest.py` does).

### `src/easy_a/sync/lock.py` and `runner.py` (no analog)

Use the RESEARCH snippets: `try_sweep_lock` with `pg_try_advisory_xact_lock` (no-op on SQLite) and the `threading.Event` SIGTERM loop. `db.py:41` already sets `prepare_threshold=None` for the pooler, so no change is needed.

### `src/easy_a/schedule/freshness.py` (modify)

**Analog:** itself. Keep `classify_observation(observed_at, *, as_of, fresh_seconds, stale_seconds)` (validation `0 <= fresh <= stale` raises `ValueError`). Extend `snapshot_freshness(snapshot, *, as_of=None)` (lines 62-77) with an optional `verified_at` and tier thresholds. Keep the old behaviour when `verified_at is None`. It has three callers: `rankings/service.py:251`, `rankings/cache.py:259`, `quality/coverage.py:42`.

### `src/easy_a/api/routes/metadata.py` (+`/sync-status`) and `schemas.py`

**Analog:** `list_terms` in the same file (lines 18-33) plus the `/coverage` route's `Query(pattern=...)`.

```python
router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])

@router.get("/terms", response_model=list[TermMetadata])
def list_terms(session: DbSession) -> list[TermMetadata]:
    terms = session.execute(select(Term).order_by(Term.banner_code.desc())).scalars().all()
    return [TermMetadata(term=term.banner_code, ...) for term in terms]

@router.get("/coverage", response_model=list[TargetCoverage])
def get_coverage(session: DbSession, term: str = Query(pattern=r"^\d{4}(01|05|08)$")) -> ...
```

Use `DbSession` from `easy_a.api.dependencies`, a pydantic response model in `schemas.py` (mirror `TermMetadata`), and the same term regex. Query `IngestRun` by `source`. Do not return raw `error_message` (return a coarse `error_kind`). Do not hang it on `/coverage`.

### `src/easy_a/api/app.py` (middleware + logging)

**Analog:** itself. Existing structure: `create_app()` builds the app, then `add_middleware(CORSMiddleware, allow_origins=settings.allowed_frontend_origin_list(), allow_methods=["GET"], ...)`, then `@app.exception_handler(SQLAlchemyError)`, then `/health` (DB-free, keep it that way). Add `@app.middleware("http")` inside `create_app()` using `time.perf_counter()` and `request.scope["route"].path`, plus `logging.basicConfig(level=logging.INFO)`. The `_lifespan` is where the `removed_at` startup guard goes, next to `get_settings().require_database_url()`, and it must respect the `get_db_session in app.dependency_overrides` test bypass.

### `migrations/versions/0004_*.py` (migration)

**Analog:** `migrations/versions/0003_create_section_rankings.py` lines 1-25.

```python
"""create section rankings cache

Revision ID: 0003_create_section_rankings
Revises: 0002_create_section_syllabus_tables
"""
from __future__ import annotations
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0003_create_section_rankings"
down_revision: str | None = "0002_create_section_syllabus_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
```

New revision: `down_revision = "0003_create_section_rankings"`. Use `op.add_column("sections", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))`, `op.create_index("ix_seat_snapshots_section_id_observed_at", ...)`, and a `downgrade()`. Model side: add `removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` after `last_seen_at` in `src/easy_a/models/sections.py:40`. It is manual apply only and needs the user's explicit go-ahead.

### `config/registration_windows.toml`

**Analog:** `config/course_targets.toml` (top-level scalars plus arrays of tables). Use the RESEARCH file verbatim: Nov 2-30 2026, Jan 7 2027, Jan 11-15 2027, each with a `source` URL.

### `web/src/components/SyncStatus.tsx` (+ test)

**Analog:** `web/src/components/CoverageNotice.tsx` lines 1-52. Copy the loader-prop pattern (`loader: CoverageLoader`), the `AbortController` effect, the loading/error/retry states, and the amber `role="status"` classes:

```tsx
useEffect(() => {
  const controller = new AbortController();
  loader(term, controller.signal)
    .then((result) => { if (!controller.signal.aborted) setItems(result); })
    .catch(() => { if (!controller.signal.aborted) { setItems([]); setError(true); } })
    .finally(() => { if (!controller.signal.aborted) setLoading(false); });
  return () => controller.abort();
}, [term, loader, version]);
```

The browser only formats "Updated N min ago". The threshold decision (`is_stale`) comes from the API. Test: `CoverageNotice.test.tsx` (vitest, `@testing-library/react`, `render(<X loader={async () => items} />)`, `screen.findByText`, retry via `userEvent`).

### `web/src/api/rankings.ts` (+`fetchSyncStatus`)

**Analog:** `fetchCoverage` at lines 170-176:

```ts
export const fetchCoverage: CoverageLoader = async (term, signal) => {
  if (isUsingMockData) return term === "202701" ? syntheticCoverage : [];
  const url = endpointUrl("/api/v1/metadata/coverage");
  url.searchParams.set("term", term);
  return fetchJson<CourseCoverage[]>(url, signal);
};
```

Add the type to `web/src/types/rankings.ts`, and label the mock branch as synthetic.

### `tests/sync/*`

**Analogs:** `tests/schedule/test_ingest.py` (SQLite `db_session` fixture) and `tests/refresh/test_postgres_coverage.py` lines 1-40 for Postgres integration:

```python
url = os.environ.get("EASY_A_TEST_POSTGRES_URL")
if not url:
    pytest.skip("Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration")
schema = "sprint5_" + uuid4().hex
connection.execute(text(f'CREATE SCHEMA "{schema}"'))
connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
Base.metadata.create_all(connection)
```

Use it for the xact-lock test (a second connection must get `false`). Add `tests/sync/__init__.py` as the other test dirs have. Fixtures live in `tests/fixtures/`.

### `docs/runbooks/hosted-beta-operations.md`

**Analog:** `docs/runbooks/all-tampa-ingestion.md`: an intro paragraph, `## Preconditions`, numbered `## 1. ...` sections with fenced `bash` `uv run` commands, and a Run Log. Required topics: refresh data, recover from a failed sweep, pause/resume the worker, `--dry-run`, un-mark a wrongly removed section. Also the migration-before-merge rule, and "do not use the legacy `refresh_*` scripts for 202701" (Pitfall 14).

### CI, Docker, Render (no repo analog)

Use the RESEARCH pins and the validated Blueprint draft. For the CI Postgres service container copy from `docker-compose.yml`:

```yaml
image: postgres:16
environment: {POSTGRES_DB: easy_a, POSTGRES_USER: easy_a, POSTGRES_PASSWORD: easy_a}
healthcheck: {test: ["CMD-SHELL", "pg_isready -U easy_a -d easy_a"], interval: 5s, timeout: 5s, retries: 10}
```

Set `EASY_A_TEST_POSTGRES_URL=postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a`. Gates: `ruff check .` (fix the two E501s first: `scripts/refresh_all_tampa.py:150`, `src/easy_a/refresh/cleanup.py:496`), `pytest`, the web `lint`/`typecheck`/`test`/`build`, and `mypy` non-blocking. There must be no path filters on the workflow. Pin `astral-sh/setup-uv@v10.2.0`.

## Shared Patterns

### IngestRun status literals
**Source:** `src/easy_a/catalog/ingest.py:24-56`. Use `"running"`, `"succeeded"`, `"failed"`, `records_seen/inserted/updated/failed`, `error_message`, `finished_at=datetime.now(UTC)`. **Apply to:** sync runner, `/sync-status` reader.

### Settings via pydantic-settings
**Source:** `src/easy_a/config.py:33-43` (`Field(default=..., validation_alias="EASY_A_*")`, `get_settings()` cached). **Apply to:** windows path, freshness overrides, any worker knobs. Do not read `os.environ` directly.

### Session and transaction
**Source:** `session_factory = get_session_factory(); with session_factory.begin() as session:` (`schedule/cli.py`). **Apply to:** all sync DB work (one sweep = one transaction).

### Module conventions
Every module starts with `from __future__ import annotations`. Strict mypy applies to `src` (currently 0 errors), so new sync code must be fully typed. Ruff line length is enforced (E501).

### removed_at filter
**Apply to:** `rankings/cache.py:99-103`, `rankings/service.py:126-130,152-155`, `analytics/queries.py:168,241`, `signals/resolver.py:68`, `refresh/coverage.py:57,95`, `api/routes/metadata.py:54`, `refresh/service.py:98,102`, `quality/checks.py:80,315`, `quality/coverage.py:34`, and scripts `validate_tampa_ingest.py`, `verify_rankings_pages.py`, `inventory_tampa_grades.py`, `benchmark_rankings_search.py:261`. Add `Section.removed_at.is_(None)`. Also delete the `section_rankings` rows for newly removed sections. The legacy `_update_section` should reset `removed_at = None`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/easy_a/sync/runner.py` | service | event-driven loop | No long-running loop or signal handling exists; use RESEARCH Patterns 6 and the `threading.Event` guidance |
| `src/easy_a/sync/lock.py` | utility | request-response | No advisory locks in repo; use the RESEARCH snippet |
| `.github/workflows/ci.yml` | config | n/a | No `.github/` exists |
| `Dockerfile`, `.dockerignore` | config | n/a | None exist; follow the uv Docker guide and Pitfall 17 |
| `render.yaml` | config | n/a | None exists; use the RESEARCH validated draft (Pitfall 11: `fromGroup` needs a human check) |

## Metadata

**Analog search scope:** `src/easy_a/{schedule,catalog,refresh,api,config.py,models}`, `migrations/`, `config/`, `web/src/{components,api}`, `tests/`, `docs/runbooks/`, `docker-compose.yml`
**Note:** RESEARCH.md lines 490-798 (rest of the Blueprint draft, open questions, validation) were not read; the planner should read them for the render.yaml body.
**Pattern extraction date:** 2026-09-29
