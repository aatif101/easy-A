"""The worker's between-sweep caches must never let a sweep diff against stale state."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.analytics.queries import GradeEvidenceCache
from easy_a.models import Section, SectionInstructor, Term
from easy_a.schedule.ingest import SCHEDULE_SOURCE
from easy_a.sync.apply import SweepStateCache, load_db_state
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    seed_from_rows,
    sweep_rows,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec

LATER = SWEEP_AT + timedelta(minutes=5)
LATEST = SWEEP_AT + timedelta(minutes=10)


def _baseline() -> list[RowSpec]:
    return [RowSpec(crn="13173", instructor="J. Doe"), *enc_rows(4)]


def _changed() -> list[RowSpec]:
    # An instructor change, a seat-only change, a structural field change and a new section.
    return [
        RowSpec(crn="13173", instructor="A. Smith"),
        *enc_rows(1, wait=5),
        *enc_rows(1, start_crn=30001, delivery="AD"),
        *enc_rows(2, start_crn=30002),
        *enc_rows(1, start_crn=30010),
    ]


def _assert_cache_matches_database(
    session_factory: sessionmaker[Session], cache: SweepStateCache
) -> None:
    with session_factory() as session:
        term = session.scalars(select(Term).where(Term.banner_code == TERM)).one()
        fresh = load_db_state(session, term.id, (), term_code=TERM)
        cached = load_db_state(session, term.id, (), term_code=TERM, cache=cache)
    assert cache.last_load_reused is True
    assert cached == fresh


def test_cached_state_matches_a_fresh_read_after_every_kind_of_change(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _baseline())
    cache = SweepStateCache()
    evidence = GradeEvidenceCache()

    first, _ = sweep_rows(session_factory, _baseline(), state_cache=cache, evidence_cache=evidence)
    second, _ = sweep_rows(
        session_factory, _changed(), at=LATER, state_cache=cache, evidence_cache=evidence
    )

    assert first.extra["state_reused"] is False
    assert second.status is SweepStatus.succeeded
    assert second.extra["state_reused"] is True
    assert second.counts is not None
    assert second.counts.records_inserted == 1
    assert cache.full_loads == 1
    _assert_cache_matches_database(session_factory, cache)

    third, _ = sweep_rows(
        session_factory, _changed(), at=LATEST, state_cache=cache, evidence_cache=evidence
    )
    assert third.extra["state_reused"] is True
    assert third.counts is not None
    assert (third.counts.records_inserted, third.counts.records_updated) == (0, 0)
    assert cache.full_loads == 1


def test_another_writer_forces_a_full_reload(session_factory: sessionmaker[Session]) -> None:
    seed_from_rows(session_factory, _baseline())
    cache = SweepStateCache()
    sweep_rows(session_factory, _baseline(), state_cache=cache)
    with session_factory.begin() as session:
        section = session.scalars(select(Section).where(Section.crn == "13173")).one()
        session.add(
            SectionInstructor(
                section_id=section.id,
                name_raw="X. Operator",
                name_normalized=None,
                source=SCHEDULE_SOURCE,
                observed_at=SWEEP_AT,
            )
        )

    outcome, _ = sweep_rows(session_factory, _baseline(), at=LATER, state_cache=cache)

    assert outcome.extra["state_reused"] is False
    assert cache.full_loads == 2
    # The full reload saw the operator's row, so the sweep restored the USF name.
    assert outcome.extra["instructor_changes"] == 1


def test_a_failed_sweep_drops_the_cached_state(session_factory: sessionmaker[Session]) -> None:
    seed_from_rows(session_factory, _baseline())
    cache = SweepStateCache()
    sweep_rows(session_factory, _baseline(), state_cache=cache)
    client, _ = usf_client(status_code=503)

    failed = run_sweep(
        session_factory, term=TERM, client=client, now_fn=lambda: LATER, state_cache=cache
    )
    after, _ = sweep_rows(session_factory, _baseline(), at=LATEST, state_cache=cache)

    assert failed.status is SweepStatus.failed
    assert after.extra["state_reused"] is False
    assert cache.full_loads == 2


def test_cached_state_older_than_max_age_is_reloaded(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _baseline())
    now = [0.0]
    cache = SweepStateCache(max_age_seconds=60, clock=lambda: now[0])
    sweep_rows(session_factory, _baseline(), state_cache=cache)
    now[0] = 30.0
    reused, _ = sweep_rows(session_factory, _baseline(), at=LATER, state_cache=cache)
    now[0] = 61.0
    expired, _ = sweep_rows(session_factory, _baseline(), at=LATEST, state_cache=cache)

    assert reused.extra["state_reused"] is True
    assert expired.extra["state_reused"] is False
    assert cache.full_loads == 2


def test_a_dry_run_never_uses_the_state_cache(session_factory: sessionmaker[Session]) -> None:
    seed_from_rows(session_factory, _baseline())
    cache = SweepStateCache()

    outcome, _ = sweep_rows(session_factory, _changed(), dry_run=True, state_cache=cache)

    assert outcome.status is SweepStatus.dry_run
    assert cache.full_loads == 0
