from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from easy_a.sync.lock import SYNC_LOCK_KEY, try_sweep_lock


def test_sqlite_session_always_gets_the_lock() -> None:
    engine = create_engine("sqlite://")
    with Session(engine) as first, Session(engine) as second:
        assert try_sweep_lock(first) is True
        assert try_sweep_lock(second) is True


def test_postgres_dialect_issues_the_transaction_scoped_lock_statement() -> None:
    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _FakeSession:
        def __init__(self, answer: bool) -> None:
            self.answer = answer
            self.statements: list[tuple[str, object]] = []

        def get_bind(self) -> _Bind:
            return _Bind()

        def scalar(self, statement: object, params: object = None) -> bool:
            self.statements.append((str(statement), params))
            return self.answer

    taken = _FakeSession(True)
    busy = _FakeSession(False)
    assert try_sweep_lock(taken) is True  # type: ignore[arg-type]
    assert try_sweep_lock(busy) is False  # type: ignore[arg-type]
    sql, params = taken.statements[0]
    assert "pg_try_advisory_xact_lock" in sql
    assert "pg_try_advisory_lock" not in sql
    assert params == {"key": SYNC_LOCK_KEY}


def test_lock_key_is_a_stable_positive_bigint() -> None:
    assert 0 < SYNC_LOCK_KEY < 2**63
    assert SYNC_LOCK_KEY.to_bytes(6, "big") == b"EASYNC"


def test_postgres_xact_lock_excludes_a_second_connection_until_commit() -> None:
    url = os.environ.get("EASY_A_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set EASY_A_TEST_POSTGRES_URL to run PostgreSQL integration")
    engine = create_engine(url)
    assert engine.dialect.name == "postgresql"
    try:
        with Session(engine) as first, Session(engine) as second:
            first.execute(text("SELECT 1"))
            assert try_sweep_lock(first) is True
            assert try_sweep_lock(second) is False
            second.rollback()
            first.commit()
            assert try_sweep_lock(second) is True
            second.commit()
    finally:
        engine.dispose()
