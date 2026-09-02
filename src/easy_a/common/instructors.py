from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from easy_a.models import SectionInstructor

STAFF_INSTRUCTOR_NAME = "staff"


class CurrentInstructorStatus(StrEnum):
    no_observations = "no_observations"
    blank_latest_state = "blank_latest_state"
    resolved = "resolved"
    ambiguous_latest_state = "ambiguous_latest_state"


@dataclass(frozen=True)
class CurrentInstructorState:
    name: str | None
    status: CurrentInstructorStatus
    latest_observed_at: datetime | None
    latest_names: tuple[str, ...]

    @property
    def is_usable_for_scoring(self) -> bool:
        return is_usable_instructor(self.name)


def get_current_instructor_state(session: Session, section_id: int) -> CurrentInstructorState:
    latest_observed_at = session.scalar(
        select(func.max(SectionInstructor.observed_at)).where(
            SectionInstructor.section_id == section_id
        )
    )
    if latest_observed_at is None:
        return CurrentInstructorState(
            name=None,
            status=CurrentInstructorStatus.no_observations,
            latest_observed_at=None,
            latest_names=(),
        )

    latest_raw_names = session.scalars(
        select(SectionInstructor.name_raw)
        .where(
            SectionInstructor.section_id == section_id,
            SectionInstructor.observed_at == latest_observed_at,
        )
        .order_by(SectionInstructor.id)
    ).all()
    latest_names = _unique_clean_names(latest_raw_names)
    if not latest_names:
        return CurrentInstructorState(
            name=None,
            status=CurrentInstructorStatus.blank_latest_state,
            latest_observed_at=latest_observed_at,
            latest_names=(),
        )
    if len(latest_names) > 1:
        return CurrentInstructorState(
            name=None,
            status=CurrentInstructorStatus.ambiguous_latest_state,
            latest_observed_at=latest_observed_at,
            latest_names=latest_names,
        )
    return CurrentInstructorState(
        name=latest_names[0],
        status=CurrentInstructorStatus.resolved,
        latest_observed_at=latest_observed_at,
        latest_names=latest_names,
    )


def is_usable_instructor(instructor_name: str | None) -> bool:
    return bool(instructor_name and instructor_name.strip()) and not is_staff_instructor(
        instructor_name
    )


def is_staff_instructor(instructor_name: str | None) -> bool:
    return (
        instructor_name is not None
        and instructor_name.strip().casefold() == STAFF_INSTRUCTOR_NAME
    )


def _unique_clean_names(names: Sequence[str]) -> tuple[str, ...]:
    unique_names: dict[str, str] = {}
    for name in names:
        cleaned = " ".join(name.strip().split())
        if cleaned:
            unique_names.setdefault(cleaned.casefold(), cleaned)
    return tuple(unique_names.values())
