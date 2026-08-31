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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
