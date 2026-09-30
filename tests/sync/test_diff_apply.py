from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from easy_a.common.instructors import CurrentInstructorState, CurrentInstructorStatus
from easy_a.models import IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.schedule.ingest import _section_values
from easy_a.schedule.normalize import NormalizedSection, normalize_schedule_row
from easy_a.schedule.parser import EXPECTED_HEADERS, parse_schedule_html
from easy_a.sync import apply as apply_module
from easy_a.sync.plan import (
    SECTION_FIELDS,
    DbState,
    ExistingSection,
    SeatValues,
    build_sweep_plan,
    normalize_instructor_name,
)
from easy_a.sync.runner import SweepStatus
from tests.sync.sweep_support import (
    SEED_AT,
    SWEEP_AT,
    count,
    enc_rows,
    naive,
    section_marks,
    seed_from_rows,
    sweep_rows,
)
from tests.sync.wholeterm_html import RowSpec, row_html

LATER = SWEEP_AT + timedelta(minutes=5)


def _normalized(spec: RowSpec) -> NormalizedSection:
    html = (
        "<table><tr>"
        + "".join(f"<th>{name}</th>" for name in EXPECTED_HEADERS)
        + "</tr>"
        + row_html(spec)
        + "</table>"
    )
    return normalize_schedule_row(parse_schedule_html(html)[0])


def _state(
    row: NormalizedSection,
    *,
    instructor: CurrentInstructorState | None,
    seats: SeatValues | None,
    removed_at: datetime | None = None,
    values_override: dict[str, object] | None = None,
) -> DbState:
    values = dict(_section_values(row))
    values.update(values_override or {})
    existing = ExistingSection(
        id=1,
        crn=row.crn,
        course_id=10,
        removed_at=removed_at,
        in_scope=True,
        values=values,
    )
    return DbState(
        sections_by_crn={row.crn: existing},
        instructor_states={} if instructor is None else {1: instructor},
        latest_seats={1: seats},
        course_ids={(row.subject, row.course_number): 10},
        active_in_scope_count=1,
        active_subjects=frozenset({row.subject}),
        last_success_records_seen=None,
    )


def _resolved(name: str) -> CurrentInstructorState:
    return CurrentInstructorState(
        name=name,
        status=CurrentInstructorStatus.resolved,
        latest_observed_at=SEED_AT,
        latest_names=(name,),
    )


def test_section_fields_match_the_schedule_ingest_mapping() -> None:
    assert tuple(_section_values(_normalized(RowSpec()))) == SECTION_FIELDS


def test_identical_state_is_an_empty_plan() -> None:
    row = _normalized(RowSpec(instructor="J. Doe"))
    plan = build_sweep_plan(
        [row],
        _state(row, instructor=_resolved("J. Doe"), seats=SeatValues.from_row(row)),
    )
    assert plan.field_updates == {}
    assert plan.instructor_appends == ()
    assert plan.snapshot_appends == ()
    assert plan.structural_change is False
    assert plan.counts().records_updated == 0


def test_name_differing_only_by_whitespace_or_case_is_not_a_change() -> None:
    assert normalize_instructor_name("  j.   DOE ") == normalize_instructor_name("J. Doe")
    row = _normalized(RowSpec(instructor="J.  DOE"))
    plan = build_sweep_plan(
        [row],
        _state(row, instructor=_resolved("j. doe"), seats=SeatValues.from_row(row)),
    )
    assert plan.instructor_appends == ()


@pytest.mark.parametrize(
    "state",
    [
        None,
        CurrentInstructorState(None, CurrentInstructorStatus.no_observations, None, ()),
        CurrentInstructorState(None, CurrentInstructorStatus.blank_latest_state, SEED_AT, ()),
        CurrentInstructorState(
            None, CurrentInstructorStatus.ambiguous_latest_state, SEED_AT, ("A. One", "B. Two")
        ),
    ],
)
def test_unusable_latest_states_append_one_row_for_a_named_instructor(
    state: CurrentInstructorState | None,
) -> None:
    row = _normalized(RowSpec(instructor="J. Doe"))
    plan = build_sweep_plan([row], _state(row, instructor=state, seats=SeatValues.from_row(row)))
    assert plan.instructor_appends == ((1, "J. Doe"),)
    assert plan.structural_change is True


def test_ambiguous_state_whose_latest_names_equal_the_new_name_appends_nothing() -> None:
    row = _normalized(RowSpec(instructor="J. Doe"))
    state = CurrentInstructorState(
        None, CurrentInstructorStatus.ambiguous_latest_state, SEED_AT, ("J. Doe",)
    )
    plan = build_sweep_plan([row], _state(row, instructor=state, seats=SeatValues.from_row(row)))
    assert plan.instructor_appends == ()


def test_section_without_a_snapshot_gets_one() -> None:
    row = _normalized(RowSpec(instructor="J. Doe"))
    plan = build_sweep_plan([row], _state(row, instructor=_resolved("J. Doe"), seats=None))
    assert plan.snapshot_appends == ((1, SeatValues.from_row(row)),)
    assert plan.structural_change is False


def test_delivery_method_change_is_a_structural_field_update() -> None:
    row = _normalized(RowSpec(instructor="J. Doe", delivery="AD"))
    plan = build_sweep_plan(
        [row],
        _state(
            row,
            instructor=_resolved("J. Doe"),
            seats=SeatValues.from_row(row),
            values_override={"delivery_method": "CL"},
        ),
    )
    assert plan.field_updates == {1: {"delivery_method": "AD"}}
    assert plan.structural_change is True


def test_seat_only_change_is_not_structural() -> None:
    row = _normalized(RowSpec(instructor="J. Doe", wait=4))
    plan = build_sweep_plan(
        [row],
        _state(
            row,
            instructor=_resolved("J. Doe"),
            seats=SeatValues.from_row(row),
            values_override={"wait_seats_available": 0},
        ),
    )
    assert set(plan.field_updates[1]) == {"wait_seats_available"}
    assert plan.structural_change is False


def test_unknown_course_row_is_reported_not_inserted() -> None:
    row = _normalized(RowSpec(crn="55555", subject="PSY", number="1012", instructor="X"))
    state = DbState(
        sections_by_crn={},
        instructor_states={},
        latest_seats={},
        course_ids={},
        active_in_scope_count=0,
        active_subjects=frozenset(),
        last_success_records_seen=None,
    )
    plan = build_sweep_plan([row], state)
    assert plan.inserts == ()
    assert plan.unknown_course_keys == {("PSY", "1012"): (row,)}
    assert plan.counts().records_failed == 1


def _instructor_and_snapshot_counts(session_factory: sessionmaker[Session]) -> tuple[int, int]:
    with session_factory() as session:
        return count(session, SectionInstructor), count(session, SeatSnapshot)


def test_repeated_sweeps_of_an_unchanged_term_append_nothing(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(4)]
    seed_from_rows(session_factory, rows)

    first, _ = sweep_rows(session_factory, rows, at=SWEEP_AT)
    before = _instructor_and_snapshot_counts(session_factory)
    second, _ = sweep_rows(session_factory, rows, at=LATER)
    after = _instructor_and_snapshot_counts(session_factory)

    assert first.status is SweepStatus.succeeded
    assert second.status is SweepStatus.succeeded
    assert before == (5, 5)
    assert after == before
    assert second.counts is not None
    assert second.counts.records_updated == 0
    assert second.counts.records_inserted == 0
    with session_factory() as session:
        seen = {section.last_seen_at for section in session.scalars(select(Section))}
    assert seen == {naive(LATER)}


def test_seat_only_sweep_appends_a_snapshot_and_does_not_rebuild_rankings(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe", wait=0), *enc_rows(3)]
    seed_from_rows(session_factory, rows)
    calls: list[object] = []
    monkeypatch.setattr(
        apply_module, "refresh_section_rankings", lambda *args, **kwargs: calls.append(kwargs)
    )

    changed = [RowSpec(crn="13173", instructor="J. Doe", wait=3), *enc_rows(3)]
    outcome, _ = sweep_rows(session_factory, changed)

    assert outcome.counts is not None
    assert outcome.counts.records_updated == 1
    assert calls == []
    with session_factory() as session:
        assert count(session, SeatSnapshot) == 5
        assert count(session, SectionInstructor) == 4
        section = session.scalar(select(Section).where(Section.crn == "13173"))
        assert section is not None
        assert section.wait_seats_available == 3


def test_delivery_method_change_updates_the_section_and_rebuilds_rankings(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe", delivery="CL"), *enc_rows(3)]
    seed_from_rows(session_factory, rows)
    calls: list[object] = []
    monkeypatch.setattr(
        apply_module, "refresh_section_rankings", lambda *args, **kwargs: calls.append(kwargs)
    )

    outcome, _ = sweep_rows(
        session_factory, [RowSpec(crn="13173", instructor="J. Doe", delivery="AD"), *enc_rows(3)]
    )

    assert outcome.status is SweepStatus.succeeded
    assert calls == [{"term": "202701"}]
    with session_factory() as session:
        section = session.scalar(select(Section).where(Section.crn == "13173"))
        assert section is not None
        assert section.delivery_method == "AD"
        # Delivery change appends no history rows.
        assert count(session, SectionInstructor) == 4
        assert count(session, SeatSnapshot) == 4


def test_removed_section_that_reappears_is_restored_and_rebuilds_rankings(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(9)]
    seed_from_rows(session_factory, rows)
    with session_factory.begin() as session:
        session.execute(
            update(Section).where(Section.crn == "13173").values(removed_at=naive(SEED_AT))
        )
    calls: list[object] = []
    monkeypatch.setattr(
        apply_module, "refresh_section_rankings", lambda *args, **kwargs: calls.append(kwargs)
    )

    outcome, _ = sweep_rows(session_factory, rows)

    assert outcome.counts is not None
    assert outcome.counts.records_updated == 1
    assert calls != []
    assert section_marks(session_factory)["13173"][0] is None


def test_unknown_course_rows_are_counted_and_named_never_dropped(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(9)]
    seed_from_rows(session_factory, rows)
    unknown = [
        RowSpec(crn="55555", subject="PSY", number="1012", section="001", instructor="Kim"),
        RowSpec(crn="55556", subject="PSY", number="1012", section="002", instructor="Kim"),
    ]

    outcome, _ = sweep_rows(session_factory, [*rows, *unknown])

    assert outcome.status is SweepStatus.succeeded
    assert outcome.counts is not None
    assert outcome.counts.records_seen == 12
    assert outcome.counts.records_inserted == 0
    assert outcome.counts.records_failed == 2
    assert outcome.unknown_course_keys == ("PSY 1012",)
    with session_factory() as session:
        assert session.scalar(select(Section).where(Section.crn == "55555")) is None
        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.records_failed == 2
        assert run.error_message is not None
        assert "PSY 1012" in run.error_message


def test_new_section_of_a_known_course_is_inserted_with_history(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(9)]
    seed_from_rows(session_factory, rows)

    outcome, _ = sweep_rows(
        session_factory, [*rows, RowSpec(crn="21111", section="009", instructor="N. New")]
    )

    assert outcome.counts is not None
    assert outcome.counts.records_inserted == 1
    with session_factory() as session:
        section = session.scalar(select(Section).where(Section.crn == "21111"))
        assert section is not None
        assert section.first_seen_at == section.last_seen_at == naive(SWEEP_AT)
        assert section.removed_at is None


def test_section_missing_a_snapshot_gets_one_from_the_sweep(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(9)]
    seed_from_rows(session_factory, rows)
    with session_factory.begin() as session:
        section_id = session.scalar(select(Section.id).where(Section.crn == "13173"))
        session.execute(delete(SeatSnapshot).where(SeatSnapshot.section_id == section_id))

    sweep_rows(session_factory, rows)

    with session_factory() as session:
        assert count(session, SeatSnapshot) == 10


def test_instructor_comparison_ignores_the_name_normalized_column(
    session_factory: sessionmaker[Session],
) -> None:
    rows = [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(9)]
    seed_from_rows(session_factory, rows)
    with session_factory.begin() as session:
        session.execute(update(SectionInstructor).values(name_normalized="unrelated value"))

    sweep_rows(session_factory, rows)

    with session_factory() as session:
        assert count(session, SectionInstructor) == 10


def test_last_seen_bulk_update_is_chunked_across_a_large_term(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = enc_rows(2500, start_crn=40000)
    seed_from_rows(session_factory, rows, refresh_cache=False)
    original = apply_module._bulk_section_update
    last_seen_updates: list[int] = []

    def spy(session: Session, where: object, **values: object) -> None:
        if "last_seen_at" in values:
            last_seen_updates.append(1)
        original(session, where, **values)

    monkeypatch.setattr(apply_module, "_bulk_section_update", spy)

    outcome, requests = sweep_rows(session_factory, rows, at=LATER)

    assert len(requests) == 1
    assert outcome.status is SweepStatus.succeeded
    assert outcome.counts is not None
    assert outcome.counts.records_updated == 0
    with session_factory() as session:
        stamps = set(session.scalars(select(Section.last_seen_at)))
    assert stamps == {naive(LATER)}
    assert len(last_seen_updates) == 3

