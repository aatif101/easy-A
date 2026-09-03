from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    SeatSnapshot,
    Section,
    SectionInstructor,
    Syllabus,
)
from easy_a.refresh import (
    CatalogInput,
    GradeInput,
    RefreshConfig,
    ScheduleInput,
    SourceMode,
    SyllabusFileInput,
    SyllabusInput,
    refresh_data,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
NOW = datetime(2026, 9, 3, 12, tzinfo=UTC)
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


def test_successful_multistage_refresh_uses_offline_sources(tmp_path: Path) -> None:
    factory, config = _offline_refresh(tmp_path)

    result = refresh_data(
        config,
        session_factory=factory,
        observed_at=NOW,
        quality_as_of=NOW,
    )

    assert result.term == "202701"
    assert result.courses == 1
    assert result.sections == 2
    assert result.instructor_observations_added == 2
    assert result.seat_snapshots_added == 2
    assert result.grade_rows == 1
    assert result.syllabi == 1
    assert result.quality_report.error_count == 0
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Course)) == 1
        assert session.scalar(select(func.count()).select_from(GradeDistribution)) == 1
        assert session.scalar(select(func.count()).select_from(Syllabus)) == 1


def test_rerun_preserves_canonical_sections_and_appends_snapshots(tmp_path: Path) -> None:
    factory, config = _offline_refresh(tmp_path)

    first = refresh_data(
        config,
        session_factory=factory,
        observed_at=NOW,
        quality_as_of=NOW,
    )
    second = refresh_data(
        config,
        session_factory=factory,
        observed_at=NOW + timedelta(hours=1),
        quality_as_of=NOW + timedelta(hours=1),
    )

    assert first.sections == second.sections == 2
    assert second.seat_snapshots_added == 2
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Section)) == 2
        assert session.scalar(select(func.count()).select_from(SeatSnapshot)) == 4
        assert session.scalar(select(func.count()).select_from(SectionInstructor)) == 4
        assert session.scalar(select(func.count()).select_from(GradeDistribution)) == 1
        assert session.scalar(select(func.count()).select_from(Syllabus)) == 1


def _offline_refresh(tmp_path: Path) -> tuple[sessionmaker[Session], RefreshConfig]:
    catalog_path = tmp_path / "catalog.html"
    catalog_path.write_text(_catalog_html(), encoding="utf-8")
    schedule_path = tmp_path / "schedule.html"
    schedule_html = (FIXTURES / "schedule_current.html").read_text(encoding="utf-8")
    schedule_path.write_text(schedule_html.replace("<td>-17</td>", "<td>0</td>"), encoding="utf-8")
    grade_path = tmp_path / "grades.xlsx"
    _write_grade_workbook(grade_path)
    syllabus_path = tmp_path / "syllabus.html"
    syllabus_path.write_text(_syllabus_html(), encoding="utf-8")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    config = RefreshConfig(
        term="202701",
        catalog=CatalogInput(
            source=SourceMode.file,
            catalog_edition="2026-2027",
            file_path=catalog_path,
        ),
        schedule=ScheduleInput(source=SourceMode.file, file_path=schedule_path),
        grades=GradeInput(file_path=grade_path),
        syllabi=SyllabusInput(
            source=SourceMode.file,
            files=(SyllabusFileInput(document_id="fixture-doc", file_path=syllabus_path),),
        ),
        stale_after=timedelta(days=7),
    )
    return factory, config


def _catalog_html() -> str:
    return """
    <div class="courseblock">
      <p class="courseblocktitle"><strong>MAC 1105 College Algebra Credit Hours: 3</strong></p>
      <p class="courseblockdesc">Linear equations, functions, and graphing.</p>
      <p><strong>Attribute(s):</strong> SGEM - General Education Core Mathematics</p>
    </div>
    """


def _syllabus_html() -> str:
    return """
    <div class="syllabus">
      <div data-block-name="term_name">Spring 2027</div>
      <div data-block-name="subject_name">MAC</div>
      <div data-block-name="course_ca_30">1105</div>
      <div data-block-name="section_name">001</div>
      <div data-block-name="section_ca_7">13173</div>
      <div data-block-name="section_ca_33">College Algebra</div>
      <div class="instructor-component"><div class="cell-content">Staff</div></div>
      <section><p>Attendance is required.</p></section>
    </div>
    """


def _write_grade_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(GRADE_HEADER)
    worksheet.append(
        [
            "MAC-1105 -001-C (13173)",
            7,
            None,
            2,
            None,
            1,
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
        ]
    )
    workbook.save(path)
