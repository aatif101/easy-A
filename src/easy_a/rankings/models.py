from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from easy_a.analytics.confidence import ConfidenceLabel, PriorLevel, ScoreSource


class RankingFreshness(StrEnum):
    current = "current"
    historical = "historical"
    unavailable = "unavailable"


class RankingProvenance(BaseModel):
    freshness: RankingFreshness
    source: str
    source_term: str | None = None
    detail: str | None = None

    model_config = ConfigDict(frozen=True)


class GenEdAttribute(BaseModel):
    code: str
    label: str

    model_config = ConfigDict(frozen=True)


class ModalityInfo(BaseModel):
    delivery_method: str | None
    delivery_label: str | None
    provenance: RankingProvenance

    model_config = ConfigDict(frozen=True)


class SeatInfo(BaseModel):
    capacity: int | None
    enrollment: int | None
    seats_remaining: int | None
    wait_seats_available: int | None
    provenance: RankingProvenance

    model_config = ConfigDict(frozen=True)


class RankingSignal(BaseModel):
    signal_type: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    source_identifier: str
    source_term: str
    freshness: RankingFreshness
    evidence: str

    model_config = ConfigDict(frozen=True)


class HistoricalAnalyticsSummary(BaseModel):
    easiness_score: float
    smoothed_withdrawal_rate: float
    confidence_label: ConfidenceLabel
    effective_n: float
    score_source: ScoreSource
    prior_level: PriorLevel
    completed_grade_count: int
    total_grade_count: int
    withdrawal_count: int
    section_count: int
    term_count: int
    mapped_instructor_section_count: int
    provenance: RankingProvenance

    model_config = ConfigDict(frozen=True)


class SectionRanking(BaseModel):
    term: str
    term_name: str
    crn: str
    subject: str
    course_number: str
    course_title: str
    instructor: str | None
    instructor_provenance: RankingProvenance
    modality: ModalityInfo
    seats_remaining: int | None
    seats: SeatInfo
    gened_attributes: tuple[GenEdAttribute, ...]
    gened_provenance: RankingProvenance
    easiness_score: float
    smoothed_withdrawal_rate: float
    confidence_label: ConfidenceLabel
    effective_n: float
    score_source: ScoreSource
    historical_analytics: HistoricalAnalyticsSummary
    signals: tuple[RankingSignal, ...]
    signal_provenance: RankingProvenance
    section_provenance: RankingProvenance

    model_config = ConfigDict(frozen=True)
