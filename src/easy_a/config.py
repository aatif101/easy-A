from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MISSING_DATABASE_URL_MESSAGE = (
    "DATABASE_URL is not set. Set it in the environment or .env "
    "(see .env.example), e.g. postgresql+psycopg://user:password@host:5432/dbname. "
    "There is no localhost fallback."
)


class DatabaseConfigError(RuntimeError):
    """Raised when the database connection is missing or misconfigured."""


def normalize_database_url(url: str) -> str:
    """Force the psycopg driver (Supabase copies plain postgresql:// / postgres://)."""
    url = url.strip()
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Settings(BaseSettings):
    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    migration_database_url: str | None = Field(
        default=None, validation_alias="MIGRATION_DATABASE_URL"
    )
    course_targets_path: str = Field(
        default="config/course_targets.toml", validation_alias="EASY_A_COURSE_TARGETS_PATH"
    )
    seat_fresh_seconds: int = Field(default=600, ge=0, validation_alias="EASY_A_SEAT_FRESH_SECONDS")
    seat_stale_seconds: int = Field(
        default=1800, ge=0, validation_alias="EASY_A_SEAT_STALE_SECONDS"
    )
    echo_sql: bool = Field(default=False, validation_alias="EASY_A_ECHO_SQL")
    api_host: str = Field(default="127.0.0.1", validation_alias="EASY_A_API_HOST")
    api_port: int = Field(default=8000, validation_alias="EASY_A_API_PORT")
    allowed_frontend_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="EASY_A_ALLOWED_FRONTEND_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def require_database_url(self) -> str:
        """Return the app connection URL, failing loudly if DATABASE_URL is unset."""
        if not (self.database_url and self.database_url.strip()):
            raise DatabaseConfigError(MISSING_DATABASE_URL_MESSAGE)
        return normalize_database_url(self.database_url)

    def require_migration_database_url(self) -> str:
        """Alembic URL: MIGRATION_DATABASE_URL (direct/session), else DATABASE_URL."""
        if self.migration_database_url and self.migration_database_url.strip():
            return normalize_database_url(self.migration_database_url)
        return self.require_database_url()

    def allowed_frontend_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.allowed_frontend_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
