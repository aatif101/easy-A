from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SignalType(StrEnum):
    attendance = "attendance"
    late_work = "late_work"
    exams = "exams"
    exam_location = "exam_location"
    participation = "participation"
    curve = "curve"
    lab = "lab"
    quiz = "quiz"
    delivery_format = "delivery_format"


class SignalSourceKind(StrEnum):
    current_term_syllabus = "current_term_syllabus"
    schedule_section_note = "schedule_section_note"
    historical_same_instructor_course = "historical_same_instructor_course"
    historical_same_course = "historical_same_course"
    unavailable = "unavailable"


class Signal(BaseModel):
    signal_type: SignalType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_kind: SignalSourceKind
    source_identifier: str
    source_term: str
    evidence_text: str = Field(min_length=1, max_length=240)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(frozen=True)


class ResolvedSignalSet(BaseModel):
    section_id: int
    signals: tuple[Signal, ...]
    provenance: SignalSourceKind
    source_term: str | None
    historical: bool
    instructor_match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)
