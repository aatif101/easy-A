from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

LOW_CONFIDENCE_MAX_EFFECTIVE_N = 60.0
HIGH_CONFIDENCE_MIN_EFFECTIVE_N = 180.0


class ConfidenceLabel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class PriorLevel(StrEnum):
    course = "course"
    subject = "subject"
    global_ = "global"


class ScoreSource(StrEnum):
    instructor_course = "instructor_course"
    course = "course"
    subject = "subject"
    global_ = "global"


@dataclass(frozen=True)
class Confidence:
    effective_n: float
    section_count: int
    term_count: int
    mapped_instructor_section_count: int
    score_source: ScoreSource
    confidence_label: ConfidenceLabel


def confidence_label_for(effective_n: float, term_count: int) -> ConfidenceLabel:
    if effective_n < LOW_CONFIDENCE_MAX_EFFECTIVE_N:
        label = ConfidenceLabel.low
    elif effective_n < HIGH_CONFIDENCE_MIN_EFFECTIVE_N:
        label = ConfidenceLabel.medium
    else:
        label = ConfidenceLabel.high

    if term_count <= 1:
        return _downgrade_one_level(label)
    return label


def _downgrade_one_level(label: ConfidenceLabel) -> ConfidenceLabel:
    if label is ConfidenceLabel.high:
        return ConfidenceLabel.medium
    if label is ConfidenceLabel.medium:
        return ConfidenceLabel.low
    return ConfidenceLabel.low
