# Grade Distribution Import Runbook

Use this runbook to import an approved, aggregate USF InfoCenter SGDIS export and make its historical evidence visible in the live rankings cache. The raw export is operator-controlled source material: never commit it or a row-level derivative.

## Preconditions

- Confirm the export is an approved aggregate grade-distribution report, not student-level data.
- Record the report's actual Banner term. The workbook and filename are not trusted term metadata; pass the confirmed term explicitly with `--term`.
- Keep every `.xlsx`/`.xls` under the ignored `data/` tree or outside the repository. Verify `git status --short` does not list it and `git ls-files -- '*.xlsx' '*.xls'` prints nothing.
- Export `DATABASE_URL` for the intended hosted Supabase transaction pooler. Verify its host ends in `.pooler.supabase.com` and its port is `6543` without printing the URL, username, or password.
- Parse and inspect the workbook before importing. Every `(subject, course_number)` must resolve to a current `courses` row. Scope or split a broader export first: one unresolved course aborts the entire workbook atomically.
- Stop if any canonical grade-count cell is blank or suppressed. The parser deliberately fails closed because blank cannot safely be assumed to mean zero.

## 1. Import under the historical term

Run the orchestrated refresh with the export's confirmed historical Banner term:

```powershell
uv run python scripts/refresh_data.py `
  --term <HISTORICAL_BANNER_TERM> `
  --grade-file <PATH_TO_APPROVED_XLSX> `
  --skip-catalog --skip-schedule --skip-syllabi
```

`--grade-file` belongs to `scripts/refresh_data.py`. The standalone `scripts/ingest_grades.py` command instead takes `--file` and does not rebuild any rankings cache.

The importer is idempotent for the same `(term, CRN, source)`: a repeated export updates the existing row when its contents differ and does not double-count it. Preserve the command result and the corresponding successful `ingest_runs` identifier as provenance.

## 2. Rebuild the live rankings cache separately

The historical import only rebuilds the cache for the historical term passed above. Rebuild the live Spring 2027 cache in a separate invocation:

```powershell
uv run python scripts/refresh_data.py `
  --term 202701 `
  --skip-catalog --skip-schedule --skip-grades --skip-syllabi
```

Do not omit this pass; otherwise the imported history can remain invisible to the live search API.

## 3. Validate the imported course

```powershell
uv run python scripts/analyze_course.py `
  --term 202701 --subject <SUBJECT> --course <NUMBER>

uv run python scripts/check_data_quality.py --term 202701 --json
```

For a covered course, each live section must report `Source=course` and `Effective N` greater than zero. A genuinely uncovered course must remain the honest `Source=global`, `Effective N=0` fallback.

The data-quality report must contain zero errors and no `unattributed_grade_row` or `grade_total_mismatch` finding for the tracer course.

Finally, sum the source workbook's `Total Grades` values for the course and compare that exact integer with the database's raw `total_grade_count`. Do not compare the source total with `easiness_score`: the displayed score is intentionally Bayesian-smoothed, while `total_grade_count` is the raw integrity contract.

## 4. Record provenance without leaking raw rows

Record only per-course aggregates and provenance: subject/number, historical term, report identity or retrieval date, `ingest_run_id`, source total, database raw total, effective sample size, and score source. Do not copy CRN-level grade buckets or other raw workbook rows into Git.

If parsing, attribution, cache rebuilding, or validation fails, retain the explicit error and stop. Do not weaken blank-cell validation, bypass atomic course resolution, or manually patch derived rankings.
