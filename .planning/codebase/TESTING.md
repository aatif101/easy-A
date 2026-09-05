# Testing Patterns

**Analysis Date:** 2026-09-05

## Test Framework

**Python runner:**
- pytest `>=8.3.0` (dev dependency in `pyproject.toml`)
- Config: `pyproject.toml` → `[tool.pytest.ini_options] testpaths = ["tests"]`
- No extra plugins (no pytest-cov, no pytest-asyncio, no pytest-mock)

**Frontend runner:**
- Vitest `^3.2.4` with `jsdom`
- Config: `web/vite.config.ts` (`test.environment = "jsdom"`, `setupFiles = "./src/test/setup.ts"`, `css: true`)
- Testing Library: `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`

**Assertion libraries:**
- Python: bare `assert` + `pytest.raises`
- Frontend: `expect` from vitest, extended by `@testing-library/jest-dom/vitest` in `web/src/test/setup.ts`

**Run Commands:**
```bash
uv run pytest                                  # all Python tests (~154 tests)
uv run pytest tests/rankings/test_service.py   # one file
uv run pytest -k rank_section                  # by name
uv run ruff check .                            # lint
uv run mypy src migrations scripts tests       # tests are type-checked too

cd web
npm test          # vitest run (single pass, no watch)
npm run lint
npm run typecheck
```
No coverage command and no CI workflow files exist (`.github/` is absent).

## Test File Organization

**Location:**
- Python: separate `tests/` tree that mirrors `src/easy_a/` package-for-package — `tests/rankings/`, `tests/schedule/`, `tests/signals/`, `tests/api/`, `tests/quality/`, `tests/refresh/`, `tests/catalog/`, `tests/grades/`, `tests/syllabi/`, `tests/analytics/`, `tests/common/`.
- Frontend: co-located with the source — `web/src/api/rankings.test.ts`, `web/src/App.test.tsx`.

**Naming:**
- Python files `test_<module>.py`, matching the source module (`tests/schedule/test_parser.py` ↔ `src/easy_a/schedule/parser.py`).
- Python test functions are long behavioral sentences: `test_staff_current_section_falls_back_to_course_analytics`, `test_rank_section_cli_outputs_synthetic_spring_2027_fixture`.
- Frontend files `<module>.test.ts(x)`; cases use `describe("ranking API client")` + `test("sends selected search filters to the real API")`.

**Structure:**
```
tests/
├── conftest.py               # shared db_session fixture + seed data
├── fixtures/                 # captured USF HTML pages
│   ├── schedule_current.html
│   ├── schedule_historical_202408_89033.html
│   ├── schedule_ambiguous.html
│   ├── schedule_not_found.html
│   └── syllabus_enc_1101.html
├── <domain>/__init__.py      # every test package has one
└── <domain>/test_*.py

web/src/
├── test/setup.ts             # jest-dom + auto cleanup
├── fixtures/rankings.ts      # syntheticRankings shared test data
└── **/*.test.ts(x)
```
Every `tests/<domain>/` directory contains an `__init__.py` — add one for any new test package.

## Test Structure

**Python — flat module functions, no classes, no `describe`-style nesting.** Bodies follow arrange / act / assert separated by blank lines:

```python
def test_rank_course_cli_requires_term_subject_and_course() -> None:
    parser = build_course_parser()

    args = parser.parse_args(["--term", "202701", "--subject", "MAC", "--course", "1105"])

    assert args.term == "202701"
    assert args.subject == "MAC"
```
(`tests/rankings/test_cli.py`)

**Patterns:**
- `from __future__ import annotations` first line; every test annotated `-> None`; fixture params fully typed (`db_session: Session`, `tmp_path: Path`, `monkeypatch: MonkeyPatch`).
- Module-level constants hold shared setup: `NOW = datetime(2026, 9, 1, tzinfo=UTC)`, `FIXTURES = Path(__file__).parents[1] / "fixtures"`, `GRADE_HEADER = [...]` (`tests/rankings/test_service.py`). All datetimes are timezone-aware UTC.
- Long HTML inputs are module-level triple-quoted constants when small (`COURSE_INVENTORY_HTML` in `tests/catalog/test_parser.py`) and files under `tests/fixtures/` when they are real captured pages.
- Row-building helpers are `_`-prefixed module functions in the test file: `_add_grade(...)`, `_add_section(...)`, `_seed_reference_data(...)`.
- `pytest.mark.parametrize` is used sparingly (4 usages); prefer separate named tests.

**Frontend — `describe` + `test`, arrange via typed loader functions:**

```tsx
const resolvedRankingLoader: RankingLoader = async (query) => pageFor(query);

const renderLoadedApp = async (
  rankingLoader: RankingLoader = resolvedRankingLoader,
  metadataLoader: MetadataLoader = resolvedMetadataLoader,
) => {
  const user = userEvent.setup();
  render(<App rankingLoader={rankingLoader} metadataLoader={metadataLoader} mockMode={false} />);
  const table = await screen.findByRole("table", { name: "Ranked USF course sections" });
  return { table, user };
};
```
(`web/src/App.test.tsx`) — query by accessible role/name, never by CSS class or test id.

## Mocking

**No mocking library on the Python side.** Fakes are built from real seams:

- **Database:** in-memory SQLite (`sqlite+pysqlite:///:memory:`) with `Base.metadata.create_all(engine)`. The API suite adds `poolclass=StaticPool` and `connect_args={"check_same_thread": False}` so the TestClient shares one connection (`tests/api/test_rankings_api.py`).
- **HTTP:** `httpx.MockTransport` with a handler function that records the request and returns a canned `httpx.Response`; the real client class is then exercised end-to-end (`tests/schedule/test_client.py`, `tests/syllabi/test_client.py`).
- **FastAPI dependencies:** `app.dependency_overrides[get_db_session] = ...` inside a fixture, cleared after yield.
- **`monkeypatch`** is used only for process-level seams, e.g. pointing `get_session_factory` at a test engine in CLI tests (`tests/rankings/test_cli.py`); 40 combined uses of `monkeypatch` / `MockTransport` / `tmp_path` across the suite.
- **Filesystem:** `tmp_path`; XLSX inputs are generated with `openpyxl.Workbook()` rather than committed binaries.
- **CLI output:** `capsys` (`CaptureFixture[str]`) asserts on printed JSON.

**Frontend — vitest built-ins:**

```ts
vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000");
const fetchMock = vi.fn<typeof fetch>()
  .mockResolvedValue(new Response(JSON.stringify(terms), { status: 200 }));
vi.stubGlobal("fetch", fetchMock);

const { fetchTerms } = await import("./rankings");   // dynamic import AFTER stubbing env

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.resetModules();
});
```
(`web/src/api/rankings.test.ts`) — the module under test is imported dynamically because it reads `import.meta.env` at module scope.

**What to Mock:**
- The network boundary (`fetch`, `httpx` transport) and the environment (`VITE_API_BASE_URL`, session factory).

**What NOT to Mock:**
- Parsers, scoring, ranking, ingest, and the ORM — run these against real SQLite and real HTML fixtures.
- React components: `App` receives `rankingLoader` / `metadataLoader` props, so pass a fake loader instead of mocking child components.

## Fixtures and Factories

**Shared Python fixture** — `tests/conftest.py` yields a `Session` pre-seeded with three `Term` rows (`202701`, `202408`, `202605`) and two `Course` rows (`MAC 1105` id=10, `ENC 1101` id=11). Reuse those IDs when adding tests:

```python
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([...])
        session.commit()
        yield session
```

**Per-suite fixtures** live in the test file itself (`api_session_factory`, `api_client` in `tests/api/test_rankings_api.py`) and tear down explicitly: `Base.metadata.drop_all(engine)` then `engine.dispose()`.

**Location:**
- HTML/page fixtures: `tests/fixtures/`
- Frontend sample payloads: `web/src/fixtures/rankings.ts` (`syntheticRankings`), shared by both `App.test.tsx` and `rankings.test.ts`

## Coverage

**Requirements:** none enforced. No coverage tool is installed for Python; vitest has no `coverage` config (though `coverage/` is eslint-ignored).

**View Coverage:**
```bash
cd web && npx vitest run --coverage   # requires adding @vitest/coverage-v8
```

## Test Types

**Unit tests:**
- Parsers (`tests/catalog/test_parser.py`, `tests/schedule/test_parser.py`, `tests/grades/test_parser.py`), scoring/analytics (`tests/analytics/`), term and instructor normalization (`tests/common/`).

**Integration tests:**
- Ingest → DB → service chains against SQLite: `tests/rankings/test_service.py` calls `ingest_grade_file` and `ingest_schedule_html` before ranking.
- HTTP API through `fastapi.testclient.TestClient`: `tests/api/test_rankings_api.py`.
- CLI end-to-end via `section_main(argv)` with a patched session factory and `capsys`: `tests/rankings/test_cli.py`, `tests/quality/test_cli.py`, `tests/refresh/test_cli.py`, `tests/signals/test_cli.py`.

**Component tests:**
- `web/src/App.test.tsx` renders the full app with injected loaders and drives it via `userEvent`.

**E2E tests:** none (no Playwright/Cypress).

## Common Patterns

**Error testing** (14 `pytest.raises` uses):
```python
with pytest.raises(ScheduleParseError):
    parse_schedule_html(FIXTURES.joinpath("schedule_not_found.html").read_text())
```
API-level errors assert on status and body instead:
```python
assert response.status_code == 404
```

**Async testing:**
- Python routes are defined `def` (sync), so no async tests exist.
- Frontend async assertions use `await expect(fetchTerms()).resolves.toEqual(terms)` and `await screen.findByRole(...)` / `waitFor(...)`.

**Health check baseline:**
```python
def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

## Adding New Tests

1. Create `tests/<domain>/__init__.py` if the package is new.
2. Start the file with `from __future__ import annotations`, annotate every test `-> None`.
3. Use `db_session` from `tests/conftest.py` for DB-backed logic; build a local engine fixture only when you need `StaticPool` or a custom session factory.
4. Stub HTTP with `httpx.MockTransport`, never by patching the client class.
5. Put new captured upstream HTML in `tests/fixtures/` and load it via `Path(__file__).parents[1] / "fixtures"`.
6. Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy src migrations scripts tests` — tests are held to the same strict typing bar as `src/`.

---

*Testing analysis: 2026-09-05*
