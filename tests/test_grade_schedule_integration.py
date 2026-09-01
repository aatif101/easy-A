from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from easy_a.grades.ingest import ingest_grade_file
from easy_a.models import GradeDistribution, Section, SectionInstructor, Term
from easy_a.schedule.ingest import ingest_schedule_html

FIXTURES = Path(__file__).parent / "fixtures"

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


def test_fall_2024_grade_and_schedule_join_by_term_crn(
    tmp_path: Path,
    db_session: Session,
) -> None:
    workbook_path = tmp_path / "fall_2024_89033.xlsx"
    _write_grade_workbook(workbook_path)
    schedule_html = (FIXTURES / "schedule_historical_202408_89033.html").read_text(
        encoding="utf-8"
    )

    ingest_grade_file(db_session, "202408", workbook_path)
    ingest_schedule_html(
        db_session,
        schedule_html,
        "202408",
        observed_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    db_session.commit()

    term = db_session.execute(select(Term).where(Term.banner_code == "202408")).scalar_one()
    grade = db_session.execute(
        select(GradeDistribution).where(
            GradeDistribution.term_id == term.id,
            GradeDistribution.crn == "89033",
        )
    ).scalar_one()
    section = db_session.execute(
        select(Section).where(Section.term_id == term.id, Section.crn == "89033")
    ).scalar_one()
    instructor = db_session.execute(
        select(SectionInstructor).where(SectionInstructor.section_id == section.id)
    ).scalar_one()

    assert grade.term_id == section.term_id
    assert grade.crn == section.crn
    assert section.seats_remaining == -17
    assert instructor.name_raw == "I. Rothstein"


def _write_grade_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    worksheet.append(
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
    )
    workbook.save(path)
