"""A short-lived, in-process cache of the API's public GET responses.

The hosted database bills for bytes sent to the API, and its data only changes when the sync
worker sweeps (every 5 minutes at the fastest). Identical searches inside ``ttl_seconds`` are
therefore served from memory instead of re-reading the same rows. A cached response is at most
``ttl_seconds`` older than a fresh one; the seat freshness label it carries was computed when it
was first served.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import Request, Response

from easy_a.api.dependencies import get_db_session

CACHED_PREFIXES = ("/api/v1/rankings/", "/api/v1/search", "/api/v1/metadata/")
# Sync status reports the worker's own health; it must never lag.
UNCACHED_PATHS = frozenset({"/api/v1/metadata/sync-status"})
DEFAULT_MAX_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class CachedResponse:
    expires_at: float
    body: bytes
    headers: dict[str, str]
    route: Any


class ResponseCache:
    """Least-recently-used entries, each kept for ``ttl_seconds``, bounded by total body bytes."""

    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_bytes: int = DEFAULT_MAX_BYTES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self._clock = clock
        self._entries: OrderedDict[str, CachedResponse] = OrderedDict()
        self._bytes = 0

    def get(self, key: str) -> CachedResponse | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            self._drop(key)
            return None
        self._entries.move_to_end(key)
        return entry

    def put(self, key: str, *, body: bytes, headers: dict[str, str], route: Any) -> None:
        # One response may use at most an eighth of the budget, so a few huge pages never
        # evict everything else.
        if len(body) > self.max_bytes // 8:
            return
        if key in self._entries:
            self._drop(key)
        self._entries[key] = CachedResponse(
            expires_at=self._clock() + self.ttl_seconds, body=body, headers=headers, route=route
        )
        self._bytes += len(body)
        while self._bytes > self.max_bytes:
            self._drop(next(iter(self._entries)))

    def _drop(self, key: str) -> None:
        self._bytes -= len(self._entries.pop(key).body)


def cache_key(request: Request) -> str:
    """Path plus the query parameters in sorted order, so parameter order never splits entries."""
    return f"{request.url.path}?{urlencode(sorted(request.query_params.multi_items()))}"


def _cacheable(request: Request) -> bool:
    path = request.url.path
    return (
        request.method == "GET"
        and path.startswith(CACHED_PREFIXES)
        and path not in UNCACHED_PATHS
        # Tests swap the session per test; a cache there would serve one test's rows to the next.
        and get_db_session not in request.app.dependency_overrides
    )


async def cache_get_responses(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """HTTP middleware: serve a fresh-enough cached 200 response, or fetch and remember one.

    It must sit inside the CORS middleware so CORS headers are added per request, never cached.
    """
    cache: ResponseCache | None = getattr(request.app.state, "response_cache", None)
    if cache is None or not _cacheable(request):
        return await call_next(request)

    key = cache_key(request)
    hit = cache.get(key)
    if hit is not None:
        # Lets the request log name the route even though the router did not run.
        request.scope["route"] = hit.route
        return Response(content=hit.body, status_code=200, headers=hit.headers)

    response = await call_next(request)
    if response.status_code != 200:
        return response
    body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
    headers = dict(response.headers)
    cache.put(key, body=body, headers=headers, route=request.scope.get("route"))
    return Response(content=body, status_code=200, headers=headers)
