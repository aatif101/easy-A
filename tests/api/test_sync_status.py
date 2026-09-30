from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.api.routes import metadata
from easy_a.db import Base
from easy_a.models import IngestRun

OUTSIDE_NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
IN_WINDOW_NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
SOURCE = "usf_schedule_sync:202701"
URL = "/api/v1/metadata/sync-status?term=202701"


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _pin_now(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    monkeypatch.setattr(metadata, "_now", lambda: now)


def _add_run(
    factory: sessionmaker[Session],
    *,
    status: str,
    started_at: datetime,
    source: str = SOURCE,
    error_message: str | None = None,
    records_failed: int = 0,
) -> None:
    finished = started_at + timedelta(seconds=20)
    with factory() as session:
        session.add(
            IngestRun(
                source=source,
                started_at=started_at,
                finished_at=finished,
                status=status,
                records_failed=records_failed,
                error_message=error_message,
            )
        )
        session.commit()


def test_no_runs_reports_nulls_and_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)

    response = client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["term"] == "202701"
    assert body["last_success_at"] is None
    assert body["last_run_at"] is None
    assert body["last_status"] is None
    assert body["last_error_kind"] is None
    assert body["last_records_failed"] is None
    assert body["failures_last_24h"] == 0
    assert body["is_stale"] is True
    assert body["in_registration_window"] is False
    assert body["cadence_seconds"] == 3600
    assert body["stale_after_seconds"] == 7200
    assert body["as_of"].startswith("2026-10-15T12:00:00")
    assert set(body) == {
        "term",
        "last_success_at",
        "last_run_at",
        "last_status",
        "last_error_kind",
        "last_records_failed",
        "failures_last_24h",
        "in_registration_window",
        "cadence_seconds",
        "stale_after_seconds",
        "is_stale",
        "as_of",
    }


def test_recent_success_outside_window_is_fresh(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    _add_run(session_factory, status="succeeded", started_at=OUTSIDE_NOW - timedelta(minutes=3))

    body = client.get(URL).json()

    assert body["is_stale"] is False
    assert body["cadence_seconds"] == 3600
    assert body["stale_after_seconds"] == 7200
    assert body["last_status"] == "succeeded"
    assert body["last_error_kind"] is None
    assert body["last_success_at"] is not None
    assert body["last_run_at"] is not None


def test_three_hour_old_success_is_stale(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    _add_run(session_factory, status="succeeded", started_at=OUTSIDE_NOW - timedelta(hours=3))

    assert client.get(URL).json()["is_stale"] is True


def test_success_inside_window_uses_five_minute_cadence(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, IN_WINDOW_NOW)
    _add_run(session_factory, status="succeeded", started_at=IN_WINDOW_NOW - timedelta(minutes=11))

    body = client.get(URL).json()

    assert body["in_registration_window"] is True
    assert body["cadence_seconds"] == 300
    assert body["stale_after_seconds"] == 600
    assert body["is_stale"] is True


def test_failed_run_reports_kind_without_leaking_error_text(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    _add_run(session_factory, status="succeeded", started_at=OUTSIDE_NOW - timedelta(minutes=30))
    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(minutes=5),
        error_message="database: connection to server at db.example.internal port 6543 failed",
        records_failed=7,
    )

    response = client.get(URL)
    body = response.json()

    assert body["last_status"] == "failed"
    assert body["last_error_kind"] == "database"
    assert body["last_records_failed"] == 7
    assert body["failures_last_24h"] == 1
    assert body["is_stale"] is False
    assert "6543" not in response.text
    assert "db.example.internal" not in response.text
    assert "connection to server" not in response.text


def test_unknown_error_prefix_maps_to_unexpected(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(minutes=5),
        error_message="secret-host.internal: boom",
    )
    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(minutes=2),
        error_message=None,
    )

    response = client.get(URL)

    assert response.json()["last_error_kind"] == "unexpected"
    assert "secret-host" not in response.text

    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(minutes=1),
        error_message="secret-host.internal: boom",
    )
    latest = client.get(URL)
    assert latest.json()["last_error_kind"] == "unexpected"
    assert "secret-host" not in latest.text


def test_failures_older_than_24_hours_are_not_counted(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(hours=25),
        error_message="usf_http: 503",
    )
    _add_run(
        session_factory,
        status="failed",
        started_at=OUTSIDE_NOW - timedelta(hours=2),
        error_message="usf_http: 503",
    )

    assert client.get(URL).json()["failures_last_24h"] == 1


def test_other_sources_and_terms_are_ignored(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_now(monkeypatch, OUTSIDE_NOW)
    recent = OUTSIDE_NOW - timedelta(minutes=1)
    _add_run(session_factory, status="succeeded", started_at=recent, source="other_source")
    _add_run(
        session_factory,
        status="failed",
        started_at=recent,
        source="usf_schedule_sync:202608",
        error_message="usf_http: 503",
    )

    body = client.get(URL).json()

    assert body["last_run_at"] is None
    assert body["last_success_at"] is None
    assert body["failures_last_24h"] == 0
    assert body["is_stale"] is True


def test_bad_term_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/metadata/sync-status?term=bad").status_code == 422
    assert client.get("/api/v1/metadata/sync-status").status_code == 422
