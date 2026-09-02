from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from easy_a.db import Base
from easy_a.models import (
    Course,
    CourseAttribute,
    GradeDistribution,
    Section,
    SectionInstructor,
    Term,
)
from easy_a.rankings.cli import build_course_parser, build_section_parser, section_main

NOW = datetime(2026, 9, 1, tzinfo=UTC)


def test_rank_section_cli_requires_term_and_crn() -> None:
    parser = build_section_parser()

    args = parser.parse_args(["--term", "202701", "--crn", "77001"])

    assert args.term == "202701"
    assert args.crn == "77001"


def test_rank_course_cli_requires_term_subject_and_course() -> None:
    parser = build_course_parser()

    args = parser.parse_args(["--term", "202701", "--subject", "MAC", "--course", "1105"])

    assert args.term == "202701"
    assert args.subject == "MAC"
    assert args.course == "1105"


def test_rank_section_cli_outputs_synthetic_spring_2027_fixture(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    session_factory = _build_cli_database(tmp_path)
    monkeypatch.setattr(
        "easy_a.rankings.cli.get_session_factory",
        lambda: session_factory,
    )

    assert section_main(["--term", "202701", "--crn", "77001"]) == 0

    assert capsys.readouterr().out == (
        "{\n"
        '  "term": "202701",\n'
        '  "term_name": "Spring 2027",\n'
        '  "crn": "77001",\n'
        '  "subject": "MAC",\n'
        '  "course_number": "1105",\n'
        '  "course_title": "College Algebra",\n'
        '  "instructor": "I. Rothstein",\n'
        '  "instructor_provenance": {\n'
        '    "freshness": "current",\n'
        '    "source": "section_instructors",\n'
        '    "source_term": "202701",\n'
        '    "detail": "latest observed instructor state"\n'
        "  },\n"
        '  "modality": {\n'
        '    "delivery_method": "CL",\n'
        '    "delivery_label": "Classroom 1\\u201349%",\n'
        '    "provenance": {\n'
        '      "freshness": "current",\n'
        '      "source": "sections.delivery_method",\n'
        '      "source_term": "202701",\n'
        '      "detail": null\n'
        "    }\n"
        "  },\n"
        '  "seats_remaining": 12,\n'
        '  "seats": {\n'
        '    "capacity": 30,\n'
        '    "enrollment": 18,\n'
        '    "seats_remaining": 12,\n'
        '    "wait_seats_available": 0,\n'
        '    "provenance": {\n'
        '      "freshness": "current",\n'
        '      "source": "sections.current_seat_fields",\n'
        '      "source_term": "202701",\n'
        '      "detail": "canonical section seat fields; no seat snapshot is stored"\n'
        "    }\n"
        "  },\n"
        '  "gened_attributes": [\n'
        "    {\n"
        '      "code": "SMEL",\n'
        '      "label": "Enhanced General Education Mathematics"\n'
        "    }\n"
        "  ],\n"
        '  "gened_provenance": {\n'
        '    "freshness": "current",\n'
        '    "source": "course_attributes",\n'
        '    "source_term": null,\n'
        '    "detail": "catalog_edition=2026-2027"\n'
        "  },\n"
        '  "easiness_score": 8.904761904761905,\n'
        '  "smoothed_withdrawal_rate": 0.047619047619047616,\n'
        '  "confidence_label": "low",\n'
        '  "effective_n": 100.0,\n'
        '  "score_source": "instructor_course",\n'
        '  "historical_analytics": {\n'
        '    "easiness_score": 8.904761904761905,\n'
        '    "smoothed_withdrawal_rate": 0.047619047619047616,\n'
        '    "confidence_label": "low",\n'
        '    "effective_n": 100.0,\n'
        '    "score_source": "instructor_course",\n'
        '    "prior_level": "course",\n'
        '    "completed_grade_count": 100,\n'
        '    "total_grade_count": 105,\n'
        '    "withdrawal_count": 5,\n'
        '    "section_count": 1,\n'
        '    "term_count": 1,\n'
        '    "mapped_instructor_section_count": 1,\n'
        '    "provenance": {\n'
        '      "freshness": "historical",\n'
        '      "source": "grade_distributions",\n'
        '      "source_term": null,\n'
        '      "detail": "computed from terms before 202701; non-grade data is excluded"\n'
        "    }\n"
        "  },\n"
        '  "signals": [\n'
        "    {\n"
        '      "signal_type": "attendance",\n'
        '      "value": "not_required",\n'
        '      "confidence": 0.99,\n'
        '      "source": "schedule_section_note",\n'
        '      "source_identifier": "section:200:note",\n'
        '      "source_term": "202701",\n'
        '      "freshness": "current",\n'
        '      "evidence": "Attendance is not required."\n'
        "    }\n"
        "  ],\n"
        '  "signal_provenance": {\n'
        '    "freshness": "current",\n'
        '    "source": "schedule_section_note",\n'
        '    "source_term": "202701",\n'
        '    "detail": "signal resolver source precedence"\n'
        "  },\n"
        '  "section_provenance": {\n'
        '    "freshness": "current",\n'
        '    "source": "sections",\n'
        '    "source_term": "202701",\n'
        '    "detail": "resolved by current term and CRN"\n'
        "  }\n"
        "}\n"
    )


def _build_cli_database(tmp_path: Path) -> sessionmaker[Session]:
    database_path = tmp_path / "rankings.sqlite"
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
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
                Course(
                    id=10,
                    subject="MAC",
                    number="1105",
                    title="College Algebra",
                    catalog_edition="2026-2027",
                ),
                CourseAttribute(
                    course_id=10,
                    attribute_code="SMEL",
                    attribute_label="Enhanced General Education Mathematics",
                ),
            ]
        )
        historical = _section(
            section_id=100,
            term_id=2,
            crn="89033",
            instructor="I. Rothstein",
        )
        current = _section(
            section_id=200,
            term_id=1,
            crn="77001",
            instructor="I. Rothstein",
            capacity=30,
            enrollment=18,
            seats_remaining=12,
            note="Attendance is not required.",
        )
        session.add_all(
            [
                historical,
                current,
                _instructor(section_id=100, name="I. Rothstein"),
                _instructor(section_id=200, name="I. Rothstein"),
                GradeDistribution(
                    term_id=2,
                    crn="89033",
                    course_id=10,
                    section_number_raw="001",
                    section_suffix_raw="C",
                    campus_raw="Tampa",
                    a_count=60,
                    b_count=30,
                    c_count=10,
                    d_count=0,
                    f_count=0,
                    i_count=0,
                    s_count=0,
                    u_count=0,
                    w_count=5,
                    other_count=0,
                    total_grades=105,
                    source="synthetic",
                    source_hash="synthetic",
                ),
            ]
        )
        session.commit()
    return factory


def _section(
    *,
    section_id: int,
    term_id: int,
    crn: str,
    instructor: str,
    capacity: int | None = None,
    enrollment: int | None = None,
    seats_remaining: int | None = None,
    note: str | None = None,
) -> Section:
    return Section(
        id=section_id,
        term_id=term_id,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        secondary_status=None,
        delivery_method="CL",
        capacity=capacity,
        enrollment=enrollment,
        seats_remaining=seats_remaining,
        wait_seats_available=0 if seats_remaining is not None else None,
        section_note=note,
        first_seen_at=NOW,
        last_seen_at=NOW,
    )


def _instructor(*, section_id: int, name: str) -> SectionInstructor:
    return SectionInstructor(
        section_id=section_id,
        name_raw=name,
        name_normalized=name.lower(),
        source="synthetic",
        observed_at=NOW,
    )
