from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from easy_a.db import Base
from easy_a.schema_guard import SchemaNotCurrentError, require_sync_schema


def _stale_engine() -> Engine:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sections (id INTEGER PRIMARY KEY, crn VARCHAR(16))"))
    return engine


def _current_engine() -> Engine:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _assert_safe_message(error: SchemaNotCurrentError) -> None:
    message = str(error)
    assert "0004_sync_removed_at" in message
    assert "sqlite://" not in message
    assert "postgresql" not in message


def test_stale_schema_raises_with_migration_name_and_no_url() -> None:
    engine = _stale_engine()

    with pytest.raises(SchemaNotCurrentError) as excinfo:
        require_sync_schema(engine)

    _assert_safe_message(excinfo.value)
    assert isinstance(excinfo.value.__cause__, Exception)


def test_stale_schema_raises_for_a_connection() -> None:
    engine = _stale_engine()

    with engine.connect() as connection, pytest.raises(SchemaNotCurrentError) as excinfo:
        require_sync_schema(connection)

    _assert_safe_message(excinfo.value)


def test_current_schema_passes_for_engine_and_connection() -> None:
    engine = _current_engine()

    assert require_sync_schema(engine) is None
    with engine.connect() as connection:
        assert require_sync_schema(connection) is None
        # The connection stays usable after the probe.
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
