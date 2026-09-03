from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from easy_a.api.routes import metadata, rankings
from easy_a.api.schemas import HealthResponse
from easy_a.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
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
