# Phase 5 Grade Import Coverage Record

## Source and scope

- Source: approved USF InfoCenter Grade Distribution (SGDIS) aggregate reports
- Confirmed historical Banner term: `202408` (Fall 2024)
- Scope: Tampa Campus, one exact course per report, covering the 10 currently ingested courses
- Retrieved: 2026-09-21 between 13:50 and 15:17 EDT
- Destination: intended hosted Supabase transaction pooler, verified by hostname class and port `6543` without recording credentials
- Raw export retention: local operator filesystem only; no workbook or row-level derivative is tracked in Git

## All-course coverage

| Course | SGDIS report | Source term | Insert ingest run | Parsed rows | Source `Total Grades` sum | DB raw `total_grade_count` | Effective N | Score source | Status |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| ACG 2021 | 863600 | 202408 | 3 | 14 | 554 | 554 | 496.0 | course | imported; exact raw match |
| ACG 2071 | 863601 | 202408 | 4 | 12 | 482 | 482 | 464.0 | course | imported; exact raw match |
| AMH 2020 | 863593 | 202408 | 5 | 20 | 1,037 | 1,037 | 1,011.0 | course | imported; exact raw match |
| ANT 2000 | 863594 | 202408 | 6 | 5 | 227 | 227 | 227.0 | course | imported; exact raw match |
| BSC 1005 | 863595 | 202408 | 7 | 2 | 500 | 500 | 494.0 | course | imported; exact raw match |
| ECO 2013 | 863596 | 202408 | 8 | 3 | 652 | 652 | 636.0 | course | imported; exact raw match |
| ENC 1101 | 863597 | 202408 | 9 | 89 | 1,715 | 1,715 | 1,680.0 | course | imported; exact raw match |
| MAC 1105 | 863582 | 202408 | 1 | 6 | 1,138 | 1,138 | 1,102.0 | course | tracer; exact raw match |
| MAC 2311 | 863598 | 202408 | 10 | 9 | 490 | 490 | 419.0 | course | imported; exact raw match |
| PSY 2012 | 863599 | 202408 | 11 | 19 | 749 | 749 | 733.0 | course | imported; exact raw match |

All 10 currently ingested courses are covered by a bounded source report. No course is omitted, and no course remains at `effective_n=0` / `score_source=global`. If a later coverage run lacks a source for any listed course, its row must remain in this table and explicitly say `effective_n=0`, `score_source=global`, and `still lacking historical grade data` rather than being removed.

The exact raw-count contract passes for every course: each database `total_grade_count` equals its source workbook's `Total Grades` aggregate. `Effective N` and the Bayesian-smoothed easiness score are derived analytics values and are not substituted for the raw integrity total.

## Execution and validation

- The nine scale-out workbooks were imported separately under their confirmed historical term. Together with the tracer, hosted Supabase now holds 179 Fall 2024 grade-distribution rows for the 10 courses.
- A single separate `202701` cache-only refresh completed after all historical imports: 10 courses, 132 sections, 0 quality errors, and 0 quality warnings.
- `analyze_course.py` was run for every course. Every live section reported `Source=course` and `Effective N` greater than zero.
- `check_data_quality.py --term 202701 --json` reported 0 errors, 0 warnings, and 0 informational findings. Counts for `no_historical_analytics`, `unattributed_grade_row`, and `grade_total_mismatch` were all zero.
- Re-importing the ACG 2021 workbook created successful ingest run 12 with 14 seen, 0 inserted, 0 updated, and 0 failed. Its row count and raw total remained 14 and 554, confirming idempotency.
- Historical-term refresh commands report quality errors because no Fall 2024 schedule sections are loaded. The grade rows are valid and attributed directly to canonical `course_id`; the Spring 2027 live-term quality gate is clean.

## OQ-04 blank-cell disposition

None of the 10 real Fall 2024 exports contained a blank canonical grade-count or `Total Grades` cell among the 179 imported section rows. The existing parser accepted every workbook with all bucket sums equal to its row total.

Therefore no `tests/grades/test_parser_real_export_shape.py` fixture is created. OQ-04 remains open: this source set does not establish what a future blank means. The parser's fail-closed policy remains unchanged, and any future blank must be escalated rather than coerced to zero.

No CRN-level grade buckets or other raw workbook rows are included in this record.
