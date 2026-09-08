# Phase 1: Baseline, Scope and Contracts - Pattern Map

**Mapped:** 2026-09-08
**Files analyzed:** 6 (3 documents, 3 code-adjacent items)
**Analogs found:** 3 / 3 for code-touching deliverables; documents have no code analog by design

## Phase Nature Note

Phase 1 is primarily a documentation/contract phase (launch coverage manifest, method-v2
reproducibility contract, UI/API state contract traceability). Those deliverables are
**documents, not modules** — there is no source-code analog to copy from, and none should be
forced. This file concentrates pattern guidance on the three places Phase 1's scope genuinely
touches or must inventory existing source, per the orchestrator's note:

1. A bounded subject-enumeration + per-subject inventory utility (net-new, narrow).
2. `src/easy_a/grades/parser.py` blank-cell/suppression-marker documentation gap (Phase 1
   documents the gap; Phase 2 fixes the code).
3. `src/easy_a/analytics/confidence.py` effective_n/N equivalence (Phase 1 documents the gap;
   Phase 2 fixes/tests the code).

## File Classification

| New/Modified File (likely) | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `01-LAUNCH-COVERAGE-MANIFEST.md` (or similar, phase doc) | config/doc | — | none (document) | n/a |
| `01-METHOD-V2-CONTRACT.md` (or similar, phase doc) | config/doc | — | none (document) | n/a |
| new subject-enumeration fetcher (e.g. `src/easy_a/schedule/subjects.py`, net-new, if scoped as work) | service/client | request-response, batch | `src/easy_a/syllabi/client.py` (host-pinned single-purpose HTTP client) | role-match |
| new per-subject inventory CLI/script (e.g. `scripts/inventory_schedule.py`, if scoped as work) | utility/CLI | batch | `src/easy_a/schedule/cli.py` + `scripts/ingest_schedule.py` | exact |
| grade suppression-state documentation (targets `src/easy_a/grades/parser.py`, no code change in Phase 1) | model/parser | transform | `src/easy_a/grades/parser.py` itself (self-analog; document what exists) | exact (self) |
| confidence equivalence documentation (targets `src/easy_a/analytics/confidence.py` + `grades.py`, no code change in Phase 1) | service/utility | transform | `src/easy_a/analytics/confidence.py` + `src/easy_a/analytics/grades.py` (self-analog) | exact (self) |

## Pattern Assignments

### Net-new subject-enumeration / bounded inventory utility (if the plan schedules it)

**Role:** service/client (fetch) + utility/CLI (invocation), data flow: request-response then batch.

**Analog 1 — narrow, host-scoped HTTP client:** `src/easy_a/syllabi/client.py`

Imports/setup pattern (lines 1-26):
```python
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

BASE_URL = "https://usf.simplesyllabus.com"
DEFAULT_USER_AGENT = "Easy-A data pipeline (https://github.com/aatif101/easy-A)"
_DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class SimpleSyllabusClient:
    def __init__(
        self,
        http_client: httpx.Client | None = None,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=BASE_URL,
            follow_redirects=True,
            timeout=timeout_seconds,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
```

Host-pin / input-validation pattern (lines 45-56) — **any new subject-enumeration fetcher must
copy this validation shape**, not the unbounded `fetch_catalog_html` pattern flagged in
`.planning/codebase/CONCERNS.md`:
```python
def extract_document_id(document_id_or_url: str) -> str:
    value = document_id_or_url.strip()
    if not value:
        raise ValueError("Simple Syllabus document ID cannot be empty.")
    if "://" in value:
        parsed = urlparse(value)
        if parsed.hostname != "usf.simplesyllabus.com":
            raise ValueError("Only public usf.simplesyllabus.com document URLs are supported.")
        value = parsed.path.rstrip("/").split("/")[-1]
    if not _DOCUMENT_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid Simple Syllabus document ID {value!r}.")
    return value
```

**Analog 2 — bounded query dataclass with `__post_init__` validation:**
`src/easy_a/schedule/client.py` lines 14-31:
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
        if self.crn is not None and not has_crn:
            raise ValueError("CRN cannot be empty.")
        if self.subject is not None and not has_subject:
            raise ValueError("Subject cannot be empty.")
        if not has_crn and not has_subject:
            raise ValueError("A narrow schedule search requires --crn or --subject.")
```
Any new "subject-list" query object (e.g. one bounded fetch of the USF Staff Schedule Search
subject dropdown) should follow this same frozen-dataclass-with-validation shape, reusing
`normalize_banner_term_code` from `src/easy_a/common/terms.py` (per RESEARCH.md's Don't-Hand-Roll
table) rather than duplicating term validation.

**Analog 3 — client + ingest CLI wiring:** `src/easy_a/schedule/cli.py` (full file, 40 lines) and
its one-line entry-point shim `scripts/ingest_schedule.py`:
```python
# scripts/ingest_schedule.py — the entire pattern for any new inventory script's entry point
from __future__ import annotations
from easy_a.schedule.cli import main
if __name__ == "__main__":
    raise SystemExit(main())
```
```python
# src/easy_a/schedule/cli.py — argparse + client + session_factory + print-summary pattern
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest a narrow public USF schedule search.")
    parser.add_argument("--term", required=True, help="Six-digit Banner term, e.g. 202701.")
    parser.add_argument("--campus", help="Banner campus code, e.g. T for Tampa.")
    parser.add_argument("--subject", required=True, help="Course subject, e.g. MAC.")
    parser.add_argument("--course", help="Course number, e.g. 1105.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = ScheduleSearchQuery(term=args.term, campus=args.campus, subject=args.subject, course=args.course)
    with StaffScheduleClient() as client:
        html = client.search(query)
    session_factory = get_session_factory()
    with session_factory.begin() as session:
        result = ingest_schedule_html(session, html, args.term)
    print(f"Schedule ingest succeeded: seen={result.records_seen} inserted={result.records_inserted} ...")
    return 0
```
A new bounded "enumerate Tampa subjects for term X" script should follow this exact shape: an
argparse CLI in `src/easy_a/schedule/` (or a new `inventory` submodule) with a thin
`scripts/*.py` shim, reusing `StaffScheduleClient`/`ScheduleSearchQuery` for the per-subject
follow-up pass, and printing a structured summary line rather than raw output — matching D-03's
requirement for explicit complete/partial/failed/unqueried states per subject.

**Existing subject-list source that is circular for this purpose** (do not copy as the
enumeration source, only as the eventual read-model): `src/easy_a/api/routes/metadata.py` lines
1-37 — `list_subjects` derives subjects from `select(Course.subject).distinct()`, i.e. only
subjects already imported. This is useful as the pattern for how subjects are *served* to the
frontend later, not as the pattern for *discovering* subjects campus-wide.

---

### Grade suppression / blank-cell documentation target

**File:** `src/easy_a/grades/parser.py` (self-analog — Phase 1 documents this behavior verbatim,
it does not change it)

Current blank-to-zero conversion (lines 250-262, quoted for the manifest/contract document):
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
```
Row-level rejection wrapper pattern to reference when documenting the "no suppression marker
path" gap (lines 168-176 area, and error types at lines 30-46):
```python
class GradeRowValidationError(BaseModel):
    row_number: int
    course: str
    message: str
    model_config = ConfigDict(frozen=True)

class GradeWorkbookValidationError(ValueError):
    def __init__(self, errors: Sequence[GradeRowValidationError], records_seen: int) -> None:
        ...
```
and the count-sum-must-equal-total-grades check that ties `N`/`T` together:
```python
count_sum = sum(counts.values())
if count_sum != total_grades:
    errors.append(GradeRowValidationError(row_number=row_number, course=course_text,
        message=f"count sum {count_sum} does not equal Total Grades {total_grades}"))
    continue
```
**Phase 1 action:** cite these exact ranges in the method-v2/data-contract document as the
confirmed current behavior; do not modify this file in Phase 1 (Phase 2 owns the fix per
REQ-DATA-01/REQ-EVID-02).

---

### Confidence-label effective_n/N equivalence documentation target

**File:** `src/easy_a/analytics/confidence.py` (self-analog, full file already read — 57 lines)

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
Paired with `src/easy_a/analytics/grades.py:127-148` (effective_n derivation and the
recency-disabled uniform-weight branch — cited fully in RESEARCH.md's RULE-60C section; not
re-quoted here to avoid duplicate reads). **Phase 1 action:** the launch/method contract document
must state the `effective_n == N` equivalence explicitly and flag it as contingent on
`RecencyConfig(enabled=False)`, per RESEARCH.md's Pitfall 2. No code change in Phase 1.

## Shared Patterns

### Narrow, host-pinned, validated HTTP client shape
**Source:** `src/easy_a/syllabi/client.py` (host-pin + regex ID validation) and
`src/easy_a/schedule/client.py` (frozen dataclass query with `__post_init__` validation)
**Apply to:** any net-new fetcher this phase scopes for subject/section enumeration. Do **not**
follow `src/easy_a/catalog/client.py`'s `fetch_catalog_html`, which `.planning/codebase/CONCERNS.md`
flags as accepting an unvalidated arbitrary URL server-side — this is the anti-pattern, not the
pattern.

### CLI entry-point wiring
**Source:** `src/easy_a/schedule/cli.py` + `scripts/ingest_schedule.py`
**Apply to:** any new inventory CLI/script — argparse parser in the package module, thin
`if __name__ == "__main__": raise SystemExit(main())` shim in `scripts/`.

### Banner term validation
**Source:** `src/easy_a/common/terms.py` (`normalize_banner_term_code`, `parse_banner_term`)
**Apply to:** any new code that accepts a term string (e.g. `202701`) — reuse this module rather
than duplicating regex/format validation, per RESEARCH.md's Don't-Hand-Roll table.

### Structured validation errors over raw exceptions
**Source:** `src/easy_a/grades/parser.py:30-46` (`GradeRowValidationError` /
`GradeWorkbookValidationError`)
**Apply to:** any new row/record-level validation in an inventory or parser context — collect
structured per-record errors rather than raising on first failure, matching this file's existing
approach.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Launch coverage manifest document | config/doc | — | Documentation deliverable; no source-code file plays this role. Use `.planning/ROADMAP.md` and `docs/final-mvp-plan.md` structure as formatting precedent, not a code analog. |
| Method v2 reproducibility contract document | config/doc | — | Documentation deliverable; content is already assembled in `01-RESEARCH.md`'s "Method v2 Reproducibility Contract" section — the phase document should restate it as a locked contract, not invent new structure. |
| UI/API state contract traceability document | config/doc | — | `docs/final-mvp-ui-spec.md` (already adapted as `01-UI-SPEC.md`) is the existing contract; Phase 1's job is to add payload-field traceability notes to it, not create a new component. |
| Simple Syllabus multi-result search/enumeration | service | batch | Explicitly confirmed not to exist anywhere in this codebase or externally verified this session (RESEARCH.md Open Question 3) — no analog can exist yet; document as an open dependency instead. |

## Metadata

**Analog search scope:** `src/easy_a/schedule/`, `src/easy_a/syllabi/`, `src/easy_a/catalog/`,
`src/easy_a/grades/`, `src/easy_a/analytics/`, `src/easy_a/api/routes/`, `src/easy_a/common/`,
`scripts/`
**Files scanned:** 9 (client.py x3, cli.py x2, parser.py, confidence.py, ingest_schedule.py,
metadata.py)
**Pattern extraction date:** 2026-09-08
</content>
</invoke>
