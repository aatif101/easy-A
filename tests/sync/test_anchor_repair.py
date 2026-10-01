"""Unterminated anchors in a note cell are repaired before the lost-rows guard counts rows.

Phase 10 gap 03: the 202505 dry run lost one legitimate 24-cell section whose note cell held a hand
typed anchor with a non-breaking space in the start tag, a curly-quote ``href`` and a ``</a`` that
never reached its ``>``. libxml2 read the broken end tag as running on into ``</td>``, the anchor
stayed open and the 16 cells after it nested inside it, leaving 8 direct cells. Everything here is
synthetic (placeholder text, ``example.invalid`` URLs). The tests pin the repair, the unchanged
accepted inputs, and that the guard still rejects every genuinely lost row.
"""

from __future__ import annotations

import pytest

from easy_a.schedule.parser import ScheduleParseError, parse_schedule_html
from easy_a.sync.fetch import parse_whole_term, repair_unterminated_anchors
from easy_a.sync.parse_diagnostics import LostRowsError
from tests.sync.wholeterm_html import (
    RowSpec,
    build_whole_term_html,
    row_html,
    sequential_rows,
)

NBSP = "\xa0"
CURLY = "“"
URL = "http://example.invalid/page"

# name -> note-cell markup. The first is the shape seen in the real page; the others are variants.
MALFORMED_NOTES = {
    # curly-quote href, NBSP in the start tag, `</a` followed by a bare URL line, then `</td>`
    "curly-href-unterminated-close-then-bare-url": (
        f'Synthetic note: <a{NBSP}href={CURLY}{URL}">link text</a\n{URL}'
    ),
    # the same without the curly quote
    "straight-href-unterminated-close-then-bare-url": (
        f'Synthetic note: <a{NBSP}href="{URL}">link text</a\n{URL}'
    ),
    # `</a` immediately before the cell close
    "unterminated-close-before-cell-close": (f'Synthetic note: <a{NBSP}href="{URL}">link text</a'),
    # unterminated start tag only: no `>` before the cell close
    "unterminated-start-tag-only": f'Synthetic note: <a{NBSP}href="{URL}"',
}

WELL_FORMED_NOTES = {
    "plain-anchor": f'Synthetic note: <a href="{URL}">link text</a> and more text',
    "mailto-and-nbsp": f'Synthetic note: <a{NBSP}href="mailto:a@example.invalid">mail</a>',
    "space-before-close-bracket": f'Synthetic note: <a href="{URL}">link text</a >',
    "self-closed-anchor": "Synthetic note: <a/> text",
    "attributes": f'Synthetic note: <a href="{URL}" target="_blank" style="color:#00f">x</a>',
    "no-anchor": "Synthetic note: no link here.",
}


def _page_with_note(note: str, *, index: int = 2, count: int = 5) -> str:
    specs = sequential_rows(count)
    html = build_whole_term_html(specs)
    row = row_html(specs[index])
    return html.replace(row, row.replace("Synthetic note.", note))


# --- the quirk is real, and the repair fixes it ---------------------------------------------------


@pytest.mark.parametrize(
    "note",
    [
        MALFORMED_NOTES["curly-href-unterminated-close-then-bare-url"],
        MALFORMED_NOTES["straight-href-unterminated-close-then-bare-url"],
        MALFORMED_NOTES["unterminated-close-before-cell-close"],
        MALFORMED_NOTES["unterminated-start-tag-only"],
    ],
    ids=list(MALFORMED_NOTES),
)
def test_without_the_repair_the_unterminated_anchor_collapses_the_row(note: str) -> None:
    """Premise: the raw parser really loses the row, so the fix below is not a no-op."""
    html = _page_with_note(note)

    assert len(parse_schedule_html(html)) == 4  # the 24-cell row is skipped as an 8-cell row


@pytest.mark.parametrize("chunk_rows", [250, 2, 1], ids=["one-chunk", "chunks-of-2", "row-by-row"])
@pytest.mark.parametrize("note", list(MALFORMED_NOTES.values()), ids=list(MALFORMED_NOTES))
def test_the_guard_path_parses_every_row_when_a_note_has_an_unterminated_anchor(
    note: str, chunk_rows: int
) -> None:
    specs = sequential_rows(5)

    parsed = parse_whole_term(_page_with_note(note), chunk_rows=chunk_rows)

    assert parsed.data_row_count == 5
    assert [row.crn for row in parsed.rows] == [spec.crn for spec in specs]
    repaired_row = parsed.rows[2]
    assert repaired_row.section_note is not None
    assert repaired_row.section_note.startswith("Synthetic note:")
    assert repaired_row.campus == "Tampa"  # the cells after the note are still its own cells


def test_the_repaired_row_keeps_the_same_cell_values_as_the_clean_row() -> None:
    clean = parse_whole_term(_page_with_note("Synthetic note.")).rows
    broken = parse_whole_term(
        _page_with_note(MALFORMED_NOTES["curly-href-unterminated-close-then-bare-url"])
    ).rows

    for index, (left, right) in enumerate(zip(clean, broken, strict=True)):
        if index == 2:  # only the note text differs
            assert left.model_dump(exclude={"section_note"}) == right.model_dump(
                exclude={"section_note"}
            )
        else:
            assert left == right


def test_two_unterminated_anchors_in_different_rows_are_both_repaired() -> None:
    specs = sequential_rows(6)
    html = build_whole_term_html(specs)
    for index, shape in (
        (1, "curly-href-unterminated-close-then-bare-url"),
        (4, "unterminated-start-tag-only"),
    ):
        row = row_html(specs[index])
        html = html.replace(row, row.replace("Synthetic note.", MALFORMED_NOTES[shape]))

    parsed = parse_whole_term(html, chunk_rows=2)

    assert (len(parsed.rows), parsed.data_row_count) == (6, 6)


# --- well-formed markup is untouched ---------------------------------------------


@pytest.mark.parametrize("note", list(WELL_FORMED_NOTES.values()), ids=list(WELL_FORMED_NOTES))
def test_well_formed_anchors_are_returned_byte_for_byte_unchanged(note: str) -> None:
    html = _page_with_note(note)
    block = row_html(sequential_rows(5)[2]).replace("Synthetic note.", note)

    assert repair_unterminated_anchors(block) == block
    parsed = parse_whole_term(html, chunk_rows=2)
    assert (len(parsed.rows), parsed.data_row_count) == (5, 5)


def test_the_repair_only_inserts_a_closing_bracket_and_is_idempotent() -> None:
    for note in MALFORMED_NOTES.values():
        block = row_html(sequential_rows(5)[2]).replace("Synthetic note.", note)

        repaired = repair_unterminated_anchors(block)

        assert repaired != block
        assert len(repaired) > len(block)
        # Nothing but ">" was added: dropping every ">" from both gives the same text.
        assert repaired.replace(">", "") == block.replace(">", "")
        assert repair_unterminated_anchors(repaired) == repaired


def test_the_repair_leaves_other_unterminated_tags_alone() -> None:
    block = "<tr><td>x <abbr title='t'</td><td>y </abbrx</td></tr>"

    assert repair_unterminated_anchors(block) == block


# --- the guard is exactly as strict as before ------------------------------------


def _nested(specs: list[RowSpec]) -> str:
    row = row_html(specs[2]).replace(
        f"<td>{specs[2].instructor}</td>",
        f"<td><table><tr><td>x</td></tr></table>{specs[2].instructor}</td>",
    )
    return build_whole_term_html(specs).replace(row_html(specs[2]), row)


def _swap(specs: list[RowSpec], replacement: str) -> str:
    return build_whole_term_html(specs).replace(row_html(specs[2]), replacement)


REJECTED = {
    "23-cell-row": lambda s: build_whole_term_html(s, malformed_crns=[s[2].crn]),
    "25-cell-row": lambda s: _swap(s, row_html(s[2]).replace("</tr>", "<td>x</td></tr>")),
    "placeholder-row": lambda s: _swap(
        s, row_html(s[2]) + '<tr><td colspan="24">Cancelled</td></tr>'
    ),
    "missing-row-close": lambda s: _swap(s, row_html(s[2]).replace("</tr>", "")),
    "nested-table": _nested,
}


@pytest.mark.parametrize("name", list(REJECTED))
def test_genuinely_lost_rows_are_still_rejected(name: str) -> None:
    html = REJECTED[name](sequential_rows(5))

    with pytest.raises(ScheduleParseError, match=r"Parsed \d+ rows from \d+ data rows"):
        parse_whole_term(html)


@pytest.mark.parametrize("name", list(REJECTED))
def test_a_lost_row_is_still_rejected_next_to_a_repaired_anchor_row(name: str) -> None:
    """The repair must not mask a real loss elsewhere on the page."""
    specs = sequential_rows(6)
    html = REJECTED[name](specs)
    row = row_html(specs[4])
    html = html.replace(
        row,
        row.replace(
            "Synthetic note.", MALFORMED_NOTES["curly-href-unterminated-close-then-bare-url"]
        ),
    )

    with pytest.raises(LostRowsError, match=r"Parsed \d+ rows from \d+ data rows"):
        parse_whole_term(html, chunk_rows=3)


def test_a_short_row_whose_note_is_also_malformed_is_still_rejected() -> None:
    specs = sequential_rows(5)
    short = row_html(specs[2], malformed=True).replace(
        "Synthetic note.", MALFORMED_NOTES["unterminated-close-before-cell-close"]
    )

    with pytest.raises(LostRowsError, match=r"Parsed 4 rows from 5 data rows"):
        parse_whole_term(_swap(specs, short))


def test_diagnostics_name_only_the_genuinely_lost_row_not_the_repaired_one() -> None:
    specs = sequential_rows(8)
    html = build_whole_term_html(specs, malformed_crns=[specs[5].crn])
    row = row_html(specs[2])
    html = html.replace(
        row,
        row.replace(
            "Synthetic note.", MALFORMED_NOTES["curly-href-unterminated-close-then-bare-url"]
        ),
    )

    with pytest.raises(LostRowsError) as caught:
        parse_whole_term(html, chunk_rows=3)

    diag = caught.value.diagnostics
    assert (diag.expected_rows, diag.parsed_rows) == (8, 7)
    assert [row.position for row in diag.suspect_rows] == [5]
