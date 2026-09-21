# Phase 5: MVP1-P2 — Grade data sourcing + import to Supabase - Research

**Researched:** 2026-09-21
**Domain:** Data import / ETL for an existing pipeline (USF InfoCenter grade-distribution XLSX → Supabase-hosted PostgreSQL), plus per-course analytics validation. No new library, framework, or architecture is introduced.
**Confidence:** HIGH (codebase claims), LOW (external sourcing-format specifics — see Open Questions)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-GRADES-01 | Ingested Tampa courses have real historical grade data, and easiness is computed from it. Acceptance: import historical grade distributions (data sourcing is Codex-owned, this phase), per-course analytics validated against the source aggregate, courses still lacking data recorded as lacking it — never quietly omitted. Never commit raw export files. | Sections "Standard Stack" (existing tooling only), "Architecture Patterns" (correct import command + mandatory cache-rebuild step), "Common Pitfalls" (atomic-failure scoping, term-vs-ranking-term cache split, `--grade-file` vs `--file` CLI discrepancy), "Code Examples" (validation command), "Runtime State Inventory"-equivalent notes on what already satisfies "record as lacking" |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` is intentionally a pointer: it states `AGENTS.md` is canonical and directs the read
order `AGENTS.md` → `.planning/STATE.md` → `.planning/PROJECT.md` → `.planning/ROADMAP.md` →
`README.md`. All of those were read for this research. No additional CLAUDE.md-specific
directives exist beyond that read order and the milestone pointer (MVP 1).

The durable hard constraints actually governing this phase live in `.planning/PROJECT.md`
`<decisions>` (D-01..D-20) and are restated below where they bind a specific finding. The
load-bearing ones for this phase: **D-02** (no scoring rewrite), **D-04** (term/CRN/source
identity + dedup), **D-06/D-07/D-20** (no fabricated data; honest `effective_n`; a global-prior
fallback is not course history), **D-08/D-09** (bounded, narrow USF requests; no scraping),
**D-19** (never commit raw grade export files), **D-10** (verify `origin/main` by fetch before
planning).

## Summary

This phase has almost no *new code* surface. The XLSX parser (`src/easy_a/grades/parser.py`), the
ingest/upsert logic (`src/easy_a/grades/ingest.py`), and two different CLI entry points already
exist and are fully wired to course attribution (fixed in MVP1-P1/Phase 04) and to a rankings
cache. The actual work in this phase is **operational, not architectural**: (1) obtain an
approved USF InfoCenter grade-distribution XLSX export scoped to the 10 courses currently present
in the hosted Supabase `courses` table (Codex-owned, external, out of this research agent's
reach), (2) import it with the *correct* existing tool, (3) explicitly rebuild the rankings cache
for the **live ranking term** (`202701`) — which does **not** happen automatically when the grade
file's own term differs from 202701 — and (4) validate the resulting per-course analytics against
the source workbook's own totals.

Three findings materially change how this phase should be planned, all confirmed by reading the
actual source, not by inference from the phase description:

1. **The phase description's CLI reference is imprecise.** `grades/cli.py` (`scripts/ingest_grades.py`)
   takes `--file`, not `--grade-file`. The flag `--grade-file` belongs to a different CLI —
   `src/easy_a/refresh/cli.py` (`scripts/refresh_data.py`) — which is the orchestrating tool that
   also rebuilds the rankings cache as part of the same run. The planner should target
   `scripts/refresh_data.py --grade-file ...` (or the standalone `scripts/ingest_grades.py --file
   ...` followed by a manual cache rebuild), not assume `grades/cli.py` accepts `--grade-file`.
2. **`scripts/refresh_data.py`'s automatic rankings-cache rebuild only rebuilds the term passed to
   `--term`.** A historical grade file (e.g., a Fall 2024 export) must be imported under its own
   real term (`--term 202408`), per README and D-04 — but the section that command's own run
   rebuilds the cache for is *also* 202408, not the live ranking term 202701. A **second**,
   grades-skipping run with `--term 202701` (or an equivalent direct call to
   `refresh_section_rankings(session, term="202701")`) is required before the imported history is
   visible in `GET /api/v1/rankings/search`. This is exactly the two-step pattern MVP1-P1's own
   proof test used.
3. **Grade-course resolution is atomic across the whole workbook, not per row.** A single
   unresolvable `(subject, course_number)` in the workbook — i.e., a course not present in the
   `courses` table — fails the **entire** import before any `GradeDistribution` row is written.
   Since the hosted DB currently has exactly 10 Course rows, a sourced export that includes any
   other course (very likely, since InfoCenter exports are typically scoped by subject/term, not
   by an arbitrary course list) will need to be pre-filtered to those 10 courses before import, or
   split per course, or the import will fail closed for the whole batch.

**Primary recommendation:** Do not build new ingestion code. Source one (or several) approved
InfoCenter XLSX export(s) covering the 10 currently-ingested Tampa courses — ACG 2021, ACG 2071,
AMH 2020, ANT 2000, BSC 1005, ECO 2013, ENC 1101, MAC 1105, MAC 2311, PSY 2012 — filter to rows
whose `(subject, course_number)` matches those 10, import per historical term with
`scripts/refresh_data.py --term <historical-term> --grade-file <path> --skip-catalog
--skip-schedule --skip-syllabi`, then run a second `--term 202701 --skip-catalog --skip-schedule
--skip-grades --skip-syllabi` pass to rebuild the live rankings cache, then validate with
`scripts/analyze_course.py` and `scripts/check_data_quality.py` per course.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sourcing the raw InfoCenter XLSX | External / Operator (Codex-owned) | — | D-08/D-09: bounded, narrow, approved USF ODS access; no scraping. Outside this codebase and outside this research agent's reach — an authenticated InfoCenter report (`report_type=SGDIS`), not a public endpoint. |
| XLSX schema validation + row parsing | Backend / Ingestion (`grades/parser.py`) | — | Already implemented; fails closed on schema mismatch, bucket-sum mismatch, and blank canonical count cells. No change needed. |
| Course attribution + upsert + dedup | Backend / Ingestion (`grades/ingest.py`) | Database (unique constraint) | `resolve_course_id()` + `uq_grade_distributions_term_crn_source` [VERIFIED: src/easy_a/models/core.py:90] `UniqueConstraint("term_id", "crn", "source", name="uq_grade_distributions_term_crn_source")`. Already implemented in MVP1-P1. |
| Rankings cache rebuild (`section_rankings`) | Backend / Derived cache (`rankings/cache.py`) | Orchestration (`refresh/service.py`) | Must be triggered for the **live ranking term**, independent of which term the grade file itself targets. |
| Per-course analytics validation | Backend / Analytics query (`analytics/queries.py`, `analytics/cli.py`) | Operator (manual diff vs. source workbook) | Existing `get_current_section_historical_analytics` + `scripts/analyze_course.py`; no new query layer needed. |
| "Lacking data" recording | Backend / Quality (`quality/checks.py`) | — | Already emits a per-section `no_historical_analytics` info finding when a section's course has no evidence; this satisfies "recorded as lacking it, never quietly omitted" without new code. |
| Raw-file exclusion from git | Repo hygiene (`.gitignore`) | Operator discipline | Already ignores `*.xlsx`, `*.xls`, `data/`, `research/raw/` [VERIFIED: .gitignore] — confirmed present; no change needed, but the operator must still avoid staging a file that bypasses these globs (e.g., renamed extension, or placed outside the ignored paths). |

## Standard Stack

No new external libraries or services are introduced by this phase. The parser already depends on
`pandas` and `openpyxl`, both already pinned in `pyproject.toml`.

### Core (already present — no install needed)
| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.5 installed; `pandas>=2.2.0` pinned [VERIFIED: pyproject.toml:14] `"pandas>=2.2.0",` | XLSX → DataFrame parsing in `grades/parser.py` | Already the project's chosen tabular-parsing library; `pd.read_excel(..., engine="openpyxl", dtype=object)` [VERIFIED: src/easy_a/grades/parser.py:139] |
| openpyxl | 3.1.5 installed; `openpyxl>=3.1.0` pinned [VERIFIED: pyproject.toml:13] `"openpyxl>=3.1.0",` | XLSX engine backing `pandas.read_excel` | Already the project's chosen XLSX engine; also used directly by tests to *build* synthetic workbooks (`openpyxl.Workbook`) [VERIFIED: tests/grades/test_ingest.py:7] `from openpyxl import Workbook` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing existing `grades/parser.py` + `grades/ingest.py` | Writing a new import script for this phase | Not needed and actively harmful — it would duplicate D-04 dedup/attribution logic that MVP1-P1 just hardened. Do not hand-roll a new import path. |

**Installation:** None required — no new packages.

## Package Legitimacy Audit

**Not applicable.** This phase installs no new external packages. `pandas` and `openpyxl` are
pre-existing pinned dependencies (`pyproject.toml:13-14`), already vetted at the time they entered
the project, and already present in the installed environment (`pandas 3.0.5`, `openpyxl 3.1.5`,
both confirmed installed via `uv run python -c "import pandas, openpyxl"` this session). If a plan
introduces any *new* package (e.g., a diffing/reporting helper), it must run the Package
Legitimacy Gate before being added — none was identified as necessary during this research.

## Architecture Patterns

### System Architecture Diagram

```
  [Approved USF InfoCenter                (Codex-owned, external, authenticated,
   grade-distribution XLSX export]  ─┐      bounded — D-08/D-09; never scraped)
                                     │
                                     ▼
                     [Operator: filter rows to the 10
                      Course rows already in Supabase]   (ACG 2021, ACG 2071, AMH 2020,
                                     │                     ANT 2000, BSC 1005, ECO 2013,
                                     ▼                     ENC 1101, MAC 1105, MAC 2311,
      scripts/refresh_data.py                             PSY 2012)
      --term <historical-term>
      --grade-file <path>
      --skip-catalog --skip-schedule --skip-syllabi
                                     │
                                     ▼
           grades/ingest.py: ingest_grade_file()
             ├─ parse_grade_workbook()  (grades/parser.py — schema + bucket-sum + blank-cell
             │                           fail-closed validation)
             ├─ _resolve_grade_course_ids()  (resolve_course_id() per distinct (subject,number);
             │                                whole workbook fails atomically on ANY miss)
             └─ upsert_grade_distributions()  (unique on term_id+crn+source; source_hash dedup)
                                     │
                                     ▼
                  GradeDistribution rows committed
              (term = historical term, course_id populated)
                                     │
                                     │   ⚠ same run's automatic cache rebuild only
                                     │     rebuilds the HISTORICAL term's cache — not 202701
                                     ▼
      scripts/refresh_data.py --term 202701
      --skip-catalog --skip-schedule --skip-grades --skip-syllabi
                                     │
                                     ▼
        rankings/cache.py: refresh_section_rankings(session, term="202701")
          └─ analytics/queries.py: get_current_section_historical_analytics()
               (aggregates GradeDistribution rows by course_id across ALL historical
                terms < 202701 — this is where the imported history actually reaches
                the live term's sections)
                                     │
                                     ▼
                 section_rankings cache rows updated
              (effective_n > 0, score_source = course, for courses with evidence;
               effective_n = 0, score_source = global, honestly, for courses without)
                                     │
                                     ▼
        GET /api/v1/rankings/search  /  scripts/analyze_course.py  /
        scripts/check_data_quality.py --term 202701
          (validation: per-course analytics vs. source workbook totals;
           no_historical_analytics info finding = honest "still lacking data" record)
```

### Recommended Import + Validation Flow (no new files)
```
1. (Codex-owned, external) Obtain approved InfoCenter XLSX for the target historical term(s).
2. Filter/split rows to only (subject, course_number) pairs already in `courses`.
3. Import with the ORCHESTRATING cli, not the standalone one, so provenance/cache wiring is exercised:
     uv run python scripts/refresh_data.py \
       --term <historical-Banner-term> \
       --grade-file <local-path-outside-git> \
       --skip-catalog --skip-schedule --skip-syllabi
4. Rebuild the LIVE ranking term's cache explicitly (does not happen automatically in step 3):
     uv run python scripts/refresh_data.py \
       --term 202701 \
       --skip-catalog --skip-schedule --skip-grades --skip-syllabi
5. Validate per course:
     uv run python scripts/analyze_course.py --term 202701 --subject <SUBJ> --course <NUM>
   Confirm effective_n > 0 and score_source == "course" for imported courses, and
   effective_n == 0 / score_source == "global" (never presented as course history) for
   still-uncovered courses.
6. Cross-check the report against the source workbook's own Total Grades sum per course
   (sum the workbook's rows for that (subject, number); compare to the DB's raw total, not the
   Bayesian-smoothed score — see "Code Examples").
7. Run the independent quality gate:
     uv run python scripts/check_data_quality.py --term 202701 --json
   Confirm 0 errors, and that `no_historical_analytics` only appears for genuinely
   uncovered courses (this IS the "recorded as lacking it" mechanism — see Pitfall 5).
```

### Pattern 1: Two-command import — never assume the auto cache rebuild covers the live term
**What:** `refresh_data()` always runs a `"rankings cache"` stage as its last step
[VERIFIED: src/easy_a/refresh/service.py:88-91]
```
    _run_stage(
        "rankings cache",
        lambda: _refresh_rankings_cache(factory, config.term),
    )
```
— but `config.term` is whatever `--term` was passed on *that* invocation. Importing a historical
grade file under `--term 202408` rebuilds the `202408` cache, not `202701`.
**When to use:** Every historical grade import where the grade file's own term differs from the
live ranking term (this is the normal case — grade history is, by definition, from a prior term).
**Example (the exact two-step pattern MVP1-P1's own integration proof used):**
```python
# Source: tests/test_grade_course_attribution.py (paraphrased call sequence, not literal code)
ingest_grade_file(session, term_code="202408", file_path=xlsx_path)   # historical term
session.commit()
refresh_section_rankings(session, term="202701")                      # LIVE ranking term
session.commit()
```
[VERIFIED: .planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-01-SUMMARY.md:108] "after
`refresh_section_rankings(session, term=\"202701\")`, `rank_section()`, the `SectionRankingCache`
row, `hydrate_ranking()`, and `GET /api/v1/rankings/search` all agree the section has
`effective_n > 0` / `score_source == \"course\"`, while a no-history control section stays an
explicit `effective_n == 0` / `score_source == \"global\"`"

### Pattern 2: Atomic whole-workbook course resolution
**What:** `_resolve_grade_course_ids()` resolves every distinct `(subject, course_number)` in the
parsed workbook *before* any `GradeDistribution` mutation; if any key is unresolved, the whole
import raises `GradeCourseResolutionError` and nothing is written.
[VERIFIED: src/easy_a/grades/ingest.py:156-179]
```python
def _resolve_grade_course_ids(
    session: Session,
    records: list[ParsedGradeDistribution],
) -> dict[tuple[str, str], int]:
    """Resolve every distinct parsed (subject, course_number) key before any
    GradeDistribution mutation. Unresolved keys are collected and reported together
    so the whole workbook fails atomically (D-04, D-06, D-07)."""
    distinct_keys = sorted({(record.subject, record.course_number) for record in records})
    resolved: dict[tuple[str, str], int] = {}
    unresolved_keys: list[tuple[str, str]] = []
    for subject, course_number in distinct_keys:
        try:
            resolved[(subject, course_number)] = resolve_course_id(session, subject, course_number)
        except CoreDataLookupError:
            unresolved_keys.append((subject, course_number))

    if unresolved_keys:
        unresolved_key_set = set(unresolved_keys)
        records_failed = sum(
            1
            for record in records
            if (record.subject, record.course_number) in unresolved_key_set
        )
        raise GradeCourseResolutionError(unresolved_keys, records_failed=records_failed)

    return resolved
```
**When to use:** Understand this before choosing how to scope the sourced workbook. If the
InfoCenter export naturally covers a whole subject or term (likely, since it is not filtered by an
arbitrary course list), it will almost certainly include courses outside the current 10-course
`courses` table — every one of those will abort the entire import, including rows for courses that
*would* have resolved cleanly.
**Recommendation:** Pre-filter the workbook (or split it into one workbook per resolvable course)
to only the 10 currently-present `(subject, number)` pairs before calling either CLI. This is an
operator/data-prep step, not new production code.

### Pattern 3: Grade rows don't require a matching historical Section
**What:** `_fetch_course_grade_observations` matches on `GradeDistribution.course_id.in_(course_ids)
OR Section.course_id.in_(course_ids)` via an `outerjoin` [VERIFIED: src/easy_a/analytics/queries.py:283-300],
so an imported historical grade row with no matching `(term, crn)` `Section` row still counts
toward the course's historical aggregate as long as `course_id` is attributed.
**When to use:** Confirms a historical export (e.g., a prior term's grades) does not require also
ingesting that historical term's *schedule* data — only the grade workbook itself, imported under
its own correct term.

### Anti-Patterns to Avoid
- **Assuming `grades/cli.py` accepts `--grade-file`:** it does not — `grades/cli.py` uses `--file`
  [VERIFIED: src/easy_a/grades/cli.py:14] `parser.add_argument("--file", required=True, type=Path, help="Path to the local XLSX export.")`.
  Using the standalone CLI is legitimate (it's what `tests/grades/test_ingest.py` and
  `tests/test_grade_course_attribution.py` exercise directly), but it does **not** rebuild the
  rankings cache at all — a manual `refresh_section_rankings(session, term="202701")` call (or the
  orchestrating CLI's cache-only pass from Pattern 1) is required afterward regardless of which
  ingest path is used.
- **Weakening the blank-cell fail-closed policy to "make an export import cleanly":** OQ-04 (real
  InfoCenter blank-cell semantics) is still unresolved. If the sourced export contains blank
  canonical-count cells, the correct action is to inspect them and record source-backed semantics
  (this phase is explicitly where that should happen per `04-02-SUMMARY.md`), not to patch the
  parser to coerce blanks to zero without evidence — that would violate D-06/D-07.
- **Committing the sourced XLSX, a derived CSV containing raw per-row data, or any file under an
  extension not covered by `.gitignore`:** violates D-19/BASE-04. Keep sourced files under
  `data/` (already ignored) or entirely outside the repository tree.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Grade-file schema validation | A new blank-cell / bucket-sum checker | `grades/parser.py` (`parse_grade_workbook`, `_cell_to_int`, bucket-sum check) | Already fails closed on the exact hazards this phase would otherwise reintroduce (OQ-04 blank cells, bucket-sum mismatch). Already covered by `tests/grades/test_ingest.py`. |
| Course/grade attribution | A grade-specific course matcher | `resolve_course_id()` (`common/lookups.py:33-49`) | MVP1-P1 deliberately unified grade attribution onto the shared lookup rather than a parallel matcher — reintroducing a separate one would reopen the exact bug that phase fixed. |
| Rankings recompute after import | A bespoke recompute script for this phase | `refresh_section_rankings()` (`rankings/cache.py:73`) via `scripts/refresh_data.py`'s cache-only stage | Already the sole source of truth for `section_rankings`; a parallel recompute would risk drifting from the cache the API actually serves. |
| "Courses lacking data" reporting | A new report/table listing course coverage gaps | `scripts/check_data_quality.py` (`no_historical_analytics` info finding, per section) | Already emits exactly this signal per section/course, already wired into the existing quality report used throughout the project's history. |
| Verifying import correctness | A custom diff tool against the XLSX | `scripts/analyze_course.py` + a manual sum of the workbook's own `Total Grades` column per course | `analyze_course.py` already prints effective N / confidence / score source per current section; the raw (unsmoothed) `total_grade_count` is available on `HistoricalOutcomeStats` for exact-count comparison against the source. |

**Key insight:** Every piece of infrastructure this phase needs to *touch* was purpose-built and
hardened in MVP1-P1 specifically so that MVP1-P2 would only need to supply data, not code. The
research risk in this phase is almost entirely operational (get the right file, scope it
correctly, run the right two commands, verify against the right numbers) rather than technical.

## Common Pitfalls

### Pitfall 1: Confusing `grades/cli.py --file` with `refresh/cli.py --grade-file`
**What goes wrong:** A plan literally following the phase description's text
("`grades/cli.py`, `--grade-file`") will fail immediately — that flag does not exist on that CLI.
**Why it happens:** The phase description conflates the two grade-ingest entry points; only one of
them (`refresh/cli.py` / `scripts/refresh_data.py`) actually has a flag named `--grade-file`.
**How to avoid:** Use `scripts/refresh_data.py --grade-file <path> --term <term> --skip-catalog
--skip-schedule --skip-syllabi` for imports where the automatic cache-rebuild stage is desired (it
still only rebuilds the term passed, per Pitfall 2), or `scripts/ingest_grades.py --file <path>
--term <term>` for a grade-only import with the standalone CLI (never rebuilds any cache — a
manual follow-up rebuild is required either way for the *live* term).
**Warning signs:** `argparse` "unrecognized arguments: --grade-file" or "the following arguments
are required: --file" from `grades/cli.py`.

### Pitfall 2: Importing a historical grade file does not update the live term's rankings cache
**What goes wrong:** Sections stay at `effective_n = 0` / `score_source = global` in
`GET /api/v1/rankings/search` even after a grade import that reports `inserted=N` rows and exits 0.
**Why it happens:** `_refresh_rankings_cache(factory, config.term)` in `refresh_data()`
[VERIFIED: src/easy_a/refresh/service.py:88-91] runs against whatever term was passed to
`--term` on that command — the historical term, not 202701.
**How to avoid:** Always run a second cache-only pass with `--term 202701 --skip-catalog
--skip-schedule --skip-grades --skip-syllabi` after any historical grade import (or call
`refresh_section_rankings(session, term="202701")` directly).
**Warning signs:** `scripts/analyze_course.py --term 202701 ...` still shows `Source: global` and
`Effective N: 0.0` for a course that was just imported.

### Pitfall 3: One bad course row silently kills an entire multi-course import
**What goes wrong:** An operator imports a subject-wide InfoCenter export (e.g., all `MAC` grade
rows for a term) expecting the 2 resolvable courses (`MAC 1105`, `MAC 2311`) to succeed and the
rest to be skipped; instead the whole run fails and *zero* rows are written, with the ingest run
marked `"failed"`.
**Why it happens:** `_resolve_grade_course_ids()` collects every unresolved `(subject,
course_number)` and raises before any row is written [VERIFIED: src/easy_a/grades/ingest.py:172-179]
"if unresolved_keys: ... raise GradeCourseResolutionError(unresolved_keys, records_failed=records_failed)".
This is intentional (D-04/D-06/D-07 — a partially-attributed workbook is worse than an explicit
failure), not a bug to work around by loosening it.
**How to avoid:** Pre-filter the sourced workbook to only the 10 courses currently present in
`courses`, or split the source export into one workbook per course/subset before import. Re-run
per historical term with only the rows that will resolve.
**Warning signs:** `Grade ingest failed: Grade workbook references N unresolved course(s): ...`
printed by the CLI; `ingest_runs.status = 'failed'`.

### Pitfall 4: "Validate against the source aggregate" must compare raw counts, not the smoothed score
**What goes wrong:** Comparing the *displayed* historical easiness score (0–10, Bayesian-shrunk,
subject/global-fallback-blended) against the workbook's raw grade counts will never match — that's
expected behavior, not a bug, and treating a mismatch there as a validation failure would be wrong.
**Why it happens:** `compute_historical_outcome_stats()` intentionally smooths small samples toward
a prior [VERIFIED: src/easy_a/analytics/scoring.py:98-143] — `grade_favorability_smoothed`,
`withdrawal_rate_smoothed`, and `easiness_score` are all shrunk; only `completed_grade_count`,
`total_grade_count`, and `withdrawal_count` on `HistoricalOutcomeStats` are raw, unweighted actual
sums pulled straight from the stored `GradeDistribution` rows.
**How to avoid:** Validate by summing the source workbook's own `Total Grades` (and per-bucket)
column for a given `(subject, course_number)` and comparing against the raw counts, either via a
direct SQL sum on `grade_distributions` for that `course_id`, or by extending the validation task
to read `HistoricalOutcomeStats.total_grade_count` rather than `easiness_score`.
**Warning signs:** A "validation failure" report where the smoothed score differs from a raw
percentage in the source file — that is normal Bayesian shrinkage, not a data-integrity bug.

### Pitfall 5: Believing "courses lacking data" needs new tracking
**What goes wrong:** A plan adds a new table/column/report to track "which courses still lack
grade data," duplicating existing functionality.
**Why it happens:** The phase's success criterion reads like a net-new feature ("record courses
still lacking data as lacking it, never quietly omitted"), but the mechanism already exists.
**How to avoid:** `_check_analytics()` already emits a `no_historical_analytics` info finding per
section whenever `stats is None or stats.section_count == 0 or stats.total_grade_count == 0`
[VERIFIED: src/easy_a/quality/checks.py:448-461]. Confirm via `scripts/check_data_quality.py
--term 202701 --json` after import; a course that legitimately still lacks any historical grade
data will continue to show this info finding, which already satisfies "recorded as lacking it."
No new code is needed — only running and reading this existing report as verification evidence.
**Warning signs:** A plan task titled "add data-lacking tracking" or similar when
`check_data_quality.py` already reports it.

### Pitfall 6: Filename/session leakage as an unintentional term source
**What goes wrong:** Assuming a workbook named e.g. `fall-2024-grades.xlsx` is safe to import
under whatever term is "current" without checking; or worse, writing tooling that infers the term
from the filename.
**Why it happens:** The workbook itself carries no trusted term field.
**How to avoid:** Already enforced by design — `--term` is always required and independent of
filename [VERIFIED: README.md] "`--grade-file` belongs to exactly the `--term` supplied on that
command. The workbook does not encode a trusted term, and its filename is never used as term
metadata." The planner's job is to make sure whoever sources the file also supplies (and the
operator confirms) the file's *actual* historical Banner term before it's imported — this is a
process discipline item, not a code change.

## Code Examples

### Two-step historical import + live-cache rebuild (operator commands, not new code)
```powershell
# Step 1: import the approved historical grade export under its OWN real term.
uv run python scripts/refresh_data.py `
  --term 202408 `
  --grade-file C:\private\infocenter-grades-fall2024.xlsx `
  --skip-catalog --skip-schedule --skip-syllabi

# Step 2: rebuild the LIVE ranking term's cache so the import is actually visible in search.
uv run python scripts/refresh_data.py `
  --term 202701 `
  --skip-catalog --skip-schedule --skip-grades --skip-syllabi
```
[Pattern derived from README.md's documented grade-only historical import example plus
`refresh/service.py`'s unconditional `"rankings cache"` stage; the two-command split is inferred
from reading the code, not stated as a single documented recipe anywhere in the repo — flag this
explicitly to the operator in the plan.]

### Per-course validation
```powershell
uv run python scripts/analyze_course.py --term 202701 --subject AMH --course 2020
# Expect: Source column == "course" and Effective N > 0.0 for an imported course;
#         Source column == "global" and Effective N == 0.0, honestly, for a still-uncovered course.

uv run python scripts/check_data_quality.py --term 202701 --json
# Expect: 0 errors; no `unattributed_grade_row` or `grade_total_mismatch` findings;
#         `no_historical_analytics` present ONLY for genuinely uncovered courses.
```
[Source: `src/easy_a/analytics/cli.py`, `README.md` "Historical Analytics" / "Data Quality"
sections — both existing, already-documented commands.]

## State of the Art

Not applicable — no framework/library version drift is relevant here; the parser, ingest, and
cache code were all authored and hardened within this same milestone (MVP1-P1, 2026-09-21).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The InfoCenter export, once sourced, will be a single workbook (or small set of workbooks) covering multiple courses/subjects at once rather than one file per course — driving the "pre-filter or split" recommendation in Pitfall 3. | Architecture Patterns / Common Pitfalls | If the sourcing task instead produces one clean workbook per course already, the pre-filter/split step is unnecessary busywork, not wrong — low risk either way, but the plan should treat it as conditional on what the sourced file actually contains. |
| A2 | The two-command (historical-term import + separate 202701 cache rebuild) pattern is the correct way to make imported history visible in search; no single-command path does both correctly for a historical term. | Architecture Patterns Pattern 1, Code Examples | Confirmed directly from `refresh/service.py` reading `config.term` for the cache stage — HIGH confidence, not really assumption-level, but flagged here because no single doc in the repo states the two-step recipe explicitly; it's synthesized from code. |
| A3 | A real InfoCenter export may or may not contain blank canonical-count cells; if it does, the parser will reject those rows (by design) and the plan should treat inspecting a real export as the moment to finally resolve OQ-04, not as a bug to patch around. | Open Questions | If the real export never has blanks, OQ-04 remains open but non-blocking for this phase's data; if it does have blanks and they get misinterpreted, D-06/D-07 honesty could be silently violated. |

## Open Questions

1. **What does a blank canonical grade-count cell mean in a real USF InfoCenter export? (OQ-04, carried over from MVP1-P1)**
   - What we know: the parser currently rejects any blank canonical count cell with an explicit,
     non-suppression-asserting error rather than guessing [VERIFIED: src/easy_a/grades/parser.py:277-282].
     No public USF documentation found this session resolves whether blank means zero, suppressed
     (e.g., small-cell privacy suppression), or unavailable — a targeted web search for USF
     InfoCenter grade-distribution blank-cell/suppression semantics returned only the report portal
     itself (an authenticated `report_type=SGDIS` report) and no technical documentation.
   - What's unclear: whether the actually-sourced export for this phase will even contain blank
     cells at all, and if so, what they mean.
   - Recommendation: this phase is exactly where a real/sample export should finally be inspected
     for this. If blanks appear, do not patch the parser to coerce them without a source-backed
     answer — record the observation and escalate to the ODS/registrar-access owner rather than
     guessing (D-06/D-07).

2. **Which historical term(s) does the sourced export actually cover, and does it need multiple separate import runs?**
   - What we know: the parser and ingest layer both operate on exactly one `--term` per invocation;
     multi-term coverage requires multiple import runs, one per historical term.
   - What's unclear: whether the Codex-owned sourcing step will produce one workbook per term or a
     combined one, since that decision is external to this codebase.
   - Recommendation: the plan should treat "how many historical terms are covered" as a fact to be
     established once the export arrives, and structure the import step as a loop over
     whatever terms are actually present, each followed by the mandatory `--term 202701` cache
     rebuild only once at the end (rebuilding it after each term is harmless but redundant).

3. **Import priority across the 10 currently-ingested courses.**
   - What we know: the superseded Phase 3 text in ROADMAP.md named a priority order (AMH 2020 →
     PSY 2012 → BSC 1005) from the earlier 5-course pilot; REQ-GRADES-01 and the current phase text
     say "ingested Tampa courses" generally (all 10: ACG 2021, ACG 2071, AMH 2020, ANT 2000,
     BSC 1005, ECO 2013, ENC 1101, MAC 1105, MAC 2311, PSY 2012).
   - What's unclear: whether that historical 3-course priority ordering still applies, or whether
     this phase should treat all 10 as equal priority (the ROADMAP's Phase 5 text does not restate
     a priority order).
   - Recommendation: without a CONTEXT.md decision to the contrary, treat all 10 currently-ingested
     courses as in scope; import whatever the sourced export covers and record the remainder as
     honestly lacking data via the existing `no_historical_analytics` mechanism — do not fabricate
     urgency ordering not stated in the current phase scope.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Running any `scripts/*.py` command | ✓ | 0.12.17 | — |
| Python | Runtime | ✓ | 3.14.4 (uv-managed venv; project targets 3.12 per `pyproject.toml` `target-version = "py312"`) | — |
| pandas | XLSX parsing | ✓ | 3.0.5 (pinned `>=2.2.0`) | — |
| openpyxl | XLSX engine | ✓ | 3.1.5 (pinned `>=3.1.0`) | — |
| `DATABASE_URL` (Supabase pooler) | All scripts read this via `get_session_factory()` → `get_settings().require_database_url()` | ✗ in this shell (not exported); `.env` file exists in repo root | — | Operator must ensure `DATABASE_URL` (and optionally `MIGRATION_DATABASE_URL`) is set/sourced before running any import or cache-rebuild command against the hosted Supabase DB — this is an existing, already-documented requirement (README "Environment" section), not new setup work for this phase. |
| Approved InfoCenter XLSX export | The entire phase | ✗ — not yet sourced (Codex-owned, external) | — | None — this is the phase's actual blocking dependency; everything else in this research assumes it exists. |

**Missing dependencies with no fallback:**
- The approved InfoCenter XLSX export itself. Nothing in this phase can proceed without it; the
  Codex-owned sourcing task is the true critical path.

**Missing dependencies with fallback:**
- `DATABASE_URL` not exported in the research shell — expected to be operator-configured per
  existing README instructions before any script in this phase runs; not a new gap this phase
  introduces.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest, `testpaths = ["tests"]` [VERIFIED: pyproject.toml] `testpaths = ["tests"]` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/grades tests/analytics tests/test_grade_course_attribution.py tests/test_grade_schedule_integration.py -q` |
| Full suite command | `uv run pytest -q` (261 passed / 3 skipped without PostgreSQL, per the latest recorded baseline after MVP1-P1 — see `.planning/STATE.md`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-GRADES-01 | Grade workbook parses and attaches to an existing course; whole-workbook atomic failure on unresolved course | unit | `uv run pytest tests/grades/test_ingest.py -q` | ✅ |
| REQ-GRADES-01 | End-to-end: generated historical XLSX → rebuilt cache → API reflects `effective_n>0`/`score_source=course` vs. honest `effective_n=0`/`score_source=global` control | integration | `uv run pytest tests/test_grade_course_attribution.py -q` | ✅ |
| REQ-GRADES-01 | `unattributed_grade_row` / `orphan_grade_row` / `grade_total_mismatch` / `no_historical_analytics` quality findings | integration | `uv run pytest tests/test_grade_schedule_integration.py -q` (and via `scripts/check_data_quality.py`, manual, against the real Supabase data post-import) | ✅ |
| REQ-GRADES-01 | Bayesian smoothing / raw-vs-smoothed count distinction (used for the "validate against source aggregate" step) | unit | `uv run pytest tests/analytics/test_grades_and_scoring.py -q` | ✅ |

**This phase adds no new production code path**, so no new automated test is strictly required
by the existing suite's shape — the phase's own verification is inherently a **data**
verification (does the real import produce the numbers the source workbook says it should),
which is manual/operational (`analyze_course.py`, `check_data_quality.py`) rather than a new
pytest case. If the plan chooses to encode the real export's blank-cell behavior as a fixture
(addressing OQ-04), that would be the one place a genuinely new unit test belongs — in
`tests/grades/test_ingest.py` or a new `tests/grades/test_parser_real_export_shape.py`.

### Sampling Rate
- **Per task commit:** `uv run pytest tests/grades tests/analytics tests/test_grade_course_attribution.py -q`
- **Per wave merge:** `uv run pytest -q` (full suite)
- **Phase gate:** Full suite green, plus a real (non-test) run of `scripts/check_data_quality.py
  --term 202701 --json` against the actual post-import hosted Supabase state, before
  `/gsd-verify-work`.

### Wave 0 Gaps
None — existing test infrastructure (`tests/grades/`, `tests/analytics/`,
`tests/test_grade_course_attribution.py`, `tests/test_grade_schedule_integration.py`) already
covers every code path this phase touches. The phase's actual gate is real-data validation, not
new test coverage.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth surface touched by this phase. |
| V3 Session Management | No | Not applicable. |
| V4 Access Control | No | Not applicable — no new endpoint or role. |
| V5 Input Validation | Yes | Already implemented in `grades/parser.py`: strict schema-column resolution, numeric-type coercion with explicit rejection of non-numeric/boolean/fractional cells, bucket-sum-equals-Total-Grades cross-check, and fail-closed blank-cell rejection. No new validation code needed; this phase's job is to exercise that validation against real data and observe what it rejects. |
| V6 Cryptography | No | `source_hash` uses SHA-256 for dedup/provenance [VERIFIED: src/easy_a/grades/ingest.py:184-189] `def hash_file(path: Path) -> str: digest = hashlib.sha256()` — already correct (a standard library hash, not hand-rolled), not a cryptographic-secrecy use case; no change needed. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/adversarial XLSX causing silent data corruption (e.g., a blank cell misread as zero, inflating a course's apparent good-outcome rate) | Tampering | Already mitigated: fail-closed blank-cell rejection (MVP1-P1) + bucket-sum-vs-Total-Grades cross-check reject any row where the parts don't add up. |
| Duplicate/re-exported workbook silently double-counting grade outcomes | Tampering / Repudiation | Already mitigated: `uq_grade_distributions_term_crn_source` + `source_hash`-aware upsert (only mutates when content actually differs) [VERIFIED: src/easy_a/grades/ingest.py:238-261]. |
| Committing an authenticated/raw InfoCenter export into git history (credential/data-access-scope leakage, and a compliance violation of the USF ODS approval's aggregate-only scope) | Information Disclosure | `.gitignore` already excludes `*.xlsx`, `*.xls`, `data/`, `research/raw/`; operator discipline (never stage the file, keep it outside the repo tree or under an already-ignored path) is the remaining control — this is a process step to include explicitly in the plan's task list, not a code change. |
| A course silently presented with a misleadingly high easiness score because a global-prior fallback score is mistaken for course-specific evidence | Repudiation / honesty (D-06/D-07/D-20, project-specific, not literal STRIDE) | `score_source` and `effective_n` are already always present and already distinguish `global` from `course`/`subject`/`instructor_course`; this phase's validation step (`analyze_course.py`) is the check that this distinction is actually true post-import, not just theoretically correct. |

## Sources

### Primary (HIGH confidence — read directly this session)
- `src/easy_a/grades/parser.py` — full read; exact required column set, blank-cell fail-closed
  behavior, section-identifier regex.
- `src/easy_a/grades/ingest.py` — full read; atomic course-resolution behavior, upsert/dedup logic,
  `hash_file`.
- `src/easy_a/grades/cli.py` — full read; confirms `--file`, not `--grade-file`.
- `src/easy_a/refresh/cli.py` — full read; confirms `--grade-file` lives here, term-required design.
- `src/easy_a/refresh/service.py` — full read; confirms the unconditional cache-rebuild stage keys
  off `config.term`.
- `src/easy_a/refresh/models.py` — full read; `GradeInput`, `RefreshConfig` shapes.
- `src/easy_a/rankings/cache.py` — full read; `refresh_section_rankings()` behavior and its
  dependency on `get_current_section_historical_analytics`.
- `src/easy_a/analytics/queries.py` — full read; course/subject/global fallback resolution, the
  `Section` outerjoin that lets orphan-of-current-term grade rows still count.
- `src/easy_a/analytics/scoring.py` — full read; raw vs. smoothed count fields on
  `HistoricalOutcomeStats`.
- `src/easy_a/analytics/grades.py` — full read; `HistoricalGradeAggregate` raw-count fields.
- `src/easy_a/analytics/cli.py` — full read; `scripts/analyze_course.py`'s exact output columns.
- `src/easy_a/analytics/confidence.py` — full read; confidence-label thresholds, `ScoreSource` enum.
- `src/easy_a/quality/checks.py` (relevant sections) — `unattributed_grade_row`, `orphan_grade_row`,
  `grade_total_mismatch`, `no_historical_analytics`, `low_confidence_ranking` check definitions.
- `src/easy_a/common/lookups.py` — full read; `resolve_course_id()` exact matching behavior.
- `src/easy_a/models/core.py` (`GradeDistribution` model) — confirmed unique constraint and column
  shape.
- `src/easy_a/db.py` — confirmed `DATABASE_URL` / Supabase pooler handling.
- `tests/grades/test_ingest.py` — confirmed exact header shape used for synthetic workbooks and CLI
  entry point under test.
- `README.md` (Real-Data Refresh, Grade Distribution Ingestion, Historical Analytics, Data Safety
  sections) — confirmed documented column list, term-vs-filename rule, `.gitignore` scope, ODS
  approval framing.
- `.gitignore` — confirmed `data/`, `research/raw/`, `*.xlsx`, `*.xls` are ignored.
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`,
  `AGENTS.md`, `CLAUDE.md` — full read for requirements, decisions (D-01..D-20), current DB state
  (10 courses, 0 grade rows), and phase sequence.
- `.planning/phases/04-mvp1-p1-grade-course-attribution-fix/04-01-SUMMARY.md`,
  `04-02-SUMMARY.md` — confirmed the exact end-to-end proof pattern (historical import +
  `refresh_section_rankings(term="202701")` + API check) and that OQ-04 remains open by design.
- `phase1_report.md` (repo root, untracked) — confirmed the current 10-course/132-section state and
  that the coverage pilot deliberately left grades untouched (0 before / 0 after).
- Direct environment probes this session: `uv --version` (0.12.17), `python3 --version` (3.14.4),
  `uv run python -c "import pandas, openpyxl"` (pandas 3.0.5, openpyxl 3.1.5 confirmed installed).

### Secondary (MEDIUM confidence)
- None used as load-bearing for a specific claim beyond what Primary sources already establish for
  this phase.

### Tertiary (LOW confidence)
- WebSearch: "USF InfoCenter grade distribution report blank cell suppression export" — returned
  only the InfoCenter portal itself (`report_type=SGDIS`, an authenticated report, consistent with
  D-08/D-09's "no scraping" framing and with this phase's sourcing being Codex-owned/external) and
  no technical documentation resolving OQ-04. This search did not add new authoritative
  information beyond what MVP1-P1's own research already established; recorded here to show the
  question was re-checked, not newly answered.

## Metadata

**Confidence breakdown:**
- Standard stack / existing tooling shape: HIGH — every claim traced to a specific file and line
  read this session.
- Architecture (two-step import + cache rebuild, atomic course resolution): HIGH — derived
  directly from reading `refresh/service.py` and `grades/ingest.py`, and cross-confirmed against
  MVP1-P1's own integration-test proof sequence.
- Pitfalls: HIGH for the code-level ones (CLI flag mismatch, atomic failure, cache-rebuild
  scoping — all directly observed in source); LOW for the external sourcing-format specifics
  (actual real-export shape, real blank-cell semantics — genuinely unknown until an export exists).
- Sourcing process itself (how to actually obtain the approved XLSX): LOW/out of scope — explicitly
  Codex-owned per the phase description; this research could not and did not attempt to source
  data, only to characterize what the sourced data must look like to import cleanly.

**Research date:** 2026-09-21
**Valid until:** Until the sourced InfoCenter export actually arrives and is inspected (at which
point OQ-04 and the "how many terms / what scope" open questions should be resolved with real
evidence rather than this research's structural analysis) — no fixed expiry otherwise, since the
underlying codebase this research describes is stable within this milestone.
