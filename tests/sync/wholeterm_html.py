"""Synthetic whole-term HTML in the shape of the live USF response (never the real 7 MB page)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from easy_a.schedule.parser import EXPECTED_HEADERS

ERROR_TAIL = (
    "<h3>We're sorry but an unexpected error has occured in this application. "
    "Please try back later.</h3>"
)


@dataclass(frozen=True)
class RowSpec:
    crn: str = "13173"
    subject: str = "MAC"
    number: str = "1105"
    section: str = "001"
    title: str = "College Algebra"
    instructor: str = "Staff"
    campus: str = "Tampa"
    capacity: int = 135
    enrollment: int = 0
    seats_remaining: int = 135
    wait: int = 0
    delivery: str = "CL"
    status: str = "A"


def header_row_html() -> str:
    return "<tr>" + "".join(f"<th>{name}</th>" for name in EXPECTED_HEADERS) + "</tr>"


def _cells(spec: RowSpec) -> list[str]:
    return [
        "Full Term",
        "AC",
        "MTH",
        spec.crn,
        f"{spec.subject}&nbsp;{spec.number}",
        spec.section,
        "Class Lecture",
        f"{spec.title}<br>Synthetic note.",
        "3",
        "No",
        "Open",
        spec.status,
        str(spec.seats_remaining),
        str(spec.wait),
        str(spec.capacity),
        str(spec.enrollment),
        "MW",
        "11:00am-12:15pm",
        "BEH",
        "104",
        spec.instructor,
        spec.campus,
        spec.delivery,
        "QMTH $15.00(F)",
    ]


def row_html(spec: RowSpec, *, malformed: bool = False) -> str:
    cells = _cells(spec)
    if malformed:
        cells = cells[:-1]  # 23 cells: parse_schedule_html would skip it silently
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def build_whole_term_html(
    rows: Iterable[RowSpec],
    *,
    error_tail: bool = True,
    include_header: bool = True,
    malformed_crns: Iterable[str] = (),
) -> str:
    malformed = set(malformed_crns)
    parts = ["<!doctype html><html><body><p>Staff Schedule Search - Spring 2027</p><table>"]
    if include_header:
        parts.append(header_row_html())
    parts.extend(row_html(spec, malformed=spec.crn in malformed) for spec in rows)
    if error_tail:
        # Live shape: the table is never closed and there is no footer or </html>.
        parts.append(ERROR_TAIL)
    else:
        parts.append("</table><p>records were found matching your criteria.</p></body></html>")
    return "".join(parts)


def sequential_rows(count: int, *, start_crn: int = 10000) -> list[RowSpec]:
    """`count` distinct undergraduate Tampa rows spread over a few subjects."""
    subjects = ("MAC", "ENC", "CHM", "BSC", "PSY")
    return [
        RowSpec(
            crn=str(start_crn + i),
            subject=subjects[i % len(subjects)],
            number=str(1000 + (i % 300)),
            section=f"{(i % 30) + 1:03d}",
        )
        for i in range(count)
    ]
