---
phase: 08-mvp1-p5-end-to-end-mvp-1-verification
reviewed: 2026-09-24T18:52:47Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - scripts/inventory_tampa_grades.py
  - scripts/validate_tampa_ingest.py
  - scripts/verify_rankings_pages.py
  - tests/api/test_verify_rankings_pages.py
  - tests/refresh/test_inventory_tampa_grades.py
  - tests/refresh/test_validate_tampa_ingest.py
  - web/src/components/RankingDetails.tsx
  - web/src/components/RankingEvidence.test.tsx
  - web/src/components/RankingTable.tsx
  - web/src/utils/rankings.ts
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-09-24T18:52:47Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the three new/changed read-only verification scripts (`inventory_tampa_grades.py`,
`validate_tampa_ingest.py`, `verify_rankings_pages.py`), their test suites, and the frontend
"honest evidence" work (`describeEvidence` in `rankings.ts` plus its consumers in
`RankingTable.tsx` / `RankingDetails.tsx` and the new `RankingEvidence.test.tsx`). Ruff, mypy,
eslint, `tsc -b`, and the full pytest/vitest suites for these files all pass, and the frontend
diff is well-covered by tests that assert D-20/D-21 wording on every surface.

The one blocker is in `inventory_tampa_grades.py`: a genuinely computed integrity signal
(`rows_at_or_after_term`) is surfaced in the JSON output's `"integrity"` block next to four
other integrity fields, but — unlike those four — it is never consulted when deciding the
PASS/FAIL verdict, so the exact anomaly this gate exists to catch (grade rows stamped at or
after the very term being inventoried, which D-21's evidence window says should be impossible)
can never fail the gate. A related precision gap in the `stale_cache` computation, and a
term-scoping asymmetry in `validate_tampa_ingest.py`'s suffix-leak check, are flagged as
warnings. Two minor, low-severity quality notes round out the findings.

## Critical Issues

### CR-01: `rows_at_or_after_term` is reported as an integrity signal but never gates the verdict

**File:** `scripts/inventory_tampa_grades.py:202-253` (verdict computation), `164`, `491-598`
(field computed), `621`, `678` (threaded into `Inventory`)

**Issue:** `Inventory.to_dict()` computes `integrity_ok` from exactly four booleans/counters:

```python
integrity_ok = (
    self.unattributed_grade_rows == 0
    and self.bucket_sum_mismatch_rows == 0
    and not self.stale_cache
    and self.non_tampa_section_count == 0
    and failure_section_count == 0
)
verdict = "PASS" if integrity_ok else "FAIL"
```

but the JSON `"integrity"` block presents `rows_at_or_after_term` as a fifth, seemingly
equivalent, integrity metric right alongside the four that do gate the verdict:

```python
"integrity": {
    "unattributed_grade_rows": self.unattributed_grade_rows,
    "bucket_sum_mismatch_rows": self.bucket_sum_mismatch_rows,
    "rows_at_or_after_term": self.rows_at_or_after_term,   # <-- never checked above
    "stale_cache": self.stale_cache,
    "non_tampa_section_count": self.non_tampa_section_count,
},
```

`rows_at_or_after_term` counts `GradeDistribution` rows whose `term_code >= before_term`
(`_aggregate_grade_rows`, lines 524-526) — i.e. grade rows stamped for the very term being
inventoried or later. Under D-21's evidence model (`Term.banner_code < before_term_code` in
`src/easy_a/analytics/queries.py`, matched here by `before_term=normalized_term`), a
Spring-2027-or-later grade row should never exist yet: the semester the pipeline is scoring
hasn't happened. A nonzero value is exactly the kind of "no narrower cause is assigned, never
silently absorbed" anomaly the module's own docstring promises to always surface as a named
integrity failure ("Every other outcome is a named integrity failure -- states are never
absorbed or hidden."). As written, it is silently absorbed: the script will print
`"verdicts": {"integrity": "PASS", ...}` and exit 0 even when this field is, say, 500.

No test in `tests/refresh/test_inventory_tampa_grades.py` exercises a nonzero
`rows_at_or_after_term` (the only fixture helper, `_make_inventory`, hardcodes
`rows_at_or_after_term=0`), so this gap has no regression coverage either.

**Fix:** Include the field in the gate, e.g.:

```python
integrity_ok = (
    self.unattributed_grade_rows == 0
    and self.bucket_sum_mismatch_rows == 0
    and self.rows_at_or_after_term == 0
    and not self.stale_cache
    and self.non_tampa_section_count == 0
    and failure_section_count == 0
)
```

and add a test seeding a row with `term_code >= before_term` asserting the verdict is `FAIL`.

## Warnings

### WR-01: `stale_cache` is computed from grade rows that never feed the score, risking both false positives and false negatives

**File:** `scripts/inventory_tampa_grades.py:492, 521-526, 647-651`

**Issue:** `overall_ingested_at_max` is updated for *every* fetched `GradeDistribution` row
before the `term_code >= before_term: continue` guard:

```python
if overall_ingested_at_max is None or ingested_at > overall_ingested_at_max:
    overall_ingested_at_max = ingested_at

if term_code >= before_term:
    rows_at_or_after_term += 1
    continue
```

so `grade_ingested_at_max` (and therefore `stale_cache = cache_refreshed_at_max <
grade_ingested_at_max`) reflects the most recent ingestion of *any* grade row, including one
whose term is at/after the term being inventoried — data that (per the D-21 evidence window)
never actually contributed to the cached scores. Two consequences:

- **False positive:** an operator can ingest an unrelated, out-of-window grade file (e.g. a
  premature Fall 2027 export) and trip `stale_cache=True`/gate FAIL even though nothing that
  actually feeds the Spring 2027 scores changed.
- **False negative (compounds CR-01):** if that out-of-window row's `ingested_at` happens to
  predate the last cache refresh, `stale_cache` stays `False`, so CR-01's gap isn't compensated
  for by this signal either.

**Fix:** Compute `overall_ingested_at_max` only from rows that pass the `term_code < before_term`
filter (the rows that actually feed `key_evidence`), matching what `stale_cache` is meant to
answer: "has the *evidence used by the cache* changed since the cache was last refreshed?"

### WR-02: `assert_suffix_exact_ingest` checks suffix-course existence without term-scoping, but term-scopes the section count it compares it against

**File:** `scripts/validate_tampa_ingest.py:84-100`

**Issue:**

```python
suffix_course_id = session.scalar(
    select(Course.id).where(Course.subject == subject, Course.number == suffix_number)
)
if suffix_course_id is None:
    continue

suffix_section_count = session.scalar(
    select(func.count(Section.id))
    .join(Term, Section.term_id == Term.id)
    .where(Term.banner_code == normalized_term, Section.course_id == suffix_course_id)
)
if not suffix_section_count:
    raise AssertionError(
        f"{subject} {suffix_number}: suffix course is ingested but owns 0 stored "
        f"sections for term {normalized_term} -- its sections were likely "
        f"mis-attributed to (leaked into) {subject} {base_number}."
    )
```

`Course` rows are not term-scoped in the schema (`src/easy_a/models/core.py` — no `term_id` on
`Course`), so `suffix_course_id` resolves to a course that exists *at all*, from any
import/term. The section-count check immediately after it, however, is scoped to
`normalized_term` only. If a suffix (e.g. lab) course is a legitimate catalog entry that simply
isn't offered in the specific term being validated — while its base course is — this raises a
false `AssertionError` claiming its sections "were likely mis-attributed," even though nothing
leaked. Given the codebase currently ingests a single term (Spring 2027) this is unlikely to
misfire today, but the check itself is internally inconsistent (unscoped existence check paired
with a scoped section check) and will misfire as soon as `Course` rows persist across more than
one ingested term (e.g. once historical-term catalog data or a second term's schedule is
ingested into the same tables).

**Fix:** Scope the `suffix_course_id` lookup to sections that actually exist for
`normalized_term` (e.g. join through `Section`/`Term` the same way the count query does), or
explicitly document/handle "configured as a target but not offered this term" as a distinct,
non-failing outcome instead of folding it into the "leaked" AssertionError.

## Info

### IN-01: `_environment_label` duplicated verbatim between the two new scripts

**File:** `scripts/inventory_tampa_grades.py:755-764`, `scripts/verify_rankings_pages.py:301-310`

**Issue:** Both new scripts define byte-identical `_environment_label(engine: Engine) -> str`
helpers (and a third, slightly different-signature copy already exists in
`scripts/benchmark_rankings_search.py`, per this module's own docstring). Any future change to
the Supabase-host-detection rule now has to be made in (at least) three places, and it's easy to
update one copy and miss another.

**Fix:** Extract to a shared helper (e.g. `scripts/_environment.py` or a small module under
`easy_a`) and import it from all three scripts.

### IN-02: Fractional `effective_n` in `(0, 0.5)` renders "0 grades" while still claiming `course_history` scope

**File:** `web/src/utils/rankings.ts:117-130`

**Issue:** `describeEvidence` classifies any `effective_n > 0` course/instructor_course row as
`scope: "course_history"` with `sampleLabel: `${Math.round(effective_n)} grades``. If a
genuinely course-backed row has a recency-shrunk `effective_n` between 0 and 0.5 (plausible
given `effective_n = min(effective_grade_n, effective_withdrawal_n)` with time-decay weighting,
per `scripts/inventory_tampa_grades.py:366-369`), the UI displays "0 grades" for a row that is,
by definition, claiming real course-level evidence — visually indistinguishable from the
`no_letter_grade_history`/`no_course_evidence` "No letter grades"/"No course grades" states this
same change was written to make unambiguous. This rounding behavior predates this diff (the old
code always rendered `Math.round(ranking.effective_n)} grades` regardless of scope), so it is
not a regression, but the new evidence-scope labeling makes the inconsistency more visible and
worth tightening given how central "honest coverage" wording is to this phase.

**Fix:** Consider flooring the displayed sample at "<1 grade" (or similar) instead of rounding
to 0 for the `course_history` scope specifically, so a real-but-tiny evidence sample is never
textually identical to "no evidence."

---

_Reviewed: 2026-09-24T18:52:47Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
