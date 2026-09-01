from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from easy_a.db import Base
from easy_a.models import Course, Term


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Term(
                    id=1,
                    banner_code="202701",
                    name="Spring 2027",
                    year=2027,
                    season="Spring",
                ),
                Term(
                    id=2,
                    banner_code="202408",
                    name="Fall 2024",
                    year=2024,
                    season="Fall",
                ),
                Term(
                    id=3,
                    banner_code="202605",
                    name="Summer 2026",
                    year=2026,
                    season="Summer",
                ),
                Course(
                    id=10,
                    subject="MAC",
                    number="1105",
                    title="College Algebra",
                    catalog_edition="2026-2027",
                ),
                Course(
                    id=11,
                    subject="ENC",
                    number="1101",
                    title="Composition I",
                    catalog_edition="2026-2027",
                ),
            ]
        )
        session.commit()
        yield session
