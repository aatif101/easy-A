# Phase 7: MVP1-P4 — Full-scale cache build + search performance — Pattern Map

**Mapped:** 2026-09-22  
**Scope source:** `07-RESEARCH.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`; no Phase 7 `CONTEXT.md` exists.  
**Files classified:** 9 likely new or modified files. **Analogs found:** 9/9 (one conditional migration). These are planning candidates, not a mandated file list.

## File Classification

| New/modified file | Role | Data flow | Closest analog | Match |
|---|---|---|---|---|
| `src/easy_a/analytics/queries.py` | service | batch, transform | Same file, `_fetch_course_grade_observations` and fallback helpers | exact |
| `src/easy_a/rankings/cache.py` | service/model | batch, database write | Same file, `refresh_section_rankings` | exact |
| `src/easy_a/quality/checks.py` | service | batch, transform | Same file, `_check_analytics` | exact |
| `src/easy_a/api/routes/rankings.py` | route/controller | request-response | Same file, `search_rankings` | exact |
| `scripts/benchmark_rankings_search.py` | utility | batch, database read/diagnostics | Same file, synthetic benchmark | exact |
| `migrations/versions/0004_*.py` (only if measurements justify indexes) | migration | schema change | `migrations/versions/0003_create_section_rankings.py` | role match |
| `tests/rankings/test_cache_parity.py` and `tests/analytics/test_queries.py` | test | batch, transform | Same files, existing scoring parity and fallback tests | exact |
| `tests/api/test_rankings_search_sql.py` | test | request-response | Same file, SQL search contract tests | exact |
| New focused benchmark test, if needed | test | diagnostics | `tests/api/test_rankings_search_sql.py` query capture and benchmark's `_percentile` | partial |

## Pattern Assignments

### `src/easy_a/analytics/queries.py` — batched analytics

**Analog:** same file, lines 46-87, 197-315, 317-415. Keep public per-course functions for on-demand callers and introduce an internal batch path for whole-term consumers if needed.

**Imports and data types** (lines 3-28): use `Sequence`, frozen `@dataclass`, SQLAlchemy `select`/`and_`/`or_`, and existing `GradeObservation`, `HistoricalGradeAggregate`, `ScoreConfig`, `HistoricalOutcomeStats`. The scoring machinery is imported from `easy_a.analytics.scoring`, not duplicated.

**Current core and fallback** (lines 64-87, 197-258):
```python
course_aggregate = _aggregate_for_course_ids(session, course_ids, before_term_code=before_term_code, config=score_config)
subject_aggregate = _aggregate_for_course_ids(session, subject_course_ids, before_term_code=before_term_code, config=score_config)
global_aggregate = _aggregate_for_course_ids(session, None, before_term_code=before_term_code, config=score_config)
return _stats_with_course_subject_global_fallback(
    course_aggregate=course_aggregate,
    subject_aggregate=subject_aggregate,
    global_aggregate=global_aggregate,
    config=score_config,
)
```
The subject input excludes the current course (`_subject_course_ids_excluding`, lines 394-404). Reuse `_stats_with_course_subject_global_fallback` and `compute_historical_outcome_stats`; do not change smoothing, source, confidence, or effective-N semantics.

**Historical row matching and validation** (lines 274-315): the query joins `Term` by grade term, outer-joins `Section` on **term and CRN**, matches either `GradeDistribution.course_id` or joined `Section.course_id`, and applies `Term.banner_code < normalize_banner_term_code(before_term_code)`. `_mapped_instructor_section_ids` (407-415) and `_grade_observation` (356-380) preserve the mapped-instructor flag and all ten grade buckets. A batch query must preserve these exact predicates and observation construction.

**Instructor branch** (lines 99-132, 174-192): unusable instructor returns `None`; instructor evidence is aggregated separately, smoothed with the course prior, and adopted only when `has_sufficient_instructor_course_evidence` succeeds. This is a branch to preserve, not a new score formula.

### `src/easy_a/rankings/cache.py` — whole-term cache write

**Analog:** same file, lines 73-203. `refresh_section_rankings(session, *, term, subject=None, course_number=None, config=None) -> int` owns the caller's transaction and calls `session.flush()` without commit (lines 73-81, 202-203). It validates paired subject/course input (93-95), normalizes the term (96), selects `(Section, Course, Term)` in deterministic course/CRN order (97-109), and groups unique course keys (117-130).

**Integration seam** (lines 110-130):
```python
# Imports stay inside the function to avoid the models/cache circular import.
from easy_a.analytics.queries import get_current_section_historical_analytics
from easy_a.signals.resolver import resolve_section_signals

section_course_rows = list(session.execute(stmt).all())
analytics_by_crn = {}
course_keys = sorted({(course.subject, course.number) for _, course, _ in section_course_rows})
for course_subject, number in course_keys:
    for row in get_current_section_historical_analytics(...):
        analytics_by_crn[row.crn] = row.stats
```
When inserting a batch API here, retain the lazy import and the section-to-stats mapping contract. The existing row payload (158-194) stores **non-seat** values with source/provenance; update-or-insert by section ID (132-138, 195-200). Do not cache seat snapshots as scoring inputs or display fields.

**Read hydration** (206-321): `hydrate_ranking` receives a provided snapshot or loads latest by `(observed_at DESC, id DESC)` (231-239), falls back to section columns (259-288), and emits explicit unavailable provenance. The search route supplies page snapshots to avoid an extra snapshot query per row.

### `src/easy_a/quality/checks.py` — shared analytics consumer

**Analog:** `_check_analytics`, lines 431-474. It builds sorted unique `(subject, number)` keys, maps `row.crn` to stats, and emits `no_historical_analytics` when stats are absent/empty and `low_confidence_ranking` for low confidence. If a shared batch function replaces the loop at 440-447, keep findings, severity, source record, and honest no-history behavior unchanged.

### `src/easy_a/api/routes/rankings.py` — SQL search

**Analog:** same file, lines 51-213. Preserve FastAPI `BannerTerm` and bounded `Query` parameters (51-65), uppercase normalization (66-69, 209-213), SQLAlchemy expressions, `RankingsSearchResponse`, and response shape. No auth mechanism exists in this API.

**Latest seat semantics** (71-108): latest snapshot orders by `observed_at DESC, id DESC`; effective seats use snapshot value if a snapshot exists, otherwise `Section.seats_remaining`. The existing window over all snapshots is a performance candidate, but the tie break and fallback are contract behavior.

**Filter, sort, and page contract** (109-206):
```python
filtered = select(SectionRankingCache, Section, ...).join(
    Section, Section.id == SectionRankingCache.section_id
).outerjoin(latest_snapshot, ...).where(SectionRankingCache.term == term)
# Apply subject, course, GenEd EXISTS, delivery method, seats-open, score floor, confidence.
course_tiebreak = (
    SectionRankingCache.subject.asc(),
    SectionRankingCache.course_number.asc(),
    SectionRankingCache.crn.asc(),
)
total = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0
rows = session.execute(filtered.order_by(*order_by).limit(limit).offset(offset)).all()
```
The GenEd filter uses correlated `exists` (133-143); sort variants are enumerated at 160-170, including live-seat sort. Rows are hydrated with the selected snapshot and section seat columns (174-199). If count and page SQL are split, derive both from the same predicate set, and include latest-seat lookup in count only when `seats_open` requires it.

### `scripts/benchmark_rankings_search.py` — synthetic and live timing

**Analog:** same file, lines 1-20, 86-193, 196-231, 373-447. Keep `argparse` typed term/positive-int validation (460-474), `main` mode selection (130-141), `get_engine()` resolution (161-169), and explicit `engine.dispose()` (192-193). Synthetic PostgreSQL runs create a throwaway schema inside a transaction and always roll it back (171-191). A live mode must be a separate read-only path rather than using `_seed_and_measure`.

**Timing and reporting** (215-231, 373-447):
```python
for query in _representative_queries(iterations=iterations, subjects=subjects_sample):
    start = time.perf_counter()
    search_rankings(term=term, session=session, subject=query.subject,
                    seats_open=query.seats_open, min_easiness=query.min_easiness,
                    sort=query.sort, limit=query.limit, offset=query.offset)
    durations.append(time.perf_counter() - start)
```
Reuse `_representative_queries` and `_percentile`. `_report` currently labels data as a synthetic fixture and derives Supabase from the optional raw `url` (392-435). For live reporting, label the actual dataset and classify the **resolved `engine.url` host/port** without printing it or a credential-bearing URL. Keep fixture and live labels distinct.

### `migrations/versions/0004_*.py` — measured indexes only

**Analog:** `0003_create_section_rankings.py`, lines 1-21, 62-79. Use a new revision with `down_revision = "0003_create_section_rankings"` only after an `EXPLAIN (ANALYZE, BUFFERS)` and wall-time comparison warrants an index. Follow `op.create_index(op.f(...), table, columns, unique=False)` and a reversible `downgrade()` using `op.drop_index`. Migration 0003 already creates six cache indexes (62-75); avoid duplicating them. Also check the actual Alembic head before assigning revision number.

### Tests

**Analytics parity:** `tests/analytics/test_queries.py:101-163` proves the target course is excluded from the subject prior and comparison courses contribute; lines 166-252 cover staff/unmapped instructors and term/CRN identity. Extend with batch-vs-public exact stats and query-count assertions for multiple courses.

**Cache parity:** `tests/rankings/test_cache_parity.py:31-79` compares cached hydration to on-demand ranking with fixed `as_of`; lines 82-172 cover all score sources, confidence labels, prior levels, and zero-evidence fallback. `tests/refresh/test_rankings_cache_refresh.py:23-92` proves a grade import changes cache stats and preserves full ranking parity. Use these for batch integration.

**Search parity and query budget:** `tests/api/test_rankings_search_sql.py:65-207` covers every sort with deterministic ties, complete paging, two SQL selects, live snapshot/section/unavailable seat states, every filter, and literal SQL metacharacters. Extend this file for any count/page split or latest-seat rewrite. The SQL capture pattern is `event.listen(engine, "before_cursor_execute", record_statement)` in lines 104-138, removed in `finally`.

**Benchmark tests:** No dedicated benchmark test file exists. A new focused test can exercise a sanitized resolved-engine label and live mode without credentials; use the existing SQL capture/fixture approach above, and do not require hosted credentials for unit tests.

## Shared Patterns

- **Transactions:** cache refresh flushes but does not commit (`cache.py:73-81,202-203`); synthetic benchmark rolls back (`benchmark_rankings_search.py:171-193`). Let the caller own commit/rollback.
- **Scoring:** `queries.py:197-258` is the single fallback/score branch; `analytics/grades.py` remains the weighted grade aggregation source. Batch/hoist inputs and reuse these functions.
- **Provenance and unavailable states:** cache payload keeps historical and section provenance (`cache.py:149-194`); hydration emits seat source/unavailable states (`cache.py:241-289`). `effective_n=0`/global is not course evidence (`test_cache_parity.py:73-79`).
- **Validation and SQL safety:** FastAPI bounds are in `rankings.py:51-65`; filters are SQLAlchemy bound expressions (`rankings.py:127-153`); literal metacharacters are tested (`test_rankings_search_sql.py:197-207`).
- **Diagnostics:** measure full request wall time with `time.perf_counter()` (`benchmark_rankings_search.py:215-231`) and use compiled SQL `EXPLAIN (ANALYZE, BUFFERS)` as a diagnosis of count/page plans. Keep secret URLs and raw grade rows out of output.

## No Close Analog

| Candidate | Reason | Source for planner |
|---|---|---|
| Separate read-only live benchmark mode | Existing harness has only synthetic fixture and SQLite smoke modes; no read-only live path | Extend benchmark CLI, timing, and report patterns above; research Pattern 5 |
| PostgreSQL plan capture/report helper, if introduced | No dedicated repository helper for `EXPLAIN` was found | Research Pattern 1/3; keep it parameterized and sanitized |

## Metadata

**Search scope:** `src/easy_a/{analytics,rankings,quality,api/routes}`, `migrations/versions`, `scripts`, and matching `tests`. Project-local `.codex/skills` and `.agents/skills` directories are absent.  
**Representative analogs read:** analytics queries, cache, quality checks, rankings route, benchmark, migration 0003, and focused analytics/cache/search/refresh tests.  
**Date:** 2026-09-22.
