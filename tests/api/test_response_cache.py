from __future__ import annotations

import json
import logging

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from easy_a.api.app import _log_request_duration, create_app
from easy_a.api.dependencies import get_db_session
from easy_a.api.response_cache import ResponseCache, cache_get_responses

ORIGIN = "https://easya.fyi"


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _app(cache: ResponseCache | None) -> tuple[FastAPI, dict[str, int]]:
    """The production middleware stack (logging, CORS, cache) around counting endpoints."""
    calls: dict[str, int] = {}
    router = APIRouter(prefix="/api/v1/rankings")

    @router.get("/search")
    def search(subject: str = "", limit: int = 50) -> dict[str, object]:
        calls["search"] = calls.get("search", 0) + 1
        return {"subject": subject, "limit": limit, "call": calls["search"]}

    @router.get("/missing")
    def missing() -> None:
        calls["missing"] = calls.get("missing", 0) + 1
        raise HTTPException(status_code=404, detail="no such section")

    status_router = APIRouter(prefix="/api/v1/metadata")

    @status_router.get("/sync-status")
    def sync_status() -> dict[str, int]:
        calls["sync-status"] = calls.get("sync-status", 0) + 1
        return {"call": calls["sync-status"]}

    app = FastAPI()
    app.state.response_cache = cache
    app.middleware("http")(cache_get_responses)
    app.add_middleware(CORSMiddleware, allow_origins=[ORIGIN], allow_methods=["GET"])
    app.middleware("http")(_log_request_duration)
    app.include_router(router)
    app.include_router(status_router)
    return app, calls


def test_identical_searches_inside_the_ttl_read_the_database_once() -> None:
    clock = Clock()
    app, calls = _app(ResponseCache(ttl_seconds=60, clock=clock))
    client = TestClient(app)

    first = client.get("/api/v1/rankings/search?subject=MAC&limit=20")
    reordered = client.get("/api/v1/rankings/search?limit=20&subject=MAC")
    other = client.get("/api/v1/rankings/search?subject=ENC&limit=20")
    clock.now = 61
    expired = client.get("/api/v1/rankings/search?subject=MAC&limit=20")

    assert first.json() == reordered.json() == {"subject": "MAC", "limit": 20, "call": 1}
    assert reordered.headers["content-type"] == "application/json"
    assert other.json()["call"] == 2
    assert expired.json()["call"] == 3
    assert calls["search"] == 3


def test_cors_headers_are_added_per_request_never_cached() -> None:
    app, calls = _app(ResponseCache(ttl_seconds=60))
    client = TestClient(app)

    without_origin = client.get("/api/v1/rankings/search?subject=MAC")
    with_origin = client.get("/api/v1/rankings/search?subject=MAC", headers={"Origin": ORIGIN})

    assert calls["search"] == 1
    assert "access-control-allow-origin" not in without_origin.headers
    assert with_origin.headers["access-control-allow-origin"] == ORIGIN


def test_errors_and_sync_status_are_never_cached() -> None:
    app, calls = _app(ResponseCache(ttl_seconds=60))
    client = TestClient(app)

    for _ in range(2):
        assert client.get("/api/v1/rankings/missing").status_code == 404
        client.get("/api/v1/metadata/sync-status")

    assert calls == {"missing": 2, "sync-status": 2}


def test_a_cache_hit_still_logs_the_route_template(caplog: pytest.LogCaptureFixture) -> None:
    app, _calls = _app(ResponseCache(ttl_seconds=60))
    client = TestClient(app)
    caplog.set_level(logging.INFO, logger="easy_a.request")

    client.get("/api/v1/rankings/search?subject=MAC")
    client.get("/api/v1/rankings/search?subject=MAC")

    routes = [
        json.loads(record.getMessage())["route"]
        for record in caplog.records
        if record.name == "easy_a.request"
    ]
    assert routes == ["/api/v1/rankings/search", "/api/v1/rankings/search"]


def test_entries_are_evicted_by_total_size() -> None:
    cache = ResponseCache(ttl_seconds=60, max_bytes=800)
    for index in range(10):
        cache.put(f"k{index}", body=b"x" * 100, headers={}, route=None)

    assert cache.get("k0") is None
    assert cache.get("k9") is not None
    cache.put("huge", body=b"x" * 101, headers={}, route=None)
    assert cache.get("huge") is None


def test_no_cache_when_disabled_or_when_tests_swap_the_session() -> None:
    disabled, calls = _app(None)
    client = TestClient(disabled)
    client.get("/api/v1/rankings/search")
    client.get("/api/v1/rankings/search")
    assert calls["search"] == 2

    overridden, override_calls = _app(ResponseCache(ttl_seconds=60))
    overridden.dependency_overrides[get_db_session] = lambda: None
    client = TestClient(overridden)
    client.get("/api/v1/rankings/search")
    client.get("/api/v1/rankings/search")
    assert override_calls["search"] == 2


def test_the_real_app_enables_the_cache_by_default_and_honours_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from easy_a.config import get_settings

    assert isinstance(create_app().state.response_cache, ResponseCache)
    monkeypatch.setenv("EASY_A_RESPONSE_CACHE_SECONDS", "0")
    get_settings.cache_clear()
    try:
        assert create_app().state.response_cache is None
    finally:
        monkeypatch.delenv("EASY_A_RESPONSE_CACHE_SECONDS")
        get_settings.cache_clear()
