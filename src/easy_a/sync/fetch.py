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
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from easy_a.schedule.client import StaffScheduleClient
from easy_a.schedule.normalize import NormalizedSection, normalize_schedule_row
from easy_a.schedule.parser import ParsedScheduleRow, ScheduleParseError, parse_schedule_html

USF_ERROR_TAIL_MARKER = "We're sorry but an unexpected error has occured"
"""USF's own spelling; the marker follows the last complete row of every whole-term response."""

DEFAULT_CHUNK_ROWS = 250

_HEADER_RE = re.compile(r"<tr[^>]*>\s*(?:<th.*?</th>\s*)+</tr>", re.S | re.I)
_ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S | re.I)
_TD_RE = re.compile(r"<td", re.I)


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
    for match in _ROW_RE.finditer(body):
        block = match.group(0)
        if _TD_RE.search(block):
            data_row_count += 1
        buffer.append(block)
        if len(buffer) >= chunk_rows:
            parsed.extend(_parse_chunk(header_html, buffer))
            buffer.clear()
    if buffer:
        parsed.extend(_parse_chunk(header_html, buffer))
        buffer.clear()

    if len(parsed) != data_row_count:
        raise ScheduleParseError(
            f"Parsed {len(parsed)} rows from {data_row_count} data rows; refusing a response "
            "that silently lost rows."
        )
    rows = tuple(normalize_schedule_row(row) for row in parsed)
    return WholeTermParse(rows=rows, data_row_count=data_row_count, tail_error=tail_error)


def _parse_chunk(header_html: str, blocks: list[str]) -> list[ParsedScheduleRow]:
    return parse_schedule_html("<table>" + header_html + "".join(blocks) + "</table>")


def fetch_whole_term(
    client: StaffScheduleClient,
    term: str,
    *,
    now_fn: Callable[[], datetime],
) -> FetchedTerm:
    """One whole-term request, parsed and normalized. Drops the HTML before returning."""
    page = client.search_term(term)
    byte_count = page.byte_count
    content_type = page.content_type
    content_encoding = page.content_encoding
    elapsed_seconds = page.elapsed_seconds
    html = page.html
    del page
    try:
        parse = parse_whole_term(html)
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
