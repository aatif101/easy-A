# Phase 1: Baseline, Scope and Contracts - Research

**Researched:** 2026-09-08
**Domain:** Repository baseline verification, launch-coverage inventory methodology, grade-method reproducibility, source data semantics (no new external stack)
**Confidence:** HIGH for everything directly executed or read in this session; MEDIUM/LOW flagged explicitly for anything that depends on data or access not available in this worktree

## Summary

Phase 1 is a documentation-and-decision phase, not a build phase. Its research need is not
"which library should we use" — no new framework, package, or external service is being adopted
here — it is "what does the existing repository actually do, and what is the cheapest reproducible
way to answer the three open coverage questions without violating the no-broad-crawl constraint."
This research executed the reproducible baseline checks directly in the worktree (Python and
frontend test suites), read the exact source files that decide method-v2 semantics and
suppression/blank-cell handling, and traced the schedule/syllabus client code to determine what an
inventory pass can and cannot do without new capability.

The headline finding: the PRD's baseline test count (166 Python / 19 frontend) is the accurate one,
not `.planning/codebase/TESTING.md`'s "~154 Python" figure — this was re-measured directly in this
worktree, not inferred. The second headline finding: the schedule and syllabus clients are both
deliberately narrow-only — neither supports a "give me everything for this term/campus" query, and
there is no existing subject-code enumeration anywhere in the repository. A campus-wide inventory
of any kind (instructor coverage, syllabus availability, subject/section reconciliation) requires a
net-new, but still narrow and bounded, enumeration step before any per-subject or per-course query
can run. The third finding: the RULE-60C confidence-label thresholds already numerically operate on
the A-F outcome count today, but only as an accident of `RecencyConfig(enabled=False)` being the
locked default — this needs to be a documented equivalence, not a coincidence the next contributor
discovers by reading two files.

**Primary recommendation:** Treat Phase 1's coverage questions as an *inventory-methodology*
deliverable (a documented, narrow, resumable acquisition plan with explicit complete/partial/failed/
unqueried states), not an inventory *result* — the actual campus-wide numbers cannot be produced in
this research session because they require the same net-new enumeration capability the planner must
scope as work, and running an unbounded live inventory now would violate the "no broad crawls"
constraint this task was given.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Launch coverage manifest (written contract) | Backend / Domain docs | — | Not a running system; a versioned artifact consumed by later ingest and by the metadata API's `/api/v1/metadata` responses |
| Subject/section enumeration for inventory | Ingest (Backend) | External source (USF Staff Schedule, unauthenticated HTTP) | `StaffScheduleClient` already lives in `src/easy_a/schedule/client.py`; enumeration is a net-new caller of the same client, not a new tier |
| Named-instructor coverage inventory | Ingest (Backend) | Persistence (`SectionInstructor` / schedule rows) | Reuses `ingest_schedule_html` write path; read-side aggregation is a new query, not a new client |
| Current-term syllabus availability inventory | External source (Simple Syllabus public library, browser-only) | Ingest (Backend, `SimpleSyllabusClient`) | The public library's course-search UI has no client wrapper in this repo — only single-document fetch by ID/URL exists (`src/easy_a/syllabi/client.py:28-32`); enumeration must happen outside the ingest tier today |
| Method v2 (grade-only ease, thresholds) | Backend / Domain (`src/easy_a/analytics/`) | API (`src/easy_a/rankings/service.py`) | Pure computation over ORM-loaded aggregates; no browser or CDN involvement |
| Source suppression / blank-cell semantics | Ingest (Backend, `src/easy_a/grades/parser.py`) | — | Decided entirely at parse time, before any row reaches the database |
| UI/API state contract (Phase 1 deliverable) | API (schema) + Browser (render contract) | — | `01-UI-SPEC.md` already defines this; Phase 1's job is to make it traceable to concrete payload fields, not to build either tier |

## Confirmed Baseline (reproduced this session, not carried over from prior documents)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-LAUNCH-01 | Launch coverage manifest defining declared scope (all USF Tampa, Spring 2027 only) before implementation | Coverage Inventory Methodology section below: what can be enumerated now, what needs a net-new bounded utility, and the exact query constraints of the existing schedule/syllabus clients |
| REQ-EVID-01 (state definitions) | Visible evidence scope, sample size, named semesters, professor-course vs. course-only | Method v2 Reproducibility Contract section: exact formula, cohort chain, and the independent nullable-state model already implied by `EMPTY_AGGREGATE` / `HistoricalGradeAggregate` in `src/easy_a/analytics/grades.py` |
| REQ-EVID-02 (state definitions) | No plausible default score from absent/insufficient/suppressed/invalid evidence | Source Suppression & Blank-Cell Semantics section: current `_cell_to_int`/`_is_empty_cell` behavior in `src/easy_a/grades/parser.py:250-262` silently converts blank cells to 0 with no suppression marker path — a direct conflict with REQ-DATA-01 that Phase 2 must resolve, that Phase 1 must document as a confirmed gap |
| REQ-UI-01 (component/state contract) | Search, details, methodology, alert flows across all failure/missing-data states | `01-UI-SPEC.md` is already the adapted contract; this research adds no new UI research, per that document's own Source Traceability table |
| REQ-OPS-01 (source and provisioning planning) | External dependencies identified with owner and blocked phase | Environment Availability section: Docker/PostgreSQL, Node, and USF/Simple Syllabus source reachability all checked directly in this worktree |

</phase_requirements>

### Git and commit baseline

`origin/main` was re-fetched this session and is still exactly
`06634490de5c765bdc7b55e4f439476b0e4fa0f7` — no newer commits exist upstream since the PRD's audit
[VERIFIED: `git fetch origin main` + `git log origin/main -1`, executed this session]. The current
worktree HEAD, `43f5b4d4fa89ecd3c8459f1be33a0f1ca888082a`, is a confirmed descendant of that commit
[VERIFIED: `git merge-base --is-ancestor 06634490de5c765bdc7b55e4f439476b0e4fa0f7 HEAD` returned
true, executed this session]. Local `main` (in the separate primary checkout at
`C:/Users/smati/VS Code Projects/easy-A`, outside this worktree) remains untouched at `d880d3c` —
this research did not read or write there, consistent with the working-root restriction given for
this task. ADR-13's "reconcile newer changes" requirement is trivially satisfied: there is nothing
newer to reconcile.

### Baseline test counts (OQ-04) — resolved by direct execution, not by picking a source

Both existing figures were quoted from documents written at different revisions. This session ran
the actual suites in the current worktree instead of trusting either document:

```text
$ uv run pytest --collect-only -q
...
166 tests collected in 15.68s

$ uv run pytest -q
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
166 passed, 1 warning in 4.75s
```
[VERIFIED: command executed this session in the worktree at HEAD `43f5b4d`]

```text
$ npm install   (web/, first run — no committed node_modules)
added 329 packages, and audited 330 packages in 12s

$ npm test
 Test Files  2 passed (2)
      Tests  19 passed (19)
```
[VERIFIED: command executed this session in `web/` at HEAD `43f5b4d`]

**Resolution of OQ-04:** the true baseline is **166 Python tests, all passing, plus 19 frontend
tests, all passing** — matching `docs/final-mvp-plan.md`'s figure exactly, not
`.planning/codebase/TESTING.md`'s "~154 Python" figure. The discrepancy is not explained by commit
drift (both worktrees are on the same commit lineage); the most likely explanation is that the
codebase-map pass undercounted or used a narrower collection filter, but the planner does not need
to resolve *why* the old figure was wrong — only that **166 / 19** is the confirmed, reproducible
regression baseline for ADR-16 going forward. Record this number in whatever document becomes the
launch coverage manifest, and re-run these two exact commands as the Phase 1 (and later, CI)
regression gate rather than re-trusting a written figure.

**One caveat carried forward, not resolved here:** all 166 Python tests run against
`sqlite+pysqlite:///:memory:` (`tests/conftest.py:12`) [VERIFIED: `tests/conftest.py`, read this
session] — none run against PostgreSQL. This worktree's Docker daemon is not reachable (`docker
info` returns `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`)
[VERIFIED: command executed this session], so a PostgreSQL-backed re-run of the same 166 tests is
not possible in this environment right now. This is explicitly **not** Phase 1 scope (ADR-16/
REQ-OPS-01 assign net-new PostgreSQL integration tests to Phase 7) — but Phase 1 should record that
the 166/19 baseline is a SQLite-only baseline, so nobody later treats a PostgreSQL regression as a
violation of "preserve the passing baseline."

## Method v2 Reproducibility Contract

Every piece below is independently stated, as the roadmap's Phase 1 success criterion #3 requires.
Each rule is cross-referenced to (a) its normative statement in `.planning/REQUIREMENTS.md` — a
project-planning document already synthesized and locked in this ingest, not primary source code —
and (b) the *current* code that either implements it, partially implements it, or does not
implement it at all. Phase 2 is where these get built or fixed; Phase 1's job is only to make the
target state reproducible from text.

### The formula

```text
g = (4*A + 3*B + 2*C + D) / (4*N)                    where N = A+B+C+D+F
adjusted_g = (N*g + k*mu) / (N+k)
historical_grade_ease = 10 * adjusted_g
```
[CITED: `.planning/REQUIREMENTS.md:26-27`, itself sourced from `docs/final-mvp-plan.md` section 3 —
both read this session]

- **`k` (RULE-K60):** shrinkage prior strength, locked default `60`. This is a formula coefficient,
  not a count threshold, and is unrelated to RULE-60A/B/C
  [CITED: `.planning/REQUIREMENTS.md:248`]. The *existing* code already uses `k=60` for the
  (currently 80/20 composite) grade-favorability smoothing:
  `DEFAULT_GRADE_PRIOR_STRENGTH = 60.0` [VERIFIED: `src/easy_a/analytics/scoring.py:19`, read this
  session]. Phase 2 reuses this constant for the new grade-only formula; the numeric value carries
  over even though the composite formula it currently feeds does not.
- **`mu`:** a *measured* reference grade-favorability mean from eligible imported history — never a
  hard-coded constant. Today's code does the opposite: `DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR =
  0.75` [VERIFIED: `src/easy_a/analytics/scoring.py:24`, read this session] is a hard-coded global
  prior, used unconditionally as `mu` whenever no more specific prior is available
  (`src/easy_a/analytics/queries.py:207` references this constant as the fallback — confirmed
  present via `grep` in this session, not independently re-read line-by-line; treat the *existence*
  of the fallback as `[VERIFIED: src/easy_a/analytics/scoring.py:24]` and its call site as
  `[CITED: .planning/codebase/CONCERNS.md, INFO 4 in .planning/INGEST-CONFLICTS.md]`). Replacing
  this with a measured `mu`, computed from the reference-cohort chain, is Phase 2's core work —
  Phase 1 only needs to confirm the target state, which it does here.

### RULE-20 — display-score floor (gating: score eligibility)

Require at least 20 A-F outcomes (`N`) in the selected cohort before showing an adjusted score;
smaller samples may show source-permitted observed counts/rates with a "Small sample" label while
the score reads "Insufficient data." Source suppression rules take precedence over this threshold.
[CITED: `.planning/REQUIREMENTS.md:244`] **Current code status: does not exist anywhere.** A
targeted search for any `20`-outcome gate in `src/easy_a/analytics/` and
`src/easy_a/rankings/service.py` found none [VERIFIED: `grep -rn "20\b" src/easy_a/analytics/*.py
src/easy_a/rankings/service.py` returned zero matches, executed this session]. This is fully
net-new Phase 2 work, not a modification.

### RULE-60A — professor-course preference threshold (gating: cohort selection)

Prefer same-professor/same-course evidence over course-only evidence only after conservative
identity resolution **and** at least 60 A-F outcomes in that professor-course cohort.
[CITED: `.planning/REQUIREMENTS.md:245`] **Current code status: a similarly-shaped gate already
exists, but on `effective_n`, not on an explicitly-named "A-F outcome count" concept:**

```python
def has_sufficient_instructor_course_evidence(
    stats: HistoricalOutcomeStats, config: ScoreConfig | None = None,
) -> bool:
    score_config = config or ScoreConfig()
    return (
        stats.score_source is ScoreSource.instructor_course
        and stats.effective_n >= score_config.instructor_course_min_effective_n
        and stats.mapped_instructor_section_count > 0
    )
```
[VERIFIED: `src/easy_a/analytics/scoring.py:151-160`, read this session] with
`DEFAULT_INSTRUCTOR_COURSE_MIN_EFFECTIVE_N = 60.0` [VERIFIED: `src/easy_a/analytics/scoring.py:23`].
This is evidence the "60-outcome professor-history threshold" concept is not new to the codebase —
it predates this milestone — but it does not yet include the "conservative identity resolution"
precondition as a separate, testable gate (identity resolution lives in
`src/easy_a/signals/resolver.py` for policy chips, and a parallel/shared mechanism for grade
attribution is Phase 2 scope per REQ-DATA-01).

### RULE-60B — reference-mean eligibility (gating: reference eligibility)

Require at least 60 eligible A-F reference outcomes before a reference mean `mu` may be computed.
If no measured reference qualifies, the adjusted score is unavailable with reason "Reference data
unavailable"; valid observed grade facts remain visible. Zero-valued reference means stay valid;
never fall back to 0.75 or any hard-coded mean. [CITED: `.planning/REQUIREMENTS.md:246`] **Current
code status: does not exist.** There is no "reference eligibility" check anywhere in
`src/easy_a/analytics/` today — the current code has no concept of a reference cohort at all; it
always uses the single hard-coded `DEFAULT_GLOBAL_GRADE_FAVORABILITY_PRIOR` regardless of sample
size [VERIFIED: `src/easy_a/analytics/scoring.py:24`, confirmed no conditional guard around its use
via the same targeted search above]. Fully net-new Phase 2 work.

### RULE-60C — evidence-strength display labels (display-only, descriptive)

"Limited" under 60 A-F outcomes, "Moderate" 60-179, "Strong" 180 or more; downgrade one level if
only one term is covered. Not probabilities; no effect on score eligibility or cohort selection.
[CITED: `.planning/REQUIREMENTS.md:247`] **Current code status: the boundary logic already exists,
almost verbatim, but is measured against `effective_n`, not a named A-F outcome count:**

```python
LOW_CONFIDENCE_MAX_EFFECTIVE_N = 60.0
HIGH_CONFIDENCE_MIN_EFFECTIVE_N = 180.0

def confidence_label_for(effective_n: float, term_count: int) -> ConfidenceLabel:
    if effective_n < LOW_CONFIDENCE_MAX_EFFECTIVE_N:
        label = ConfidenceLabel.low
    elif effective_n < HIGH_CONFIDENCE_MIN_EFFECTIVE_N:
        label = ConfidenceLabel.medium
    else:
        label = ConfidenceLabel.high
    if term_count <= 1:
        return _downgrade_one_level(label)
    return label
```
[VERIFIED: `src/easy_a/analytics/confidence.py:6-49`, read this session, quoted verbatim]

**A load-bearing finding for Phase 2 planning, derived by reading the two files together:**
`effective_n` is computed as `min(effective_grade_n, effective_withdrawal_n)` where
`effective_grade_n = completed_grade_count(weighted_counts)` (i.e., the weighted `A+B+C+D+F` sum,
which *is* `N`) and `effective_withdrawal_n = weighted_counts.total_grades` (i.e., `T`)
[VERIFIED: `src/easy_a/analytics/grades.py:127-129`, read this session — exact lines:
`effective_grade_n = completed_grade_count(weighted_counts)`, `effective_withdrawal_n =
weighted_counts.total_grades`, `effective_n = min(effective_grade_n, effective_withdrawal_n)`].
Because the grade parser enforces `count_sum == total_grades` at import time (every one of the ten
buckets summed must equal the source's own Total Grades field, or the row is rejected)
[VERIFIED: `src/easy_a/grades/parser.py:168-176`, read this session — the `count_sum != total_grades`
check raising `GradeRowValidationError`], `T` (=`total_grades`) always equals `N` plus the
non-A-F buckets (`I+S+U+W+O`), so `T >= N` always holds. Therefore, **whenever term-level recency
weighting is disabled** (`RecencyConfig(enabled=False)`, the current and ADR-12/CON-CALC-01-locked
default — weights are uniformly `1.0` [VERIFIED: `src/easy_a/analytics/grades.py:141-148`, the
`_term_weights` function's `if not recency.enabled: return {... : 1.0 ...}` branch]), `effective_n`
reduces exactly to `N`, the A-F outcome count. **This means RULE-60C's boundary values (60/180) are
already numerically correct against the A-F outcome count today — but only as a byproduct of
recency staying disabled, and nothing in the code documents or tests this equivalence.** If recency
weighting is ever enabled (a locked-off default, not a removed capability — `RecencyConfig` still
has an `enabled` flag), this equivalence silently breaks and `effective_n` would diverge from raw
`N`. Phase 2 should either (a) rename/re-derive `effective_n` explicitly as the A-F count with a
regression test proving the recency-disabled equivalence, or (b) keep the current variable but add
an explicit test locking `effective_n == N` under the default config, so a future recency-toggle
change cannot silently reclassify every confidence label. Either way, this is a **documentation and
test-coverage gap Phase 1 must record, not a code change Phase 1 should make.**

### Reference cohort chain (supplies `mu` only)

For professor-course history: other sections of the same course first, then other courses in the
subject, then the eligible institutional reference corpus. For course-only cohorts: start with
other courses in the subject. Exclude the displayed cohort from the reference at every level. This
chain supplies `mu` only — ADR-02/ADR-03 forbid any subject- or corpus-level value from becoming a
*displayed* score. [CITED: `.planning/REQUIREMENTS.md:257-264`, resolving the ADR-vs-PRD tension
already recorded as INFO in `.planning/INGEST-CONFLICTS.md`] **Current code status:** no reference
chain exists; the single global constant serves every case today, so there is nothing in the
current code to reconcile with this contract — it is new work, cleanly scoped.

## Source Suppression and Blank-Cell Semantics (USF InfoCenter grade exports)

No public documentation of the USF InfoCenter grade-export format's suppression conventions was
found or is claimed here — **this section states what the current parser code does, and what
remains unconfirmed against real files.** [ASSUMED: no InfoCenter-specific suppression-marker
documentation was located; treat any statement below about the *source's own* semantics as
unconfirmed until real exported files are inspected]

What the parser code actually does today, read directly:

```python
def _cell_to_int(value: Any, row_number: int, column_name: str) -> int:
    if _is_empty_cell(value):
        return 0
    if isinstance(value, bool):
        raise ValueError(f"{column_name} contains a boolean at row {row_number}")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        float_value = float(value)
        if float_value.is_integer():
            return int(float_value)
        raise ValueError(f"{column_name} contains non-integer value {value!r} at row {row_number}")
    ...
```
[VERIFIED: `src/easy_a/grades/parser.py:250-262`, read this session, quoted verbatim] — and
`_is_empty_cell` treats `None` and anything `pd.isna(...)` accepts as empty
[VERIFIED: `src/easy_a/grades/parser.py:264-269`, read via the same session's earlier `cat`, content
matches the function signature `_is_empty_cell(value)` referenced above; re-confirmed present at
this path and behavior by direct call-site reading].

**The gap:** REQ-DATA-01 requires "a blank source cell must not silently become zero unless
documented export semantics permit it" [CITED: `.planning/REQUIREMENTS.md:79-80`]. The current
code does the opposite unconditionally — every blank/`NaN` cell becomes `0` with no distinction
between "this bucket had zero students" and "this cell was blank because the source suppressed a
small count" (a common practice in FERPA-constrained grade-distribution exports, though this
specific InfoCenter export's convention is not confirmed here). There is also **no suppression
marker path at all** in the parser — no handling for a literal string like `"<10"`, `"*"`, `"N/A"`,
or similar common small-cell-suppression notations; any such value would currently either be
coerced by `_cell_to_int`'s numeric-text branch (raising `ValueError` → the whole row is rejected
via `GradeWorkbookValidationError`) or, if truly blank, silently become `0`
[VERIFIED: `src/easy_a/grades/parser.py:250-277`, read this session — the final `_cell_to_int`
branch attempts `float(text)` on any non-empty non-numeric string and raises `ValueError` if that
fails, which propagates as a row-level validation error, not a suppression state].

**What Phase 1 can confirm without possessing real export files:** the exact current behavior
(blank → 0, unparseable non-blank text → whole-row rejection) is fully verified above. **What Phase
1 cannot confirm:** whether real USF InfoCenter grade-distribution XLSX exports actually contain
blank cells for FERPA-style small-cell suppression, or whether blank simply means "zero students in
this bucket" as a matter of the export's own convention. This is a genuine external-data dependency,
not a code question — **the input needed is a real (or at minimum, a small representative sample)
InfoCenter export file, owned by whoever has ODS/registrar access to download it** (the README
records ODS approval for aggregate data per `01-CONTEXT.md`, but no file has been supplied to this
planning session). Recommend the planner add a task in Phase 1 or early Phase 2 that: (a) requests
one real (or one anonymized/sample) InfoCenter XLSX export, (b) inspects it for any non-numeric or
blank cells before writing the suppression-state logic REQ-DATA-01 requires, and (c) only then
decides whether blank-as-zero is safe to keep, or must become an explicit `suppressed` metric state.

## Coverage Inventory Methodology (OQ-02, OQ-03) — approach, not results

Per this task's explicit constraint, **no broad live crawl was run**. What follows is the bounded
approach the existing clients support, and the exact reason a full campus-wide count cannot be
produced without new (but still narrow) capability.

### What the schedule client can and cannot do

```python
@dataclass(frozen=True)
class ScheduleSearchQuery:
    term: str
    campus: str | None = None
    subject: str | None = None
    course: str | None = None
    crn: str | None = None

    def __post_init__(self) -> None:
        normalize_banner_term_code(self.term)
        has_crn = self.crn is not None and bool(self.crn.strip())
        has_subject = self.subject is not None and bool(self.subject.strip())
        ...
        if not has_crn and not has_subject:
            raise ValueError("A narrow schedule search requires --crn or --subject.")
```
[VERIFIED: `src/easy_a/schedule/client.py:14-31`, read this session, quoted verbatim] — the CLI
wrapper independently enforces `--subject` as `required=True`
[VERIFIED: `src/easy_a/schedule/cli.py`, `parser.add_argument("--subject", required=True, ...)`,
read this session]. **There is no "all subjects" or "all sections" query supported by this client
or its CLI.** Every schedule query must name a subject (or a CRN). Campus is filterable via
`P_CAMPUS` and the codebase already documents `T` as the Tampa Banner campus code
[VERIFIED: `src/easy_a/schedule/cli.py`, `parser.add_argument("--campus", help="Banner campus code,
e.g. T for Tampa.")`, read this session].

**Consequence:** to inventory named-instructor coverage across "all offered USF Tampa sections,
Spring 2027," the acquisition step must first know the list of subjects offered at Tampa for
`202701`. **No such list exists anywhere in this repository today** — a targeted search for a
static subject-code list, an "ALL"-subject sentinel, or any subject enumeration helper found
nothing [VERIFIED: `grep -rn "P_SUBJ=ALL\|subject.*ALL\|ALL SUBJECTS\|subject_codes\|SUBJECT_CODES"
src/ docs/ .planning/` returned zero matches, executed this session]. The existing
`/api/v1/metadata/subjects` endpoint derives its list from the `Course` table
[VERIFIED: `src/easy_a/api/routes/metadata.py:33-37`, read this session — `select(Course.subject)
.distinct()`], which is itself populated by catalog ingest, not by any independent USF subject
directory — so this endpoint only reflects subjects *already imported*, and is circular for the
purpose of first discovering what to import.

**The bounded path that does not require a broad crawl:** the USF public Staff Schedule Search form
itself (`https://usfweb.usf.edu/DSS/StaffScheduleSearch/`) is the acquisition starting point named
in the PRD [CITED: `docs/final-mvp-plan.md` section 5, "the existing USF public schedule form...is
an acquisition starting point"]. That form's own subject dropdown is a single bounded HTML page —
fetching it once is one request, not a crawl, and yields the authoritative current-term Tampa
subject list without guessing at a static code list that could be stale. This is a **net-new, but
narrow, one-request enumeration step** that does not exist in the codebase yet; it is the natural
first stage of the "campus-wide acquisition/inventory utility" `01-CONTEXT.md` says is in scope
where needed. Once the subject list is known, a per-subject schedule search (one bounded POST per
subject, term=`202701`, campus=`T`) using the *existing* `StaffScheduleClient` produces the full
section/instructor inventory — this is the "subject/section reconciliation" the roadmap's D-03 and
Phase 1 success criteria call for. The number of Tampa subjects is bounded (tens, not thousands) —
this is well within "narrow, bounded checks," not a broad crawl, provided it runs once as a
deliberate inventory pass with recorded observation timestamps, not as an ad hoc or repeated
scrape.

**What this research does NOT do:** fetch that subject-dropdown page, enumerate subjects, or run
any per-subject schedule search. That is the inventory *work* the plan must schedule (likely as a
small new CLI/script reusing `StaffScheduleClient`, `ingest_schedule_html`, and a new subject-
discovery function) — not something to execute inside a research pass. Executing it here would
itself be exactly the "broad crawl" this task was told to avoid, and its results would not be
reproducible/auditable the way a planned, timestamped inventory task's would be.

### What the syllabus client can and cannot do

```python
def fetch_document_html(self, document_id_or_url: str) -> tuple[str, str]:
    document_id = extract_document_id(document_id_or_url)
    response = self._client.get(f"/api2/doc-html/{document_id}")
    response.raise_for_status()
    return document_id, response.text
```
[VERIFIED: `src/easy_a/syllabi/client.py:28-32`, read this session, quoted verbatim] — this client
fetches exactly one document, given an already-known document ID or public URL
(`^[A-Za-z0-9_-]+$`-validated, host-pinned to `usf.simplesyllabus.com`)
[VERIFIED: `src/easy_a/syllabi/client.py:10, 45-56`]. **There is no search/enumeration method on
this client at all** — no "find the syllabus for course X in term Y" call exists in the codebase.
The prior narrow-check evidence in `docs/live-source-drift-2026-09-01.md` confirms this
operationally: it describes "two course searches in the public Simple Syllabus library"
[CITED: `docs/live-source-drift-2026-09-01.md`, "Scope" section, read this session] — i.e., a
human/browser search against the public library's own search UI, not a scripted API call, because
no such API call exists in this codebase or (as far as this research found) is exposed by Simple
Syllabus for unauthenticated bulk enumeration.

**Consequence for OQ-03 inventory:** a campus-wide current-term syllabus availability inventory
requires either (a) one manual/browser-driven library search per course (does not scale to "all
offered USF Tampa sections" without becoming exactly the kind of broad, repeated, unbounded access
this task says to avoid), or (b) discovering and validating an actual Simple Syllabus search/listing
endpoint that returns multiple results per query (unconfirmed to exist; would need to be
independently verified against the tenant's actual API surface before being relied on — this
research did not attempt that discovery, as it would itself risk becoming exactly the broad probing
this task excludes). **Recommendation for the planner:** treat full campus-wide syllabus-availability
inventory as **out of reach for a single Phase 1 research/planning pass** and scope it instead as a
*sampled* inventory — e.g., one search per subject (not per course-and-section) across the Tampa
subject list discovered above, which is bounded to "tens of subjects," recorded with timestamps, and
explicitly labeled as a subject-level sample rather than a section-level census. This directly
matches the roadmap's own framing: "the two-course September 1 observation is not a coverage
denominator" [CITED: `.planning/phases/01-baseline-scope-and-contracts/01-UI-SPEC.md`, Surface and
Payload Contract section] — a subject-level sampled inventory is a larger, but still honest and
bounded, sample; it should be reported with the same complete/partial/failed/unqueried state
vocabulary the roadmap already specifies for schedule reconciliation, not presented as a full census
either.

### What the two-course sample actually says today, and its evidentiary weight

Restated precisely from the source document, since the planner needs the exact numbers, not a
paraphrase: `MAC 1105` — 5 Tampa sections, all instructor `Staff`; `ENC 1101` — 41 Tampa sections,
all instructor `Staff`; no Spring 2027 syllabus found in the public library for either course,
matching results were Fall 2026 only [CITED: `docs/live-source-drift-2026-09-01.md`, read in full
this session]. This is a **2-course, 46-section sample out of an unknown-but-larger full Tampa
Spring 2027 catalog** — it establishes that near-zero named-instructor coverage and thin current-
syllabus availability are *plausible* outcomes for the full scope, not that they are *confirmed*
campus-wide facts. `01-CONTEXT.md` and `01-UI-SPEC.md` already correctly treat this as a risk
signal, not a denominator — this research found no reason to revise that framing, and found no
additional live evidence (by design — no further live crawling was performed).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bounded USF schedule queries | A new HTTP client for schedule search | `src/easy_a/schedule/client.py` `StaffScheduleClient` / `ScheduleSearchQuery` | Already validates required narrow-query shape, normalizes term codes, and is fully tested (`tests/schedule/`) |
| Single-document syllabus fetch | A new Simple Syllabus HTTP client | `src/easy_a/syllabi/client.py` `SimpleSyllabusClient` | Already host-pins and validates document IDs; reuse it for the fetch half of any inventory pass |
| Grade-only ease computation | A from-scratch formula module | Extend `src/easy_a/analytics/grades.py` and `scoring.py` | `HistoricalGradeAggregate`, `GradeCounts`, and the shrinkage math (`bayesian_smooth`) already exist and are unit-tested; Phase 2 adapts them, it does not replace them |
| Confidence-label boundary math | A new label function | `confidence_label_for` in `src/easy_a/analytics/confidence.py` | The 60/180 boundary logic and one-term downgrade rule are already correct in shape; only the input semantics need documenting/pinning per the RULE-60C finding above |
| Term-code validation | Ad hoc regex on Banner codes | `normalize_banner_term_code` / `parse_banner_term` in `src/easy_a/common/terms.py` | Already the single validated path (`{4-digit year}{01|05|08}`), used by both the API dependency layer and the ingest CLIs — REQ-LAUNCH-01's "historical-only terms are not selectable registration targets" contract should extend this module, not duplicate it |

**Key insight:** almost every piece of machinery Phase 1's inventory work and Phase 2's method work
needs already exists in some partial form. The risk in this codebase is not "we lack a client" — it
is "the existing client's narrow-by-design shape (subject-or-CRN only, single-document-only) means
campus-wide anything requires a net-new *enumeration* layer above the existing fetch layer," which
is exactly the gap the Coverage Inventory Methodology section above documents.

## Common Pitfalls

### Pitfall 1: Treating the two-course sample as a coverage denominator
**What goes wrong:** A later phase computes "X% named-instructor coverage" using the 5+41=46
sampled sections as the denominator instead of the actual full Tampa Spring 2027 section count.
**Why it happens:** it is the only number currently in hand, and it is tempting to report it as if
it were representative.
**How to avoid:** the launch coverage manifest (REQ-LAUNCH-01) must state the actual full-scope
section count once the subject enumeration described above runs, and must label any partial/sample
figure explicitly as a sample, per D-03 ("Samples are a testing strategy, never evidence of
campus-wide completeness").
**Warning signs:** any percentage or coverage claim in a document that does not cite an inventory
run's timestamp and section-count denominator.

### Pitfall 2: Assuming `effective_n` already means "A-F outcome count" everywhere
**What goes wrong:** Phase 2 reuses `effective_n` for RULE-20 or RULE-60B gating without confirming
recency stays disabled, silently reintroducing a dependency on an assumption that is currently true
by coincidence, not by contract.
**Why it happens:** the numeric equivalence (`effective_n == N` when recency is disabled) is real
today, so naive reuse "just works" until someone flips `RecencyConfig(enabled=True)`.
**How to avoid:** add an explicit unit test in Phase 2 asserting `effective_n == N` under the
default (recency-disabled) config, and/or introduce a distinctly-named `af_outcome_count` field so
the three RULE-60 variants and RULE-20 read from an unambiguous source rather than an
incidentally-correct one.
**Warning signs:** any new gating logic added to `confidence.py` or `scoring.py` that reads
`effective_n` without a comment or test tying it to the A-F outcome definition.

### Pitfall 3: Treating "blank cell" and "zero" as interchangeable in the grade parser
**What goes wrong:** a genuinely suppressed small-cell value (if the real InfoCenter export uses
blank-for-suppression, which is unconfirmed but common in FERPA-constrained aggregate exports)
silently becomes a real `0` in `N`/`T`, understating a course's actual grade distribution without
any visible flag.
**Why it happens:** `_cell_to_int`'s `_is_empty_cell` branch returns `0` unconditionally
[VERIFIED: `src/easy_a/grades/parser.py:250-262`], and nothing downstream distinguishes "true zero"
from "blank."
**How to avoid:** obtain a real (or representative sample) InfoCenter export before finalizing
Phase 2's parser changes, and add a `suppressed` metric state (already required by REQ-EVID-02's
independent nullable-state model) if blank cells turn out to represent suppression rather than true
zero.
**Warning signs:** any row where one grade bucket is blank while adjacent buckets in the same row
have populated small values — a pattern consistent with cell-level suppression rather than a
genuinely empty bucket.

### Pitfall 4: Building a bulk RMP or Simple Syllabus crawler to "solve" OQ-02/OQ-03 quickly
**What goes wrong:** violates ADR-10 (no bulk RMP crawler) and the constraint this task itself was
given ("do not perform broad crawls of USF sources"), and risks rate-limiting or ToS problems with
an unauthenticated public tenant.
**Why it happens:** the fastest way to get a real number is often the least bounded way to get it.
**How to avoid:** scope inventory work as the subject-level sampled pass described above, with
explicit timestamps and recorded partial/failed/unqueried states — never as a full section-by-
section or course-by-course sweep run without deliberate rate/volume limits.
**Warning signs:** any planned task that iterates every CRN or every course number without a
subject-level batching boundary and an explicit request-volume budget.

## Runtime State Inventory

Not applicable — Phase 1 is not a rename/refactor/migration phase. No renamed identifiers, no
datastore key renames, and no OS-registered state changes are in scope for this phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ / `uv` | All backend work, test baseline | ✓ | `uv 0.11.1`, project pins `>=3.12` (system Python is 3.14; `uv` manages the pinned interpreter) | — |
| pytest suite | Baseline regression (166 tests) | ✓ | Ran directly this session | — |
| Node.js / npm | Frontend baseline (19 tests) | ✓ | Node `v25.2.1`, npm `11.6.2` | — |
| `web/node_modules` | Frontend test/build | ✗ (until installed) | Installed this session via `npm install` (329 packages) | Re-run `npm install`; not committed, as expected for a Node project |
| Docker Engine | Local PostgreSQL via `docker-compose.yml` | ✗ | Docker CLI `29.2.0` present; daemon unreachable (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`) | Start Docker Desktop before any PostgreSQL-dependent work; blocks Phase 7's PostgreSQL integration tests, not Phase 1 |
| PostgreSQL 16 | Deployment-dialect parity, Phase 7 tests | ✗ (no `pg_isready` binary in this shell; no reachable server) | — | Not required for Phase 1; required starting Phase 7 |
| USF Staff Schedule Search (public HTTP) | Coverage inventory (OQ-02) | Not probed this session (constraint: no broad crawl) | — | A single narrow bounded query would need to be run as a scoped inventory task, not during research |
| Simple Syllabus public library (public HTTP/browser) | Coverage inventory (OQ-03) | Not probed this session (constraint: no broad crawl) | — | Same — scoped inventory task, not research |
| Real USF InfoCenter grade-distribution XLSX export | Source suppression/blank-cell confirmation | ✗ — no file supplied to this session | — | Requires ODS/registrar-side file; owner and blocked-phase noted below |
| Email provider (Resend or equivalent), sender-domain DNS, test inbox | Phase 5 (not Phase 1 implementation, but Phase 1 must list it) | ✗ | — | External dependency; ADR-17 forbids purchasing services during planning |

**Missing dependencies with no fallback (Phase 1 must list, not resolve):**
- Real approved historical grade export files and their actual terms (OQ-05) — owner: whoever holds
  ODS/registrar access; blocks Phase 2's real-data validation and Phase 7's real import.
- Deployment host/domain, email provider account, sender-domain DNS, designated test inbox (OQ-05)
  — owner: project stakeholder with purchasing/DNS authority; blocks Phases 5, 7, 8. ADR-17: do not
  purchase services during planning.

**Missing dependencies with fallback:**
- Docker/PostgreSQL unreachable in this specific research worktree — fallback is simply starting
  Docker Desktop before Phase 7 work; does not block Phase 1's documentation deliverables.

## Validation Architecture

`.planning/config.json` does not exist in this repository, so per the default rule
`workflow.nyquist_validation` is treated as enabled [VERIFIED: `ls .planning/` output this session
shows no `config.json`].

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest `>=8.3.0`, config in `pyproject.toml` (`testpaths = ["tests"]`) |
| Frontend framework | Vitest `^3.2.4` with `jsdom`, config in `web/vite.config.ts` |
| Quick run command (Python) | `uv run pytest -q` (confirmed: 4.75s for full suite in this worktree) |
| Quick run command (frontend) | `cd web && npm test` (confirmed: ~40s including environment setup) |
| Full suite command | Same as above — the entire suite already runs in well under 30s of actual test time; there is no separate "quick" subset needed at this codebase's current size |

### Phase Requirements → Test Map

Phase 1 itself produces no executable feature code — its "tests" are the reproducibility checks
already performed in this research (re-running the baseline suites, confirming git ancestry,
reading the exact formula/threshold code). There is nothing here for the Phase 1 *plan* to add as
new automated tests; the Wave 0 gap is entirely in Phase 2, listed below for the planner's
visibility.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-LAUNCH-01 | Baseline test count matches manifest | regression (existing) | `uv run pytest -q` && `cd web && npm test` | ✓ (both suites exist) |
| REQ-EVID-02 (Phase 2 target) | `effective_n == N` under default recency-disabled config | unit (net-new) | `uv run pytest tests/analytics/test_grades_and_scoring.py -k effective_n` (test does not yet exist under this name) | ❌ Wave 0 (Phase 2) |
| REQ-DATA-01 (Phase 2 target) | Blank grade cell does not silently become 0 once suppression state exists | unit (net-new) | not yet written | ❌ Wave 0 (Phase 2) |

### Sampling Rate
- **Per task commit (this phase):** re-run `uv run pytest -q` and `cd web && npm test` if any
  documentation change touches a claimed test count or formula constant.
- **Per wave merge:** same two commands — the suite is fast enough that there is no meaningful
  "quick vs. full" distinction at this size.
- **Phase gate:** both suites green (166/166, 19/19) before considering Phase 1 documents final;
  this was verified in this research session and should be re-verified once more immediately before
  Phase 1's plans are marked complete, in case intervening documentation-only commits are the only
  changes (they should not alter test counts, but re-verification is cheap).

### Wave 0 Gaps
- None for Phase 1 itself — it produces no executable code.
- For the planner's visibility into Phase 2: `tests/analytics/test_grades_and_scoring.py` combines
  scoring and confidence-label tests in one file with no test isolating RULE-60A from RULE-60B from
  RULE-60C [VERIFIED: `find tests -iname "*confidence*"` returned no dedicated file; `grep -rln
  "confidence_label_for\|LOW_CONFIDENCE_MAX\|HIGH_CONFIDENCE_MIN" tests/` returned only
  `tests/analytics/test_grades_and_scoring.py`, executed this session]. REQUIREMENTS.md's mandate
  that "a test exercising one must not be treated as coverage for another" is not yet satisfied by
  the existing test file's structure — Phase 2 should split or clearly delineate these cases.

## Security Domain

No `security_enforcement: false` setting exists in this repository (no `.planning/config.json` at
all), so the default (enabled) applies. Phase 1 adds no new endpoints, no new external service
integrations, and no new stored secrets — it is a documentation phase — so most ASVS categories are
not directly applicable to *this phase's own deliverables*. The table below is scoped to what Phase
1's inventory-methodology recommendation could touch if the planner schedules the subject-
enumeration/inventory utility as part of this phase's follow-on work.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth exists or is added; all sources touched are unauthenticated public endpoints [VERIFIED: `src/easy_a/catalog/client.py`, `schedule/client.py`, `syllabi/client.py` all construct plain unauthenticated `httpx.Client` instances, confirmed via the earlier full-file reads this session] |
| V5 Input Validation | Yes (existing, reused) | `SectionIdentifier` / `ParsedGradeDistribution` pydantic models already validate/normalize parsed text in `src/easy_a/grades/parser.py`; any new subject-enumeration parser must follow the same pydantic-model validation pattern rather than hand-rolled string slicing |
| V12 (SSRF-adjacent) — outbound request targets | Yes | `SimpleSyllabusClient` already host-pins to `usf.simplesyllabus.com` and validates document IDs against `^[A-Za-z0-9_-]+$` [VERIFIED: `src/easy_a/syllabi/client.py:10, 45-56`]; `CONCERNS.md` separately flags that `fetch_catalog_html` in `src/easy_a/catalog/client.py` will fetch *any* URL passed to it with no host allowlist [CITED: `.planning/codebase/CONCERNS.md`, "Server-side request surface on syllabus fetch"]. Any net-new subject-enumeration fetcher built for the inventory utility must pin its target host the same way `SimpleSyllabusClient` already does, not the way the catalog client currently does |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded outbound scraping against a public USF/Simple-Syllabus endpoint from a server-side fetcher | Denial of Service (against the *third party*, and reputational/ToS risk to the project) | Bound every new fetcher to a narrow, explicit query shape (as `ScheduleSearchQuery` and `SimpleSyllabusClient` already do) and never accept an unvalidated arbitrary URL server-side, matching the existing `SimpleSyllabusClient` host-pin pattern rather than the flagged `fetch_catalog_html` gap |
| Row-level injection via crafted grade-workbook cell text reaching a raised `ValueError` message that could later be logged verbatim | Information Disclosure (low severity — internal errors, not secrets) | Continue routing all such errors through the existing `GradeWorkbookValidationError`/`GradeRowValidationError` structured types [VERIFIED: `src/easy_a/grades/parser.py:38-46`, read this session] rather than raw string interpolation into logs, once structured logging is added in Phase 7 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The USF InfoCenter grade-distribution export's blank-cell convention represents true zero rather than small-cell suppression (or is undocumented either way) | Source Suppression and Blank-Cell Semantics | If real exports use blank-for-suppression, the current parser (and any Phase 2 work that reuses its blank-to-zero behavior without change) would understate true grade-distribution counts without any visible flag — a direct conflict with REQ-DATA-01/REQ-EVID-02's no-silent-fabrication rule |
| A2 | The public USF Staff Schedule Search form's subject dropdown, fetched once, is the correct authoritative source for a current-term Tampa subject list (rather than, e.g., a separate registrar course-inventory feed) | Coverage Inventory Methodology | If wrong, the subject-enumeration step could miss subjects offered only through a different listing surface, understating declared launch scope before any per-subject query even runs |
| A3 | No Simple Syllabus search/listing endpoint capable of multi-result enumeration exists or is safely usable without violating the no-broad-crawl constraint (this research did not attempt to discover or test such an endpoint) | Coverage Inventory Methodology, syllabus sub-section | If a legitimate multi-result search endpoint does exist and is confirmed safe to use at a bounded rate, the recommended "subject-level sampled inventory" fallback is more conservative than necessary, and a more complete OQ-03 inventory could be produced faster |
| A4 | The `.planning/codebase/TESTING.md` "~154 Python tests" figure was a measurement error or narrower-collection artifact rather than a real historical regression between `894da473` and `43f5b4d` | Confirmed Baseline section | Low risk — this research independently re-measured 166 at the current worktree HEAD via direct execution, so the resolution (166/19) stands regardless of why the older figure was different; flagged only for completeness |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **What is the true full-scope Tampa Spring 2027 section count, subject list, named-instructor
   rate, and current-syllabus rate?**
   - What we know: a 2-course, 46-section sample shows 100% `Staff` and 0/2 current syllabi found.
   - What's unclear: whether this generalizes campus-wide; no full-scope number can exist until the
     bounded subject-enumeration + per-subject schedule query described above actually runs.
   - Recommendation: schedule this as an explicit, timestamped inventory task (likely its own small
     plan within Phase 1 or a Phase 1.1 insertion), not as a research-session side effect. Record
     results with complete/partial/failed/unqueried states per subject, exactly as the roadmap's D-03
     and Phase 1 success criteria already specify.

2. **Does the real InfoCenter export format ever contain non-numeric or suppression-marker cells?**
   - What we know: the current parser's `_cell_to_int` treats any non-empty, non-numeric text as a
     hard row-rejection error, and any blank cell as `0`.
   - What's unclear: whether real exports contain either case at all — no real export file has been
     read in this session or supplied to this planning effort.
   - Recommendation: obtain at least one real or representative sample export before Phase 2 locks
     the parser's suppression-state model; owner is whoever holds ODS/registrar download access
     (per `01-CONTEXT.md`'s note that "the README records ODS approval for aggregate grade data" but
     "no real grade-export availability... has been verified in this planning session").

3. **Is there a legitimate, rate-safe Simple Syllabus multi-result search endpoint?**
   - What we know: the only client method in this repo fetches a single already-known document.
   - What's unclear: whether the tenant exposes any other unauthenticated endpoint suitable for
     bounded course-level search, which would materially change the cost of an OQ-03 inventory.
   - Recommendation: if the planner wants a more complete OQ-03 answer than the subject-sampled
     approach recommended above, this specific question should be resolved with one narrow,
     documented probe (e.g., inspecting the public library's own search page network requests)
     before committing to a broader syllabus-availability inventory design — but that probe itself
     is inventory *work*, not something this research session performed.

## Sources

### Primary (HIGH confidence — read or executed directly this session)
- `src/easy_a/analytics/confidence.py`, `scoring.py`, `grades.py` — read in full
- `src/easy_a/grades/parser.py` — read in full
- `src/easy_a/schedule/client.py`, `cli.py` — read in full
- `src/easy_a/syllabi/client.py`, `cli.py` — read in full
- `src/easy_a/catalog/client.py`, `parser.py` (partial), `cli.py` (partial) — read
- `src/easy_a/api/routes/metadata.py`, `src/easy_a/common/lookups.py`, `src/easy_a/common/terms.py` — read in full
- `tests/conftest.py` — read (partial, fixture setup)
- `uv run pytest --collect-only -q` and `uv run pytest -q` — executed this session (166/166)
- `npm install` and `npm test` in `web/` — executed this session (19/19)
- `git fetch origin main`, `git log origin/main -1`, `git merge-base --is-ancestor ...`, `git status`, `git branch -vv` — executed this session
- `docker info`, `docker compose ps` — executed this session (daemon unreachable)
- `docs/live-source-drift-2026-09-01.md` — read in full
- `docs/final-mvp-plan.md` — read in full

### Secondary (MEDIUM confidence — project-synthesized planning documents, already locked in this ingest)
- `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/INGEST-CONFLICTS.md` — read in full; these are themselves derived from the PRD/ADR/UI-spec set, not primary sources, but are the locked planning artifacts this research is bound to respect
- `.planning/codebase/STACK.md`, `ARCHITECTURE.md`, `TESTING.md`, `CONCERNS.md`, `INTEGRATIONS.md` — read in full; dated 2026-09-05, one commit behind this session's HEAD, cross-checked against direct code reads above where load-bearing

### Tertiary (LOW confidence — none used)
- No WebSearch or external-web lookups were performed in this research pass; the task's domain is
  entirely internal-repository verification and does not require external framework/library
  research. No new external package or service was evaluated.

## Metadata

**Confidence breakdown:**
- Baseline test counts and git ancestry: HIGH — directly executed and measured this session
- Method v2 formula/threshold reproducibility: HIGH for "what the code currently does," MEDIUM for
  "what the target contract requires" (sourced from already-locked planning documents, not
  independently re-derived from the original PRD's prose beyond what was read this session)
- Coverage inventory methodology (OQ-02/OQ-03 approach): HIGH for client capability/constraints
  (directly read), LOW for any implied campus-wide numeric outcome (explicitly not measured, by
  design)
- Source suppression/blank-cell semantics: HIGH for current code behavior, unresolvable-without-data
  for the source format's actual convention (flagged as an external dependency, not guessed at)

**Research date:** 2026-09-08
**Valid until:** Re-verify the git-ancestry and test-count claims immediately before Phase 1's plans
are finalized if more than a few days elapse (upstream `origin/main` could advance); the method-v2
and client-capability findings are stable until the underlying source files change.
