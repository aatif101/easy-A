# 10-GAP-02: parse-guard diagnostics (offline)

Decision: "revise-diagnostics". The five-term dry run (10-07 Task 2) failed at 202505 with `Parsed 2174 rows from 2175 data rows; refusing a response that silently lost rows.` and the response was not kept, so the dropped row could not be identified. This gap makes the failure diagnosable. It makes no USF request and no hosted-database connection, and it does not change what the guard accepts or rejects.

## What changed

- `src/easy_a/sync/parse_diagnostics.py` (new): `LostRowsError(ScheduleParseError)` carrying `diagnostics`; `build_lost_rows_diagnostics`. Runs only on the failure path. It re-parses, one block at a time, only the rows of chunks whose data-row and parsed counts differ.
- `src/easy_a/sync/fetch.py`: `parse_whole_term` records per-chunk counts as bookkeeping (never feeding the guard decision) and raises `LostRowsError` from the unchanged condition `len(parsed) != data_row_count`. The message keeps its original text and gains a short suffix (`expected=… parsed=… Suspect data rows (0-based): #N c/24 cells (fingerprint)`), so the live sweep's stored `error_detail` also names the row. `fetch_whole_term` gains an optional `on_parse_failure(html)` hook, unset by the live sweep.
- `src/easy_a/schedule/backfill_cli.py`: failure report gains `parse_diagnostics`; new `--save-failed-response PATH` (dry run and apply only, default off, rejected for rollback and rebuild-only) saves the raw response, mode 0600, only when a term fails the parse guard. A path inside the repo is accepted only under `.planning/phases/10-professor-level-grades/failed-responses/`; any other tracked path or a directory is refused with exit 2 before any request. A save error is reported and never masks the parse failure.
- `.gitignore`: ignores `.planning/phases/10-professor-level-grades/failed-responses/`.
- `docs/runbooks/historical-instructor-backfill.md`: new section 1a, "When a term fails the parse guard".

Per suspect row (capped at 10; mismatched chunks capped at 10; totals always exact): 0-based `position` among data rows, `block_index` among all `<tr>` blocks, `cell_count`, `td_tag_count`, `nested_table`, `colspan_cells`, `isolated_rows`, a `cell_shape` string (`.` empty, `d` digits, `a` other), a digits-only `crn` (else a shape label), and a fixed-vocabulary `fingerprint`. No cell text, URLs, names or raw HTML are ever reported.

One scope note: the save also fires for the other parse-guard failures (missing header row, unparseable subject/course cell), not only the lost-rows count, since they are the same fail-closed family and are equally undiagnosable without the page. Other failure kinds (HTTP, timeout, response type) never save.

## Offline findings: row shapes against the parser

Synthetic variants of the fixture row shape, run through `parse_schedule_html` (whole page) and `parse_whole_term` (chunked guard):

| Shape | Whole-page parser | Chunked guard | Diagnostic reading |
|---|---|---|---|
| 23 cells | skips row | rejects (N-1 of N) | `missing FEES` |
| 25 cells | skips row | rejects | `1 extra cells` |
| 1-cell `colspan` placeholder row (cancelled/banner) | skips row | rejects (N of N+1) | `1 spanning cells, crn absent` |
| Row missing `</tr>` | parses both rows | rejects (more parsed than counted) | `block holds 2 rows` |
| Nested table inside a cell | **parses the row** | **rejects (N-1 of N)** | `nested table` |
| `</tr>` inside an HTML comment, row attributes | parses | accepts | none |

Findings:

1. **Latent chunker/parser divergence (plausible bug, no evidence it occurs in USF data).** `_ROW_RE` ends a row block at the first `</tr>`, so a data row containing a nested table is cut short and dropped by the chunker, while `parse_schedule_html` on the whole page parses that row. Reported with a strict `xfail` test (`test_a_row_with_a_nested_table_parses_the_same_whole_page_and_chunked`); the suite stays green and the test flips to a failure the day the divergence is fixed, forcing the marker to be removed. **Not fixed:** it would change which responses the live sync and backfill accept, and nothing shows 202505 contains a nested table.
2. **Short, extra-cell and placeholder rows are rejected by design.** The guard counts every `<tr>` with a `<td>`; the parser silently skips any row whose direct cell count is not 24. A legitimate non-data row with a `<td>` (for example a one-cell cancelled or summary banner) would trip the guard for the whole term. This is the original, intended fail-closed behaviour and is unchanged. Whether USF emits such a row in 202505 is the open question the diagnostics will answer.
3. The existing fixtures (`schedule_current`, `schedule_ambiguous`, `schedule_historical_202408_89033`, `schedule_not_found`) contain only 24-cell rows and no placeholder or nested shapes, so they give no evidence for the 202505 failure.

## Guard strictness

Pinned by tests: five rejected shapes (short, extra cell, placeholder row, unclosed row, nested table) still raise `ScheduleParseError` with `Parsed N rows from M data rows`; three accepted shapes (clean, row attributes, comment containing `</tr>`) still parse; a missing header is still a plain `ScheduleParseError` with no diagnostics; a failure inside the diagnostics never replaces the guard error. No behaviour change in accept/reject.

## Tests

- `tests/sync/test_parse_diagnostics.py` (new): positions across chunks, block index versus position, fingerprints (short, extra, placeholder, nested, unclosed row, non-numeric CRN), caps (10 rows, 10 chunks, exact totals, bounded shape), no URL/name/HTML leakage, guard accept/reject sets, diagnostics failure isolation, the `on_parse_failure` hook (called only on a parse failure, error unchanged), and the xfail finding.
- `tests/schedule/test_backfill.py`: CLI report carries sanitized diagnostics and no leakage (stdout and `--report-json`); `--save-failed-response` writes only on a parse failure (exact decoded text, mode 0600), writes nothing on success, without the option, or for an HTTP failure; a save error never masks the parse failure; tracked repo paths and directories are refused (exit 2); the ignored directory and outside paths are accepted; refused for rollback; `git check-ignore` confirms the directory is ignored and untracked.

Gates: `uv run pytest -q` 903 passed, 4 skipped, 1 xfailed; `uv run ruff check .` and `uv run mypy src` clean.

## Next step for the operator

To diagnose 202505, rerun `--terms 202505 --dry-run --save-failed-response .planning/phases/10-professor-level-grades/failed-responses/202505.html` (one request, after an explicit go-ahead; runbook section 1a explains how to read the output). This note does not authorise that request.
