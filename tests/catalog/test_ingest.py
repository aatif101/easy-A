from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from easy_a.catalog.ingest import ingest_catalog_html
from easy_a.db import Base
from easy_a.models import Course, CourseAttribute, IngestRun

COURSEBLOCK_HTML = """
<html>
  <body>
    <div class="courseblock">
      <p class="courseblocktitle"><strong>MAC 1105 College Algebra Credit Hours: 3</strong></p>
      <p class="courseblockdesc">Linear equations, functions, and graphing.</p>
      <p><strong>Attribute(s):</strong> SGEM - General Education Core Mathematics</p>
    </div>
  </body>
</html>
"""


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def test_catalog_ingest_inserts_course_and_raw_attributes(session: Session) -> None:
    result = ingest_catalog_html(session, COURSEBLOCK_HTML, catalog_edition="2026-2027")

    course = session.execute(select(Course)).scalar_one()
    attributes = (
        session.execute(select(CourseAttribute).order_by(CourseAttribute.id)).scalars().all()
    )
    ingest_run = session.execute(select(IngestRun)).scalar_one()

    assert result.records_seen == 1
    assert result.records_inserted == 1
    assert result.records_updated == 0
    assert course.subject == "MAC"
    assert course.number == "1105"
    assert [(attribute.attribute_code, attribute.attribute_label) for attribute in attributes] == [
        ("SGEM", "General Education Core Mathematics"),
    ]
    assert ingest_run.status == "succeeded"


def test_catalog_ingest_is_idempotent_for_unchanged_course(session: Session) -> None:
    first = ingest_catalog_html(session, COURSEBLOCK_HTML, catalog_edition="2026-2027")
    second = ingest_catalog_html(session, COURSEBLOCK_HTML, catalog_edition="2026-2027")

    courses = session.execute(select(Course)).scalars().all()
    attributes = session.execute(select(CourseAttribute)).scalars().all()

    assert first.records_inserted == 1
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert len(courses) == 1
    assert len(attributes) == 1
