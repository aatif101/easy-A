"""Database side of a sweep: three bulk reads in, change-only writes out.

``load_db_state`` reads the term's sections, their current instructor state and their latest seat
snapshot with one statement each (no per-row SELECT). ``apply_sweep_plan`` performs exactly the
writes a ``SweepPlan`` lists, batches ``last_seen_at`` into chunked bulk UPDATEs and rebuilds the
rankings cache only when a cached field can have changed.

This module must stay light: no pandas, nothing from ``easy_a.refresh`` and nothing from
``easy_a.api`` (the worker must not import FastAPI routes).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.instructors import get_current_instructor_states
from easy_a.models import Course, IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings
from easy_a.schedule.ingest import SCHEDULE_SOURCE
from easy_a.schedule.ingest import _section_values as section_values
from easy_a.schedule.normalize import NormalizedSection
from easy_a.sync import sync_source
from easy_a.sync.plan import (
    SECTION_FIELDS,
    DbState,
    ExistingSection,
    SeatValues,
    SweepPlan,
)
from easy_a.sync.scope import is_undergraduate_number

CHUNK_SIZE = 1000


def _chunks[T](items: Sequence[T], size: int = CHUNK_SIZE) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def load_db_state(
    session: Session,
    term_id: int,
    rows: Iterable[NormalizedSection],
    *,
    term_code: str,
) -> DbState:
    """Read everything the pure diff needs with bulk statements only."""
    scoped_rows = tuple(rows)

    field_columns = [getattr(Section, name) for name in SECTION_FIELDS]
    section_rows = session.execute(
        select(
            Section.id,
            Section.course_id,
            Section.removed_at,
            Course.subject,
            Course.number,
            *field_columns,
        )
        .join(Course, Section.course_id == Course.id)
        .where(Section.term_id == term_id)
    ).all()

    sections_by_crn: dict[str, ExistingSection] = {}
    active_subjects: set[str] = set()
    active_in_scope = 0
    for record in section_rows:
        section_id, course_id, removed_at, subject, number, *values = record
        named = dict(zip(SECTION_FIELDS, values, strict=True))
        in_scope = same_campus(str(named["campus"]), SUPPORTED_CAMPUS) and is_undergraduate_number(
            str(number)
        )
        crn = str(named["crn"])
        sections_by_crn[crn] = ExistingSection(
            id=section_id,
            crn=crn,
            course_id=course_id,
            removed_at=removed_at,
            in_scope=in_scope,
            values=named,
        )
        if in_scope and removed_at is None:
            active_in_scope += 1
            active_subjects.add(subject)

    section_ids = [section.id for section in sections_by_crn.values()]
    instructor_states = get_current_instructor_states(session, section_ids)
    latest_seats = _latest_seats(session, term_id)

    subjects = sorted({row.subject for row in scoped_rows})
    course_ids: dict[tuple[str, str], int] = {}
    if subjects:
        course_rows = session.execute(
            select(Course.subject, Course.number, Course.id)
            .where(Course.subject.in_(subjects))
            .order_by(Course.catalog_edition.desc(), Course.id.desc())
        ).all()
        for subject, number, course_id in course_rows:
            course_ids.setdefault((subject, number), course_id)

    last_success = session.scalar(
        select(IngestRun.records_seen)
        .where(IngestRun.source == sync_source(term_code), IngestRun.status == "succeeded")
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .limit(1)
    )
    return DbState(
        sections_by_crn=sections_by_crn,
        instructor_states=instructor_states,
        latest_seats=latest_seats,
        course_ids=course_ids,
        active_in_scope_count=active_in_scope,
        active_subjects=frozenset(active_subjects),
        last_success_records_seen=last_success,
    )


def _latest_seats(session: Session, term_id: int) -> dict[int, SeatValues | None]:
    """Latest snapshot per section (newest observed_at, then highest id), portable SQL."""
    ranked = (
        select(
            SeatSnapshot.section_id.label("section_id"),
            SeatSnapshot.capacity.label("capacity"),
            SeatSnapshot.enrollment.label("enrollment"),
            SeatSnapshot.seats_remaining.label("seats_remaining"),
            SeatSnapshot.wait_seats_available.label("wait_seats_available"),
            func.row_number()
            .over(
                partition_by=SeatSnapshot.section_id,
                order_by=(SeatSnapshot.observed_at.desc(), SeatSnapshot.id.desc()),
            )
            .label("rank"),
        )
        .where(SeatSnapshot.section_id.in_(select(Section.id).where(Section.term_id == term_id)))
        .subquery()
    )
    records = session.execute(
        select(
            ranked.c.section_id,
            ranked.c.capacity,
            ranked.c.enrollment,
            ranked.c.seats_remaining,
            ranked.c.wait_seats_available,
        ).where(ranked.c.rank == 1)
    ).all()
    return {
        section_id: SeatValues(capacity, enrollment, seats_remaining, wait)
        for section_id, capacity, enrollment, seats_remaining, wait in records
    }


def apply_sweep_plan(
    session: Session,
    plan: SweepPlan,
    *,
    term_id: int,
    term_code: str,
    observed_at: datetime,
) -> None:
    """Write exactly what ``plan`` lists. The caller owns the transaction."""
    if plan.inserts:
        new_sections: list[tuple[Section, NormalizedSection]] = []
        for insert in plan.inserts:
            section = Section(
                term_id=term_id,
                course_id=insert.course_id,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                removed_at=None,
                **section_values(insert.row),
            )
            session.add(section)
            new_sections.append((section, insert.row))
        session.flush()
        for section, row in new_sections:
            session.add(
                SectionInstructor(
                    section_id=section.id,
                    name_raw=row.instructor_raw,
                    name_normalized=None,
                    source=SCHEDULE_SOURCE,
                    observed_at=observed_at,
                )
            )
            seats = SeatValues.from_row(row)
            session.add(_snapshot(section.id, seats, observed_at))

    for section_id, changed in plan.field_updates.items():
        session.execute(
            update(Section)
            .where(Section.id == section_id)
            .values(**dict(changed))
            .execution_options(synchronize_session=False)
        )

    for section_id, name in plan.instructor_appends:
        session.add(
            SectionInstructor(
                section_id=section_id,
                name_raw=name,
                name_normalized=None,
                source=SCHEDULE_SOURCE,
                observed_at=observed_at,
            )
        )
    for section_id, seats in plan.snapshot_appends:
        session.add(_snapshot(section_id, seats, observed_at))

    for chunk in _chunks(plan.removals):
        _bulk_section_update(session, Section.id.in_(chunk), removed_at=observed_at)
        session.execute(
            delete(SectionRankingCache)
            .where(SectionRankingCache.section_id.in_(chunk))
            .execution_options(synchronize_session=False)
        )
    for chunk in _chunks(plan.restores):
        _bulk_section_update(session, Section.id.in_(chunk), removed_at=None)

    seen = sorted(plan.seen_crns)
    for chunk_crns in _chunks(seen):
        _bulk_section_update(
            session,
            (Section.term_id == term_id) & Section.crn.in_(chunk_crns),
            last_seen_at=observed_at,
        )

    session.flush()
    if plan.structural_change:
        refresh_section_rankings(session, term=term_code)
    session.flush()


def _snapshot(section_id: int, seats: SeatValues, observed_at: datetime) -> SeatSnapshot:
    return SeatSnapshot(
        section_id=section_id,
        observed_at=observed_at,
        capacity=seats.capacity,
        enrollment=seats.enrollment,
        seats_remaining=seats.seats_remaining,
        wait_seats_available=seats.wait_seats_available,
    )


def _bulk_section_update(session: Session, where: Any, **values: object) -> None:
    session.execute(
        update(Section).where(where).values(**values).execution_options(synchronize_session=False)
    )
