from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.api.app import app
from easy_a.api.dependencies import get_db_session
from easy_a.db import Base
from easy_a.models import Course, Section, Term
from easy_a.rankings.cache import refresh_section_rankings

spec = importlib.util.spec_from_file_location(
    "verify_rankings_pages",
    Path(__file__).resolve().parents[2] / "scripts/verify_rankings_pages.py",
)
assert spec is not None and spec.loader is not None
verify = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = verify
spec.loader.exec_module(verify)

TERM = "202701"
NOW = datetime(2026, 9, 1, tzinfo=UTC)


def _crn(i: int) -> str:
    return f"{i:05d}"


def _make_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


def _seed_sections(
    session: Session,
    *,
    count: int,
    term_code: str = TERM,
    campuses: list[str] | None = None,
) -> None:
    term = Term(id=1, banner_code=term_code, name="Spring 2027", year=2027, season="Spring")
    course = Course(
        id=1,
        subject="MAC",
        number="1105",
        title="Test Course",
        catalog_edition="2026-2027",
    )
    session.add_all([term, course])
    session.flush()
    for i in range(count):
        campus = campuses[i] if campuses is not None else "Tampa"
        session.add(
            Section(
                term_id=term.id,
                crn=_crn(i),
                course_id=course.id,
                section_number=f"{i + 1:03d}",
                campus=campus,
                session="Full Term",
                section_type="Class Lecture",
                primary_status="Active",
                first_seen_at=NOW,
                last_seen_at=NOW,
            )
        )
    session.flush()
    refresh_section_rankings(session, term=term_code)
    session.commit()


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = _make_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def api_client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_seeded_three_section_walk_at_page_size_two_yields_pass(
    session_factory: sessionmaker[Session],
    api_client: TestClient,
) -> None:
    with session_factory() as session:
        _seed_sections(session, count=3)

    with session_factory() as session:
        stored = verify.stored_identities(session, term=TERM)

    scan = verify.scan_pages(api_client, TERM, 2)
    verdict = verify.reconcile(stored, scan)

    assert verdict.verdict == "PASS"
    assert len(stored.identities) == 3
    assert scan.api_total == 3
    assert scan.pages_fetched == 2
    assert len(verdict.missing) == 0
    assert len(verdict.extra) == 0
    assert len(verdict.duplicates) == 0


def test_omitted_stored_crn_yields_identity_mismatch(
    session_factory: sessionmaker[Session],
    api_client: TestClient,
) -> None:
    with session_factory() as session:
        _seed_sections(session, count=3)

    with session_factory() as session:
        stored = verify.stored_identities(session, term=TERM)

    full = api_client.get(
        "/api/v1/rankings/search",
        params={"term": TERM, "sort": "course", "limit": 200, "offset": 0},
    ).json()
    omitted_crn = full["items"][0]["crn"]
    omitted_items = full["items"][1:]
    payload = {**full, "items": omitted_items, "total": len(omitted_items)}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:8000"
    ) as mock_client:
        scan = verify.scan_pages(mock_client, TERM, 200)

    verdict = verify.reconcile(stored, scan)

    assert verdict.verdict == "FAIL"
    assert verdict.reason == "identity_mismatch"
    assert omitted_crn in verdict.missing


def test_connection_error_yields_not_measured_exit_3(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = _make_engine()
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        _seed_sections(session, count=1)

    monkeypatch.setattr(verify, "get_engine", lambda: engine)

    def raise_connect_error(*_args: object, **_kwargs: object) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(verify, "scan_pages", raise_connect_error)

    exit_code = verify.main(["--term", TERM, "--http-base-url", "http://127.0.0.1:8000"])

    assert exit_code == 3
    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "NOT MEASURED"
    assert output["gate"] == "api_identity"
