# 10-GAP-03: unterminated-anchor repair (offline)

Decision: "repair-anchor". The diagnostic dry run for term 202505 (see 10-GAP-02) tripped the lost-rows guard (`expected=2175 parsed=2174`) on one legitimate data row. This gap repairs the cause in the parser input. It made no USF request and no hosted-database connection, and the guard condition is unchanged.

## Cause

Data row `#486` (0-based among data rows) is a legitimate 24-cell section. Its notes cell (the TITLE cell, which holds the title, a line break and the note) contains a hand-typed link:

- the `<a` start tag has a non-breaking space where an ordinary space belongs, and the `href` value starts with a curly quote and ends with a straight one;
- the closing tag is `</a` with no `>`, followed by a newline and a bare URL, then `</td>`.

libxml2 reads `</a\n...</td>` as a single end tag and skips to the next `>`, which is the `>` of `</td>`. The anchor was opened with the non-breaking-space start tag, so it is never matched and stays open, and the 16 cells after it nest inside it. The row then has 8 direct cells, the parser skips it, and the guard (2175 data rows vs 2174 parsed) refuses the whole term. The same ordinary-space start tag with the same broken close does not collapse the row, so the non-breaking space is part of the trigger. The diagnostics from 10-GAP-02 read `8/24 cells (missing CR, PMT, STATUS +13, 24 td tags vs 8 direct cells)`.

## What changed

- `src/easy_a/sync/fetch.py`: new `repair_unterminated_anchors(block)`. It runs on each `<tr>` block, before the guard counts data rows and before the block is parsed, in both `parse_whole_term` and the diagnostics block iterator (so diagnostics see the same text the parser did). `fetch_whole_term`, the live sweep and the backfill CLI all go through `parse_whole_term`, so there is one code path. It applies two regular expressions that both stop at the next `<` and never at a `>`:
  - `</a` followed directly by `<`, or by whitespace and then text containing no `<` or `>` up to the next `<`, becomes `</a>`;
  - `<a` + whitespace + text with no `<` or `>` up to the next `<` gets a `>` appended.

  Only a `>` is ever inserted; no text is removed or reordered, and a well-formed anchor (`<a ...>`, `</a>`, `</a >`, `<a/>`, `<abbr ...`) never matches.
- The lost-rows guard (`len(parsed) != data_row_count`), the row regex, the header regex and `parse_schedule_html` are untouched. `parse_diagnostics.py` is untouched.
- `docs/runbooks/historical-instructor-backfill.md` (section 1a) has a short note on the quirk and the repair.

Known limit: the start-tag repair would also close a tag whose quoted attribute value legitimately contains a `<`. None exists in the saved page (see the unchanged-row comparison below).

## Offline validation against the saved 202505 page

Read-only, from the git-ignored saved page (never committed, copied or quoted). Counts only.

| Check | Result |
|---|---|
| `parse_whole_term`, default 250-row chunks | 2175 of 2175 rows parsed, guard passes, `tail_error` true (the usual USF error tail) |
| Same, chunks of 7 rows and 1 row | 2175 of 2175 in both |
| Row blocks changed by the repair | 34 (one is the failing row; the others are 33 blocks with a `</a` cut off by `</td>`) |
| Rows that parsed before the change | 2174; all 2174 are field-for-field identical after the repair (compared per row, before vs after) |
| Rows newly parsed | 1 (data row `#486`, one row) |
| Whole-term CRNs, all three chunkings | the 2174 previously parsed CRNs in the same order, plus exactly one more |

Before the change, parsing the same page failed with `expected=2175 parsed=2174` and the single suspect row `#486`. After it, there is no suspect row.

## Tests

`tests/sync/test_anchor_repair.py` (new, 38 cases, all synthetic: placeholder text, `example.invalid` URLs, a curly quote, a non-breaking space, a missing `>`):

- Premise: each malformed shape really collapses the row when parsed without the repair (whole-page parser returns 4 of 5).
- Four shapes through the guard path at three chunkings (one chunk, chunks of 2, row by row): the real shape (curly href, `</a`, bare URL line), the same with a straight quote, `</a` directly before `</td>`, and an unterminated `<a` start tag only. All parse 5 of 5, CRNs in order, note text kept, cells after the note intact.
- The repaired row equals the clean row apart from the note text; two broken anchors in different rows are both repaired.
- Six well-formed note shapes are returned byte for byte unchanged and parse 5 of 5. The repair only inserts `>` and is idempotent. Other unterminated tags (`<abbr`, `</abbrx`) are left alone.
- Still rejected, alone and next to a repaired anchor row: 23-cell row, 25-cell row, one-cell placeholder row, missing `</tr>`, nested table. A short row whose note is also malformed is still rejected (4 of 5). Diagnostics name only the genuinely lost row, not the repaired one.
- With the repair disabled (a throwaway run), the repair tests fail and the rejection tests are unaffected.

The strict `xfail` nested-table test in `tests/sync/test_parse_diagnostics.py` is left as is: the repair does not touch that shape (it still xfails).

Gates: `uv run pytest -q` 941 passed, 4 skipped, 1 xfailed; `uv run ruff check .` clean; `uv run mypy src` clean (93 files).

## Next step for the operator

The five-term dry run can be rerun (one whole-term request per term, five in all) only after an explicit go-ahead; this note does not authorise it.
