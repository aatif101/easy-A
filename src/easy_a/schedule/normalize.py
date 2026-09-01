from __future__ import annotations

import re
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict

from easy_a.schedule.parser import ParsedScheduleRow, ScheduleParseError

SECONDARY_STATUS_LABELS = {
    "A": "Active",
    "C": "Cancelled with Enrollment",
    "H": "Held",
    "N": "Regional Campus — Not Approved",
    "U": "Cancelled without Enrollment",
}

DELIVERY_METHOD_LABELS = {
    "AD": "All Online 100%",
    "CL": "Classroom 1–49%",
    "HB": "Hybrid Blend 50–79%",
    "PD": "Primarily DL 80–99%",
}

_TIME_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*[ap]m)\s*[-–—]\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*[ap]m)",
    re.IGNORECASE,
)


class NormalizedSection(BaseModel):
    crn: str
    subject: str
    course_number: str
    section_number: str
    title: str
    campus: str
    session: str
    section_type: str
    credits: str | None
    primary_status: str
    secondary_status: str | None
    delivery_method: str | None
    days: str | None
    start_time: time | None
    end_time: time | None
    building: str | None
    room: str | None
    capacity: int | None
    enrollment: int | None
    seats_remaining: int | None
    wait_seats_available: int | None
    instructor_raw: str
    section_note: str | None
    fees_raw: str | None

    model_config = ConfigDict(frozen=True)


def normalize_schedule_row(row: ParsedScheduleRow) -> NormalizedSection:
    start_time, end_time = _parse_time_range(row.time_raw)
    return NormalizedSection(
        crn=row.crn.strip(),
        subject=row.subject.strip().upper(),
        course_number=row.course_number.strip().upper(),
        section_number=row.section_number.strip(),
        title=row.title.strip(),
        campus=row.campus.strip(),
        session=row.session.strip(),
        section_type=row.section_type.strip(),
        credits=_optional_clean(row.credits_raw),
        primary_status=row.primary_status.strip(),
        secondary_status=_optional_clean(row.secondary_status),
        delivery_method=_optional_clean(row.delivery_method),
        days=_optional_clean(row.days_raw),
        start_time=start_time,
        end_time=end_time,
        building=_optional_clean(row.building),
        room=_optional_clean(row.room),
        capacity=_parse_optional_int(row.capacity_raw, "capacity"),
        enrollment=_parse_optional_int(row.enrollment_raw, "enrollment"),
        seats_remaining=_parse_optional_int(row.seats_remaining_raw, "seats remaining"),
        wait_seats_available=_parse_optional_int(
            row.wait_seats_available_raw, "wait seats available"
        ),
        instructor_raw=row.instructor_raw,
        section_note=row.section_note,
        fees_raw=row.fees_raw,
    )


def _parse_optional_int(value: str | None, field_name: str) -> int | None:
    if value is None or not value.strip() or value.strip().upper() in {"N/A", "TBA"}:
        return None
    cleaned = value.replace(",", "").strip()
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ScheduleParseError(f"Invalid {field_name} value {value!r}.") from exc


def _parse_time_range(value: str | None) -> tuple[time | None, time | None]:
    if value is None or value.strip().upper() in {"", "TBA", "ARR"}:
        return None, None
    ranges = list(_TIME_RANGE_RE.finditer(value.strip()))
    if not ranges:
        raise ScheduleParseError(f"Invalid schedule time range {value!r}.")
    # Some sections contain several day/time components in a single source row.
    # The V1 schema has one start/end pair, so leave those fields unset rather
    # than inventing precedence or silently presenting only one meeting.
    if len(ranges) > 1:
        return None, None
    match = ranges[0]
    try:
        return (_parse_clock(match.group("start")), _parse_clock(match.group("end")))
    except ValueError as exc:
        raise ScheduleParseError(f"Invalid schedule time range {value!r}.") from exc


def _parse_clock(value: str) -> time:
    compact = re.sub(r"\s+", "", value).upper()
    return datetime.strptime(compact, "%I:%M%p").time()


def _optional_clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
