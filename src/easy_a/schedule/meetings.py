from __future__ import annotations

import re
from datetime import datetime, time
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from easy_a.models import Section

_TIME_TOKEN_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*[ap]m)\s*[-–—]\s*(?P<end>\d{1,2}:\d{2}\s*[ap]m)|TBA|ARR",
    re.IGNORECASE,
)

EXAM_BUILDINGS = frozenset({"EXAM", "PRLD"})
"""USF's schedule places common and preliminary exams in these pseudo-buildings."""


class Meeting(BaseModel):
    days: str
    start_time: str | None = None
    end_time: str | None = None
    building: str | None = None
    room: str | None = None
    is_exam: bool = False

    model_config = ConfigDict(frozen=True)


def _clock(value: str) -> str | None:
    try:
        parsed = datetime.strptime(value.replace(" ", "").upper(), "%I:%M%p")
    except ValueError:
        return None
    return parsed.strftime("%H:%M")


def _time_pairs(cell: str) -> list[tuple[str | None, str | None]]:
    return [
        (_clock(match["start"]), _clock(match["end"])) if match["start"] else (None, None)
        for match in _TIME_TOKEN_RE.finditer(cell)
    ]


def parse_meetings(
    *,
    days: str | None,
    meeting_times: str | None,
    start_time: time | None,
    end_time: time | None,
    building: str | None,
    room: str | None,
) -> tuple[Meeting, ...]:
    """Pair the schedule's space-separated day, time, building and room cells.

    A cell is only used when it has one value per meeting; otherwise that detail stays unset
    rather than being guessed. Sections stored before meeting_times existed fall back to their
    single start/end pair.
    """
    day_tokens = (days or "").split()
    if not day_tokens:
        return ()
    pairs = _time_pairs(meeting_times) if meeting_times else []
    if not meeting_times and len(day_tokens) == 1 and start_time and end_time:
        pairs = [(start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))]
    times = pairs if len(pairs) == len(day_tokens) else [(None, None)] * len(day_tokens)
    buildings = (building or "").split()
    rooms = (room or "").split()
    has_buildings = len(buildings) == len(day_tokens)
    return tuple(
        Meeting(
            days=day,
            start_time=start,
            end_time=end,
            building=buildings[index] if has_buildings else None,
            room=rooms[index] if len(rooms) == len(day_tokens) else None,
            is_exam=has_buildings and buildings[index] in EXAM_BUILDINGS,
        )
        for index, (day, (start, end)) in enumerate(zip(day_tokens, times, strict=True))
    )


def section_meetings(section: Section) -> tuple[Meeting, ...]:
    return parse_meetings(
        days=section.days,
        meeting_times=section.meeting_times,
        start_time=section.start_time,
        end_time=section.end_time,
        building=section.building,
        room=section.room,
    )
