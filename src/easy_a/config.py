from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a",
        validation_alias="DATABASE_URL",
    )
    echo_sql: bool = Field(default=False, validation_alias="EASY_A_ECHO_SQL")
    api_host: str = Field(default="127.0.0.1", validation_alias="EASY_A_API_HOST")
    api_port: int = Field(default=8000, validation_alias="EASY_A_API_PORT")
    allowed_frontend_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="EASY_A_ALLOWED_FRONTEND_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def allowed_frontend_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_frontend_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
