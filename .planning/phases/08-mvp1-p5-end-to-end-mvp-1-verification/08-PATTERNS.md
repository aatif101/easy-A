# Phase 8: MVP1-P5 End-to-end MVP-1 verification — Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 9 likely new or modified files; no `CONTEXT.md` exists
**Analogs found:** 9 / 9

These are planning assignments, not a mandate to create every file. The planner may combine the two read-only CLIs if one focused verification command is simpler. All analog paths below are Git-tracked source or evidence, checked with `git ls-files`.

## File Classification

| New/modified file | Role | Data flow | Closest tracked analog | Match |
|---|---|---|---|---|
| `scripts/inventory_tampa_grades.py` (new) | read-only CLI/service | batch DB read → aggregate report | `scripts/validate_tampa_ingest.py` | role + flow |
| `tests/refresh/test_inventory_tampa_grades.py` (new) | test | seeded DB → aggregate assertions | `tests/refresh/test_validate_tampa_ingest.py` | role + flow |
| `scripts/verify_rankings_pages.py` (new) | read-only CLI | DB identity set + paged HTTP → reconciliation | `scripts/benchmark_rankings_search.py` | role + flow |
| `tests/api/test_verify_rankings_pages.py` (new) | test | mocked HTTP/seeded API → page identity assertions | `tests/api/test_benchmark_rankings_search.py`, `tests/api/test_rankings_api.py` | role + flow |
| `web/src/components/RankingTable.tsx` (modified if wording fails) | component | API ranking → desktop/mobile rendering | same file; `web/src/components/RankingDetails.tsx` | exact |
| `web/src/components/RankingDetails.tsx` (modified if wording fails) | component | API ranking → expanded evidence rendering | same file | exact |
| `web/src/utils/rankings.ts` (modified if shared copy helps) | utility | score-source → display label | same file | exact |
| `web/src/components/RankingEvidence.test.tsx` (new; name discretionary) | test | fixture ranking → visible desktop/mobile copy | `web/src/components/SeatBadge.test.tsx` | role + flow |
| `08-VERIFICATION-REPORT.md` (new) | evidence | live commands/results → dated gate verdict | `07-PERF-REPORT.md` | role + flow |

## Pattern Assignments

### Grade inventory CLI and tests

**Copy from:** `scripts/validate_tampa_ingest.py:1-20,102-171,174-220` and `tests/refresh/test_validate_tampa_ingest.py:21-105,145-181`.

Imports and read-only session pattern:

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from easy_a.common.terms import normalize_banner_term_code
from easy_a.db import get_session_factory
from easy_a.models import Course, Section, Term
from easy_a.rankings.cache import SectionRankingCache

session_factory = get_session_factory()
with session_factory() as session:
    ...
```

The validator filters term-scoped rows with `.join(Term, Section.term_id == Term.id).where(Term.banner_code == normalized_term)` at lines 127-131 and compares independent totals at lines 132-142. Its D-20 check reads `score_source` and `effective_n` at lines 145-170, raising an `AssertionError` with an offending CRN. Follow its `build_parser()`/`main(argv)` structure at lines 174-220 and print explicit `PASS`/`FAIL` results with a nonzero exit code.

For inventory, use the existing `GradeDistribution` model in `src/easy_a/models/core.py:87-132`: unique `(term_id, crn, source)` at line 90, attributed `course_id`, provenance `source`, `source_hash`, `ingested_at` at lines 87-132. Join the represented `202701` course set to `GradeDistribution.course_id`; group by course and source/term, and reconcile raw grade totals. Keep course-backed, subject fallback, and global fallback as separate states. Do not count a numeric global-prior score as course evidence. `SectionRankingCache.score_source` and `.effective_n` are the existing cache fields (`src/easy_a/rankings/cache.py:56-57`).

Test shape from `tests/refresh/test_validate_tampa_ingest.py`: create Course and Section rows via `_add_course`/`_add_section` at lines 21-49, a cached ranking with explicit source and denominator via `_add_ranking` at lines 52-90, commit the fixture at lines 93-105, then assert both honest and bad cases with `db_session` and `pytest.raises` at lines 145-181. Add distinct sourced/no-history/subject fallback cases and duplicated-source identity cases. Assert no invented totals or source attribution.

### Full API pagination and identity CLI/tests

**Copy from:** `scripts/benchmark_rankings_search.py:93-158,223-314`, `tests/api/test_benchmark_rankings_search.py:52-87`, and `tests/api/test_rankings_api.py:106-119,223-238`.

HTTP client and response validation:

```python
with (
    Session(engine) as session,
    httpx.Client(timeout=60, trust_env=False, follow_redirects=False) as client,
):
    if engine.dialect.name == "postgresql":
        session.execute(text("SET TRANSACTION READ ONLY"))
    ...
```

`scripts/benchmark_rankings_search.py:243-262` counts stored `Section` and cache rows and requires equality. Its `_http_search` at lines 223-240 uses `client.get`, rejects non-200 responses, validates JSON with `RankingsSearchResponse.model_validate`, and checks `total`, `limit`, and `offset`. Reuse this request/validation approach; the new scan must fetch *all* pages, assert a stable `total`, compare the exact `(term, crn)` set against stored rows, and reject duplicates, omissions, extra identities, or a short nonfinal page. Use the route contract's `limit <= 200`, `offset >= 0` (`src/easy_a/api/routes/rankings.py:52-66`) and a deterministic `sort=course`. The route pages narrow keys before hydrating results (`rankings.py:116-175`).

The benchmark only checks an unfiltered first-page total at `scripts/benchmark_rankings_search.py:269-272`; it does not establish full-page identity. Its HTTP tests use `httpx.MockTransport(handler)` at `tests/api/test_benchmark_rankings_search.py:52-87` to test both valid and malformed/error responses. The API tests assert exact CRN sets and page metadata at `tests/api/test_rankings_api.py:106-119,223-238`. Add tests that deliberately repeat one CRN across pages, omit one CRN, and alter `total` between pages.

### Fallback UI and component regression tests

**Copy from:** `web/src/components/RankingTable.tsx:1-107`, `web/src/components/RankingDetails.tsx:1-94`, `web/src/utils/rankings.ts:79-87`, and `web/src/components/SeatBadge.test.tsx:1-53`.

`RankingTable` renders desktop table rows at lines 43-81 and mobile cards at lines 84-104. Its low-confidence copy currently says “Based on limited historical data” in both layouts (lines 65 and 96), including possible `score_source="global"`, `effective_n=0`. `RankingDetails` shows an effective sample and source at lines 31-36, but also uses the generic limited-data sentence at line 35 and a generic historical-estimate sentence at line 89. Use the existing typed `scoreSourceLabel` mapping (`rankings.ts:79-87`) as the shared source-label pattern. If the wording repair needs a new utility, branch on the explicit `score_source`/`effective_n` contract; keep subject fallback distinct from course history and global fallback explicit.

Test pattern:

```tsx
import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { syntheticRankings } from "../fixtures/rankings";

test("global fallback is visibly unavailable", () => {
  // Copy a fixture with score_source: "global" and effective_n: 0.
  // Assert the rendered text names the unavailable course evidence.
});
```

`SeatBadge.test.tsx:8-15` copies and overrides a fixture, lines 23-29 assert that unavailable values are visible and false zero copy is absent, and lines 45-53 use `within` to scope expanded details. `web/src/fixtures/rankings.ts:114-122,298` already includes typed score source/effective-N values and a global example. Test both desktop and mobile render branches plus expanded details for course, subject and global states. Avoid snapshot-only assertions; assert student-visible text and absence of misleading historical-data wording for global fallback.

### Dated verification report

**Copy from:** `.planning/phases/07-mvp1-p4-full-scale-cache-build-search-performance-p95-1-5s/07-PERF-REPORT.md:1-53,117-185`.

The report begins with the UTC date, actual environment and same-settings basis (lines 1-8), reconciles section/cache/grade and source-split counts (lines 10-17), records exact commands (lines 19-25), and defines what HTTP timing includes and excludes (lines 27-33). It records the measured workload and UTC completion (lines 35-53), quality findings by severity/check ID (lines 117-127), p50/p95/max and a narrow performance verdict (lines 140-161), and skipped tests and residual limits (lines 163-185).

Phase 8 should use separate PASS/FAIL/NOT MEASURED verdicts for stored/target/API identity coverage, grade-source coverage and raw totals, UI/API honesty, quality, and hosted-DB loopback p95. State the full MVP-1 verdict separately: `PROJECT.md:23-27` requires course history for every section, so passing Phase 8's softer “wherever data exists” behavior check does not close the milestone if any represented course lacks sourced history. Record actual source, denominator, UTC timestamp, commit, term, command and failure reason. Publish derived aggregates only; omit credentials and raw grade rows.

## Shared Patterns

### Exact evidence identity and term scoping

**Sources:** `src/easy_a/models/core.py:87-132`; `scripts/validate_tampa_ingest.py:102-171`; `src/easy_a/api/routes/rankings.py:52-66`.

`GradeDistribution` source identity is `(term_id, crn, source)`; `Section` identity is term plus CRN; cached search is filtered by term. Normalize the input term before DB comparisons, and compare actual sets rather than just totals when claiming every section is searchable.

### No auth and no write path for verification

**Sources:** `scripts/validate_tampa_ingest.py:185-220`; `scripts/benchmark_rankings_search.py:243-314`.

The application has no auth for these public ranking reads. Verification scripts use the configured DB session and read-only SQL; the benchmark explicitly sets PostgreSQL transaction read-only. Both report failures without logging connection strings. A new CLI should expose bounded term/page/host inputs and dispose any engine it creates.

### Source state and UI truth

**Sources:** `scripts/validate_tampa_ingest.py:145-170`; `web/src/utils/rankings.ts:79-87`; `web/src/components/RankingDetails.tsx:31-36`.

`course`/`instructor_course` with `effective_n > 0` claim course evidence; `subject` is only a subject-level fallback; `global` with `effective_n=0` is no course evidence. The report and both UI layouts must preserve these meanings.

## No Analog Found

None. The full-page identity assertion and course-grade ledger are new behaviors, but their database, HTTP and test mechanics have tracked analogs above.

## Metadata

**Analog search scope:** tracked `scripts/`, `tests/`, `src/easy_a/`, `web/src/`, and prior `.planning/phases/07-*` evidence.
**Files scanned:** 13 primary analog files, with additional targeted searches for model and fixture fields.
**Extraction date:** 2026-09-23.
