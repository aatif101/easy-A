# Coding Conventions

**Analysis Date:** 2026-09-05

Two codebases live here with separate convention sets:
- Python backend/pipeline: `src/easy_a/`, `scripts/`, `migrations/`, `tests/`
- React frontend: `web/src/`

## Naming Patterns

**Python files:**
- `snake_case.py`, one concern per module.
- Per-domain package with a fixed module vocabulary — reuse these names when adding a domain:
  - `client.py` (HTTP fetch), `parser.py` (HTML/XLSX → typed rows), `ingest.py` (persist to DB),
    `service.py` (orchestration), `models.py` (Pydantic DTOs), `cli.py` (argparse entry point).
  - Examples: `src/easy_a/schedule/`, `src/easy_a/syllabi/`, `src/easy_a/catalog/`, `src/easy_a/signals/`.
- SQLAlchemy ORM tables live only in `src/easy_a/models/core.py` and `src/easy_a/models/sections.py` — not in per-domain `models.py`.

**Python functions:**
- `snake_case`. Verb-first for actions: `rank_section`, `ingest_schedule_html`, `parse_catalog_html`, `normalize_banner_term_code`.
- Module-private helpers are prefixed with `_` and defined below the public API in the same file: `_seat_info_for`, `_historical_summary`, `_get_section_course_term` in `src/easy_a/rankings/service.py`.
- CLI modules expose `build_*_parser()`, `format_*()`, and `*_main(argv: list[str] | None = None) -> int` (`src/easy_a/rankings/cli.py`).

**Python variables/constants:**
- `snake_case` locals; `UPPER_SNAKE` module constants (`RESULTS_PATH` in `src/easy_a/schedule/client.py`, `DELIVERY_METHOD_LABELS` in `src/easy_a/schedule/normalize.py`, `NAMING_CONVENTION` in `src/easy_a/db.py`).

**Python types:**
- `PascalCase` classes. Pydantic DTOs are nouns (`SectionRanking`, `SeatInfo`, `RankingProvenance` in `src/easy_a/rankings/models.py`).
- Exceptions end in `Error` and subclass a stdlib type, one per domain module: `RankingResolutionError(ValueError)`, `ScheduleParseError(ValueError)`, `RefreshStageError(RuntimeError)`.
- `StrEnum` for wire-visible enumerations, with **lowercase member names matching their values**: `RankingFreshness.current = "current"` (`src/easy_a/rankings/models.py`), `RankingSort.easiness_desc` (`src/easy_a/api/schemas.py`).

**TypeScript files:**
- `camelCase.ts` for modules (`web/src/api/rankings.ts`, `web/src/utils/rankings.ts`), `PascalCase.tsx` for components (`web/src/components/RankingTable.tsx`, `FilterBar.tsx`, `SignalChips.tsx`).
- Tests sit next to the unit under test: `web/src/api/rankings.test.ts`, `web/src/App.test.tsx`.

**TypeScript symbols:**
- `camelCase` functions/consts, `PascalCase` components and types (`RankingQuery`, `RankingsSearchResponse`, `MetadataLoader` in `web/src/types/rankings.ts`).
- API field names crossing the boundary stay in Python `snake_case` (`term_name`, `seats_remaining`) — do not rename in the TS types.

## Code Style

**Formatting (Python):**
- Ruff, `line-length = 100`, `target-version = "py312"` (`pyproject.toml`).
- No separate formatter config; write code that already satisfies ruff's line length.
- Multi-line call arguments use trailing-comma / one-arg-per-line style (see `rank_course_sections(...)` in `src/easy_a/rankings/cli.py`).

**Linting (Python):**
- `[tool.ruff.lint] select = ["B", "C4", "E", "F", "I", "SIM", "UP"]` — bugbear, comprehensions, pycodestyle, pyflakes, **import sorting (I)**, simplify, pyupgrade.
- Consequences to respect: no mutable default args, prefer comprehensions, no legacy typing syntax (`X | None`, not `Optional[X]`), no redundant `if/else` where a ternary or `or` works.

**Type checking (Python):**
- mypy `strict = true`, `mypy_path = "src"`, `ignore_missing_imports = false`, `warn_unused_ignores`, `warn_return_any` (`pyproject.toml`).
- Every function — including test functions — is fully annotated, return types included (`-> None` on tests).
- Missing third-party stubs must be added as dev deps (`pandas-stubs`, `types-beautifulsoup4`, `types-openpyxl`) rather than silenced with `# type: ignore`.

**Frontend:**
- ESLint flat config `web/eslint.config.js`: `js.configs.recommended` + `tseslint.configs.recommended` + `react-hooks` recommended + `react-refresh/only-export-components` (warn). Ignores `dist`, `coverage`.
- TypeScript project references: `web/tsconfig.json` → `tsconfig.app.json` / `tsconfig.node.json`. Typecheck with `tsc -b`.
- Tailwind for styling (`web/tailwind.config.ts`); no CSS-in-JS.
- Double quotes and semicolons throughout `web/src/`.

**Commands:**
```bash
uv run ruff check .
uv run mypy src migrations scripts tests
cd web && npm run lint && npm run typecheck
```

## Import Organization

**Python** (enforced by ruff `I`):
1. `from __future__ import annotations` — **first line of every Python module**, including tests and scripts.
2. Standard library.
3. Third party (`sqlalchemy`, `pydantic`, `fastapi`, `httpx`, `pytest`).
4. First party, always absolute from the package root: `from easy_a.rankings.service import rank_section`.

Never use relative imports; `src/easy_a/**` modules always import via `easy_a.*`.

**TypeScript:**
1. Third party (`react`, `@testing-library/*`, `vitest`).
2. Local modules, relative paths (`./rankings`, `../fixtures/rankings`).
3. Type-only imports use `import type { ... }` (`web/src/App.test.tsx`).

No path aliases configured in either stack.

## Error Handling

**Define a domain exception per module** and raise it instead of bare `ValueError`:

```python
class RankingResolutionError(ValueError):
    """Raised when a section ranking request cannot be resolved."""
```
(`src/easy_a/rankings/service.py`; same shape in `src/easy_a/schedule/parser.py`, `src/easy_a/syllabi/ingest.py`, `src/easy_a/common/terms.py`.)

**Translate to HTTP at the route boundary only**, with `from exc` chaining:

```python
try:
    return rank_section(session, term=term, crn=crn)
except RankingResolutionError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
```
(`src/easy_a/api/routes/rankings.py`.) Service and parser layers never import FastAPI.

**CLI entry points catch the domain error, print a message, and return a nonzero int** rather than letting it traverse:
`src/easy_a/grades/cli.py:33`, `src/easy_a/refresh/cli.py:104`. Scripts wrap with `raise SystemExit(main())` (`scripts/rank_section.py`).

**Database work goes through the transaction helper**, which commits on success and rolls back on any exception: `session_scope()` in `src/easy_a/db.py`.

## Logging

**Framework:** none. No `logging` module usage anywhere in `src/easy_a/`.

**Patterns:**
- User-facing output is `print()` and only in `*/cli.py` modules. Library/service/parser code returns values or raises; it never prints.
- Structured output uses Pydantic serialization: `print(report.model_dump_json(indent=2))` (`src/easy_a/quality/cli.py`) or `json.dumps(model.model_dump(mode="json"), indent=2)` (`src/easy_a/rankings/cli.py`).
- SQL echo is config-driven, not ad hoc: `EASY_A_ECHO_SQL` → `Settings.echo_sql` (`src/easy_a/config.py`).

## Comments

**When to Comment:**
- Sparse. Most modules have zero docstrings (`grep '"""'` returns 0 for most of `src/easy_a/*/`), and the code relies on names plus type annotations instead.
- Docstrings are used almost exclusively as one-line exception descriptions and package-level `__init__.py` summaries.
- No inline `#` commentary explaining obvious code. Add a comment only for non-obvious upstream quirks (Banner form fields, USF HTML shapes).

**JSDoc/TSDoc:** not used in `web/src/`.

## Function Design

**Size:** small; long orchestration functions (e.g. `rank_section` in `src/easy_a/rankings/service.py`) are composed of many `_`-prefixed single-purpose helpers rather than inline blocks.

**Parameters:**
- **Keyword-only after the first positional** is the house style: `def rank_section(session: Session, *, term: str | int, crn: str, config: ScoreConfig | None = None)`. Helpers follow the same `*,` pattern.
- Dependencies are injected as parameters with a default-resolving fallback (`get_engine(database_url: str | None = None)`, `get_session_factory(engine: Engine | None = None)` in `src/easy_a/db.py`) so tests can pass a SQLite engine.
- Accept flexible inputs, normalize immediately: `normalize_banner_term_code(term)` and `crn.strip()` at the top of `rank_section`.

**Return Values:**
- Return frozen Pydantic models, not dicts: DTOs set `model_config = ConfigDict(frozen=True)` (`src/easy_a/rankings/models.py`).
- CLI `*_main` returns `int` exit codes.

## Module Design

**Exports:**
- Packages re-export their public surface in `__init__.py` with an `__all__` and a one-line docstring; consumers import from the package (`from easy_a.rankings import RankingFreshness, rank_section`) while internals import from the exact module.
- `src/easy_a/models/__init__.py` is the single import point for all ORM entities.

**Barrel Files:** package `__init__.py` files serve this role on the Python side. The frontend has no barrels — import directly from the component/module file.

## Configuration & Data Layer

- All settings go through `Settings` (pydantic-settings) in `src/easy_a/config.py` with explicit `validation_alias` env names (`DATABASE_URL`, `EASY_A_API_HOST`, ...) and `get_settings()` cached via `@lru_cache`. Never read `os.environ` directly.
- ORM models use SQLAlchemy 2.0 typed style: `Mapped[...]` + `mapped_column(...)`, a shared `Timestamped` mixin, and the `NAMING_CONVENTION` metadata in `src/easy_a/db.py` so Alembic autogenerate produces stable constraint names.
- FastAPI routes use `Annotated[...]` query params and shared dependency aliases `BannerTerm` / `DbSession` from `src/easy_a/api/dependencies.py`.

---

*Convention analysis: 2026-09-05*
