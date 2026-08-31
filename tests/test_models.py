from __future__ import annotations

from sqlalchemy import create_engine, inspect

import easy_a.models  # noqa: F401
from easy_a.db import Base


def test_model_metadata_can_create_all_tables_in_test_database() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    Base.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())

    assert {
        "terms",
        "courses",
        "course_attributes",
        "grade_distributions",
        "ingest_runs",
    }.issubset(table_names)
