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
