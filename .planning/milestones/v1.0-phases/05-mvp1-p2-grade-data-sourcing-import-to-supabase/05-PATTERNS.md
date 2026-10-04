# Phase 5: MVP1-P2 — Grade data sourcing + import to Supabase - Pattern Map

**Mapped:** 2026-09-21
**Files analyzed:** 0 required new/modified production files; 1 conditional new test file identified
**Analogs found:** 1 / 1 (conditional file only)

## Headline finding: this phase creates no new production code path

RESEARCH.md's own conclusion (`## Summary`, `## Don't Hand-Roll`, `## Validation Architecture` →
"This phase adds no new production code path") is confirmed by directly reading every file it
names. The phase is an **operational data-import workflow**: source an approved InfoCenter XLSX
(external/Codex-owned), run two existing CLI commands, and validate with two more existing CLI
commands. There is no controller, service, model, middleware, route, hook, provider, or store to
scaffold. Do not let the planner invent a "grade import service" or "validation script" — both
already exist and are exercised by the existing test suite.

Confirmed by direct read this session (not inference):

- `scripts/refresh_data.py`, `scripts/analyze_course.py`, `scripts/check_data_quality.py`,
  `scripts/ingest_grades.py` are all four-line stubs that import `main()` from the corresponding
  `src/easy_a/*/cli.py` module and call `raise SystemExit(main())` — there is no script-local logic
  to add or modify.
- `src/easy_a/refresh/cli.py` (full file, 221 lines) already defines `--grade-file`, `--term`,
  `--skip-catalog`, `--skip-schedule`, `--skip-grades`, `--skip-syllabi` exactly as RESEARCH.md's
  recommended command lines use them.
- `src/easy_a/refresh/service.py:88-91` already runs an unconditional `"rankings cache"` stage keyed
  on `config.term` — confirming Pitfall 2 (two-command import is a real, already-built constraint,
  not something to code around).
- `src/easy_a/quality/checks.py:452-462` already emits the `no_historical_analytics` finding per
  section with zero grade coverage — confirming Pitfall 5 (no new "lacking data" tracking needed).
- `src/easy_a/grades/parser.py:277-282` already fails closed on blank count cells with a message
  that explicitly refuses to assume zero-vs-suppressed-vs-unavailable semantics (this is exactly
  where OQ-04 would surface against a real export, with no code change required to detect it).

**Planner implication:** No `## File Classification` / `## Pattern Assignments` table is populated
for new production files because there are none. The one place net-new code *could* legitimately
land — if a real InfoCenter export's blank-cell shape needs to be encoded as a regression fixture
per OQ-04 — is described below as a single conditional file with its analog fully mapped, so the
planner can act on it immediately if the sourced export turns out to contain blank cells.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `tests/grades/test_parser_real_export_shape.py` (conditional — only if OQ-04 needs a fixture) | test | file-I/O | `tests/grades/test_parser.py` | exact |

No other files are created or modified by this phase. The import/validation work itself is a
sequence of existing-CLI invocations (see `## Shared Patterns` → "Operator command sequence"),
not a code change.

## Pattern Assignments

### `tests/grades/test_parser_real_export_shape.py` (test, file-I/O) — CONDITIONAL

**Only create this file if the sourced InfoCenter export contains a blank canonical grade-count
cell (OQ-04) and the plan decides to encode its real shape as a permanent regression fixture.** If
the sourced export has no blank cells, do not create this file — there is nothing to regress-test
that `tests/grades/test_parser.py`'s existing synthetic blank-cell cases
(`test_blank_bucket_count_fails_closed`, `test_blank_total_fails_closed`) don't already cover.

**Analog:** `tests/grades/test_parser.py` (git-tracked: `git ls-files` confirms
`tests/grades/test_parser.py`; 217 lines, read in full this session)

**Imports pattern** (`tests/grades/test_parser.py:1-12`):
```python
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from easy_a.grades.parser import (
    GradeWorkbookValidationError,
    parse_grade_workbook,
    parse_section_identifier,
)
```

**Fixture-workbook-building pattern** (`tests/grades/test_parser.py:14-37`, `164-217`): a module-level
`GRADE_HEADER` list matching the real InfoCenter column order, a `_write_workbook(path, rows)`
helper that builds an `openpyxl.Workbook`, appends the header then each row, and saves — plus a
`_grade_row(...)` keyword-based row builder and a `_hierarchy_row(label)` builder for the
campus/subject/total rows the parser is expected to skip. **A new fixture file should extract the
real export's actual header order/row shape into this same `_write_workbook` + `_grade_row` idiom**
rather than hand-building `Workbook()` calls inline — this keeps it consistent with the existing
suite's synthetic-workbook convention.

**Core assertion pattern for a fail-closed case** (`tests/grades/test_parser.py:99-113`,
the blank-bucket-count case — the direct template for an OQ-04 fixture):
```python
def test_blank_bucket_count_fails_closed(tmp_path: Path) -> None:
    workbook_path = tmp_path / "blank_bucket.xlsx"
    _write_workbook(
        workbook_path,
        [_grade_row("MAC-1105 -001-C (89033)", a=2, b=None, w=1, total=3)],
    )

    with pytest.raises(GradeWorkbookValidationError) as exc_info:
        parse_grade_workbook(workbook_path)

    message = str(exc_info.value)
    assert "row 2" in message
    assert "B" in message
    assert "unverified" in message.lower()
    assert "suppressed the value" not in message.lower()
```

**What the fixture is proving, concretely:** `src/easy_a/grades/parser.py:277-282`
(`_blank_count_cell_message`) intentionally raises rather than assuming blank means zero:
```python
def _blank_count_cell_message(row_number: int, column_name: str) -> str:
    return (
        f"{column_name} is blank at row {row_number}; blank count-cell semantics are "
        "unverified (cannot distinguish zero from unavailable or suppressed) and are "
        "rejected rather than assumed."
    )
```
A new OQ-04 fixture test should assert this same fail-closed message shape against the *real*
export's actual blank-cell row shape (column position, surrounding hierarchy/total rows if the real
export's layout differs from the synthetic one) — not weaken or bypass this rejection (explicitly
flagged as an anti-pattern in RESEARCH.md `## Anti-Patterns to Avoid`).

**Error handling pattern:** identical to the analog — `pytest.raises(GradeWorkbookValidationError)`,
asserting on the exception's `str(...)` message content, never on a return value (the parser fails
closed, it does not return a sentinel).

**Test runner command** (matches existing convention, `pyproject.toml` `testpaths = ["tests"]`):
```bash
uv run pytest tests/grades/test_parser.py tests/grades/test_ingest.py -q
```

---

## No Analog Found

None. The single conditional file above has an exact analog. No other new files are anticipated by
this phase.

## Shared Patterns

### Operator command sequence (not code — the actual "pattern" this phase reuses)
**Source:** `src/easy_a/refresh/cli.py` (full file), `src/easy_a/refresh/service.py:88-91`,
`src/easy_a/grades/cli.py`, `src/easy_a/analytics/cli.py`, `src/easy_a/quality/cli.py` — all
git-tracked, all read in full or by targeted excerpt this session.
**Apply to:** The entire phase's execution (there is no "apply to multiple files" here since there
are no new files — this is the cross-cutting operational pattern the plan's tasks should be built
around).

Two-step import (historical term, then live-term cache-only rebuild):
```bash
# Step 1 — import under the workbook's OWN real historical term.
uv run python scripts/refresh_data.py \
  --term <historical-Banner-term> \
  --grade-file <path-outside-git-or-under-ignored-data/> \
  --skip-catalog --skip-schedule --skip-syllabi

# Step 2 — rebuild the LIVE ranking term's cache (does not happen automatically in step 1).
uv run python scripts/refresh_data.py \
  --term 202701 \
  --skip-catalog --skip-schedule --skip-grades --skip-syllabi
```
Validation:
```bash
uv run python scripts/analyze_course.py --term 202701 --subject <SUBJ> --course <NUM>
uv run python scripts/check_data_quality.py --term 202701 --json
```

### Fail-closed input validation (already implemented — reference only, do not reimplement)
**Source:** `src/easy_a/grades/parser.py:277-282` (blank cell), `~line` bucket-sum check
(`test_invalid_total_fails` / "count sum ... does not equal Total Grades ...").
**Apply to:** Understanding *why* a sourced export row might reject during import — not something
new files need to reimplement.

### Atomic whole-workbook course resolution (already implemented — reference only)
**Source:** `src/easy_a/grades/ingest.py:156-179` (`_resolve_grade_course_ids`).
**Apply to:** Scoping the sourced export (pre-filter/split to the 10 current `courses` rows) before
calling either CLI — an operator/data-prep step, not a code change.

### "Lacking data" honesty (already implemented — reference only)
**Source:** `src/easy_a/quality/checks.py:452-462` (`no_historical_analytics` finding).
**Apply to:** Satisfying REQ-GRADES-01's "record courses still lacking data as lacking it" clause
via existing tooling, not a new report.

## Metadata

**Analog search scope:** `src/easy_a/grades/`, `src/easy_a/refresh/`, `src/easy_a/quality/`,
`src/easy_a/analytics/`, `tests/grades/`, `scripts/*.py` — all confirmed git-tracked via
`git ls-files`; no gitignored mirror paths encountered.
**Files scanned:** `src/easy_a/grades/parser.py`, `src/easy_a/grades/ingest.py`,
`src/easy_a/grades/cli.py`, `src/easy_a/refresh/cli.py`, `src/easy_a/refresh/service.py`,
`src/easy_a/quality/checks.py` (targeted excerpt), `tests/grades/test_parser.py` (full),
`tests/grades/test_ingest.py` (full), all six `scripts/*.py` stubs referenced by RESEARCH.md,
`.gitignore`.
**Pattern extraction date:** 2026-09-21
