# Codebase Concerns

**Analysis Date:** 2026-09-05

Scope: full repo (`src/easy_a/`, `web/`, `scripts/`, `tests/`, `migrations/`, `docs/`).

Overall the codebase is unusually clean for its stage: strict mypy, ruff with `B/C4/E/F/I/SIM/UP`, no `TODO`/`FIXME`/`HACK`/`XXX` markers anywhere in `src/`, `web/src/`, `scripts/`, or `migrations/`, and broad per-module test coverage. The concerns below are structural and data-integrity risks, not sloppiness.

## Tech Debt

**No CI pipeline:**
- Issue: there is no `.github/` directory and no CI config anywhere in the repo. `ruff`, `mypy`, `pytest`, and the web `vitest`/`tsc -b` suites only run when a developer remembers to run them.
- Files: repo root (missing `.github/workflows/`), `pyproject.toml`, `web/package.json`
- Impact: regressions in parsers or scoring can merge unnoticed; the two most recent fix commits both touched data-correctness paths.
- Fix approach: add a workflow running `uv run ruff check`, `uv run mypy src`, `uv run pytest`, and `npm --prefix web run typecheck && npm --prefix web test`.

**`assert` used for control flow in production code:**
- Issue: `assert term_row is not None` guards the summary query after refresh stages.
- Files: `src/easy_a/refresh/service.py`
- Impact: under `python -O` the assert is stripped and the following code raises `AttributeError` on `None` instead of a clear error.
- Fix approach: raise an explicit `RefreshStageError` / `ValueError` instead.

**Two parallel seat sources of truth:**
- Issue: seat values are written both to canonical `Section` columns (`_section_values` in `src/easy_a/schedule/ingest.py`) and to `SeatSnapshot` rows, and the ranking layer falls back between them (`_seat_info_for` in `src/easy_a/rankings/service.py`).
- Files: `src/easy_a/schedule/ingest.py`, `src/easy_a/rankings/service.py`, `src/easy_a/models/sections.py`
- Impact: the two can disagree; the fallback silently reports `sections.current_seat_fields` provenance, so a stale canonical column can look "current".
- Fix approach: make `SeatSnapshot` the single source for point-in-time seats and derive section columns as a materialized latest view, or drop the fallback branch.

**Commit authorship is unconfigured:**
- Issue: recent commits (`0f67b94`, `c67f04e`) are authored as `kanishk-sc <your-email@example.com>`.
- Impact: blame/attribution is unreliable; placeholder emails leak into public history.
- Fix approach: set per-repo `user.email`.

## Known Bugs

No confirmed open bugs were found. Two recently fixed classes of bug indicate where regressions are likely to recur:

**Cross-dialect query behavior (recently fixed):**
- Symptoms: ranking search ordering behaved differently on PostgreSQL than on the SQLite test database (`c67f04e`, `src/easy_a/api/routes/rankings.py`).
- Trigger: tests run entirely on `sqlite+pysqlite:///:memory:` (`tests/conftest.py`), while `docker-compose.yml` and the default `DATABASE_URL` in `src/easy_a/config.py` target PostgreSQL 16.
- Workaround: none — dialect divergence is only caught in manual runs. See "Test Coverage Gaps".

**Seat/catalog data quality (recently fixed):**
- Symptoms: catalog parsing and seat findings produced bad values (`0f67b94`, `src/easy_a/catalog/parser.py`, `src/easy_a/quality/checks.py`).
- Trigger: upstream HTML variation. `docs/live-source-drift-2026-09-01.md` documents a live seat row changing from `190/207/-17` to `135/0/135`, i.e. upstream genuinely publishes negative seats-remaining.

## Security Considerations

**Default database credentials committed:**
- Risk: `docker-compose.yml` and the fallback `database_url` in `src/easy_a/config.py` both use the same trivial dev username/password/database triple, and the Postgres port is published to the host.
- Files: `docker-compose.yml`, `src/easy_a/config.py`
- Current mitigation: values are development-only and `DATABASE_URL` overrides them; `.env` is gitignored (`.gitignore`).
- Recommendations: do not publish port 5432 to `0.0.0.0` by default, and document that these credentials must never be reused outside local dev.

**Secrets handling is sound but minimal:**
- `.env.example` holds only non-secret placeholders and `.env` is gitignored. No API keys, tokens, or credentials are required by any client — all three external clients (`src/easy_a/catalog/client.py`, `src/easy_a/schedule/client.py`, `src/easy_a/syllabi/client.py`) hit unauthenticated public endpoints.
- Recommendation: keep it that way; if an authenticated source is added, route it through `Settings` in `src/easy_a/config.py` rather than ad-hoc `os.environ`.

**CORS origins are configuration-driven:**
- Risk: `allowed_frontend_origins` is a comma-joined string parsed at request-config time; a malformed env value silently yields a wrong or empty origin list.
- Files: `src/easy_a/config.py`, `src/easy_a/api/app.py`
- Current mitigation: `allow_credentials=False` and `allow_methods=["GET"]` keep the blast radius small.
- Recommendations: validate origins as URLs at settings-load time.

**Server-side request surface on syllabus fetch:**
- Risk: `fetch_catalog_html` in `src/easy_a/catalog/client.py` will fetch any URL passed to it (CLI-driven only, but with `follow_redirects=True`).
- Current mitigation: `src/easy_a/syllabi/client.py` correctly pins the host to `usf.simplesyllabus.com` and validates document IDs against a regex.
- Recommendations: apply the same host allowlist to the catalog fetcher before exposing any fetch path over HTTP.

## Performance Bottlenecks

**`GET /api/v1/rankings/search` ranks every section in the term per request:**
- Problem: `_rank_candidate_sections` selects all matching CRNs, then calls `rank_section` once per CRN; filtering, sorting, and pagination all happen in Python after the full set is materialized.
- Files: `src/easy_a/api/routes/rankings.py`, `src/easy_a/rankings/service.py`
- Cause: each `rank_section` call issues several independent queries (section/course/term, instructor state, latest seat snapshot, course attributes, historical analytics, signal resolution) — a classic N+1 multiplied by ~6. `limit`/`offset` are applied only to the already-computed list.
- Improvement path: batch the per-section lookups into set-based queries keyed by section id, and push filtering/ordering/pagination into SQL. Cache `get_current_section_historical_analytics` per (term, subject, course_number) within a request — it is currently recomputed for every CRN of the same course.

**Historical analytics recomputed per section:**
- Problem: `_historical_stats_for_section` calls `get_current_section_historical_analytics` for the whole course and then linearly scans for the one matching CRN.
- Files: `src/easy_a/rankings/service.py`, `src/easy_a/analytics/queries.py`
- Improvement path: compute once per course and index by CRN.

## Fragile Areas

**Positional HTML column parsing:**
- Files: `src/easy_a/schedule/parser.py`
- Why fragile: `_parse_row` reads 24 fixed cell indices (`values[0]` … `values[23]`) from the USF Staff Schedule table. A single upstream column insertion shifts every field, and seats/capacity would be silently misread as adjacent columns.
- Safe modification: the header guard (`EXPECTED_HEADERS`) must stay in place and be treated as the contract; prefer mapping by header name rather than index when touching this file.
- Test coverage: `tests/schedule/test_parser.py` plus checked-in HTML fixtures (`tests/fixtures/schedule_*.html`) — good, but they encode one upstream layout snapshot.

**Regex signal extraction with hardcoded high confidences:**
- Files: `src/easy_a/signals/rules.py`, `src/easy_a/signals/extract.py`, `src/easy_a/signals/resolver.py`
- Why fragile: rules assign 0.94–0.99 confidence to plain regex matches over free-text syllabus prose. Wording variation produces confident wrong answers rather than abstentions, and negation handling depends on rule ordering.
- Safe modification: add a fixture-backed test for every new rule and prefer lower confidence over a broader pattern.

**Scoring thresholds are magic constants:**
- Files: `src/easy_a/analytics/confidence.py` (`LOW_CONFIDENCE_MAX_EFFECTIVE_N = 60.0`, `HIGH_CONFIDENCE_MIN_EFFECTIVE_N = 180.0`), `src/easy_a/analytics/scoring.py`
- Why fragile: user-facing confidence labels hinge on undocumented cutoffs; changing them silently reclassifies every ranking.
- Safe modification: treat changes as a data-contract change and update `README.md` alongside.

**Frontend silently falls back to synthetic data:**
- Files: `web/src/api/rankings.ts`, `web/src/fixtures/rankings.ts`
- Why fragile: when `VITE_API_BASE_URL` is unset, `isUsingMockData` is true and the app serves 287 lines of fabricated rankings. A misconfigured deploy renders plausible fake course data instead of failing.
- Safe modification: ensure the mock banner is prominent and gate the fallback to `import.meta.env.DEV`.

## Scaling Limits

**Search endpoint:**
- Current capacity: fine at fixture scale (single subject/course).
- Limit: an unfiltered `search?term=202701` ranks every section in a full USF term (tens of thousands of sections × ~6 queries each) in one synchronous request.
- Scaling path: SQL-side filtering + pagination as described under Performance, plus a materialized rankings table refreshed by `src/easy_a/refresh/service.py`.

**Seat snapshots grow unbounded:**
- Current capacity: every schedule ingest appends a `SeatSnapshot` and a `SectionInstructor` row per section, with no dedupe of unchanged values (`src/easy_a/schedule/ingest.py`).
- Limit: repeated refreshes multiply row count by section count with no retention policy; the latest-snapshot query in `src/easy_a/rankings/service.py` scans an ever-growing history.
- Scaling path: only insert on change, add a retention/compaction job, and ensure an index on `(section_id, observed_at desc)`.

**Single-process synchronous API:**
- Files: `src/easy_a/api/app.py`, `src/easy_a/api/dependencies.py`
- Limit: sync SQLAlchemy sessions on FastAPI's threadpool; concurrency is bounded by pool size, and one slow search request occupies a worker thread for its whole duration.

## Dependencies at Risk

**None critical.** All Python dependencies are current major versions pinned by `uv.lock`; `web/` is on React 19 / Vite 7 / Tailwind 3 with a committed `package-lock.json`.

**Two lockfile ecosystems, one project:**
- Risk: `uv.lock` and `web/package-lock.json` must be updated independently and neither is verified by CI.
- Impact: drift between local and deploy environments goes undetected.

## Missing Critical Features

**No deployment or serving story:**
- Problem: `docker-compose.yml` provisions only PostgreSQL. There is no Dockerfile for the API, no production ASGI configuration beyond `uvicorn` defaults, and no build/serve path for `web/`.
- Blocks: shipping the beta UI to anyone who is not running both processes locally.

**No scheduled refresh:**
- Problem: `scripts/refresh_data.py` and `src/easy_a/refresh/cli.py` exist but must be invoked manually.
- Blocks: keeping seat and instructor data fresh; `src/easy_a/quality/checks.py` already flags observations older than `DEFAULT_STALE_AFTER_DAYS = 7`, a threshold nothing currently enforces.

**No structured logging or observability:**
- Problem: no logging configuration anywhere in `src/easy_a/`. The API's `SQLAlchemyError` handler in `src/easy_a/api/app.py` returns `{"detail": "Database error."}` and discards the exception without recording it.
- Blocks: diagnosing production failures at all.

## Test Coverage Gaps

**PostgreSQL is never exercised by tests:**
- What's not tested: every query path under the production dialect. `tests/conftest.py` builds an in-memory SQLite engine; production runs PostgreSQL 16.
- Files: `tests/conftest.py`, all of `tests/`
- Risk: exactly the class of bug fixed in `c67f04e` — ordering, collation, `NULL` sort placement, `func.upper` semantics, and integer division all differ.
- Priority: High

**Alembic migrations are never applied in tests:**
- What's not tested: `migrations/versions/0001_create_data_core.py` and `0002_create_section_syllabus_tables.py`. Tests use `Base.metadata.create_all`, so migration/model drift is invisible.
- Files: `tests/conftest.py`, `migrations/versions/`
- Risk: a fresh production database built by Alembic can diverge from the schema every test asserts against.
- Priority: High

**No end-to-end test for the search endpoint's filter/sort/paginate composition:**
- What's not tested: interaction of `seats_open`, `min_easiness`, `confidence`, `sort`, and `offset`/`limit` across a multi-course result set.
- Files: `src/easy_a/api/routes/rankings.py`, `tests/api/test_rankings_api.py`
- Risk: pagination applied after Python-side filtering is easy to break silently.
- Priority: Medium

**Live-source drift is checked manually, not automatically:**
- What's not tested: whether checked-in fixtures still match upstream HTML. `docs/live-source-drift-2026-09-01.md` is a hand-written one-off audit, and it notes there is no checked-in ENC baseline at all.
- Files: `tests/fixtures/schedule_*.html`, `docs/live-source-drift-2026-09-01.md`
- Risk: parsers pass against stale fixtures while failing against the live source.
- Priority: Medium

**Frontend coverage is shallow:**
- What's not tested: `web/src/components/*` have no dedicated tests; only `web/src/App.test.tsx` and `web/src/api/rankings.test.ts` exist. `web/src/utils/rankings.ts` (formatting/derivation logic) is untested directly.
- Priority: Low

---

*Concerns audit: 2026-09-05*
