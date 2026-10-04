# Phase 6: MVP1-P3 — All-Tampa section ingestion (10 → ~3,782) - Pattern Map

**Mapped:** 2026-09-21
**Files analyzed:** 5 (1 new script, 1 new/regenerated config, 3 candidate code touch-points)
**Analogs found:** 5 / 5

All analog paths below were verified git-tracked via `git ls-files` before being cited (Tracked-
source gate, #3645) — none are gitignored mirrors.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `scripts/generate_tampa_targets.py` (NEW) | utility / config-generator | transform (CSV → validated TOML/JSON) | `src/easy_a/refresh/targets.py` (validation model) + `src/easy_a/catalog/cli.py` (script/CLI shape) | role-match (composite — no existing "read file, validate, write config" script exists; nearest CLI shape + nearest validation model) |
| `config/course_targets.toml` (RECONCILE — full ~1,402-entry list or stays pilot-sized with `--targets` override) | config | batch (static data file consumed at ingest time) | itself (existing 5-entry file) — same file, same schema, larger cardinality | exact |
| `src/easy_a/refresh/coverage.py` (`refresh_targets`, `_retain_exact_course_rows`) | service | CRUD (per-course catalog+schedule ingest loop) | itself — **no modification recommended**, reused unmodified at scale | exact (self) |
| Orchestration: per-subject batched invocation (NEW — shell loop or `scripts/refresh_tampa_coverage.sh`-style runbook, not necessarily a new Python file) | script / runbook | batch (bounded transaction per subject) | `src/easy_a/refresh/target_cli.py` (existing `--subject`/`--course`/`--crn` filters, existing per-invocation `get_session_factory().begin()` transaction scope) | exact (reuses existing flag, zero new production code) |
| `tests/refresh/test_generate_targets.py` (NEW — Wave 0 gap identified in RESEARCH.md) | test | transform / batch | `tests/refresh/test_targets.py` (`test_config_parsing_and_filters`, lines 39-53) | exact (same fixture/assertion style, same `CourseTarget`/`CourseTargets` model under test) |

No new controller/component/route/model/middleware files are implied by this phase — RESEARCH.md
is explicit that no new persistence model, API route, or frontend work is in scope.

## Pattern Assignments

### `scripts/generate_tampa_targets.py` (NEW) — utility, transform

**Analogs:** `src/easy_a/refresh/targets.py` (validation core) and `src/easy_a/catalog/cli.py` (script shape)

**Imports pattern** — copy the `CourseTarget`/`CourseTargets` import + stdlib-only shape already
used by `targets.py` (`src/easy_a/refresh/targets.py:1-9`):
```python
from __future__ import annotations

import tomllib
from pathlib import Path
from string import Formatter

from pydantic import BaseModel, ConfigDict, Field, model_validator

from easy_a.config import get_settings
```
For the generator script itself, follow `catalog/cli.py`'s import shape (`src/easy_a/catalog/cli.py:1-8`):
```python
from __future__ import annotations

import argparse
from pathlib import Path

from easy_a.catalog.client import fetch_catalog_html
from easy_a.catalog.ingest import ingest_catalog_html
from easy_a.db import get_session_factory
```
i.e. `from __future__ import annotations`, stdlib first, then `easy_a.*` absolute imports — no
relative imports anywhere in this codebase (confirmed across every file read this session).

**Core pattern — validate every row against the existing model, do not hand-roll validation**
(`src/easy_a/refresh/targets.py:12-40`, read in full this session):
```python
class CourseTarget(BaseModel):
    subject: str = Field(pattern=r"^[A-Z]{2,4}$")
    number: str = Field(pattern=r"^[0-9]{4}[A-Z]?$")
    model_config = ConfigDict(frozen=True, extra="forbid")


class CourseTargets(BaseModel):
    catalog_edition: str = Field(min_length=1)
    catalog_url_template: str
    targets: tuple[CourseTarget, ...] = Field(min_length=1)
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_targets(self) -> CourseTargets:
        if len(set(self.targets)) != len(self.targets):
            raise ValueError("Duplicate course targets.")
        if not self.catalog_url_template.startswith("https://"):
            raise ValueError("Catalog URL must use HTTPS.")
        fields = {
            field
            for _, field, _, _ in Formatter().parse(self.catalog_url_template)
            if field is not None
        }
        if fields != {"subject", "number"}:
            raise ValueError("Catalog URL template requires {subject} and {number} only.")
        self.catalog_url_template.format(
            subject=self.targets[0].subject, number=self.targets[0].number
        )
        return self
```
The generator script should build a `CourseTargets(...)` instance (or a `tuple[CourseTarget, ...]`
that is subsequently wrapped in one) directly from parsed `courses.csv` rows and let this
`model_validator` raise `ValidationError`/`ValueError` at generation time — this is the exact
mechanism RESEARCH.md's Code Examples section sketches (`CourseTarget(subject=row["subject"],
number=row["number"])` per row). **Do not** write new regex/duplicate-checking logic; the model
already does both (pattern fields + `validate_targets`'s `len(set(...)) != len(...)` check).

**CLI shape to copy** (`src/easy_a/catalog/cli.py:11-49`, the closest existing "small script,
argparse, read input, print a one-line summary, return an int exit code" shape in the repo):
```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest public USF catalog course HTML.")
    parser.add_argument("--catalog-edition", required=True, help="Catalog edition, e.g. 2026-2027.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url", help="Public catalog or course inventory URL to fetch.")
    source.add_argument("--file", type=Path, help="Local HTML fixture/file to ingest.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ...
    return 0
```
Follow the same `build_parser()` / `main(argv: list[str] | None = None) -> int` split (also used by
`target_cli.py`, `src/easy_a/refresh/target_cli.py:15`) so the new script is testable the same way
`tests/refresh/test_targets.py::test_cli_one_pass_and_empty_warning` (lines 247-277) tests
`target_cli.main` — call `main([...])` directly in a test, assert the return code and `capsys`
output, rather than shelling out.

**Error handling pattern:** Let `pydantic.ValidationError` / the model's own `ValueError`s propagate
uncaught to a non-zero exit — this matches `load_targets`'s own behavior (`targets.py:58-60`,
`CourseTargets.model_validate(tomllib.loads(...))` — no try/except wrapping, errors are meant to
surface directly) and `catalog/cli.py:37-39`'s narrow `except Exception: session.commit(); raise`
(commit-then-reraise, never swallow).

**No test file currently covers this** — see `tests/refresh/test_generate_targets.py` below.

---

### `config/course_targets.toml` (RECONCILE) — config, batch

**Analog:** itself — same schema, same file, decide cardinality per Open Question 1 in RESEARCH.md

**Schema to preserve exactly** (`config/course_targets.toml:1-19`, full file read this session):
```toml
catalog_edition = "2026-2027"
catalog_url_template = "https://cloud.usf.edu/academic-programs/details/prefix/{subject}/code/{number}"

[[targets]]
subject = "MAC"
number = "1105"
[[targets]]
subject = "ENC"
number = "1101"
```
Whatever the planner decides on Open Question 1 (commit the full ~1,402-entry list here vs. keep
this file pilot-sized and pass a generated file via `target_cli.py`'s existing `--targets` flag,
`target_cli.py:18`), the **shape** of each entry (`[[targets]]` array-of-tables with `subject`/
`number` string fields) must stay byte-for-byte compatible with `CourseTarget`/`CourseTargets`
above — `load_targets` (`targets.py:58-60`) parses this file with `tomllib` and
`CourseTargets.model_validate`, so any deviation fails validation, not silently.

---

### Per-subject batched orchestration (NEW runbook/script) — script, batch

**Analog:** `src/easy_a/refresh/target_cli.py` (existing `--subject` filter; existing
per-invocation transaction scope)

**Core pattern — the existing CLI already does everything one subject-batch needs**
(`src/easy_a/refresh/target_cli.py:15-36`, full file read this session):
```python
def main(argv: list[str] | None = None, *, coverage: bool = False) -> int:
    parser = argparse.ArgumentParser(description="One-pass configured course refresh")
    parser.add_argument("--term", required=True)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--subject")
    parser.add_argument("--course")
    parser.add_argument("--crn")
    args = parser.parse_args(argv)
    config = load_targets(args.targets)
    targets = config.select(args.subject, args.course)
    with get_session_factory().begin() as session, StaffScheduleClient() as client:
        ensure_term(session, args.term)
        rows = refresh_targets(
            session,
            term=args.term,
            config=config,
            search=client.search,
            refresh_catalog=coverage,
            subject=args.subject,
            course=args.course,
            crn=args.crn,
        )
        ...
```
Note `with get_session_factory().begin() as session` wraps the **entire** `refresh_targets` call in
one transaction, per invocation (`target_cli.py:25`) — this is exactly the mechanism RESEARCH.md's
Pitfall 1 identifies as unsafe at full-universe scale and exactly why the recommended fix is
invoking this unmodified CLI once per subject (bounding blast radius to 1–33 courses), not editing
this function. `scripts/refresh_course_coverage.py` (`refresh_course_coverage.py:1-5`) is the thin
`if __name__ == "__main__"` wrapper that calls `target_cli.main(coverage=True)` — this is the
existing entrypoint to invoke per subject; RESEARCH.md's Code Examples section already shows the
per-subject shell loop:
```sh
for subject in $(cut -d, -f1 courses.csv | tail -n +2 | sort -u); do
  uv run python scripts/refresh_course_coverage.py \
    --term 202701 \
    --targets config/course_targets_full.toml \
    --subject "$subject"
  sleep 2   # pacing, per Pitfall 4
done
```
**Do not** add pacing/retry/backoff logic inside `coverage.py`/`target_cli.py` themselves — per
RESEARCH.md's Anti-Patterns and Pitfall 4, this is an execution-time/runbook concern layered on top
of unmodified production functions, not a signature change to `refresh_targets` or `main`.

---

### `src/easy_a/refresh/coverage.py` — service, CRUD (reused unmodified)

**Analog:** itself. Confirmed via `git ls-files -- src/easy_a/refresh/coverage.py` (tracked).

**Do not modify `refresh_targets` or `_retain_exact_course_rows`.** Both were read in full this
session (`coverage.py:74-182` and `coverage.py:185-214`) and match RESEARCH.md's description
exactly: `refresh_targets` does catalog-fetch → `resolve_course_id` precondition → schedule search →
`_retain_exact_course_rows` suffix filter → Tampa/CRN scope assertion (raises `ValueError` on
violation, which the caller's transaction rolls back) → `ingest_schedule_html` → cache refresh, per
target, in one Python loop. The one **inconsistency worth fixing for consistency** (flagged in
RESEARCH.md's Don't-Hand-Roll table, not a functional bug) is that the scope guard at
`coverage.py:151-155` compares `r.campus.strip() != "Tampa"` directly instead of calling the shared
`same_campus`/`describe_campus` helpers already used by `quality/checks.py::_check_section_campus`
(see below) — if the plan chooses to touch this line, copy the shared helper rather than
re-deriving the string comparison:
```python
# src/easy_a/common/campus.py:1-19 (full file read this session)
SUPPORTED_CAMPUS = "Tampa"


def same_campus(stored: str | None, expected: str) -> bool:
    if stored is None or not stored.strip():
        return False
    return stored.strip().casefold() == expected.strip().casefold()
```

---

### `tests/refresh/test_generate_targets.py` (NEW) — test, transform/batch

**Analog:** `tests/refresh/test_targets.py::test_config_parsing_and_filters` (lines 39-53, full file
read this session)

**Pattern to copy:**
```python
def test_config_parsing_and_filters(tmp_path: Path) -> None:
    config = load_targets()
    assert len(config.targets) == 5
    assert config.select("mac", "1105") == (CourseTarget(subject="MAC", number="1105"),)
    for subject, course in [(None, "1105"), ("XXX", None)]:
        with pytest.raises(ValueError):
            config.select(subject, course)
    source = Path("config/course_targets.toml").read_text()
    path = tmp_path / "targets.toml"
    path.write_text(source + '\n[[targets]]\nsubject="MAC"\nnumber="1105"\n')
    with pytest.raises(ValueError, match="Duplicate"):
        load_targets(path)
    path.write_text(source.replace('subject = "MAC"', 'subject = "../MAC"'))
    with pytest.raises(ValueError):
        load_targets(path)
```
For the new test, follow the same `tmp_path`-based fixture style: write (or reuse) a `courses.csv`
sample into `tmp_path`, run the new generator's row-to-`CourseTarget` conversion over every row, and
assert (a) it produces exactly the expected count with zero `ValidationError`s for a clean input,
matching RESEARCH.md's claim that all 1,402 real rows pattern-match with zero exceptions, and (b) it
raises (not silently drops) on a deliberately malformed row (e.g. lowercase subject, 3-digit
number) — mirroring how `test_config_parsing_and_filters` asserts `pytest.raises(ValueError)` for a
path-traversal-shaped subject (`"../MAC"`) rather than silently ignoring it. Also add a test in the
same style as `tests/refresh/test_coverage_suffix_guard.py` (full file read this session,
`test_suffix_variants_are_excluded_before_scope_validation`, lines 15-38) if the plan chooses to
exercise `_retain_exact_course_rows` against more than one of the 33 documented suffix-risk base
courses — the fixture-building helper `_mixed_chm_response` (lines 73-105) is directly reusable as a
template, parametrized by `(subject, number, suffix_number)` instead of hardcoded `CHM`/`2045`/
`2045L`.

## Shared Patterns

### Transaction-per-invocation (existing, must not be widened)
**Source:** `src/easy_a/refresh/target_cli.py:25` — `with get_session_factory().begin() as session`
**Apply to:** Any orchestration script/runbook step that drives `refresh_targets` at scale. Each
process invocation is its own transaction; the plan must keep invocation granularity at "one
subject" (1–33 courses per `courses.csv`), not "all ~1,402 targets," per RESEARCH.md Pitfall 1.
Verified this session (`tests/refresh/test_targets.py::test_cli_source_failure_rolls_back`, lines
280-300) that a mid-batch failure rolls back *every* row from that invocation — this is exercised
and correct behavior, just must be bounded to small batches at call time.

### Suffix-row exclusion before ingest (existing, do not touch)
**Source:** `src/easy_a/refresh/coverage.py:185-214` (`_retain_exact_course_rows`)
**Apply to:** Every one of the 33 base courses in `data/coverage-pilot-2026-09-20/suffix-query-risks.json`
that have a suffix variant. The mechanism is generic (24-`<th>`/24-`<td>` row detection + positional
zip against parsed rows), not CHM-specific — no per-course special-casing needed in the target
generator; each base/suffix pair simply needs its own `CourseTarget` row (confirmed this session
that `courses.csv` already lists `CHM,2045` and `CHM,2045L` as two separate rows).

### Tampa/course/CRN scope assertion (existing, do not weaken)
**Source:** `src/easy_a/refresh/coverage.py:151-155`
```python
if any(
    r.campus.strip() != "Tampa" or (crn is not None and r.crn != crn)
    for r in rows
):
    raise ValueError("Schedule response exceeded the requested Tampa/course/CRN scope.")
```
**Apply to:** Every ingestion pass, at every scale. This is the exact guard that fixed the PR #18
47-row non-Tampa contamination incident; RESEARCH.md's Anti-Patterns section explicitly forbids
loosening it. Any subject/course whose schedule response legitimately contains non-Tampa rows must
be handled by row-level exclusion (same technique as `_retain_exact_course_rows`), never by relaxing
this check.

### Data-quality verification at scale (existing, run unmodified)
**Source:** `src/easy_a/quality/checks.py::run_quality_checks` (full file read this session, lines
49-118) and `src/easy_a/quality/coverage.py::coverage_findings` (full file read this session)
**Apply to:** Post-ingestion verification for the full ~3,782-section universe. Already includes
`unsupported_campus_section` (`checks.py:191-211`, the exact Tampa-only guard as an independent
DB-level check), `target_missing_catalog`/`target_missing_sections` (`coverage.py:16-31` in
`quality/`), `no_historical_analytics`/`low_confidence_ranking` (`checks.py:431-474`, the D-20
honest-fallback signal). No term-size assumption was found in this file that would break at
~3,782 rows — reuse via `scripts/check_data_quality.py --term 202701 --json`
(`scripts/check_data_quality.py` → `easy_a.quality.cli.main`), do not write a new scale-specific
checker.

### Core-identity resolution (existing, do not duplicate)
**Source:** `src/easy_a/common/lookups.py:33-49` (`resolve_course_id`)
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
**Apply to:** Already called by `src/easy_a/schedule/ingest.py:68` (`_upsert_sections`) for every
parsed row, and enforced as a precondition inside `refresh_targets` (`coverage.py:125-139`, checks
`Course.id` presence before ever calling `search`). No new file in this phase should re-implement
subject/number lookup or normalization — import and call this function.

## No Analog Found

None. Every file this phase touches or creates has a concrete, git-tracked analog read this
session — either an existing sibling of the same shape (`config/course_targets.toml` reconciled
against itself) or a close composite of two existing patterns (the new generator script combining
`targets.py`'s validation model with `catalog/cli.py`'s CLI shape).

## Metadata

**Analog search scope:** `src/easy_a/refresh/`, `src/easy_a/catalog/`, `src/easy_a/schedule/`,
`src/easy_a/common/`, `src/easy_a/quality/`, `scripts/`, `tests/refresh/`, `config/`
**Files scanned:** 15 read this session (10 source, 2 test, 1 config, 2 thin script wrappers), all
confirmed git-tracked via `git ls-files` before citation
**Pattern extraction date:** 2026-09-21
