from __future__ import annotations

import json
import logging
from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api import app as app_module
from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import Course, Section, Term
from easy_a.schema_guard import SchemaNotCurrentError

NOW = datetime(2026, 9, 1, tzinfo=UTC)


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


def _request_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.name == "easy_a.request"
    ]


def test_health_and_search_each_log_one_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="easy_a.request"):
        assert client.get("/health").status_code == 200
        health_lines = _request_lines(caplog)
        caplog.clear()
        assert client.get("/api/v1/rankings/search?term=202701").status_code == 200
        search_lines = _request_lines(caplog)

    assert len(health_lines) == 1
    assert health_lines[0]["event"] == "request"
    assert health_lines[0]["method"] == "GET"
    assert health_lines[0]["route"] == "/health"
    assert health_lines[0]["status"] == 200
    assert len(search_lines) == 1
    assert search_lines[0]["route"] == "/api/v1/rankings/search"
    assert search_lines[0]["status"] == 200
    duration = search_lines[0]["duration_ms"]
    assert isinstance(duration, int | float)
    assert duration >= 0
    assert set(search_lines[0]) == {"event", "method", "route", "status", "duration_ms"}


def test_unmatched_route_logs_placeholder_and_never_the_query(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="easy_a.request"):
        response = client.get("/does-not-exist?secret=x")
        lines = _request_lines(caplog)

    assert response.status_code == 404
    assert len(lines) == 1
    assert lines[0]["route"] == "unmatched"
    assert lines[0]["status"] == 404
    assert all(
        "secret" not in record.getMessage() and "does-not-exist" not in record.getMessage()
        for record in caplog.records
        if record.name == "easy_a.request"
    )


def test_request_logger_is_configured_for_info() -> None:
    assert logging.getLogger("easy_a.request").level == logging.INFO


def test_unhandled_error_logs_status_500_and_reraises(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    def boom() -> None:
        raise RuntimeError("kaboom")

    app.add_api_route("/__boom", boom)
    try:
        with caplog.at_level(logging.INFO, logger="easy_a.request"):
            with pytest.raises(RuntimeError):
                client.get("/__boom")
            lines = _request_lines(caplog)
    finally:
        app.router.routes.pop()

    assert len(lines) == 1
    assert lines[0]["route"] == "/__boom"
    assert lines[0]["status"] == 500


def _stale_engine() -> Engine:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sections (id INTEGER PRIMARY KEY, crn VARCHAR(16))"))
    return engine


def test_startup_refuses_a_schema_without_removed_at(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        app_module, "get_settings", lambda: SimpleNamespace(require_database_url=lambda: "unused")
    )
    monkeypatch.setattr(app_module, "_startup_engine", _stale_engine)
    app.dependency_overrides.clear()

    with pytest.raises(SchemaNotCurrentError) as excinfo, TestClient(app):
        pass

    assert "0004_sync_removed_at" in str(excinfo.value)


def test_startup_accepts_a_current_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(
        app_module, "get_settings", lambda: SimpleNamespace(require_database_url=lambda: "unused")
    )
    monkeypatch.setattr(app_module, "_startup_engine", lambda: engine)
    app.dependency_overrides.clear()

    with TestClient(app) as test_client:
        assert test_client.get("/health").json() == {"status": "ok"}


def test_startup_with_dependency_override_never_touches_the_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> Engine:
        raise AssertionError("engine must not be touched when the DB dependency is overridden")

    monkeypatch.setattr(app_module, "_startup_engine", fail)
    app.dependency_overrides[get_db_session] = lambda: None
    try:
        with TestClient(app) as test_client:
            assert test_client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_health_performs_no_database_access(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> Engine:
        raise AssertionError("/health must not open a database connection")

    monkeypatch.setattr(app_module, "_startup_engine", fail)
    app.dependency_overrides[get_db_session] = lambda: None
    try:
        with TestClient(app) as test_client:
            assert test_client.get("/health").json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()


def test_delivery_methods_exclude_methods_used_only_by_removed_sections(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    with session_factory() as session:
        term = Term(banner_code="202701", name="Spring 2027", year=2027, season="Spring")
        course = Course(
            subject="MAC", number="1105", title="College Algebra", catalog_edition="2026-2027"
        )
        session.add_all([term, course])
        session.flush()

        def _section(crn: str, delivery_method: str, removed_at: datetime | None) -> Section:
            return Section(
                term_id=term.id,
                crn=crn,
                course_id=course.id,
                section_number="001",
                campus="Tampa",
                session="Full",
                section_type="Lecture",
                primary_status="A",
                delivery_method=delivery_method,
                first_seen_at=NOW,
                last_seen_at=NOW,
                removed_at=removed_at,
            )

        session.add_all(
            [
                _section("10001", "HB", None),
                _section("10002", "OL", NOW),
            ]
        )
        session.commit()

    codes = [item["code"] for item in client.get("/api/v1/metadata/delivery-methods").json()]

    assert codes == ["HB"]
