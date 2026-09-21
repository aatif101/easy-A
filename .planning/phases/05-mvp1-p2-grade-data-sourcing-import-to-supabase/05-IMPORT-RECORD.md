# Phase 5-1 Tracer Import Record

## Source and scope

- Source: approved USF InfoCenter Grade Distribution (SGDIS) aggregate report
- Report ID: `863582`
- Retrieved: 2026-09-21 13:50 EDT
- Confirmed historical Banner term: `202408` (Fall 2024)
- Tracer course: `MAC 1105`
- Report scope: Tampa Campus; College of Arts and Sciences; Mathematics & Statistics; MAC 1105
- Destination: intended hosted Supabase transaction pooler, verified by hostname class and port `6543` without recording credentials
- Raw export retention: local operator filesystem only; no workbook or row-level derivative is tracked in Git

## Import result

| Course | Source term | Insert ingest run | Parsed rows | Source `Total Grades` sum | DB raw `total_grade_count` | Effective N | Score source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| MAC 1105 | 202408 | 1 | 6 | 1,138 | 1,138 | 1,102.0 | course |

The exact raw-count contract passes: the database `total_grade_count` equals the source workbook aggregate. `Effective N` is lower because it is an analytics evidence measure; it is not substituted for the raw integrity total. The Bayesian-smoothed easiness score is likewise not used for source reconciliation.

## Execution and validation notes

- Pre-import state: each of the five Spring 2027 MAC 1105 sections reported `Source=global`, `Effective N=0.0`.
- The grade stage committed ingest run 1 with 6 seen, 6 inserted, 0 updated, and 0 failed.
- Hosted Supabase was at Alembic revision `0002_create_section_syllabus_tables`; the checked-in `0003_create_section_rankings` migration was applied before cache rebuilding.
- A repeat import produced successful ingest run 2 with 6 seen, 0 inserted, 0 updated, and 0 failed, confirming the same export did not double-count rows.
- The separate `202701` cache-only refresh completed for 10 courses and 132 sections with 0 quality errors.
- Post-import `analyze_course.py` reported `Source=course`, `Effective N=1102.0`, and medium confidence for all five live MAC 1105 sections.
- Post-import `check_data_quality.py --term 202701 --json` reported 0 errors, 112 warnings, and 112 informational findings. It reported no `unattributed_grade_row` or `grade_total_mismatch` finding.
- The historical `202408` refresh reports six quality errors because no 202408 schedule sections are loaded. The grade rows remain valid and are attributed directly to the canonical course, which is the supported historical analytics path.

No CRN-level grade buckets or other raw workbook rows are included in this record.
