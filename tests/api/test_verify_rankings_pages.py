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


def _provenance(source: str = "sections", freshness: str = "current") -> dict[str, object]:
    return {"freshness": freshness, "source": source, "source_term": TERM, "detail": None}


def _item(
    crn: str,
    *,
    subject: str = "MAC",
    course_number: str = "1105",
    score_source: str = "course",
    effective_n: float = 10.0,
) -> dict[str, object]:
    return {
        "term": TERM,
        "term_name": "Spring 2027",
        "crn": crn,
        "subject": subject,
        "course_number": course_number,
        "course_title": "Test Course",
        "instructor": None,
        "instructor_provenance": _provenance("section_instructors", "unavailable"),
        "modality": {
            "delivery_method": None,
            "delivery_label": None,
            "provenance": _provenance("sections.delivery_method"),
        },
        "seats_remaining": None,
        "seats": {
            "observed_at": None,
            "freshness": "unavailable",
            "age_seconds": None,
            "capacity": None,
            "enrollment": None,
            "seats_remaining": None,
            "wait_seats_available": None,
            "provenance": _provenance(
                "seat_snapshots/sections.current_seat_fields", "unavailable"
            ),
        },
        "gened_attributes": [],
        "gened_provenance": _provenance("course_attributes"),
        "easiness_score": 5.0,
        "smoothed_withdrawal_rate": 0.1,
        "confidence_label": "low",
        "effective_n": effective_n,
        "score_source": score_source,
        "historical_analytics": {
            "easiness_score": 5.0,
            "smoothed_withdrawal_rate": 0.1,
            "confidence_label": "low",
            "effective_n": effective_n,
            "score_source": score_source,
            "prior_level": "global" if score_source == "global" else "course",
            "completed_grade_count": 0,
            "total_grade_count": 0,
            "withdrawal_count": 0,
            "section_count": 0,
            "term_count": 0,
            "mapped_instructor_section_count": 0,
            "provenance": _provenance("grade_distributions", "unavailable"),
        },
        "signals": [],
        "signal_provenance": _provenance("schedule/syllabi", "unavailable"),
        "section_provenance": _provenance("sections"),
    }


def _mock_client(pages: dict[int, dict[str, object]]) -> httpx.Client:
    """pages maps offset -> {"total": int, "items": [...]} or {"status": 500} or
    {"malformed": True}. An offset not present in the map returns an empty page."""

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params.get("offset", "0"))
        limit = int(request.url.params.get("limit", "200"))
        page = pages.get(offset)
        if page is None:
            return httpx.Response(
                200, json={"items": [], "total": 0, "limit": limit, "offset": offset}
            )
        if page.get("status") is not None:
            return httpx.Response(int(page["status"]), json={})  # type: ignore[arg-type]
        if page.get("malformed"):
            return httpx.Response(200, content=b"not json")
        return httpx.Response(
            200,
            json={
                "items": page["items"],
                "total": page["total"],
                "limit": page.get("limit", limit),
                "offset": offset,
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://127.0.0.1:8000")


def test_exactly_page_size_rows_scans_one_page_with_no_overlap() -> None:
    items = [_item(_crn(i)) for i in range(200)]
    with _mock_client({0: {"total": 200, "items": items}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    stored = verify.StoredSnapshot(
        identities=frozenset(_crn(i) for i in range(200)), cache_count=200, non_tampa_count=0
    )
    verdict = verify.reconcile(stored, scan)

    assert scan.reason is None
    assert scan.pages_fetched == 1
    assert verdict.verdict == "PASS"


def test_one_row_past_page_size_yields_second_page_of_exactly_one() -> None:
    page0 = [_item(_crn(i)) for i in range(200)]
    page1 = [_item(_crn(200))]
    with _mock_client(
        {0: {"total": 201, "items": page0}, 200: {"total": 201, "items": page1}}
    ) as client:
        scan = verify.scan_pages(client, TERM, 200)

    stored = verify.StoredSnapshot(
        identities=frozenset(_crn(i) for i in range(201)), cache_count=201, non_tampa_count=0
    )
    verdict = verify.reconcile(stored, scan)

    assert scan.reason is None
    assert scan.pages_fetched == 2
    assert verdict.verdict == "PASS"


def test_empty_term_yields_pass_with_zero_stored_and_one_page() -> None:
    with _mock_client({0: {"total": 0, "items": []}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    stored = verify.StoredSnapshot(identities=frozenset(), cache_count=0, non_tampa_count=0)
    verdict = verify.reconcile(stored, scan)

    assert scan.reason is None
    assert scan.pages_fetched == 1
    assert verdict.verdict == "PASS"
    assert len(stored.identities) == 0


def test_short_non_final_page_fails_with_short_page_reason() -> None:
    page0 = [_item(_crn(0)), _item(_crn(1))]
    page1 = [_item(_crn(2))]  # total says 5, but only 1 more item is returned
    with _mock_client(
        {0: {"total": 5, "items": page0}, 2: {"total": 5, "items": page1}}
    ) as client:
        scan = verify.scan_pages(client, TERM, 2)

    assert scan.reason == "short_page"


def test_duplicate_crn_across_adjacent_pages_fails_with_duplicate_identity() -> None:
    page0 = [_item(_crn(0)), _item(_crn(1))]
    page1 = [_item(_crn(1))]  # repeats the last identity of page0
    with _mock_client(
        {0: {"total": 3, "items": page0}, 2: {"total": 3, "items": page1}}
    ) as client:
        scan = verify.scan_pages(client, TERM, 2)

    assert scan.reason == "duplicate_identity"


def test_substituted_crn_same_count_yields_identity_mismatch() -> None:
    items = [_item(_crn(0)), _item(_crn(1)), _item(_crn(9))]
    with _mock_client({0: {"total": 3, "items": items}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    stored = verify.StoredSnapshot(
        identities=frozenset({_crn(0), _crn(1), _crn(2)}), cache_count=3, non_tampa_count=0
    )
    verdict = verify.reconcile(stored, scan)

    assert scan.reason is None
    assert verdict.verdict == "FAIL"
    assert verdict.reason == "identity_mismatch"
    assert _crn(2) in verdict.missing
    assert _crn(9) in verdict.extra


def test_total_changing_between_pages_fails_with_snapshot_changed() -> None:
    page0 = [_item(_crn(0)), _item(_crn(1))]
    page1 = [_item(_crn(2)), _item(_crn(3))]
    with _mock_client(
        {0: {"total": 5, "items": page0}, 2: {"total": 6, "items": page1}}
    ) as client:
        scan = verify.scan_pages(client, TERM, 2)

    assert scan.reason == "snapshot_changed"


def test_out_of_order_items_fail_with_order_violation() -> None:
    items = [_item(_crn(2)), _item(_crn(1))]
    with _mock_client({0: {"total": 2, "items": items}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    assert scan.reason == "order_violation"


def test_http_500_fails_with_http_status_reason() -> None:
    with _mock_client({0: {"status": 500}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    assert scan.reason == "http_status"


def test_malformed_json_body_fails_with_invalid_response_reason() -> None:
    with _mock_client({0: {"malformed": True}}) as client:
        scan = verify.scan_pages(client, TERM, 200)

    assert scan.reason == "invalid_response"


def test_collecting_more_items_than_total_fails_with_page_overrun() -> None:
    page0 = [_item(_crn(0)), _item(_crn(1))]
    page1 = [_item(_crn(2)), _item(_crn(3))]  # total says 3, but 4 identities are returned
    with _mock_client(
        {0: {"total": 3, "items": page0}, 2: {"total": 3, "items": page1}}
    ) as client:
        scan = verify.scan_pages(client, TERM, 2)

    assert scan.reason == "page_overrun"


def test_stored_non_tampa_section_fails_with_non_tampa_section_reason(
    session_factory: sessionmaker[Session],
    api_client: TestClient,
) -> None:
    with session_factory() as session:
        _seed_sections(session, count=2, campuses=["Tampa", "St. Petersburg"])

    with session_factory() as session:
        stored = verify.stored_identities(session, term=TERM)

    scan = verify.scan_pages(api_client, TERM, 200)
    verdict = verify.reconcile(stored, scan)

    assert scan.reason is None
    assert stored.non_tampa_count == 1
    assert verdict.verdict == "FAIL"
    assert verdict.reason == "non_tampa_section"


def test_score_source_split_counts_every_returned_section_without_claiming_coverage(
    session_factory: sessionmaker[Session],
    api_client: TestClient,
) -> None:
    with session_factory() as session:
        _seed_sections(session, count=3)

    scan = verify.scan_pages(api_client, TERM, 200)

    assert scan.reason is None
    total_counted = sum(scan.score_source_counts.values())
    assert total_counted == 3
    # score_source is a reporting split only; it is never treated as grade coverage
    # (D-20/D-21) by the scanner itself -- the split has no separate "coverage" field.
    assert set(scan.score_source_counts) <= {"course", "instructor_course", "subject", "global"}


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
