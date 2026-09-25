# Verified sketch content

Snapshot captured **2026-09-25T08:20:27.727025Z** from hosted Supabase and the local production API.
This is a selected design sample, not a campus-wide listing or a current registration feed.
Every sampled course includes its complete stored Spring 2027 section list.

| Course | Recorded As | Recorded A–F grades | Historical sections | Observed history span | Spring 2027 sections |
|---|---:|---:|---:|---|---:|
| MAC 1105 | 1,534 | 3,200 | 23 | Fall 2024–Spring 2026 | 5 |
| ENC 1101 | 3,482 | 4,932 | 267 | Fall 2024–Spring 2026 | 41 |
| PSY 2012 | 1,809 | 2,793 | 63 | Fall 2024–Spring 2026 | 10 |
| BSC 1005 | 881 | 1,864 | 9 | Fall 2024–Spring 2026 | 2 |
| AMH 2020 | 2,352 | 4,049 | 84 | Fall 2024–Spring 2026 | 19 |
| MVJ 1111 | 4 | 5 | 1 | Fall 2025 | 1 |
| CAI 1000 | unavailable | unavailable | 0 imported rows | unavailable | 1 |
| THE 3111 | 2 | 4 | 1 | Spring 2026 | 1 |

Source: `usf_infocenter_grade_distribution_xlsx`, displayed as **USF InfoCenter**. Aggregation
includes only stored rows before target term `202701`, for the exact subject/number across
catalog identities. A history span states the earliest/latest observed term, not complete
coverage of every section or intervening term. It makes no instructor-specific assertion.

MAC 1105 counts: A=1,534; the denominator is A+B+C+D+F=3,200. Displayed 48% is the rounded
observed A share. The unchanged calculated score is 7.95482293129276 (displayed 8.0/10), not
an A percentage. Its withdrawal denominator is all 3,344 recorded outcomes, with 142 withdrawals.
The sketch exposes non-letter outcomes separately rather than hiding them in the A–F denominator.

`snapshot.json` stores course aggregates, source names/hashes, import timestamps, metadata,
and public schedule facts. `snapshot.js` contains the same data for offline browser use.
Neither contains raw historical grade rows or grade export files. The exporter:

1. Opens a repeatable-read, read-only database transaction.
2. Limits work to eight explicitly named courses and pre-Spring-2027 grade rows.
3. Fails if multiple source rows overlap a term/CRN, rather than summing them silently.
4. Reconciles letter counts, total outcomes, and historical section counts with existing API
   course-backed analytics. No new score calculation is performed.
5. Retrieves up to 100 sections per exact course, asserts the API total fits, and reconciles
   the complete CRN set with the database. There is no first-50-page grouping shortcut.
6. Preserves observed seat/schedule timestamps, instructor state, exact format labels, and
   quoted signal provenance. It performs no source crawl or database write.

CAI 1000 has no imported course rows; the UI shows no percentage or course score. Its fallback
source is retained in the data record for traceability but is never portrayed as course history.
MVJ 1111 and THE 3111 reuse the existing **low** confidence classification for “Limited history.”
There are no generated evidence examples or fabricated grade distributions.

Refresh deliberately, with the local API running against the same database as `DATABASE_URL`:

```sh
.venv/bin/python .planning/sketches/001-student-experience/export_snapshot.py
```

Refreshing changes the dated evidence. Re-review `DATA.md`, screenshots and acceptance findings
if new source data changes the sample. Do not quietly treat this frozen preview as live data.
