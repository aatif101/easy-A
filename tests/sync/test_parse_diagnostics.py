"""The lost-rows guard names the rows that disagree, without relaxing it or leaking content.

Phase 10 gap 02: the 202505 backfill dry run tripped ``Parsed 2174 rows from 2175 data rows`` and
the response was not kept, so the dropped row could not be identified. These tests pin the
diagnostics (positions, cell counts, fingerprints, caps, no URL or name leakage) and pin which
inputs the guard accepts and rejects so that none of that changed.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from easy_a.schedule.parser import ScheduleParseError, parse_schedule_html
from easy_a.sync import parse_diagnostics
from easy_a.sync.fetch import fetch_whole_term, parse_whole_term
from easy_a.sync.parse_diagnostics import MAX_REPORTED_ROWS, LostRowsError
from tests.sync.test_fetch import _client
from tests.sync.wholeterm_html import (
    RowSpec,
    build_whole_term_html,
    row_html,
    sequential_rows,
)

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _html_with(specs: list[RowSpec], index: int, replacement: str) -> str:
    """The whole-term page with row ``index`` swapped for hand-made row HTML."""
    html = build_whole_term_html(specs)
    return html.replace(row_html(specs[index]), replacement)


def _diagnostics(html: str, **kwargs: int) -> parse_diagnostics.LostRowsDiagnostics:
    with pytest.raises(LostRowsError) as caught:
        parse_whole_term(html, **kwargs)
    return caught.value.diagnostics


# --- diagnostics content --------------------------------------------------------------------------


def test_a_short_row_is_reported_with_position_cell_count_and_missing_cell() -> None:
    specs = sequential_rows(20)
    html = build_whole_term_html(specs, malformed_crns=[specs[7].crn])

    diag = _diagnostics(html)

    assert (diag.expected_rows, diag.parsed_rows) == (20, 19)
    assert diag.suspect_total == 1
    (row,) = diag.suspect_rows
    assert row.position == 7
    assert row.block_index == 7
    assert row.cell_count == 23
    assert row.isolated_rows == 0
    assert row.crn == specs[7].crn
    assert row.crn_shape == "digits"
    assert "missing FEES" in row.fingerprint
    assert len(row.cell_shape) == 23


def test_the_error_message_keeps_the_original_text_and_adds_a_compact_summary() -> None:
    specs = sequential_rows(20)
    html = build_whole_term_html(specs, malformed_crns=[specs[7].crn])

    with pytest.raises(
        ScheduleParseError, match=r"^Parsed 19 rows from 20 data rows; refusing"
    ) as e:
        parse_whole_term(html)

    message = str(e.value)
    assert "that silently lost rows." in message
    assert "expected=20 parsed=19" in message
    assert "#7 23/24 cells (missing FEES)" in message


def test_position_counts_data_rows_not_header_or_chunk_offsets() -> None:
    specs = sequential_rows(23)
    html = build_whole_term_html(specs, malformed_crns=[specs[17].crn])

    diag = _diagnostics(html, chunk_rows=5)

    assert [row.position for row in diag.suspect_rows] == [17]
    assert len(diag.chunks) == 1
    chunk = diag.chunks[0]
    assert (chunk.index, chunk.first_position, chunk.data_rows, chunk.parsed_rows) == (3, 15, 5, 4)
    assert diag.chunk_rows == 5


def test_a_non_data_row_between_data_rows_shifts_block_index_but_not_position() -> None:
    specs = sequential_rows(6)
    html = build_whole_term_html(specs)
    spacer = "<tr><th>sub-header</th></tr>"  # no <td>: not a data row, not counted by the guard
    html = html.replace(row_html(specs[2]), spacer + row_html(specs[2], malformed=True))

    (row,) = _diagnostics(html).suspect_rows

    assert row.position == 2
    assert row.block_index == 3


def test_a_one_cell_placeholder_row_is_fingerprinted_as_spanning_and_crnless() -> None:
    specs = sequential_rows(5)
    placeholder = '<tr><td colspan="24">Cancelled</td></tr>'
    html = _html_with(specs, 2, row_html(specs[2]) + placeholder)

    diag = _diagnostics(html)

    assert (diag.expected_rows, diag.parsed_rows) == (6, 5)
    (row,) = diag.suspect_rows
    assert row.position == 3
    assert row.cell_count == 1
    assert row.colspan_cells == 1
    assert row.crn is None
    assert row.crn_shape == "absent"
    assert row.cell_shape == "a"
    assert "spanning" in row.fingerprint
    assert "Cancelled" not in json.dumps(diag.to_dict())


def test_a_nested_table_inside_a_cell_is_fingerprinted() -> None:
    specs = sequential_rows(5)
    nested = row_html(specs[2]).replace(
        f"<td>{specs[2].instructor}</td>",
        f"<td><table><tr><td>x</td></tr></table>{specs[2].instructor}</td>",
    )

    (row,) = _diagnostics(_html_with(specs, 2, nested)).suspect_rows

    assert row.nested_table is True
    assert row.td_tag_count > row.cell_count
    assert "nested table" in row.fingerprint


def test_a_row_with_an_extra_cell_is_reported_as_extra() -> None:
    specs = sequential_rows(5)
    wide = row_html(specs[1]).replace("</tr>", "<td>x</td></tr>")

    (row,) = _diagnostics(_html_with(specs, 1, wide)).suspect_rows

    assert row.cell_count == 25
    assert "1 extra cells" in row.fingerprint


def test_a_missing_row_close_makes_a_block_that_swallows_the_next_row() -> None:
    specs = sequential_rows(5)
    html = _html_with(specs, 2, row_html(specs[2]).replace("</tr>", ""))

    diag = _diagnostics(html)

    assert diag.parsed_rows > diag.expected_rows
    (row,) = diag.suspect_rows
    assert row.position == 2
    assert row.isolated_rows == 2
    assert "block holds 2 rows" in row.fingerprint


def test_a_mismatch_that_needs_chunk_context_still_names_the_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    specs = sequential_rows(12)
    html = build_whole_term_html(specs, malformed_crns=[specs[6].crn])
    monkeypatch.setattr(parse_diagnostics, "_inspect_block", lambda *args: None)

    diag = _diagnostics(html, chunk_rows=5)

    assert diag.suspect_rows == ()
    assert [chunk.index for chunk in diag.chunks] == [1]
    assert "No row reproduces alone; first mismatch is chunk 1" in str(LostRowsError("x", diag))


def test_a_non_numeric_crn_cell_is_reported_by_shape_only() -> None:
    specs = sequential_rows(4)
    broken = row_html(specs[1], malformed=True).replace(
        f"<td>{specs[1].crn}</td>", "<td>AB-12&nbsp;secret</td>"
    )

    (row,) = _diagnostics(_html_with(specs, 1, broken)).suspect_rows

    assert row.crn is None
    assert row.crn_shape == "non_numeric_12_chars"
    assert "secret" not in json.dumps(row.to_dict())


# --- caps ------------------------------------------------------------


def test_reported_rows_and_chunks_are_capped_but_totals_are_exact() -> None:
    specs = sequential_rows(60)
    bad = [spec.crn for spec in specs[::2]]  # 30 short rows
    html = build_whole_term_html(specs, malformed_crns=bad)

    diag = _diagnostics(html, chunk_rows=2)
    payload = diag.to_dict()

    assert diag.expected_rows == 60
    assert diag.parsed_rows == 30
    assert payload["difference"] == 30
    assert diag.suspect_total == 30
    assert len(diag.suspect_rows) == MAX_REPORTED_ROWS == 10
    assert payload["suspect_rows_omitted"] == 20
    assert [row.position for row in diag.suspect_rows] == list(range(0, 20, 2))
    assert payload["mismatched_chunks_total"] == 30
    assert len(payload["mismatched_chunks"]) == MAX_REPORTED_ROWS
    assert "+27 more" in str(LostRowsError("x", diag))


def test_cell_shape_is_bounded() -> None:
    specs = sequential_rows(3)
    wide = row_html(specs[1]).replace("</tr>", "<td>x</td>" * 60 + "</tr>")

    (row,) = _diagnostics(_html_with(specs, 1, wide)).suspect_rows

    assert row.cell_count == 84
    assert len(row.cell_shape) == parse_diagnostics.MAX_SHAPE_CHARS + 1
    assert row.cell_shape.endswith("+")


# --- no leakage ---------------------------------------------------------------


def test_no_url_name_title_or_raw_html_leaks_into_the_message_or_the_diagnostics() -> None:
    specs = [
        RowSpec(
            crn=str(20000 + i),
            instructor="Ada Lovelace",
            title="Secret Topics http://leak.example/title",
        )
        for i in range(8)
    ]
    leaky = row_html(specs[3], malformed=True).replace(
        "Ada Lovelace", '<a href="https://leak.example/ada">Ada Lovelace</a>'
    )
    html = _html_with(specs, 3, leaky)

    with pytest.raises(LostRowsError) as caught:
        parse_whole_term(html)

    blob = str(caught.value) + json.dumps(caught.value.diagnostics.to_dict())
    for forbidden in (
        "Ada",
        "Lovelace",
        "Secret",
        "http",
        "://",
        "leak",
        "<td",
        "<tr",
        "<a ",
        "href",
    ):
        assert forbidden not in blob, forbidden
    assert "20003" in blob  # the digits-only CRN is the one cell value that is reported


# --- the guard is exactly as strict as before ----------------------------------------------------


def _nested(specs: list[RowSpec]) -> str:
    row = row_html(specs[2]).replace(
        f"<td>{specs[2].instructor}</td>",
        f"<td><table><tr><td>x</td></tr></table>{specs[2].instructor}</td>",
    )
    return _html_with(specs, 2, row)


@pytest.mark.parametrize(
    "build",
    [
        lambda s: build_whole_term_html(s, malformed_crns=[s[2].crn]),
        lambda s: _html_with(s, 2, row_html(s[2]).replace("</tr>", "<td>x</td></tr>")),
        lambda s: _html_with(s, 2, row_html(s[2]) + '<tr><td colspan="24">Cancelled</td></tr>'),
        lambda s: _html_with(s, 2, row_html(s[2]).replace("</tr>", "")),
        _nested,
    ],
    ids=["short-row", "extra-cell", "placeholder-row", "unclosed-row", "nested-table"],
)
def test_the_guard_still_rejects_every_input_it_rejected_before(build: object) -> None:
    html = build(sequential_rows(5))  # type: ignore[operator]

    with pytest.raises(ScheduleParseError, match=r"Parsed \d+ rows from \d+ data rows"):
        parse_whole_term(html)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda h: h,
        lambda h: h.replace("<tr>", '<tr class="a" onclick="x">'),
        lambda h: h.replace("<td>Synthetic note", "<td><!-- </tr> -->Synthetic note"),
    ],
    ids=["clean", "row-attributes", "comment-with-close"],
)
def test_the_guard_still_accepts_every_input_it_accepted_before(
    mutate: object,
) -> None:
    html = mutate(build_whole_term_html(sequential_rows(5)))  # type: ignore[operator]

    parsed = parse_whole_term(html)

    assert len(parsed.rows) == parsed.data_row_count == 5


def test_a_missing_header_is_still_a_plain_parse_error_without_diagnostics() -> None:
    html = build_whole_term_html(sequential_rows(5), include_header=False)

    with pytest.raises(ScheduleParseError, match="headers were not found") as caught:
        parse_whole_term(html)

    assert not isinstance(caught.value, LostRowsError)


def test_a_failure_inside_the_diagnostics_never_replaces_the_guard_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args: object) -> None:
        raise RuntimeError("inspection bug")

    monkeypatch.setattr(parse_diagnostics, "_inspect_block", boom)
    specs = sequential_rows(6)
    html = build_whole_term_html(specs, malformed_crns=[specs[1].crn])

    diag = _diagnostics(html)

    assert diag.inspection_failed is True
    assert (diag.expected_rows, diag.parsed_rows) == (6, 5)
    assert diag.suspect_rows == ()


# --- the opt-in failure hook ---------------------------------------------------------------------


def test_the_failure_hook_receives_the_raw_html_only_when_the_parse_guard_trips() -> None:
    specs = sequential_rows(6)
    good = build_whole_term_html(specs)
    bad = build_whole_term_html(specs, malformed_crns=[specs[2].crn])
    seen: list[str] = []

    for html in (good, bad):
        transport = httpx.MockTransport(
            lambda request, body=html: httpx.Response(
                200, text=body, headers={"content-type": "text/html"}
            )
        )
        http, client = _client(transport)
        with http, contextlib.suppress(LostRowsError):
            fetch_whole_term(client, "202701", now_fn=lambda: NOW, on_parse_failure=seen.append)

    assert seen == [bad]


def test_the_hook_does_not_change_what_is_raised() -> None:
    specs = sequential_rows(6)
    bad = build_whole_term_html(specs, malformed_crns=[specs[2].crn])
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=bad, headers={"content-type": "text/html"})
    )
    http, client = _client(transport)
    with http, pytest.raises(LostRowsError, match=r"Parsed 5 rows from 6 data rows"):
        fetch_whole_term(client, "202701", now_fn=lambda: NOW, on_parse_failure=lambda html: None)


# --- offline finding: a nested table row parses whole-page but is lost by the chunker


@pytest.mark.xfail(
    strict=True,
    raises=ScheduleParseError,
    reason=(
        "Latent chunker/parser divergence (Phase 10 gap 02, not shown to occur in USF data): "
        "_ROW_RE ends a row block at the first </tr>, so a data row holding a nested table is "
        "cut short and dropped, while parse_schedule_html on the whole page parses it. Not fixed: "
        "changing what the guard accepts needs an explicit decision and USF evidence."
    ),
)
def test_a_row_with_a_nested_table_parses_the_same_whole_page_and_chunked() -> None:
    specs = sequential_rows(5)
    html = _nested(specs)

    assert len(parse_schedule_html(html)) == 5  # the unchunked parser accepts it
    assert len(parse_whole_term(html).rows) == 5
