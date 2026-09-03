from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from easy_a.rankings.models import SectionRanking


class RankingSort(StrEnum):
    easiness_desc = "easiness_desc"
    easiness_asc = "easiness_asc"
    withdrawal_asc = "withdrawal_asc"
    seats_desc = "seats_desc"
    course = "course"


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])

    model_config = ConfigDict(frozen=True)


class RankingsSearchResponse(BaseModel):
    items: list[SectionRanking]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(frozen=True)


class TermMetadata(BaseModel):
    term: str
    term_name: str
    year: int
    season: str

    model_config = ConfigDict(frozen=True)


class SubjectMetadata(BaseModel):
    subject: str

    model_config = ConfigDict(frozen=True)


class GenEdAttributeMetadata(BaseModel):
    code: str
    label: str

    model_config = ConfigDict(frozen=True)


class DeliveryMethodMetadata(BaseModel):
    code: str
    label: str | None

    model_config = ConfigDict(frozen=True)
