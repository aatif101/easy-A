# Phase 04: MVP1-P1 — Grade→course attribution fix - Pattern Map

**Mapped:** 2026-09-20
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7 (the new vertical test uses a composite analog)
**Context basis:** `04-RESEARCH.md`; no `CONTEXT.md` exists, and the user chose to plan from roadmap, requirements, and research

## File Classification

| New/Modified File | Role | Data Flow | Closest Tracked Analog | Match Quality |
|---|---|---|---|---|
| `src/easy_a/grades/parser.py` | utility/parser | file-I/O → transform/validation | existing `src/easy_a/grades/parser.py` | exact extension |
| `src/easy_a/grades/ingest.py` | service | file-I/O → batch CRUD | existing `src/easy_a/grades/ingest.py` plus `src/easy_a/schedule/ingest.py` | exact role, composite behavior |
| `src/easy_a/quality/checks.py` | service/utility | database read → batch findings | existing `_check_grades()` in `src/easy_a/quality/checks.py` | exact extension; recommended guard |
| `tests/grades/test_parser.py` | test | generated file-I/O → transform | existing `tests/grades/test_parser.py` | exact extension |
| `tests/grades/test_ingest.py` | test | generated file-I/O → CRUD | existing `tests/grades/test_ingest.py` plus `tests/conftest.py` | exact extension |
| `tests/test_grade_course_attribution.py` | vertical integration/API test | file-I/O → CRUD → batch cache → request-response | `tests/test_grade_schedule_integration.py`, `tests/refresh/test_rankings_cache_refresh.py`, `tests/api/test_rankings_search_sql.py` | composite role-match |
| `tests/quality/test_checks.py` | test | database seed → batch findings | existing `tests/quality/test_checks.py` | exact extension; recommended guard |

The quality files are a recommended research addition. If the planner deliberately omits the
`unattributed_grade_row` guard, omit both `src/easy_a/quality/checks.py` and its paired test; do not
plan one without the other.

Files intentionally unchanged: `src/easy_a/common/lookups.py`, `src/easy_a/analytics/queries.py`,
the scoring modules, `src/easy_a/rankings/cache.py`, and `src/easy_a/refresh/service.py`. They are
dependencies/consumers whose existing behavior should be exercised, not rewritten. No model or
Alembic change is needed because `GradeDistribution.course_id` already exists.

## Pattern Assignments

### `src/easy_a/grades/parser.py` (utility/parser, file-I/O → transform)

**Analog:** the file's current workbook-wide validation path.

**Imports and typed error pattern** (`src/easy_a/grades/parser.py:1-10`, `:35-50`):

```python
from collections.abc import Iterable, Sequence
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, field_validator

class GradeRowValidationError(BaseModel):
    row_number: int
    course: str
    message: str

    model_config = ConfigDict(frozen=True)

class GradeWorkbookValidationError(ValueError):
    def __init__(self, errors: Sequence[GradeRowValidationError], records_seen: int) -> None:
        self.errors = tuple(errors)
        self.records_seen = records_seen
```

**Core fail-closed aggregation pattern** (`src/easy_a/grades/parser.py:145-219`):

```python
records: list[ParsedGradeDistribution] = []
errors: list[GradeRowValidationError] = []

for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):
    # ... identify a real section row ...
    records_seen += 1
    try:
        counts = {
            bucket: _cell_to_int(row[columns[bucket]], row_number, bucket)
            for bucket in GRADE_BUCKETS
        }
        total_grades = _cell_to_int(row[columns["total_grades"]], row_number, "Total Grades")
    except ValueError as exc:
        errors.append(
            GradeRowValidationError(
                row_number=row_number,
                course=course_text,
                message=str(exc),
            )
        )
        continue

if errors:
    raise GradeWorkbookValidationError(errors, records_seen=records_seen)
```

Keep this aggregate-all-invalid-rows behavior. Change only the canonical count conversion policy:
blank `A/B/C/D/F/I/S/U/W/O` or `Total Grades` must raise a row/column-specific `ValueError` whose
reason says the semantics are unverified. Percentage columns remain ignored and may stay blank.

**Numeric validation to preserve** (`src/easy_a/grades/parser.py:250-283`):

```python
def _cell_to_int(value: Any, row_number: int, column_name: str) -> int:
    if _is_empty_cell(value):
        return 0  # Phase 04 replaces this branch with an explicit failure.
    if isinstance(value, bool):
        raise ValueError(f"{column_name} contains a boolean at row {row_number}")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        float_value = float(value)
        if float_value.is_integer():
            return int(float_value)
        raise ValueError(f"{column_name} contains non-integer value {value!r} at row {row_number}")
    # String parsing and nonnumeric/noninteger failures continue below.

def _is_empty_cell(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False
```

Reuse `_is_empty_cell()`; do not add engine-specific `None` checks or nullable/suppressed counts.
Explicit integer `0` remains valid. Do not change grade buckets, totals, parsed identity, or the
frozen scoring inputs.

---

### `tests/grades/test_parser.py` (test, generated file-I/O → transform)

**Analog:** current generated-XLSX helper and validation assertions.

**Fixture pattern** (`tests/grades/test_parser.py:114-121`, `:128-166`):

```python
def _write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)

def _grade_row(..., b: object = 0, ..., total: object = 0) -> list[object]:
    return [course, a, None, b, None, ..., total]
```

Continue generating workbooks under `tmp_path`; never add a tracked XLSX. The `None` values after
each count are percentage cells and deliberately ignored. Replace
`test_empty_count_cells_are_zero` (`tests/grades/test_parser.py:99-111`) with a failure assertion
that checks row, column, and the unverified-semantics reason, and retain/add a separate success
case containing explicit numeric zeros in every canonical count bucket.

**Error assertion pattern** (`tests/grades/test_parser.py:86-96`):

```python
with pytest.raises(GradeWorkbookValidationError) as exc_info:
    parse_grade_workbook(workbook_path)

assert "count sum 5 does not equal Total Grades 99" in str(exc_info.value)
```

Use the same pattern for both a blank bucket and blank `Total Grades`. Do not assert or invent a
source label such as `suppressed`; the verified statement is only that blank semantics are unknown.

---

### `src/easy_a/grades/ingest.py` (service, file-I/O → batch CRUD)

**Primary analogs:** current grade upsert for identity/provenance; schedule ingest for canonical
course resolution and domain-error translation.

**Canonical lookup contract** (`src/easy_a/common/lookups.py:33-49`):

```python
def resolve_course_id(session: Session, subject: str, number: str) -> int:
    normalized_subject = subject.strip().upper()
    normalized_number = number.strip().upper()
    if not normalized_subject or not normalized_number:
        raise CoreDataLookupError("Course subject and number must be non-empty.")

    course_id = session.execute(
        select(Course.id)
        .where(Course.subject == normalized_subject, Course.number == normalized_number)
        .order_by(Course.catalog_edition.desc())
        .limit(1)
    ).scalar_one_or_none()
    if course_id is None:
        raise CoreDataLookupError(
            f"Course {normalized_subject} {normalized_number} is not present in the courses table."
        )
    return course_id
```

Import and reuse `CoreDataLookupError` and `resolve_course_id`; do not duplicate normalization or
catalog-edition selection.

**Error translation analog** (`src/easy_a/schedule/ingest.py:57-70`):

```python
for row in rows:
    try:
        course_id = resolve_course_id(session, row.subject, row.course_number)
    except CoreDataLookupError as exc:
        raise ScheduleIngestError(str(exc)) from exc
```

Copy the lookup/error contract, **not this placement**. Grade ingest must first collect the sorted
distinct `(record.subject, record.course_number)` keys and resolve all of them before entering the
upsert loop. An unresolved key must mark the `IngestRun` failed and leave the grade table
unchanged. Prefer a grade-domain error that reports all unresolved keys deterministically. The
existing CLI commits unexpected exception paths (`src/easy_a/grades/cli.py:23-38`), so the ingest
service itself must set the failed-run fields before raising.

**Identity-preserving upsert pattern** (`src/easy_a/grades/ingest.py:90-119`):

```python
for record in records:
    existing = session.execute(
        select(GradeDistribution).where(
            GradeDistribution.term_id == term.id,
            GradeDistribution.crn == record.crn,
            GradeDistribution.source == source,
        )
    ).scalar_one_or_none()

    if existing is None:
        session.add(_new_grade_distribution(...))
        inserted += 1
        continue

    if _grade_distribution_differs(...):
        _apply_grade_distribution(...)
        updated += 1
```

Keep `(term_id, crn, source)` as the lookup/uniqueness boundary. Resolve a mapping once, then pass
the resolved `course_id` to `_new_grade_distribution`, `_apply_grade_distribution`, and
`_grade_distribution_differs`. Do not add `course_id` to identity and do not delete/reinsert rows.

**Loaded-instance update/diff pattern** (`src/easy_a/grades/ingest.py:130-194`):

```python
distribution = GradeDistribution(
    term_id=term.id,
    crn=record.crn,
    course_id=None,  # replace with the pre-resolved ID
    source=source,
    source_hash=source_hash,
    total_grades=record.total_grades,
)
_apply_grade_distribution(distribution, record, source_hash)

return (
    distribution.section_number_raw != record.section_number_raw
    # ... all existing fields ...
    or distribution.source_hash != source_hash
)
```

Set `distribution.course_id = course_id` in apply, and include
`distribution.course_id != course_id` in the diff. This is what makes a same-key re-import repair
an existing null-attributed row and increment `records_updated` without creating a duplicate.
Keep SHA-256 file provenance (`src/easy_a/grades/ingest.py:122-127`) unchanged.

**Failure ledger pattern** (`src/easy_a/grades/ingest.py:61-80`, `:197-207`):

```python
except GradeWorkbookValidationError as exc:
    _mark_run_failed(
        run=run,
        message=str(exc),
        records_seen=exc.records_seen,
        records_failed=len(exc.errors),
    )
    session.flush()
    raise

def _mark_run_failed(...):
    run.status = "failed"
    run.finished_at = datetime.now(UTC)
    run.records_seen = records_seen
    run.records_failed = records_failed
    run.error_message = message
```

Apply this to resolution failure. Do not silently skip unresolved rows or create placeholder
courses/null-attributed rows.

---

### `tests/grades/test_ingest.py` (test, generated file-I/O → CRUD)

**Analog:** current idempotency/failure tests, with canonical core-data seeding copied from the
shared fixture.

**Core-data seed pattern** (`tests/conftest.py:13-57`):

```python
with Session(engine) as session:
    session.add_all(
        [
            Term(id=1, banner_code="202701", name="Spring 2027", year=2027, season="Spring"),
            Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
            Course(
                id=10,
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            ),
        ]
    )
    session.commit()
```

The file's local `session` fixture currently creates empty tables
(`tests/grades/test_ingest.py:43-48`). Once resolution is required, seed the canonical course in
that fixture or use `db_session`; otherwise all existing positive imports will correctly fail.

**Idempotency/provenance assertion pattern** (`tests/grades/test_ingest.py:51-96`):

```python
first = ingest_grade_file(session, "202408", workbook_path)
second = ingest_grade_file(session, "202408", workbook_path)

distributions = session.execute(select(GradeDistribution)).scalars().all()
assert first.records_inserted == 1
assert second.records_inserted == 0
assert second.records_updated == 0
assert len(distributions) == 1
assert distributions[0].source_hash
```

Strengthen this with `distributions[0].course_id == mac.id`. Add three focused cases:

1. Parsed subject/number assigns the canonical course ID on insert.
2. Seed a same `(term_id, crn, source)` row with `course_id=None`; re-import updates that row,
   yields `records_updated == 1`, and leaves exactly one distribution.
3. Build a workbook with at least one resolvable and one missing course; assert the ingest run is
   failed and **zero** grade rows were inserted (preflight atomicity).

Continue using the local `_write_workbook()` (`tests/grades/test_ingest.py:148-155`) and explicit
numeric zeros in count cells. Percentage cells may remain `None`.

---

### `src/easy_a/quality/checks.py` (service/utility, database read → findings)

**Analog:** existing `_check_grades()` and `QualityFinding` construction.

**Pipeline wiring** (`src/easy_a/quality/checks.py:87-113`):

```python
findings = check_duplicate_section_identities(...)
findings.extend(_check_section_campus(term, sections, supported_campus))
findings.extend(_check_grades(session, term_row))
findings.extend(_check_orphan_instructor_observations(session))
# ...
return QualityReport.from_findings(..., findings=findings)
```

Put the null-attribution guard inside `_check_grades`; no new top-level orchestration is needed.

**Per-row finding pattern** (`src/easy_a/quality/checks.py:214-247`):

```python
distributions = session.scalars(
    select(GradeDistribution)
    .where(GradeDistribution.term_id == term.id)
    .order_by(GradeDistribution.crn, GradeDistribution.id)
).all()
for distribution in distributions:
    if count_sum != distribution.total_grades:
        findings.append(
            QualityFinding(
                check_id="grade_total_mismatch",
                severity=FindingSeverity.error,
                term=term.banner_code,
                crn=distribution.crn,
                source_record=f"grade_distribution:{distribution.id}",
                message="...",
            )
        )
```

Add one deterministic error finding per distribution whose `course_id is None`, using a stable
ID such as `unattributed_grade_row`, the same term/CRN/source-record fields, and a message that the
row cannot provide course historical analytics. Do not infer a course from CRN alone. Preserve
the existing historical term+CRN orphan check; the new guard diagnoses a different invariant.

---

### `tests/quality/test_checks.py` (test, database seed → findings)

**Analog:** existing grade finding tests and helper.

**Finding assertion pattern** (`tests/quality/test_checks.py:36-57`):

```python
db_session.add(_grade(crn="99999", total_grades=10))

report = run_quality_checks(db_session, "202701", as_of=NOW)

finding = _finding(report.findings, "orphan_grade_row")
assert finding.severity == "error"
assert finding.crn == "99999"
```

**Grade factory pattern** (`tests/quality/test_checks.py:258-277`):

```python
def _grade(*, crn: str, total_grades: int) -> GradeDistribution:
    return GradeDistribution(
        term_id=1,
        crn=crn,
        course_id=10,
        # explicit grade counts and source provenance
        source=f"synthetic-{crn}",
        source_hash="synthetic",
    )
```

Allow the helper to accept `course_id: int | None = 10`, seed `course_id=None`, then assert the
new finding's ID, error severity, term, CRN, and source record. Add a positive control showing an
attributed row produces no `unattributed_grade_row` finding.

---

### `tests/test_grade_course_attribution.py` (vertical integration/API test)

**Composite analogs:** generated workbook from `tests/test_grade_schedule_integration.py`, cache
freshness from `tests/refresh/test_rankings_cache_refresh.py`, and TestClient dependency override
from `tests/api/test_rankings_search_sql.py`.

**Generated workbook pattern** (`tests/test_grade_schedule_integration.py:42-52`, `:81-112`):

```python
workbook_path = tmp_path / "fall_2024_89033.xlsx"
_write_grade_workbook(workbook_path)
ingest_grade_file(db_session, "202408", workbook_path)

def _write_grade_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    worksheet.append(["MAC-1105 -001-C (89033)", 10, None, 4, None, ..., 15])
    workbook.save(path)
```

Copy the temp-workbook shape, but **do not** call `ingest_schedule_html` for term `202408` and do
not create a historical `Section` for CRN `89033`. The legacy analytics fallback joins historical
sections, so such a fixture would hide a broken direct `GradeDistribution.course_id` path.

**Cache-consumer proof pattern** (`tests/refresh/test_rankings_cache_refresh.py:66-91`):

```python
refresh_targets(..., term="202701", ...)

refreshed = db_session.scalar(
    select(SectionRankingCache).where(SectionRankingCache.crn == "13173")
)
assert refreshed is not None
assert refreshed.effective_n > 0
assert hydrate_ranking(db_session, refreshed, as_of=as_of).model_dump(
    mode="json"
) == rank_section(
    db_session, term="202701", crn="13173", as_of=as_of
).model_dump(mode="json")
```

For this phase, invoke the narrower existing consumer API directly:

```python
refresh_section_rankings(session, term="202701")
```

(`src/easy_a/rankings/cache.py:73-81`). Seed two Spring 2027 sections: one for the course in the
historical workbook and one no-history control. Assert the stored grade's `course_id` first, then
assert on-demand and cache-backed behavior:

- history course: `effective_n > 0` and `score_source == "course"`;
- no-history control: `effective_n == 0` and `score_source == "global"`;
- cached search values agree with `rank_section()` for the same CRN.

**Request-response fixture pattern** (`tests/api/test_rankings_search_sql.py:22-52`):

```python
engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
factory = sessionmaker(bind=engine, expire_on_commit=False)

def override_get_db_session() -> Generator[Session, None, None]:
    with factory() as session:
        yield session

app.dependency_overrides[get_db_session] = override_get_db_session
with TestClient(app) as client:
    yield client
app.dependency_overrides.clear()
```

Use the shared `StaticPool` factory so ingestion/cache writes and the TestClient request see the
same in-memory database. Search with the public route pattern
(`tests/api/test_rankings_search_sql.py:65-76`):

```python
response = client.get(
    "/api/v1/rankings/search",
    params={"term": "202701", "sort": "course"},
)
assert response.status_code == 200
```

Inspect `response.json()["items"]` by CRN and assert both honest evidence states. This test must
exercise the real parser, ingest, analytics, cache rebuild, and API search; do not seed
`GradeDistribution` or `SectionRankingCache` directly.

## Shared Patterns

### Canonical identity and normalization

**Source:** `src/easy_a/common/lookups.py:33-49`

Apply to grade ingest. Parsed `subject`/`course_number` are normalized by the shared lookup, and
the chosen ID is the newest catalog edition. No grade-specific matcher or placeholder course.

### Transaction ownership and failure reporting

**Sources:** `src/easy_a/grades/ingest.py:32-87`, `src/easy_a/grades/cli.py:23-38`

Services flush but do not commit; CLI owns commit. Because the CLI commits failure ledgers even
when an exception is raised, resolution must occur before grade upserts and the run must be marked
failed before raising. Tests should inspect both the failed run and absence of grade mutations.

### Deduplication and provenance

**Source:** `src/easy_a/grades/ingest.py:100-127`

Keep same-source identity `(term_id, crn, source)` and SHA-256 `source_hash`. `course_id` is an
attributed property, not identity. A re-import repairs the loaded mapped instance in place.

### Validation and unavailable-state language

**Sources:** `src/easy_a/grades/parser.py:145-219`, `src/easy_a/quality/checks.py:214-272`

Reject invalid workbooks explicitly and report stored invariant violations as typed findings.
Blank canonical counts are “unverified semantics,” not asserted zero or asserted suppression.

### Test data safety

**Sources:** `tests/grades/test_parser.py:114-121`,
`tests/test_grade_schedule_integration.py:81-112`

All XLSX inputs are generated beneath `tmp_path`. Never add `.xlsx`/`.xls` fixtures to Git.
Use explicit numeric zero for canonical count cells and reserve `None` for ignored percentage
cells or deliberate blank-rejection cases.

### Cache and search boundary

**Sources:** `src/easy_a/rankings/cache.py:73-117`,
`src/easy_a/api/routes/rankings.py:51-70`, `:109-206`

Historical import does not update search by itself. Rebuild `section_rankings` for the current
ranking term, then test `/api/v1/rankings/search`, which reads the cache. Do not change the cache,
search contract, analytics query, or scoring implementation in this phase.

### Authentication

None. This application has no auth/account scope, and these operator ingestion and public read
paths do not add guards.

## No Single-File Analog

| File | Role | Data Flow | Resolution |
|---|---|---|---|
| `tests/test_grade_course_attribution.py` | vertical integration/API test | file-I/O → CRUD → cache → request-response | No existing test spans all four seams. Compose the three tracked test patterns above; specifically omit the historical-section setup from `tests/test_grade_schedule_integration.py`. |

Every target has an actionable tracked analog; the table records only that the new vertical proof
requires composition rather than copying one test wholesale.

## Planner Guardrails

- Do not modify scoring, confidence, analytics fallback logic, seats, GenEd, modality, or signals.
- Do not add a migration or make grade counts nullable.
- Do not infer course identity from CRN alone; CRNs are term-scoped.
- Do not resolve courses during the mutation loop; preflight all distinct course keys first.
- Do not set `course_id` only on inserts; include apply and diff paths so re-import backfills nulls.
- Do not test direct attribution with a matching historical `Section`.
- Do not claim blank means suppressed or zero without external source evidence.
- Do not assume a historical grade import refreshes Spring 2027 search; rebuild the current-term cache.
- Do not commit raw or synthetic workbook files.

## Metadata

**Analog search scope:** `src/easy_a/{grades,schedule,common,quality,rankings,api,refresh}` and
`tests/{grades,quality,refresh,api}` plus root integration tests

**Tracked-source gate:** every analog named above was verified with `git ls-files`; no `.gsd`,
plugin-cache, virtualenv, or runtime-mirror path is used.

**Strong analog groups:** 5 — parser validation, grade upsert, canonical lookup, quality findings,
and composite vertical cache/API verification

**Pattern extraction date:** 2026-09-20
