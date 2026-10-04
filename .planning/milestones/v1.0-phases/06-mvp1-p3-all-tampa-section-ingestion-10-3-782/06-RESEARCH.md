# Phase 6: MVP1-P3 — All-Tampa section ingestion (10 → ~3,782) - Research

**Researched:** 2026-09-21
**Domain:** Scaling an existing target-driven USF ingestion pipeline (catalog + schedule) from 10 to ~1,402 courses / ~3,782 sections, in-repo (no new external services)
**Confidence:** HIGH — every claim below is grounded in code actually read this session, an existing unit test, and an in-repo prior pilot report with real, dated, measured results.

<user_constraints>
## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase — the user chose to continue without `/gsd-discuss-phase`.
There are no captured user design decisions. The design forks below (target-list generation
strategy, subject-level vs per-course schedule ingest, whether to commit the generated target
list) are **not locked** and must be surfaced to the user/planner explicitly, either via
`/gsd-discuss-phase` before planning or as explicit checkpoints inside the plan.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| REQ-COVERAGE-03 | All ~3,782 USF Tampa Spring 2027 sections ingested and searchable; CHM 2045/2045L suffix guard resolved without weakening it; config and stored data reconciled. | See Standard Stack, Architecture Patterns, Runtime State Inventory, and Common Pitfalls below — the ingestion mechanism, the suffix fix, and the reconciliation path are all identified and grounded in code/tests already in the repo. |
</phase_requirements>

## Summary

This phase does not need new libraries, new external services, or a new ingestion architecture.
It needs to **scale an existing, already-correct architecture** from 10 configured courses to the
full enumerated Tampa Spring 2027 universe, and to close three concrete gaps: (1) catalog rows for
~1,392 not-yet-catalog-ingested courses must exist before `resolve_course_id` can attach sections
to them; (2) the schedule side needs a decision between reusing the existing per-course
target-loop (`refresh_targets`) at ~1,402x scale, or writing a new subject-level ingestion path;
(3) `config/course_targets.toml` (5 entries) must be reconciled against the 10 courses actually
stored, and then against the full ~1,402-course universe.

The most important finding from reading the code directly: **the CHM 2045 / 2045L suffix-guard
fix already exists and is already merged.** `_retain_exact_course_rows` in
`src/easy_a/refresh/coverage.py` (added in commit `8ea08db`, 2026-09-20 14:02, as part of Phase
03.5) already excludes non-matching suffix rows from the HTML *before* ingestion, rather than
rejecting the whole response — and `tests/refresh/test_coverage_suffix_guard.py` already asserts
exactly this behavior for a synthetic CHM 2045/2045L mix. The pilot failure described in
`phase1_report.md` (`Verified 2026-09-20T07:44:55`) happened *before* this fix landed the same
afternoon. STATE.md/ROADMAP.md still describe the suffix guard as an open blocker — that
description is stale relative to the code on disk. The planner's job for item 3 is not "invent a
fix," it is "validate the existing fix generalizes correctly across all 33 affected base courses at
full scale," plus the config/stored-data reconciliation.

The second most important finding: **catalog ingestion has no bulk path.** The configured
`catalog_url_template` (`https://cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}`)
returns exactly one course per page — confirmed by fetching it live for CHM 2045 this session — so
catalog-ingesting all ~1,402 courses requires ~1,402 individual bounded HTTP GETs regardless of
which schedule-ingestion strategy is chosen. This is the dominant cost/risk driver of the phase,
not the schedule side.

The third important finding, from actually reading `target_cli.py` and `coverage.py`: **the
existing CLI wraps the entire configured target list in one database transaction**
(`get_session_factory().begin()` around the whole `refresh_targets` loop). At 5–10 targets this is
harmless. At ~1,402 targets run sequentially against live USF endpoints over what will likely be
tens of minutes, a single transient failure partway through discards *all* prior successful work
in that invocation. This is a genuine scaling gap the current code does not handle, and the plan
must address it (batching/commit boundaries + resumability), or it will re-run 1,400 successful
network calls after every transient failure.

**Primary recommendation:** Reuse the existing, already-tested, already-guard-proven per-course
target loop (`refresh_targets` / `refresh_course_coverage.py`) rather than writing a new
subject-level ingestion code path. Generate the full ~1,402-entry target list from the enumeration
already sitting in the repo (`courses.csv`, unverified fresh, dated 2026-09-20), validate it against
the existing `CourseTarget` Pydantic pattern (already confirmed to accept every row), and drive the
existing CLI **in per-subject batches** using its existing `--subject` filter — each subject
invocation is its own process/transaction, giving natural, zero-new-code checkpointing. Do not
build a new subject-level bulk-schedule-search code path for this phase; it would roughly halve
total HTTP requests (schedule side only — catalog is unavoidably ~1,402 requests either way) at the
cost of new, untested ingestion logic during a phase the roadmap itself calls a "large lift." That
trade is not worth it here; it is a legitimate Phase 7+ optimization if runtime becomes a problem.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Course catalog enumeration/ingestion (1,402 courses) | Ingestion pipeline (`src/easy_a/catalog/`) | — | Populates the `courses` table `resolve_course_id` depends on; no browser/API tier involvement |
| Schedule/section ingestion (~3,782 sections) | Ingestion pipeline (`src/easy_a/refresh/`, `src/easy_a/schedule/`) | Database / Storage | Writes `Section`, `SeatSnapshot`, `SectionInstructor` rows; campus/suffix guards live here |
| Suffix-course (CHM 2045 vs 2045L) disambiguation | Ingestion pipeline (`coverage.py::_retain_exact_course_rows`) | — | Already implemented at HTML-filtering layer before DB write; not an API/frontend concern |
| Target-list config reconciliation (5 vs 10 vs ~1,402) | Ingestion pipeline / Config (`config/course_targets.toml`, `src/easy_a/refresh/targets.py`) | — | Pydantic-validated config file drives the CLI; no runtime/API impact once resolved |
| Coverage/quality reporting at scale | API / Backend (`GET /api/v1/metadata/coverage`, `scripts/check_data_quality.py`) | Database | Reads already-ingested rows; must remain correct as row counts grow ~29x |
| Search/ranking of the expanded section set | API / Backend + Database | — | Out of scope for this phase (Phase 7, REQ-PERF-01) — do not tune search here, only ensure sections are ingested and searchable in the existing sense |

## Standard Stack

No new libraries are required. Every mechanism this phase needs (HTTP client, HTML parsing,
Pydantic config validation, SQLAlchemy upsert, ORM session/transaction) already exists and is
already exercised at small scale by the current 10-course pilot.

### Core (existing, reused as-is)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `httpx` | pinned in repo lockfile (not re-verified this session; unchanged usage) | Bounded HTTP GET/POST to USF public endpoints (`catalog/client.py`, `schedule/client.py`) | Already the project's sole HTTP client; no reason to add another |
| `beautifulsoup4` + `lxml` | pinned in repo lockfile (unchanged usage) | Parse catalog/schedule HTML, including the existing suffix-row-decompose mechanism | Already the project's sole HTML parser; the suffix fix depends on `BeautifulSoup`/`Tag` semantics already in use |
| `pydantic` | pinned in repo lockfile (unchanged usage) | `CourseTarget`/`CourseTargets` validation of the generated ~1,402-entry target list | Already validates every field pattern this phase needs — confirmed against real data this session (see Package Legitimacy Audit / verification below) |
| SQLAlchemy ORM | pinned in repo lockfile (unchanged usage) | `resolve_course_id`, upserts in `catalog/ingest.py` and `schedule/ingest.py` | Already the project's sole persistence layer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `tomllib` (stdlib) | Python 3.12+ stdlib | Parse the generated target-list TOML (`targets.py::load_targets`) | Already used; if the generated list is emitted as TOML rather than committed inline, no new dependency needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-course catalog detail page (`cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}`) | A CourseLeaf subject-listing page on `catalog.usf.edu` (the 2026-2027 undergraduate catalog is hosted there per this session's web search) that may return multiple `.courseblock` elements per request, which `parse_catalog_html` already supports natively | **Not verified this session** — I confirmed `catalog.usf.edu` exists and hosts a CourseLeaf-style 2026-2027 undergraduate catalog, but did not fetch a subject-level page to confirm it returns multiple `.courseblock` records for USF specifically, nor whether the fields it exposes (credits/description/prerequisites/attributes) match what the currently-configured source provides. If confirmed by a single bounded probe fetch, this could cut catalog-ingestion HTTP volume from ~1,402 to ~212 requests. Treat as an open question / optional Phase 6 spike, not a default plan. `[ASSUMED]` |
| Per-course exact-match schedule search, looped 1,402 times (reuses `refresh_targets`) | A new subject-level schedule search (`ScheduleSearchQuery(term=..., campus="T", subject=target.subject)` with `course=None`) issued once per subject (~212 requests per `phase1_report.md`'s own enumeration method), followed by new code to group/guard/ingest all courses under that subject in one response | Subject-level cuts schedule-side HTTP volume ~85% but requires **new, untested production code** (grouping parsed rows by `(subject, number)`, extending the Tampa-campus guard to apply across all rows instead of one target's rows, and widening the transaction blast radius to "one subject's ~1–33 courses" instead of "one course"). Catalog ingestion remains ~1,402 requests either way, so this optimizes the smaller of the two costs. Recommend deferring unless total runtime proves to be a hard blocker. |
| Single 1,402-target transaction (today's `target_cli.py` behavior) | Per-subject-batched invocations of the existing CLI (`--subject` filter already exists), each its own process/transaction | Batching by subject requires **zero new production code** (the `--subject` filter is already implemented and tested) and bounds the blast radius of any single failure to one subject's courses (1–33) instead of all 1,402. Strongly recommended — see Common Pitfalls. |

**Installation:** None — no new packages.

**Version verification:** Not applicable; no new packages. Existing pinned versions in
`pyproject.toml`/lockfile are unchanged by this phase's scope.

## Package Legitimacy Audit

**Not applicable.** This phase introduces no new external packages. No install commands are
added to any environment. The Package Legitimacy Gate protocol was not run because there is
nothing to audit — `git diff`-equivalent scope for this phase is pure application code + generated
config data, not `pyproject.toml`/`package.json` changes.

## Architecture Patterns

### System Architecture Diagram

```
courses.csv (enumeration snapshot, git-ignored, dated 2026-09-20)
        |
        v
 [generate full target list]  <-- NEW: small script, reuses CourseTarget/CourseTargets validation
        |
        v
 config/course_targets.toml  (or a --targets override path)   <-- reconciles item 3
        |
        v
 scripts/refresh_course_coverage.py --term 202701 --targets <path> --subject <SUBJ>
   (invoked once per subject, ~212 sequential subject batches -- NEW orchestration, no new
    production code; reuses --subject filter that already exists in target_cli.py)
        |
        v
 refresh_targets()  [src/easy_a/refresh/coverage.py]  -- existing, per target within the batch:
   1. fetch catalog detail page (1 HTTP GET per course)          --> upsert_catalog_courses()
   2. confirm Course row now present                              --> resolve_course_id() precondition
   3. schedule search P_SUBJ+P_NUM exact match (1 HTTP POST)       --> parse_schedule_html()
   4. _retain_exact_course_rows() decomposes CHM-2045L-style       --> suffix guard (ALREADY FIXED,
      suffix rows from the raw HTML before ingest                     see Common Pitfalls)
   5. Tampa/course/CRN scope assertion on the exact-match subset    --> raises + rolls back the
                                                                         CURRENT TRANSACTION on violation
   6. ingest_schedule_html() -> Section/SeatSnapshot/SectionInstructor upserts, resolve_course_id()
   7. refresh_section_rankings(term, subject, course_number)        --> section_rankings cache row(s)
        |
        v
 scripts/check_data_quality.py --term 202701 --json   -- existing, must report 0 errors at scale
        |
        v
 GET /api/v1/metadata/coverage , GET /api/v1/rankings/search        -- existing, must agree with DB
```

A reader can trace the primary flow: enumeration snapshot -> generated target list -> per-subject
batched CLI invocation -> existing per-course catalog+schedule ingest loop (with the suffix guard
already inside it) -> existing quality/coverage verification. No new persistence model, no new API
route, no new frontend work.

### Recommended Project Structure

No new top-level packages. Only additions:

```
scripts/
├── refresh_course_coverage.py   # existing, reused unmodified (accepts --targets, --subject)
├── generate_tampa_targets.py    # NEW: reads courses.csv (or re-enumerates), emits a validated
│                                 #      CourseTargets-shaped TOML/JSON; validates every row against
│                                 #      the existing CourseTarget pattern before writing
config/
└── course_targets.toml          # RECONCILE: decide whether this becomes the full ~1,402-entry
                                  #            list (see Open Questions) or stays a small pilot
                                  #            default with the full list passed via --targets
```

### Pattern 1: Reuse the existing per-target loop, do not rewrite it

**What:** `refresh_targets(session, term=..., config=..., search=..., refresh_catalog=True, subject=<one subject>)`
already does catalog-ingest-then-schedule-ingest-then-cache-refresh, per course, with the Tampa
guard and the suffix-row filter already inside it.

**When to use:** For every course in the generated target list. This is the only ingestion path
this phase needs.

**Example (existing code, unmodified — `src/easy_a/refresh/coverage.py`):**
```python
# Source: src/easy_a/refresh/coverage.py:74-182 (read this session)
def refresh_targets(
    session: Session,
    *,
    term: str,
    config: CourseTargets,
    search: Callable[[ScheduleSearchQuery], str],
    catalog_fetch: Callable[[str], str] = fetch_catalog_html,
    refresh_catalog: bool = False,
    subject: str | None = None,
    course: str | None = None,
    crn: str | None = None,
    observed_at: datetime | None = None,
) -> list[TargetRefresh]:
    """One sequential pass. Caller owns transaction; failures must roll it back."""
```
The docstring's own words — *"Caller owns transaction; failures must roll it back"* — is the exact
mechanism behind the transaction-scope pitfall documented below: it is honest about what it does,
and at 1,402 targets in one call that honesty becomes a scaling risk the plan must manage at the
call-site (batch by subject), not by changing this function.

### Pattern 2: The suffix guard already works — reuse it, do not touch it

**What:** `_retain_exact_course_rows` decomposes any parsed HTML row whose `(subject, course_number)`
does not exactly match the target before the row ever reaches `ingest_schedule_html`.

**Verbatim source, read this session (`src/easy_a/refresh/coverage.py:185-214`):**
```python
def _retain_exact_course_rows(
    html: str,
    *,
    parsed_rows: list[ParsedScheduleRow],
    subject: str,
    course_number: str,
) -> str:
    """Remove source rows excluded by the exact-course pre-filter before ingestion."""
    soup = BeautifulSoup(html, "lxml")
    header = next(
        (
            row
            for row in soup.find_all("tr")
            if isinstance(row, Tag) and len(row.find_all("th", recursive=False)) == 24
        ),
        None,
    )
    if header is None:
        return html
    html_rows = [
        row
        for row in header.find_all_next("tr")
        if isinstance(row, Tag) and len(row.find_all("td", recursive=False)) == 24
    ]
    if len(html_rows) != len(parsed_rows):
        raise ValueError("Parsed schedule rows no longer match the schedule response.")
    for html_row, parsed_row in zip(html_rows, parsed_rows, strict=True):
        if (parsed_row.subject, parsed_row.course_number) != (subject, course_number):
            html_row.decompose()
    return str(soup)
```
And the existing test asserting this behavior for the exact CHM 2045 / 2045L case, read this
session (`tests/refresh/test_coverage_suffix_guard.py:15-38`):
```python
def test_suffix_variants_are_excluded_before_scope_validation(db_session: Session) -> None:
    config = _chm_config(db_session)

    try:
        rows = refresh_targets(
            db_session,
            term="202701",
            config=config,
            search=lambda query: _mixed_chm_response(query),
            observed_at=NOW,
        )
    except ValueError as exc:
        pytest.fail(f"suffix-only schedule rows must be excluded, not rejected: {exc}")

    assert rows[0].section_count == 5
```
**When to use:** For every one of the 33 base courses in `data/coverage-pilot-2026-09-20/suffix-query-risks.json`
(verified this session: exactly 33 entries, `[VERIFIED: data/coverage-pilot-2026-09-20/suffix-query-risks.json]`,
e.g. `{"subject": "CHM", "number": "2045", "suffix_courses": ["2045L"]}`). Both the base course
(`CHM 2045`) and its suffix variant (`CHM 2045L`) must appear as **separate** entries in the
generated target list so each is correctly ingested on its own exact-match pass — confirmed this
session that `courses.csv` already lists them as two separate rows
(`CHM,2045,General Chemistry I` and `CHM,2045L,General Chemistry I Lab`), so a straightforward
one-row-per-`courses.csv`-line target generator handles this automatically with no special-casing.

### Anti-Patterns to Avoid

- **Rewriting or "fixing" the suffix guard.** It is already correct and already tested for the
  documented failure case. The only remaining risk is whether it generalizes to schedule-table
  layouts USF might use for other subjects (e.g., a different column count, or a row without the
  expected 24 `<td>`s) — validate at scale, do not replace the mechanism.
- **Running all ~1,402 targets inside one `session.begin()` context**, as `target_cli.main`
  currently does when invoked once with a large target list. See Common Pitfalls.
- **Fetching a "bulk" catalog source that hasn't been confirmed to exist for USF's site.** The
  configured `cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}` endpoint is
  confirmed (this session) to return exactly one course. Do not assume a subject-level bulk catalog
  endpoint exists on that host without a probe fetch.
- **Weakening `same_campus`/the Tampa scope check to "make ingestion pass."** The check exists
  specifically because of the 47-row non-Tampa contamination incident (REQ-DATA-02, PR #18). Any
  course/subject that legitimately returns non-Tampa rows in an exact-match query must be handled
  by *excluding those rows* (same mechanism as the suffix fix), never by loosening the guard.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Course/section identity resolution | A new lookup or cache for course IDs | `resolve_course_id()` (`src/easy_a/common/lookups.py:33-49`, read this session) | Already handles subject/number normalization and the "not present" error path `ingest_schedule_html` depends on; duplicating it risks the two falling out of sync |
| Tampa-only scope enforcement | A new campus filter | `same_campus`/`describe_campus` (`src/easy_a/common/campus.py`, read this session) | Already the canonical Tampa-comparison logic used by the quality checker (`_check_section_campus`); **note** `coverage.py`'s own scope-guard at line 152 currently compares `r.campus.strip() != "Tampa"` directly rather than calling `same_campus` — flagged as a minor inconsistency worth fixing for consistency, not a functional bug at today's scale |
| Course-target list generation/validation | Ad hoc string parsing of `courses.csv` | `CourseTarget`/`CourseTargets` Pydantic models (`src/easy_a/refresh/targets.py`, read this session) | Already validates subject pattern `^[A-Z]{2,4}$` and number pattern `^[0-9]{4}[A-Z]?$` — confirmed this session that **every** row in the current `courses.csv` (1,402 rows) matches both patterns with zero exceptions, so no new validation logic is needed |
| Coverage/data-quality verification at scale | A new scale-specific quality script | `scripts/check_data_quality.py` + `run_quality_checks()` (`src/easy_a/quality/checks.py`, read this session) | Already includes `unsupported_campus_section` (the exact PR #18 guard), `no_historical_analytics`/`low_confidence_ranking` (the exact honest-fallback signals REQ-GRADES-01/D-20 require), and scales by iterating all sections for the term — no term-size assumption found in the code that would break at ~3,782 rows |

**Key insight:** Nearly everything this phase needs already exists and has already been proven at
small scale (10 courses, 132 sections) in `phase1_report.md`'s own pilot run against live Supabase.
The work is orchestration and scale-hardening (batching, resumability, validating the suffix fix
broadly), not new domain logic.

## Runtime State Inventory

This is not a rename/refactor/migration phase in the traditional sense, but it does expand stored
state broadly, so the same discipline applies to avoid silent gaps.

| Category | Items Found | Action Required |
|----------|-------------|-------------------|
| Stored data | Hosted Supabase currently holds 132 sections / 10 courses / 179 grade rows for term 202701 (verified in STATE.md, read this session). Expanding to ~1,402 courses / ~3,782 sections is additive (upsert-based), not destructive — `upsert_catalog_courses` and `_upsert_sections` both use `select ... scalar_one_or_none()` then insert-or-update, never delete. | Code edit: none required for the upsert path itself. Data migration: none — purely additive ingestion. Verify no existing 10-course/132-section rows are altered unexpectedly (`section_count` for existing courses might legitimately change if USF has updated schedule data since 2026-09-21, per the historical AMH 2020 17→19 precedent). |
| Live service config | `config/course_targets.toml` is the one piece of "live config not yet reconciled" this phase must resolve (5 configured vs 10 stored). It is version-controlled (not a UI/DB-only config), so this is a straightforward code-level reconciliation, not a hidden runtime-state gap. | Code edit: regenerate/replace this file (or its effective content via `--targets`) to cover the full course universe — see Open Questions for the commit-vs-generate-at-runtime fork. |
| OS-registered state | None found. No scheduled tasks, services, or process managers reference course counts or target lists. | None — verified by reading `scripts/`, `.gitignore`, and finding no cron/task-scheduler/pm2 references to course counts anywhere in the repo. |
| Secrets/env vars | None found related to this phase. `course_targets_path` is a `Settings` field (`src/easy_a/config.py:33`, confirmed present) pointing at the TOML file path, not a secret. | None. |
| Build artifacts | None found. No compiled/packaged artifact embeds course counts. | None — verified by the absence of any `egg-info`/build cache referencing course data in the repo tree. |

**Canonical question applied:** After all 1,402 courses are ingested, is there any runtime system
still holding the "5 courses" or "10 courses" figure? Only `config/course_targets.toml` (git-tracked
code, addressed above) and the prose in `STATE.md`/`PROJECT.md`/`ROADMAP.md`/`REQUIREMENTS.md`
(which the phase's completion summary must update, per this project's own documentation
convention — not a runtime concern, a documentation-hygiene one).

## Common Pitfalls

### Pitfall 1: One failure discards the whole batch

**What goes wrong:** `target_cli.main` (`src/easy_a/refresh/target_cli.py:25`, read this session)
opens exactly one `get_session_factory().begin()` context around the *entire* call to
`refresh_targets`, which internally loops over every target in `config.select(...)`. If invoked
with all ~1,402 targets in a single process run, and target #1,200 raises (network timeout, a
schedule-page layout `refresh_targets`/`_retain_exact_course_rows` doesn't expect, a transient USF
5xx), the whole transaction rolls back — all 1,199 prior successful upserts in that call are lost
and must be re-fetched from USF on retry.

**Why it happens:** `refresh_targets`'s own docstring says as much: *"One sequential pass. Caller
owns transaction; failures must roll it back."* This was a reasonable design for 5–10 configured
targets; it was never exercised past pilot scale (10 targets, per `phase1_report.md`).

**How to avoid:** Drive the existing CLI **once per subject** using its already-implemented
`--subject` filter (`target_cli.py:19,24`, confirmed present), rather than once for the whole
universe. Each subject invocation is its own process and its own transaction, bounding blast radius
to that subject's course count (1–33 per `courses.csv`, confirmed this session). This requires zero
new production code — only an orchestration script/runbook step that loops `--subject` values and
records which subjects have completed (idempotent re-run: upserts make re-running a completed
subject a no-op).

**Warning signs:** A full-run log that stops partway with no partial-completion record; re-running
from scratch after every transient failure; USF-side rate-limit or throttling responses appearing
partway through a very long single-process run.

### Pitfall 2: Catalog-before-schedule ordering is hard-enforced, not advisory

**What goes wrong:** `ingest_schedule_html` calls `resolve_course_id(session, row.subject, row.course_number)`
for *every parsed row* (`src/easy_a/schedule/ingest.py:68`, read this session) and raises
`CoreDataLookupError` → `ScheduleIngestError` if no matching `Course` row exists. If a batch
attempts to ingest schedule data for a course whose catalog page fetch failed or was skipped, the
entire schedule-ingest call for that pass fails.

**Why it happens:** This is intentional (REQ-COVERAGE-03's own scope note: "course rows must
pre-exist for `resolve_course_id`") — but `refresh_targets` already handles this correctly for the
single-target case (`if present is None: ... continue` before ever calling `search`,
`coverage.py:130-139`). The risk is only in a *hypothetical* new subject-level bulk-ingest path
(Alternatives Considered) where the schedule response could span multiple courses and only some of
that subject's catalog pages have been successfully fetched.

**How to avoid:** If the per-course `refresh_targets` loop (recommended path) is used, this is
already handled — no action needed. If a subject-level path is ever built, it must catalog-ingest
**every** course in that subject before issuing that subject's schedule search, and must not
partially apply a subject's schedule rows if any of its courses are missing a catalog row.

**Warning signs:** `ScheduleIngestError` referencing a course subject/number that should have been
catalog-ingested moments earlier in the same run.

### Pitfall 3: Stale documentation describing an already-fixed problem

**What goes wrong:** `STATE.md` and `ROADMAP.md` (both dated 2026-09-21/2026-09-20 "last updated")
still describe the suffix guard as unresolved blocking work. Planning against that prose without
reading the actual code risks re-implementing or "re-fixing" `_retain_exact_course_rows`
unnecessarily, or writing a redundant guard.

**Why it happens:** The fix (commit `8ea08db`, 2026-09-20T14:02) landed as part of Phase 03.5 (a
different, already-completed phase) *after* the pilot report that first surfaced the CHM 2045
failure (`phase1_report.md`, dated 2026-09-20T07:44) — and the project's own documents were not
re-verified against the code after that merge.

**How to avoid:** Trust the code and its test (`tests/refresh/test_coverage_suffix_guard.py`,
passing as written, confirmed by reading it this session) over the phase-level prose. The
remaining real work for item 3 is: (a) generalize/validate across all 33 affected base courses at
full-scale ingestion, not just CHM 2045; (b) reconcile `config/course_targets.toml`.

### Pitfall 4: No rate limiting or retry/backoff exists anywhere in the ingestion code today

**What goes wrong:** A grep of `src/easy_a` and `scripts/` for `sleep`/`backoff`/`retry`/`rate.limit`
returned zero matches (confirmed this session). The only pacing ever used against USF's live
endpoints was an ad hoc "two-second pause" in the *pilot enumeration process itself*
(`phase1_report.md`: "sequential subject searches with two-second pauses"), which is not part of
`src/easy_a` and would not be reused automatically by `refresh_course_coverage.py`. At ~1,402
catalog fetches plus up to ~1,402 schedule searches run back-to-back with no pacing, this risks
triggering USF-side throttling/blocking, and violates the spirit of D-08/D-09's "bounded, narrow"
posture even though each individual request is still a direct, non-crawling GET/POST.

**Why it happens:** The existing code was built and tested at 5–10 target scale, where pacing was
never a practical concern.

**How to avoid:** The plan should explicitly add a deliberate pacing/delay between sequential
requests during the full-scale run (matching the pilot's own precedent of ~2 seconds), and treat
this as an execution-time operational concern (a runbook step / script flag), not a change to the
production ingestion functions' signatures.

**Warning signs:** HTTP 429/503 responses from `cloud.usf.edu` or `usfweb.usf.edu` partway through
a run; unusually slow or failed responses clustering together.

## Code Examples

### Generating a full target list from the existing enumeration snapshot

`courses.csv` already exists in the working tree (git-ignored per `.gitignore:14`, confirmed this
session), with 1,402 data rows (1,403 lines including header, confirmed this session via `wc -l`),
each row already matching the `CourseTarget` validation patterns (confirmed this session — zero
non-matching subject or number values across all 1,402 rows). A minimal, dependency-free generator:

```python
# New script sketch — not yet written; illustrates the validated shape only.
# Source pattern for CourseTarget: src/easy_a/refresh/targets.py:12-15 (read this session)
import csv
from pathlib import Path

from easy_a.refresh.targets import CourseTarget

def load_generated_targets(csv_path: Path) -> tuple[CourseTarget, ...]:
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return tuple(
            CourseTarget(subject=row["subject"], number=row["number"])
            for row in reader
        )
```
This reuses the exact validated model the rest of the pipeline already trusts — no new validation
logic, and any row that somehow fails the pattern will raise a Pydantic `ValidationError` at
generation time, before any network request is made.

### Per-subject batched CLI invocation (recommended orchestration, zero new production code)

```sh
# Existing CLI, existing --subject flag (src/easy_a/refresh/target_cli.py:19,24, read this session)
for subject in $(cut -d, -f1 courses.csv | tail -n +2 | sort -u); do
  uv run python scripts/refresh_course_coverage.py \
    --term 202701 \
    --targets config/course_targets_full.toml \
    --subject "$subject"
  sleep 2   # pacing, per Pitfall 4 — matches the pilot's own precedent
done
```

## State of the Art

Not applicable in the usual "library version drift" sense — this phase reuses in-repo code
exclusively. The one relevant "current vs prior" fact: the suffix-guard fix itself *is* the state
of the art for this codebase as of 2026-09-21 (see Pitfall 3); do not plan against the pre-fix
description in ROADMAP.md/STATE.md.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | `catalog.usf.edu` (the CourseLeaf-hosted 2026-2027 undergraduate catalog) may expose subject-level pages with multiple `.courseblock` records, which could cut catalog-ingestion HTTP volume from ~1,402 to ~212 requests. | Alternatives Considered | Low — this is offered only as an optional future optimization, not the recommended path. If wrong, no plan built on it breaks, since the primary recommendation does not depend on it. |
| A2 | `courses.csv` (dated enumeration snapshot from 2026-09-20) still accurately reflects the Tampa Spring 2027 course/section universe at execution time. | Summary, Code Examples | Medium — USF schedule data can change between enumeration and execution (precedent: AMH 2020 went from 17 to 19 sections between two 2026-09 pilot runs). The plan should either re-verify freshness or explicitly treat the snapshot as dated evidence, consistent with this project's existing "measured and dated" convention (D-06/D-07). |
| A3 | A ~2-second pacing delay between sequential requests is sufficient to avoid USF-side throttling at ~1,402–2,800+ total requests. | Common Pitfalls (Pitfall 4), Code Examples | Low-medium — no rate-limit policy for USF's endpoints was found or tested this session; this figure is carried over from the pilot's own precedent, not independently verified against USF's actual limits. |

## Open Questions

1. **Should the full ~1,402-course target list be committed to `config/course_targets.toml`, or generated at execution time from a git-ignored snapshot and passed via `--targets`?**
   - What we know: `config/course_targets.toml` (5 entries) is git-tracked today; `courses.csv` (the enumeration source) and the `data/` directory are both explicitly git-ignored (`.gitignore:12,14`, confirmed this session) — an established project convention of keeping derived/raw data out of git.
   - What's unclear: Whether a ~1,402-entry *target list* (just subject+number pairs, no scraped content) should be treated like "config" (commit it, matching REQ-COVERAGE-01's original intent of configurable, version-controlled coverage) or like "derived data" (regenerate it at execution time, matching the `courses.csv`/`data/` precedent).
   - Recommendation: Surface this explicitly to the user before planning locks it in — it changes whether Phase 6's PR includes a large generated config file or a small generator script plus a runbook step.

2. **Does the suffix-row-exclusion mechanism (`_retain_exact_course_rows`) generalize correctly across all 33 affected base courses, or was it validated only against the one documented CHM 2045 case?**
   - What we know: The unit test (`tests/refresh/test_coverage_suffix_guard.py`) exercises a synthetic CHM 2045/2045L HTML fixture only. The mechanism's row-matching logic (24-`<th>`/24-`<td>` header/row detection, positional zip between parsed rows and HTML rows) is generic, not CHM-specific, so there is no code reason it would fail for the other 32 base courses — but this has not been exercised against live USF responses for those 32.
   - What's unclear: Whether any of the other 32 base courses' schedule tables have a different column layout, an unusual suffix pattern (e.g., two suffix variants of one base course), or another edge case not present in the CHM 2045 fixture.
   - Recommendation: Treat full-scale ingestion itself as the validation — the plan's success criteria (0 quality errors, 0 non-Tampa rows) will surface any generalization failure directly; no separate spike needed before starting.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|-----------|
| `cloud.usf.edu/academic-programs/details/...` (catalog detail pages) | Catalog ingestion | ✓ (confirmed reachable this session via live fetch of CHM 2045) | — | — |
| `usfweb.usf.edu/DSS/StaffScheduleSearch/StaffSearch/Results` (schedule search) | Schedule ingestion | ✓ (already used successfully by the 10-course pilot per STATE.md/phase1_report.md) | — | — |
| Hosted Supabase PostgreSQL | Persistence target | ✓ — STATE.md states it is "the only live DB now" and already holds 132 sections from the pilot | PostgreSQL 16 (per PROJECT.md D-01) | — |
| `courses.csv` enumeration snapshot | Target-list generation | ✓ — confirmed present on disk this session (1,402 data rows) | dated 2026-09-20 | Re-run the same enumeration methodology `phase1_report.md` documents if freshness is a concern (see Assumption A2) |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** `courses.csv` freshness (A2) — fallback is re-enumeration
using the already-documented, already-proven method in `phase1_report.md`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed via `pyproject.toml:39-40`, `testpaths = ["tests"]`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/refresh/ tests/catalog/ tests/schedule/ tests/quality/ -q` |
| Full suite command | `uv run pytest -q` (SQLite default; add `EASY_A_TEST_POSTGRES_URL` for the PostgreSQL-specific suite per `README.md`/STATE.md D-12) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|---------------|
| REQ-COVERAGE-03 | Suffix guard excludes CHM-2045L-style rows across a generalized target set (not just the one fixture course) | unit | `uv run pytest tests/refresh/test_coverage_suffix_guard.py -q` | ✅ exists (confirmed this session) |
| REQ-COVERAGE-03 | Generated target list validates against `CourseTarget`/`CourseTargets` for every row | unit | `uv run pytest tests/refresh/test_targets.py -q` (extend with a new test parametrized over `courses.csv`, or a dedicated `test_generate_targets.py`) | ❌ Wave 0 — no test currently loads the full `courses.csv`; the closest existing coverage (`test_config_parsing_and_filters`) only exercises the 5-entry default config |
| REQ-COVERAGE-03 | Full-scale ingestion: stored/API/coverage counts agree, 0 non-Tampa rows, quality 0 errors | integration/manual | `uv run python scripts/refresh_course_coverage.py --term 202701 ... ` per subject, then `uv run python scripts/check_data_quality.py --term 202701 --json` | ✅ scripts exist; this is inherently a live-data validation pass against hosted Supabase, matching the pilot's own verification method in `phase1_report.md` — not a unit test |
| REQ-COVERAGE-03 | Config vs stored-data reconciliation | manual/checkpoint | Compare `config/course_targets.toml` (or the effective generated list) against `SELECT DISTINCT subject, number FROM courses` | — no automated test; a `checkpoint:human-verify` step is appropriate given this closes a documented discrepancy (5 vs 10 vs ~1,402) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/refresh/ tests/catalog/ tests/schedule/ -q`
- **Per wave merge:** `uv run pytest -q` (full suite)
- **Phase gate:** Full suite green, plus a live `scripts/check_data_quality.py --term 202701 --json` run against hosted Supabase reporting 0 errors, before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] A test (new or extended `tests/refresh/test_targets.py`) that validates the *generated*
      target list (not just the 5-entry default) parses and validates cleanly — covers the "every
      `courses.csv` row matches the `CourseTarget` pattern" claim structurally, not just by this
      session's one-off `grep` check.
- [ ] No fixture currently exercises more than a handful of targets in one `refresh_targets` call;
      consider a test that exercises the per-subject-batch orchestration pattern (multiple targets,
      one transaction, one of them failing) to lock in the chosen resumability behavior.
- [ ] Framework install: none — pytest is already configured and used.

## Security Domain

`security_enforcement` is absent from `.planning/config.json` (confirmed this session — the file
contains only `workflow._auto_chain_active`), so it is treated as enabled per the protocol default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | No | This phase touches no auth surface — the application has no auth (confirmed D-06/out-of-scope in PROJECT.md: "Auth, accounts, or a user-profile product" is explicitly out of scope) |
| V3 Session Management | No | No session surface touched |
| V4 Access Control | No | No access-control surface touched; ingestion runs as a trusted operator script, not a user-facing endpoint |
| V5 Input Validation | Yes | Already handled by `CatalogCourse`/`CatalogParseError` and `ParsedScheduleRow` Pydantic validation on all fetched HTML, and by `CourseTarget`'s regex-constrained fields on the generated target list — no new validation surface is introduced, but scale increases the *volume* of untrusted HTML parsed, so parser exceptions (`CatalogParseError`) at scale should fail one course, not the whole batch (ties directly to Pitfall 1's batching recommendation) |
| V6 Cryptography | No | No new cryptographic operation introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Scope creep / data contamination from an over-broad upstream response (the exact failure mode that produced the 47 non-Tampa rows fixed by PR #18) | Tampering (of stored data integrity, not a malicious actor) | Already mitigated by the Tampa/CRN scope assertion in `refresh_targets` (`coverage.py:151-155`) and the independent `unsupported_campus_section` quality check (`quality/checks.py:191-211`) — both already read this session and confirmed present; this phase must not weaken either (see Anti-Patterns) |
| Untrusted HTML parsing (USF catalog/schedule pages are external, uncontrolled input) | Tampering / Denial of Service (malformed HTML causing parser exceptions or resource exhaustion) | Already mitigated by `BeautifulSoup`/`lxml` (a mature, non-`eval`-based parser) and by `CatalogParseError`/`ScheduleIngestError` raising cleanly rather than executing untrusted content; at scale, ensure one course's parse failure cannot abort the whole batch (Pitfall 1) |
| Unbounded/uncooperative scraping (explicitly prohibited by D-08/D-09) | — (policy/compliance, not a STRIDE category) | This phase's request volume (~1,402–2,800+ direct GETs/POSTs to known, deterministic URLs) is bounded and enumerable in advance — it is not crawling or discovery — but the *volume* is new territory for this codebase; pacing (Pitfall 4) keeps it within the spirit of "narrow, bounded" rather than a burst that could be mistaken for abusive traffic |

## Sources

### Primary (HIGH confidence — code/tests/in-repo docs read directly this session)

- `src/easy_a/refresh/coverage.py` — full file read; `refresh_targets`, `_retain_exact_course_rows`, `coverage_metadata`
- `src/easy_a/common/lookups.py` — full file read; `resolve_course_id`, `ensure_term`
- `src/easy_a/refresh/targets.py` — full file read; `CourseTarget`, `CourseTargets`, `load_targets`
- `config/course_targets.toml` — full file read (5 entries confirmed)
- `src/easy_a/catalog/client.py`, `src/easy_a/catalog/parser.py`, `src/easy_a/catalog/ingest.py` — full files read
- `src/easy_a/schedule/client.py`, `src/easy_a/schedule/ingest.py` — full files read
- `src/easy_a/quality/checks.py` — full file read
- `src/easy_a/common/campus.py` — full file read
- `src/easy_a/models/core.py`, `src/easy_a/models/sections.py` — `Course`, `Section`, `GradeDistribution` class definitions read
- `src/easy_a/rankings/cache.py` — `refresh_section_rankings` signature and whole-term support confirmed (lines 73-100 read)
- `src/easy_a/refresh/target_cli.py`, `src/easy_a/catalog/cli.py`, `src/easy_a/refresh/cli.py` (partial), `src/easy_a/refresh/service.py` (partial) — read
- `tests/refresh/test_coverage_suffix_guard.py` — full file read
- `tests/catalog/test_parser.py` (partial), `tests/refresh/test_targets.py` (partial) — read
- `phase1_report.md` (repo root) — full file read; the prior pilot's dated, measured results (1,402 courses / 3,782 sections enumerated; 10-course/132-section pilot ingest result; the documented CHM 2045 failure and its timing)
- `data/coverage-pilot-2026-09-20/suffix-query-risks.json` — read and counted (33 entries confirmed)
- `courses.csv` (repo root, git-ignored) — read and validated (1,402 data rows; zero pattern-validation failures against `CourseTarget`)
- `git log`/`git show` on `src/easy_a/refresh/coverage.py` and `tests/refresh/test_coverage_suffix_guard.py` — confirmed commit `8ea08db` (2026-09-20T14:02:26-04:00) introduced the suffix fix, after the pilot's documented failure (2026-09-20T07:44:55)
- `.gitignore` — confirmed `data/` and `/courses.csv` entries
- `pyproject.toml` — confirmed `requires-python = ">=3.12"`, pytest config path
- `.planning/config.json` — confirmed no `security_enforcement`/`nyquist_validation` overrides
- `.planning/STATE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` (Phase 6/7/8 sections), `.planning/WINDOWS.md` — read

### Secondary (MEDIUM confidence)

- Live `WebFetch` of `https://cloud.usf.edu/academic-programs/details/prefix/CHM/code/2045` this session — confirmed single-course-per-page structure `[CITED: live fetch this session]`
- Live `WebFetch` of `https://cloud.usf.edu/academic-programs/readdata/course/1/U/colgempty/deptempty` this session — confirmed this is a subject-prefix list, not a course listing `[CITED: live fetch this session]`

### Tertiary (LOW confidence)

- `WebSearch` confirming `catalog.usf.edu` hosts a CourseLeaf-based 2026-2027 undergraduate catalog — existence confirmed, but subject-level page structure and field coverage were **not** fetched/verified this session `[ASSUMED]` (see Assumption A1)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every mechanism confirmed present in code read this session
- Architecture: HIGH — the recommended path reuses code and a passing test already in the repo; the one new orchestration pattern (per-subject batching) reuses an existing, already-implemented CLI flag
- Pitfalls: HIGH — all four pitfalls are grounded in code actually read this session (transaction scope, catalog-ordering enforcement, the fix/test timing via `git log`, and a `grep` confirming zero rate-limiting code exists)

**Research date:** 2026-09-21
**Valid until:** Short-lived — this research is tightly coupled to the current code state and to
`courses.csv`'s 2026-09-20 enumeration snapshot. Re-verify `courses.csv` freshness before execution
if more than a few days elapse (Assumption A2), and re-confirm no further commits have touched
`coverage.py`'s guard logic since this session.
