from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from easy_a.db import Base
from easy_a.grades.cli import build_parser
from easy_a.grades.ingest import ingest_grade_file
from easy_a.grades.parser import GradeWorkbookValidationError
from easy_a.models import GradeDistribution, IngestRun, Term

GRADE_HEADER = [
    "course",
    "A",
    "% A",
    "B",
    "% B",
    "C",
    "% C",
    "D",
    "% D",
    "F",
    "% F",
    "I",
    "% I",
    "S",
    "% S",
    "U",
    "% U",
    "W",
    "% W",
    "O",
    "% O",
    "Total Grades",
]


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def test_duplicate_grade_ingestion_is_idempotent(tmp_path: Path, session: Session) -> None:
    workbook_path = tmp_path / "synthetic_grade_distribution.xlsx"
    _write_workbook(
        workbook_path,
        [
            [
                "MAC-1105 -001-C (89033)",
                10,
                None,
                4,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                1,
                None,
                0,
                None,
                15,
            ]
        ],
    )

    first = ingest_grade_file(session, "202408", workbook_path)
    second = ingest_grade_file(session, "202408", workbook_path)

    distributions = session.execute(select(GradeDistribution)).scalars().all()
    term = session.execute(select(Term)).scalar_one()

    assert first.records_inserted == 1
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert len(distributions) == 1
    assert distributions[0].crn == "89033"
    assert distributions[0].source_hash
    assert term.banner_code == "202408"
    assert term.name == "Fall 2024"


def test_invalid_total_logs_failed_ingest_run(tmp_path: Path, session: Session) -> None:
    workbook_path = tmp_path / "invalid_total.xlsx"
    _write_workbook(
        workbook_path,
        [
            [
                "MAC-1105 -001-C (89033)",
                10,
                None,
                4,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                0,
                None,
                1,
                None,
                0,
                None,
                99,
            ]
        ],
    )

    with pytest.raises(GradeWorkbookValidationError):
        ingest_grade_file(session, "202408", workbook_path)

    ingest_run = session.execute(select(IngestRun)).scalar_one()
    distributions = session.execute(select(GradeDistribution)).scalars().all()

    assert ingest_run.status == "failed"
    assert ingest_run.records_seen == 1
    assert ingest_run.records_failed == 1
    assert distributions == []


def test_grade_cli_requires_term() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--file", "sample.xlsx"])


def _write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
