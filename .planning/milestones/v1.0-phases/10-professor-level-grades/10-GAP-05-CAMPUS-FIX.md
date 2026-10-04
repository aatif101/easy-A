# GAP-05: backfill requests every campus and keeps the Tampa-credited labels

Date: 2026-10-01. Task: implement the fix chosen by the user ("implement-campus-fix") after the GAP-04 diagnosis and its confirmation probe. **Offline only**: no USF request, no hosted database connection, no backfill CLI run against anything live, no push or deploy. Code and tests are committed on `phase-10-prof-grades`; the next step is a new dry run (needs the user's go-ahead under D-22(e)).

## What changed

| Area | Change |
|------|--------|
| Request (backfill only) | `backfill.BACKFILL_WHOLE_TERM_CAMPUS = ALL_CAMPUSES = ""`: the backfill's whole-term POST sends a blank `P_CAMPUS`. It is passed explicitly: `fetch_whole_term(..., campus=BACKFILL_WHOLE_TERM_CAMPUS)`. |
| Request (live sync) | Unchanged. `LIVE_WHOLE_TERM_CAMPUS = "T"` is the default of `StaffScheduleClient.search_term`, `build_whole_term_form_data` and `fetch_whole_term`, so `sweep.py` still sends `campus=T` (D-22(a)). No shared default was changed; constants only name the existing values. |
| Selection gate | `select_backfill_rows` no longer uses `same_campus(row.campus, "Tampa")`. It uses the allow-list `BACKFILL_CAMPUS_LABELS = {"tampa", "off-campus - tampa"}` after collapsing whitespace and case-folding (nothing else is normalised). `common/campus.py` and the live sync's `same_campus` use are untouched. |
| Excluded labels | `St. Petersburg`, `Off-campus - St. Petersburg`, `Sarasota-Manatee`, `Off-campus - Sarasota-Manatee` and every other label (including blank) stay out of the Section rows and are counted in `non_tampa`. A label that is not allowed and not one of those four known ones is also listed under `unknown_campus_labels`. |
| Guard | `unmatched_fraction` definition and the 2% default (`DEFAULT_MAX_UNMATCHED_FRACTION = 0.02`) are unchanged, as are `zero_rows`, `duplicate_crn` and the lost-rows parse guard. |
| Report | Per term: `rows_by_campus` (all fetched rows by label), `campus_allowed_rows`, `non_tampa` plus `non_tampa_by_label` and `unknown_campus_labels` (graded rows excluded by the gate), `response_bytes`, with the existing counters (`fetched_rows`, `to_write`, `unmatched_*`, `guard_failures`, ...). Top level: `request` (`whole_term_campus`, `campus_allow_list`) and `fetch_seconds` per term (kept outside `terms` because timings differ between a dry run and its apply). Only labels and counts: no URLs, names or row text. |

## Design choices

- **Unknown labels go into `non_tampa`, not a separate counter.** Keeping them in `non_tampa` preserves the accounting identity in the runbook (`to_write` plus the skip counters covers every graded row) and the existing counter semantics. `unknown_campus_labels` is a view of `non_tampa_by_label` for labels nobody has classified, so a new label cannot hide inside a large known count.
- **Allow-list is exact on the label text.** `Off-campus-Tampa` (no spaces) and `Tampa Campus` are not on it and would show up as unknown. The grade source's own label (`0001 - Tampa Campus`) is a different field (grade `campus_raw`) and is not compared here.
- **Report labels are whitespace-collapsed, case preserved, capped at 60 characters**, so two spellings that differ only in case would appear as two keys; both are allowed by the gate.
- **The guard is intentionally computed over the whole response.** `unmatched_grade_crns` is still "graded CRN absent from every fetched row, whatever its label", so an excluded-label row counts as matched for the guard and as `non_tampa` for selection. A graded CRN that appears only under a St. Petersburg label would be reported in `non_tampa`, not unmatched, which is the visible signal if the grade source and schedule disagree on a campus.

## Offline checks of the larger payload (item 5)

Measured with the repo's own `parse_whole_term` on the git-ignored saved 202505 page (`failed-responses/202505.html`, 2,293,005 bytes, 2,175 rows for `campus=T`; never committed or quoted). Pages for larger sizes were built in the session scratchpad by repeating that page's row blocks, which is a size and shape stand-in, not a real response. Counts only.

| Page | Rows | Parse time | Process RSS after parse |
|------|-----:|-----------:|------------------------:|
| 2.3 MB (as saved) | 2,175 | 1.1 s | about 110 MB |
| 3.4 MB (x1.5) | 3,262 | 1.7 s | about 145 MB |
| 5.7 MB (x2.5) | 5,437 | 2.5 s | about 170 MB |
| 11.4 MB (x5) | 10,875 | 4.5 s | about 240 MB |

Cost is linear in rows and well inside a workstation's limits (the parser is chunked at 250 rows; the retained cost is the normalised rows, not BeautifulSoup trees, per the note at the top of `sync/fetch.py`).

How big can an all-campus page get? The only campus-mix evidence is the 2026-09-28 sample (202408, 8 subjects: 1,728 rows all-campus against 1,236 `Tampa`, about 1.4x) and the ENC probe (77 rows against 9 `Tampa`, a much more off-campus-heavy subject). A 1.4x to 2x factor on the historical `campus=T` pages (2.3 MB for the small summer term; the live term's whole-term page is about 7 MB per `sync/fetch.py`) gives roughly 3 to 14 MB. Limits in the whole-term fetch path (`schedule/client.py`):

- **`WHOLE_TERM_MAX_BYTES = 25_000_000`**: above the estimated range even for a fall or spring term at 2x (about 14 MB). **Not changed.**
- **`WHOLE_TERM_READ_TIMEOUT_SECONDS = 120`**: an `httpx` read timeout, which bounds the gap between received chunks, not the total download time; a larger body streams for longer without tripping it. **Not changed.** The connect timeout (15 s) and the 30 s inter-term pause are unaffected.
- **Memory**: the response is held once as bytes, then once as text before parsing (`b"".join`, then `decode`), about 2 to 3x the page size transiently: tens of MB at 14 MB. Not a concern.

Evidence that would change this: `error_kind` `usf_response` ("exceeded N bytes") or `usf_timeout` on a real run. The dry run now reports `response_bytes` and `fetch_seconds` per term, so the first real run settles the estimate. Nothing was adjusted on an assumption.

**Anchor repair and lost-rows guard on the new path.** Both live inside `parse_whole_term`, which the backfill still calls through `fetch_whole_term`; the request campus does not touch them. A new test sends a blank-campus response containing an `Off-campus - Tampa` row with an unterminated anchor in its note cell and checks that it is repaired (2 of 2 rows, `to_write` 2, no parse error), and that a genuine 23-cell row on the same path still fails with `error_kind` `parse` and writes nothing.

## Tests added

In `tests/schedule/test_backfill.py` and `tests/sync/test_fetch.py`:

- backfill request carries a blank `P_CAMPUS`; the live sweep's whole-term request carries `T` (`sweep_rows` against a mock transport); `search_term` and `fetch_whole_term` default to `T` and pass an explicit blank through;
- allow-list: six spellings kept (case and whitespace variants of the two Tampa labels); nine labels excluded (the four known non-Tampa labels, `Online`, `Tampa Campus`, `Off-campus-Tampa`, `Off-campus - Tampa Bay`, blank) with the per-label breakdown and the known/unknown split;
- the allow-list constant is exactly the two labels; the breakdown counts all fetched rows by label and the excluded graded ones;
- the guard still passes at exactly 2% unmatched (2 of 100) and 0%, and trips at 3% (`unmatched_fraction`), with the 2% default pinned in the constant and the CLI parser;
- a SQLite `--apply` over eight graded CRNs: `Tampa` and two spellings of `Off-campus - Tampa` rows are written with their instructor rows and stored campus label; Sarasota, `Off-campus - Sarasota-Manatee`, St. Petersburg, `Off-campus - St. Petersburg` and an unknown label never produce a Section; the report breakdown matches.

The existing tracer test now asserts the blank campus instead of `T`.

## What the next dry run should show

- `request.whole_term_campus` `(blank: all campuses)`; every term's `rows_by_campus` should contain `Off-campus - Tampa` and the other campuses, and `response_bytes` for each term.
- `unmatched_grade_crns` near 0 (the 2026-09-28 reference was 1 of 8,662, the one "Staff" row) and `guard_failures: []`. If the unmatched fraction is still above 2%, GAP-04's H2 (a capped or incomplete response) is back in play for those terms; read `rows_by_campus` first.
- `non_tampa` should be 0 or small: graded CRNs filed under Tampa by the grade source should be on the two Tampa labels. A graded CRN excluded under St. Petersburg or Sarasota would be a grade/schedule disagreement worth reading before apply. `unknown_campus_labels` should be empty; any entry needs a decision.
- `pairs_match_reference` PASS (3,216 / 1,329 / 2,178 / 2,829) is the end-to-end test; the GAP-04 expectation is that it passes once the 1,500 CRNs are matched.
- GAP-04 section 4 noted 633 non-`O` unmatched CRNs (C/L/I, labs) that the probe did not check, because every unmatched ENC CRN is type "Other". The new `to_write` and `section_type_histogram` for `Laboratory` will show whether off-campus Tampa also holds labs and classroom sections.

## Follow-up (separate decision, NOT changed here): the live term has the same blind spot

The live sync sends `campus=T` for the whole-term request (D-22(a)) and its scope filter (`sync/scope.py`, `sync/apply.py`, `same_campus(row.campus, "Tampa")`) keeps only the exact label `Tampa`; the Sprint 5 Tampa-only cleanup deleted any other nonblank campus. If the grade source files `Off-campus - Tampa` sections under Tampa, then Spring 2027 (202701) is missing the same block of sections (online and off-site "Other" types, ENC and similar large courses) from search, seat tracking and the ranking cache. In the 2026-09-28 sample the block was about 10% of rows, and the live term holds 78 "Other" sections of about 3,700 (2%) against 12% suffix `O` in the grade table (GAP-04, "Side effect").

Nothing was changed for it. It needs its own decision because it would alter D-22(a) (the request's campus), the scope filter and the Tampa-only correction, and it is a coverage statement about the shipped product (D-06/D-07), not a Phase 10 backfill matter. Questions for that follow-up: are `Off-campus - Tampa` sections really Tampa-credited for students (the grade source says so for 2024-2026); should the live sweep request every campus and allow-list the two labels as the backfill now does; what it does to the sweep's removal gate (row-count ratio thresholds, `max_missing_fraction`) and to the cadence payload; and the one-time cost of ingesting the missing block. This note is the only place the follow-up is recorded; `STATE.md` was not edited.

## Not done

No USF request, database connection, backfill CLI run, push, merge or deploy. The git-ignored saved page was only read locally for the size and timing measurements above.
