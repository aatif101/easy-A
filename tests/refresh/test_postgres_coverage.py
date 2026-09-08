from __future__ import annotations

import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from easy_a.db import Base
from easy_a.models import Course, SeatSnapshot
from easy_a.rankings import rank_section
from easy_a.refresh.coverage import coverage_metadata, refresh_targets
from easy_a.refresh.targets import load_targets
from tests.refresh.test_targets import NOW, schedule


def test_postgres_coverage_and_latest_snapshot() -> None:
    url = os.environ.get("EASY_A_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    schema = "sprint5_" + uuid4().hex
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            Base.metadata.create_all(connection)
            with Session(bind=connection) as session:
                session.add(
                    Course(
                        subject="MAC", number="1105", title="Algebra", catalog_edition="2026-2027"
                    )
                )
                session.flush()
                config = load_targets()
                for observed in (NOW, NOW + timedelta(minutes=1)):
                    refresh_targets(
                        session,
                        term="202701",
                        config=config,
                        subject="MAC",
                        search=schedule,
                        observed_at=observed,
                    )
                rows = coverage_metadata(session, "202701", config.targets)
                assert rows[0].section_count == 2
                assert rows[0].latest_observed_at == NOW + timedelta(minutes=1)
                assert len(list(session.scalars(select(SeatSnapshot)))) == 4
                # Equal timestamps use the snapshot id as a deterministic tie-breaker.
                ranking = rank_section(session, term="202701", crn="13173")
                snapshot = session.scalars(select(SeatSnapshot).order_by(SeatSnapshot.id)).first()
                assert snapshot is not None
                session.add(
                    SeatSnapshot(
                        section_id=snapshot.section_id,
                        observed_at=NOW + timedelta(minutes=1),
                        seats_remaining=7,
                    )
                )
                session.flush()
                latest = rank_section(session, term="202701", crn="13173")
                assert latest.seats_remaining == 7
                assert latest.seats.observed_at == NOW + timedelta(minutes=1)
                assert latest.historical_analytics == ranking.historical_analytics
            transaction.rollback()
    finally:
        engine.dispose()
