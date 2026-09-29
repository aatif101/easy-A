from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.models import IngestRun, SeatSnapshot, Section, SectionInstructor
from easy_a.rankings.cache import SectionRankingCache
from easy_a.sync import sync_source
from easy_a.sync.runner import SweepStatus
from easy_a.sync.sweep import run_sweep
from tests.sync.sweep_support import (
    SWEEP_AT,
    TERM,
    enc_rows,
    naive,
    seed_from_rows,
    usf_client,
)
from tests.sync.wholeterm_html import RowSpec, build_whole_term_html


def _seed_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="Staff", enrollment=0, seats_remaining=135),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="20000", section="003", instructor="A. Smith"),
        *enc_rows(10),
    ]


def _response_rows() -> list[RowSpec]:
    return [
        RowSpec(crn="13173", instructor="J. Doe", enrollment=20, seats_remaining=115),
        RowSpec(crn="19410", section="002", instructor="Staff"),
        RowSpec(crn="21111", section="004", instructor="N. New"),
        RowSpec(crn="90001", subject="MAC", number="6000", section="001", title="Grad Algebra"),
        *enc_rows(10),
    ]


def test_sweep_applies_usf_state_in_one_transaction(
    session_factory: sessionmaker[Session],
) -> None:
    seed_from_rows(session_factory, _seed_rows())
    client, requests = usf_client(build_whole_term_html(_response_rows()))

    outcome = run_sweep(session_factory, term=TERM, client=client, now_fn=lambda: SWEEP_AT)

    assert len(requests) == 1
    assert outcome.status is SweepStatus.succeeded
    assert outcome.counts is not None
    assert outcome.counts.records_seen == 13
    assert outcome.counts.records_inserted == 1
    assert outcome.counts.records_updated == 2
    assert outcome.counts.records_failed == 0
    assert outcome.scope is not None
    assert outcome.scope["graduate_rows"] == 1

    with session_factory() as session:
        sections = {section.crn: section for section in session.scalars(select(Section))}
        assert sections["20000"].removed_at is not None
        assert sections["21111"].removed_at is None
        assert sections["13173"].removed_at is None
        # The graduate row is out of scope and never becomes a section.
        assert "90001" not in sections

        def instructor_rows(crn: str) -> list[str]:
            return list(
                session.scalars(
                    select(SectionInstructor.name_raw)
                    .where(SectionInstructor.section_id == sections[crn].id)
                    .order_by(SectionInstructor.id)
                )
            )

        def snapshots(crn: str) -> int:
            return len(
                session.scalars(
                    select(SeatSnapshot.id).where(SeatSnapshot.section_id == sections[crn].id)
                ).all()
            )

        assert instructor_rows("13173") == ["Staff", "J. Doe"]
        assert instructor_rows("21111") == ["N. New"]
        assert instructor_rows("19410") == ["Staff"]
        assert snapshots("13173") == 2
        assert snapshots("21111") == 1
        assert snapshots("19410") == 1

        sweep_time = naive(SWEEP_AT)
        seen = {"13173", "19410", "21111", *(str(30000 + i) for i in range(10))}
        for crn in seen:
            assert sections[crn].last_seen_at == sweep_time, crn
        assert sections["20000"].last_seen_at != sweep_time
        assert sections["21111"].first_seen_at == sweep_time

        cached = set(session.scalars(select(SectionRankingCache.crn)))
        assert "20000" not in cached
        assert {"13173", "19410", "21111"} <= cached

        run = session.scalar(select(IngestRun).order_by(IngestRun.id.desc()))
        assert run is not None
        assert run.source == sync_source(TERM)
        assert run.status == "succeeded"
        assert (
            run.records_seen,
            run.records_inserted,
            run.records_updated,
            run.records_failed,
        ) == (13, 1, 2, 0)
        assert run.error_message is None

    def override() -> object:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override
    try:
        with TestClient(app) as api:
            response = api.get("/api/v1/rankings/search", params={"term": TERM, "limit": 100})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    crns = {item["crn"] for item in response.json()["items"]}
    assert "20000" not in crns
    assert {"13173", "21111"} <= crns
