# Phase 10: Professor-level grades - Pattern Map

**Mapped:** 2026-09-30
**Files analyzed:** 14 (new/modified)
**Analogs found:** 13 / 14

All analog paths verified git-tracked (`git ls-files`). No RESEARCH.md; file list derived from CONTEXT.md and UI-SPEC.md.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `scripts/backfill_historical_sections.py` (or `src/easy_a/schedule/backfill_cli.py`; planner picks) | CLI / batch | batch, file-I/O (HTTP fetch then DB upsert) | `src/easy_a/schedule/cli.py` + `src/easy_a/schedule/ingest.py` | role-match |
| `src/easy_a/schedule/ingest.py` (modify or reuse; backfill write path) | service | CRUD upsert | itself (`_upsert_sections`) | exact |
| `src/easy_a/analytics/scoring.py` (modify: add `instructor_prior_strength`, min n 60 to 30) | config/service | transform | itself | exact |
| `src/easy_a/analytics/queries.py` (modify: instructor stats use new prior; lab exclusion in `_instructor_section_ids`; new instructor-breakdown query) | service | request-response / transform | itself (`get_instructor_course_historical_outcome_stats`, `_instructor_section_ids`) | exact |
| `src/easy_a/rankings/models.py` (add breakdown pydantic models, field on `SectionRanking`) | model | request-response | `HistoricalAnalyticsSummary` in same file | exact |
| `src/easy_a/rankings/service.py` (build breakdown in `rank_section` / batch path) | service | request-response | `_historical_summary`, `_historical_stats_for_section` | exact |
| `scripts/` or `src/easy_a/rankings/cli.py` before/after diff report (D-04) | CLI / report | batch | `scripts/benchmark_rankings_search.py`, `src/easy_a/rankings/cli.py` | role-match |
| `.planning/PROJECT.md` D-24 update | doc | n/a | existing D-xx entries | exact |
| `tests/analytics/test_grades_and_scoring.py`, `test_queries.py` (extend) | test | transform | themselves | exact |
| `tests/schedule/test_ingest.py` (backfill tests) | test | CRUD | itself | exact |
| `web/src/types/rankings.ts` (add types) | model | request-response | `HistoricalAnalytics` interface | exact |
| `web/src/utils/rankings.ts` (add `formatTermShort`, count/plural helpers) | utility | transform | `describeEvidence`, `instructorLabel` | exact |
| `web/src/components/InstructorBreakdown.tsx` (new) | component | request-response (read-only render) | `RankingDetails.tsx` Policy-signals block + `InfoTip.tsx` | role-match |
| `web/src/components/RankingDetails.tsx` (modify: insert block) and `web/src/components/InstructorBreakdown.test.tsx` / extend `RankingEvidence.test.tsx`; `web/src/fixtures/rankings.ts` | component/test | request-response | `RankingEvidence.test.tsx` | exact |

## Pattern Assignments

### Scoring retune: `src/easy_a/analytics/scoring.py` (config, transform)

**Analog:** itself. **Constants and config** (lines 19-35):
```python
DEFAULT_GRADE_PRIOR_STRENGTH = 60.0
DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N = 60.0   # -> 30.0 (D-01)
...
@dataclass(frozen=True)
class ScoreConfig:
    grade_prior_strength: float = DEFAULT_GRADE_PRIOR_STRENGTH
    instructor_course_min_effective_n: float = DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N
```
Add `DEFAULT_INSTRUCTOR_PRIOR_STRENGTH = 30.0` and field `instructor_prior_strength` beside `grade_prior_strength` (D-03). Do not change `DEFAULT_GRADE_PRIOR_STRENGTH`.

**Where the prior strength is consumed** (lines 98-121): `compute_historical_outcome_stats` hard-wires `score_config.grade_prior_strength` into `bayesian_smooth(...)`. The instructor path calls it with `score_source=ScoreSource.instructor_course` (queries.py 129-136). Planner must choose: select strength inside `compute_historical_outcome_stats` when `score_source is ScoreSource.instructor_course` (use `instructor_prior_strength`), else `grade_prior_strength`. Course-level must remain byte-identical (add a regression test). Withdrawal prior strength: decide explicitly whether instructor uses 30 too (D-24 text says "instructor-level prior strength ~30"; confirm in PROJECT.md D-24).

**Gate** (lines 146-155), reuse unchanged apart from the default:
```python
def has_sufficient_instructor_course_evidence(stats, config=None) -> bool:
    score_config = config or ScoreConfig()
    return (
        stats.score_source is ScoreSource.instructor_course
        and stats.effective_n >= score_config.instructor_course_min_effective_n
        and stats.mapped_instructor_section_count > 0
    )
```
Single-term flag is label-only (D-02): no scoring change; expose `term_count` to UI.

### `src/easy_a/analytics/queries.py` (service, request-response)

**Analog:** itself. Per-instructor stats pattern (lines 94-136): `is_usable_instructor` guard, `_course_ids`, `aggregate_grade_observations(_fetch_instructor_course_grade_observations(...), score_config.recency)`, then `compute_historical_outcome_stats(..., grade_prior=course_stats.grade_favorability_smoothed, prior_level=PriorLevel.course, score_source=ScoreSource.instructor_course)`. Copy this per instructor for the breakdown rows.

**Join to modify for labs (D-13)** (lines 651-665):
```python
def _instructor_section_ids(session, course_ids, instructor_name) -> set[int]:
    return set(session.execute(
        select(Section.id)
        .join(SectionInstructor, SectionInstructor.section_id == Section.id)
        .where(Section.course_id.in_(course_ids), SectionInstructor.name_raw == instructor_name)
    ).scalars())
```
Add a `Section.section_type` filter excluding laboratory types (`section_type` stored as e.g. "Class Lecture"; confirm exact lab string such as "Laboratory" against hosted data / `tests/fixtures`). Batch path equivalent: `for_instructor` (lines ~400-408) uses `instructor_names_by_section_id` built at ~384; apply the same exclusion there. Course-level history keeps lab grades.

**Batch path** (lines 282-300): per-instructor memoization dict `instructor_stats_by_name` then `has_sufficient_instructor_course_evidence`; keep this shape.

**Identity (D-14):** within a course key by `name_raw` (as now). Staff/blank excluded via `is_usable_instructor` (`easy_a.common.instructors`) (D-08).

### `src/easy_a/rankings/models.py` and `service.py` (model/service)

**Analog:** `HistoricalAnalyticsSummary` (models.py 68-83), frozen pydantic:
```python
class HistoricalAnalyticsSummary(BaseModel):
    easiness_score: float
    ...
    provenance: RankingProvenance
    model_config = ConfigDict(frozen=True)
```
New models (names are discretion) mirror UI-SPEC "Data the UI Needs": `status` (`ready|lab_section|no_instructor_history`), `instructors[]` (name, a_share, grade_count, term_count, first_term, last_term, shrunk_score|None, scored), `current_instructor`, `others {instructor_count, cutoff}`, `scoring_min_grades`, `collapse_cutoff`. Add as `instructor_breakdown: InstructorBreakdown | None` on `SectionRanking` (models.py 86-111). Use `tuple[...]` for sequences like existing fields. Builder goes beside `_historical_summary` (service.py ~376-400) fed from `_historical_stats_for_section` (~348). Mirror the change in `src/easy_a/api/schemas.py` only if it wraps the model (it reuses rankings models). Check `rankings/cache.py` (cache rebuild; embedded vs lazy transport is discretion; embedded avoids loading/error states). Return `null` when `score_source` is not course-history (D-20) so the UI omits the block.

### Backfill CLI (D-05..D-08) (batch, file-I/O)

**Analog 1 (CLI shape):** `src/easy_a/schedule/cli.py` lines 10-47: argparse `build_parser()` / `main(argv) -> int`, `StaffScheduleClient` context manager, `get_session_factory()` with `session_factory.begin()`, and a final `print("... seen=... inserted=...")`.
```python
with StaffScheduleClient() as client:
    html = client.search(query)
session_factory = get_session_factory()
with session_factory.begin() as session:
    result = ingest_schedule_html(session, html, args.term)
```
Whole-term fetch: `StaffScheduleClient.search_term(...)` (client.py 74) and `build_whole_term_form_data(term, campus="T")` (142), as used by the sync worker (`src/easy_a/sync/fetch.py`) and 2026-09-28 pull. One request per term, five terms: 202408, 202501, 202505, 202508, 202601.

**Analog 2 (write path):** `src/easy_a/schedule/ingest.py` `_upsert_sections` (57-110) with `parse_schedule_html` + `normalize_schedule_row` (lines 40). Key gotchas for the planner:
- Existing upsert is keyed by `Section.term_id + Section.crn` (idempotent for sections) BUT it unconditionally `session.add(SectionInstructor(...))` and a `SeatSnapshot` every run (lines 90-108), so re-runs duplicate instructor rows (test_ingest asserts 4 rows after 2 ingests). D-07 requires idempotence: write a dedicated backfill upsert (or add an option) that skips if a `SectionInstructor` with same `section_id` + `name_raw` + source exists, and writes no seat snapshots for historical terms.
- Filter before write (D-06): only rows whose `(term, crn)` exists in `grade_distributions` (`GradeDistribution.term_id/crn`) and whose course resolves (`resolve_course_id` raises `CoreDataLookupError` -> skip and count, do not abort, unlike `ingest_schedule_html` which raises `ScheduleIngestError`).
- `ensure_term(session, term_code)` from `easy_a.common.lookups`.
- Do not stamp `removed_at`; sync sweeps only act on current terms (check `src/easy_a/sync/scope.py`/`plan.py` for term scoping so historical rows cannot be marked removed).
- `--dry-run` prints counts only (copy the dry-run print style from `src/easy_a/sync/cli.py` `--dry-run`). Print skipped/staff/unmatched counts for the post-run re-measure vs 2026-09-28 report.
- Keep module light; never log connection URLs (see sync/cli.py docstring convention).

### Before/after diff report (D-04) (batch report)

**Analog:** `src/easy_a/rankings/cli.py` (argparse + `json.dumps(model_dump(mode="json"))`) and `scripts/benchmark_rankings_search.py` for script style. Compute scores with old `ScoreConfig(instructor_course_min_effective_n=60, instructor_prior_strength=60)` vs new defaults via `rank_course_sections`/batch path, and report changed sections, magnitudes, and an assertion that `score_source != instructor_course` rows are identical.

### Frontend types and utils

**Analog:** `web/src/types/rankings.ts` (60-90): plain `export interface` / string-union types, snake_case API fields (`HistoricalAnalytics`, `SectionRanking`). Add `InstructorBreakdown*` interfaces and an optional `instructor_breakdown` on `SectionRanking`; update `web/src/fixtures/rankings.ts` (`syntheticRankings`).

**Analog:** `web/src/utils/rankings.ts`, arrow-function exports. `describeEvidence` (117+) returns `scope: "course_history"` (gate for rendering the block) and `instructorLabel` (163-172) returns "Staff"/"Ambiguous / unavailable"/"Unknown" for unnamed. Add `formatTermShort(code)` (suffix 01 Spr, 05 Sum, 08 Fall; unknown suffix returns raw code), plural helpers (`1 grade`, `1 term`, `1 other instructor`), and a named-instructor predicate derived from `instructorLabel`.

### `web/src/components/InstructorBreakdown.tsx` (component)

**Analog:** `RankingDetails.tsx` policy-signal list (lines 49-73) for row/list/dashed-note classes:
```tsx
<li className="rounded-md border border-rule bg-white/70 p-3" key=...>
...
<p className="mt-3 rounded-md border border-dashed border-stone-300 bg-white/50 p-4 text-sm font-semibold text-stone-600">No policy information available</p>
```
Reuse these class strings for rows and the empty/lab notes. Heading: `<h4 className="detail-heading">`. InfoTip usage (InfoTip.tsx 1-30): `<InfoTip label="USF lists one instructor per section; ..." />`, takes only `label`; must be the last right-aligned item in the header row (`flex items-center justify-between gap-2`). Imports follow RankingDetails: `import type { ... } from "../types/rankings"; import { ... } from "../utils/rankings";` (relative paths, no alias).
Container: `<section className="mt-6" aria-labelledby={`${id}-instructors-heading`}>` with the `id` prop from `RankingDetails` (rendered twice: desktop plus mobile). Do not use an `aria-label` starting "Details for". Use native `<details><summary>`; only weights 400/700 and sizes 12/14/18; no `text-[11px]`. Note the existing file uses `text-[11px]` and `font-extrabold` at lines 26/59; do not copy those.

**Integration:** in `RankingDetails.tsx`, insert after the `<dl>` (line 38) and before the seat section (line 39), gated on `evidence.scope === "course_history"` and the breakdown status. The existing `evidence` const (line 15) is already in scope.

### Frontend tests

**Analog:** `web/src/components/RankingEvidence.test.tsx` lines 1-27: `renderExpanded(ranking)` renders the real `RankingTable` with `expandedCrn` and returns `table`, `cardContainer`, `detailRegions` (`getAllByRole("region", { name: /^Details for/ })`, length 2); assertions use `within(region).getByText(...)`; fixtures spread from `syntheticRankings[n]`. Cover the 8 test hooks in UI-SPEC (row format, Staff, lab, non-course-history scopes, pinned-first, InfoTip label, duplicate ids, existing assertions). Fixtures: CNT 4419, PSY 2012, ENC 1101, MAC 1105.

### Backend tests

- Scoring: extend `tests/analytics/test_grades_and_scoring.py`; assert new defaults, course-level scores unchanged, instructor score changes with `instructor_prior_strength`.
- Queries: `tests/analytics/test_queries.py` (e.g. `test_staff_instructor_falls_back_to_course_level` line 170, `test_missing_historical_instructor_mapping_only_contributes_to_course_history` line 187) are the pattern for lab exclusion, Staff, and name-key cases; uses `db_session` fixture (`tests/conftest.py`).
- Backfill: `tests/schedule/test_ingest.py` pattern (lines 1-32: `ingest_schedule_html(db_session, html, "202701", observed_at=...)`, count assertions with `func.count()`), fixtures in `tests/fixtures/` (`schedule_historical_202408_89033.html`). Add an idempotence test (two runs, no duplicate `SectionInstructor`) and a "no grade row -> not written" test.
- API: `tests/api/test_rankings_api.py` for the response shape.

## Shared Patterns

### Evidence honesty (D-06/D-07/D-20)
**Source:** `web/src/utils/rankings.ts` `describeEvidence`; AGENTS.md hard constraints. Every instructor figure shows n, term count, and source; block omitted unless scope is `course_history`; Staff lists display-only and never feed score (D-11).

### Presentation-only labels, no scoring changes in UI
**Source:** `RankingDetails.tsx` line 36 (low-confidence note gated on `evidence.scope === "course_history"`). UI performs no statistics.

### CLI conventions
**Source:** `src/easy_a/schedule/cli.py`: `build_parser()`, `main(argv: list[str] | None = None) -> int`, `get_session_factory()`, `session_factory.begin()` for transactional writes, summary line `key=value` print. Sync worker CLI documents exit codes and never logs connection URLs.

### Frozen pydantic models
**Source:** `src/easy_a/rankings/models.py`: `model_config = ConfigDict(frozen=True)`, `tuple[...]` collections.

## No Analog Found

| File | Role | Reason |
|---|---|---|
| Historical-only idempotent section upsert (no seat snapshot, dedup instructor rows) | service | Existing `_upsert_sections` always appends `SectionInstructor`/`SeatSnapshot`; closest is `src/easy_a/sync/apply.py` (change-only writes) which is for live terms. Use it as a reference for change-only semantics (`apply_sweep_plan`, line 158) but do not wire into the worker (D-05). |
| Native `<details>` disclosure and `formatTermShort` | component/utility | Nothing equivalent in `web/src`; follow UI-SPEC. |

## Metadata

**Analog search scope:** `src/easy_a/{analytics,schedule,rankings,sync,common}`, `scripts/`, `tests/`, `web/src/{components,utils,types,fixtures}`
**Pattern extraction date:** 2026-09-30
