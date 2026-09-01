from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import Column, Integer, String, Table, create_engine
from sqlalchemy.orm import Session

from easy_a.db import Base

TERMS = Table(
    "terms",
    Base.metadata,
    Column[int]("id", Integer, primary_key=True),
    Column[str]("banner_code", String(6), nullable=False, unique=True),
)
COURSES = Table(
    "courses",
    Base.metadata,
    Column[int]("id", Integer, primary_key=True),
    Column[str]("subject", String(16), nullable=False),
    Column[str]("number", String(16), nullable=False),
    Column[str]("catalog_edition", String(32), nullable=False),
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.execute(
            TERMS.insert(),
            [
                {"id": 1, "banner_code": "202701"},
                {"id": 2, "banner_code": "202408"},
                {"id": 3, "banner_code": "202605"},
            ],
        )
        session.execute(
            COURSES.insert(),
            [
                {"id": 10, "subject": "MAC", "number": "1105", "catalog_edition": "2026"},
                {"id": 11, "subject": "ENC", "number": "1101", "catalog_edition": "2026"},
            ],
        )
        session.commit()
        yield session
