from __future__ import annotations

import pytest

from easy_a.config import DatabaseConfigError, Settings, normalize_database_url
from easy_a.db import get_engine, is_transaction_pooler

POOLER = "postgresql://u.ref:pw@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"
DIRECT = "postgresql://postgres:pw@db.ref.supabase.co:5432/postgres?sslmode=require"
LOCAL = "postgresql+psycopg://easy_a:easy_a@localhost:5432/easy_a"


def _settings(**env: str | None) -> Settings:
    return Settings(_env_file=None, **env)  # type: ignore[call-arg]


def test_missing_database_url_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigError, match="DATABASE_URL is not set"):
        _settings().require_database_url()
    with pytest.raises(DatabaseConfigError):
        _settings().require_migration_database_url()


def test_normalize_driver_prefix() -> None:
    assert normalize_database_url(POOLER).startswith("postgresql+psycopg://")
    assert normalize_database_url("postgres://a@h/d") == "postgresql+psycopg://a@h/d"
    assert normalize_database_url(LOCAL) == LOCAL


def test_migration_url_preferred_then_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    only_app = _settings(DATABASE_URL=POOLER)
    assert ":6543/" in only_app.require_migration_database_url()
    both = _settings(DATABASE_URL=POOLER, MIGRATION_DATABASE_URL=DIRECT)
    assert ":5432/" in both.require_migration_database_url()
    assert ":6543/" in both.require_database_url()


def test_pooler_detection() -> None:
    assert is_transaction_pooler(normalize_database_url(POOLER))
    assert not is_transaction_pooler(normalize_database_url(DIRECT))
    assert not is_transaction_pooler(LOCAL)


def test_pooler_engine_disables_prepared_statements() -> None:
    engine = get_engine(POOLER)
    assert engine.dialect.name == "postgresql"
    assert engine.pool._pre_ping is True  # type: ignore[attr-defined]
    assert engine.dialect.create_connect_args(engine.url) is not None
    engine.dispose()


def test_local_engine_unchanged() -> None:
    engine = get_engine(LOCAL)
    assert engine.pool._pre_ping is True  # type: ignore[attr-defined]
    engine.dispose()
