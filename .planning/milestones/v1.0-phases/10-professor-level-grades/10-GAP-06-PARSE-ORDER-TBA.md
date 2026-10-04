# GAP-06: campus gate before normalisation, all-placeholder time cells, row quarantine, replay

Date: 2026-10-01. Task: the "fix-both" decision after dry run 3 failed at 202601 (`10-ROLLOUT-EVIDENCE.md`, "Five-term dry run 3"). **Offline only**: no USF request, no hosted database connection, no backfill CLI run against anything live, no push or deploy. Code and tests are committed on `phase-10-prof-grades`; the next step is a fourth dry run, which needs the user's go-ahead under D-22(e).

## The defect

`parse_whole_term` normalised every fetched row before the backfill's campus allow-list was applied, and `_parse_time_range` accepted a lone `TBA`/`ARR` but not a cell of two unscheduled components (`TBA TBA`). Two `Sarasota-Manatee` rows (a campus the backfill excludes) in the 202601 page therefore aborted the whole run before any report, guard or what-if existed.

## What changed

| Area | Change |
|------|--------|
| Gate before normalisation (backfill only) | `parse_whole_term(..., row_gate=...)` is an explicit, opt-in parameter, `None` by default. A row the gate rejects is never normalised; it comes back as a `SkippedRow` (CRN and campus only). The backfill passes `backfill.backfill_row_gate` (the existing allow-list `{Tampa, Off-campus - Tampa}`). `select_backfill_rows(..., skipped=, failures=)` counts skipped rows exactly as a normalised row on the same campus was counted: `fetched_rows`, `rows_by_campus`, `not_graded`, `non_tampa`, `non_tampa_by_label`, `unknown_campus_labels` and the unmatched-CRN guard. A test proves the whole `TermSelection` is `==` between "normalise everything, then select" and "gate first, then select" on a mixed-campus page. |
| Normaliser (SHARED) | `_parse_time_range`: a time cell with no clock range whose whitespace-separated tokens are ALL `TBA`/`ARR` (any case) is `(None, None)`, consistent with the existing multi-range rule. Everything else is untouched; see "Shared-code call-outs". |
| Quarantine (backfill only) | `parse_whole_term(..., quarantine_row_failures=True)` (default `False`): a row that is normalised and fails is collected as a `RowFailure` (0-based data-row `position`, `crn`, campus label, failing `field`, fixed-vocabulary `shape`) instead of raising, and parsing continues. The lost-rows guard is unchanged and runs first, over every row. |
| Guard | `_guard_failures` adds `row_normalisation_failures` when a term has any quarantined row. Dry run still computes the what-if and prints the full report, then exits 1; `--apply` has `can_write` false, refuses and writes nothing (not even an `ingest_runs` row). Error kind `guard`. Any allowed-campus row that cannot be read fails the run, graded or not, so strictness for data we would write is unchanged. |
| Report | Per term: `row_normalisation_failures` (full count), `row_failures` (capped at `ROW_FAILURE_REPORT_LIMIT = 10`; `position`, `campus`, `field`, `shape`) and `row_failures_omitted`. Quarantined rows count in `fetched_rows`, `rows_by_campus`, `campus_allowed_rows`, never in `to_write`, and are excluded from `matched_grade_rows`. No cell text, URL or name. |
| `--save-responses DIR` | Opt-in (default off; dry run and apply only). `fetch_whole_term(..., on_response=...)` hands each raw response to a saver as it arrives, before parsing: `DIR/<term>.html`, decoded text, mode `0600` (an existing file is `fchmod`-ed to `0600`; `--save-failed-response` got the same fix). Same path rules as `--save-failed-response` (outside the repo, or under the git-ignored `failed-responses/`; other in-repo paths exit 2 before any request). Pages that arrived before a later failure stay saved. A save error is reported (`saved: false`) and never stops the run. Report key `saved_responses`. |
| `--from-saved DIR` | Offline replay, dry run only. Reads `DIR/<term>.html` per `--terms`, runs the identical parse, gate, quarantine, selection, guards and what-if through `parse_saved_term` (no client parameter). `main` never builds a `StaffScheduleClient` or calls `client_factory` on this path; no sleep. Refused with exit 2 for `--apply`, `--rollback`, `--rebuild-only`, `--save-responses`, `--save-failed-response` or a missing directory. A requested term without a file fails closed (`saved_response_missing`, exit 1). `request` reads `{"source": "saved_responses", "requests_made": 0, ...}`. Database access is the same read-only, always-rolled-back what-if as a normal dry run. |
| Error type | `RowNormalizationError(ScheduleParseError)` in `normalize.py` carries `field` and `shape`; message text and base class are unchanged, so every existing `except ScheduleParseError` and the live sweep's `parse` classification behave identically. |

## Shared-code call-outs (affects the live sync)

1. **`schedule/normalize.py::_parse_time_range` is shared** by the live sweep (`sync/fetch.py` via `normalize_schedule_row`), the narrow-search ingest (`schedule/ingest.py`) and the resolver (`schedule/resolver.py`). **Behaviour change:** a time cell of several components that are all `TBA`/`ARR` (for example `TBA TBA`) used to raise `Invalid schedule time range` and now normalises to no start and no end. For the live sync this means a live section with such a cell is stored with no time instead of failing the whole sweep as `parse`. That is the intended consistency with the lone `TBA` and the multi-range rules, and a test (`test_a_placeholder_only_time_cell_no_longer_fails_the_live_sweep`) pins it. It is the only live-visible behaviour change in this gap.
2. **Every other time-cell shape is unchanged.** `tests/schedule/test_normalize_time.py` keeps a verbatim copy of the old function as an oracle and (a) lists the previously rejected non-all-placeholder shapes (a lone clock, `TBA 8:00am`, `8:00am TBA`, `TBA xyz`, `TBD`, `TBA TBD`, `TBA, TBA`, `TBA/TBA`, `TBA-TBA`, `TBA TBA 9`, `ARR?`, `N/A`, impossible clocks) and asserts each is still rejected with the unchanged message, and (b) exhaustively compares old and new over every 1 to 4 token combination of an 8-token vocabulary (4,680 cells): the only differences are the multi-component all-placeholder cells, and every one of those differs. `TBA 8:00am-9:00am` (one range next to a placeholder) was accepted as that range before and still is.
3. **`sync/fetch.py` is shared** (`parse_whole_term`, `fetch_whole_term`). The new parameters (`row_gate`, `quarantine_row_failures`, `on_response`) default to off and the live sweep passes none of them (`sweep.py` is not edited; a test records the exact kwargs of a real sweep's `fetch_whole_term` call). With no gate and no quarantine `parse_whole_term` runs the previous code path unchanged: `tuple(normalize_schedule_row(row) for row in parsed)`, so the live sync still normalises every row first and still fails on a bad row (tests: a bad row on an excluded campus still raises on the default path and still fails a real sweep with `error_kind` `parse`). `fetch_whole_term` now delegates its parse to a private `_parse_page` helper with identical behaviour (`on_parse_failure` semantics unchanged).
4. **Not touched:** `sync/sweep.py`, `sync/scope.py`, `sync/apply.py`, `schedule/client.py` (request campus, caps and timeouts), `common/campus.py`, the lost-rows guard, the anchor repair, the unmatched-fraction guard and its 2% default, scoring.

## Offline validation

Against the git-ignored saved pages only (`failed-responses/dry-run-3.html`, `failed-responses/202505.html`); never committed, copied or quoted. Counts only. The replay ran through the real CLI `main(... --dry-run --from-saved ...)` over an in-memory SQLite seeded in the session scratchpad (a grade row for every fetched CRN, a course row per course key), with no USF request and no hosted connection.

202601 (10,756,455 bytes):

| Measure | Value |
|---------|------:|
| data rows / parsed rows (lost-rows guard) | 9,969 / 9,969, passes |
| `Tampa` rows normalised | 6,703 |
| `Off-campus - Tampa` rows normalised | 1,958 |
| rows normalised in total (allowed campuses) | 8,661 |
| rows set aside before normalisation (`non_tampa`) | 1,308: `St. Petersburg` 646, `Off-campus - Sarasota-Manatee` 253, `Sarasota-Manatee` 195, `Off-campus - St. Petersburg` 175, `Off Campus Special Programs` 39 |
| the 2 `TBA TBA` rows (both `Sarasota-Manatee`, data-row positions 3226 and 3227) | set aside as `non_tampa`, never normalised |
| `row_normalisation_failures` | 0 |
| `unknown_campus_labels` | `Off Campus Special Programs` 39 (as expected; needs a decision only if graded) |
| `guard_failures` | none; replay exit 0 |
| parse time, process peak RSS | about 5 s, about 290 MB |

Two further checks on the same page, in scratch scripts: (a) with the normaliser change alone and no gate the page now parses (the two `TBA TBA` rows become no-time rows), so the gate is a second, independent protection; (b) with the OLD normaliser behaviour re-created and no gate the page fails exactly as in dry run 3, while with the gate it parses (8,661 normalised, 1,308 set aside, 0 failures), which is the proof that the gate alone, not the normaliser change, removes the abort.

202505 (2,293,005 bytes, the earlier `campus=T` page): 2,175 rows, all `Tampa`, 2,175 normalised, 0 set aside, 0 quarantined, `guard_failures` none. The two pages were replayed together in one invocation (`--terms 202505 202601`, a subset of the five terms), which printed `requests_made` 0.

## Tests

80 new tests in three files plus the whole suite: `uv run pytest -q` 1043 passed, 4 skipped, 1 xfailed; `uv run ruff check .` clean; `uv run mypy src` clean (93 files).

- `tests/schedule/test_normalize_time.py`: all-placeholder cells accepted; previously rejected shapes still rejected (message, field and shape); old-versus-new exhaustive differential; shape vocabulary; integer-cell failures name their field.
- `tests/sync/test_row_gate.py`: default path unchanged (normalises every row first, still fails on a bad row, no skipped or failed rows); parameters default off; the live sweep passes none of the new kwargs, still fails on an unreadable row on another campus, and now succeeds on `TBA TBA`; gate and quarantine semantics; the lost-rows guard still runs first.
- `tests/schedule/test_backfill_gap06.py`: filter-before-normalise equals normalise-then-filter (whole `TermSelection`); skipped allowed row raises; quarantined rows are counted but never written; guard failure; an unreadable excluded-campus row no longer aborts and is counted as `non_tampa`; `TBA TBA` on an allowed campus is written with no time; dry run reports quarantine, computes the rest and exits 1 with no writes; the cap (10 listed, full count, omitted count); `--apply` refuses and writes nothing (table counts identical, no `ingest_runs`), including when only a later term has the bad row and when the failing row is ungraded; `--save-responses` (every term, mode 0600, off by default, kept after a later failure, existing file mode reset, save error does not stop the run, path rules, refused before any request, refused for undo modes); `--from-saved` (report identical to the live dry run it replays, no client built or factory called with `StaffScheduleClient` and `httpx.Client` booby-trapped, no sleep, subset of terms, quarantine report, missing page, lost-rows diagnostics, refused with apply, rollback, rebuild-only and the save options, needs an existing directory).

## Remaining risk

- The abort that the gate removes is the normalisation one. A **parse-stage** error (the subject/course cell, `parse_schedule_html`) still aborts a term, on any campus, because it happens before the gate can read the row. None occurred in the 202601 and 202505 pages (0 of 12,144 rows), and the lost-rows diagnostics already cover that class; the terms 202408, 202501 and 202508 have never been seen offline. Running the next dry run with `--save-responses` makes any further failure diagnosable without a rerun.
- A live section whose time cell is `TBA TBA` now stores no time (call-out 1). It was previously a sweep failure; nothing in the live term is known to have the shape.
- The replay proves the parse, gate, selection and guard path on real pages; it cannot prove USF returns the same bytes next time.

## Not done

No USF request, database connection, backfill CLI run against anything live, push, merge or deploy. `STATE.md` and `ROADMAP.md` were not edited.
