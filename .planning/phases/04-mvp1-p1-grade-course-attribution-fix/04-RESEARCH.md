# Phase 04: MVP1-P1 — Grade→course attribution fix - Research

**Researched:** 2026-09-20
**Domain:** Historical grade ingestion, canonical course attribution, derived ranking-cache freshness
**Confidence:** HIGH for repository behavior and implementation path; LOW for upstream blank-cell semantics

## Project Constraints (from AGENTS.md)

- Preserve the existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vite/Tailwind application; this is a brownfield correction, not a rewrite. [VERIFIED: AGENTS.md:14-20]
- Do not change the historical scoring formula, shrinkage, confidence labels, or course/instructor-course fallback. Seats, GenEd, modality, and syllabus signals remain score-isolated. [VERIFIED: AGENTS.md:46-53]
- Preserve grade identity and provenance by real term + CRN + source; duplicate imports must not double-count. [VERIFIED: AGENTS.md:54-55]
- Never commit raw grade exports; use generated workbooks under `tmp_path` for tests and keep operator files outside Git. [VERIFIED: AGENTS.md:56-56; README.md:632-649; .gitignore:12-16]
- A global-prior result with `effective_n = 0` is not evidence-backed course history, and absent or unsupported evidence must remain explicit. [VERIFIED: AGENTS.md:49-52]
- Use bounded USF access only; this phase does not need any public-source request or scrape. [VERIFIED: AGENTS.md:57-58]
- Planning artifacts belong in `.planning/`; archival `docs/` proposals and `_superseded/` plans are not current scope. [VERIFIED: AGENTS.md:62-82,84-92]
- Verify `origin/main` before execution and preserve unrelated/untracked work. At research time, `HEAD` and `origin/main` both resolved to `cf0f195b50e6e8ae1e8a038fa7db3f2027a433dd`; execution must fetch again rather than treating this as durable state. [VERIFIED: AGENTS.md:59-60; local git probe 2026-09-20]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-GRADES-01 | Ingested Tampa courses have real historical grade data and easiness is computed from it; courses still lacking history remain explicitly lacking it. | Resolve every parsed grade row to the existing canonical `Course`; update null-attributed rows on same-key re-import; preserve term/CRN/source uniqueness; rebuild the current-term derived cache; verify one history and one no-history course through the search response. [VERIFIED: .planning/REQUIREMENTS.md:169-178] |
</phase_requirements>

## Summary

The parser already produces normalized `subject` and `course_number` for every accepted section row, but the ingestion layer discards both and constructs `GradeDistribution(course_id=None)`. The database already has a nullable `course_id` foreign key and the shared `resolve_course_id()` lookup used by schedule and syllabus ingestion. The smallest correct repair is therefore an ingestion change, not a schema or scoring change: resolve each distinct parsed `(subject, course_number)` before row mutation, pass the resolved ID through insert/update/diff, and let a same-term/CRN/source re-import repair an existing null `course_id` without inserting another row. [VERIFIED: src/easy_a/grades/parser.py:70-98,193-213; src/easy_a/grades/ingest.py:90-119,130-194; src/easy_a/common/lookups.py:33-49; src/easy_a/models/core.py:87-131]

The analytics cohort query already accepts direct `GradeDistribution.course_id` attribution and retains the historical term+CRN `Section.course_id` path as a compatibility fallback. Direct attribution is essential when historical schedule rows were never ingested. A test that also ingests a matching historical `Section` would hide this bug and is therefore insufficient. [VERIFIED: src/easy_a/analytics/queries.py:274-314]

Two adjacent behaviors must be planned explicitly. First, upstream blank-cell semantics are unresolved: the current parser silently converts blank count cells to zero, while no approved real/sample export is available in the repository or this environment to prove that this means true zero rather than suppression. The safe Phase 04 behavior is fail-closed row/workbook validation for blank canonical count cells, with a reason that says their semantics are unverified; do not invent a persisted `suppressed` meaning or nullable-count schema. Second, rankings search reads `section_rankings`, so importing Fall 2024 grades does not refresh Spring 2027 search. After historical imports, run the existing cache-only current-term refresh path and prove both on-demand and cache-backed results. [VERIFIED: src/easy_a/grades/parser.py:244-283; tests/grades/test_parser.py:99-111; src/easy_a/api/routes/rankings.py:109-206; src/easy_a/refresh/service.py:69-91,230-232]

**Primary recommendation:** pre-resolve and upsert canonical `course_id`, fail closed on unresolved course or blank canonical count cells, then prove historical import → current-term cache rebuild → search response with `effective_n > 0` while a no-history control remains `0`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Parse subject/course and grade buckets | API / Backend (ingestion) | — | XLSX interpretation and validation occur before persistence. [VERIFIED: src/easy_a/grades/parser.py:136-219] |
| Resolve canonical course identity | API / Backend (ingestion) | Database / Storage | The backend uses the shared lookup; the FK persists the result. [VERIFIED: src/easy_a/common/lookups.py:33-49; src/easy_a/models/core.py:104-131] |
| Preserve term/CRN/source dedup and provenance | Database / Storage | API / Backend | The database unique constraint enforces identity; ingestion controls source and SHA-256 hash updates. [VERIFIED: src/easy_a/models/core.py:87-123; src/easy_a/grades/ingest.py:100-127] |
| Select historical grade evidence | API / Backend (analytics) | Database / Storage | Analytics filters prior terms and accepts direct grade course IDs or historical section joins. [VERIFIED: src/easy_a/analytics/queries.py:274-314] |
| Refresh derived current-term ranking data | API / Backend (refresh/cache) | Database / Storage | `section_rankings` is recomputed from canonical tables and stored for search. [VERIFIED: src/easy_a/rankings/cache.py:73-203; src/easy_a/refresh/service.py:88-91,230-232] |
| Return search results | API / Backend | Database / Storage | Search reads `section_rankings` and hydrates live seats; it does not recompute historical analytics. [VERIFIED: src/easy_a/api/routes/rankings.py:109-206] |

## Standard Stack

No new package is needed. Preserve the locked repository stack and existing APIs.

### Core

| Library | Version | Purpose | Why Standard Here |
|---------|---------|---------|-------------------|
| SQLAlchemy | 2.0.52 | ORM lookup, mapped-instance update, FK/unique constraints | Already implements every relevant persistence path; official 2.0 docs support `select()` with `Session.execute()`/`scalars()` and unit-of-work updates on loaded instances. [VERIFIED: uv.lock:1125-1133] [CITED: https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html] |
| pandas | 3.0.5 | Read XLSX into `DataFrame` with `dtype=object` | Existing parser dependency; official docs distinguish object preservation from default NA detection. [VERIFIED: uv.lock:798-807; src/easy_a/grades/parser.py:136-142] [CITED: https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html] |
| openpyxl | 3.1.5 | XLSX engine and generated test workbooks | Existing parser engine and test-fixture writer. [VERIFIED: uv.lock:777-786; src/easy_a/grades/parser.py:136-142; tests/grades/test_parser.py:114-121] |
| Pydantic | 2.13.5 | Immutable parsed-row models and field normalization | Existing `ParsedGradeDistribution` contract. [VERIFIED: uv.lock:932-944; src/easy_a/grades/parser.py:53-98] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Generated XLSX unit/integration tests | Use `tmp_path` so no raw or synthetic workbook is committed. [VERIFIED: uv.lock:1045-1058; tests/grades/test_ingest.py:51-98] |
| Existing refresh/cache services | Repository code | Rebuild derived current-term rankings | Use after historical imports; do not create a second cache implementation. [VERIFIED: src/easy_a/refresh/service.py:41-118,230-232] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Shared `resolve_course_id()` | Duplicate a grade-specific subject/number query | Reject: it risks different normalization/catalog-edition selection from schedule ingestion. [VERIFIED: src/easy_a/common/lookups.py:33-49; src/easy_a/schedule/ingest.py:57-88] |
| Re-import to repair same-key null rows | One-off SQL joining only term+CRN to `sections` | Useful only where a verified historical section exists; it cannot recover parsed subject/number from a grade row because those fields are not stored. Re-import is the evidence-preserving repair. [VERIFIED: src/easy_a/models/core.py:104-123] |
| Fail closed on blank canonical counts | Continue blank→0 or invent a suppression threshold | Reject both until source semantics are evidenced; zero and suppressed are materially different inputs to the frozen score. [VERIFIED: src/easy_a/grades/parser.py:250-274; src/easy_a/analytics/grades.py:77-95] |
| Explicit current-term cache-only refresh | Auto-refresh every later term inside grade ingestion | Prefer explicit orchestration: it preserves grade-ingest separation, avoids circular coupling, and allows one rebuild after a batch of historical files. [VERIFIED: src/easy_a/refresh/service.py:41-91; src/easy_a/rankings/cache.py:73-81] |

**Installation:** none.

## Package Legitimacy Audit

Not applicable. Phase 04 should install no external packages and should use only dependencies already locked in `uv.lock`.

## Architecture Patterns

### System Architecture Diagram

```text
Operator-supplied historical XLSX outside Git
        |
        v
pandas/openpyxl reader
        |
        v
ParsedGradeDistribution
  subject + course_number + term argument + CRN + counts
        |
        +--> blank/non-numeric/count-total validation fails closed
        |
        v
preflight distinct (subject, number) -> resolve_course_id()
        |
        +--> unresolved course -> failed ingest, no grade mutations
        |
        v
upsert by (term_id, CRN, source)
  insert or update course_id + counts + source_hash
        |
        v
GradeDistribution canonical history
        |
        v
analytics query for terms before 202701
  direct GradeDistribution.course_id path
  OR legacy term+CRN Section.course_id path
        |
        v
current-term cache-only refresh
        |
        v
section_rankings for 202701
        |
        +--> course with evidence: effective_n > 0, score_source="course"
        |
        +--> control without evidence: effective_n = 0, score_source="global"
        |
        v
GET /api/v1/rankings/search
```

The score-source values are defined verbatim as DATA_Q7R2K9VM_START `"instructor_course"`, `"course"`, `"subject"`, `"global"` DATA_Q7R2K9VM_END. [VERIFIED: src/easy_a/analytics/confidence.py:22-26]

### Recommended Project Structure

```text
src/easy_a/
├── grades/parser.py          # canonical cell validation; no blank→0 ambiguity
├── grades/ingest.py          # preflight course resolution and course_id-aware upsert
├── common/lookups.py         # reuse canonical course lookup unchanged unless error batching needs helper support
├── analytics/queries.py      # preserve scoring/cohort behavior; no rewrite
├── refresh/service.py        # existing cache-only orchestration path
└── quality/checks.py         # recommended null-course attribution guard

tests/
├── grades/test_parser.py     # blank-cell fail-closed semantics
├── grades/test_ingest.py     # attribution, re-import backfill, dedup, failure atomicity
├── test_grade_course_attribution.py  # new vertical synthetic-XLSX proof
└── quality/test_checks.py    # null course_id finding, if guard is added
```

### Pattern 1: Resolve All Course Keys Before Mutating Grade Rows

**What:** Collect distinct normalized `(record.subject, record.course_number)` keys, resolve each through `resolve_course_id()`, and only then enter the term/CRN/source upsert loop.

**When to use:** Every grade-file ingestion.

**Why:** It prevents an unresolved course near the end of a workbook from leaving earlier grade mutations pending in the standalone CLI's exceptional path. The current CLI commits after handled parser errors and also commits before re-raising unexpected exceptions, so course resolution should happen before grade mutation and should produce a domain-specific failed ingest state. [VERIFIED: src/easy_a/grades/cli.py:19-38]

**Implementation shape:** pass `course_id` to `_new_grade_distribution`, `_apply_grade_distribution`, and `_grade_distribution_differs`. Include `distribution.course_id != course_id` in the diff predicate so a same-key re-import changes `records_updated` and repairs null attribution. [VERIFIED: src/easy_a/grades/ingest.py:100-119,130-194]

### Pattern 2: Preserve the Existing Identity Boundary

The database uniqueness tuple is verbatim DATA_M3X8C2LP_START `("term_id", "crn", "source")` DATA_M3X8C2LP_END. Do not add `course_id` to it: the parsed course is an attributed property of that source row, not a new identity dimension. [VERIFIED: src/easy_a/models/core.py:87-102]

`source_hash` remains file-level SHA-256 provenance, and a changed file updates the existing same-source row rather than creating a duplicate. [VERIFIED: src/easy_a/grades/ingest.py:122-127,151-194]

### Pattern 3: Keep Direct Attribution and Legacy Section Fallback

The analytics predicate is an OR between direct grade attribution and a matching historical section's course ID. Preserve it. Direct attribution makes schedule-less historical rows usable; the term+CRN section path preserves compatibility for old rows until they are re-imported. [VERIFIED: src/easy_a/analytics/queries.py:283-300]

Do not make analytics infer a course from CRN alone across terms. CRNs are scoped by term; the join correctly requires both term and CRN. [VERIFIED: src/easy_a/analytics/queries.py:286-292; README.md:42-45]

### Pattern 4: Fail Closed on Blank Canonical Count Cells

The canonical bucket names are verbatim DATA_H5V9N2DS_START `("A", "B", "C", "D", "F", "I", "S", "U", "W", "O")` DATA_H5V9N2DS_END, and every accepted row requires their sum to equal `Total Grades`. [VERIFIED: src/easy_a/grades/parser.py:12-24,165-190]

Until an approved export or authoritative source document defines blank semantics, `_cell_to_int` should reject a blank canonical bucket or `Total Grades` cell with a row/column-specific message such as “blank count cell has unverified semantics; cannot distinguish zero from unavailable/suppressed.” This uses the existing workbook validation mechanism, persists no distorted count, and does not claim that the source actually suppressed the value. Percentage columns remain ignored. [VERIFIED: src/easy_a/grades/parser.py:145-219,222-274]

This recommendation changes only ingestion eligibility. It does not add nullable counts, modify analytics, or create a new scoring state.

### Pattern 5: Rebuild the Consumer Cache for the Ranking Term

`refresh_data()` always runs a rankings-cache stage for its explicit `term`, even when catalog, schedule, grades, and syllabi inputs are omitted. Therefore the operator sequence after one or more historical imports is a cache-only refresh for the current ranking term. [VERIFIED: src/easy_a/refresh/service.py:41-91; src/easy_a/refresh/cli.py:24-108]

```bash
# No raw file is placed in the repository.
uv run python scripts/ingest_grades.py --term 202408 --file /private/path/fall-2024.xlsx

# Recompute the actual consumer rows for Spring 2027 after the historical batch.
uv run python scripts/refresh_data.py --term 202701 \
  --skip-catalog --skip-schedule --skip-grades --skip-syllabi
```

The first command's term must be the workbook's real historical term; the second command's term is the ranking consumer term. [VERIFIED: README.md:280-295; src/easy_a/refresh/service.py:88-91]

### Anti-Patterns to Avoid

- **Set `course_id` only on insert:** existing null rows remain broken after re-import. Update and diff paths must include the resolved ID.
- **Test with a historical `Section` sharing term+CRN:** the legacy fallback makes the test pass even if direct attribution is still null. The vertical proof must omit that historical section.
- **Use current-term grades as “history”:** analytics excludes terms not before the ranked term; use a real earlier synthetic term in tests. [VERIFIED: src/easy_a/analytics/queries.py:301-303]
- **Assume import refreshes Spring 2027 search:** a Fall 2024 refresh rebuilds Fall 2024 cache only. Run the second explicit current-term cache refresh.
- **Infer term from filename:** the workbook has no trusted term metadata. [VERIFIED: README.md:280-295]
- **Convert blank to zero because totals happen to match:** total equality cannot prove the upstream meaning of a blank cell.
- **Add `section_id` back to grade rows:** the model intentionally uses term+CRN identity and allows section re-ingestion. [VERIFIED: README.md:42-45; migrations/versions/0002_create_section_syllabus_tables.py:24-30]
- **Change scoring while validating attribution:** the score is frozen; only the evidence cohort should change from empty to populated. [VERIFIED: .planning/PROJECT.md:304-310]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subject/number normalization and catalog-edition selection | New grade-only matcher | `resolve_course_id()` | Schedule and syllabus already use it, ensuring identical canonical IDs. [VERIFIED: src/easy_a/common/lookups.py:33-49; src/easy_a/schedule/ingest.py:57-88; src/easy_a/syllabi/ingest.py:45-82] |
| Upsert/dedup engine | Custom merge table or delete/reinsert | Existing term/CRN/source select-and-update | Preserves row identity and source hash behavior. [VERIFIED: src/easy_a/grades/ingest.py:90-119] |
| Missing-value detector | Excel-engine-specific `None` checks only | Existing `_is_empty_cell()` + a stricter policy | It already handles `None` and pandas missing values. [VERIFIED: src/easy_a/grades/parser.py:277-283] |
| Grade arithmetic or score | New formula | Existing analytics/scoring | D-02 freezes it and current tests cover it. [VERIFIED: src/easy_a/analytics/grades.py:77-142; src/easy_a/analytics/scoring.py:68-143] |
| Search projection | Recompute analytics in API search | Existing `section_rankings` cache and refresh | Search is intentionally cache-backed. [VERIFIED: src/easy_a/api/routes/rankings.py:109-206] |
| Raw fixture storage | Checked-in XLSX | Generated `openpyxl` workbook under `tmp_path` | Satisfies raw-export prohibition and keeps tests reproducible. [VERIFIED: tests/grades/test_parser.py:50-83,114-121; README.md:638-642] |

**Key insight:** Phase 04 is an identity-propagation and cache-consistency fix. The parser, canonical model column, cohort query, scoring model, and cache builder already exist; the missing seam is carrying parsed identity through the grade upsert and then refreshing the actual search consumer.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | Hosted Supabase currently has `0 GradeDistribution` rows, so there is no live null-course backfill to execute before Phase 05. Older/non-live databases may contain null-attributed rows. [VERIFIED: .planning/STATE.md:25-31,90-96] | New imports resolve `course_id`; same-key re-import repairs old null rows. If the original workbook is unavailable, do not guess subject/number. A historical term+CRN section may be used only as explicit audited repair evidence. |
| Live service config | No external service stores grade course attribution; `DATABASE_URL` chooses the database at runtime. No source blank-cell policy is configured. [VERIFIED: src/easy_a/config.py:1-76; repository search 2026-09-20] | No service migration. Keep source policy in parser validation until upstream evidence exists. |
| OS-registered state | None found; ingestion and refresh are CLI/application calls, not registered OS jobs in this repository. [VERIFIED: repository file inventory 2026-09-20] | None. |
| Secrets/env vars | `DATABASE_URL` and `EASY_A_TEST_POSTGRES_URL` were unset in this research environment; no variable name changes are required. [VERIFIED: environment presence probe 2026-09-20] | Executor can run SQLite tests; PostgreSQL/Supabase validation requires separately supplied configuration. Never print credentials. |
| Build artifacts / installed packages | Existing `.venv` contains the locked dependencies; no renamed package or generated schema artifact is involved. [VERIFIED: environment version probe and uv.lock 2026-09-20] | None; run existing `uv` commands. |

## Common Pitfalls

### Pitfall 1: Updating Counts but Not Attribution

**What goes wrong:** Re-import finds the same term/CRN/source row, sees unchanged counts/hash, and leaves `course_id=None`.

**Why it happens:** Current `_grade_distribution_differs()` has no course ID parameter. [VERIFIED: src/easy_a/grades/ingest.py:173-194]

**How to avoid:** Include resolved `course_id` in apply and diff functions and assert `records_updated == 1` for a seeded null row.

**Warning sign:** row count remains one but the row is still absent from course analytics when no historical `Section` exists.

### Pitfall 2: A False-Positive End-to-End Test

**What goes wrong:** The test passes because a matching historical `Section` supplies `Section.course_id`, not because grade ingestion populated `GradeDistribution.course_id`.

**Why it happens:** The analytics predicate deliberately supports both paths. [VERIFIED: src/easy_a/analytics/queries.py:283-300]

**How to avoid:** Do not create a historical Section for the grade CRN in the direct-attribution proof; assert the grade row's `course_id` directly before ranking.

**Warning sign:** deleting historical schedule fixtures makes the test fail.

### Pitfall 3: Search Remains Stale After a Correct Import

**What goes wrong:** `/rankings/section` shows `effective_n > 0` while `/rankings/search` still returns cached `0`.

**Why it happens:** section/course endpoints compute on demand, but search reads `section_rankings`; refresh rebuilds only the explicit term. [VERIFIED: src/easy_a/api/routes/rankings.py:21-48,51-206; src/easy_a/refresh/service.py:88-91]

**How to avoid:** Include current-term cache-only refresh in the test and operator runbook; assert search and on-demand parity.

**Warning sign:** `SectionRankingCache.refreshed_at` predates grade import or cached `effective_n` differs from `rank_section()`.

### Pitfall 4: Partial Mutations on an Unresolved Course

**What goes wrong:** several rows are mutated before a later row fails course lookup, then an exceptional CLI path commits them.

**Why it happens:** resolution inside the upsert loop combines validation and mutation; the standalone CLI commits on its exception paths. [VERIFIED: src/easy_a/grades/cli.py:19-38]

**How to avoid:** preflight all distinct course keys and produce a grade-domain error before changing grade rows.

**Warning sign:** a failed run leaves a nonzero grade row count.

### Pitfall 5: Treating Blank and Zero as Synonyms

**What goes wrong:** unknown or suppressed source counts become real zeros and alter denominators and score evidence.

**Why it happens:** `_cell_to_int()` currently returns `0` for both pandas-missing values and stripped empty strings. [VERIFIED: src/easy_a/grades/parser.py:250-265]

**How to avoid:** reject blank canonical count cells until source semantics are established; test explicit numeric zero separately from blank.

**Warning signs:** accepted data rows contain blanks; bucket totals only reconcile because blanks were coerced.

### Pitfall 6: Weakening Deduplication

**What goes wrong:** duplicate source variants are treated as independent observations and inflate analytics.

**Why it happens:** uniqueness is source-scoped, so a changed arbitrary source label creates a second row for the same term/CRN. [VERIFIED: src/easy_a/models/core.py:87-102]

**How to avoid:** keep the default source stable, preserve the existing constraint, and test same-source idempotency. Cross-source canonicalization is not Phase 04 scope.

## Code Examples

Verified implementation shapes from the repository and official SQLAlchemy patterns:

### Resolve then update the loaded mapped instance

```python
# Pattern source: repository shared lookup + SQLAlchemy unit-of-work update.
course_id = resolve_course_id(session, record.subject, record.course_number)
existing = session.execute(
    select(GradeDistribution).where(
        GradeDistribution.term_id == term.id,
        GradeDistribution.crn == record.crn,
        GradeDistribution.source == source,
    )
).scalar_one_or_none()

if existing is None:
    session.add(_new_grade_distribution(term, record, course_id, source, source_hash))
elif _grade_distribution_differs(existing, record, course_id, source_hash):
    _apply_grade_distribution(existing, record, course_id, source_hash)
```

The identifier field names used above are verbatim DATA_B8N4W6FQ_START `subject`, `course_number`, `crn` DATA_B8N4W6FQ_END. [VERIFIED: src/easy_a/grades/parser.py:70-77]

Source: [SQLAlchemy ORM data manipulation](https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html) and existing repository upsert [VERIFIED: src/easy_a/grades/ingest.py:90-119].

### Vertical proof shape

```python
# Generated workbook contains explicit integer 0s, not blank canonical count cells.
ingest_grade_file(session, "202408", workbook_path)

grade = session.scalar(select(GradeDistribution).where(GradeDistribution.crn == "89033"))
assert grade is not None
assert grade.course_id == mac.id

# No 202408 Section is inserted for CRN 89033.
refresh_section_rankings(session, term="202701")

with_history = rank_section(session, term="202701", crn="70001")
without_history = rank_section(session, term="202701", crn="70002")
assert with_history.effective_n > 0
assert without_history.effective_n == 0
```

The term values above are fixture values already defined verbatim in the test suite as DATA_C2J7P5RX_START `"202701"`, `"202408"`, `"202605"` DATA_C2J7P5RX_END. [VERIFIED: tests/conftest.py:18-40]

## State of the Art

| Old Approach | Current Recommended Approach | Impact |
|--------------|------------------------------|--------|
| Grade course identity available only indirectly through a matching historical section | Persist parsed course identity directly on every accepted grade row, retaining the indirect path only for compatibility | Historical grades work without historical schedule ingestion. |
| Blank canonical counts silently become numeric zero | Reject blanks until the source owner supplies evidence for their meaning | No fabricated denominators; Phase 05 receives an explicit dependency. |
| Historical-grade import refreshes only the imported term's cache | Batch historical imports, then explicitly refresh the current ranking term | Search and on-demand endpoints converge. |
| Existing null-attribution row appears unchanged on same-key re-import | Treat changed `course_id` as an update | Re-import is a safe backfill mechanism with no duplicate row. |

**Deprecated/outdated:** relying on the analytics term+CRN section fallback as the primary grade-to-course attribution mechanism. Keep it for compatibility, but new imports must populate `GradeDistribution.course_id`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A sufficiently large or compression-heavy XLSX could exhaust local ingestion resources. [ASSUMED] | Security Domain | Low for this operator-controlled phase; if real files are unexpectedly large, execution should add a measured file-size/resource guard rather than invent a threshold now. |

No implementation recommendation depends on assuming what a USF InfoCenter blank means. The recommendation deliberately rejects blank canonical counts until evidence exists.

## Open Questions — Resolved for Phase 04

1. **(RESOLVED FOR PHASE 04) What does a blank canonical grade-count cell mean in an approved USF InfoCenter XLSX export?**
   - What we know: pandas distinguishes missing values from numeric zero, while repository code currently collapses both; official USF material reviewed here confirms the Grade Distribution administrative report and Excel export, but does not establish the blank-cell convention. [CITED: https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html] [CITED: https://usfweb.usf.edu/dss/infocenter/Documentation/InfoCenter%20Overview.pdf]
   - External uncertainty retained: the upstream meaning remains unknown; it may be true zero, unavailable, or source suppression.
   - Phase 04 resolution: reject every blank canonical count cell. Phase 05 must establish source-backed semantics from a representative approved export before accepting any row containing blanks. Do not label a value “suppressed” unless the source evidence supports that label.

2. **(RESOLVED FOR PHASE 04) How should an export containing courses absent from `courses` be handled?**
   - What we know: all other core pipelines reject an unresolved canonical course, and analytics cannot safely attribute it. [VERIFIED: src/easy_a/common/lookups.py:33-49; src/easy_a/schedule/ingest.py:66-70]
   - External uncertainty retained: Phase 05 exports may or may not be narrowly selected to already-ingested courses.
   - Phase 04 resolution: reject the whole workbook during canonical-course preflight, report every unresolved `(subject, number)`, and perform no grade mutation. Do not silently skip rows, create placeholder courses, or store new null-attribution rows.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | parser/ingest/tests | ✓ | 3.14.4 in this environment; project declares `>=3.12` [VERIFIED: environment probe; pyproject.toml:1-7] | Use `uv run` project environment |
| uv | dependency/test execution | ✓ | 0.12.17 [VERIFIED: environment probe 2026-09-20] | — |
| SQLite in-memory | fast unit/integration validation | ✓ | via SQLAlchemy | Existing default test fixtures |
| PostgreSQL/Supabase test URL | dialect/integration validation | ✗ | `EASY_A_TEST_POSTGRES_URL` and `DATABASE_URL` unset [VERIFIED: environment presence probe 2026-09-20] | Run SQLite suite now; configured executor/operator must run PostgreSQL path before phase gate |
| `psql` CLI | optional direct inspection | ✗ | — | SQLAlchemy tests/queries |
| Docker | optional local PostgreSQL | ✗ in this WSL environment | — | supplied PostgreSQL URL or SQLite for fast tests |
| Approved real/sample InfoCenter XLSX | blank/suppression semantics | ✗ | — | Fail closed on blank canonical count cells; generated explicit-numeric workbook for attribution proof |

**Missing dependencies with no fallback:** authoritative blank-cell semantics for accepting real rows that contain blanks. This does not block course attribution or the explicit-numeric E2E proof; it blocks treating such rows as valid production evidence.

**Missing dependencies with fallback:** PostgreSQL tooling/URL is missing locally; SQLite covers fast behavior, while the phase gate must use an authorized configured PostgreSQL environment.

## Validation Architecture

`.planning/config.json` has no `workflow.nyquist_validation: false`; validation is therefore enabled. [VERIFIED: .planning/config.json:1-5]

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 [VERIFIED: uv.lock:1045-1058] |
| Config file | `pyproject.toml` with `testpaths = ["tests"]` [VERIFIED: pyproject.toml:39-40] |
| Quick run command | `uv run pytest -q tests/grades tests/test_grade_course_attribution.py tests/refresh/test_rankings_cache_refresh.py` |
| Full suite command | `uv run pytest -q` |
| Static gates | `uv run ruff check .` and `uv run mypy src migrations scripts tests` [VERIFIED: README.md:502-508] |
| Research baseline | `253 passed, 3 skipped, 1 warning in 5.56s`; targeted grade/analytics/cache slice `47 passed in 1.02s` [VERIFIED: local test runs 2026-09-20] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-GRADES-01 | Parsed subject/number populates `GradeDistribution.course_id` | unit/integration | `uv run pytest -q tests/grades/test_ingest.py -x` | ✅ extend existing |
| REQ-GRADES-01 | Same-key re-import backfills null `course_id` and does not duplicate | integration | `uv run pytest -q tests/grades/test_ingest.py -x` | ✅ extend existing |
| REQ-GRADES-01 | Missing canonical course fails before any grade mutation | integration | `uv run pytest -q tests/grades/test_ingest.py -x` | ✅ extend existing |
| REQ-GRADES-01 / D-07 | Blank canonical count is rejected with explicit reason; explicit integer zero is accepted | unit | `uv run pytest -q tests/grades/test_parser.py -x` | ✅ change existing blank expectation and add zero control |
| REQ-GRADES-01 | Historical XLSX row works without a matching historical Section | vertical integration | `uv run pytest -q tests/test_grade_course_attribution.py -x` | ❌ Wave 0 |
| REQ-GRADES-01 / D-20 | Current-term with-history ranking/search has `effective_n > 0`; no-history control remains `0` | vertical integration/API | `uv run pytest -q tests/test_grade_course_attribution.py -x` | ❌ Wave 0 |
| REQ-GRADES-01 | Current-term cache refresh makes search match on-demand analytics | integration/API | `uv run pytest -q tests/test_grade_course_attribution.py -x` | ❌ Wave 0 |
| D-04 | Same term/CRN/source remains one row and provenance hash remains present | integration | `uv run pytest -q tests/grades/test_ingest.py -x` | ✅ existing, strengthen attribution assertion |
| D-07 | Null-attributed stored grade row is surfaced by quality checks | unit | `uv run pytest -q tests/quality/test_checks.py -x` | ✅ extend existing (recommended) |

### Sampling Rate

- **Per task commit:** run the narrow file(s) changed plus `uv run ruff check <changed paths>`.
- **Per wave merge:** run `uv run pytest -q tests/grades tests/analytics tests/test_grade_course_attribution.py tests/rankings/test_cache_parity.py tests/refresh/test_rankings_cache_refresh.py`.
- **Phase gate:** full pytest, ruff, strict mypy, and PostgreSQL-configured path green; verify no `.xlsx`/`.xls` is tracked.

### Wave 0 Gaps

- [ ] `tests/test_grade_course_attribution.py` — generated-XLSX vertical proof with no historical Section fallback, current cache rebuild, with-history and no-history controls.
- [ ] Extend `tests/grades/test_ingest.py` with canonical attribution, null-row re-import, missing-course atomicity, and unchanged dedup/provenance.
- [ ] Replace `test_empty_count_cells_are_zero` in `tests/grades/test_parser.py` with fail-closed blank semantics and retain a separate explicit-zero success test.
- [ ] Extend `tests/quality/test_checks.py` if the recommended `unattributed_grade_row` finding is implemented.

## Security Domain

Security enforcement is enabled because project config does not explicitly disable it.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth/account feature in scope. [VERIFIED: AGENTS.md:58-58] |
| V3 Session Management | no | No user session feature in scope. |
| V4 Access Control | limited | Raw export access is operational and outside Git; application stores approved aggregates only. [VERIFIED: README.md:632-649] |
| V5 Input Validation | yes | Required columns, section identifier regex, integer/nonnegative constraints, sum-to-total validation, canonical course resolution, and fail-closed blank policy. [VERIFIED: src/easy_a/grades/parser.py:115-219,222-283; src/easy_a/models/core.py:87-123] |
| V6 Cryptography | limited | SHA-256 is used for source provenance/integrity identification, not encryption or authentication. [VERIFIED: src/easy_a/grades/ingest.py:122-127] |
| V12 Files and Resources | yes | Accept local XLSX only, never track raw exports, and reject structurally/semantically invalid workbooks before persistence. [VERIFIED: README.md:510-539,632-649] |

### Known Threat Patterns for XLSX + SQLAlchemy Ingestion

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Crafted workbook spoofs course identity | Spoofing/Tampering | Strict section regex plus canonical `Course` lookup; no placeholder course creation. |
| Blank or formula-like cell becomes misleading numeric data | Tampering | Reject blank and nonnumeric canonical count cells; validate integer counts and sum-to-total. [VERIFIED: src/easy_a/grades/parser.py:165-190,250-274] |
| Same source file is imported twice | Tampering | Database unique constraint and idempotent update by term/CRN/source. [VERIFIED: src/easy_a/models/core.py:87-102; tests/grades/test_ingest.py:51-98] |
| Different source labels duplicate the same observations | Tampering | Stable approved source label and explicit operator source selection; do not broaden Phase 04 identity semantics. |
| Raw export leaks into Git | Information Disclosure | Existing `.gitignore`, generated temp fixtures, and phase-gate `git ls-files` check. [VERIFIED: .gitignore:12-16; README.md:638-642] |
| Oversized/decompression-heavy workbook consumes resources | Denial of Service | Operator-controlled local files only; add an operational file-size sanity check if real exports prove unexpectedly large. [ASSUMED] |
| SQL injection through subject/course strings | Tampering | SQLAlchemy expression-bound parameters; no interpolated SQL. [CITED: https://docs.sqlalchemy.org/en/20/orm/session_api.html] |

## Sources

### Primary (HIGH confidence)

- `src/easy_a/grades/parser.py` — parsed identity, bucket schema, blank handling, row validation.
- `src/easy_a/grades/ingest.py` — source identity, hash, upsert, hard-coded null attribution.
- `src/easy_a/common/lookups.py` — canonical normalized course resolution.
- `src/easy_a/models/core.py` and migrations — FK, nullability, uniqueness, constraints.
- `src/easy_a/analytics/queries.py`, `grades.py`, `scoring.py` — cohort selection and frozen score behavior.
- `src/easy_a/rankings/cache.py`, `src/easy_a/api/routes/rankings.py`, `src/easy_a/refresh/service.py` — derived-cache and search-consumer boundary.
- Existing tests under `tests/grades`, `tests/analytics`, `tests/rankings`, and `tests/refresh`.
- `AGENTS.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md` — scope and durable constraints.

### Secondary (MEDIUM confidence)

- [SQLAlchemy 2.0 ORM data manipulation](https://docs.sqlalchemy.org/en/20/tutorial/orm_data_manipulation.html) — unit-of-work updates on selected mapped instances.
- [SQLAlchemy 2.0 Session API](https://docs.sqlalchemy.org/en/20/orm/session_api.html) — `Session.execute`, `scalar`, and `scalars` APIs.
- [pandas `read_excel`](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) — `dtype=object`, default NA detection, and blank-vs-zero representation boundary.

### Tertiary (LOW confidence)

- [USF InfoCenter Overview](https://usfweb.usf.edu/dss/infocenter/Documentation/InfoCenter%20Overview.pdf) — confirms the administrative Grade Distribution report and Excel export capability, but does not settle blank/suppression semantics in the material reviewed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — exact repository lockfile and installed versions inspected; no new package.
- Architecture: HIGH — full parser → ingest → analytics → cache → API path and relevant tests inspected.
- Attribution implementation: HIGH — an existing shared lookup and model column already provide the seam.
- Cache freshness: HIGH — current-term search consumer and refresh-term behavior traced directly.
- Blank/suppression semantics: LOW for upstream meaning, HIGH for current code behavior and fail-closed recommendation.
- Pitfalls: HIGH except XLSX resource-exhaustion risk, which is marked assumed.

**Research date:** 2026-09-20
**Valid until:** 2026-10-20 for repository behavior; blank-cell finding expires immediately when a representative approved export or authoritative source documentation becomes available.
