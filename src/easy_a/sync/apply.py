"""Database side of a sweep: three bulk reads in, change-only writes out.

``load_db_state`` reads the term's sections, their current instructor state and their latest seat
snapshot with one statement each (no per-row SELECT). ``apply_sweep_plan`` performs exactly the
writes a ``SweepPlan`` lists, batches ``last_seen_at`` into chunked bulk UPDATEs and rebuilds the
rankings cache only when a cached field can have changed.

This module must stay light: no pandas, nothing from ``easy_a.refresh`` and nothing from
``easy_a.api`` (the worker must not import FastAPI routes).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from easy_a.common.campus import SUPPORTED_CAMPUS, same_campus
from easy_a.common.instructors import CurrentInstructorState, get_current_instructor_states
from easy_a.models import Course, IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache, refresh_section_rankings
from easy_a.schedule.ingest import SCHEDULE_SOURCE
from easy_a.schedule.ingest import _section_values as section_values
from easy_a.schedule.normalize import NormalizedSection
from easy_a.sync import sync_source
from easy_a.sync.plan import (
    SEAT_FIELDS,
    SECTION_FIELDS,
    DbState,
    ExistingSection,
    SeatValues,
    SweepPlan,
)
from easy_a.sync.scope import is_undergraduate_number

if TYPE_CHECKING:
    from easy_a.analytics.queries import GradeEvidenceCache

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
    cache: SweepStateCache | None = None,
) -> DbState:
    """Read everything the pure diff needs with bulk statements only.

    With a ``cache`` the term's section state is reused from the previous sweep when nothing else
    has written to it, so an unchanged term costs a few one-row reads instead of a full re-read.
    """
    scoped_rows = tuple(rows)
    sections = (
        _load_term_sections(session, term_id, loaded_at=0.0)
        if cache is None
        else cache.load(session, term_id)
    )

    active_subjects: set[str] = set()
    active_in_scope = 0
    for crn, existing in sections.sections_by_crn.items():
        if existing.in_scope and existing.removed_at is None:
            active_in_scope += 1
            active_subjects.add(sections.subjects_by_crn[crn])

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
        sections_by_crn=sections.sections_by_crn,
        instructor_states=sections.instructor_states,
        latest_seats=sections.latest_seats,
        course_ids=course_ids,
        active_in_scope_count=active_in_scope,
        active_subjects=frozenset(active_subjects),
        last_success_records_seen=last_success,
    )


@dataclass(frozen=True)
class _TermSections:
    """The per-section part of a DbState: what SweepStateCache keeps between sweeps."""

    term_id: int
    sections_by_crn: Mapping[str, ExistingSection]
    subjects_by_crn: Mapping[str, str]
    instructor_states: Mapping[int, CurrentInstructorState]
    latest_seats: Mapping[int, SeatValues | None]
    fingerprint: tuple[object, ...]
    loaded_at: float


class SweepStateCache:
    """Keeps a term's section state between one worker's sweeps (database egress, not speed).

    A full term re-read every sweep was most of the worker's egress. The cached state is reused
    only while ``term_fingerprint`` still equals the value this worker committed, and for at most
    ``max_age_seconds``; a new term, a failed sweep or any other writer (an operator CLI adding,
    deleting or re-marking sections, instructors or snapshots) forces a full reload. After a
    sweep only the sections it touched are re-read, and the result is kept only once the sweep's
    transaction has committed.
    """

    def __init__(
        self,
        *,
        max_age_seconds: float = 6 * 3600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_age_seconds = max_age_seconds
        self._clock = clock
        self._state: _TermSections | None = None
        self._current: _TermSections | None = None
        self._pending: _TermSections | None = None
        self.full_loads = 0
        self.last_load_reused = False

    def load(self, session: Session, term_id: int) -> _TermSections:
        state = self._state
        self._pending = None
        reusable = (
            state is not None
            and state.term_id == term_id
            and self._clock() - state.loaded_at < self._max_age_seconds
            and term_fingerprint(session, term_id) == state.fingerprint
        )
        if state is None or not reusable:
            self._state = None
            state = _load_term_sections(session, term_id, loaded_at=self._clock())
            self.full_loads += 1
        self.last_load_reused = reusable
        self._current = state
        return state

    def stage(self, session: Session, touched_section_ids: Iterable[int]) -> None:
        """Re-read the sections a sweep wrote, inside its transaction; kept only on commit()."""
        if self._current is not None:
            self._pending = _reload_sections(session, self._current, touched_section_ids)

    def commit(self) -> None:
        if self._pending is not None:
            self._state = self._pending
        self._current = self._pending = None

    def invalidate(self) -> None:
        self._state = self._current = self._pending = None


def term_fingerprint(session: Session, term_id: int) -> tuple[object, ...]:
    """Three one-row aggregates that change when sections, instructors or snapshots are written."""
    term_section_ids = select(Section.id).where(Section.term_id == term_id)
    sections = session.execute(
        select(func.count(Section.id), func.max(Section.id), func.count(Section.removed_at)).where(
            Section.term_id == term_id
        )
    ).one()
    instructors = session.execute(
        select(func.count(SectionInstructor.id), func.max(SectionInstructor.id)).where(
            SectionInstructor.section_id.in_(term_section_ids)
        )
    ).one()
    seats = session.execute(
        select(func.count(SeatSnapshot.id), func.max(SeatSnapshot.id)).where(
            SeatSnapshot.section_id.in_(term_section_ids)
        )
    ).one()
    return (*sections, *instructors, *seats)


def _section_records(session: Session, where: Any) -> list[tuple[ExistingSection, str]]:
    """Each matching section as the diff sees it, with its course subject."""
    field_columns = [getattr(Section, name) for name in SECTION_FIELDS]
    records = session.execute(
        select(
            Section.id,
            Section.course_id,
            Section.removed_at,
            Course.subject,
            Course.number,
            *field_columns,
        )
        .join(Course, Section.course_id == Course.id)
        .where(where)
    ).all()
    existing: list[tuple[ExistingSection, str]] = []
    for record in records:
        section_id, course_id, removed_at, subject, number, *values = record
        named = dict(zip(SECTION_FIELDS, values, strict=True))
        in_scope = same_campus(str(named["campus"]), SUPPORTED_CAMPUS) and is_undergraduate_number(
            str(number)
        )
        section = ExistingSection(
            id=section_id,
            crn=str(named["crn"]),
            course_id=course_id,
            removed_at=removed_at,
            in_scope=in_scope,
            values=named,
        )
        existing.append((section, subject))
    return existing


def _load_term_sections(session: Session, term_id: int, *, loaded_at: float) -> _TermSections:
    sections_by_crn: dict[str, ExistingSection] = {}
    subjects_by_crn: dict[str, str] = {}
    for existing, subject in _section_records(session, Section.term_id == term_id):
        sections_by_crn[existing.crn] = existing
        subjects_by_crn[existing.crn] = subject
    section_ids = [section.id for section in sections_by_crn.values()]
    return _TermSections(
        term_id=term_id,
        sections_by_crn=sections_by_crn,
        subjects_by_crn=subjects_by_crn,
        instructor_states=get_current_instructor_states(session, section_ids),
        latest_seats=_latest_seats(session, select(Section.id).where(Section.term_id == term_id)),
        fingerprint=term_fingerprint(session, term_id),
        loaded_at=loaded_at,
    )


def _reload_sections(
    session: Session, state: _TermSections, section_ids: Iterable[int]
) -> _TermSections:
    """``state`` with the given sections and the fingerprint read again."""
    ids = sorted(set(section_ids))
    sections_by_crn = dict(state.sections_by_crn)
    subjects_by_crn = dict(state.subjects_by_crn)
    instructor_states = dict(state.instructor_states)
    latest_seats = dict(state.latest_seats)
    for chunk in _chunks(ids):
        for existing, subject in _section_records(session, Section.id.in_(chunk)):
            sections_by_crn[existing.crn] = existing
            subjects_by_crn[existing.crn] = subject
        for section_id in chunk:
            instructor_states.pop(section_id, None)
            latest_seats.pop(section_id, None)
        instructor_states.update(get_current_instructor_states(session, chunk))
        latest_seats.update(_latest_seats(session, chunk))
    return _TermSections(
        term_id=state.term_id,
        sections_by_crn=sections_by_crn,
        subjects_by_crn=subjects_by_crn,
        instructor_states=instructor_states,
        latest_seats=latest_seats,
        fingerprint=term_fingerprint(session, state.term_id),
        loaded_at=state.loaded_at,
    )


def _latest_seats(session: Session, section_ids: Any) -> dict[int, SeatValues | None]:
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
        .where(SeatSnapshot.section_id.in_(section_ids))
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
    evidence_cache: GradeEvidenceCache | None = None,
) -> frozenset[int]:
    """Write exactly what ``plan`` lists and return the ids of the sections it wrote.

    The caller owns the transaction. ``last_seen_at`` bumps are not counted as writes: the diff
    never reads that column.
    """
    inserted_ids: list[int] = []
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
            inserted_ids.append(section.id)
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
        # Only the courses this sweep touched: a whole-term rebuild re-reads every cache row and
        # was most of the project's database egress.
        refresh_section_rankings(
            session,
            term=term_code,
            course_keys=_changed_course_keys(session, plan, inserted_ids),
            evidence_cache=evidence_cache,
        )
    session.flush()
    return frozenset(
        {
            *inserted_ids,
            *plan.field_updates,
            *(section_id for section_id, _ in plan.instructor_appends),
            *(section_id for section_id, _ in plan.snapshot_appends),
            *plan.removals,
            *plan.restores,
        }
    )


def _changed_course_keys(
    session: Session, plan: SweepPlan, inserted_ids: Iterable[int]
) -> list[tuple[str, str]]:
    """(subject, number) of every course with a section whose cached ranking can have changed."""
    section_ids = {
        *inserted_ids,
        *plan.removals,
        *plan.restores,
        *(section_id for section_id, _ in plan.instructor_appends),
        *(
            section_id
            for section_id, changed in plan.field_updates.items()
            if any(name not in SEAT_FIELDS for name in changed)
        ),
    }
    keys: set[tuple[str, str]] = set()
    for chunk in _chunks(sorted(section_ids)):
        keys.update(
            (subject, number)
            for subject, number in session.execute(
                select(Course.subject, Course.number)
                .join(Section, Section.course_id == Course.id)
                .where(Section.id.in_(chunk))
            )
        )
    return sorted(keys)


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
