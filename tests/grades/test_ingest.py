from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from easy_a.common.lookups import ensure_term
from easy_a.db import Base
from easy_a.grades.cli import build_parser
from easy_a.grades.ingest import (
    GRADE_DISTRIBUTION_SOURCE,
    GradeCourseResolutionError,
    hash_file,
    ingest_grade_file,
)
from easy_a.grades.parser import GradeWorkbookValidationError
from easy_a.models import Course, GradeDistribution, IngestRun, Term

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
        database_session.add(
            Course(
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            )
        )
        database_session.commit()
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
    mac = session.execute(
        select(Course).where(Course.subject == "MAC", Course.number == "1105")
    ).scalar_one()

    assert first.records_inserted == 1
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert len(distributions) == 1
    assert distributions[0].crn == "89033"
    assert distributions[0].course_id == mac.id
    assert distributions[0].source == GRADE_DISTRIBUTION_SOURCE
    assert distributions[0].source_hash
    assert term.banner_code == "202408"
    assert term.name == "Fall 2024"


def test_grade_ingest_assigns_canonical_course_id(tmp_path: Path, session: Session) -> None:
    workbook_path = tmp_path / "assigns_course_id.xlsx"
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

    result = ingest_grade_file(session, "202408", workbook_path)

    mac = session.execute(
        select(Course).where(Course.subject == "MAC", Course.number == "1105")
    ).scalar_one()
    distribution = session.execute(select(GradeDistribution)).scalar_one()

    assert result.records_inserted == 1
    assert result.records_updated == 0
    assert distribution.course_id == mac.id


def test_same_key_reimport_backfills_null_course_id_without_duplicate(
    tmp_path: Path,
    session: Session,
) -> None:
    workbook_path = tmp_path / "backfill_null_course_id.xlsx"
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

    # Seed an existing null-attributed row with the exact same term/CRN/source identity
    # and source_hash the workbook will produce, so the only difference re-import repairs
    # is the missing course_id (D-04).
    term = ensure_term(session, "202408")
    session.add(
        GradeDistribution(
            term_id=term.id,
            crn="89033",
            course_id=None,
            section_number_raw="001",
            section_suffix_raw="C",
            campus_raw=None,
            a_count=10,
            b_count=4,
            c_count=0,
            d_count=0,
            f_count=0,
            i_count=0,
            s_count=0,
            u_count=0,
            w_count=1,
            other_count=0,
            total_grades=15,
            source=GRADE_DISTRIBUTION_SOURCE,
            source_hash=hash_file(workbook_path),
        )
    )
    session.commit()

    result = ingest_grade_file(session, "202408", workbook_path)

    distributions = session.execute(select(GradeDistribution)).scalars().all()
    mac = session.execute(
        select(Course).where(Course.subject == "MAC", Course.number == "1105")
    ).scalar_one()

    assert result.records_inserted == 0
    assert result.records_updated == 1
    assert len(distributions) == 1
    assert distributions[0].course_id == mac.id
    assert distributions[0].source_hash == hash_file(workbook_path)


def test_missing_courses_fail_atomically_and_report_all_keys(
    tmp_path: Path,
    session: Session,
) -> None:
    workbook_path = tmp_path / "mixed_known_unknown.xlsx"
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
            ],
            [
                "PSY-2012 -001-C (10001)",
                5,
                None,
                5,
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
                0,
                None,
                0,
                None,
                10,
            ],
            [
                "BSC-1005 -001-C (10002)",
                3,
                None,
                3,
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
                0,
                None,
                0,
                None,
                6,
            ],
        ],
    )

    with pytest.raises(GradeCourseResolutionError) as exc_info:
        ingest_grade_file(session, "202408", workbook_path)

    assert exc_info.value.unresolved_keys == (("BSC", "1005"), ("PSY", "2012"))
    assert exc_info.value.records_failed == 2

    ingest_run = session.execute(select(IngestRun)).scalar_one()
    distributions = session.execute(select(GradeDistribution)).scalars().all()

    assert ingest_run.status == "failed"
    assert ingest_run.records_seen == 3
    assert ingest_run.records_failed == 2
    assert ingest_run.error_message is not None
    assert "PSY 2012" in ingest_run.error_message
    assert "BSC 1005" in ingest_run.error_message
    assert distributions == []


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
