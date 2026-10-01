from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, ValidationError

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

PLACEHOLDER_TIME_TOKENS = frozenset({"TBA", "ARR"})
"""A time cell token meaning "no scheduled time", compared upper-cased."""

SHAPE_PLACEHOLDER = "P"
SHAPE_RANGE = "R"
SHAPE_OTHER = "?"
_SHAPE_TOKEN_LIMIT = 8


class RowNormalizationError(ScheduleParseError):
    """A parsed row that cannot be normalised, naming the failing field and its cell shape.

    A ``ScheduleParseError`` with the same message as before, so every existing handler (the live
    sweep's error classification above all) behaves identically. ``field`` and ``shape`` exist so
    the one-off backfill can quarantine and report the row without ever carrying the cell text:
    ``shape`` is a fixed-vocabulary fingerprint (``time_cell_shape`` or ``non_integer``).
    """

    def __init__(self, message: str, *, field: str, shape: str) -> None:
        super().__init__(message)
        self.field = field
        self.shape = shape


@dataclass(frozen=True)
class SkippedRow:
    """A parsed row a pre-normalisation gate excluded: identity and campus, never normalised."""

    crn: str
    campus: str


@dataclass(frozen=True)
class RowFailure:
    """A row that passed the gate but failed normalisation (backfill quarantine; no cell text)."""

    position: int
    """0-based among the response's data rows, the unit the lost-rows guard counts."""
    crn: str
    campus: str
    field: str
    shape: str


def row_failure_from(exc: ValueError, *, position: int, row: ParsedScheduleRow) -> RowFailure:
    """The quarantine record for a normalisation failure (field and shape only)."""
    if isinstance(exc, RowNormalizationError):
        field, shape = exc.field, exc.shape
    elif isinstance(exc, ValidationError) and exc.errors():
        first = exc.errors()[0]
        field = "validation:" + (".".join(str(part) for part in first.get("loc", ())) or "unknown")
        shape = "invalid_value"
    else:
        field, shape = "unknown", "invalid_value"
    return RowFailure(
        position=position, crn=row.crn.strip(), campus=row.campus.strip(), field=field, shape=shape
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
        raise RowNormalizationError(
            f"Invalid {field_name} value {value!r}.",
            field=field_name.replace(" ", "_"),
            shape="non_integer",
        ) from exc


def _is_placeholder_time(value: str) -> bool:
    """Whether every whitespace-separated component of a time cell is a placeholder.

    ``TBA``, ``ARR`` and the empty cell are the existing placeholder forms; a cell of several of
    them (``TBA TBA``: two meeting components, both unscheduled) is as unscheduled as one. A mix
    with a real time or any other token is not a placeholder.
    """
    tokens = value.upper().split()
    return all(token in PLACEHOLDER_TIME_TOKENS for token in tokens)


def time_cell_shape(value: str) -> str:
    """A fixed-vocabulary fingerprint of a time cell: ``R`` range, ``P`` placeholder, ``?`` other.

    Each clock range is one ``R`` and every remaining whitespace-separated token is ``P`` or ``?``,
    in order and space-separated (``P P``, ``R ?``), capped at eight symbols with a trailing ``+``.
    It carries the structure of the cell and none of its text.
    """
    symbols: list[str] = []
    cursor = 0
    text = value.strip()
    for match in _TIME_RANGE_RE.finditer(text):
        symbols.extend(_token_shapes(text[cursor : match.start()]))
        symbols.append(SHAPE_RANGE)
        cursor = match.end()
    symbols.extend(_token_shapes(text[cursor:]))
    if len(symbols) > _SHAPE_TOKEN_LIMIT:
        return " ".join(symbols[:_SHAPE_TOKEN_LIMIT]) + "+"
    return " ".join(symbols) or SHAPE_OTHER


def _token_shapes(fragment: str) -> list[str]:
    return [
        SHAPE_PLACEHOLDER if token.upper() in PLACEHOLDER_TIME_TOKENS else SHAPE_OTHER
        for token in fragment.split()
    ]


def _invalid_time(value: str) -> RowNormalizationError:
    return RowNormalizationError(
        f"Invalid schedule time range {value!r}.", field="time", shape=time_cell_shape(value)
    )


def _parse_time_range(value: str | None) -> tuple[time | None, time | None]:
    if value is None or value.strip().upper() in {"", "TBA", "ARR"}:
        return None, None
    ranges = list(_TIME_RANGE_RE.finditer(value.strip()))
    if not ranges:
        # Several components that are ALL unscheduled placeholders (``TBA TBA``) are no time, the
        # same rule as several ranges below. Nothing else changes: a placeholder mixed with any
        # other token, or any unknown token, is still invalid.
        if _is_placeholder_time(value):
            return None, None
        raise _invalid_time(value)
    # Some sections contain several day/time components in a single source row.
    # The V1 schema has one start/end pair, so leave those fields unset rather
    # than inventing precedence or silently presenting only one meeting.
    if len(ranges) > 1:
        return None, None
    match = ranges[0]
    try:
        return (_parse_clock(match.group("start")), _parse_clock(match.group("end")))
    except ValueError as exc:
        raise _invalid_time(value) from exc


def _parse_clock(value: str) -> time:
    compact = re.sub(r"\s+", "", value).upper()
    return datetime.strptime(compact, "%I:%M%p").time()


def _optional_clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
