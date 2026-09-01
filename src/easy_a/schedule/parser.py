from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict, Field


class ScheduleParseError(ValueError):
    """Raised when a schedule result page has an unexpected structure."""


class ParsedScheduleRow(BaseModel):
    session: str
    college: str
    department: str
    crn: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    course_number: str = Field(min_length=1)
    section_number: str = Field(min_length=1)
    section_type: str
    title: str
    section_note: str | None
    credits_raw: str | None
    payment_raw: str | None
    primary_status: str
    secondary_status: str | None
    seats_remaining_raw: str | None
    wait_seats_available_raw: str | None
    capacity_raw: str | None
    enrollment_raw: str | None
    days_raw: str | None
    time_raw: str | None
    building: str | None
    room: str | None
    instructor_raw: str
    campus: str
    delivery_method: str | None
    fees_raw: str | None

    model_config = ConfigDict(frozen=True)


EXPECTED_HEADERS = (
    "SESSION",
    "COL",
    "DPT",
    "CRN",
    "SUBJ CRS#",
    "SEC",
    "TYPE",
    "TITLE",
    "CR",
    "PMT",
    "STATUS",
    "STATUS2",
    "SEATS REMAIN",
    "WAIT SEATS AVAIL",
    "CAP",
    "ENRL",
    "DAYS",
    "TIME",
    "BLDG",
    "ROOM",
    "INSTRUCTOR",
    "CAMPUS",
    "DELIVERY METHOD",
    "FEES",
)


def parse_schedule_html(html: str) -> list[ParsedScheduleRow]:
    soup = BeautifulSoup(html, "lxml")
    header_row = _find_header_row(soup)
    if header_row is None:
        if _is_no_results_page(soup):
            return []
        raise ScheduleParseError("Schedule result table headers were not found.")

    rows: list[ParsedScheduleRow] = []
    for row in header_row.find_all_next("tr"):
        if not isinstance(row, Tag):
            continue
        cells = row.find_all("td", recursive=False)
        if len(cells) != len(EXPECTED_HEADERS):
            continue
        rows.append(_parse_row(cells))
    return rows


def _find_header_row(soup: BeautifulSoup) -> Tag | None:
    for row in soup.find_all("tr"):
        if not isinstance(row, Tag):
            continue
        headers = row.find_all("th", recursive=False)
        normalized = tuple(_clean_text(cell.get_text(" ", strip=True)).upper() for cell in headers)
        if normalized == EXPECTED_HEADERS:
            return row
    return None


def _parse_row(cells: list[Tag]) -> ParsedScheduleRow:
    values = [_optional_text(cell.get_text(" ", strip=True)) for cell in cells]
    subject, course_number = _parse_subject_course(values[4] or "")
    title, section_note = _parse_title_and_note(cells[7])
    return ParsedScheduleRow(
        session=values[0] or "",
        college=values[1] or "",
        department=values[2] or "",
        crn=values[3] or "",
        subject=subject,
        course_number=course_number,
        section_number=values[5] or "",
        section_type=values[6] or "",
        title=title,
        section_note=section_note,
        credits_raw=values[8],
        payment_raw=values[9],
        primary_status=values[10] or "",
        secondary_status=values[11],
        seats_remaining_raw=values[12],
        wait_seats_available_raw=values[13],
        capacity_raw=values[14],
        enrollment_raw=values[15],
        days_raw=values[16],
        time_raw=values[17],
        building=values[18],
        room=values[19],
        instructor_raw=values[20] or "",
        campus=values[21] or "",
        delivery_method=values[22],
        fees_raw=values[23],
    )


def _parse_subject_course(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"(?P<subject>[A-Za-z]{2,4})\s+(?P<number>[A-Za-z0-9]+)", value)
    if match is None:
        raise ScheduleParseError(f"Could not parse subject/course value {value!r}.")
    return match.group("subject").upper(), match.group("number").upper()


def _parse_title_and_note(cell: Tag) -> tuple[str, str | None]:
    fragments = [_clean_text(fragment) for fragment in cell.stripped_strings]
    fragments = [fragment for fragment in fragments if fragment]
    if not fragments:
        return "", None
    note = _clean_text(" ".join(fragments[1:])) if len(fragments) > 1 else ""
    return fragments[0], note or None


def _is_no_results_page(soup: BeautifulSoup) -> bool:
    text = _clean_text(soup.get_text(" ", strip=True)).lower()
    return "0 records were found" in text or "no records were found" in text


def _optional_text(value: str) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
