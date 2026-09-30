from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import Course, Term
from easy_a.sync import courses as courses_module
from easy_a.sync.courses import CatalogSettings, CourseAdder
from tests.sync.sweep_support import TERM


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all(
            [
                Term(id=1, banner_code=TERM, name="Spring 2027", year=2027, season="Spring"),
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
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _offline_catalog_fetch(url: str) -> str:
    raise httpx.ConnectError(f"catalog is offline in tests: {url}")


@pytest.fixture(autouse=True)
def offline_default_course_adder(monkeypatch: pytest.MonkeyPatch) -> CourseAdder:
    """Sweeps without an explicit adder use the worker singleton; never let a test reach USF."""
    adder = CourseAdder(
        fetch=_offline_catalog_fetch,
        sleep=lambda seconds: None,
        settings=CatalogSettings(
            catalog_edition="2026-2027",
            catalog_url_template="https://catalog.invalid/{subject}/{number}",
        ),
    )
    monkeypatch.setattr(courses_module, "_default_adder", adder)
    return adder
