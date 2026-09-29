from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from easy_a.api.dependencies import get_api_session_factory, get_db_session
from easy_a.api.routes import metadata, rankings
from easy_a.api.schemas import HealthResponse
from easy_a.config import get_settings
from easy_a.schema_guard import require_sync_schema

request_logger = logging.getLogger("easy_a.request")


def _startup_engine() -> Engine:
    """The API's cached engine, so the startup probe shares the request pool."""
    bind = get_api_session_factory().kw["bind"]
    assert isinstance(bind, Engine)
    return bind


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Fail at startup, not on first request, when DATABASE_URL is missing or the schema lacks
    # migration 0004. Skipped when the DB dependency is overridden (tests); /health stays DB-free.
    if get_db_session not in app.dependency_overrides:
        get_settings().require_database_url()
        require_sync_schema(_startup_engine())
    yield


def _configure_logging() -> None:
    # uvicorn leaves the root logger at WARNING, which would drop INFO request lines.
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    request_logger.setLevel(logging.INFO)


def _matched_route(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


async def _log_request_duration(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """One JSON line per request: route template only, never the raw path or query string."""
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        request_logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "route": _matched_route(request),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
        )


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging()
    app = FastAPI(
        lifespan=_lifespan,
        title="Easy-A API",
        version="0.1.0",
        description="Thin API over computed Easy-A section rankings.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_frontend_origin_list(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.middleware("http")(_log_request_duration)

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_error_handler(
        _request: Request,
        _exc: SQLAlchemyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Database error."},
        )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(rankings.router)
    app.include_router(metadata.router)
    return app


app = create_app()
