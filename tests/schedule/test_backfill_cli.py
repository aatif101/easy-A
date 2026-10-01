"""The backfill CLI as the D-04 rollout instrument: what-if, atomic apply, rollback, rebuild-only.

Seeds a small 202701 (live term) with one section taught by "X. Ou" and a 202408 grade history for
the same course, so the backfill moves exactly that section from course-level to instructor-course
scoring. Everything runs over SQLite and a fake USF client; nothing touches a live service.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from easy_a.db import Base
from easy_a.models import (
    Course,
    GradeDistribution,
    Section,
    SectionInstructor,
    SectionRankingCache,
    Term,
)
from easy_a.rankings.cache import refresh_section_rankings
from easy_a.schedule.backfill_cli import main
from easy_a.schedule.client import StaffScheduleClient
from tests.schedule.test_backfill import client_for, run
from tests.sync.sweep_support import table_counts
from tests.sync.wholeterm_html import RowSpec

SEEDED_AT = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
LIVE_TERM = "202701"
OU_CRN = "89033"
OTHER_CRN = "89100"
LIVE_OU_CRN = "70001"
LIVE_OTHER_CRN = "70002"

ClientFactory = Callable[[], StaffScheduleClient]


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    eng = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add_all(
            [
                Term(id=1, banner_code=LIVE_TERM, name="Spring 2027", year=2027, season="Spring"),
                Term(id=2, banner_code="202408", name="Fall 2024", year=2024, season="Fall"),
                Course(
                    id=10,
                    subject="MAC",
                    number="1105",
                    title="College Algebra",
                    catalog_edition="2026-2027",
                ),
            ]
        )
        session.commit()
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _grade(session: Session, *, crn: str, a: int, b: int, c: int, d: int, f: int) -> None:
    session.add(
        GradeDistribution(
            term_id=2,
            crn=crn,
            course_id=10,
            section_number_raw="001",
            a_count=a,
            b_count=b,
            c_count=c,
            d_count=d,
            f_count=f,
            total_grades=a + b + c + d + f,
            source="usf_infocenter",
            source_hash=f"hash-{crn}",
        )
    )


def _live_section(session: Session, *, crn: str, instructor: str) -> None:
    section = Section(
        term_id=1,
        crn=crn,
        course_id=10,
        section_number="001",
        campus="Tampa",
        session="Full Term",
        section_type="Class Lecture",
        primary_status="Active",
        delivery_method="CL",
        first_seen_at=SEEDED_AT,
        last_seen_at=SEEDED_AT,
    )
    session.add(section)
    session.flush()
    session.add(
        SectionInstructor(
            section_id=section.id,
            name_raw=instructor,
            name_normalized=None,
            source="usf_schedule_sync",
            observed_at=SEEDED_AT,
        )
    )


def seed_what_if(session_factory: sessionmaker[Session]) -> list[RowSpec]:
    """202408 grades for two MAC 1105 sections and a built 202701 cache; returns the USF rows."""
    with session_factory.begin() as session:
        _grade(session, crn=OU_CRN, a=20, b=10, c=5, d=3, f=2)  # 40 letter grades
        _grade(session, crn=OTHER_CRN, a=30, b=30, c=20, d=10, f=10)
        _live_section(session, crn=LIVE_OU_CRN, instructor="X. Ou")
        _live_section(session, crn=LIVE_OTHER_CRN, instructor="Staff")
        refresh_section_rankings(session, term=LIVE_TERM)
    return [
        RowSpec(crn=OU_CRN, subject="MAC", number="1105", instructor="X. Ou"),
        RowSpec(crn=OTHER_CRN, subject="MAC", number="1105", instructor="A. Other"),
    ]


def stored_scores(session_factory: sessionmaker[Session]) -> dict[str, tuple[Any, ...]]:
    with session_factory() as session:
        return {
            row.crn: (row.easiness_score, row.score_source, row.effective_n)
            for row in session.scalars(
                select(SectionRankingCache).where(SectionRankingCache.term == LIVE_TERM)
            )
        }


def historical_client(session_factory: sessionmaker[Session]) -> ClientFactory:
    factory, _ = client_for({"202408": seed_what_if(session_factory)})
    return factory


def dry_run(
    session_factory: sessionmaker[Session],
    client_factory: ClientFactory,
    capsys: pytest.CaptureFixture[str],
    *extra: str,
) -> tuple[int, dict[str, Any]]:
    return run(["--terms", "202408", "--dry-run", *extra], session_factory, client_factory, capsys)


def run_main_raw(
    argv: list[str],
    session_factory: sessionmaker[Session],
    client_factory: ClientFactory,
) -> int:
    return main(
        argv,
        session_factory=session_factory,
        client_factory=client_factory,
        now_fn=lambda: SEEDED_AT,
        sleep=lambda seconds: None,
    )


# --- Task 1: the dry-run what-if -----------------------------------------------------------------


def test_tracer_dry_run_reports_the_full_what_if_and_commits_nothing(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    counts_before = table_counts(session_factory)
    scores_before = stored_scores(session_factory)
    assert scores_before[LIVE_OU_CRN][1] == "course"

    code, report = dry_run(session_factory, client_factory, capsys)

    assert code == 0
    assert report["mode"] == "dry_run"
    assert report["status"] == "succeeded"
    what_if = report["what_if"]
    assert what_if["term"] == LIVE_TERM

    assert what_if["code_only_parity"]["identical"] is True
    ranking = what_if["ranking_diff"]
    assert ranking["changed"] == 1
    assert ranking["transitions"] == {"course->instructor_course": 1}
    assert ranking["course_level_violations"] == []
    assert ranking["course_level_invariant"] is True
    assert "changes" not in ranking

    pairs = what_if["pairs"]
    assert pairs["pairs_total"] == 2
    assert pairs["before_term"] == LIVE_TERM
    assert what_if["verdicts"] == {
        "code_only_parity": "PASS",
        "course_level_invariant": "PASS",
        "pairs_match_reference": "FAIL",  # a one-term seed cannot match the five-term reference
    }

    assert table_counts(session_factory) == counts_before
    assert stored_scores(session_factory) == scores_before


def test_report_json_carries_the_per_section_changes_list(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    client_factory = historical_client(session_factory)
    target = tmp_path / "what-if.json"

    code, report = dry_run(session_factory, client_factory, capsys, "--report-json", str(target))

    assert code == 0
    full = json.loads(target.read_text())
    changes = full["what_if"]["ranking_diff"]["changes"]
    assert [change["crn"] for change in changes] == [LIVE_OU_CRN]
    assert changes[0]["score_source_before"] == "course"
    assert changes[0]["score_source_after"] == "instructor_course"
    assert "changes" not in report["what_if"]["ranking_diff"]
    # Everything else on stdout is also in the file.
    full["what_if"]["ranking_diff"].pop("changes")
    full["what_if"]["code_only_parity"].pop("changes", None)
    assert full == report


def test_a_tampered_stored_cache_row_fails_code_only_parity(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    with session_factory.begin() as session:
        row = session.scalars(
            select(SectionRankingCache).where(SectionRankingCache.crn == LIVE_OTHER_CRN)
        ).one()
        row.easiness_score = row.easiness_score + 1.5

    code, report = dry_run(session_factory, client_factory, capsys)

    assert code == 1
    assert report["status"] == "failed"
    assert report["error_kind"] == "what_if"
    what_if = report["what_if"]
    assert what_if["verdicts"]["code_only_parity"] == "FAIL"
    assert what_if["code_only_parity"]["identical"] is False
    assert what_if["code_only_parity"]["changed"] == 1


def test_what_if_term_must_be_a_live_six_digit_term(
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:
    client_factory = historical_client(session_factory)
    for bad in ("202408", "2027", "abcdef"):
        code = run_main_raw(
            ["--terms", "202408", "--dry-run", "--what-if-term", bad],
            session_factory,
            client_factory,
        )
        assert code == 2
        assert capsys.readouterr().out == ""

