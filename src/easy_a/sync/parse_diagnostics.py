"""Structural diagnostics for the whole-term lost-rows guard (Phase 10 gap 02).

``parse_whole_term`` refuses a response when the parsed row count differs from the number of
``<tr>`` blocks that hold ``<td>`` cells. That guard names two counts and nothing else, so a failure
on a 7 MB response could not be traced to a row. This module reports *which* data rows disagree and
*how* they are shaped, without relaxing the guard and without leaking any cell content.

Everything reported is a count, a position, a fixed-vocabulary label, or a CRN that is purely
digits. No cell text, instructor name, attribute value, URL or raw HTML ever enters a diagnostic.
The raw response stays on the operator's machine only when ``--save-failed-response`` is given.

Runs only on the failure path, so it may re-parse blocks one at a time: it costs nothing on a
healthy sweep and its memory use is bounded by one chunk.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from easy_a.schedule.parser import (
    EXPECTED_HEADERS,
    ParsedScheduleRow,
    ScheduleParseError,
    parse_schedule_html,
)

MAX_REPORTED_ROWS = 10
"""Cap on the rows (and on the chunk windows) listed in one diagnostic."""

MAX_SHAPE_CHARS = 40
_CRN_INDEX = EXPECTED_HEADERS.index("CRN")
_DIGITS_RE = re.compile(r"\d{1,10}")


class LostRowsError(ScheduleParseError):
    """The lost-rows guard tripped; ``diagnostics`` says which data rows disagree and how."""

    def __init__(self, message: str, diagnostics: LostRowsDiagnostics) -> None:
        super().__init__(f"{message} {diagnostics.summary()}")
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class ChunkStat:
    """One chunk handed to the parser: how many data rows it held and how many rows came back."""

    index: int
    first_block_index: int
    first_position: int
    data_rows: int
    parsed_rows: int

    @property
    def mismatched(self) -> bool:
        return self.data_rows != self.parsed_rows

    def to_dict(self) -> dict[str, int]:
        return {
            "chunk_index": self.index,
            "first_position": self.first_position,
            "data_rows": self.data_rows,
            "parsed_rows": self.parsed_rows,
        }


@dataclass(frozen=True)
class SuspectRow:
    """One data row that did not parse to exactly one row when parsed on its own."""

    position: int
    """0-based among data rows (``<tr>`` blocks holding a ``<td>``), the unit the guard counts."""
    block_index: int
    """0-based among every ``<tr>`` block after the header row."""
    isolated_rows: int
    """Rows the parser returned for this block alone (0 = dropped, 2+ = block swallowed a row)."""
    cell_count: int
    """Direct ``<td>`` children, the number the parser compares with the 24 expected headers."""
    td_tag_count: int
    nested_table: bool
    colspan_cells: int
    block_chars: int
    text_chars: int
    cell_shape: str
    crn: str | None
    crn_shape: str
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "block_index": self.block_index,
            "isolated_rows": self.isolated_rows,
            "cell_count": self.cell_count,
            "td_tag_count": self.td_tag_count,
            "nested_table": self.nested_table,
            "colspan_cells": self.colspan_cells,
            "block_chars": self.block_chars,
            "text_chars": self.text_chars,
            "cell_shape": self.cell_shape,
            "crn": self.crn,
            "crn_shape": self.crn_shape,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class LostRowsDiagnostics:
    expected_rows: int
    """Data rows the guard counted (what a clean parse should return)."""
    parsed_rows: int
    suspect_total: int
    """Suspect rows found in the mismatched chunks, before the reporting cap."""
    suspect_rows: tuple[SuspectRow, ...]
    chunk_total: int
    """Mismatched chunks, before the reporting cap."""
    chunks: tuple[ChunkStat, ...]
    chunk_rows: int
    inspection_failed: bool = False
    """True when the row inspection itself raised; the counts and chunks are still reported."""

    def summary(self) -> str:
        """A short single-line form that survives the 200 to 500 character error-text caps."""
        parts = [f"expected={self.expected_rows} parsed={self.parsed_rows}."]
        if self.suspect_rows:
            expected = len(EXPECTED_HEADERS)
            shown = "; ".join(
                f"#{row.position} {row.cell_count}/{expected} cells ({row.fingerprint})"
                for row in self.suspect_rows[:3]
            )
            more = self.suspect_total - min(3, len(self.suspect_rows))
            parts.append(
                f"Suspect data rows (0-based): {shown}" + (f"; +{more} more." if more else ".")
            )
        elif self.chunks:
            first = self.chunks[0]
            parts.append(
                f"No row reproduces alone; first mismatch is chunk {first.index} "
                f"(data rows from {first.first_position})."
            )
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_rows": self.expected_rows,
            "parsed_rows": self.parsed_rows,
            "difference": self.expected_rows - self.parsed_rows,
            "suspect_total": self.suspect_total,
            "suspect_rows_omitted": self.suspect_total - len(self.suspect_rows),
            "suspect_rows": [row.to_dict() for row in self.suspect_rows],
            "chunk_rows": self.chunk_rows,
            "mismatched_chunks_total": self.chunk_total,
            "mismatched_chunks": [chunk.to_dict() for chunk in self.chunks],
            "inspection_failed": self.inspection_failed,
        }


def build_lost_rows_diagnostics(
    *,
    header_html: str,
    blocks: Iterator[tuple[int, int, str]],
    chunk_stats: list[ChunkStat],
    chunk_rows: int,
    expected_rows: int,
    parsed_rows: int,
) -> LostRowsDiagnostics:
    """Re-parse only the rows of mismatched chunks, one block at a time.

    ``blocks`` yields ``(block_index, position, html)`` for every data row, in order. A row is
    reported when it parses to anything other than exactly one row on its own; when no row
    reproduces in isolation (the mismatch depends on chunk context) the mismatched chunks are still
    reported so the operator knows which window of data rows to look at.
    """
    mismatched = [stat for stat in chunk_stats if stat.mismatched]
    windows = [(stat.first_position, stat.first_position + stat.data_rows) for stat in mismatched]
    suspects: list[SuspectRow] = []
    suspect_total = 0
    inspection_failed = False
    if windows:
        try:
            for block_index, position, block in blocks:
                if not any(start <= position < end for start, end in windows):
                    continue
                row = _inspect_block(header_html, block_index, position, block)
                if row is None:
                    continue
                suspect_total += 1
                if len(suspects) < MAX_REPORTED_ROWS:
                    suspects.append(row)
        except Exception:  # diagnostics must never replace the guard's own error
            inspection_failed = True
    return LostRowsDiagnostics(
        expected_rows=expected_rows,
        parsed_rows=parsed_rows,
        suspect_total=suspect_total,
        suspect_rows=tuple(suspects),
        chunk_total=len(mismatched),
        chunks=tuple(mismatched[:MAX_REPORTED_ROWS]),
        chunk_rows=chunk_rows,
        inspection_failed=inspection_failed,
    )


def _inspect_block(
    header_html: str, block_index: int, position: int, block: str
) -> SuspectRow | None:
    try:
        isolated: list[ParsedScheduleRow] | None = parse_schedule_html(
            "<table>" + header_html + block + "</table>"
        )
    except ScheduleParseError:
        isolated = None
    if isolated is not None and len(isolated) == 1:
        return None
    tr = BeautifulSoup("<table>" + block + "</table>", "lxml").find("tr")
    cells = tr.find_all("td", recursive=False) if isinstance(tr, Tag) else []
    cell_count = len(cells)
    td_tags = len(re.findall(r"<td", block, re.I))
    nested = bool(re.search(r"<table", block, re.I))
    colspan = sum(1 for cell in cells if cell.has_attr("colspan") or cell.has_attr("rowspan"))
    text_chars = len(" ".join(tr.get_text(" ", strip=True).split())) if isinstance(tr, Tag) else 0
    shape = "".join(_cell_class(cell) for cell in cells)
    if len(shape) > MAX_SHAPE_CHARS:
        shape = shape[:MAX_SHAPE_CHARS] + "+"
    crn, crn_shape = _crn(cells)
    return SuspectRow(
        position=position,
        block_index=block_index,
        isolated_rows=len(isolated) if isolated is not None else -1,
        cell_count=cell_count,
        td_tag_count=td_tags,
        nested_table=nested,
        colspan_cells=colspan,
        block_chars=len(block),
        text_chars=text_chars,
        cell_shape=shape,
        crn=crn,
        crn_shape=crn_shape,
        fingerprint=_fingerprint(
            cell_count=cell_count,
            td_tags=td_tags,
            nested=nested,
            colspan=colspan,
            isolated=isolated,
            crn_shape=crn_shape,
        ),
    )


def _cell_class(cell: Tag) -> str:
    """'.' empty, 'd' digits only, 'a' anything else: structure without content."""
    text = " ".join(cell.get_text(" ", strip=True).replace("\xa0", " ").split())
    if not text:
        return "."
    return "d" if text.isdigit() else "a"


def _crn(cells: list[Tag]) -> tuple[str | None, str]:
    if len(cells) <= _CRN_INDEX:
        return None, "absent"
    text = " ".join(cells[_CRN_INDEX].get_text(" ", strip=True).replace("\xa0", " ").split())
    if not text:
        return None, "empty"
    if _DIGITS_RE.fullmatch(text):
        return text, "digits"
    return None, f"non_numeric_{min(len(text), 99)}_chars"


def _fingerprint(
    *,
    cell_count: int,
    td_tags: int,
    nested: bool,
    colspan: int,
    isolated: list[ParsedScheduleRow] | None,
    crn_shape: str,
) -> str:
    expected = len(EXPECTED_HEADERS)
    notes: list[str] = []
    if cell_count < expected:
        if cell_count == 0:
            notes.append("no direct cells")
        else:
            missing = EXPECTED_HEADERS[cell_count:]
            more = f" +{len(missing) - 3}" if len(missing) > 3 else ""
            notes.append("missing " + ", ".join(missing[:3]) + more)
    elif cell_count > expected:
        notes.append(f"{cell_count - expected} extra cells")
    if td_tags != cell_count:
        notes.append(f"{td_tags} td tags vs {cell_count} direct cells")
    if nested:
        notes.append("nested table")
    if colspan:
        notes.append(f"{colspan} spanning cells")
    if isolated is not None and len(isolated) > 1:
        notes.append(f"block holds {len(isolated)} rows")
    if isolated is None:
        notes.append("row parser raised")
    if crn_shape not in ("digits",):
        notes.append(f"crn {crn_shape}")
    return ", ".join(notes) if notes else "no structural cause found in isolation"
