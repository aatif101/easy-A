---
phase: 10-professor-level-grades
reviewed: 2026-10-01T23:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - .gitignore
  - README.md
  - docs/runbooks/historical-instructor-backfill.md
  - docs/runbooks/hosted-beta-operations.md
  - scripts/backfill_historical_sections.py
  - scripts/measure_instructor_pairs.py
  - scripts/report_ranking_diff.py
  - src/easy_a/analytics/pair_coverage.py
  - src/easy_a/analytics/queries.py
  - src/easy_a/analytics/scoring.py
  - src/easy_a/common/section_types.py
  - src/easy_a/rankings/cache.py
  - src/easy_a/rankings/diff.py
  - src/easy_a/rankings/models.py
  - src/easy_a/rankings/service.py
  - src/easy_a/schedule/backfill.py
  - src/easy_a/schedule/backfill_cli.py
  - src/easy_a/schedule/client.py
  - src/easy_a/schedule/normalize.py
  - src/easy_a/sync/fetch.py
  - src/easy_a/sync/parse_diagnostics.py
  - web/src/components/InstructorBreakdown.tsx
  - web/src/components/RankingDetails.tsx
  - web/src/fixtures/rankings.ts
  - web/src/types/rankings.ts
  - web/src/utils/rankings.ts
  - web/src/components/InstructorBreakdown.test.tsx
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-10-01
**Depth:** standard
**Files Reviewed:** 27 (test files were executed, not line-reviewed, except where cited)
**Status:** issues_found

## Summary

Reviewed the Phase 10 source at merge commit bcf1dbb (the checkout at `0cd7068` has identical source): the D-24 retune and lab rule, `build_instructor_breakdown` and the per-course versus whole-term parity, the backfill module and CLI, the unterminated-anchor repair and parse diagnostics, the diff and tolerance logic, the read-only scripts, and the React breakdown component. The Python and web test suites for the touched areas pass (`pytest tests/analytics tests/rankings tests/schedule tests/sync`, `vitest run`: 118 passed). `ruff check` is clean. `mypy` reports 4 pre-existing errors in files outside this phase (`benchmark_rankings_search.py`, `measure_term_build.py`).

The core scoring and breakdown code holds up. I traced it and found no defects in these areas:

- **Course-level scores.** They are untouched by D-24, because `instructor_prior_strength` applies only when `score_source is ScoreSource.instructor_course`.
- **Breakdown parity.** The per-course path (`_fetch_course_instructor_observations`) and the whole-term path (`_TermGradeEvidence.instructor_observations`) use the same join, lab exclusion, name filtering and course attribution. The gating, row selection, collapse rule and ordering `(not is_current, -effective_n, name)` are identical on both paths. The only difference is summation order, which the tolerance covers.
- **Anchor repair.** I ran it on synthetic 10 MB inputs (`<a ` repeated 2M times, `</a ` repeated 2M times, a 10 MB run with no `<`, a mixed input). The worst case was 0.33 s, so it is linear with no ReDoS. It is idempotent, leaves well-formed anchors, `<abbr>` and `<address>` untouched, and the lost-rows guard condition is unchanged.
- **Diff tolerance.** `float_differs` is written as `not abs(new - old) <= tol`, so NaN counts as a difference and the comparison is symmetric. Source, label, `effective_n` and CRN identity stay exact.
- **Apply ordering.** The sweep lock (`pg_try_advisory_xact_lock`) is the first statement of the apply transaction, taken after the slow USF fetches, and the transaction commits once.
- **Rollback.** Children are deleted before sections. Eligibility excludes any section with a seat snapshot, a syllabus or a non-backfill instructor row. The term allow-list is applied in both the select and the delete.

No Critical issues. The five Warnings are, in order:

- A user-visible false statement in the instructor panel.
- Database error text leaking host, IP and role name into stdout and the report file, despite the "no hostnames" claim.
- A vacuous safety gate in `--apply` when `--rebuild-term` is wrong.
- Unguarded `--report-json` handling.
- Gating scripts that mask any `SQLAlchemyError` as "NOT MEASURED".

Documented tradeoffs from the GAP notes are not re-reported. These include the parse-stage subject/course abort, the 1 ULP cache noise, the all-placeholder time change shared with the live sync, and `pairs_match_reference` unmet at D-04. Where a docstring overstates one of them, it is listed as Info.

## Warnings

### WR-01: Instructor panel states "No instructor-level grade history is recorded" while also listing instructors with history

**File:** `web/src/components/InstructorBreakdown.tsx:135,157-158,187-193` (cause in `src/easy_a/analytics/queries.py:160-173`)
**Issue:** `isEmpty = !named && breakdown.instructors.length === 0` ignores `other_instructor_count`. When the section is Staff, blank or ambiguous, and every instructor with history on the course is under the 15-grade collapse cutoff, the backend returns `status="ready"`, `instructors=[]` and `other_instructor_count=N`. I confirmed this by calling `build_instructor_breakdown` with two instructors at 5 and 6 grades and `current_instructor=None`:
```
status=ready instructors=() other_instructor_count=2
```
The UI then renders the dashed note "No instructor-level grade history is recorded for this course." directly above "2 other instructors with under 15 grades each". The first sentence is false, because history is recorded and only collapsed. This breaks the project's core promise that the product does not state evidence that does not exist. The UI-SPEC copy is written for "zero qualifying instructors", but it asserts absence of history, which is wrong in this state. No test covers `!named && instructors=[] && other_instructor_count>0`; the existing empty-state test uses `status: "no_instructor_history"` with `other_instructor_count: 0`.
**Fix:** Do not use the "no history recorded" copy when `other_instructor_count > 0`. Either gate on both conditions, or use different wording:
```tsx
const isEmpty = !named && breakdown.instructors.length === 0 && breakdown.other_instructor_count === 0;
...
// when !named && instructors.length === 0 && othersCount > 0, render only the Others line
// ("N other instructors with under 15 grades each") under the "Historically taught by" heading.
```
Add a test for this state.

### WR-02: Database error text leaks the database host, IP and role name into stdout and the report file

**File:** `src/easy_a/schedule/backfill_cli.py:396-398` (also `:520`, `:608`, `:836`, `:1071-1074`)
**Issue:** `_failure("database", detail=str(exc))` passes SQLAlchemy and psycopg error text through `_scrub`, which only removes `scheme://...` strings and truncates to 200 characters. A psycopg connection or auth error names the server hostname, IP, port and role. I simulated one:
```
'(builtins.Exception) connection to server at "aws-0-us-east-1.pooler.supabase.com" (52.1.2.3), port 6543 failed: FATAL: password authentication failed for user "postgres.abcdefghijklmnop"\n(Background '
```
This text survives `_scrub` and is printed to stdout and written to `--report-json`. The Supabase role name embeds the project ref, which maps to the project URL. This contradicts the module docstring ("no URL (request or database) is ever printed"), the runbook ("no URLs, no instructor names") and `10-ROLLOUT-EVIDENCE.md` ("No ... hostnames or credentials appear"). The same text, up to 200 characters of the statement and parameters, can also carry row data for `IntegrityError`s. For comparison, the sibling scripts print no error text at all.
**Fix:** For `SQLAlchemyError` (and for `OSError`), report only the exception class plus a fixed vocabulary:
```python
return _emit(args, _failure("database", detail=type(exc).__name__ + ((" (" + type(exc.orig).__name__ + ")") if getattr(exc, "orig", None) else "")), EXIT_FAILED)
```
Keep `_scrub` for httpx and parse errors only, and add a test that a simulated `OperationalError` containing a hostname does not appear in the output.

### WR-03: `--apply` safety gate is vacuous when `--rebuild-term` is a nonexistent or wrong term

**File:** `src/easy_a/schedule/backfill_cli.py:154-163` (`_live_term`), `:579`, `:594-600`, `:743-749`
**Issue:** `_live_term` only checks "six digits and not historical". In `--apply`, `stored_score_rows(session, args.rebuild_term)` is read before the writes and `refresh_section_rankings` is run for that term afterwards. For a typo such as `202710` (or any term with no cache rows), `stored_before` is `{}`, the rebuild writes 0 rows (`rows_rebuilt=0`), and `diff_score_rows({}, {})` yields `course_level_invariant=True`. The transaction commits. The T-10-19 guarantee that the cache is rebuilt in the same transaction and the course-level invariant is checked does not hold; the backfill data is committed with the real term's cache stale. The worker only rebuilds on a changed sweep, so the stale scores can persist. Only the optional `--expect-inserted` check remains. The same applies to `--rebuild-only` and `--rollback`, which would no-op "successfully".
**Fix:** In `_run` and `_run_undo`, fail before any write when the rebuild term has no stored cache rows:
```python
if not stored_before:
    session.rollback()
    return _emit(args, _failure("rebuild_term_empty", term=args.rebuild_term), EXIT_FAILED)
```
Alternatively, add `rows_rebuilt == 0 or total_before == 0` to `Applied.gate_failures` for gated applies.

### WR-04: `--report-json` is written unguarded after the commit, with no path rule, no atomic write and no OSError handling

**File:** `src/easy_a/schedule/backfill_cli.py:1061-1075`
**Issue:** `_emit` prints the report and then calls `args.report_json.write_text(...)`.
- For `--apply`, this happens after `session.commit()`. A missing parent directory, a read-only path or a full disk raises an uncaught `OSError`, so the operator sees a traceback and exit 1 for a run that committed (`written: true` was only on the already-printed stdout line). The runbook says exit 1 means "Nothing was written".
- The file is a non-atomic `write_text`. A partial file is left on interruption, while the two read-only scripts in this same phase use a `mkstemp` + `os.replace` helper.
- Unlike `--save-responses`, `--save-failed-response` and `--from-saved`, `--report-json` goes through no `_local_only_path` check, so nothing stops an in-repo, tracked path. The runbook instructs "Pick a directory outside the repository for the report files. Never commit them", yet `10-APPLY-REPORT.json` and `10-WHATIF-DIFF.json` (about 430 KB each, per-CRN changes) are tracked in git.
**Fix:** Write the report file before the final commit decision, or wrap the write:
```python
try:
    _write_atomic(args.report_json, text)
except OSError as exc:
    print(json.dumps({"mode": mode, "report_json_error": type(exc).__name__}), file=sys.stderr)
    # keep the original exit code; the run's outcome must not change because of a report-file problem
```
Share the existing `_write_atomic` helper rather than copying it again. Either enforce the "outside the repo" rule for `--report-json` or correct the runbook to say that committing the derived (CRN and number only) reports is allowed.

### WR-05: Gating scripts report every `SQLAlchemyError` as "NOT MEASURED (database unreachable)" with no diagnostic, and config errors exit 1

**File:** `scripts/report_ranking_diff.py:147-155`, `scripts/measure_instructor_pairs.py:114-129`
**Issue:** The `except SQLAlchemyError` block wraps the whole measurement and prints only the envelope and `NOT MEASURED`, exit 3. A `ProgrammingError` (missing column or table after a schema or code mismatch), a statement-timeout `OperationalError`, or a failed `SET TRANSACTION` on a pooler is therefore reported as "database unreachable" with no class or message, so a defect in the measurement looks like an outage. Separately, `get_engine()` sits outside the `try`, so a missing `DATABASE_URL` (`DatabaseConfigError`) or any non-SQLAlchemy exception (for example a `KeyError`) exits via an uncaught traceback with code 1. In `report_ranking_diff.py`, exit 1 documents "any difference beyond tolerance", so a crash is indistinguishable from a real diff by exit code.
**Fix:** Distinguish connection failures from the rest, and emit the exception class:
```python
except (OperationalError, InterfaceError) as exc:   # connectivity
    print(json.dumps({**_not_measured(...), "error_kind": type(exc).__name__})); return 3
```
Let other `SQLAlchemyError`s propagate (or map them to a distinct exit code, for example 4, with `error_kind`). Move `get_engine()` inside the handled region and map `DatabaseConfigError` to 3.

## Info

### IN-01: `_redact` runs on serialized JSON and can corrupt the output

**File:** `src/easy_a/schedule/backfill_cli.py:1057-1074`
**Issue:** `_URL_RE` is `[a-z][a-z0-9+.-]*://\S*`, applied to the already-serialized JSON text. `\S*` swallows the closing quote and brace. I reproduced this with a campus label key containing `http://x.y/z`:
```
{"non_tampa_by_label": {"Campus [redacted-url] 3}, "status": "ok"}   -> json.loads fails
```
USF-supplied strings reach the report as dict keys (`rows_by_campus`, `non_tampa_by_label`, `unknown_campus_labels`) and as histogram keys. Probability is low, and the failure mode is an unparseable report rather than a leak.
**Fix:** Redact string values and keys before `json.dumps` (a recursive scrub over the report dict), not the serialized text.

### IN-02: Docstrings overstate what the pre-normalisation gate and diagnostics guarantee

**File:** `src/easy_a/schedule/backfill_cli.py:38-39,48-49`, `src/easy_a/schedule/backfill.py:94-98`, `docs/runbooks/historical-instructor-backfill.md` (Purpose, 1c)
**Issue:** The text says "a row on an excluded campus can never abort a run" and the report carries no cell text. `10-GAP-06-PARSE-ORDER-TBA.md` correctly records that a parse-stage error from `parse_schedule_html` still aborts a term on any campus. In that case `ScheduleParseError("Could not parse subject/course value {value!r}.")` (`schedule/parser.py:139`) goes through `str(exc)` into the report's `error` field. That echoes the raw cell (subject/course text, up to 200 characters) and contradicts "still without any cell text". The data exposed is a course-code cell, not an instructor name, so severity is low. This is a doc and comment accuracy problem, not a new defect.
**Fix:** Qualify the docstrings with "normalisation-stage". Optionally replace the parser message in the CLI with `error_kind: parse` plus the shape fingerprint.

### IN-03: Float noise inflates `abs_delta` and `abs_delta_buckets`, and rank is computed from raw floats

**File:** `src/easy_a/rankings/diff.py:294-300,121,244-246,384-396`
**Issue:**
- Every common CRN's `abs(delta)` is appended to `abs_deltas`, including within-tolerance noise. A noise delta of 5e-15 lands in the `(0,0.25]` bucket rather than `"0"`, and `abs_delta.max` reports it, while `changed == 0`. On the live 202701 check this means about 3,670 sections appear in `(0,0.25]` with `changed: 0`. The runbook describes the buckets as "how far scores moved".
- The tolerance does not apply to `rank_rows`, which orders by raw `-easiness_score`. Two different courses with mathematically equal but not bit-equal scores can swap rank under 1 ULP noise, and `identical` then fails. `GAP-01` documents that rank movement must still fail, so this is by design, but it leaves a residual failure mode that the tolerance was meant to remove.
**Fix:** Count a delta in the `"0"` bucket when `not float_differs(...)`, or compute the bucket from `changed_fields`. Optionally round scores to about 1e-9 before ranking, or document the residual hazard in the runbook.

### IN-04: `measure_instructor_pairs` groups names differently from the scoring code, so it cannot cross-check the grouping

**File:** `src/easy_a/analytics/pair_coverage.py:117-119,196-200`
**Issue:** The module is described as an independent cross-check of the scoring join. It keys instructors by whitespace-cleaned, case-folded name, while `queries.py` keys by the raw `name_raw`. Case variants such as `SMITH, J` and `Smith, J` are one pair here and two in scoring. Names are whitespace-cleaned at parse time, so the current effect is limited to case, but any divergence between the two would not be detected.
**Fix:** Note the difference in the module docstring, or key by raw `name_raw` as the scorer does.

### IN-05: Unbounded `IN (...)` lists built from grade-row-sized lists

**File:** `src/easy_a/analytics/queries.py:526-535,743-744,899-907`, `src/easy_a/analytics/pair_coverage.py:189-193`
**Issue:** `_TermGradeEvidence.load`, `_fetch_course_grade_observations(None)` and `measure_instructor_pairs` pass one bind parameter per grade row (a list, so duplicates are included) to `section_id.in_(...)`. The backfill code is careful to chunk at 500. At the current 8,662 grade rows this is about 13% of psycopg3's 65,535 server-side parameter limit (the repo's pooler configuration uses psycopg3), but it grows with each imported term and fails only on PostgreSQL, since SQLite's limit is higher.
**Fix:** De-duplicate (`set`) and chunk, or join through a subquery (`SectionInstructor.section_id.in_(select(Section.id)...)`).

### IN-06: The repair can move visible note text into the tag, and the helper scripts duplicate code

**File:** `src/easy_a/sync/fetch.py:43-44,76-85`; `scripts/report_ranking_diff.py:78-90,119-140`, `scripts/measure_instructor_pairs.py:56-104`
**Issue:**
- `_UNTERMINATED_START_A_RE` closes `<a ...` at the next `<`, wherever that is. `<a href="x" Click here</a>` becomes `<a href="x" Click here></a>`, so "Click here" becomes attribute junk. Likewise an attribute containing a literal `<` is split. The docstring's "never removes ... text" is true byte-wise but not semantically. The affected cell is a note cell, which feeds policy-signal extraction. This is a narrow, accepted heuristic (the GAP-03 incident is the targeted shape), but the semantic caveat is not documented.
- `_environment_label`, `_write_atomic`, `_term_code` and the Supabase host check are copied across both scripts (and into `benchmark_rankings_search.py`). Also, `_ResponseSaver` opens with `os.open(..., O_TRUNC)` without `O_NOFOLLOW`, so a pre-planted symlink at `DIR/<term>.html` is followed (local, operator-only).
**Fix:** Add a sentence to the `repair_unterminated_anchors` docstring. Move the duplicated helpers into a shared `scripts/_common.py` or `easy_a.common`. Add `os.O_NOFOLLOW` in `_ResponseSaver`.

### IN-07: Exit code 2 is overloaded and the operations runbook says to retry on it

**File:** `src/easy_a/schedule/backfill_cli.py:8-10,108-110,347-348`, `docs/runbooks/hosted-beta-operations.md` (section 14)
**Issue:** Exit 2 means both an argparse usage error and "sweep lock busy". The CLI docstring and the backfill runbook disambiguate via `status: busy` in stdout, but section 14 of the hosted-beta runbook says to "retry on exit 2". An operator or wrapper script that keys on the exit code alone will retry a usage error indefinitely. It is harmless, since nothing is written, but it is easy to avoid.
**Fix:** Use a distinct code (for example 75 or 4) for `EXIT_BUSY`, or word the runbook as "exit 2 with `status: busy`".

---

_Reviewed: 2026-10-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
