from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from easy_a.api.dependencies import get_db_session
from easy_a.api.routes import metadata, rankings
from easy_a.api.schemas import HealthResponse
from easy_a.config import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Fail at startup, not on first request, when DATABASE_URL is missing.
    if get_db_session not in app.dependency_overrides:
        get_settings().require_database_url()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
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
