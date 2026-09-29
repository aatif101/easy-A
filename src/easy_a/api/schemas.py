from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

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


class SyncStatusResponse(BaseModel):
    """Public health of the live schedule sync for one term (D-07).

    Reports only coarse facts. The raw ``IngestRun.error_message`` is never serialized;
    ``last_error_kind`` comes from the fixed ``easy_a.sync.SYNC_ERROR_KINDS`` vocabulary.
    """

    term: str = Field(examples=["202701"])
    last_success_at: datetime | None = Field(
        description="Finish time of the latest succeeded sweep (UTC); null when none exists."
    )
    last_run_at: datetime | None = Field(
        description="Start time of the latest sweep of any status (UTC); null when none exists."
    )
    last_status: Literal["succeeded", "failed"] | None = Field(examples=["succeeded"])
    last_error_kind: str | None = Field(
        description="Coarse failure kind of the latest sweep, only when it failed.",
        examples=["usf_http"],
    )
    last_records_failed: int | None
    failures_last_24h: int = Field(examples=[0])
    in_registration_window: bool
    cadence_seconds: int = Field(examples=[3600])
    stale_after_seconds: int = Field(examples=[7200])
    is_stale: bool
    as_of: datetime

    model_config = ConfigDict(frozen=True)
