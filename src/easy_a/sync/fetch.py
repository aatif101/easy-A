"""Whole-term fetch and memory-bounded, fail-closed parsing for one sweep.

The real USF whole-term response is about 7 MB, always ends in a USF error tail (no closing
table, no footer) and would peak near 443 MB if BeautifulSoup parsed it in one piece. Rows are
therefore fed to the unchanged ``parse_schedule_html`` in chunks, and the parsed row count is
checked against the number of ``<tr>`` blocks that hold ``<td>`` cells, because the parser skips
short rows silently.

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from easy_a.schedule.client import StaffScheduleClient
from easy_a.schedule.normalize import NormalizedSection, normalize_schedule_row
from easy_a.schedule.parser import ParsedScheduleRow, ScheduleParseError, parse_schedule_html
from easy_a.sync.parse_diagnostics import ChunkStat, LostRowsError, build_lost_rows_diagnostics

USF_ERROR_TAIL_MARKER = "We're sorry but an unexpected error has occured"
"""USF's own spelling; the marker follows the last complete row of every whole-term response."""

DEFAULT_CHUNK_ROWS = 250

_HEADER_RE = re.compile(r"<tr[^>]*>\s*(?:<th.*?</th>\s*)+</tr>", re.S | re.I)
_ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S | re.I)
_TD_RE = re.compile(r"<td", re.I)

# USF note cells occasionally hold hand-typed anchors with an unterminated tag. libxml2 reads a
# ``</a`` that never reaches its ``>`` as one end tag that runs on into the next ``</td>``, so the
# cell close is swallowed and the row collapses to a handful of direct cells. Both patterns stop at
# the next ``<`` (never at a ``>``), so a well-formed anchor never matches.
_UNTERMINATED_END_A_RE = re.compile(r"</a(?=<|\s[^<>]*<)", re.I)
_UNTERMINATED_START_A_RE = re.compile(r"(<a\s[^<>]*)(?=<)", re.I)


@dataclass(frozen=True)
class WholeTermParse:
    rows: tuple[NormalizedSection, ...]
    data_row_count: int
    tail_error: bool


@dataclass(frozen=True)
class FetchedTerm:
    """A parsed whole-term response. The HTML itself is not kept."""

    byte_count: int
    content_type: str
    content_encoding: str | None
    elapsed_seconds: float
    parse: WholeTermParse
    fetched_at: datetime


def repair_unterminated_anchors(block: str) -> str:
    """Close an anchor tag that is cut off by the next tag, inside one ``<tr>`` block.

    Repairs only two shapes: a ``</a`` that has no ``>`` before the next ``<`` and a ``<a ...``
    that has no ``>`` before the next ``<``. It adds a ``>`` and nothing else, never removes or
    reorders text, and leaves well-formed anchors byte-for-byte unchanged. It runs before the
    guard counts and parses rows, and the guard condition itself is unchanged.
    """
    block = _UNTERMINATED_END_A_RE.sub("</a>", block)
    return _UNTERMINATED_START_A_RE.sub(r"\1>", block)


def parse_whole_term(html: str, *, chunk_rows: int = DEFAULT_CHUNK_ROWS) -> WholeTermParse:
    """Parse a whole-term page in chunks, failing closed on a lost header or lost rows."""
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be at least 1.")
    header = _HEADER_RE.search(html)
    if header is None:
        raise ScheduleParseError("Schedule result table headers were not found.")
    header_html = header.group(0)
    body = html[header.end() :]
    tail_error = USF_ERROR_TAIL_MARKER in body

    parsed: list[ParsedScheduleRow] = []
    buffer: list[str] = []
    data_row_count = 0
    # Bookkeeping for the failure diagnostics only; it never feeds the guard decision below.
    chunk_stats: list[ChunkStat] = []
    chunk_first_block = 0
    chunk_first_position = 0
    for block_index, match in enumerate(_ROW_RE.finditer(body)):
        block = repair_unterminated_anchors(match.group(0))
        if _TD_RE.search(block):
            data_row_count += 1
        buffer.append(block)
        if len(buffer) >= chunk_rows:
            before = len(parsed)
            parsed.extend(_parse_chunk(header_html, buffer))
            chunk_stats.append(
                ChunkStat(
                    index=len(chunk_stats),
                    first_block_index=chunk_first_block,
                    first_position=chunk_first_position,
                    data_rows=data_row_count - chunk_first_position,
                    parsed_rows=len(parsed) - before,
                )
            )
            chunk_first_block = block_index + 1
            chunk_first_position = data_row_count
            buffer.clear()
    if buffer:
        before = len(parsed)
        parsed.extend(_parse_chunk(header_html, buffer))
        chunk_stats.append(
            ChunkStat(
                index=len(chunk_stats),
                first_block_index=chunk_first_block,
                first_position=chunk_first_position,
                data_rows=data_row_count - chunk_first_position,
                parsed_rows=len(parsed) - before,
            )
        )
        buffer.clear()

    if len(parsed) != data_row_count:
        raise LostRowsError(
            f"Parsed {len(parsed)} rows from {data_row_count} data rows; refusing a response "
            "that silently lost rows.",
            build_lost_rows_diagnostics(
                header_html=header_html,
                blocks=_data_blocks(body),
                chunk_stats=chunk_stats,
                chunk_rows=chunk_rows,
                expected_rows=data_row_count,
                parsed_rows=len(parsed),
            ),
        )
    rows = tuple(normalize_schedule_row(row) for row in parsed)
    return WholeTermParse(rows=rows, data_row_count=data_row_count, tail_error=tail_error)


def _data_blocks(body: str) -> Iterator[tuple[int, int, str]]:
    """``(block_index, position, html)`` for each data row, as the guard counts them."""
    position = 0
    for block_index, match in enumerate(_ROW_RE.finditer(body)):
        block = repair_unterminated_anchors(match.group(0))
        if _TD_RE.search(block):
            yield block_index, position, block
            position += 1


def _parse_chunk(header_html: str, blocks: list[str]) -> list[ParsedScheduleRow]:
    return parse_schedule_html("<table>" + header_html + "".join(blocks) + "</table>")


def fetch_whole_term(
    client: StaffScheduleClient,
    term: str,
    *,
    now_fn: Callable[[], datetime],
    on_parse_failure: Callable[[str], None] | None = None,
) -> FetchedTerm:
    """One whole-term request, parsed and normalized. Drops the HTML before returning.

    ``on_parse_failure`` is an opt-in hook for the one-off backfill: when the parse guard raises it
    receives the raw response (never otherwise), so an operator can keep it locally to diagnose.
    The live sweep leaves it unset. The error is always re-raised unchanged.
    """
    page = client.search_term(term)
    byte_count = page.byte_count
    content_type = page.content_type
    content_encoding = page.content_encoding
    elapsed_seconds = page.elapsed_seconds
    html = page.html
    del page
    try:
        try:
            parse = parse_whole_term(html)
        except ScheduleParseError:
            if on_parse_failure is not None:
                on_parse_failure(html)
            raise
    finally:
        del html
    return FetchedTerm(
        byte_count=byte_count,
        content_type=content_type,
        content_encoding=content_encoding,
        elapsed_seconds=elapsed_seconds,
        parse=parse,
        fetched_at=now_fn(),
    )
