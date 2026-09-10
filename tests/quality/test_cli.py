from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from easy_a.db import Base
from easy_a.models import GradeDistribution, Term
from easy_a.quality.cli import main


def test_quality_cli_returns_zero_without_error_findings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory = _factory_with_term()

    exit_code = main(["--term", "202701", "--json"], session_factory=factory)

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert exit_code == 0
    assert payload["error_count"] == 0


def test_quality_cli_returns_nonzero_only_for_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory = _factory_with_term()
    with factory.begin() as session:
        session.add(
            GradeDistribution(
                term_id=1,
                crn="99999",
                course_id=None,
                section_number_raw="001",
                a_count=1,
                b_count=0,
                c_count=0,
                d_count=0,
                f_count=0,
                i_count=0,
                s_count=0,
                u_count=0,
                w_count=0,
                other_count=0,
                total_grades=1,
                source="synthetic",
                source_hash="synthetic",
            )
        )

    exit_code = main(["--term", "202701"], session_factory=factory)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "ERROR orphan_grade_row CRN 99999" in output


def _factory_with_term() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(
            Term(
                id=1,
                banner_code="202701",
                name="Spring 2027",
                year=2027,
                season="Spring",
            )
        )
    return factory


def test_quality_cli_reports_unsupported_campus_sections(
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory = _factory_with_term()
    _add_section(factory, crn="12345", campus="St. Petersburg")

    exit_code = main(["--term", "202701"], session_factory=factory)

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "ERROR unsupported_campus_section" in output
    assert "St. Petersburg" in output


def test_quality_cli_campus_flag_widens_the_supported_campus(
    capsys: pytest.CaptureFixture[str],
) -> None:
    factory = _factory_with_term()
    _add_section(factory, crn="12345", campus="St. Petersburg")

    exit_code = main(
        ["--term", "202701", "--campus", "St. Petersburg"], session_factory=factory
    )

    assert exit_code == 0
    assert "unsupported_campus_section" not in capsys.readouterr().out


def _add_section(factory: sessionmaker[Session], *, crn: str, campus: str) -> None:
    from datetime import UTC, datetime

    from easy_a.models import Course, Section

    with factory.begin() as session:
        session.add(
            Course(
                id=10,
                subject="MAC",
                number="1105",
                title="College Algebra",
                catalog_edition="2026-2027",
            )
        )
        session.flush()
        observed_at = datetime(2026, 9, 3, 12, tzinfo=UTC)
        session.add(
            Section(
                term_id=1,
                crn=crn,
                course_id=10,
                section_number="001",
                campus=campus,
                session="Full Term",
                section_type="Class Lecture",
                primary_status="Open",
                delivery_method="CL",
                first_seen_at=observed_at,
                last_seen_at=observed_at,
            )
        )
