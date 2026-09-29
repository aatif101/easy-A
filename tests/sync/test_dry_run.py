from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.models import Section, SectionInstructor
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    section_marks,
    seed_from_rows,
    sweep_rows,
    table_counts,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html


def _seed_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="Staff"),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="20000", section="003", instructor="A. Smith"),
        *enc_rows(10),
    ]


def _response_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="J. Doe", enrollment=20, seats_remaining=115),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="21111", section="004", instructor="N. New"),
        RowSpec(crn="55555", subject="PSY", number="1012", section="001", instructor="Kim"),
        RowSpec(crn="90001", subject="MAC", number="6000", section="001", title="Grad"),
        *enc_rows(10),
    ]


def _instructor_names(session_factory: sessionmaker[Session]) -> list[tuple[int, str]]:
    with session_factory() as session:
        return list(
            session.execute(
                select(SectionInstructor.section_id, SectionInstructor.name_raw).order_by(
                    SectionInstructor.id
                )
            ).tuples()
        )


def test_dry_run_writes_nothing_and_reports_what_a_real_sweep_then_applies(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    counts_before = table_counts(session_factory)
    marks_before = section_marks(session_factory)
    instructors_before = _instructor_names(session_factory)
    adder_calls: list[object] = []
    client, requests = usf_client(build_whole_term_html(_response_rows()))

    dry = run_sweep(
        session_factory,
        term=TERM,
        client=client,
        now_fn=lambda: SWEEP_AT,
        dry_run=True,
        course_adder=lambda *args, **kwargs: adder_calls.append(args),
    )

    assert len(requests) == 1
    assert dry.status is SweepStatus.dry_run
    assert adder_calls == []
    assert table_counts(session_factory) == counts_before
    assert section_marks(session_factory) == marks_before
    assert _instructor_names(session_factory) == instructors_before
    assert dry.scope is not None
    assert dry.scope["graduate_rows"] == 1
    assert dry.would_add == ("PSY 1012",)
    assert dry.counts is not None

    real, _ = sweep_rows(session_factory, _response_rows(), at=SWEEP_AT + timedelta(minutes=1))

    assert real.status is SweepStatus.succeeded
    assert real.counts == dry.counts
    assert real.unknown_course_keys == ("PSY 1012",)
    with session_factory() as session:
        assert session.scalar(select(Section).where(Section.crn == "55555")) is None


def test_dry_run_gate_failure_is_reported_without_any_write(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    counts_before = table_counts(session_factory)

    outcome, requests = sweep_rows(session_factory, _seed_rows()[6:], dry_run=True)

    assert len(requests) == 1
    assert outcome.status is SweepStatus.failed
    assert outcome.error_kind == "gate"
    assert table_counts(session_factory) == counts_before


def test_dry_run_last_seen_and_instructors_are_untouched(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    with session_factory() as session:
        before: dict[str, datetime] = {
            section.crn: section.last_seen_at for section in session.scalars(select(Section))
        }

    sweep_rows(session_factory, _response_rows(), dry_run=True)

    with session_factory() as session:
        after = {section.crn: section.last_seen_at for section in session.scalars(select(Section))}
    assert after == before


@pytest.mark.parametrize("dry_run", [True, False])
def test_each_sweep_issues_exactly_one_request(
    session_factory: sessionmaker[Session], dry_run: bool
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    _, requests = sweep_rows(session_factory, _response_rows(), dry_run=dry_run)
    assert len(requests) == 1
