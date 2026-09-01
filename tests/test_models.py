from __future__ import annotations

from sqlalchemy import UniqueConstraint, create_engine, inspect

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
        "sections",
        "section_instructors",
        "seat_snapshots",
        "syllabi",
    }.issubset(table_names)
    assert "section_id" not in Base.metadata.tables["grade_distributions"].c


def test_feature_model_tables_and_identity_constraints_are_registered() -> None:
    assert {"sections", "section_instructors", "seat_snapshots", "syllabi"}.issubset(
        Base.metadata.tables
    )

    section_constraints = Base.metadata.tables["sections"].constraints
    section_unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in section_constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("term_id", "crn") in section_unique_columns
    assert Base.metadata.tables["syllabi"].c.document_id.unique is True
