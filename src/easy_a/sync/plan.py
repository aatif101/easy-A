"""Pure sweep diff: what a scoped USF response changes relative to the database.

``build_sweep_plan`` performs no I/O. It compares the in-scope rows of one sweep with a
``DbState`` snapshot (three bulk reads, see ``easy_a.sync.apply``) and returns exactly the
writes that are needed, so an unchanged sweep is an empty plan (REQ-SYNC-01, change-only).

This module must stay light: no pandas and nothing from ``easy_a.refresh``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from easy_a.common.instructors import CurrentInstructorState, CurrentInstructorStatus
from easy_a.schedule.ingest import _section_values as section_values
from easy_a.schedule.normalize import NormalizedSection

SEAT_FIELDS: frozenset[str] = frozenset(
    {"capacity", "enrollment", "seats_remaining", "wait_seats_available"}
)
"""Section columns that mirror the latest seat snapshot. A change here alone is not structural."""

SECTION_FIELDS: tuple[str, ...] = (
    "crn",
    "section_number",
    "campus",
    "session",
    "section_type",
    "credits",
    "primary_status",
    "secondary_status",
    "delivery_method",
    "days",
    "start_time",
    "end_time",
    "building",
    "room",
    "capacity",
    "enrollment",
    "seats_remaining",
    "wait_seats_available",
    "section_note",
    "fees_raw",
)
"""The Section columns the schedule ingest maps from a row (a test pins it to _section_values)."""

# The CRN is the identity key, never a change.
_IDENTITY_FIELDS: frozenset[str] = frozenset({"crn"})


@dataclass(frozen=True)
class SeatValues:
    capacity: int | None
    enrollment: int | None
    seats_remaining: int | None
    wait_seats_available: int | None

    @classmethod
    def from_row(cls, row: NormalizedSection) -> SeatValues:
        return cls(
            capacity=row.capacity,
            enrollment=row.enrollment,
            seats_remaining=row.seats_remaining,
            wait_seats_available=row.wait_seats_available,
        )


@dataclass(frozen=True)
class ExistingSection:
    id: int
    crn: str
    course_id: int
    removed_at: datetime | None
    in_scope: bool
    values: Mapping[str, object]
    """The current ``_section_values`` field values as stored."""


@dataclass(frozen=True)
class DbState:
    sections_by_crn: Mapping[str, ExistingSection]
    instructor_states: Mapping[int, CurrentInstructorState]
    latest_seats: Mapping[int, SeatValues | None]
    course_ids: Mapping[tuple[str, str], int]
    active_in_scope_count: int
    active_subjects: frozenset[str]
    last_success_records_seen: int | None


@dataclass(frozen=True)
class SectionInsert:
    row: NormalizedSection
    course_id: int


@dataclass(frozen=True)
class SweepCounts:
    records_seen: int
    records_inserted: int
    records_updated: int
    records_failed: int


@dataclass(frozen=True)
class SweepPlan:
    records_seen: int
    inserts: tuple[SectionInsert, ...] = ()
    field_updates: Mapping[int, Mapping[str, object]] = field(default_factory=dict)
    instructor_appends: tuple[tuple[int, str], ...] = ()
    snapshot_appends: tuple[tuple[int, SeatValues], ...] = ()
    removals: tuple[int, ...] = ()
    restores: tuple[int, ...] = ()
    seen_crns: frozenset[str] = frozenset()
    unknown_course_keys: Mapping[tuple[str, str], tuple[NormalizedSection, ...]] = field(
        default_factory=dict
    )

    @property
    def structural_change(self) -> bool:
        """True when a cached ranking field can change (anything but a seat-only sweep)."""
        if self.inserts or self.removals or self.restores or self.instructor_appends:
            return True
        return any(
            any(name not in SEAT_FIELDS for name in changed)
            for changed in self.field_updates.values()
        )

    @property
    def unapplied_count(self) -> int:
        return sum(len(rows) for rows in self.unknown_course_keys.values())

    def counts(self) -> SweepCounts:
        changed_ids: set[int] = set(self.field_updates)
        changed_ids.update(section_id for section_id, _ in self.instructor_appends)
        changed_ids.update(section_id for section_id, _ in self.snapshot_appends)
        changed_ids.update(self.removals)
        changed_ids.update(self.restores)
        return SweepCounts(
            records_seen=self.records_seen,
            records_inserted=len(self.inserts),
            records_updated=len(changed_ids),
            records_failed=self.unapplied_count,
        )


def normalize_instructor_name(name: str) -> str:
    """Whitespace-collapsed, case-folded comparison key. Never stored."""
    return " ".join(name.split()).casefold()


def _instructor_changed(state: CurrentInstructorState | None, new_name: str) -> bool:
    new_key = normalize_instructor_name(new_name)
    if state is None or state.status is CurrentInstructorStatus.no_observations:
        return True
    latest = tuple(normalize_instructor_name(name) for name in state.latest_names)
    if state.status is CurrentInstructorStatus.blank_latest_state:
        return new_key != ""
    # Resolved: the one latest name. Ambiguous: different unless the latest names equal
    # exactly the new name.
    return latest != (new_key,)


def _changed_fields(existing: ExistingSection, row: NormalizedSection) -> dict[str, object]:
    changed: dict[str, object] = {}
    for name, value in section_values(row).items():
        if name in _IDENTITY_FIELDS:
            continue
        if existing.values.get(name) != value:
            changed[name] = value
    return changed


def build_sweep_plan(rows: Iterable[NormalizedSection], state: DbState) -> SweepPlan:
    """Diff in-scope rows against the database. Pure; returns change-only writes."""
    in_scope_rows = tuple(rows)
    inserts: list[SectionInsert] = []
    field_updates: dict[int, dict[str, object]] = {}
    instructor_appends: list[tuple[int, str]] = []
    snapshot_appends: list[tuple[int, SeatValues]] = []
    restores: list[int] = []
    unknown: dict[tuple[str, str], list[NormalizedSection]] = {}
    seen_crns: set[str] = set()

    for row in in_scope_rows:
        seen_crns.add(row.crn)
        existing = state.sections_by_crn.get(row.crn)
        if existing is None:
            course_id = state.course_ids.get((row.subject, row.course_number))
            if course_id is None:
                unknown.setdefault((row.subject, row.course_number), []).append(row)
                continue
            inserts.append(SectionInsert(row=row, course_id=course_id))
            continue

        changed = _changed_fields(existing, row)
        if changed:
            field_updates[existing.id] = changed
        if existing.removed_at is not None:
            restores.append(existing.id)
        if _instructor_changed(state.instructor_states.get(existing.id), row.instructor_raw):
            instructor_appends.append((existing.id, row.instructor_raw))
        seats = SeatValues.from_row(row)
        if state.latest_seats.get(existing.id) != seats:
            snapshot_appends.append((existing.id, seats))

    removals = tuple(
        section.id
        for crn, section in state.sections_by_crn.items()
        if section.in_scope and section.removed_at is None and crn not in seen_crns
    )
    return SweepPlan(
        records_seen=len(in_scope_rows),
        inserts=tuple(inserts),
        field_updates=field_updates,
        instructor_appends=tuple(instructor_appends),
        snapshot_appends=tuple(snapshot_appends),
        removals=removals,
        restores=tuple(restores),
        seen_crns=frozenset(seen_crns),
        unknown_course_keys={key: tuple(value) for key, value in unknown.items()},
    )


def missing_active_count(rows: Iterable[NormalizedSection], state: DbState) -> int:
    """Active in-scope database CRNs that the sweep does not list (input to the gate)."""
    seen = {row.crn for row in rows}
    return sum(
        1
        for crn, section in state.sections_by_crn.items()
        if section.in_scope and section.removed_at is None and crn not in seen
    )


def describe_unknown_courses(plan: SweepPlan) -> list[str]:
    """Sorted 'SUBJ NNNN' labels of in-scope courses that are not in Easy-A."""
    return sorted(f"{subject} {number}" for subject, number in plan.unknown_course_keys)
