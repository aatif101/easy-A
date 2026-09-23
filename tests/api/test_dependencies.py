from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from easy_a.api import dependencies


def test_db_session_dependency_reuses_one_engine_per_process(monkeypatch) -> None:
    created: list[object] = []

    def fake_get_engine():
        engine = create_engine("sqlite+pysqlite:///:memory:")
        created.append(engine)
        return engine

    monkeypatch.setattr(dependencies, "get_engine", fake_get_engine)
    dependencies.get_api_session_factory.cache_clear()
    try:
        sessions = []
        for _ in range(3):
            generator = dependencies.get_db_session()
            sessions.append(next(generator))
            generator.close()

        assert len(created) == 1
        assert all(session.get_bind() is created[0] for session in sessions)
        assert isinstance(dependencies.get_api_session_factory(), sessionmaker)
    finally:
        dependencies.get_api_session_factory.cache_clear()
